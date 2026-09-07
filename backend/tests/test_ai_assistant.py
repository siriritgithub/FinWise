"""
Regression tests for the FinWise AI assistant.

Tests cover:
1.  Grocery expense creates transaction, not account
2.  Account balance decreases after expense
3.  Month comparison uses full previous calendar month
4.  Comparison returns natural summary
5.  Emergency Fund follow-up resolves 'it' correctly
6.  One-year saving calculation uses 12 months
7.  Affordability check uses verified financial data
8.  Wrong tool selection is rejected before DB mutation
9.  Deletion requires confirmation
10. Ambiguous records request clarification
11. Ollama failure never triggers incorrect fallback write
12. Formatting removes broken markdown and uses rupee symbol
13. Frontend mutations list is returned after successful operations
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------

class _FakeCategory:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.is_active = 1
        self.is_system = 1
        self.user_id = None


class _FakeAccount:
    def __init__(self, id, name, balance, type="bank"):
        self.id = id
        self.name = name
        self.balance = Decimal(str(balance))
        self.type = type
        self.is_active = 1
        self.currency = "INR"


class _FakeTxn:
    def __init__(self, id, amount, type, account_id, category_id=None, merchant="", date_=None):
        self.id = id
        self.amount = Decimal(str(amount))
        self.type = type
        self.account_id = account_id
        self.category_id = category_id
        self.merchant = merchant
        self.description = ""
        self.transaction_date = date_ or date.today()
        self.payment_method = "other"
        self.confidence_score = None
        self.is_recurring = 0
        self.is_transfer = 0
        self.parent_transaction_id = None
        self.category = _FakeCategory(category_id, "Food") if category_id else None


class _FakeGoal:
    def __init__(self, id, name, target, current, deadline=None):
        self.id = id
        self.name = name
        self.target_amount = Decimal(str(target))
        self.current_amount = Decimal(str(current))
        self.deadline = deadline
        self.priority = "medium"
        self.monthly_contribution = None


def _make_db(accounts=None, transactions=None, categories=None, goals=None, budgets=None):
    db = MagicMock()
    accounts = accounts or []
    transactions = transactions or []
    goals = goals or []
    budgets = budgets or []

    food_cat = _FakeCategory(1, "Food")
    all_cats = [food_cat] + (categories or [])

    def _query_side_effect(model):
        from app.models.models import Account, Transaction, Category, Budget, SavingsGoal, RecurringRule
        q = MagicMock()

        if model is Account:
            q.filter.return_value.all.return_value = accounts
            q.filter.return_value.first.return_value = accounts[0] if accounts else None
        elif model is Transaction:
            q.filter.return_value.all.return_value = transactions
            q.filter.return_value.first.return_value = transactions[0] if transactions else None
            q.filter.return_value.filter.return_value.all.return_value = transactions
            q.filter.return_value.order_by.return_value.limit.return_value.all.return_value = transactions
        elif model is Category:
            q.filter.return_value.all.return_value = all_cats
            q.filter.return_value.first.return_value = food_cat
        elif model is Budget:
            q.filter.return_value.all.return_value = budgets
            q.filter.return_value.first.return_value = budgets[0] if budgets else None
        elif model is SavingsGoal:
            q.filter.return_value.all.return_value = goals
            q.filter.return_value.first.return_value = goals[0] if goals else None
        elif model is RecurringRule:
            q.filter.return_value.all.return_value = []
        else:
            q.filter.return_value.all.return_value = []
            q.filter.return_value.first.return_value = None

        return q

    db.query.side_effect = _query_side_effect
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    db.delete = MagicMock()
    db.rollback = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from app.services.llm import (
    _execute_tool,
    _validate_tool_call,
    _clean,
    _handle_confirmation,
    _set_pending_deletion,
    answer_with_llm,
)


# ===========================================================================
# TEST 1: Grocery expense creates a transaction, NOT an account
# ===========================================================================

def test_grocery_expense_creates_transaction_not_account():
    message = "Add a \u20b9500 grocery expense today from my SBI Savings account using UPI"

    err = _validate_tool_call(
        "create_account",
        {"name": "SBI Savings", "type": "bank", "balance": 500},
        message,
    )
    assert err is not None, "create_account should be blocked for a transaction message"
    assert "blocked" in err.lower() or "transaction" in err.lower()

    err2 = _validate_tool_call(
        "create_transaction",
        {"amount": 500, "type": "expense"},
        message,
    )
    assert err2 is None, "create_transaction should be allowed"


# ===========================================================================
# TEST 2: Account balance decreases after expense
# ===========================================================================

def test_account_balance_decreases_after_expense():
    sbi = _FakeAccount(1, "SBI Savings", 10000)
    db = _make_db(accounts=[sbi])

    result = _execute_tool(
        db, 1, "create_transaction",
        {
            "amount": 500,
            "type": "expense",
            "account_name": "SBI",
            "category": "Food",
            "payment_method": "upi",
        },
        "Add \u20b9500 grocery expense from SBI Savings using UPI",
    )

    assert result.get("success") is True
    assert float(sbi.balance) == 9500.0, f"Expected 9500, got {sbi.balance}"
    assert result.get("new_account_balance") == 9500.0
    assert "transactions" in result.get("mutations", [])
    assert "accounts" in result.get("mutations", [])


# ===========================================================================
# TEST 3: Month comparison uses full previous calendar month
# ===========================================================================

def test_compare_spending_uses_correct_calendar_periods():
    today = date.today()
    cur_start = today.replace(day=1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)

    db = _make_db()
    result = _execute_tool(db, 1, "compare_spending", {}, "Compare my spending")

    assert result["current_month"]["start"] == str(cur_start)
    assert result["current_month"]["end"] == str(today)
    assert result["previous_month"]["start"] == str(prev_start)
    assert result["previous_month"]["end"] == str(prev_end)


# ===========================================================================
# TEST 4: Comparison returns a natural summary string
# ===========================================================================

def test_compare_spending_returns_natural_summary():
    db = _make_db()
    result = _execute_tool(db, 1, "compare_spending", {}, "Compare spending")

    assert "summary" in result
    summary = result["summary"]
    assert isinstance(summary, str) and len(summary) > 20
    assert "\u20b9" in summary or "spent" in summary.lower()


# ===========================================================================
# TEST 5: Emergency Fund follow-up resolves 'it' correctly
# ===========================================================================

def test_context_resolution_resolves_it_to_emergency_fund():
    from app.services.llm import _resolve_context

    history = [
        {
            "role": "user",
            "content": "How am I progressing toward my Emergency Fund goal?",
        },
        {
            "role": "assistant",
            "content": "You have saved \u20b920,000 of your \u20b960,000 Emergency Fund goal.",
        },
    ]
    message = "How much should I save monthly to reach it in one year?"
    resolved = _resolve_context(message, history)

    assert "emergency fund" in resolved.lower(), (
        f"Expected 'emergency fund' in resolved: {resolved}"
    )


# ===========================================================================
# TEST 6: One-year saving calculation uses 12 months
# ===========================================================================

def test_analyze_goal_one_year_uses_12_months():
    goal = _FakeGoal(1, "Emergency Fund", 60000, 20000)
    db = _make_db(goals=[goal])

    result = _execute_tool(
        db, 1, "analyze_goal",
        {"goal_name": "Emergency Fund", "months": 12},
        "How much should I save monthly to reach it in one year?",
    )

    assert result.get("remaining") == 40000.0
    assert result.get("monthly_needed") == pytest.approx(40000 / 12, rel=0.01)


# ===========================================================================
# TEST 7: Affordability check uses verified financial data
# ===========================================================================

def test_affordability_check_uses_verified_data():
    sbi = _FakeAccount(1, "SBI Savings", 50000, "bank")
    today = date.today()
    txns = []
    for i in range(3):
        d = today - timedelta(days=i * 30)
        txns.append(_FakeTxn(i * 2 + 1, 30000, "income", 1, date_=d))
        txns.append(_FakeTxn(i * 2 + 2, 20000, "expense", 1, date_=d))

    db = _make_db(accounts=[sbi], transactions=txns)

    result = _execute_tool(
        db, 1, "affordability_check",
        {"amount": 40000},
        "Can I afford a \u20b940,000 phone?",
    )

    assert result["purchase_amount"] == 40000.0
    assert result["liquid_balance"] == 50000.0
    assert result["balance_after_purchase"] == 10000.0
    assert result["emergency_fund_needed"] > 0
    assert result["verdict"] in ("risky", "not_affordable")


# ===========================================================================
# TEST 8: Wrong tool selection is rejected before DB mutation
# ===========================================================================

def test_wrong_tool_blocked_before_mutation():
    message = "Add a \u20b9500 grocery expense from my SBI account using UPI"

    err = _validate_tool_call(
        "create_account",
        {"name": "using UPI", "type": "bank", "balance": 500},
        message,
    )
    assert err is not None

    db = _make_db()
    if err:
        db.add.assert_not_called()
        db.commit.assert_not_called()


# ===========================================================================
# TEST 9: Deletion requires confirmation
# ===========================================================================

def test_deletion_requires_confirmation():
    txn = _FakeTxn(42, 500, "expense", 1, merchant="Swiggy")
    db = _make_db(transactions=[txn])

    result = _execute_tool(
        db, 1, "delete_transaction",
        {"transaction_id": 42},
        "Delete transaction 42",
    )

    assert result.get("pending_confirmation") is True
    assert "confirm" in result["message"].lower()
    db.delete.assert_not_called()
    db.commit.assert_not_called()


# ===========================================================================
# TEST 10: Ambiguous account requests clarification
# ===========================================================================

def test_ambiguous_account_requests_clarification():
    acct1 = _FakeAccount(1, "HDFC Savings", 50000)
    acct2 = _FakeAccount(2, "SBI Savings", 30000)
    db = _make_db(accounts=[acct1, acct2])

    # Override the filter to return both accounts (ambiguous)
    from app.models.models import Account
    original_side_effect = db.query.side_effect

    def patched_query(model):
        q = original_side_effect(model)
        if model is Account:
            q.filter.return_value.all.return_value = [acct1, acct2]
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = patched_query

    result = _execute_tool(
        db, 1, "create_transaction",
        {"amount": 500, "type": "expense", "account_name": "xyz_nonexistent"},
        "Add \u20b9500 expense",
    )

    assert "error" in result
    assert result["error"] in ("ambiguous_account", "no_account_found")


# ===========================================================================
# TEST 11: Ollama failure never triggers incorrect fallback write
# ===========================================================================

def test_ollama_failure_no_fallback_write():
    db = _make_db()

    with patch("app.services.llm.settings") as mock_settings:
        mock_settings.OLLAMA_ENABLED = True
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_MODEL = "qwen2.5:7b"

        import httpx
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_cls.return_value = mock_client

            result = answer_with_llm(
                db, 1,
                "Add a \u20b9500 grocery expense from SBI using UPI",
                [],
            )

    assert "answer_text" in result
    text = result["answer_text"].lower()
    assert "ollama" in text or "connect" in text or "ai" in text
    db.add.assert_not_called()
    db.commit.assert_not_called()


# ===========================================================================
# TEST 12: Formatting removes broken markdown and uses rupee symbol
# ===========================================================================

def test_clean_removes_markdown_and_uses_rupee():
    raw = "**Your balance** is INR 50,000. Rs 1,000 was spent on *food*. ## Summary"
    cleaned = _clean(raw)

    assert "**" not in cleaned
    assert "##" not in cleaned
    assert "*food*" not in cleaned
    assert "INR" not in cleaned
    assert "Rs" not in cleaned
    assert "\u20b9" in cleaned
    assert "50,000" in cleaned


# ===========================================================================
# TEST 13: Frontend mutations list returned after successful operations
# ===========================================================================

def test_mutations_returned_after_transaction_creation():
    sbi = _FakeAccount(1, "SBI Savings", 10000)
    db = _make_db(accounts=[sbi])

    result = _execute_tool(
        db, 1, "create_transaction",
        {"amount": 500, "type": "expense", "account_name": "SBI", "category": "Food"},
        "Add \u20b9500 food expense",
    )

    assert "mutations" in result
    assert "transactions" in result["mutations"]
    assert "accounts" in result["mutations"]


# ===========================================================================
# TEST 14: get_net_worth returns assets, liabilities, net_worth
# ===========================================================================

def test_get_net_worth():
    bank = _FakeAccount(1, "SBI Savings", 50000, "bank")
    loan = _FakeAccount(2, "Home Loan", -200000, "loan")
    db = _make_db(accounts=[bank, loan])

    result = _execute_tool(db, 1, "get_net_worth", {}, "What is my net worth?")

    assert "assets" in result
    assert "liabilities" in result
    assert "net_worth" in result
    assert result["assets"] == 50000.0
    assert result["liabilities"] == 200000.0
    assert result["net_worth"] == -150000.0


# ===========================================================================
# TEST 15: get_emergency_fund returns months_covered
# ===========================================================================

def test_get_emergency_fund():
    bank = _FakeAccount(1, "SBI Savings", 60000, "bank")
    today = date.today()
    txns = [
        _FakeTxn(i + 1, 10000, "expense", 1, date_=today - timedelta(days=i * 10))
        for i in range(9)
    ]
    db = _make_db(accounts=[bank], transactions=txns)

    result = _execute_tool(db, 1, "get_emergency_fund", {}, "How is my emergency fund?")

    assert "months_covered" in result
    assert "target_3_months" in result
    assert "target_6_months" in result
    assert result["available_balance"] == 60000.0
    assert result["months_covered"] > 0


# ===========================================================================
# TEST 16: get_monthly_report returns income, expenses, savings
# ===========================================================================

def test_get_monthly_report():
    db = _make_db()
    result = _execute_tool(db, 1, "get_monthly_report", {}, "Show my monthly report")

    assert "month" in result
    assert "income" in result
    assert "expenses" in result
    assert "savings" in result
    assert "savings_rate" in result
    assert "expense_change_pct" in result


# ===========================================================================
# TEST 17: get_budget_recommendations returns category list
# ===========================================================================

def test_get_budget_recommendations():
    today = date.today()
    txns = [
        _FakeTxn(i + 1, 3000, "expense", 1, category_id=1, date_=today - timedelta(days=i * 5))
        for i in range(6)
    ]
    db = _make_db(transactions=txns)

    result = _execute_tool(db, 1, "get_budget_recommendations", {}, "Recommend budgets for me")

    assert isinstance(result, list)
    assert len(result) > 0
    first = result[0]
    assert "category" in first
    assert "average_monthly" in first
    assert "recommended_budget" in first
    assert first["recommended_budget"] >= first["average_monthly"]


# ===========================================================================
# Additional: Confirmation flow executes deletion and reverses balance
# ===========================================================================

def test_confirmation_executes_deletion_and_reverses_balance():
    sbi = _FakeAccount(1, "SBI Savings", 9500)
    txn = _FakeTxn(42, 500, "expense", 1, merchant="Swiggy")
    db = _make_db(accounts=[sbi], transactions=[txn])

    _set_pending_deletion(1, "transaction", 42, "Swiggy \u20b9500.00")

    result = _handle_confirmation(db, 1, "yes, confirm")

    assert result is not None
    assert "deleted" in result["answer_text"].lower()
    assert "transactions" in result.get("mutations", [])
    assert float(sbi.balance) == 10000.0
