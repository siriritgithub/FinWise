"""
Cash-flow forecasting service.

Rule-based forecasting model:
- Current account balance
- Recent spending behavior
- Weighted recent spending
- Recurring expenses
- Expected salary/income
- Projected ending balance
- Lowest projected balance
- Upcoming cash-flow events
- Balance safety status

The response remains compatible with the existing
CashflowForecast frontend interface.
"""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple

from sqlalchemy.orm import Session


# =========================================================
# CONFIGURATION
# =========================================================

LOW_BALANCE_THRESHOLD = Decimal("3000.00")
CAUTION_THRESHOLD = Decimal("6000.00")

DEFAULT_DAILY_SPEND = Decimal("500.00")

LOOKBACK_DAYS = 60
RECENT_DAYS = 30

# Minimum number of days of transaction history before
# we consider the calculated daily spending reliable.
MIN_HISTORY_DAYS = 7


# =========================================================
# HELPER
# =========================================================

def _to_date(value):
    """
    Safely convert date/datetime values to date.
    """

    if value is None:
        return None

    if hasattr(value, "date"):
        return value.date()

    return value


def _money(value: Decimal) -> Decimal:
    """
    Safely round money values to two decimal places.
    """

    return Decimal(str(value or 0)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


# =========================================================
# RECENT SPENDING
# =========================================================

def _avg_daily_spend(
    db: Session,
    user_id: int,
    lookback_days: int = LOOKBACK_DAYS,
) -> Decimal:
    """
    Calculate a realistic weighted average daily expense.

    Strategy:

    1. Look at the last 60 days.
    2. Separate the most recent 30 days from the older 30 days.
    3. Calculate spending per ACTIVE spending day.
    4. Give recent spending 70% weight.
    5. Give older spending 30% weight.
    6. If there is insufficient history, use a reasonable fallback.

    This avoids producing an artificially tiny daily amount simply
    because the user has only a few transactions.
    """

    from app.models.models import Transaction

    today = date.today()

    cutoff = today - timedelta(days=lookback_days)
    recent_cutoff = today - timedelta(days=RECENT_DAYS)

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= cutoff,
        )
        .order_by(
            Transaction.transaction_date.desc()
        )
        .all()
    )

    if not transactions:
        return DEFAULT_DAILY_SPEND

    recent_total = Decimal("0.00")
    older_total = Decimal("0.00")

    recent_dates = set()
    older_dates = set()

    for transaction in transactions:

        amount = Decimal(
            str(transaction.amount or 0)
        )

        if amount <= 0:
            continue

        transaction_date = _to_date(
            transaction.transaction_date
        )

        if not transaction_date:
            continue

        if transaction_date >= recent_cutoff:

            recent_total += amount
            recent_dates.add(transaction_date)

        else:

            older_total += amount
            older_dates.add(transaction_date)

    # =====================================================
    # CALCULATE ACTIVE SPENDING DAYS
    # =====================================================

    recent_active_days = len(recent_dates)
    older_active_days = len(older_dates)

    # We still need to avoid overestimating spending when
    # there are only one or two transactions.
    #
    # Therefore we use a hybrid approach:
    #
    # - If enough transaction history exists, use calendar days.
    # - If spending is concentrated on a few days, use a
    #   capped active-day estimate.

    recent_calendar_days = min(
        RECENT_DAYS,
        max(
            1,
            (today - recent_cutoff).days + 1
        ),
    )

    older_calendar_days = max(
        1,
        lookback_days - RECENT_DAYS,
    )

    # =====================================================
    # RECENT DAILY SPENDING
    # =====================================================

    if recent_total > 0:

        if recent_active_days >= MIN_HISTORY_DAYS:
            recent_daily = (
                recent_total
                / Decimal(str(recent_calendar_days))
            )

        else:
            # With limited recent data, spread the amount over
            # the full recent period instead of dividing by only
            # the transaction days.
            recent_daily = (
                recent_total
                / Decimal(str(recent_calendar_days))
            )

    else:
        recent_daily = Decimal("0.00")

    # =====================================================
    # OLDER DAILY SPENDING
    # =====================================================

    if older_total > 0:

        if older_active_days >= MIN_HISTORY_DAYS:
            older_daily = (
                older_total
                / Decimal(str(older_calendar_days))
            )

        else:
            older_daily = (
                older_total
                / Decimal(str(older_calendar_days))
            )

    else:
        older_daily = Decimal("0.00")

    # =====================================================
    # WEIGHT RECENT SPENDING MORE HEAVILY
    # =====================================================

    if recent_total > 0 and older_total > 0:

        weighted_average = (
            recent_daily * Decimal("0.70")
            + older_daily * Decimal("0.30")
        )

    elif recent_total > 0:

        weighted_average = recent_daily

    elif older_total > 0:

        weighted_average = older_daily

    else:

        return DEFAULT_DAILY_SPEND

    # =====================================================
    # SANITY CHECK
    # =====================================================

    if weighted_average <= Decimal("0"):
        return DEFAULT_DAILY_SPEND

    # Don't allow an absurdly tiny value when there is
    # meaningful historical spending.
    #
    # ₹50/day is used as a conservative lower bound.
    minimum_daily_spend = Decimal("50.00")

    if weighted_average < minimum_daily_spend:
        weighted_average = minimum_daily_spend

    return _money(weighted_average)


