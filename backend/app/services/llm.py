"""Conversational LLM layer for FinWise.

FinWise keeps financial facts in its database. The LLM is only used to understand
natural language and explain verified results. Ollama/Qwen is the default local,
free option; OpenAI remains an optional cloud fallback.
"""
import json
from datetime import date, timedelta
from decimal import Decimal
import httpx
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.models import Account, Transaction, Category, Budget, SavingsGoal

settings = get_settings()


def _snapshot(db: Session, uid: int):
    today = date.today(); start = today.replace(day=1)
    accounts = db.query(Account).filter(Account.user_id == uid, Account.is_active == 1).all()
    tx = db.query(Transaction).filter(
        Transaction.user_id == uid,
        Transaction.transaction_date >= start,
        Transaction.transaction_date <= today,
    ).all()
    inc = sum(float(t.amount) for t in tx if t.type == "income")
    exp = sum(float(t.amount) for t in tx if t.type == "expense")
    cats = {c.id: c.name for c in db.query(Category).filter(Category.is_active == 1).all()}
    by = {}
    for t in tx:
        if t.type == "expense":
            name = cats.get(t.category_id, "Other")
            by[name] = by.get(name, 0) + float(t.amount)
    budgets = db.query(Budget).filter(Budget.user_id == uid, Budget.month == today.strftime("%Y-%m")).all()
    goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == uid).all()
    return {
        "balance": round(sum(float(a.balance) for a in accounts), 2),
        "accounts": [{"name": a.name, "type": a.type, "balance": float(a.balance)} for a in accounts],
        "month": today.strftime("%Y-%m"),
        "income": round(inc, 2),
        "expenses": round(exp, 2),
        "savings": round(inc - exp, 2),
        "top_categories": sorted(
            ({"category": k, "amount": round(v, 2)} for k, v in by.items()),
            key=lambda x: -x["amount"],
        )[:8],
        "budgets": [{"category": b.category.name if b.category else "Other", "amount": float(b.amount)} for b in budgets],
        "goals": [{"name": g.name, "target": float(g.target_amount), "current": float(g.current_amount), "deadline": str(g.deadline) if g.deadline else None} for g in goals],
    }


def _tool(db: Session, uid: int, name: str, args: dict):
    """Verified FinWise operations used by the cloud LLM path."""
    if name == "get_financial_snapshot":
        return _snapshot(db, uid)
    if name == "get_financial_health":
        from app.services.health_score import compute_health_score
        return compute_health_score(db, uid)
    if name == "get_cashflow_forecast":
        from app.services.forecasting import build_forecast
        return build_forecast(db, uid, int(args["days"]))
    if name == "run_what_if":
        tx = db.query(Transaction).filter(Transaction.user_id == uid, Transaction.transaction_date >= date.today().replace(day=1)).all()
        income = sum(float(t.amount) for t in tx if t.type == "income")
        expense = sum(float(t.amount) for t in tx if t.type == "expense")
        days = max(date.today().day, 1); monthly = expense / days * 30
        reduction = float(args["monthly_reduction"])
        return {
            "monthly_reduction": reduction,
            "current_monthly_savings": round(max(0, income - monthly), 2),
            "projected_monthly_savings": round(max(0, income - max(0, monthly - reduction)), 2),
            "annual_improvement": round(reduction * 12, 2),
        }
    if name == "get_spending":
        days = int(args["days"]); cutoff = date.today() - timedelta(days=days - 1)
        q = db.query(Transaction).filter(
            Transaction.user_id == uid, Transaction.type == "expense", Transaction.transaction_date >= cutoff
        )
        if args.get("category"):
            cat_ids = [c.id for c in db.query(Category).filter(
                Category.user_id.in_([uid, None]), Category.name.ilike(f"%{args['category']}%"), Category.is_active == 1
            ).all()]
            if cat_ids: q = q.filter(Transaction.category_id.in_(cat_ids))
        tx = q.all()
        return {"days": days, "category": args.get("category"), "total": round(sum(float(t.amount) for t in tx), 2), "count": len(tx)}
    if name == "create_account":
        acc = Account(user_id=uid, name=args["name"].strip(), type=args["type"], balance=Decimal(str(args["balance"])), currency="INR")
        db.add(acc); db.commit(); db.refresh(acc)
        return {"success": True, "account_id": acc.id, "name": acc.name, "balance": float(acc.balance)}
    if name == "create_budget":
        cat = db.query(Category).filter(Category.user_id.in_([uid, None]), Category.name.ilike(f"%{args['category']}%"), Category.is_active == 1).first()
        if not cat: return {"success": False, "error": "Category not found"}
        b = Budget(user_id=uid, category_id=cat.id, amount=Decimal(str(args["amount"])), month=args["month"])
        db.add(b); db.commit(); db.refresh(b)
        return {"success": True, "budget_id": b.id, "category": cat.name, "amount": float(b.amount), "month": b.month}
    if name == "create_goal":
        g = SavingsGoal(user_id=uid, name=args["name"].strip(), target_amount=Decimal(str(args["target_amount"])), current_amount=Decimal("0"), deadline=args.get("deadline"))
        db.add(g); db.commit(); db.refresh(g)
        return {"success": True, "goal_id": g.id, "name": g.name, "target_amount": float(g.target_amount)}
    return {"error": "Unknown tool"}


