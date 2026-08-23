"""
Categorization service.
Phase 1: keyword rules (instant, no training data needed).
Phase 2: TF-IDF + LogisticRegression trained on user-corrected labels.
confidence_score is stored on every transaction so the UI can flag low-confidence ones.
"""
import re
from typing import Optional, Tuple
from sqlalchemy.orm import Session

# Keyword rules: (pattern, category_name)
KEYWORD_RULES: list[Tuple[str, str]] = [
    # Income
    (r"\b(salary|payroll|ctc|stipend)\b", "Salary"),
    (r"\b(freelance|invoice|client payment)\b", "Freelance"),
    # Food
    (r"\b(swiggy|zomato|dominos|pizza|burger|restaurant|cafe|food|biryani|hotel)\b", "Food"),
    # Transport
    (r"\b(uber|ola|rapido|metro|irctc|train|bus|petrol|fuel|parking|toll)\b", "Transport"),
    # Rent
    (r"\b(rent|landlord|pg|hostel)\b", "Rent"),
    # Utilities
    (r"\b(electricity|water bill|gas|broadband|wifi|internet|bsnl|airtel|jio|vi|recharge)\b", "Utilities"),
    # Shopping
    (r"\b(amazon|flipkart|myntra|ajio|meesho|shopping|mall|store)\b", "Shopping"),
    # Entertainment
    (r"\b(netflix|prime|hotstar|spotify|youtube|bookmyshow|movie|concert|game)\b", "Entertainment"),
    # Health
    (r"\b(pharmacy|medical|hospital|doctor|clinic|apollo|1mg|netmeds|health)\b", "Health"),
    # Education
    (r"\b(udemy|coursera|school|college|tuition|books|education)\b", "Education"),
    # Subscriptions
    (r"\b(subscription|membership|annual plan|monthly plan)\b", "Subscriptions"),
    # Loans & EMI
    (r"\b(emi|loan|hdfc loan|sbi loan|bajaj|lic|insurance premium)\b", "Loans & EMI"),
    # Savings & Investments
    (r"\b(mutual fund|sip|zerodha|groww|nps|ppf|fd|fixed deposit|investment)\b", "Savings & Investments"),
    # Cash
    (r"\b(atm|cash withdrawal|withdraw)\b", "Cash Withdrawal"),
    # Gifts
    (r"\b(gift|birthday|wedding|donation)\b", "Gifts"),
]


def _rule_based_categorize(text: str) -> Tuple[Optional[str], float]:
    """Return (category_name, confidence) using keyword rules."""
    text_lower = text.lower()
    for pattern, category in KEYWORD_RULES:
        if re.search(pattern, text_lower):
            return category, 0.85
    return None, 0.0


def categorize_transaction(
    description: str,
    merchant: str,
    db: Session,
    user_id: int,
) -> Tuple[Optional[int], float]:
    """
    Returns (category_id, confidence_score).
    Tries rule-based first; falls back to 'Other'.
    """
    from app.models.models import Category

    combined = f"{merchant or ''} {description or ''}".strip()
    cat_name, confidence = _rule_based_categorize(combined)

    if not cat_name:
        cat_name = "Other"
        confidence = 0.3

    # Look up category id — system categories first, then user's
    cat = (
        db.query(Category)
        .filter(
            Category.name == cat_name,
            Category.is_active == 1,
        )
        .order_by(Category.is_system.desc())
        .first()
    )
    if cat:
        return cat.id, confidence
    return None, 0.0


def batch_categorize(transactions: list, db: Session, user_id: int) -> int:
    """Re-categorize transactions with no category or low confidence. Returns count updated."""
    from app.models.models import Transaction

    updated = 0
    for txn in transactions:
        if txn.category_id is not None and (txn.confidence_score or 0) >= 0.7:
            continue
        cat_id, score = categorize_transaction(
            txn.description or "", txn.merchant or "", db, user_id
        )
        if cat_id:
            txn.category_id = cat_id
            txn.confidence_score = score
            updated += 1
    db.commit()
    return updated
