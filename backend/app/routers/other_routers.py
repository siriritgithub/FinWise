"""
Remaining routers: categories, budgets, recurring, goals, receipts, analytics, chat.
All in one file for brevity; split into separate files if the project grows.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import os, shutil, uuid
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.models import (
    Category, Budget, RecurringRule, SavingsGoal, Receipt, Transaction, Account
)
from app.schemas.schemas import (
    CategoryCreate, CategoryOut,
    BudgetCreate, BudgetOut, BudgetSummaryItem,
    RecurringRuleOut, RecurringRuleUpdate,
    GoalCreate, GoalUpdate, GoalOut, GoalPlan, DashboardSummary,
    ReceiptOut, ReceiptExtracted,
    ChatRequest, ChatResponse,
    CashflowForecast, HealthScore, AnomalyOut, SpendingTrend,
)

settings = get_settings()

# ── Categories ────────────────────────────────────────────────────────────────
categories_router = APIRouter(prefix="/categories", tags=["categories"])


@categories_router.get("", response_model=List[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == 1),
        Category.is_active == 1,
    ).all()


@categories_router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    body: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = Category(user_id=current_user.id, **body.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@categories_router.put("/{cat_id}", response_model=CategoryOut)
def update_category(
    cat_id: int,
    body: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = db.query(Category).filter(
        Category.id == cat_id, Category.user_id == current_user.id
    ).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    cat.name = body.name
    cat.parent_category_id = body.parent_category_id
    db.commit()
    db.refresh(cat)
    return cat


@categories_router.delete("/{cat_id}", status_code=204)
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = db.query(Category).filter(
        Category.id == cat_id, Category.user_id == current_user.id, Category.is_system == 0
    ).first()
    if not cat:
        raise HTTPException(404, "Category not found or is a system category")
    cat.is_active = 0
    db.commit()


# ── Budgets ───────────────────────────────────────────────────────────────────
budgets_router = APIRouter(prefix="/budgets", tags=["budgets"])


@budgets_router.get("", response_model=List[BudgetOut])
def list_budgets(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Budget).filter(Budget.user_id == current_user.id)
    if month:
        q = q.filter(Budget.month == month)
    return q.all()


@budgets_router.post("", response_model=BudgetOut, status_code=201)
def create_budget(
    body: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = Budget(user_id=current_user.id, **body.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@budgets_router.put("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    body: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id, Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(404, "Budget not found")
    for field, value in body.model_dump().items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return budget


@budgets_router.delete("/{budget_id}", status_code=204)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id, Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(404, "Budget not found")
    db.delete(budget)
    db.commit()


@budgets_router.get("/summary")
def budget_summary(
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id, Budget.month == month
    ).all()

    result = []
    for b in budgets:
        spent = db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == b.category_id,
            Transaction.type == "expense",
            Transaction.transaction_date.like(f"{month}%"),
        ).all()
        spent_total = sum(float(t.amount) for t in spent)
        cat_name = b.category.name if b.category else "Total"
        result.append({
            "category_id": b.category_id,
            "category_name": cat_name,
            "budget_amount": float(b.amount),
            "spent_amount": spent_total,
            "remaining": float(b.amount) - spent_total,
            "pct_used": round(spent_total / float(b.amount) * 100, 1) if b.amount else 0,
        })
    return result


# ── Recurring ─────────────────────────────────────────────────────────────────
recurring_router = APIRouter(prefix="/recurring", tags=["recurring"])


@recurring_router.get("/rules", response_model=List[RecurringRuleOut])
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(RecurringRule).filter(RecurringRule.user_id == current_user.id).all()


@recurring_router.post("/detect")
def detect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.recurring import detect_recurring
    count = detect_recurring(db, current_user.id)
    return {"rules_created_or_updated": count}


@recurring_router.put("/rules/{rule_id}", response_model=RecurringRuleOut)
def update_rule(
    rule_id: int,
    body: RecurringRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(RecurringRule).filter(
        RecurringRule.id == rule_id, RecurringRule.user_id == current_user.id
    ).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@recurring_router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(RecurringRule).filter(
        RecurringRule.id == rule_id, RecurringRule.user_id == current_user.id
    ).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    db.delete(rule)
    db.commit()


@recurring_router.get("/subscriptions")
def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rules = db.query(RecurringRule).filter(
        RecurringRule.user_id == current_user.id,
        RecurringRule.is_subscription == 1,
    ).all()
    result = []
    for r in rules:
        monthly = (
            float(r.expected_amount) * 30 / r.interval_days
            if r.expected_amount and r.interval_days else 0
        )
        result.append({
            "id": r.id,
            "merchant": r.merchant_pattern,
            "expected_amount": float(r.expected_amount) if r.expected_amount else 0,
            "interval_days": r.interval_days,
            "next_expected_date": r.next_expected_date,
            "last_seen_date": r.last_seen_date,
            "monthly_cost": round(monthly, 2),
            "annual_cost": round(monthly * 12, 2),
        })
    return result


# ── Goals ─────────────────────────────────────────────────────────────────────
goals_router = APIRouter(prefix="/goals", tags=["goals"])


@goals_router.get("", response_model=List[GoalOut])
def list_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(SavingsGoal).filter(SavingsGoal.user_id == current_user.id).all()


@goals_router.post("", response_model=GoalOut, status_code=201)
def create_goal(
    body: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = SavingsGoal(user_id=current_user.id, **body.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@goals_router.put("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: int,
    body: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


@goals_router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    db.delete(goal)
    db.commit()


@goals_router.get("/{goal_id}/plan")
def goal_plan(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date, datetime, timedelta
    from dateutil.relativedelta import relativedelta

    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(404, "Goal not found")

    remaining = float(goal.target_amount) - float(goal.current_amount)
    months_remaining = None
    required_monthly = None

    if goal.deadline:
        today = date.today()
        delta = relativedelta(goal.deadline, today)
        months_remaining = delta.years * 12 + delta.months
        if months_remaining > 0:
            required_monthly = round(remaining / months_remaining, 2)

    # Estimate surplus from last 30 days
    from app.models.models import Transaction
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=30)
    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_date >= cutoff,
    ).all()
    income_30 = sum(float(t.amount) for t in txns if t.type == "income")
    expense_30 = sum(float(t.amount) for t in txns if t.type == "expense")
    surplus = income_30 - expense_30

    suggestions = []
    if required_monthly and surplus < required_monthly:
        gap = required_monthly - surplus
        suggestions.append(f"You need INR {required_monthly:,.0f}/month but your current surplus is INR {surplus:,.0f}.")
        suggestions.append(f"Reduce discretionary spending by INR {gap:,.0f} to meet this goal.")
        suggestions.append("Consider reducing Food budget by INR 1,500 and Shopping by INR 2,000.")

    return {
        "goal": goal,
        "months_remaining": months_remaining,
        "required_monthly": required_monthly,
        "current_surplus": round(surplus, 2),
        "is_achievable": required_monthly is None or surplus >= required_monthly,
        "tradeoff_suggestions": suggestions,
    }


# ── Receipts ──────────────────────────────────────────────────────────────────
receipts_router = APIRouter(prefix="/receipts", tags=["receipts"])


@receipts_router.post("/upload", status_code=201)
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.ocr import process_receipt, validate_file

    # Validate file type BEFORE saving to disk
    validate_file(file.filename or "", file.content_type or "")

    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # process_receipt raises HTTPException with clear message on failure
    extracted = process_receipt(file_path)

    receipt = Receipt(
        user_id=current_user.id,
        file_path=file_path,
        merchant=extracted.get("merchant"),
        total_amount=extracted.get("total_amount"),
        receipt_date=extracted.get("receipt_date"),
        tax_amount=extracted.get("tax_amount"),
        ocr_raw_text=extracted.get("raw_text"),
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return {
        "id": receipt.id,
        "transaction_id": receipt.transaction_id,
        "file_path": receipt.file_path,
        "merchant": receipt.merchant,
        "total_amount": receipt.total_amount,
        "receipt_date": receipt.receipt_date,
        "tax_amount": receipt.tax_amount,
        "ocr_raw_text": receipt.ocr_raw_text,
        "created_at": receipt.created_at,
    }


@receipts_router.get("", response_model=List[ReceiptOut])
def list_receipts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Receipt).filter(Receipt.user_id == current_user.id).all()


@receipts_router.get("/{receipt_id}", response_model=ReceiptOut)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(Receipt).filter(
        Receipt.id == receipt_id, Receipt.user_id == current_user.id
    ).first()
    if not r:
        raise HTTPException(404, "Receipt not found")
    return r


@receipts_router.delete("/{receipt_id}", status_code=204)
def delete_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(Receipt).filter(
        Receipt.id == receipt_id, Receipt.user_id == current_user.id
    ).first()
    if not r:
        raise HTTPException(404, "Receipt not found")
    db.delete(r)
    db.commit()


@receipts_router.post("/{receipt_id}/link-transaction")
def link_transaction(
    receipt_id: int,
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(Receipt).filter(
        Receipt.id == receipt_id, Receipt.user_id == current_user.id
    ).first()
    if not r:
        raise HTTPException(404, "Receipt not found")
    r.transaction_id = transaction_id
    db.commit()
    return {"message": "Linked"}


# ── Analytics ─────────────────────────────────────────────────────────────────
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/dashboard-summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Provides key metrics for the main user dashboard."""
    from app.services import analytics as analytics_service
    return analytics_service.get_dashboard_summary(db, current_user.id)


