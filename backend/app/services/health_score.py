"""
Financial health score (0-100).
Formula is fully transparent and documented in the UI.
Each factor contributes a max sub-score; total is the sum.
"""
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session


FACTOR_WEIGHTS = {
    "savings_rate":          20,
    "budget_adherence":      20,
    "emergency_fund":        20,
    "debt_to_income":        15,
    "recurring_burden":      10,
    "spending_volatility":   15,
}


def compute_health_score(db: Session, user_id: int) -> dict:
    from app.models.models import Transaction, Budget, Account
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    today = date.today()
    last_90 = today - timedelta(days=90)

    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.transaction_date >= last_90)
        .all()
    )

    total_income = sum(float(t.amount) for t in txns if t.type == "income")
    total_expense = sum(float(t.amount) for t in txns if t.type == "expense")
    total_balance = sum(
        float(a.balance)
        for a in db.query(Account).filter(Account.user_id == user_id, Account.is_active == 1).all()
    )

    factors = []

    # 1. Savings rate (income - expense) / income
    if total_income > 0:
        savings_rate = (total_income - total_expense) / total_income
        score = min(20, round(savings_rate * 40))  # 50% savings = full score
        tip = None if savings_rate >= 0.2 else "Try to save at least 20% of your income."
    else:
        score, savings_rate, tip = 5, 0.0, "Add income transactions to improve this score."
    factors.append({
        "name": "Savings Rate",
        "score": max(0, score),
        "max_score": 20,
        "description": f"{savings_rate*100:.1f}% of income saved in last 90 days",
        "tip": tip,
    })

    # 2. Budget adherence — % of budgets not exceeded this month
    month_str = today.strftime("%Y-%m")
    budgets = db.query(Budget).filter(Budget.user_id == user_id, Budget.month == month_str).all()
    if budgets:
        within = 0
        for b in budgets:
            spent = sum(
                float(t.amount)
                for t in txns
                if t.category_id == b.category_id
                and t.type == "expense"
                and t.transaction_date.strftime("%Y-%m") == month_str
            )
            if spent <= float(b.amount):
                within += 1
        adherence = within / len(budgets)
        score = round(adherence * 20)
        tip = None if adherence >= 0.8 else "You exceeded budget in some categories this month."
    else:
        score, adherence, tip = 10, 0.5, "Set monthly budgets to track adherence."
    factors.append({
        "name": "Budget Adherence",
        "score": score,
        "max_score": 20,
        "description": f"{adherence*100:.0f}% of budgets within limit this month",
        "tip": tip,
    })

    # 3. Emergency fund (months of expenses covered by current balance)
    monthly_expense = total_expense / 3 if total_expense > 0 else 1
    months_covered = total_balance / monthly_expense if monthly_expense > 0 else 0
    score = min(20, round(months_covered / 6 * 20))  # 6 months = full score
    tip = None if months_covered >= 3 else f"Build emergency fund to cover 3+ months (currently {months_covered:.1f})."
    factors.append({
        "name": "Emergency Fund",
        "score": max(0, score),
        "max_score": 20,
        "description": f"Current balance covers {months_covered:.1f} months of expenses",
        "tip": tip,
    })

    # 4. Debt-to-income ratio
    loan_accounts = db.query(Account).filter(
        Account.user_id == user_id, Account.type == "loan", Account.is_active == 1
    ).all()
    total_debt = sum(abs(float(a.balance)) for a in loan_accounts)
    monthly_income = total_income / 3 if total_income > 0 else 1
    dti = total_debt / (monthly_income * 12) if monthly_income > 0 else 0
    score = max(0, round(15 - dti * 15))
    tip = None if dti < 0.4 else "High debt-to-income ratio. Focus on debt repayment."
    factors.append({
        "name": "Debt-to-Income",
        "score": score,
        "max_score": 15,
        "description": f"Debt is {dti*100:.0f}% of annual income",
        "tip": tip,
    })

    # 5. Recurring expense burden (% of income)
    from app.models.models import RecurringRule
    rules = db.query(RecurringRule).filter(RecurringRule.user_id == user_id).all()
    monthly_recurring = sum(
        float(r.expected_amount) * 30 / r.interval_days
        for r in rules
        if r.expected_amount and r.interval_days
    )
    burden = monthly_recurring / monthly_income if monthly_income > 0 else 0
    score = max(0, round(10 - burden * 10))
    tip = None if burden < 0.5 else "Recurring expenses are over 50% of income. Review subscriptions."
    factors.append({
        "name": "Recurring Burden",
        "score": score,
        "max_score": 10,
        "description": f"Recurring payments are {burden*100:.0f}% of monthly income",
        "tip": tip,
    })

    # 6. Spending volatility (std of weekly spend)
    weekly: dict[str, float] = {}
    for t in txns:
        if t.type == "expense":
            wk = t.transaction_date.strftime("%Y-W%W")
            weekly[wk] = weekly.get(wk, 0) + float(t.amount)
    if len(weekly) >= 2:
        vals = list(weekly.values())
        mean_w = sum(vals) / len(vals)
        std_w = (sum((v - mean_w) ** 2 for v in vals) / len(vals)) ** 0.5
        cv = std_w / mean_w if mean_w > 0 else 0
        score = max(0, round(15 - cv * 15))
        tip = None if cv < 0.5 else "High spending volatility. Try to smooth out expenses."
    else:
        score, cv, tip = 10, 0.0, "More transaction history needed for volatility analysis."
    factors.append({
        "name": "Spending Volatility",
        "score": score,
        "max_score": 15,
        "description": f"Weekly spending coefficient of variation: {cv:.2f}",
        "tip": tip,
    })

    total = sum(f["score"] for f in factors)
    grade = (
        "A" if total >= 80 else
        "B" if total >= 65 else
        "C" if total >= 50 else
        "D" if total >= 35 else "F"
    )

    return {
        "total_score": total,
        "grade": grade,
        "factors": factors,
        "disclaimer": (
            "This score is for informational purposes only. "
            "FinWise is not a SEBI-registered advisor. "
            "Forecasts and suggestions are estimates, not guarantees."
        ),
    }
