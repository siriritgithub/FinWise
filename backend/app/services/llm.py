"""
FinWise AI Assistant - Ollama tool-calling engine.

Architecture:
  User message
    -> Ollama/Qwen selects tool
    -> Backend safety layer validates tool choice
    -> Backend executes verified DB operation
    -> Result returned to Ollama
    -> Ollama generates natural response

The LLM never touches the database directly.
Financial truth always comes from verified backend tools.
"""

import json
import re
import threading
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Per-user pending deletion store
# {uid: {"entity": str, "id": int, "label": str, "expires": datetime}}
# ---------------------------------------------------------------------------
_pending_deletions: dict = {}
_pending_lock = threading.Lock()
DELETION_TTL_SECONDS = 120


def _set_pending_deletion(uid: int, entity: str, entity_id: int, label: str):
    with _pending_lock:
        _pending_deletions[uid] = {
            "entity": entity,
            "id": entity_id,
            "label": label,
            "expires": datetime.now(tz=None) + timedelta(seconds=DELETION_TTL_SECONDS),
        }


def _get_pending_deletion(uid: int):
    with _pending_lock:
        p = _pending_deletions.get(uid)
        if p and datetime.now(tz=None) < p["expires"]:
            return p
        _pending_deletions.pop(uid, None)
        return None


def _clear_pending_deletion(uid: int):
    with _pending_lock:
        _pending_deletions.pop(uid, None)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt(amount) -> str:
    """Format a number as Indian rupee string."""
    try:
        v = float(amount or 0)
    except Exception:
        v = 0.0
    return f"\u20b9{v:,.2f}"


def _clean(text: str) -> str:
    """Remove broken markdown symbols and raw INR labels from LLM output."""
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\bINR\s*", "\u20b9", text)
    text = re.sub(r"\bRs\.?\s*", "\u20b9", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Verified financial snapshot (read-only, used to ground the LLM)
# ---------------------------------------------------------------------------

def _snapshot(db: Session, uid: int) -> dict:
    from app.models.models import Account, Transaction, Category, Budget, SavingsGoal

    today = date.today()
    month_start = today.replace(day=1)
    prev_end = month_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)

    accounts = db.query(Account).filter(
        Account.user_id == uid, Account.is_active == 1
    ).all()

    def _txns(start, end):
        return db.query(Transaction).filter(
            Transaction.user_id == uid,
            Transaction.transaction_date >= datetime.combine(start, datetime.min.time()),
            Transaction.transaction_date < datetime.combine(end + timedelta(days=1), datetime.min.time()),
        ).all()

    cur_txns = _txns(month_start, today)
    prev_txns = _txns(prev_start, prev_end)

    cats = {c.id: c.name for c in db.query(Category).filter(Category.is_active == 1).all()}

    def _totals(txns):
        inc = sum(float(t.amount or 0) for t in txns if t.type == "income")
        exp = sum(float(t.amount or 0) for t in txns if t.type == "expense")
        return inc, exp

    cur_inc, cur_exp = _totals(cur_txns)
    prev_inc, prev_exp = _totals(prev_txns)

    cat_totals: dict = {}
    for t in cur_txns:
        if t.type == "expense":
            n = cats.get(t.category_id, "Other")
            cat_totals[n] = cat_totals.get(n, 0) + float(t.amount or 0)

    prev_cat_totals: dict = {}
    for t in prev_txns:
        if t.type == "expense":
            n = cats.get(t.category_id, "Other")
            prev_cat_totals[n] = prev_cat_totals.get(n, 0) + float(t.amount or 0)

    top_cats = sorted(
        [{"category": k, "amount": round(v, 2)} for k, v in cat_totals.items()],
        key=lambda x: -x["amount"],
    )[:10]

    largest = sorted(
        [
            {
                "id": t.id,
                "amount": float(t.amount or 0),
                "merchant": t.merchant or "Unknown",
                "category": cats.get(t.category_id, "Other"),
                "date": t.transaction_date.strftime("%Y-%m-%d") if t.transaction_date else None,
            }
            for t in cur_txns if t.type == "expense"
        ],
        key=lambda x: -x["amount"],
    )[:5]

    budgets = db.query(Budget).filter(
        Budget.user_id == uid, Budget.month == today.strftime("%Y-%m")
    ).all()

    budget_data = []
    for b in budgets:
        spent = sum(
            float(t.amount or 0)
            for t in db.query(Transaction).filter(
                Transaction.user_id == uid,
                Transaction.category_id == b.category_id,
                Transaction.type == "expense",
                Transaction.transaction_date >= datetime.combine(month_start, datetime.min.time()),
            ).all()
        )
        ba = float(b.amount or 0)
        budget_data.append({
            "id": b.id,
            "category": b.category.name if b.category else "Other",
            "budget": ba,
            "spent": round(spent, 2),
            "remaining": round(ba - spent, 2),
            "pct_used": round(spent / ba * 100, 2) if ba else 0,
        })

    goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == uid).all()
    goal_data = [
        {
            "id": g.id,
            "name": g.name,
            "target": float(g.target_amount or 0),
            "current": float(g.current_amount or 0),
            "remaining": max(0, float(g.target_amount or 0) - float(g.current_amount or 0)),
            "deadline": str(g.deadline) if g.deadline else None,
        }
        for g in goals
    ]

    total_balance = sum(float(a.balance or 0) for a in accounts)
    savings = cur_inc - cur_exp
    savings_rate = savings / cur_inc * 100 if cur_inc else 0

    exp_change = (cur_exp - prev_exp) / prev_exp * 100 if prev_exp else 0

    return {
        "as_of": str(today),
        "current_balance": round(total_balance, 2),
        "accounts": [
            {"id": a.id, "name": a.name, "type": a.type, "balance": float(a.balance or 0)}
            for a in accounts
        ],
        "current_month": today.strftime("%Y-%m"),
        "current_month_period": {"start": str(month_start), "end": str(today)},
        "previous_month_period": {"start": str(prev_start), "end": str(prev_end)},
        "income": round(cur_inc, 2),
        "expenses": round(cur_exp, 2),
        "savings": round(savings, 2),
        "savings_rate": round(savings_rate, 2),
        "prev_income": round(prev_inc, 2),
        "prev_expenses": round(prev_exp, 2),
        "expense_change_pct": round(exp_change, 2),
        "top_categories": top_cats,
        "prev_categories": [
            {"category": k, "amount": round(v, 2)} for k, v in
            sorted(prev_cat_totals.items(), key=lambda x: -x[1])
        ][:10],
        "largest_expenses": largest,
        "budgets": budget_data,
        "goals": goal_data,
    }