TOOLS = [
    {"type":"function","name":"get_financial_snapshot","description":"Get verified current balances, this-month income/expenses/savings, top spending categories, budgets and goals for the signed-in user.","parameters":{"type":"object","properties":{},"additionalProperties":False},"strict":True},
    {"type":"function","name":"get_spending","description":"Get verified spending for a period and optionally a category keyword.","parameters":{"type":"object","properties":{"days":{"type":"integer","minimum":1,"maximum":365},"category":{"type":["string","null"]}},"required":["days","category"],"additionalProperties":False},"strict":True},
    {"type":"function","name":"get_financial_health","description":"Get the FinWise financial health score and verified component insights.","parameters":{"type":"object","properties":{},"additionalProperties":False},"strict":True},
    {"type":"function","name":"get_cashflow_forecast","description":"Get a verified FinWise cash-flow forecast for 7 to 90 days.","parameters":{"type":"object","properties":{"days":{"type":"integer","minimum":7,"maximum":90}},"required":["days"],"additionalProperties":False},"strict":True},
    {"type":"function","name":"run_what_if","description":"Calculate a verified savings scenario for reducing monthly spending by a given amount.","parameters":{"type":"object","properties":{"monthly_reduction":{"type":"number","exclusiveMinimum":0}},"required":["monthly_reduction"],"additionalProperties":False},"strict":True},
    {"type":"function","name":"create_account","description":"Create a new FinWise account when the user explicitly asks to add/create/open one.","parameters":{"type":"object","properties":{"name":{"type":"string"},"type":{"type":"string","enum":["bank","cash","credit_card","wallet","investment","loan"]},"balance":{"type":"number"}},"required":["name","type","balance"],"additionalProperties":False},"strict":True},
    {"type":"function","name":"create_budget","description":"Create a category budget when the user explicitly asks for one.","parameters":{"type":"object","properties":{"category":{"type":"string"},"amount":{"type":"number"},"month":{"type":"string"}},"required":["category","amount","month"],"additionalProperties":False},"strict":True},
    {"type":"function","name":"create_goal","description":"Create a savings goal when the user explicitly asks for one.","parameters":{"type":"object","properties":{"name":{"type":"string"},"target_amount":{"type":"number"},"deadline":{"type":["string","null"]}},"required":["name","target_amount","deadline"],"additionalProperties":False},"strict":True},
]


def _is_action_request(message: str) -> bool:
    low = message.lower()
    return any(word in low for word in ("create account", "add account", "open account", "create budget", "set budget", "create goal", "add goal"))


def _local_finwise_answer(db: Session, uid: int, message: str, history):
    """Use the existing deterministic FinWise engine for verified financial facts/actions."""
    from app.services.chat import answer
    return answer(db, uid, message, history)


