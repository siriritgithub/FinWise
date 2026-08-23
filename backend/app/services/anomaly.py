"""
Anomaly detection service.
Uses statistical rules (z-score, duplicate check, category spike).
Returns structured anomaly records — never marks as confirmed fraud.
"""
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
from typing import List
from sqlalchemy.orm import Session


def detect_anomalies(db: Session, user_id: int, days: int = 90) -> List[dict]:
    """
    Scan recent transactions and return a list of anomaly dicts.
    Each dict matches the AnomalyOut schema.
    """
    from app.models.models import Transaction, Category

    cutoff = date.today() - timedelta(days=days)
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= cutoff,
            Transaction.type == "expense",
        )
        .order_by(Transaction.transaction_date)
        .all()
    )

    # Build per-category stats from the first 60 days (baseline)
    baseline_cutoff = date.today() - timedelta(days=days)
    cat_amounts: dict[int, list] = defaultdict(list)
    merchant_amounts: dict[str, list] = defaultdict(list)

    for t in txns:
        if t.category_id:
            cat_amounts[t.category_id].append(float(t.amount))
        if t.merchant:
            merchant_amounts[t.merchant.lower()].append(float(t.amount))

    def z_score(value: float, values: list) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        std = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
        return (value - mean) / std if std > 0 else 0.0

    anomalies = []
    seen: set = set()  # for duplicate detection

    for t in txns:
        amount = float(t.amount)
        cat_name = t.category.name if t.category else "Unknown"

        # 1. Amount z-score vs category history
        if t.category_id and len(cat_amounts[t.category_id]) >= 3:
            z = z_score(amount, cat_amounts[t.category_id])
            if z > 2.5:
                ratio = amount / (sum(cat_amounts[t.category_id]) / len(cat_amounts[t.category_id]))
                anomalies.append({
                    "transaction_id": t.id,
                    "transaction_date": t.transaction_date,
                    "merchant": t.merchant,
                    "amount": Decimal(str(amount)),
                    "category_name": cat_name,
                    "anomaly_type": "high_amount",
                    "severity": "high" if z > 3.5 else "medium",
                    "message": (
                        f"This INR {amount:,.0f} {cat_name} transaction is "
                        f"{ratio:.1f}x your average {cat_name} expense."
                    ),
                })

        # 2. New merchant with high amount (never seen before in history)
        if t.merchant:
            key = t.merchant.lower()
            if len(merchant_amounts[key]) == 1 and amount > 2000:
                anomalies.append({
                    "transaction_id": t.id,
                    "transaction_date": t.transaction_date,
                    "merchant": t.merchant,
                    "amount": Decimal(str(amount)),
                    "category_name": cat_name,
                    "anomaly_type": "new_merchant",
                    "severity": "low",
                    "message": (
                        f"First transaction with '{t.merchant}' for INR {amount:,.0f}. "
                        "Please verify this is expected."
                    ),
                })

        # 3. Duplicate detection (same amount + merchant within 24h)
        dup_key = (
            round(amount),
            (t.merchant or "").lower(),
            t.transaction_date.date(),
        )
        if dup_key in seen:
            anomalies.append({
                "transaction_id": t.id,
                "transaction_date": t.transaction_date,
                "merchant": t.merchant,
                "amount": Decimal(str(amount)),
                "category_name": cat_name,
                "anomaly_type": "duplicate",
                "severity": "high",
                "message": (
                    f"Possible duplicate: INR {amount:,.0f} at '{t.merchant}' "
                    "appears more than once on the same day."
                ),
            })
        seen.add(dup_key)

    return anomalies
