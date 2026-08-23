"""
Cash-flow forecasting service.
Rule-based model: current balance + known inflows/outflows + avg daily spend.
Structured so a time-series model (Prophet, ARIMA) can replace _forecast_daily_spend().
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy.orm import Session


LOW_BALANCE_THRESHOLD = Decimal("3000.00")


def _avg_daily_spend(db: Session, user_id: int, lookback_days: int = 60) -> Decimal:
    """Average daily expense over the last N days."""
    from app.models.models import Transaction

    cutoff = date.today() - timedelta(days=lookback_days)
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= cutoff,
        )
        .all()
    )
    if not txns:
        return Decimal("500.00")  # safe default
    total = sum(float(t.amount) for t in txns)
    return Decimal(str(round(total / lookback_days, 2)))


def _get_recurring_events(
    db: Session, user_id: int, start: date, end: date
) -> List[Tuple[date, Decimal, str]]:
    """Return (date, amount, label) for recurring rules falling in [start, end]."""
    from app.models.models import RecurringRule

    rules = db.query(RecurringRule).filter(RecurringRule.user_id == user_id).all()
    events = []
    for rule in rules:
        if not rule.next_expected_date or not rule.expected_amount:
            continue
        d = rule.next_expected_date
        while d <= end:
            if d >= start:
                label = f"Recurring: {rule.merchant_pattern or 'payment'}"
                events.append((d, Decimal(str(rule.expected_amount)), label))
            if rule.interval_days:
                d = d + timedelta(days=rule.interval_days)
            else:
                break
    return events


def build_forecast(db: Session, user_id: int, days: int = 30):
    """
    Returns a CashflowForecast-compatible dict.
    """
    from app.models.models import Account
    from app.models.user import User

    # Current total balance across active accounts
    accounts = (
        db.query(Account)
        .filter(Account.user_id == user_id, Account.is_active == 1)
        .all()
    )
    current_balance = sum(float(a.balance) for a in accounts)

    user = db.query(User).filter(User.id == user_id).first()
    avg_daily = _avg_daily_spend(db, user_id)

    today = date.today()
    end_date = today + timedelta(days=days)
    recurring_events = _get_recurring_events(db, user_id, today, end_date)

    # Build event map: date -> list of (amount_delta, label)
    event_map: dict[date, list] = {}
    for ev_date, amount, label in recurring_events:
        event_map.setdefault(ev_date, []).append((-float(amount), label))

    # Add salary if known
    if user and user.monthly_salary:
        salary_day = 1  # assume 1st of month
        d = today.replace(day=salary_day)
        if d < today:
            # next month
            if d.month == 12:
                d = d.replace(year=d.year + 1, month=1)
            else:
                d = d.replace(month=d.month + 1)
        if d <= end_date:
            event_map.setdefault(d, []).append(
                (float(user.monthly_salary), f"Salary: INR {user.monthly_salary}")
            )

    forecast = []
    balance = current_balance
    assumptions = [
        f"Average daily spending: INR {avg_daily}",
        f"Based on last 60 days of transactions",
        f"Recurring payments from {len(recurring_events)} detected rules",
    ]
    if user and user.monthly_salary:
        assumptions.append(f"Salary of INR {user.monthly_salary} expected on 1st")

    for i in range(days):
        d = today + timedelta(days=i)
        events_today = event_map.get(d, [])
        day_delta = -float(avg_daily)  # baseline daily spend

        event_labels = []
        for delta, label in events_today:
            day_delta += delta
            event_labels.append(label)

        balance += day_delta
        forecast.append({
            "date": d,
            "predicted_balance": Decimal(str(round(balance, 2))),
            "is_low_balance": balance < float(LOW_BALANCE_THRESHOLD),
            "events": event_labels,
        })

    return {
        "days": days,
        "forecast": forecast,
        "assumptions": assumptions,
        "current_balance": Decimal(str(round(current_balance, 2))),
    }