def _ollama_chat(system: str, messages: list[dict]) -> str:
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    with httpx.Client(timeout=120) as client:
        response = client.post(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    text = data.get("message", {}).get("content", "").strip()
    if not text:
        raise RuntimeError("Ollama returned an empty response")
    return text


def _answer_with_ollama(db: Session, uid: int, message: str, history=None):
    if not settings.OLLAMA_ENABLED:
        return None

    # Mutating operations stay deterministic and database-backed. The local LLM
    # never gets permission to invent or directly modify financial records.
    if _is_action_request(message):
        return _local_finwise_answer(db, uid, message, history)

    verified = _local_finwise_answer(db, uid, message, history)
    snapshot = _snapshot(db, uid)

    # If the deterministic engine has a verified financial answer, ask Qwen to
    # explain/rephrase it. The model receives the exact verified answer and snapshot.
    verified_text = verified.get("answer_text", "") if isinstance(verified, dict) else ""
    prompt = f"""Verified FinWise context for the signed-in user (do not alter numbers):
{json.dumps(snapshot, default=str, indent=2)}

Verified FinWise answer, if available:
{verified_text}

User question:
{message}

Rules:
- Be conversational, concise and useful.
- For financial facts, use only the verified context/answer above.
- Never invent balances, transactions, income, expenses, forecasts or goals.
- If the verified answer says the requested data is unavailable, say so honestly.
- For general finance education, explain clearly but do not pretend it is personalized data.
- Do not claim to have access to bank accounts outside FinWise.
"""
    msgs = [{"role": "user", "content": prompt}]
    # Keep a small amount of conversational context without exposing unrelated data.
    for item in (history or [])[-6:]:
        if item.get("role") in {"user", "assistant"} and item.get("content"):
            msgs.append({"role": item["role"], "content": item["content"]})
    text = _ollama_chat("You are FinWise AI, a privacy-first personal finance assistant. Verified database facts always win over model guesses.", msgs)
    return {"answer_text": text, "data_summary": verified.get("data_summary", {}) if isinstance(verified, dict) else {}, "suggestions": verified.get("suggestions", []) if isinstance(verified, dict) else []}


def _answer_with_openai(db: Session, uid: int, message: str, history=None):
    if not settings.OPENAI_ENABLED or not settings.OPENAI_API_KEY:
        return None
    messages = [{"role": "system", "content":[{"type":"input_text","text":("You are FinWise AI, a helpful personal-finance assistant. Use FinWise tools whenever the user asks about actual finances. Never invent balances, spending, forecasts, or goals. You may create accounts, budgets, and goals only when explicitly requested. For general non-financial questions, answer normally. Do not claim to be a licensed financial adviser.")}] }]
    for m in (history or [])[-10:]:
        messages.append({"role":m["role"],"content":[{"type":"input_text","text":m["content"]}]})
    messages.append({"role":"user","content":[{"type":"input_text","text":message}]})
    payload={"model":settings.OPENAI_MODEL,"input":messages,"tools":TOOLS}
    with httpx.Client(timeout=45) as client:
        r=client.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {settings.OPENAI_API_KEY}","Content-Type":"application/json"},json=payload)
        r.raise_for_status(); data=r.json()
        for _ in range(4):
            calls=[x for x in data.get("output",[]) if x.get("type")=="function_call"]
            if not calls:
                return {"answer_text":data.get("output_text","").strip() or "I could not generate a response.","data_summary":{},"suggestions":[]}
            tool_outputs=[]
            for call in calls:
                try: result=_tool(db,uid,call["name"],json.loads(call.get("arguments") or "{}"))
                except Exception as exc: result={"error":str(exc)}
                tool_outputs.append({"type":"function_call_output","call_id":call["call_id"],"output":json.dumps(result,default=str)})
            follow={"model":settings.OPENAI_MODEL,"previous_response_id":data.get("id"),"input":tool_outputs,"tools":TOOLS}
            r=client.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {settings.OPENAI_API_KEY}","Content-Type":"application/json"},json=follow)
            r.raise_for_status(); data=r.json()
    return {"answer_text":"I reached the tool-call limit for this request.","data_summary":{},"suggestions":[]}


def answer_with_llm(db: Session, uid: int, message: str, history=None):
    """Prefer free local Ollama, then optional OpenAI. Return None to use local rules."""
    if settings.OLLAMA_ENABLED:
        return _answer_with_ollama(db, uid, message, history)
    if settings.OPENAI_ENABLED and settings.OPENAI_API_KEY:
        return _answer_with_openai(db, uid, message, history)
    return None