@analytics_router.get("/cashflow")
def cashflow(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.forecasting import build_forecast
    return build_forecast(db, current_user.id, days)


@analytics_router.get("/health-score")
def health_score(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.health_score import compute_health_score
    return compute_health_score(db, current_user.id)


@analytics_router.get("/anomalies")
def anomalies(
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.anomaly import detect_anomalies
    return detect_anomalies(db, current_user.id, days)


@analytics_router.get("/spending-trends")
def spending_trends(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import timedelta
    from app.models.models import Transaction, Category

    cutoff = date.today() - timedelta(days=months * 30)
    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        Transaction.transaction_date >= cutoff,
    ).all()

    # Group by month + category
    data: dict = {}
    for t in txns:
        month = t.transaction_date.strftime("%Y-%m")
        cat_name = t.category.name if t.category else "Other"
        key = (month, cat_name)
        data[key] = data.get(key, 0) + float(t.amount)

    return [
        {"month": k[0], "category_name": k[1], "total_spent": round(v, 2)}
        for k, v in sorted(data.items())
    ]


# ── Portfolio intelligence ────────────────────────────────────────────────────
@analytics_router.get("/net-worth")
def net_worth(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.user_id == current_user.id, Account.is_active == 1).all()
    assets = sum(float(a.balance) for a in accounts if a.type not in ("loan", "credit_card"))
    liabilities = sum(abs(float(a.balance)) for a in accounts if a.type in ("loan", "credit_card"))
    return {"assets": round(assets,2), "liabilities": round(liabilities,2), "net_worth": round(assets-liabilities,2)}

@analytics_router.get("/emergency-fund")
def emergency_fund(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=90)
    tx = db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.type == "expense", Transaction.transaction_date >= cutoff).all()
    monthly = sum(float(t.amount) for t in tx) / 3 if tx else 0
    balances = sum(float(a.balance) for a in db.query(Account).filter(Account.user_id == current_user.id, Account.is_active == 1).all())
    months = balances / monthly if monthly else 0
    return {"monthly_essential_estimate": round(monthly,2), "available_balance": round(balances,2), "months_covered": round(months,2), "target_3_months": round(monthly*3,2), "target_6_months": round(monthly*6,2)}

@analytics_router.get("/budget-recommendations")
def budget_recommendations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=90)
    tx = db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.type == "expense", Transaction.transaction_date >= cutoff).all()
    groups = {}
    for t in tx:
        name = t.category.name if t.category else "Other"
        groups[name] = groups.get(name, 0) + float(t.amount)
    return [{"category":name,"average_monthly":round(total/3,2),"recommended_budget":round(total/3*1.10,2),"buffer":round(total/3*.10,2),"reason":"90-day average plus a 10% variability buffer"} for name,total in sorted(groups.items(), key=lambda x:-x[1])[:12]]

