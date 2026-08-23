from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import Account, Transaction


def get_dashboard_summary(db: Session, user_id: int):
    today = date.today()
    this_month_start = today.replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    # 1. Total Balance
    total_balance = db.query(func.sum(Account.balance)).filter(
        Account.user_id == user_id, Account.is_active == True
    ).scalar() or Decimal(0)

    # 2. Income and Expenses
    def get_sum(start_date, end_date, type):
        return db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == type,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        ).scalar() or Decimal(0)

    this_month_income = get_sum(this_month_start, today, "income")
    this_month_expenses = get_sum(this_month_start, today, "expense")
    last_month_income = get_sum(last_month_start, last_month_end, "income")
    last_month_expenses = get_sum(last_month_start, last_month_end, "expense")

    # 3. Calculate changes and savings rate
    income_change = ((this_month_income - last_month_income) / last_month_income * 100) if last_month_income else 0
    expense_change = ((this_month_expenses - last_month_expenses) / last_month_expenses * 100) if last_month_expenses else 0
    savings_rate = ((this_month_income - this_month_expenses) / this_month_income * 100) if this_month_income else 0

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