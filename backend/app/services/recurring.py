"""
Recurring payment detection.
Groups transactions by (user, merchant_pattern) and looks for
regular intervals and similar amounts.
"""
from datetime import date, timedelta
from collections import defaultdict
from typing import List
from sqlalchemy.orm import Session
import re


def _normalize_merchant(merchant: str) -> str:
    """Strip trailing numbers/IDs to get a stable pattern."""
    if not merchant:
        return ""
    return re.sub(r"[\d\-_/]+$", "", merchant.strip().lower()).strip()


def detect_recurring(db: Session, user_id: int) -> int:
    """
    Scan past 180 days of transactions, detect recurring patterns,
    and upsert recurring_rules. Returns count of rules created/updated.
    """
    from app.models.models import Transaction, RecurringRule, Category

    cutoff = date.today() - timedelta(days=180)
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.transaction_date >= cutoff,
        )
        .order_by(Transaction.transaction_date)
        .all()
    )

    # Group by normalized merchant
    groups: dict[str, list] = defaultdict(list)
    for t in txns:
        key = _normalize_merchant(t.merchant or t.description or "")
        if key:
            groups[key].append(t)

    upserted = 0
    for pattern, group in groups.items():
        if len(group) < 2:
            continue

        # Sort by date and compute intervals
        group.sort(key=lambda t: t.transaction_date)
        dates = [t.transaction_date.date() for t in group]
        intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]

        if not intervals:
            continue

        avg_interval = sum(intervals) / len(intervals)
        # Only flag if interval is reasonably regular (std < 10 days)
        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        if variance ** 0.5 > 10:
            continue

        # Check amount similarity (within 20%)
        amounts = [float(t.amount) for t in group]
        avg_amount = sum(amounts) / len(amounts)
        if any(abs(a - avg_amount) / avg_amount > 0.20 for a in amounts):
            continue

        last_date = dates[-1]
        next_date = last_date + timedelta(days=round(avg_interval))
        is_sub = int(avg_interval <= 35)  # monthly-ish = subscription

        # Upsert
        rule = (
            db.query(RecurringRule)
            .filter(
                RecurringRule.user_id == user_id,
                RecurringRule.merchant_pattern == pattern,
            )
            .first()
        )
        if rule:
            rule.expected_amount = avg_amount
            rule.interval_days = round(avg_interval)
            rule.next_expected_date = next_date
            rule.last_seen_date = last_date
            rule.is_subscription = is_sub
        else:
            cat_id = group[-1].category_id
            rule = RecurringRule(
                user_id=user_id,
                merchant_pattern=pattern,
                category_id=cat_id,
                expected_amount=avg_amount,
                interval_days=round(avg_interval),
                next_expected_date=next_date,
                is_subscription=is_sub,
                last_seen_date=last_date,
            )
            db.add(rule)
        upserted += 1

    db.commit()
    return upserted