@analytics_router.get("/what-if")
def what_if(reduction: float = Query(..., gt=0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start=date.today().replace(day=1)
    tx=db.query(Transaction).filter(Transaction.user_id==current_user.id,Transaction.transaction_date>=start).all()
    income=sum(float(t.amount) for t in tx if t.type=="income"); expense=sum(float(t.amount) for t in tx if t.type=="expense")
    days=max(date.today().day,1); monthly=expense/days*30
    current=max(0,income-monthly); projected=max(0,income-max(0,monthly-reduction))
    return {"reduction":reduction,"current_monthly_savings":round(current,2),"projected_monthly_savings":round(projected,2),"annual_improvement":round(reduction*12,2)}

@analytics_router.get("/monthly-report")
def monthly_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today=date.today(); start=today.replace(day=1); prev_end=start-timedelta(days=1); prev_start=prev_end.replace(day=1)
    def totals(a,b):
        tx=db.query(Transaction).filter(Transaction.user_id==current_user.id,Transaction.transaction_date>=a,Transaction.transaction_date<datetime.combine(b+timedelta(days=1),datetime.min.time())).all()
        return sum(float(t.amount) for t in tx if t.type=="income"),sum(float(t.amount) for t in tx if t.type=="expense")
    inc,exp=totals(start,today); pinc,pexp=totals(prev_start,prev_end)
    return {"month":today.strftime("%Y-%m"),"income":round(inc,2),"expenses":round(exp,2),"savings":round(inc-exp,2),"savings_rate":round((inc-exp)/inc*100,2) if inc else 0,"expense_change_pct":round((exp-pexp)/pexp*100,2) if pexp else 0,"income_change_pct":round((inc-pinc)/pinc*100,2) if pinc else 0}

# ── Chat ──────────────────────────────────────────────────────────────────────
chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("")
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = [m.model_dump() for m in body.history]
    try:
        from app.services.llm import answer_with_llm
        result = answer_with_llm(db, current_user.id, body.message, history)
        if result is not None:
            return result
    except Exception as exc:
        # Keep the core assistant available if the LLM is disabled, unavailable,
        # or the API key/model is temporarily unavailable.
        fallback = None
        try:
            fallback = __import__('app.services.chat', fromlist=['answer']).answer(db, current_user.id, body.message, history)
        except Exception:
            fallback = {"answer_text": f"The AI service is temporarily unavailable. FinWise local assistant is also unavailable: {exc}", "data_summary": {}, "suggestions": []}
        if isinstance(fallback, dict):
            fallback.setdefault("data_summary", {})
            fallback["data_summary"]["llm_fallback"] = True
            return fallback
    from app.services.chat import answer
    return answer(db, current_user.id, body.message, history)