# ---------------------------------------------------------------------------
# MUTATION SAFETY LAYER
# ---------------------------------------------------------------------------
# Maps each tool name to the only allowed intent class.
# "read"    - never mutates data
# "txn"     - creates/updates/deletes transactions (adjusts account balance)
# "account" - creates/updates/deletes accounts
# "budget"  - creates/updates/deletes budgets
# "goal"    - creates/updates/deletes goals / contributions
# ---------------------------------------------------------------------------

_TOOL_INTENT = {
    "get_financial_overview": "read",
    "find_transactions": "read",
    "analyze_spending": "read",
    "compare_spending": "read",
    "check_budgets": "read",
    "analyze_goal": "read",
    "savings_capacity": "read",
    "affordability_check": "read",
    "get_subscriptions": "read",
    "get_health_score": "read",
    "get_forecast": "read",
    "get_anomalies": "read",
    "get_net_worth": "read",
    "get_emergency_fund": "read",
    "get_monthly_report": "read",
    "get_budget_recommendations": "read",
    "create_transaction": "txn",
    "update_transaction": "txn",
    "delete_transaction": "txn",
    "create_account": "account",
    "update_account": "account",
    "delete_account": "account",
    "create_budget": "budget",
    "update_budget": "budget",
    "delete_budget": "budget",
    "create_goal": "goal",
    "update_goal": "goal",
    "delete_goal": "goal",
    "contribute_to_goal": "goal",
}

# Keywords that indicate a transaction request (not account creation)
_TXN_KEYWORDS = re.compile(
    r"\b(expense|spent|spend|paid|pay|bought|buy|purchase|grocery|groceries|food|"
    r"bill|fee|charge|upi|cash|card|netbanking|transfer|income|salary|received|earned)\b",
    re.I,
)
_ACCOUNT_CREATE_KEYWORDS = re.compile(
    r"\b(create|open|add|new)\b.{0,30}\b(account|bank account|wallet|savings account|"
    r"credit card|investment account)\b",
    re.I,
)


def _validate_tool_call(tool_name: str, args: dict, message: str) -> str | None:
    """
    Return an error string if the tool call is unsafe, else None.

    Critical rule: if the message mentions an account as the SOURCE of a
    transaction (e.g. 'from my SBI account'), that must never trigger
    create_account. Only explicit account-creation phrasing is allowed.
    """
    if tool_name not in _TOOL_INTENT:
        return f"Unknown tool: {tool_name}"

    intent = _TOOL_INTENT[tool_name]

    # Block account creation when the message is clearly a transaction request
    if intent == "account" and tool_name == "create_account":
        if _TXN_KEYWORDS.search(message) and not _ACCOUNT_CREATE_KEYWORDS.search(message):
            return (
                "Blocked: message describes a transaction, not account creation. "
                "Use create_transaction instead."
            )

    return None


# ---------------------------------------------------------------------------
# VERIFIED TOOL EXECUTOR
# ---------------------------------------------------------------------------

