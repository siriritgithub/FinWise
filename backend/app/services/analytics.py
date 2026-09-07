from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Account, Transaction


def get_dashboard_summary(db: Session, user_id: int):

    # =========================================================
    # DATE / MONTH SETUP
    # =========================================================

    today = date.today()

    # First day of current month
    this_month_start = today.replace(day=1)

    # First day of next month
    if this_month_start.month == 12:
        next_month_start = date(
            this_month_start.year + 1,
            1,
            1,
        )
    else:
        next_month_start = date(
            this_month_start.year,
            this_month_start.month + 1,
            1,
        )

    # First day of previous month
    if this_month_start.month == 1:
        last_month_start = date(
            this_month_start.year - 1,
            12,
            1,
        )
    else:
        last_month_start = date(
            this_month_start.year,
            this_month_start.month - 1,
            1,
        )

    # Convert dates to datetime boundaries
    current_month_start = datetime.combine(
        this_month_start,
        time.min,
    )

    next_month_start_datetime = datetime.combine(
        next_month_start,
        time.min,
    )

    previous_month_start = datetime.combine(
        last_month_start,
        time.min,
    )

    # =========================================================
    # DEBUG
    # =========================================================

    all_transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc())
        .all()
    )

    print("\n================ DASHBOARD DEBUG ================")
    print("USER ID:", user_id)
    print("TODAY:", today)
    print("CURRENT MONTH START:", current_month_start)
    print("NEXT MONTH START:", next_month_start_datetime)
    print("PREVIOUS MONTH START:", previous_month_start)
    print("TOTAL USER TRANSACTIONS:", len(all_transactions))

    for t in all_transactions:
        print(
            "TRANSACTION:",
            "id=", t.id,
            "| amount=", t.amount,
            "| type=", t.type,
            "| date=", t.transaction_date,
            "| user_id=", t.user_id,
        )

    print("==================================================\n")

    # =========================================================
    # 1. TOTAL BALANCE
    # =========================================================

    total_balance = (
        db.query(func.sum(Account.balance))
        .filter(
            Account.user_id == user_id,
            Account.is_active == 1,
        )
        .scalar()
        or Decimal("0.00")
    )

    # =========================================================
    # HELPER FUNCTION
    # =========================================================

    def get_sum(start_datetime, end_datetime, transaction_type):

        result = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.user_id == user_id,

                Transaction.type == transaction_type,

                # Include start
                Transaction.transaction_date >= start_datetime,

                # Exclude next period
                Transaction.transaction_date < end_datetime,
            )
            .scalar()
        )

        return result or Decimal("0.00")

    # =========================================================
    # 2. CURRENT MONTH INCOME
    # =========================================================

    this_month_income = get_sum(
        current_month_start,
        next_month_start_datetime,
        "income",
    )

    # =========================================================
    # 3. CURRENT MONTH EXPENSES
    # =========================================================

    this_month_expenses = get_sum(
        current_month_start,
        next_month_start_datetime,
        "expense",
    )

    # =========================================================
    # DEBUG CURRENT MONTH
    # =========================================================

    current_month_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= current_month_start,
            Transaction.transaction_date < next_month_start_datetime,
        )
        .order_by(Transaction.transaction_date.desc())
        .all()
    )

    print("\n========== CURRENT MONTH TRANSACTIONS ==========")
    print(
        "COUNT:",
        len(current_month_transactions)
    )

    for t in current_month_transactions:
        print(
            "CURRENT MONTH:",
            "id=", t.id,
            "| amount=", t.amount,
            "| type=", t.type,
            "| date=", t.transaction_date,
        )

    print(
        "CURRENT MONTH INCOME:",
        this_month_income
    )

    print(
        "CURRENT MONTH EXPENSES:",
        this_month_expenses
    )

    print("================================================\n")

    # =========================================================
    # 4. PREVIOUS MONTH
    # =========================================================

    last_month_income = get_sum(
        previous_month_start,
        current_month_start,
        "income",
    )

    last_month_expenses = get_sum(
        previous_month_start,
        current_month_start,
        "expense",
    )

    # =========================================================
    # 5. INCOME CHANGE
    # =========================================================

    if last_month_income:
        income_change = (
            (this_month_income - last_month_income)
            / last_month_income
            * 100
        )
    else:
        income_change = 0

    # =========================================================
    # 6. EXPENSE CHANGE
    # =========================================================

    if last_month_expenses:
        expense_change = (
            (this_month_expenses - last_month_expenses)
            / last_month_expenses
            * 100
        )
    else:
        expense_change = 0

    # =========================================================
    # 7. SAVINGS RATE
    # =========================================================

    if this_month_income:
        savings_rate = (
            (this_month_income - this_month_expenses)
            / this_month_income
            * 100
        )
    else:
        savings_rate = 0

    # =========================================================
    # 8. FINAL RESPONSE
    # =========================================================

    return {
        "total_balance": total_balance,

        "this_month_income": {
            "total": this_month_income,
            "change": income_change,
        },

        "this_month_expenses": {
            "total": this_month_expenses,
            "change": expense_change,
        },

        "savings_rate": savings_rate,
    }