# =========================================================
# RECURRING EVENTS
# =========================================================

def _get_recurring_events(
    db: Session,
    user_id: int,
    start: date,
    end: date,
) -> List[Tuple[date, Decimal, str]]:
    """
    Return recurring expense events falling inside [start, end].

    Returns:

        (date, amount, label)
    """

    from app.models.models import RecurringRule

    rules = (
        db.query(RecurringRule)
        .filter(
            RecurringRule.user_id == user_id
        )
        .all()
    )

    events = []

    for rule in rules:

        if not rule.next_expected_date:
            continue

        if not rule.expected_amount:
            continue

        event_date = _to_date(
            rule.next_expected_date
        )

        if not event_date:
            continue

        amount = Decimal(
            str(rule.expected_amount)
        )

        if amount <= 0:
            continue

        label = (
            f"Recurring: "
            f"{rule.merchant_pattern or 'payment'}"
        )

        while event_date <= end:

            if event_date >= start:

                events.append(
                    (
                        event_date,
                        amount,
                        label,
                    )
                )

            if rule.interval_days:

                event_date = (
                    event_date
                    + timedelta(
                        days=rule.interval_days
                    )
                )

            else:
                break

    return events


# =========================================================
# SALARY EVENTS
# =========================================================

def _get_salary_events(
    user,
    today: date,
    end_date: date,
):
    """
    Generate expected salary events.

    Current application assumption:
    salary arrives on the 1st of each month.
    """

    events = []

    if not user:
        return events

    if not user.monthly_salary:
        return events

    salary_amount = Decimal(
        str(user.monthly_salary)
    )

    if salary_amount <= 0:
        return events

    salary_date = today.replace(day=1)

    # If this month's salary date has passed,
    # start with next month.
    if salary_date < today:

        if salary_date.month == 12:

            salary_date = salary_date.replace(
                year=salary_date.year + 1,
                month=1,
                day=1,
            )

        else:

            salary_date = salary_date.replace(
                month=salary_date.month + 1,
                day=1,
            )

    # Add every salary occurrence inside forecast.
    while salary_date <= end_date:

        events.append(
            (
                salary_date,
                salary_amount,
                f"Salary: INR {salary_amount}",
            )
        )

        if salary_date.month == 12:

            salary_date = salary_date.replace(
                year=salary_date.year + 1,
                month=1,
                day=1,
            )

        else:

            salary_date = salary_date.replace(
                month=salary_date.month + 1,
                day=1,
            )

    return events