def _execute_tool(db: Session, uid: int, tool_name: str, args: dict, message: str) -> dict:
    """Execute a verified FinWise tool. Never called without safety check."""
    from app.models.models import (
        Account, Transaction, Category, Budget, SavingsGoal, RecurringRule
    )

    # ---- READ TOOLS --------------------------------------------------------

    if tool_name == "get_financial_overview":
        return _snapshot(db, uid)

    if tool_name == "find_transactions":
        limit = min(int(args.get("limit", 10)), 50)
        q = db.query(Transaction).filter(Transaction.user_id == uid)
        if args.get("type"):
            q = q.filter(Transaction.type == args["type"])
        if args.get("category"):
            cats = db.query(Category).filter(
                or_(Category.user_id == uid, Category.is_system == 1),
                Category.name.ilike(f"%{args['category']}%"),
                Category.is_active == 1,
            ).all()
            if cats:
                q = q.filter(Transaction.category_id.in_([c.id for c in cats]))
        if args.get("days"):
            cutoff = date.today() - timedelta(days=int(args["days"]))
            q = q.filter(Transaction.transaction_date >= cutoff)
        txns = q.order_by(Transaction.transaction_date.desc()).limit(limit).all()
        cats_map = {c.id: c.name for c in db.query(Category).filter(Category.is_active == 1).all()}
        return {
            "transactions": [
                {
                    "id": t.id,
                    "date": t.transaction_date.strftime("%Y-%m-%d") if t.transaction_date else None,
                    "amount": float(t.amount or 0),
                    "type": t.type,
                    "merchant": t.merchant or "",
                    "category": cats_map.get(t.category_id, "Other"),
                    "description": t.description or "",
                    "payment_method": t.payment_method or "other",
                }
                for t in txns
            ],
            "count": len(txns),
        }

    if tool_name == "analyze_spending":
        today = date.today()
        days = int(args.get("days", 30))
        cutoff = today - timedelta(days=days - 1)
        txns = db.query(Transaction).filter(
            Transaction.user_id == uid,
            Transaction.type == "expense",
            Transaction.transaction_date >= cutoff,
        ).all()
        cats_map = {c.id: c.name for c in db.query(Category).filter(Category.is_active == 1).all()}
        by_cat: dict = {}
        for t in txns:
            n = cats_map.get(t.category_id, "Other")
            by_cat[n] = by_cat.get(n, 0) + float(t.amount or 0)
        total = sum(by_cat.values())
        return {
            "period_days": days,
            "total_expenses": round(total, 2),
            "by_category": sorted(
                [{"category": k, "amount": round(v, 2)} for k, v in by_cat.items()],
                key=lambda x: -x["amount"],
            ),
            "transaction_count": len(txns),
        }

    if tool_name == "compare_spending":
        today = date.today()
        cur_start = today.replace(day=1)
        prev_end = cur_start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)

        def _period_expenses(start, end):
            txns = db.query(Transaction).filter(
                Transaction.user_id == uid,
                Transaction.type == "expense",
                Transaction.transaction_date >= datetime.combine(start, datetime.min.time()),
                Transaction.transaction_date < datetime.combine(end + timedelta(days=1), datetime.min.time()),
            ).all()
            cats_map = {c.id: c.name for c in db.query(Category).filter(Category.is_active == 1).all()}
            total = sum(float(t.amount or 0) for t in txns)
            by_cat: dict = {}
            for t in txns:
                n = cats_map.get(t.category_id, "Other")
                by_cat[n] = by_cat.get(n, 0) + float(t.amount or 0)
            return round(total, 2), by_cat

        cur_total, cur_cats = _period_expenses(cur_start, today)
        prev_total, prev_cats = _period_expenses(prev_start, prev_end)

        diff = cur_total - prev_total
        pct = diff / prev_total * 100 if prev_total else 0

        all_cats = set(cur_cats) | set(prev_cats)
        cat_changes = []
        for c in all_cats:
            cur_v = cur_cats.get(c, 0)
            prev_v = prev_cats.get(c, 0)
            cat_changes.append({
                "category": c,
                "current": round(cur_v, 2),
                "previous": round(prev_v, 2),
                "change": round(cur_v - prev_v, 2),
            })
        cat_changes.sort(key=lambda x: -abs(x["change"]))

        direction = "decreased" if diff < 0 else "increased" if diff > 0 else "unchanged"
        summary = (
            f"You spent {_fmt(cur_total)} this month and {_fmt(prev_total)} last month. "
            f"Your spending {direction} by {_fmt(abs(diff))}, or {abs(pct):.1f}%."
        )

        return {
            "current_month": {"start": str(cur_start), "end": str(today), "total": cur_total},
            "previous_month": {"start": str(prev_start), "end": str(prev_end), "total": prev_total},
            "difference": round(diff, 2),
            "pct_change": round(pct, 2),
            "direction": direction,
            "category_changes": cat_changes[:8],
            "summary": summary,
        }

    if tool_name == "check_budgets":
        snap = _snapshot(db, uid)
        return {"budgets": snap["budgets"], "month": snap["current_month"]}

    if tool_name == "analyze_goal":
        goal_name = args.get("goal_name", "")
        goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == uid).all()
        goal = None
        if goal_name:
            low = goal_name.lower()
            for g in goals:
                if g.name and low in g.name.lower():
                    goal = g
                    break
        if not goal and len(goals) == 1:
            goal = goals[0]
        if not goal:
            names = [g.name for g in goals]
            return {"error": "goal_not_found", "available_goals": names}
        target = float(goal.target_amount or 0)
        current = float(goal.current_amount or 0)
        remaining = max(0, target - current)
        pct = current / target * 100 if target else 0
        monthly_needed = None
        if args.get("months"):
            months = max(1, int(args["months"]))
            monthly_needed = round(remaining / months, 2)
        elif goal.deadline:
            days_left = (goal.deadline - date.today()).days
            if days_left > 0:
                monthly_needed = round(remaining / max(days_left / 30, 1), 2)
        return {
            "id": goal.id,
            "name": goal.name,
            "target": round(target, 2),
            "current": round(current, 2),
            "remaining": round(remaining, 2),
            "progress_pct": round(pct, 2),
            "deadline": str(goal.deadline) if goal.deadline else None,
            "monthly_needed": monthly_needed,
        }

    if tool_name == "savings_capacity":
        today = date.today()
        cutoff = today - timedelta(days=90)
        txns = db.query(Transaction).filter(
            Transaction.user_id == uid,
            Transaction.transaction_date >= cutoff,
        ).all()
        inc = sum(float(t.amount or 0) for t in txns if t.type == "income") / 3
        exp = sum(float(t.amount or 0) for t in txns if t.type == "expense") / 3
        surplus = max(0, inc - exp)
        return {
            "avg_monthly_income": round(inc, 2),
            "avg_monthly_expenses": round(exp, 2),
            "monthly_surplus": round(surplus, 2),
            "annual_surplus": round(surplus * 12, 2),
        }

    if tool_name == "affordability_check":
        purchase_amount = float(args.get("amount", 0))
        accounts = db.query(Account).filter(
            Account.user_id == uid, Account.is_active == 1
        ).all()
        liquid_balance = sum(
            float(a.balance or 0) for a in accounts
            if a.type in ("bank", "cash", "wallet")
        )
        today = date.today()
        cutoff = today - timedelta(days=90)
        txns = db.query(Transaction).filter(
            Transaction.user_id == uid,
            Transaction.transaction_date >= cutoff,
        ).all()
        avg_inc = sum(float(t.amount or 0) for t in txns if t.type == "income") / 3
        avg_exp = sum(float(t.amount or 0) for t in txns if t.type == "expense") / 3
        surplus = max(0, avg_inc - avg_exp)
        balance_after = liquid_balance - purchase_amount
        # Emergency fund = 3 months of expenses
        emergency_needed = avg_exp * 3
        safe_to_spend = max(0, liquid_balance - emergency_needed)

        if purchase_amount <= 0:
            verdict = "unknown"
        elif balance_after < 0:
            verdict = "not_affordable"
        elif balance_after < emergency_needed:
            verdict = "risky"
        elif purchase_amount <= safe_to_spend:
            verdict = "affordable"
        else:
            verdict = "risky"

        return {
            "purchase_amount": round(purchase_amount, 2),
            "liquid_balance": round(liquid_balance, 2),
            "balance_after_purchase": round(balance_after, 2),
            "avg_monthly_income": round(avg_inc, 2),
            "avg_monthly_expenses": round(avg_exp, 2),
            "monthly_surplus": round(surplus, 2),
            "emergency_fund_needed": round(emergency_needed, 2),
            "safe_to_spend": round(safe_to_spend, 2),
            "verdict": verdict,
        }

    if tool_name == "get_subscriptions":
        from app.models.models import RecurringRule
        subs = db.query(RecurringRule).filter(
            RecurringRule.user_id == uid, RecurringRule.is_subscription == 1
        ).all()
        monthly = sum(
            float(s.expected_amount or 0) * 30 / s.interval_days
            for s in subs if s.expected_amount and s.interval_days
        )
        return {
            "count": len(subs),
            "monthly_cost": round(monthly, 2),
            "annual_cost": round(monthly * 12, 2),
            "subscriptions": [
                {
                    "merchant": s.merchant_pattern,
                    "amount": float(s.expected_amount or 0),
                    "interval_days": s.interval_days,
                    "next_date": str(s.next_expected_date) if s.next_expected_date else None,
                }
                for s in subs
            ],
        }

    if tool_name == "get_health_score":
        from app.services.health_score import compute_health_score
        return compute_health_score(db, uid)

    if tool_name == "get_forecast":
        from app.services.forecasting import build_forecast
        days = max(7, min(int(args.get("days", 30)), 90))
        return build_forecast(db, uid, days)

    if tool_name == "get_anomalies":
        from app.services.anomaly import detect_anomalies
        return {"anomalies": detect_anomalies(db, uid, 90)}

    if tool_name == "get_net_worth":
        accounts = db.query(Account).filter(Account.user_id == uid, Account.is_active == 1).all()
        assets = sum(float(a.balance or 0) for a in accounts if a.type not in ("loan", "credit_card"))
        liabilities = sum(abs(float(a.balance or 0)) for a in accounts if a.type in ("loan", "credit_card"))
        return {
            "assets": round(assets, 2),
            "liabilities": round(liabilities, 2),
            "net_worth": round(assets - liabilities, 2),
            "accounts": [{"name": a.name, "type": a.type, "balance": float(a.balance or 0)} for a in accounts],
        }

    if tool_name == "get_emergency_fund":
        today = date.today()
        cutoff = today - timedelta(days=90)
        txns = db.query(Transaction).filter(
            Transaction.user_id == uid, Transaction.type == "expense",
            Transaction.transaction_date >= cutoff,
        ).all()
        monthly = sum(float(t.amount or 0) for t in txns) / 3 if txns else 0
        balances = sum(
            float(a.balance or 0)
            for a in db.query(Account).filter(Account.user_id == uid, Account.is_active == 1).all()
        )
        months = balances / monthly if monthly else 0
        return {
            "monthly_essential_estimate": round(monthly, 2),
            "available_balance": round(balances, 2),
            "months_covered": round(months, 2),
            "target_3_months": round(monthly * 3, 2),
            "target_6_months": round(monthly * 6, 2),
        }

    if tool_name == "get_monthly_report":
        today = date.today()
        start = today.replace(day=1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)

        def _totals(a, b):
            txns = db.query(Transaction).filter(
                Transaction.user_id == uid,
                Transaction.transaction_date >= a,
                Transaction.transaction_date < datetime.combine(b + timedelta(days=1), datetime.min.time()),
            ).all()
            return (
                sum(float(t.amount or 0) for t in txns if t.type == "income"),
                sum(float(t.amount or 0) for t in txns if t.type == "expense"),
            )

        inc, exp = _totals(start, today)
        pinc, pexp = _totals(prev_start, prev_end)
        return {
            "month": today.strftime("%Y-%m"),
            "income": round(inc, 2),
            "expenses": round(exp, 2),
            "savings": round(inc - exp, 2),
            "savings_rate": round((inc - exp) / inc * 100, 2) if inc else 0,
            "expense_change_pct": round((exp - pexp) / pexp * 100, 2) if pexp else 0,
            "income_change_pct": round((inc - pinc) / pinc * 100, 2) if pinc else 0,
        }

    if tool_name == "get_budget_recommendations":
        today = date.today()
        cutoff = today - timedelta(days=90)
        txns = db.query(Transaction).filter(
            Transaction.user_id == uid, Transaction.type == "expense",
            Transaction.transaction_date >= cutoff,
        ).all()
        cats_map = {c.id: c.name for c in db.query(Category).filter(Category.is_active == 1).all()}
        groups: dict = {}
        for t in txns:
            name = cats_map.get(t.category_id, "Other")
            groups[name] = groups.get(name, 0) + float(t.amount or 0)
        return [
            {
                "category": name,
                "average_monthly": round(total / 3, 2),
                "recommended_budget": round(total / 3 * 1.10, 2),
                "buffer": round(total / 3 * 0.10, 2),
                "reason": "90-day average plus a 10% variability buffer",
            }
            for name, total in sorted(groups.items(), key=lambda x: -x[1])[:12]
        ]

    # ---- WRITE TOOLS -------------------------------------------------------

    if tool_name == "create_transaction":
        amount = Decimal(str(args["amount"]))
        txn_type = args["type"]  # "income" or "expense"

        # Resolve account
        account_name = args.get("account_name", "")
        accounts = db.query(Account).filter(
            Account.user_id == uid, Account.is_active == 1
        ).all()
        account = None
        if account_name:
            low = account_name.lower()
            for a in accounts:
                if a.name and low in a.name.lower():
                    account = a
                    break
        if not account and len(accounts) == 1:
            account = accounts[0]
        if not account:
            names = [a.name for a in accounts]
            if len(names) > 1:
                return {"error": "ambiguous_account", "available_accounts": names}
            return {"error": "no_account_found"}

        # Resolve category
        cat_name = args.get("category", "")
        category_id = None
        if cat_name:
            cat = db.query(Category).filter(
                or_(Category.user_id == uid, Category.is_system == 1),
                Category.name.ilike(f"%{cat_name}%"),
                Category.is_active == 1,
            ).first()
            if cat:
                category_id = cat.id

        # Payment method
        pm_raw = (args.get("payment_method") or "other").lower()
        valid_pm = {"upi", "card", "cash", "netbanking", "other"}
        payment_method = pm_raw if pm_raw in valid_pm else "other"

        txn_date = datetime.now()
        if args.get("date"):
            try:
                txn_date = datetime.strptime(args["date"], "%Y-%m-%d")
            except Exception:
                pass

        txn = Transaction(
            user_id=uid,
            account_id=account.id,
            amount=amount,
            type=txn_type,
            category_id=category_id,
            merchant=args.get("merchant") or args.get("description") or "",
            description=args.get("description") or "",
            transaction_date=txn_date,
            payment_method=payment_method,
        )
        db.add(txn)

        if txn_type == "expense":
            account.balance = Decimal(str(account.balance)) - amount
        else:
            account.balance = Decimal(str(account.balance)) + amount

        db.commit()
        db.refresh(txn)

        return {
            "success": True,
            "transaction_id": txn.id,
            "amount": float(amount),
            "type": txn_type,
            "account": account.name,
            "new_account_balance": float(account.balance),
            "payment_method": payment_method,
            "mutations": ["transactions", "accounts"],
        }

    if tool_name == "update_transaction":
        txn_id = int(args["transaction_id"])
        txn = db.query(Transaction).filter(
            Transaction.id == txn_id, Transaction.user_id == uid
        ).first()
        if not txn:
            return {"error": "transaction_not_found"}

        old_amount = Decimal(str(txn.amount))
        old_type = txn.type
        account = db.query(Account).filter(Account.id == txn.account_id).first()

        if "amount" in args:
            new_amount = Decimal(str(args["amount"]))
            if account:
                # Reverse old effect
                if old_type == "expense":
                    account.balance += old_amount
                else:
                    account.balance -= old_amount
                # Apply new effect
                if old_type == "expense":
                    account.balance -= new_amount
                else:
                    account.balance += new_amount
            txn.amount = new_amount

        if "merchant" in args:
            txn.merchant = args["merchant"]
        if "description" in args:
            txn.description = args["description"]
        if "category" in args:
            cat = db.query(Category).filter(
                or_(Category.user_id == uid, Category.is_system == 1),
                Category.name.ilike(f"%{args['category']}%"),
                Category.is_active == 1,
            ).first()
            if cat:
                txn.category_id = cat.id

        db.commit()
        return {"success": True, "transaction_id": txn_id, "mutations": ["transactions", "accounts"]}

    if tool_name == "delete_transaction":
        txn_id = int(args["transaction_id"])
        txn = db.query(Transaction).filter(
            Transaction.id == txn_id, Transaction.user_id == uid
        ).first()
        if not txn:
            return {"error": "transaction_not_found"}
        label = f"{txn.merchant or 'transaction'} {_fmt(txn.amount)}"
        _set_pending_deletion(uid, "transaction", txn_id, label)
        return {
            "pending_confirmation": True,
            "message": f"Are you sure you want to delete the transaction: {label}? Reply 'yes, confirm' to proceed or 'cancel' to abort.",
        }

    if tool_name == "create_account":
        account = Account(
            user_id=uid,
            name=args["name"].strip(),
            type=args["type"],
            balance=Decimal(str(args.get("balance", 0))),
            currency="INR",
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return {
            "success": True,
            "account_id": account.id,
            "name": account.name,
            "balance": float(account.balance),
            "mutations": ["accounts"],
        }

    if tool_name == "update_account":
        acct_id = int(args["account_id"])
        account = db.query(Account).filter(
            Account.id == acct_id, Account.user_id == uid
        ).first()
        if not account:
            return {"error": "account_not_found"}
        if "name" in args:
            account.name = args["name"]
        if "balance" in args:
            account.balance = Decimal(str(args["balance"]))
        db.commit()
        return {"success": True, "account_id": acct_id, "mutations": ["accounts"]}

    if tool_name == "delete_account":
        acct_id = int(args["account_id"])
        account = db.query(Account).filter(
            Account.id == acct_id, Account.user_id == uid
        ).first()
        if not account:
            return {"error": "account_not_found"}
        _set_pending_deletion(uid, "account", acct_id, account.name)
        return {
            "pending_confirmation": True,
            "message": f"Are you sure you want to delete account '{account.name}'? Reply 'yes, confirm' to proceed or 'cancel' to abort.",
        }

    if tool_name == "create_budget":
        cat = db.query(Category).filter(
            or_(Category.user_id == uid, Category.is_system == 1),
            Category.name.ilike(f"%{args['category']}%"),
            Category.is_active == 1,
        ).first()
        if not cat:
            return {"error": "category_not_found"}
        month = args.get("month") or date.today().strftime("%Y-%m")
        existing = db.query(Budget).filter(
            Budget.user_id == uid,
            Budget.category_id == cat.id,
            Budget.month == month,
        ).first()
        if existing:
            existing.amount = Decimal(str(args["amount"]))
            db.commit()
            return {"success": True, "budget_id": existing.id, "action": "updated", "mutations": ["budgets"]}
        budget = Budget(
            user_id=uid,
            category_id=cat.id,
            amount=Decimal(str(args["amount"])),
            month=month,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        return {"success": True, "budget_id": budget.id, "action": "created", "mutations": ["budgets"]}

    if tool_name == "update_budget":
        budget_id = int(args["budget_id"])
        budget = db.query(Budget).filter(
            Budget.id == budget_id, Budget.user_id == uid
        ).first()
        if not budget:
            return {"error": "budget_not_found"}
        if "amount" in args:
            budget.amount = Decimal(str(args["amount"]))
        db.commit()
        return {"success": True, "budget_id": budget_id, "mutations": ["budgets"]}

    if tool_name == "delete_budget":
        budget_id = int(args["budget_id"])
        budget = db.query(Budget).filter(
            Budget.id == budget_id, Budget.user_id == uid
        ).first()
        if not budget:
            return {"error": "budget_not_found"}
        label = f"{budget.category.name if budget.category else 'budget'} {budget.month}"
        _set_pending_deletion(uid, "budget", budget_id, label)
        return {
            "pending_confirmation": True,
            "message": f"Are you sure you want to delete the budget for '{label}'? Reply 'yes, confirm' to proceed.",
        }

    if tool_name == "create_goal":
        goal = SavingsGoal(
            user_id=uid,
            name=args["name"].strip(),
            target_amount=Decimal(str(args["target_amount"])),
            current_amount=Decimal("0"),
            deadline=args.get("deadline"),
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return {"success": True, "goal_id": goal.id, "name": goal.name, "mutations": ["goals"]}

    if tool_name == "update_goal":
        goal_id = int(args["goal_id"])
        goal = db.query(SavingsGoal).filter(
            SavingsGoal.id == goal_id, SavingsGoal.user_id == uid
        ).first()
        if not goal:
            return {"error": "goal_not_found"}
        if "name" in args:
            goal.name = args["name"]
        if "target_amount" in args:
            goal.target_amount = Decimal(str(args["target_amount"]))
        if "deadline" in args:
            goal.deadline = args["deadline"]
        db.commit()
        return {"success": True, "goal_id": goal_id, "mutations": ["goals"]}

    if tool_name == "delete_goal":
        goal_id = int(args["goal_id"])
        goal = db.query(SavingsGoal).filter(
            SavingsGoal.id == goal_id, SavingsGoal.user_id == uid
        ).first()
        if not goal:
            return {"error": "goal_not_found"}
        _set_pending_deletion(uid, "goal", goal_id, goal.name)
        return {
            "pending_confirmation": True,
            "message": f"Are you sure you want to delete goal '{goal.name}'? Reply 'yes, confirm' to proceed.",
        }

    if tool_name == "contribute_to_goal":
        goal_name = args.get("goal_name", "")
        goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == uid).all()
        goal = None
        if goal_name:
            low = goal_name.lower()
            for g in goals:
                if g.name and low in g.name.lower():
                    goal = g
                    break
        if not goal and len(goals) == 1:
            goal = goals[0]
        if not goal:
            return {"error": "goal_not_found", "available_goals": [g.name for g in goals]}
        amount = Decimal(str(args["amount"]))
        goal.current_amount = Decimal(str(goal.current_amount)) + amount
        db.commit()
        target = float(goal.target_amount or 0)
        current = float(goal.current_amount)
        pct = current / target * 100 if target else 0
        return {
            "success": True,
            "goal_name": goal.name,
            "contributed": float(amount),
            "current_amount": current,
            "target_amount": target,
            "progress_pct": round(pct, 2),
            "mutations": ["goals"],
        }

    return {"error": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# OLLAMA TOOL DEFINITIONS
# ---------------------------------------------------------------------------

OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_financial_overview",
            "description": "Get the user's complete financial overview: balances, income, expenses, savings, budgets, goals, top categories.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_transactions",
            "description": "Find and list the user's transactions with optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["income", "expense", "transfer"]},
                    "category": {"type": "string"},
                    "days": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_spending",
            "description": "Analyze the user's spending by category for a given period.",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_spending",
            "description": "Compare spending between the current calendar month and the previous full calendar month.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_budgets",
            "description": "Get the user's current month budget status: budget amounts, spent, remaining.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_goal",
            "description": "Analyze a specific savings goal: progress, remaining amount, monthly savings needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_name": {"type": "string"},
                    "months": {"type": "integer", "description": "Number of months to reach the goal"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "savings_capacity",
            "description": "Calculate the user's monthly savings capacity based on recent income and expenses.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "affordability_check",
            "description": "Check if the user can afford a purchase given their liquid balance, income, expenses, emergency fund and goals.",
            "parameters": {
                "type": "object",
                "properties": {"amount": {"type": "number"}},
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_subscriptions",
            "description": "Get the user's detected recurring subscriptions and their monthly/annual cost.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_health_score",
            "description": "Get the user's financial health score with factor breakdown.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Get a cash-flow forecast for the next N days.",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomalies",
            "description": "Get unusual or duplicate transactions detected in the last 90 days.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_net_worth",
            "description": "Calculate the user's net worth: total assets minus liabilities (loans, credit cards).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_emergency_fund",
            "description": "Check the user's emergency fund coverage: how many months of expenses their current balance covers.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_report",
            "description": "Get the current month's financial report: income, expenses, savings, and month-over-month changes.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_recommendations",
            "description": "Get data-driven budget recommendations based on the user's last 90 days of spending.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_transaction",
            "description": (
                "Record a new income or expense transaction. "
                "Use this when the user says they spent money, paid for something, bought something, "
                "or received income. NEVER use this to create an account. "
                "account_name is the SOURCE account for the transaction, not a new account to create."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "type": {"type": "string", "enum": ["income", "expense"]},
                    "account_name": {"type": "string", "description": "Name of the existing account to debit/credit"},
                    "category": {"type": "string"},
                    "merchant": {"type": "string"},
                    "description": {"type": "string"},
                    "payment_method": {"type": "string", "enum": ["upi", "card", "cash", "netbanking", "other"]},
                    "date": {"type": "string", "description": "YYYY-MM-DD, defaults to today"},
                },
                "required": ["amount", "type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_transaction",
            "description": "Update an existing transaction by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "integer"},
                    "amount": {"type": "number"},
                    "merchant": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["transaction_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_transaction",
            "description": "Request deletion of a transaction. Requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {"transaction_id": {"type": "integer"}},
                "required": ["transaction_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_account",
            "description": (
                "Create a new financial account. "
                "ONLY use this when the user explicitly says 'create account', 'add account', or 'open account'. "
                "NEVER use this when the user mentions an account as the source of a transaction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["bank", "cash", "credit_card", "wallet", "investment", "loan"]},
                    "balance": {"type": "number"},
                },
                "required": ["name", "type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_account",
            "description": "Update an existing account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "balance": {"type": "number"},
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_account",
            "description": "Request deletion of an account. Requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "integer"}},
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_budget",
            "description": "Create or update a monthly budget for a category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "amount": {"type": "number"},
                    "month": {"type": "string", "description": "YYYY-MM"},
                },
                "required": ["category", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_budget",
            "description": "Update an existing budget by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget_id": {"type": "integer"},
                    "amount": {"type": "number"},
                },
                "required": ["budget_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_budget",
            "description": "Request deletion of a budget. Requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {"budget_id": {"type": "integer"}},
                "required": ["budget_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": "Create a new savings goal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "target_amount": {"type": "number"},
                    "deadline": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["name", "target_amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal",
            "description": "Update an existing savings goal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "target_amount": {"type": "number"},
                    "deadline": {"type": "string"},
                },
                "required": ["goal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_goal",
            "description": "Request deletion of a savings goal. Requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {"goal_id": {"type": "integer"}},
                "required": ["goal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "contribute_to_goal",
            "description": "Add an amount to a savings goal's current progress.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_name": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["amount"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# OLLAMA STATUS CHECK
# ---------------------------------------------------------------------------

def check_ollama_status() -> bool:
    """Return True if Ollama is reachable and the configured model is available."""
    if not settings.OLLAMA_ENABLED:
        return False
    try:
        with httpx.Client(timeout=5) as client:
            r = client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
            return any(settings.OLLAMA_MODEL in m for m in models)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are FinWise AI, a privacy-first personal finance assistant for Indian users.

CORE RULE — CHECK DATA BEFORE ASKING:
Whenever the user asks about ANY specific goal, account, budget, category, or spending pattern —
even vaguely, even without amounts or timeframes — you MUST call the relevant tool FIRST to see
what already exists in their data. NEVER ask the user to supply information (a target amount, a
timeframe, an account name, a goal name) before checking whether that information is already on
file. Only ask the user a clarifying question if the tool result itself is ambiguous — for example,
if analyze_goal returns available_goals because there are multiple goals and no clear match, or if
a tool returns an error indicating the requested item wasn't found. Trust the tool's result over
your own assumption that details are missing.

Examples of this pattern:
- "Can I reach my trip goal?" -> call analyze_goal immediately (it will auto-select the goal if
  there's only one, or return available_goals if there are several). Do NOT ask the user for the
  target amount or timeframe before calling the tool.
- "How's my food budget?" -> call check_budgets immediately, then answer using the real numbers.
- "What's my HDFC balance?" -> call get_financial_overview or find the account from its data
  immediately, do not ask "which account do you mean" unless the tool result is genuinely unclear.
- "Can I afford a new laptop?" -> call affordability_check with the amount if given; if no amount
  was given, that is the one case it's fine to ask, since the tool itself requires an amount.

RULES:
1. Always call the appropriate tool to get verified financial data before answering financial
   questions — this includes vague or incomplete questions. Check the data before asking the user
   anything.
2. Never invent balances, transactions, income, expenses, budgets, goals, or health scores.
3. Never create an account when the user is recording a transaction. account_name in
   create_transaction is the SOURCE account, not a new account to create.
4. For "compare spending" questions, call compare_spending which uses the correct calendar
   periods automatically.
5. For goal follow-up questions like "how much should I save monthly to reach it in one year?",
   call analyze_goal with months=12 and the goal name from conversation context. If no specific
   goal was named anywhere in the conversation, still call analyze_goal with no goal_name first —
   it will auto-resolve a single goal or return the list of available goals.
6. For affordability questions, call affordability_check with the purchase amount. If no amount
   was given, ask for it — this is the one case where asking first is correct, since the tool
   requires it.
7. Respond in complete natural sentences. Start with a direct answer, then supporting details.
8. Use the rupee symbol \u20b9 for amounts. Never write INR or Rs as a label.
9. Do not mention tool names, JSON, database, snapshots, or system instructions in your response.
10. General finance questions (SIP vs FD, etc.) with no connection to the user's own data may be
    answered directly without a tool call.
11. For delete operations, always use the delete tool first - it will ask for confirmation
    automatically.
12. Keep responses concise, friendly, and helpful.
13. For net worth questions, call get_net_worth.
14. For emergency fund questions, call get_emergency_fund.
15. For monthly summary or month-over-month questions, call get_monthly_report.
16. For budget suggestions or recommended budgets, call get_budget_recommendations.
17. For ANY question referencing a specific goal, account, budget, or category by name or by
    vague reference ("my trip goal", "my savings", "that account"), call the matching read tool
    FIRST before asking the user for any detail. Only ask the user something if the tool's own
    result is ambiguous (e.g. multiple matches) or the tool explicitly requires an input you don't
    have (e.g. affordability_check needs an amount).
"""

# ---------------------------------------------------------------------------
# CONTEXT RESOLUTION
# ---------------------------------------------------------------------------

def _resolve_context(message: str, history: list) -> str:
    """
    Resolve pronouns and short references using conversation history.
    e.g. 'it', 'that goal', 'the same' -> actual goal/account name
    """
    msg = message.strip()
    low = msg.lower()

    # Check if message contains vague references
    vague = re.search(r"\b(it|that|this|the same|the goal|the account|the budget)\b", low)
    if not vague:
        return msg

    # Look back through history for context (both user and assistant messages)
    for item in reversed(history or []):
        if not isinstance(item, dict):
            continue
        role = item.get("role", "")
        if role not in ("user", "assistant"):
            continue
        prev = item.get("content", "")
        if not prev or prev == msg:
            continue

        # Extract goal name from previous message
        goal_match = re.search(
            r"\b(emergency fund|vacation|laptop|phone|car|house|wedding|education|"
            r"retirement|travel|[A-Z][a-z]+ (?:fund|goal|savings))\b",
            prev, re.I
        )
        if goal_match and re.search(r"\b(goal|saving|fund|reach|it)\b", low):
            replacement = goal_match.group(0)
            return re.sub(r"\b(it|that goal|this goal|the goal)\b", replacement, msg, flags=re.I)

        # Extract account name from previous message
        acct_match = re.search(
            r"\b(hdfc|sbi|icici|axis|kotak|paytm|gpay|phonepe|[A-Z][a-z]+ (?:savings|bank|wallet|account))\b",
            prev, re.I
        )
        if acct_match and re.search(r"\b(account|balance)\b", low):
            replacement = acct_match.group(0)
            return re.sub(r"\b(it|that account|this account|the account)\b", replacement, msg, flags=re.I)

    return msg


# ---------------------------------------------------------------------------
# CONFIRMATION HANDLER
# ---------------------------------------------------------------------------

def _handle_confirmation(db: Session, uid: int, message: str) -> dict | None:
    """Handle yes/cancel for pending deletions. Returns response dict or None."""
    from app.models.models import Account, Transaction, Budget, SavingsGoal

    low = message.strip().lower()
    is_confirm = bool(re.search(r"\b(yes|confirm|yes confirm|proceed|delete it|go ahead)\b", low))
    is_cancel = bool(re.search(r"\b(no|cancel|abort|stop|never mind|nevermind)\b", low))

    if not is_confirm and not is_cancel:
        return None

    pending = _get_pending_deletion(uid)
    if not pending:
        return None

    if is_cancel:
        _clear_pending_deletion(uid)
        return {
            "answer_text": "Deletion cancelled. No data was changed.",
            "data_summary": {},
            "suggestions": [],
            "mutations": [],
        }

    # Execute the deletion
    entity = pending["entity"]
    entity_id = pending["id"]
    label = pending["label"]
    _clear_pending_deletion(uid)

    try:
        if entity == "transaction":
            txn = db.query(Transaction).filter(
                Transaction.id == entity_id, Transaction.user_id == uid
            ).first()
            if txn:
                account = db.query(Account).filter(Account.id == txn.account_id).first()
                if account:
                    if txn.type == "expense":
                        account.balance = Decimal(str(account.balance)) + Decimal(str(txn.amount))
                    else:
                        account.balance = Decimal(str(account.balance)) - Decimal(str(txn.amount))
                db.delete(txn)
                db.commit()
            return {
                "answer_text": f"Done. The transaction '{label}' has been deleted and the account balance has been updated.",
                "data_summary": {},
                "suggestions": [],
                "mutations": ["transactions", "accounts"],
            }

        if entity == "account":
            account = db.query(Account).filter(
                Account.id == entity_id, Account.user_id == uid
            ).first()
            if account:
                account.is_active = 0
                db.commit()
            return {
                "answer_text": f"Done. Account '{label}' has been deactivated.",
                "data_summary": {},
                "suggestions": [],
                "mutations": ["accounts"],
            }

        if entity == "budget":
            budget = db.query(Budget).filter(
                Budget.id == entity_id, Budget.user_id == uid
            ).first()
            if budget:
                db.delete(budget)
                db.commit()
            return {
                "answer_text": f"Done. The budget for '{label}' has been deleted.",
                "data_summary": {},
                "suggestions": [],
                "mutations": ["budgets"],
            }

        if entity == "goal":
            goal = db.query(SavingsGoal).filter(
                SavingsGoal.id == entity_id, SavingsGoal.user_id == uid
            ).first()
            if goal:
                db.delete(goal)
                db.commit()
            return {
                "answer_text": f"Done. The goal '{label}' has been deleted.",
                "data_summary": {},
                "suggestions": [],
                "mutations": ["goals"],
            }

    except Exception as exc:
        db.rollback()
        return {
            "answer_text": f"Something went wrong while deleting: {exc}",
            "data_summary": {},
            "suggestions": [],
            "mutations": [],
        }

    return None


# ---------------------------------------------------------------------------
# OLLAMA TOOL-CALLING ENGINE
# ---------------------------------------------------------------------------


def _call_ollama_with_tools(
    db: Session,
    uid: int,
    message: str,
    history: list,
) -> dict:
    """
    Full Ollama tool-calling loop.
    1. Send message + tools to Ollama
    2. Ollama selects a tool
    3. Safety layer validates the selection
    4. Backend executes the tool
    5. Result sent back to Ollama
    6. Ollama generates natural response
    """
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    # Build message list
    msgs = []
    for item in (history or [])[-10:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
            content = item.get("content", "")
            if content:
                msgs.append({"role": item["role"], "content": str(content)})

    msgs.append({"role": "user", "content": message})

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [{"role": "system", "content": _SYSTEM_PROMPT}] + msgs,
        "tools": OLLAMA_TOOLS,
        "stream": False,
        "options": {"temperature": 0.1},
    }

    with httpx.Client(timeout=300) as client:
        resp = client.post(f"{base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

    # ------------------------------------------------------------------
    # DEBUG — remove once diagnosed
    # ------------------------------------------------------------------
    print("=" * 80)
    print("MODEL BEING USED:", settings.OLLAMA_MODEL)
    print("RAW OLLAMA RESPONSE:")
    print(json.dumps(data, indent=2, default=str))
    print("=" * 80)
    # ------------------------------------------------------------------

    msg_obj = data.get("message", {})
    tool_calls = msg_obj.get("tool_calls") or []

    # ------------------------------------------------------------------
    # DEBUG — remove once diagnosed
    # ------------------------------------------------------------------
    print("TOOL CALLS RECEIVED:", tool_calls)
    print("PLAIN CONTENT (if no tool calls):", msg_obj.get("content", ""))
    print("=" * 80)
    # ------------------------------------------------------------------

    mutations: list = []

    # If no tool calls, return the text response directly
    if not tool_calls:
        text = _clean(msg_obj.get("content", "").strip())
        if not text:
            raise RuntimeError("Ollama returned empty response with no tool calls")
        return {"answer_text": text, "data_summary": {}, "suggestions": [], "mutations": []}

    # Execute tool calls
    tool_results = []
    for call in tool_calls:
        fn = call.get("function", {})
        tool_name = fn.get("name", "")
        raw_args = fn.get("arguments", {})
        args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args or "{}")

        # Safety validation
        err = _validate_tool_call(tool_name, args, message)
        if err:
            tool_results.append({
                "role": "tool",
                "content": json.dumps({"error": err, "blocked": True}),
            })
            continue

        try:
            result = _execute_tool(db, uid, tool_name, args, message)
        except Exception as exc:
            db.rollback()
            result = {"error": str(exc)}

        # Track mutations for frontend cache invalidation
        if isinstance(result, dict):
            mutations.extend(result.get("mutations", []))
            # If pending confirmation, return immediately without second LLM call
            if result.get("pending_confirmation"):
                return {
                    "answer_text": result["message"],
                    "data_summary": {},
                    "suggestions": [],
                    "mutations": [],
                }

        tool_results.append({
            "role": "tool",
            "content": json.dumps(result, default=str),
        })

    # Send tool results back to Ollama for natural language response
    follow_up_msgs = (
        [{"role": "system", "content": _SYSTEM_PROMPT}]
        + msgs
        + [{"role": "assistant", "content": "", "tool_calls": tool_calls}]
        + tool_results
    )

    follow_payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": follow_up_msgs,
        "stream": False,
        "options": {"temperature": 0.1},
    }

    with httpx.Client(timeout=300) as client:
        resp2 = client.post(f"{base_url}/api/chat", json=follow_payload)
        resp2.raise_for_status()
        data2 = resp2.json()

    text = _clean(data2.get("message", {}).get("content", "").strip())
    if not text:
        # Fallback: summarize tool result directly
        if tool_results:
            try:
                result_data = json.loads(tool_results[0]["content"])
                text = _summarize_tool_result(tool_results[0].get("_tool_name", ""), result_data)
            except Exception:
                text = "I retrieved your financial data but could not generate a response."

    return {
        "answer_text": text,
        "data_summary": {},
        "suggestions": [],
        "mutations": list(set(mutations)),
    }
def answer_with_llm(
    db: Session,
    uid: int,
    message: str,
    history: list | None = None,
) -> dict:
    """
    Main entry point for the AI assistant.
    """
    history = history or []

    confirmation_result = _handle_confirmation(db, uid, message)
    if confirmation_result is not None:
        return confirmation_result

    resolved_message = _resolve_context(message, history)

    if settings.OLLAMA_ENABLED:
        try:
            return _call_ollama_with_tools(db, uid, resolved_message, history)
        except httpx.ConnectError:
            return {
                "answer_text": (
                    "I couldn't connect to the local FinWise AI, so I did not change any financial data. "
                    "Please make sure Ollama is running with: ollama serve\n"
                    f"Then ensure the model is available: ollama pull {settings.OLLAMA_MODEL}"
                ),
                "data_summary": {},
                "suggestions": [],
                "mutations": [],
                "ollama_offline": True,
            }
        except Exception as exc:
            # ------------------------------------------------------------
            # DEBUG — remove once diagnosed
            # ------------------------------------------------------------
            import traceback
            print("=" * 80)
            print("CHAT ERROR:", repr(exc))
            traceback.print_exc()
            print("=" * 80)
            # ------------------------------------------------------------
            err_str = str(exc)
            if "connect" in err_str.lower() or "refused" in err_str.lower():
                return {
                    "answer_text": (
                        "I couldn't connect to the local FinWise AI, so I did not change any financial data. "
                        "Please make sure Ollama is running and try again."
                    ),
                    "data_summary": {},
                    "suggestions": [],
                    "mutations": [],
                    "ollama_offline": True,
                }
            return {
                "answer_text": (
                    "The AI assistant encountered an error and did not modify any data. "
                    "Please try again."
                ),
                "data_summary": {},
                "suggestions": [],
                "mutations": [],
            }

    return {
        "answer_text": (
            "The local AI assistant is currently disabled. "
            "Set OLLAMA_ENABLED=true in backend/.env and ensure Ollama is running."
        ),
        "data_summary": {},
        "suggestions": [],
        "mutations": [],
    }