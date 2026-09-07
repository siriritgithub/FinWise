"""
Local FinWise financial assistant.

Financial facts always come from the FinWise database.
Natural-language questions are converted into deterministic,
verified database queries.

The assistant supports:
- balances
- current/previous month spending
- category spending
- largest expenses
- income
- savings
- savings rate
- budgets
- goals
- subscriptions
- forecasts
- anomalies
- financial health
- net worth
- what-if scenarios
- account creation
- transaction recording
- budget creation
- goal creation/contributions

No external LLM is required for verified financial answers.
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session


# ============================================================================
# BASIC HELPERS
# ============================================================================

def _money(value) -> float:
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _parse_amount(text: str):
    """
    Extract an INR amount from natural language.

    Examples:
        ₹5,000
        Rs 5000
        INR 5000
        5000
    """
    if not text:
        return None

    patterns = [
        r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        r"\b([0-9][0-9,]*(?:\.\d{1,2})?)\s*(?:rupees|rs)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return Decimal(match.group(1).replace(",", ""))

    # Fallback: plain number, but avoid extracting years.
    match = re.search(r"\b([0-9][0-9,]*(?:\.\d{1,2})?)\b", text)
    if match:
        value = match.group(1).replace(",", "")
        try:
            number = Decimal(value)
            if 1900 <= number <= 2100:
                return None
            return number
        except Exception:
            pass

    return None


def _format_period(start: date, end: date) -> str:
    if start == end:
        return start.strftime("%d %b %Y")

    return (
        f"{start.strftime('%d %b %Y')} "
        f"to {end.strftime('%d %b %Y')}"
    )


def _period(text: str):
    """
    Resolve natural-language periods.
    """

    t = text.lower().strip()
    today = date.today()

    # Today
    if re.search(r"\btoday\b", t):
        return today, today

    # Yesterday
    if re.search(r"\byesterday\b", t):
        d = today - timedelta(days=1)
        return d, d

    # This month
    if "this month" in t or "current month" in t:
        return today.replace(day=1), today

    # Last month
    if "last month" in t or "previous month" in t:
        current_start = today.replace(day=1)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end.replace(day=1)
        return previous_start, previous_end

    # This week
    if "this week" in t or "current week" in t:
        start = today - timedelta(days=today.weekday())
        return start, today

    # Last week
    if "last week" in t or "previous week" in t:
        current_week_start = today - timedelta(days=today.weekday())
        previous_end = current_week_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=6)
        return previous_start, previous_end

    # Last N days
    match = re.search(r"last\s+(\d+)\s+days?", t)
    if match:
        n = max(1, min(int(match.group(1)), 365))
        return today - timedelta(days=n - 1), today

    # Previous N days
    match = re.search(r"past\s+(\d+)\s+days?", t)
    if match:
        n = max(1, min(int(match.group(1)), 365))
        return today - timedelta(days=n - 1), today

    # Month names
    month_names = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    for name, month_number in month_names.items():
        if name in t:
            year_match = re.search(rf"{name}\s+(\d{{4}})", t)

            if year_match:
                year = int(year_match.group(1))
            else:
                year = today.year

            # Avoid future month accidentally becoming current year.
            if year == today.year and month_number > today.month:
                year -= 1

            start = date(year, month_number, 1)

            if month_number == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month_number + 1, 1) - timedelta(days=1)

            if end > today:
                end = today

            return start, end

    # Default = current month
    return today.replace(day=1), today


# ============================================================================
# CATEGORY HELPERS
# ============================================================================

def _category(db: Session, user_id: int, text: str):
    from app.models.models import Category

    keywords = {
        "food": "Food",
        "grocery": "Food",
        "groceries": "Food",
        "restaurant": "Food",
        "swiggy": "Food",
        "zomato": "Food",

        "shopping": "Shopping",
        "amazon": "Shopping",
        "flipkart": "Shopping",

        "transport": "Transport",
        "travel": "Transport",
        "uber": "Transport",
        "ola": "Transport",

        "rent": "Rent",

        "utility": "Utilities",
        "utilities": "Utilities",
        "electricity": "Utilities",
        "water": "Utilities",

        "entertainment": "Entertainment",
        "movie": "Entertainment",

        "health": "Health",
        "medical": "Health",
        "medicine": "Health",

        "education": "Education",
        "college": "Education",

        "investment": "Investments",
        "investments": "Investments",

        "loan": "Loans",
        "emi": "Loans",

        "gift": "Gifts",
        "gifts": "Gifts",
    }

    low = text.lower()

    target = None

    for keyword, category_name in keywords.items():
        if keyword in low:
            target = category_name
            break

    if not target:
        return None, 0.0

    cat = (
        db.query(Category)
        .filter(
            or_(
                Category.user_id == user_id,
                Category.is_system == 1,
            ),
            Category.name.ilike(f"%{target}%"),
            Category.is_active == 1,
        )
        .first()
    )

    if cat:
        return cat.id, 0.95

    return None, 0.0


def _find_category_by_text(db: Session, user_id: int, text: str):
    """
    More flexible category lookup for questions such as:
        How much did I spend on food?
        What did I spend on shopping?
    """

    from app.models.models import Category

    categories = (
        db.query(Category)
        .filter(
            or_(
                Category.user_id == user_id,
                Category.is_system == 1,
            ),
            Category.is_active == 1,
        )
        .all()
    )

    low = text.lower()

    # Exact category name first.
    for cat in categories:
        if cat.name and cat.name.lower() in low:
            return cat

    # Common aliases.
    aliases = {
        "food": ["food", "groceries", "grocery", "restaurant", "swiggy", "zomato"],
        "shopping": ["shopping", "amazon", "flipkart"],
        "transport": ["transport", "travel", "uber", "ola"],
        "rent": ["rent"],
        "utilities": ["utilities", "utility", "electricity", "water"],
        "entertainment": ["entertainment", "movie"],
        "health": ["health", "medical", "medicine"],
        "education": ["education", "college"],
        "gifts": ["gift", "gifts"],
        "loans": ["loan", "emi"],
        "investments": ["investment", "investments"],
    }

    for category_name, words in aliases.items():
        if any(word in low for word in words):
            for cat in categories:
                if cat.name and cat.name.lower() == category_name:
                    return cat

    return None


# ============================================================================
# ACCOUNT / GOAL HELPERS
# ============================================================================

def _account(db: Session, user_id: int, text: str):
    from app.models.models import Account

    accounts = (
        db.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.is_active == 1,
        )
        .all()
    )

    low = text.lower()

    for account in accounts:
        if account.name and account.name.lower() in low:
            return account

    if len(accounts) == 1:
        return accounts[0]

    return None


def _account_type(text: str):
    low = text.lower()

    for account_type in (
        "credit_card",
        "investment",
        "wallet",
        "loan",
        "cash",
        "bank",
    ):
        if account_type.replace("_", " ") in low:
            return account_type

        if account_type in low:
            return account_type

    return "bank"


def _goal(db: Session, user_id: int, text: str):
    from app.models.models import SavingsGoal

    goals = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.user_id == user_id)
        .all()
    )

    low = text.lower()

    for goal in goals:
        if goal.name and goal.name.lower() in low:
            return goal

    if len(goals) == 1:
        return goals[0]

    return None


# ============================================================================
# DATABASE ANALYSIS
# ============================================================================

def _transactions_for_period(
    db: Session,
    user_id: int,
    start: date,
    end: date,
):
    from app.models.models import Transaction

    end_datetime = datetime.combine(
        end + timedelta(days=1),
        datetime.min.time(),
    )

    return (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end_datetime,
        )
        .order_by(Transaction.transaction_date.desc())
        .all()
    )


def _summary(
    db: Session,
    user_id: int,
    start: date,
    end: date,
):
    from app.models.models import Account, Category

    tx = _transactions_for_period(
        db,
        user_id,
        start,
        end,
    )

    income = sum(
        _money(t.amount)
        for t in tx
        if t.type == "income"
    )

    expenses = sum(
        _money(t.amount)
        for t in tx
        if t.type == "expense"
    )

    categories = {
        c.id: c.name
        for c in (
            db.query(Category)
            .filter(Category.is_active == 1)
            .all()
        )
    }

    by_category = {}

    for transaction in tx:
        if transaction.type != "expense":
            continue

        name = categories.get(
            transaction.category_id,
            "Other",
        )

        by_category[name] = (
            by_category.get(name, 0)
            + _money(transaction.amount)
        )

    accounts = (
        db.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.is_active == 1,
        )
        .all()
    )

    return (
        income,
        expenses,
        by_category,
        accounts,
        tx,
    )


def _current_balance(db: Session, user_id: int):
    from app.models.models import Account

    accounts = (
        db.query(Account)
        .filter(
            Account.user_id == user_id,
            Account.is_active == 1,
        )
        .all()
    )

    return sum(
        _money(account.balance)
        for account in accounts
    )


def _largest_expenses(
    db: Session,
    user_id: int,
    start: date,
    end: date,
    limit: int = 5,
):
    from app.models.models import Category

    transactions = _transactions_for_period(
        db,
        user_id,
        start,
        end,
    )

    category_map = {
        c.id: c.name
        for c in (
            db.query(Category)
            .filter(Category.is_active == 1)
            .all()
        )
    }

    expenses = [
        t
        for t in transactions
        if t.type == "expense"
    ]

    expenses.sort(
        key=lambda t: _money(t.amount),
        reverse=True,
    )

    result = []

    for t in expenses[:limit]:
        result.append(
            {
                "id": t.id,
                "amount": _money(t.amount),
                "merchant": t.merchant or "Unknown",
                "category": category_map.get(
                    t.category_id,
                    "Other",
                ),
                "date": (
                    t.transaction_date.strftime("%d %b %Y")
                    if t.transaction_date
                    else None
                ),
                "description": t.description or "",
            }
        )

    return result


def _category_spending(
    db: Session,
    user_id: int,
    category_name: str,
    start: date,
    end: date,
):
    from app.models.models import Category

    category = (
        db.query(Category)
        .filter(
            or_(
                Category.user_id == user_id,
                Category.is_system == 1,
            ),
            Category.name.ilike(f"%{category_name}%"),
            Category.is_active == 1,
        )
        .first()
    )

    if not category:
        return 0.0, 0

    transactions = _transactions_for_period(
        db,
        user_id,
        start,
        end,
    )

    matching = [
        t
        for t in transactions
        if (
            t.type == "expense"
            and t.category_id == category.id
        )
    ]

    return (
        round(
            sum(_money(t.amount) for t in matching),
            2,
        ),
        len(matching),
    )


# ============================================================================
# MONTHLY REPORT
# ============================================================================

def _monthly_report(db: Session, user_id: int):

    today = date.today()

    start = today.replace(day=1)

    previous_end = start - timedelta(days=1)

    previous_start = previous_end.replace(day=1)

    income, expenses, categories, _, tx = _summary(
        db,
        user_id,
        start,
        today,
    )

    previous_income, previous_expenses, _, _, _ = _summary(
        db,
        user_id,
        previous_start,
        previous_end,
    )

    savings = income - expenses

    savings_rate = (
        savings / income * 100
        if income
        else 0
    )

    expense_change = (
        (expenses - previous_expenses)
        / previous_expenses
        * 100
        if previous_expenses
        else 0
    )

    top_category = max(
        categories.items(),
        key=lambda item: item[1],
        default=("None", 0),
    )

    largest = _largest_expenses(
        db,
        user_id,
        start,
        today,
        3,
    )

    largest_text = "\n".join(
        f"• {x['date']} — {x['merchant']} — "
        f"INR {x['amount']:,.2f} — {x['category']}"
        for x in largest
    )

    if not largest_text:
        largest_text = "No expense transactions recorded."

    direction = (
        "increased"
        if expense_change > 0
        else "decreased"
        if expense_change < 0
        else "did not change"
    )

    answer_text = (
        f"**{today.strftime('%B %Y')} financial report**\n\n"
        f"Period: **{_format_period(start, today)}**\n"
        f"Transactions analyzed: **{len(tx)}**\n\n"
        f"Income: **INR {income:,.2f}**\n"
        f"Expenses: **INR {expenses:,.2f}**\n"
        f"Savings: **INR {savings:,.2f}**\n"
        f"Savings rate: **{savings_rate:.1f}%**\n\n"
        f"Top spending category: "
        f"**{top_category[0]} — INR {top_category[1]:,.2f}**\n\n"
        f"Compared with {previous_start.strftime('%B')}, "
        f"expenses {direction} by **{abs(expense_change):.1f}%**.\n\n"
        f"**Largest expenses**\n"
        f"{largest_text}"
    )

    return answer_text, {
        "period_start": str(start),
        "period_end": str(today),
        "transaction_count": len(tx),
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "savings_rate": round(savings_rate, 2),
        "expense_change_pct": round(expense_change, 2),
        "top_category": top_category[0],
        "top_category_amount": top_category[1],
        "largest_expenses": largest,
    }


# ============================================================================
# WHAT-IF
# ============================================================================

def _what_if(db: Session, user_id: int, text: str):

    amount = _parse_amount(text)

    if amount is None:
        return (
            "Tell me the monthly reduction, for example: "
            "**What if I reduce food spending by ₹2,000 per month?**"
        )

    today = date.today()

    start = today.replace(day=1)

    income, expenses, _, _, _ = _summary(
        db,
        user_id,
        start,
        today,
    )

    days_elapsed = max(today.day, 1)

    estimated_monthly_expenses = (
        expenses / days_elapsed * 30
    )

    current_savings = max(
        0,
        income - estimated_monthly_expenses,
    )

    new_expenses = max(
        0,
        estimated_monthly_expenses - float(amount),
    )

    projected_savings = max(
        0,
        income - new_expenses,
    )

    annual_improvement = float(amount) * 12

    return (
        f"If you reduce monthly spending by "
        f"**INR {float(amount):,.2f}**:\n\n"
        f"Current estimated monthly savings: "
        f"**INR {current_savings:,.2f}**\n"
        f"Projected monthly savings: "
        f"**INR {projected_savings:,.2f}**\n"
        f"Annual improvement: "
        f"**INR {annual_improvement:,.2f}**\n\n"
        f"This is an estimate based on your current-month "
        f"recorded income and spending."
    )


def _last_user_message(history):
    """Return the most recent meaningful user message from chat history."""
    for item in reversed(history or []):
        if not isinstance(item, dict):
            continue
        if item.get("role") == "user" and item.get("content"):
            return str(item["content"]).strip()
    return ""


def _contextualize_followup(message: str, history=None) -> str:
    """
    Resolve short conversational follow-ups before deterministic intent matching.

    Examples:
        "What about last month?" after a spending question -> previous question + last month
        "What about food?" after a spending question -> previous question + food
    """
    msg = (message or "").strip()
    previous = _last_user_message(history)

    if not msg or not previous:
        return msg

    low = msg.lower()
    prev_low = previous.lower()

    follow_up = (
        low.startswith(("what about", "how about", "and", "what if"))
        or low in {"why?", "why", "more", "tell me more", "details", "and then?"}
        or bool(re.fullmatch(r"(this|last|previous|current)\s+(month|week)", low))
    )

    if not follow_up:
        return msg

    # A period-only follow-up should inherit the previous analytical intent.
    if re.fullmatch(r"(this|last|previous|current)\s+(month|week)", low):
        return f"{previous} {msg}"

    # "What about food?" / "How about shopping?" inherits spending intent.
    if low.startswith(("what about ", "how about ")) and any(
        word in prev_low
        for word in ("spend", "spent", "expense", "income", "save", "savings")
    ):
        subject = re.sub(r"^(what about|how about)\s+", "", msg, flags=re.I).strip(" ?.")
        if subject:
            return f"{previous} on {subject}"

    return msg


def _is_analytical_question(text: str) -> bool:
    """Return True for questions that ask about recorded data rather than recording data."""
    low = (text or "").lower().strip()
    return bool(
        re.search(r"\bhow much\b", low)
        or re.search(r"\bhow many\b", low)
        or re.search(r"\bshow me\b", low)
        or re.search(r"\bwhat (?:is|was|are|were)\b", low)
        or re.search(r"\bwhere am i\b", low)
        or re.search(r"\bwhich\b.*\b(spending|expense|category)\b", low)
        or low.startswith(("why", "tell me about", "compare ", "give me a report"))
    )


# ============================================================================
# MAIN ANSWER ENGINE
# ============================================================================

def answer(
    db: Session,
    user_id: int,
    message: str,
    history=None,
):

    msg = _contextualize_followup(message, history)

    low = msg.lower()

    if not msg:
        return {
            "answer_text": "Please tell me what you'd like to know.",
            "data_summary": {},
            "suggestions": [],
        }

    # ========================================================================
    # CREATE ACCOUNT
    # ========================================================================

    if re.search(
        r"\b(create|add|open)\b.*\b(account|bank account|wallet|cash)",
        low,
    ):
        amount = _parse_amount(msg) or Decimal("0")

        match = re.search(
            r"(?:account|called|named)\s+"
            r"(?:called\s+|named\s+)?"
            r"([A-Za-z][A-Za-z0-9 _-]{1,40})",
            msg,
            re.I,
        )

        name = (
            match.group(1).strip()
            if match
            else "New Account"
        )

        name = re.split(
            r"\s+(?:with|having|and)\s+",
            name,
            flags=re.I,
        )[0].strip()

        from app.models.models import Account

        account = Account(
            user_id=user_id,
            name=name,
            type=_account_type(low),
            balance=amount,
            currency="INR",
        )

        db.add(account)
        db.commit()
        db.refresh(account)

        return {
            "answer_text": (
                f"Done. I created **{account.name}** "
                f"with an opening balance of "
                f"**INR {float(amount):,.2f}**."
            ),
            "data_summary": {
                "account_id": account.id,
                "balance": float(amount),
            },
            "suggestions": [
                "How much money do I have?",
                "How much did I spend this month?",
            ],
        }

    # ========================================================================
    # ADD MONEY TO ACCOUNT
    # ========================================================================

    if re.search(
        r"\b(add|deposit|put|increase)\b.*"
        r"\b(balance|money|account)\b",
        low,
    ):
        amount = _parse_amount(msg)

        account = _account(
            db,
            user_id,
            msg,
        )

        if amount is None:
            return {
                "answer_text": (
                    "Tell me the amount, for example: "
                    "**Add ₹5,000 to HDFC.**"
                ),
                "data_summary": {},
                "suggestions": [],
            }

        if not account:
            return {
                "answer_text": (
                    "I couldn't identify the account. "
                    "Please mention its name, for example: "
                    "**Add ₹5,000 to HDFC.**"
                ),
                "data_summary": {},
                "suggestions": [],
            }

        account.balance = (
            Decimal(str(account.balance))
            + amount
        )

        from app.models.models import Transaction

        transaction = Transaction(
            user_id=user_id,
            account_id=account.id,
            amount=amount,
            type="income",
            merchant="Account top-up",
            description=(
                "Balance added via FinWise assistant"
            ),
            transaction_date=datetime.utcnow(),
            payment_method="other",
        )

        db.add(transaction)
        db.commit()

        return {
            "answer_text": (
                f"Done. **INR {float(amount):,.2f}** "
                f"was added to **{account.name}**.\n\n"
                f"New balance: "
                f"**INR {float(account.balance):,.2f}**"
            ),
            "data_summary": {
                "account_id": account.id,
                "new_balance": float(account.balance),
            },
            "suggestions": [],
        }

    # ========================================================================
    # RECORD EXPENSE
    # ========================================================================

    expense_record_request = (
        bool(re.search(
            r"\b(add|record|log|paid|purchase|bought)\b.*"
            r"\b(spent|spend|expense|paid|purchase|bought|for|on)\b",
            low,
        ))
        or bool(re.search(r"\bi\s+(?:just\s+)?spent\b", low))
    )

    # Never treat an analytical question such as "How much did I spend
    # this month?" as a request to create a transaction.
    if expense_record_request and not _is_analytical_question(low):

        amount = _parse_amount(msg)

        account = _account(
            db,
            user_id,
            msg,
        )

        if amount is None:
            return {
                "answer_text": (
                    "Tell me the amount, for example: "
                    "**I spent ₹850 on food.**"
                ),
                "data_summary": {},
                "suggestions": [],
            }

        if not account:
            return {
                "answer_text": (
                    "Please create or mention an account "
                    "first so I know where to record the expense."
                ),
                "data_summary": {},
                "suggestions": [],
            }

        category_id, confidence = _category(
            db,
            user_id,
            msg,
        )

        merchant = None

        match = re.search(
            r"(?:at|from|on)\s+"
            r"([A-Za-z][A-Za-z0-9 &.-]{1,50})",
            msg,
            re.I,
        )

        if match:
            merchant = match.group(1).strip()

        from app.models.models import Transaction

        transaction = Transaction(
            user_id=user_id,
            account_id=account.id,
            amount=amount,
            type="expense",
            category_id=category_id,
            merchant=merchant,
            description=msg,
            transaction_date=datetime.utcnow(),
            payment_method="other",
            confidence_score=(
                confidence or None
            ),
        )

        db.add(transaction)

        account.balance = (
            Decimal(str(account.balance))
            - amount
        )

        db.commit()
        db.refresh(transaction)

        return {
            "answer_text": (
                f"Recorded **INR {float(amount):,.2f}** "
                f"expense in **{account.name}**.\n\n"
                f"New balance: "
                f"**INR {float(account.balance):,.2f}**"
            ),
            "data_summary": {
                "transaction_id": transaction.id,
                "amount": float(amount),
            },
            "suggestions": [
                "How much did I spend this month?",
            ],
        }

    # ========================================================================
    # RECORD INCOME
    # ========================================================================

    if re.search(
        r"\b(add|record|log)\b.*"
        r"\b(income|salary|earned|received)\b",
        low,
    ):

        amount = _parse_amount(msg)

        account = _account(
            db,
            user_id,
            msg,
        )

        if amount is None:
            return {
                "answer_text": (
                    "Tell me the income amount, for example: "
                    "**Add ₹50,000 salary.**"
                ),
                "data_summary": {},
                "suggestions": [],
            }

        if not account:
            return {
                "answer_text": (
                    "Please mention which account received "
                    "the income."
                ),
                "data_summary": {},
                "suggestions": [],
            }

        from app.models.models import Transaction

        transaction = Transaction(
            user_id=user_id,
            account_id=account.id,
            amount=amount,
            type="income",
            merchant="Income",
            description=msg,
            transaction_date=datetime.utcnow(),
            payment_method="other",
        )

        db.add(transaction)

        account.balance = (
            Decimal(str(account.balance))
            + amount
        )

        db.commit()

        return {
            "answer_text": (
                f"Recorded **INR {float(amount):,.2f}** "
                f"income in **{account.name}**.\n\n"
                f"New balance: "
                f"**INR {float(account.balance):,.2f}**"
            ),
            "data_summary": {
                "transaction_id": transaction.id,
                "amount": float(amount),
            },
            "suggestions": [],
        }

    # ========================================================================
    # CREATE BUDGET
    # ========================================================================

    if re.search(
        r"\b(create|add|set)\b.*\bbudget\b",
        low,
    ):

        amount = _parse_amount(msg)

        if amount is None:
            return {
                "answer_text": (
                    "Tell me the budget amount, for example: "
                    "**Create a food budget of ₹8,000 this month.**"
                ),
                "data_summary": {},
                "suggestions": [],
            }

        category_id, _ = _category(
            db,
            user_id,
            msg,
        )

        if not category_id:
            return {
                "answer_text": (
                    "Tell me the budget category, for example: "
                    "**Create a Food budget of ₹8,000 this month.**"
                ),
                "data_summary": {},
                "suggestions": [],
            }

        from app.models.models import Budget

        month = date.today().strftime("%Y-%m")

        existing = (
            db.query(Budget)
            .filter(
                Budget.user_id == user_id,
                Budget.category_id == category_id,
                Budget.month == month,
            )
            .first()
        )

        if existing:
            existing.amount = amount
            action = "updated"
            budget_id = existing.id
        else:
            budget = Budget(
                user_id=user_id,
                category_id=category_id,
                amount=amount,
                month=month,
            )
            db.add(budget)
            db.commit()
            db.refresh(budget)
            action = "created"
            budget_id = budget.id

        db.commit()

        return {
            "answer_text": (
                f"Budget {action}: **INR {float(amount):,.2f}** "
                f"for this month."
            ),
            "data_summary": {
                "budget_id": budget_id,
                "month": month,
                "amount": float(amount),
            },
            "suggestions": [],
        }

    # ========================================================================
    # CREATE GOAL
    # ========================================================================

    if re.search(
        r"\b(create|add|set)\b.*\bgoal\b",
        low,
    ):

        amount = _parse_amount(msg)

        if amount is None:
            return {
                "answer_text": (
                    "Tell me the target, for example: "
                    "**Create a goal to save ₹100,000 for a laptop.**"
                ),
                "data_summary": {},
                "suggestions": [],
            }

        from app.models.models import SavingsGoal

        match = re.search(
            r"(?:for|called|named)\s+"
            r"([A-Za-z][A-Za-z0-9 _-]{1,50})",
            msg,
            re.I,
        )

        name = (
            match.group(1).strip()
            if match
            else "Savings Goal"
        )

        name = re.split(
            r"\s+(?:by|with|of)\s+",
            name,
            flags=re.I,
        )[0].strip()

        goal = SavingsGoal(
            user_id=user_id,
            name=name,
            target_amount=amount,
            current_amount=Decimal("0"),
        )

        db.add(goal)
        db.commit()
        db.refresh(goal)

        return {
            "answer_text": (
                f"Created the **{goal.name}** goal "
                f"with a target of "
                f"**INR {float(amount):,.2f}**."
            ),
            "data_summary": {
                "goal_id": goal.id,
                "target_amount": float(amount),
            },
            "suggestions": [],
        }

    # ========================================================================
    # ADD TO GOAL
    # ========================================================================

    goal_record_request = bool(re.search(
        r"\b(add|contribute|put|save)\b.*\b(goal|savings)\b",
        low,
    ))

    if goal_record_request and not _is_analytical_question(low):

        amount = _parse_amount(msg)

        goal = _goal(
            db,
            user_id,
            msg,
        )

        if amount is None or not goal:
            return {
                "answer_text": (
                    "Tell me the amount and goal name, for example: "
                    "**Add ₹5,000 to my laptop goal.**"
                ),
                "data_summary": {},
                "suggestions": [],
            }

        goal.current_amount = (
            Decimal(str(goal.current_amount))
            + amount
        )

        db.commit()

        percentage = (
            float(goal.current_amount)
            / float(goal.target_amount)
            * 100
            if float(goal.target_amount)
            else 0
        )

        return {
            "answer_text": (
                f"Added **INR {float(amount):,.2f}** "
                f"to **{goal.name}**.\n\n"
                f"Progress: "
                f"**INR {float(goal.current_amount):,.2f} / "
                f"INR {float(goal.target_amount):,.2f}** "
                f"({min(percentage, 100):.1f}%)"
            ),
            "data_summary": {
                "goal_id": goal.id,
                "current_amount": float(goal.current_amount),
                "target_amount": float(goal.target_amount),
            },
            "suggestions": [],
        }

    # ========================================================================
    # WHAT IF
    # ========================================================================

    if (
        "what if" in low
        or (
            "reduce" in low
            and "spending" in low
        )
    ):
        return {
            "answer_text": _what_if(
                db,
                user_id,
                msg,
            ),
            "data_summary": {},
            "suggestions": [],
        }

    # ========================================================================
    # MONTHLY REPORT
    # ========================================================================

    if (
        "monthly report" in low
        or "monthly financial report" in low
        or "what changed" in low
    ):
        text, data = _monthly_report(
            db,
            user_id,
        )

        return {
            "answer_text": text,
            "data_summary": data,
            "suggestions": [
                "Where am I spending the most?",
                "Show my largest expenses.",
            ],
        }

    # ========================================================================
    # FINANCIAL HEALTH
    # ========================================================================

    if (
        "health score" in low
        or "financial health" in low
        or "financial health score" in low
    ):
        from app.services.health_score import compute_health_score

        health = compute_health_score(
            db,
            user_id,
        )

        factors = health.get(
            "factors",
            [],
        )

        factor_text = "\n".join(
            (
                f"• {factor['name']}: "
                f"{factor['score']}/{factor['max_score']} — "
                f"{factor['description']}"
            )
            for factor in factors
        )

        return {
            "answer_text": (
                f"Your Financial Health Score is "
                f"**{health['total_score']:.0f}/100 "
                f"(Grade {health['grade']})**.\n\n"
                f"{factor_text}"
            ),
            "data_summary": health,
            "suggestions": [],
        }

    # ========================================================================
    # FORECAST
    # ========================================================================

    if (
        "forecast" in low
        or "predict my cash" in low
        or "future balance" in low
        or "cash flow prediction" in low
    ):
        from app.services.forecasting import build_forecast

        forecast = build_forecast(
            db,
            user_id,
            30,
        )

        assumptions = forecast.get(
            "assumptions",
            [],
        )

        assumption_text = "\n".join(
            f"• {item}"
            for item in assumptions
        )

        return {
            "answer_text": (
                f"Your **30-day cash-flow forecast** "
                f"starts from "
                f"**INR {_money(forecast.get('current_balance')):,.2f}**.\n\n"
                f"Expected ending balance: "
                f"**INR {_money(forecast.get('ending_balance')):,.2f}**\n\n"
                f"Assumptions:\n"
                f"{assumption_text}"
            ),
            "data_summary": forecast,
            "suggestions": [],
        }

    # ========================================================================
    # ANOMALIES
    # ========================================================================

    if (
        "anomal" in low
        or "unusual spending" in low
        or "unusual transaction" in low
    ):
        from app.services.anomaly import detect_anomalies

        anomalies = detect_anomalies(
            db,
            user_id,
            90,
        )

        if not anomalies:
            text = (
                "No unusual spending was detected "
                "in the last 90 days."
            )
        else:
            text = (
                "**Unusual spending detected:**\n\n"
                + "\n".join(
                    f"• {item['message']}"
                    for item in anomalies[:8]
                )
            )

        return {
            "answer_text": text,
            "data_summary": {
                "count": len(anomalies),
                "period_days": 90,
            },
            "suggestions": [],
        }

    # ========================================================================
    # NET WORTH
    # ========================================================================

    if (
        "net worth" in low
        or "networth" in low
    ):
        from app.models.models import Account

        accounts = (
            db.query(Account)
            .filter(
                Account.user_id == user_id,
                Account.is_active == 1,
            )
            .all()
        )

        assets = sum(
            _money(a.balance)
            for a in accounts
            if a.type not in (
                "loan",
                "credit_card",
            )
        )

        liabilities = sum(
            abs(_money(a.balance))
            for a in accounts
            if a.type in (
                "loan",
                "credit_card",
            )
        )

        net_worth = assets - liabilities

        return {
            "answer_text": (
                f"Your estimated net worth is "
                f"**INR {net_worth:,.2f}**.\n\n"
                f"Assets: **INR {assets:,.2f}**\n"
                f"Liabilities: **INR {liabilities:,.2f}**"
            ),
            "data_summary": {
                "assets": assets,
                "liabilities": liabilities,
                "net_worth": net_worth,
            },
            "suggestions": [],
        }

    # ========================================================================
    # BALANCE
    # ========================================================================

    if (
        "balance" in low
        or "how much money" in low
        or "how much do i have" in low
        or "how much cash" in low
    ):
        from app.models.models import Account

        accounts = (
            db.query(Account)
            .filter(
                Account.user_id == user_id,
                Account.is_active == 1,
            )
            .all()
        )

        if not accounts:
            return {
                "answer_text": (
                    "No active accounts found. "
                    "Add an account first and I'll track its balance."
                ),
                "data_summary": {},
                "suggestions": [],
            }

        total = sum(
            _money(a.balance)
            for a in accounts
        )

        lines = "\n".join(
            f"• {a.name}: INR {_money(a.balance):,.2f}"
            for a in accounts
        )

        return {
            "answer_text": (
                f"Your total current balance is "
                f"**INR {total:,.2f}**.\n\n"
                f"{lines}"
            ),
            "data_summary": {
                "total_balance": total,
                "account_count": len(accounts),
            },
            "suggestions": [
                "How much did I spend this month?",
                "What is my savings rate?",
            ],
        }

    # ========================================================================
    # LARGEST EXPENSES
    # ========================================================================

    if (
        "largest expense" in low
        or "biggest expense" in low
        or "highest expense" in low
        or "top expenses" in low
        or "three largest" in low
        or "5 largest" in low
        or "five largest" in low
    ):

        start, end = _period(low)

        largest = _largest_expenses(
            db,
            user_id,
            start,
            end,
            5,
        )

        if not largest:
            return {
                "answer_text": (
                    f"No expense transactions were found "
                    f"for **{_format_period(start, end)}**."
                ),
                "data_summary": {
                    "period_start": str(start),
                    "period_end": str(end),
                    "count": 0,
                },
                "suggestions": [],
            }

        lines = "\n".join(
            (
                f"{index}. **{item['merchant']}** — "
                f"INR {item['amount']:,.2f} — "
                f"{item['category']} — "
                f"{item['date']}"
            )
            for index, item in enumerate(
                largest,
                start=1,
            )
        )

        total = sum(
            item["amount"]
            for item in largest
        )

        return {
            "answer_text": (
                f"**Largest expenses**\n\n"
                f"Period: **{_format_period(start, end)}**\n\n"
                f"{lines}\n\n"
                f"Top {len(largest)} expenses total: "
                f"**INR {total:,.2f}**"
            ),
            "data_summary": {
                "period_start": str(start),
                "period_end": str(end),
                "count": len(largest),
                "largest_expenses": largest,
            },
            "suggestions": [],
        }

    # ========================================================================
    # CATEGORY SPENDING
    # ========================================================================

    category = _find_category_by_text(
        db,
        user_id,
        msg,
    )

    if category and (
        "spend" in low
        or "spent" in low
        or "expense" in low
        or "how much" in low
        or "cost" in low
    ):

        start, end = _period(low)

        total, count = _category_spending(
            db,
            user_id,
            category.name,
            start,
            end,
        )

        return {
            "answer_text": (
                f"You spent **INR {total:,.2f}** "
                f"on **{category.name}**.\n\n"
                f"Period: **{_format_period(start, end)}**\n"
                f"Transactions analyzed: **{count}**"
            ),
            "data_summary": {
                "category": category.name,
                "period_start": str(start),
                "period_end": str(end),
                "total": total,
                "transaction_count": count,
            },
            "suggestions": [
                "Where am I spending the most?",
                "Show my largest expenses.",
            ],
        }

    # ========================================================================
    # WHERE AM I SPENDING MOST?
    # ========================================================================

    if (
        "where am i spending" in low
        or "spending most" in low
        or "spend most" in low
        or "biggest spending category" in low
        or "largest spending category" in low
        or "top spending category" in low
    ):

        start, end = _period(low)

        _, expenses, categories, _, tx = _summary(
            db,
            user_id,
            start,
            end,
        )

        ranked = sorted(
            categories.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        if not ranked:
            return {
                "answer_text": (
                    f"No expenses were recorded for "
                    f"**{_format_period(start, end)}**."
                ),
                "data_summary": {},
                "suggestions": [],
            }

        lines = "\n".join(
            (
                f"{index}. **{name}** — "
                f"INR {amount:,.2f}"
            )
            for index, (name, amount)
            in enumerate(
                ranked[:8],
                start=1,
            )
        )

        percentage = (
            ranked[0][1] / expenses * 100
            if expenses
            else 0
        )

        return {
            "answer_text": (
                f"Your biggest spending category is "
                f"**{ranked[0][0]}** at "
                f"**INR {ranked[0][1]:,.2f}** "
                f"({percentage:.1f}% of expenses).\n\n"
                f"Period: **{_format_period(start, end)}**\n"
                f"Transactions analyzed: **{len(tx)}**\n\n"
                f"**Spending by category**\n"
                f"{lines}"
            ),
            "data_summary": {
                "period_start": str(start),
                "period_end": str(end),
                "total_expenses": expenses,
                "categories": [
                    {
                        "category": name,
                        "amount": amount,
                    }
                    for name, amount in ranked
                ],
            },
            "suggestions": [],
        }

    # ========================================================================
    # SAVINGS RATE
    # ========================================================================

    if (
        "savings rate" in low
        or "how much did i save" in low
        or "how much have i saved" in low
        or "how much can i save" in low
    ):

        start, end = _period(low)

        income, expenses, _, _, tx = _summary(
            db,
            user_id,
            start,
            end,
        )

        savings = income - expenses

        rate = (
            savings / income * 100
            if income
            else 0
        )

        return {
            "answer_text": (
                f"For **{_format_period(start, end)}**:\n\n"
                f"Income: **INR {income:,.2f}**\n"
                f"Expenses: **INR {expenses:,.2f}**\n"
                f"Saved: **INR {savings:,.2f}**\n"
                f"Savings rate: **{rate:.1f}%**\n\n"
                f"Transactions analyzed: **{len(tx)}**"
            ),
            "data_summary": {
                "period_start": str(start),
                "period_end": str(end),
                "income": income,
                "expenses": expenses,
                "savings": savings,
                "savings_rate": round(rate, 2),
                "transaction_count": len(tx),
            },
            "suggestions": [],
        }

    # ========================================================================
    # GENERAL SPENDING / INCOME
    # ========================================================================

    if any(
        keyword in low
        for keyword in (
            "spend",
            "spent",
            "expense",
            "expenses",
            "income",
            "salary",
            "save",
            "savings",
        )
    ):

        start, end = _period(low)

        income, expenses, categories, _, tx = _summary(
            db,
            user_id,
            start,
            end,
        )

        savings = income - expenses

        rate = (
            savings / income * 100
            if income
            else 0
        )

        top_category = max(
            categories.items(),
            key=lambda item: item[1],
            default=("None", 0),
        )

        return {
            "answer_text": (
                f"For **{_format_period(start, end)}**:\n\n"
                f"Income: **INR {income:,.2f}**\n"
                f"Expenses: **INR {expenses:,.2f}**\n"
                f"Net savings: **INR {savings:,.2f}**\n"
                f"Savings rate: **{rate:.1f}%**\n\n"
                f"Transactions analyzed: **{len(tx)}**\n"
                f"Top category: **{top_category[0]} — "
                f"INR {top_category[1]:,.2f}**"
            ),
            "data_summary": {
                "period_start": str(start),
                "period_end": str(end),
                "income": income,
                "expenses": expenses,
                "savings": savings,
                "savings_rate": round(rate, 2),
                "transaction_count": len(tx),
                "top_category": top_category[0],
                "top_category_amount": top_category[1],
            },
            "suggestions": [
                "Where am I spending the most?",
                "Show my largest expenses.",
            ],
        }

    # ========================================================================
    # BUDGET STATUS
    # ========================================================================

    if "budget" in low:

        from app.models.models import Budget, Transaction

        month = date.today().strftime("%Y-%m")

        budgets = (
            db.query(Budget)
            .filter(
                Budget.user_id == user_id,
                Budget.month == month,
            )
            .all()
        )

        if not budgets:
            return {
                "answer_text": (
                    "You have no budgets set for this month."
                ),
                "data_summary": {},
                "suggestions": [
                    "Create a Food budget of ₹5,000.",
                ],
            }

        lines = []

        total_budget = 0
        total_spent = 0

        for budget in budgets:

            spent = sum(
                _money(t.amount)
                for t in (
                    db.query(Transaction)
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.category_id == budget.category_id,
                        Transaction.type == "expense",
                        Transaction.transaction_date.like(
                            f"{month}%"
                        ),
                    )
                    .all()
                )
            )

            budget_amount = _money(
                budget.amount
            )

            percentage = (
                spent / budget_amount * 100
                if budget_amount
                else 0
            )

            category_name = (
                budget.category.name
                if budget.category
                else "Other"
            )

            remaining = budget_amount - spent

            lines.append(
                f"• **{category_name}**: "
                f"INR {spent:,.2f} / "
                f"INR {budget_amount:,.2f} "
                f"({percentage:.1f}%) — "
                f"Remaining INR {remaining:,.2f}"
            )

            total_budget += budget_amount
            total_spent += spent

        return {
            "answer_text": (
                f"**{date.today().strftime('%B %Y')} budget status**\n\n"
                + "\n".join(lines)
                + f"\n\nTotal budget: **INR {total_budget:,.2f}**"
                f"\nTotal spent: **INR {total_spent:,.2f}**"
            ),
            "data_summary": {
                "month": month,
                "total_budget": total_budget,
                "total_spent": total_spent,
            },
            "suggestions": [],
        }

    # ========================================================================
    # SUBSCRIPTIONS
    # ========================================================================

    if (
        "subscription" in low
        or "recurring" in low
    ):

        from app.models.models import RecurringRule

        subscriptions = (
            db.query(RecurringRule)
            .filter(
                RecurringRule.user_id == user_id,
                RecurringRule.is_subscription == 1,
            )
            .all()
        )

        monthly = sum(
            _money(item.expected_amount)
            * 30
            / item.interval_days
            for item in subscriptions
            if item.expected_amount
            and item.interval_days
        )

        return {
            "answer_text": (
                f"You have **{len(subscriptions)}** "
                f"detected subscriptions.\n\n"
                f"Estimated monthly cost: "
                f"**INR {monthly:,.2f}**\n"
                f"Estimated annual cost: "
                f"**INR {monthly * 12:,.2f}**"
            ),
            "data_summary": {
                "count": len(subscriptions),
                "monthly": round(monthly, 2),
                "annual": round(monthly * 12, 2),
            },
            "suggestions": [],
        }

    # ========================================================================
    # GOALS
    # ========================================================================

    if (
        "goal" in low
        or "saving for" in low
        or "savings goal" in low
    ):

        from app.models.models import SavingsGoal

        goals = (
            db.query(SavingsGoal)
            .filter(
                SavingsGoal.user_id == user_id
            )
            .all()
        )

        if not goals:
            return {
                "answer_text": (
                    "You don't have any savings goals yet."
                ),
                "data_summary": {},
                "suggestions": [
                    "Create a goal to save ₹50,000 for a phone.",
                ],
            }

        lines = []

        for goal in goals:

            target = _money(
                goal.target_amount
            )

            current = _money(
                goal.current_amount
            )

            percentage = (
                current / target * 100
                if target
                else 0
            )

            remaining = max(
                0,
                target - current,
            )

            lines.append(
                f"• **{goal.name}**: "
                f"INR {current:,.2f} / "
                f"INR {target:,.2f} "
                f"({min(percentage, 100):.1f}%) — "
                f"Remaining INR {remaining:,.2f}"
            )

        return {
            "answer_text": (
                "**Your savings goals**\n\n"
                + "\n".join(lines)
            ),
            "data_summary": {
                "goal_count": len(goals),
            },
            "suggestions": [],
        }

    # ========================================================================
    # FAQ / GENERAL FINANCE
    # ========================================================================

    faq = {
        "compound interest": (
            "Compound interest means you earn interest "
            "on both your original principal and previously "
            "earned interest. In FinWise, use it as a planning "
            "concept rather than a guaranteed return."
        ),

        "emergency fund": (
            "A common planning target is around 3–6 months "
            "of essential expenses. FinWise can estimate "
            "your coverage from your recorded balances "
            "and spending."
        ),

        "50/30/20": (
            "The 50/30/20 rule is a budgeting guideline: "
            "roughly 50% needs, 30% wants and 20% savings "
            "or debt repayment. It is a rule of thumb, "
            "not a universal prescription."
        ),
    }

    for key, value in faq.items():
        if key in low:
            return {
                "answer_text": value,
                "data_summary": {},
                "suggestions": [],
            }

    # ========================================================================
    # FALLBACK
    # ========================================================================

    return {
        "answer_text": (
            "I can analyze your FinWise data using your "
            "actual database records.\n\n"
            "Try asking me:\n"
            "• **How much did I spend this month?**\n"
            "• **How much did I spend on food?**\n"
            "• **Where am I spending the most?**\n"
            "• **Show my largest expenses.**\n"
            "• **How much did I save this month?**\n"
            "• **What is my savings rate?**\n"
            "• **How is my budget?**\n"
            "• **What is my net worth?**\n"
            "• **Show my financial health.**\n"
            "• **Give me a cash-flow forecast.**\n"
            "• **What if I reduce spending by ₹2,000?**"
        ),
        "data_summary": {},
        "suggestions": [
            "How much did I spend this month?",
            "Where am I spending the most?",
            "Show my largest expenses.",
        ],
    }