# =========================================================
# BUILD FORECAST
# =========================================================

def build_forecast(
    db: Session,
    user_id: int,
    days: int = 30,
):
    """
    Build cash-flow forecast.

    Forecast logic:

        Current Balance
        - Estimated Daily Spending
        - Recurring Expenses
        + Expected Salary

    Also returns:

        expected_income
        expected_expenses
        projected_ending_balance
        lowest_projected_balance
        lowest_balance_date
        upcoming_events
        status
        net_cash_flow
    """

    from app.models.models import Account
    from app.models.user import User

    # =====================================================
    # VALIDATE DAYS
    # =====================================================

    if days < 1:
        days = 1

    if days > 365:
        days = 365

    # =====================================================
    # CURRENT BALANCE
    # =====================================================

    accounts = (
        db.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.is_active == 1,
        )
        .all()
    )

    current_balance = sum(
        (
            Decimal(
                str(account.balance or 0)
            )
            for account in accounts
        ),
        Decimal("0.00"),
    )

    current_balance = _money(
        current_balance
    )

    # =====================================================
    # USER
    # =====================================================

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    # =====================================================
    # DAILY SPENDING
    # =====================================================

    avg_daily_spend = _avg_daily_spend(
        db,
        user_id,
        LOOKBACK_DAYS,
    )

    # =====================================================
    # FORECAST DATES
    # =====================================================

    today = date.today()

    end_date = (
        today
        + timedelta(days=days - 1)
    )

    # =====================================================
    # RECURRING EXPENSES
    # =====================================================

    recurring_events = _get_recurring_events(
        db,
        user_id,
        today,
        end_date,
    )

    # =====================================================
    # SALARY EVENTS
    # =====================================================

    salary_events = _get_salary_events(
        user,
        today,
        end_date,
    )

    # =====================================================
    # EVENT MAP
    #
    # date -> list of events
    #
    # Each event:
    #
    # {
    #     amount: Decimal,
    #     type: income/expense,
    #     label: str
    # }
    # =====================================================

    event_map = {}

    # Recurring expenses
    for (
        event_date,
        amount,
        label,
    ) in recurring_events:

        event_map.setdefault(
            event_date,
            [],
        ).append(
            {
                "amount": amount,
                "type": "expense",
                "label": label,
            }
        )

    # Salary
    for (
        event_date,
        amount,
        label,
    ) in salary_events:

        event_map.setdefault(
            event_date,
            [],
        ).append(
            {
                "amount": amount,
                "type": "income",
                "label": label,
            }
        )

    # =====================================================
    # FORECAST TOTALS
    # =====================================================

    expected_income = Decimal("0.00")
    expected_expenses = Decimal("0.00")

    # Baseline daily spending
    baseline_expenses = (
        avg_daily_spend
        * Decimal(str(days))
    )

    expected_expenses += baseline_expenses

    # Recurring expenses
    for (
        event_date,
        amount,
        label,
    ) in recurring_events:

        expected_expenses += amount

    # Salary
    for (
        event_date,
        amount,
        label,
    ) in salary_events:

        expected_income += amount

    expected_income = _money(
        expected_income
    )

    expected_expenses = _money(
        expected_expenses
    )

    # =====================================================
    # FORECAST
    # =====================================================

    forecast = []

    balance = current_balance

    lowest_balance = current_balance
    lowest_balance_date = today

    upcoming_events = []

    for i in range(days):

        forecast_date = (
            today
            + timedelta(days=i)
        )

        # =================================================
        # NORMAL DAILY SPENDING
        # =================================================

        day_delta = -avg_daily_spend

        events_today = event_map.get(
            forecast_date,
            [],
        )

        event_labels = []
        event_details = []

        # =================================================
        # SCHEDULED EVENTS
        # =================================================

        for event in events_today:

            amount = Decimal(
                str(event["amount"])
            )

            event_type = event["type"]
            label = event["label"]

            if event_type == "income":

                day_delta += amount

            else:

                day_delta -= amount

            event_labels.append(
                label
            )

            event_details.append(
                {
                    "type": event_type,
                    "amount": _money(amount),
                    "label": label,
                }
            )

            upcoming_events.append(
                {
                    "date": forecast_date,
                    "type": event_type,
                    "amount": _money(amount),
                    "label": label,
                }
            )

        # =================================================
        # UPDATE BALANCE
        # =================================================

        balance += day_delta

        balance = _money(
            balance
        )

        # =================================================
        # TRACK LOWEST BALANCE
        # =================================================

        if balance < lowest_balance:

            lowest_balance = balance

            lowest_balance_date = (
                forecast_date
            )

        # =================================================
        # SAFETY STATUS
        # =================================================

        if balance < LOW_BALANCE_THRESHOLD:

            status = "critical"

        elif balance < CAUTION_THRESHOLD:

            status = "caution"

        else:

            status = "safe"

        # =================================================
        # FORECAST ROW
        # =================================================

        forecast.append(
            {
                "date": forecast_date,

                # IMPORTANT:
                # Keep this name because the frontend
                # expects predicted_balance.
                "predicted_balance": balance,

                "is_low_balance": (
                    balance
                    < LOW_BALANCE_THRESHOLD
                ),

                "status": status,

                "events": event_labels,

                "event_details": event_details,
            }
        )

    # =====================================================
    # PROJECTED ENDING BALANCE
    # =====================================================

    projected_ending_balance = _money(
        balance
    )

    # =====================================================
    # NET CASH FLOW
    # =====================================================

    net_cash_flow = _money(
        expected_income
        - expected_expenses
    )

    # =====================================================
    # OVERALL STATUS
    # =====================================================

    if lowest_balance < LOW_BALANCE_THRESHOLD:

        overall_status = "critical"

    elif lowest_balance < CAUTION_THRESHOLD:

        overall_status = "caution"

    else:

        overall_status = "safe"

    # =====================================================
    # ASSUMPTIONS
    # =====================================================

    assumptions = [
        (
            f"Weighted average daily spending: "
            f"INR {avg_daily_spend}"
        ),
        (
            "Recent 30-day spending weighted "
            "more heavily than older spending"
        ),
        (
            f"Based on approximately "
            f"{LOOKBACK_DAYS} days of transactions"
        ),
        (
            f"{len(recurring_events)} recurring "
            f"payment event(s) detected"
        ),
    ]

    # Salary assumption
    if user and user.monthly_salary:

        assumptions.append(
            (
                f"Salary of INR "
                f"{user.monthly_salary} "
                f"expected on the 1st"
            )
        )

    # Lowest balance assumption
    if lowest_balance < LOW_BALANCE_THRESHOLD:

        assumptions.append(
            (
                f"Lowest projected balance: "
                f"INR "
                f"{lowest_balance} "
                f"on {lowest_balance_date}"
            )
        )

    elif lowest_balance < CAUTION_THRESHOLD:

        assumptions.append(
            (
                "Projected balance enters the "
                "caution range below INR 6,000"
            )
        )

    else:

        assumptions.append(
            (
                "Projected balance remains above "
                "the INR 3,000 safety threshold"
            )
        )

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {
        "days": days,

        "forecast": forecast,

        "assumptions": assumptions,

        "current_balance": current_balance,

        "expected_income": expected_income,

        "expected_expenses": expected_expenses,

        "net_cash_flow": net_cash_flow,

        "projected_ending_balance": (
            projected_ending_balance
        ),

        "lowest_projected_balance": (
            _money(lowest_balance)
        ),

        "lowest_balance_date": (
            lowest_balance_date
        ),

        "overall_status": overall_status,

        "upcoming_events": upcoming_events,
    }