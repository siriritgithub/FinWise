"""Local FinWise financial assistant.

No external LLM is used. The assistant combines deterministic intent parsing with
real database queries and controlled write operations. This keeps financial
numbers grounded in the user's data and makes every action auditable.
"""
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session


def _parse_amount(text: str):
    m = re.search(r"(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text.lower())
    return Decimal(m.group(1).replace(",", "")) if m else None


def _period(text: str):
    t = text.lower(); today = date.today()
    if "today" in t: return today, today
    if "yesterday" in t:
        d=today-timedelta(days=1); return d,d
    if "this month" in t: return today.replace(day=1), today
    if "last month" in t:
        end=today.replace(day=1)-timedelta(days=1); return end.replace(day=1), end
    if "this week" in t: return today-timedelta(days=today.weekday()), today
    if "last week" in t:
        end=today-timedelta(days=today.weekday()+1); start=end-timedelta(days=6); return start,end
    m=re.search(r"last\s+(\d+)\s+days", t)
    if m:
        n=int(m.group(1)); return today-timedelta(days=n-1),today
    return today.replace(day=1), today


def _category(db, user_id, text):
    from app.models.models import Category
    keywords={
        "food":"Food","groceries":"Food","restaurant":"Food","shopping":"Shopping",
        "transport":"Transport","travel":"Transport","rent":"Rent","utility":"Utilities",
        "utilities":"Utilities","entertainment":"Entertainment","health":"Health",
        "education":"Education","investment":"Investments","loan":"Loans","emi":"Loans",
    }
    lower=text.lower()
    target=next((v for k,v in keywords.items() if k in lower),None)
    if not target: return None, 0.0
    cat=db.query(Category).filter(Category.user_id.in_([user_id, None]), Category.name.ilike(f"%{target}%"), Category.is_active==1).first()
    return (cat.id, 0.95) if cat else (None,0.0)


def _account(db,user_id,text):
    from app.models.models import Account
    accounts=db.query(Account).filter(Account.user_id==user_id,Account.is_active==1).all()
    low=text.lower()
    for a in accounts:
        if a.name.lower() in low: return a
    return accounts[0] if len(accounts)==1 else None


def _account_type(text):
    low=text.lower()
    for t in ("credit_card","investment","wallet","loan","cash","bank"):
        if t.replace("_"," ") in low or t in low: return t
    return "bank"


def _goal(db,user_id,text):
    from app.models.models import SavingsGoal
    goals=db.query(SavingsGoal).filter(SavingsGoal.user_id==user_id).all()
    low=text.lower()
    for g in goals:
        if g.name.lower() in low: return g
    return goals[0] if len(goals)==1 else None


def _summary(db,user_id,start,end):
    from app.models.models import Transaction,Account,Category
    tx=db.query(Transaction).filter(Transaction.user_id==user_id,Transaction.transaction_date>=start,Transaction.transaction_date<datetime.combine(end+timedelta(days=1),datetime.min.time())).all()
    income=sum(float(t.amount) for t in tx if t.type=="income")
    expense=sum(float(t.amount) for t in tx if t.type=="expense")
    cats={c.id:c.name for c in db.query(Category).filter(Category.is_active==1).all()}
    by={}
    for t in tx:
        if t.type=="expense": by[cats.get(t.category_id,"Other")]=by.get(cats.get(t.category_id,"Other"),0)+float(t.amount)
    accounts=db.query(Account).filter(Account.user_id==user_id,Account.is_active==1).all()
    return income,expense,by,accounts


def _format_period(start,end):
    return start.strftime("%d %b %Y") if start==end else f"{start.strftime('%d %b %Y')} to {end.strftime('%d %b %Y')}"


def _monthly_report(db,user_id):
    today=date.today(); start=today.replace(day=1); prev_end=start-timedelta(days=1); prev_start=prev_end.replace(day=1)
    inc,exp,by,_=_summary(db,user_id,start,today); pinc,pexp,pby,_=_summary(db,user_id,prev_start,prev_end)
    savings=inc-exp; rate=(savings/inc*100) if inc else 0
    top=max(by.items(),key=lambda x:x[1],default=("None",0))
    prev_top=max(pby.items(),key=lambda x:x[1],default=("None",0))
    return (f"**{today.strftime('%B %Y')} report**\n\nIncome: INR {inc:,.0f}\nExpenses: INR {exp:,.0f}\nSavings: INR {savings:,.0f}\nSavings rate: {rate:.1f}%\nTop category: {top[0]} (INR {top[1]:,.0f})\n\nCompared with {prev_start.strftime('%B')}: expenses changed by {((exp-pexp)/pexp*100 if pexp else 0):+.1f}%. "
            f"Your largest category is {top[0]}."), {"income":inc,"expenses":exp,"savings":savings,"savings_rate":rate}


def _what_if(db,user_id,text):
    amount=_parse_amount(text)
    if amount is None: return "Tell me the monthly reduction, for example: **What if I reduce food spending by ₹2,000 per month?**"
    start=date.today().replace(day=1); today=date.today(); inc,exp,_,_= _summary(db,user_id,start,today)
    days=max(today.day,1); monthly_exp=exp/days*30; current=max(0,inc-exp)
    new_exp=max(0,monthly_exp-float(amount)); new_savings=max(0,inc-new_exp)
    annual=float(amount)*12
    return (f"If you reduce monthly spending by INR {amount:,.0f}:\n\nCurrent estimated monthly savings: **INR {current:,.0f}**\n"
            f"Projected monthly savings: **INR {new_savings:,.0f}**\nAnnual improvement: **INR {annual:,.0f}**\n\nThis is a scenario estimate based on your current-month income and spending.")


def answer(db:Session,user_id:int,message:str,history=None):
    msg=message.strip(); low=msg.lower()
    if not msg: return {"answer_text":"Please tell me what you'd like to do.","data_summary":{},"suggestions":[]}

    # CREATE ACCOUNT
    if re.search(r"\b(create|add|open)\b.*\b(account|bank account|wallet|cash)",low):
        amount=_parse_amount(msg) or Decimal("0")
        m=re.search(r"(?:account|called|named)\s+(?:called\s+|named\s+)?([A-Za-z][A-Za-z0-9 _-]{1,40})",msg,re.I)
        name=(m.group(1).strip() if m else "New Account")
        # stop at common trailing phrases
        name=re.split(r"\s+(?:with|having|and)\s+",name,flags=re.I)[0].strip()
        from app.models.models import Account
        acc=Account(user_id=user_id,name=name,type=_account_type(low),balance=amount,currency="INR")
        db.add(acc); db.commit(); db.refresh(acc)
        return {"answer_text":f"Done. I created **{acc.name}** with an opening balance of **INR {amount:,.2f}**.","data_summary":{"account_id":acc.id},"suggestions":[]}

    # ADD BALANCE / INCOME TO ACCOUNT
    if re.search(r"\b(add|deposit|put|increase)\b.*\b(balance|money|account)\b",low):
        amount=_parse_amount(msg); acc=_account(db,user_id,msg)
        if amount is None: return {"answer_text":"Tell me the amount, for example: Add ₹5,000 to HDFC.","data_summary":{},"suggestions":[]}
        if not acc: return {"answer_text":"I couldn't identify the account. Please mention its name, for example: Add ₹5,000 to HDFC.","data_summary":{},"suggestions":[]}
        acc.balance=Decimal(str(acc.balance))+amount
        from app.models.models import Transaction
        tx=Transaction(user_id=user_id,account_id=acc.id,amount=amount,type="income",merchant="Account top-up",description="Balance added via FinWise assistant",transaction_date=datetime.utcnow(),payment_method="other")
        db.add(tx); db.commit()
        return {"answer_text":f"Done. **INR {amount:,.2f}** was added to **{acc.name}**. New balance: **INR {float(acc.balance):,.2f}**.","data_summary":{"account_id":acc.id,"new_balance":float(acc.balance)},"suggestions":[]}

    # EXPENSE / INCOME transaction actions
    if re.search(r"\b(i|add|record|log)\b.*\b(spent|spend|expense|paid|purchase|bought)\b",low):
        amount=_parse_amount(msg); acc=_account(db,user_id,msg)
        if amount is None: return {"answer_text":"Tell me the amount, for example: I spent ₹850 on food.","data_summary":{},"suggestions":[]}
        if not acc: return {"answer_text":"Please create or mention an account first so I know where to record the expense.","data_summary":{},"suggestions":[]}
        cat_id,conf=_category(db,user_id,msg)
        merchant=None
        m=re.search(r"(?:at|from|on)\s+([A-Za-z][A-Za-z0-9 &.-]{1,50})",msg,re.I)
        if m: merchant=m.group(1).strip()
        tx=__import__('app.models.models',fromlist=['Transaction']).Transaction(user_id=user_id,account_id=acc.id,amount=amount,type="expense",category_id=cat_id,merchant=merchant,description=msg,transaction_date=datetime.utcnow(),payment_method="other",confidence_score=conf or None)
        db.add(tx); acc.balance=Decimal(str(acc.balance))-amount; db.commit()
        cat=merchant or "expense"
        return {"answer_text":f"Recorded **INR {amount:,.2f}** expense in **{acc.name}**. New balance: **INR {float(acc.balance):,.2f}**.","data_summary":{"transaction_id":tx.id},"suggestions":[]}

    if re.search(r"\b(add|record|log)\b.*\b(income|salary|earned|received)\b",low):
        amount=_parse_amount(msg); acc=_account(db,user_id,msg)
        if amount is None: return {"answer_text":"Tell me the income amount, for example: Add ₹50,000 salary.","data_summary":{},"suggestions":[]}
        if not acc: return {"answer_text":"Please mention which account received the income.","data_summary":{},"suggestions":[]}
        from app.models.models import Transaction
        tx=Transaction(user_id=user_id,account_id=acc.id,amount=amount,type="income",merchant="Income",description=msg,transaction_date=datetime.utcnow(),payment_method="other")
        db.add(tx); acc.balance=Decimal(str(acc.balance))+amount; db.commit()
        return {"answer_text":f"Recorded **INR {amount:,.2f}** income in **{acc.name}**. New balance: **INR {float(acc.balance):,.2f}**.","data_summary":{"transaction_id":tx.id},"suggestions":[]}

    # BUDGET action
    if re.search(r"\b(create|add|set)\b.*\bbudget\b",low):
        amount=_parse_amount(msg)
        if amount is None: return {"answer_text":"Tell me the budget amount, for example: Create a food budget of ₹8,000 this month.","data_summary":{},"suggestions":[]}
        cat_id,_=_category(db,user_id,msg)
        if not cat_id: return {"answer_text":"Tell me the budget category, for example: Create a Food budget of ₹8,000 this month.","data_summary":{},"suggestions":[]}
        from app.models.models import Budget
        month=date.today().strftime("%Y-%m")
        existing=db.query(Budget).filter(Budget.user_id==user_id,Budget.category_id==cat_id,Budget.month==month).first()
        if existing: existing.amount=amount; action="updated"
        else: db.add(Budget(user_id=user_id,category_id=cat_id,amount=amount,month=month)); action="created"
        db.commit(); return {"answer_text":f"Budget {action}: **INR {amount:,.0f}** for **{msg.split('budget')[0].strip().title() or 'this category'}** this month.","data_summary":{"month":month},"suggestions":[]}

    # GOAL creation/contribution
    if re.search(r"\b(create|add|set)\b.*\bgoal\b",low):
        amount=_parse_amount(msg)
        if amount is None: return {"answer_text":"Tell me the target, for example: Create a goal to save ₹100,000 for a laptop.","data_summary":{},"suggestions":[]}
        from app.models.models import SavingsGoal
        m=re.search(r"(?:for|called|named)\s+([A-Za-z][A-Za-z0-9 _-]{1,50})",msg,re.I)
        name=(m.group(1).strip() if m else "Savings Goal")
        name=re.split(r"\s+(?:by|with|of)\s+",name,flags=re.I)[0].strip()
        g=SavingsGoal(user_id=user_id,name=name,target_amount=amount,current_amount=0)
        db.add(g); db.commit(); db.refresh(g)
        return {"answer_text":f"Created the **{g.name}** goal with a target of **INR {amount:,.0f}**.","data_summary":{"goal_id":g.id},"suggestions":[]}

    if re.search(r"\b(add|contribute|put|save)\b.*\b(goal|savings)\b",low):
        amount=_parse_amount(msg); g=_goal(db,user_id,msg)
        if amount is None or not g: return {"answer_text":"Tell me the amount and goal name, for example: Add ₹5,000 to my laptop goal.","data_summary":{},"suggestions":[]}
        g.current_amount=Decimal(str(g.current_amount))+amount; db.commit()
        return {"answer_text":f"Added **INR {amount:,.0f}** to **{g.name}**. Progress: **INR {float(g.current_amount):,.0f} / INR {float(g.target_amount):,.0f}**.","data_summary":{"goal_id":g.id},"suggestions":[]}

    # ANALYTICS actions
    if "what if" in low or "reduce" in low and "spending" in low:
        return {"answer_text":_what_if(db,user_id,msg),"data_summary":{},"suggestions":[]}
    if "monthly report" in low or "monthly financial report" in low or "what changed" in low:
        text,data=_monthly_report(db,user_id); return {"answer_text":text,"data_summary":data,"suggestions":[]}
    if "health score" in low or "financial health" in low:
        from app.services.health_score import compute_health_score
        h=compute_health_score(db,user_id); return {"answer_text":f"Your Financial Health Score is **{h['total_score']:.0f}/100 (Grade {h['grade']})**.\n\n"+"\n".join(f"• {x['name']}: {x['score']}/{x['max_score']} — {x['description']}" for x in h['factors']),"data_summary":h,"suggestions":[]}
    if "forecast" in low or "predict" in low:
        from app.services.forecasting import build_forecast
        f=build_forecast(db,user_id,30); return {"answer_text":f"30-day cash-flow forecast starts from **INR {float(f['current_balance']):,.0f}**.\n\nAssumptions:\n"+"\n".join(f"• {x}" for x in f['assumptions']),"data_summary":f,"suggestions":[]}
    if "anomal" in low or "unusual spending" in low:
        from app.services.anomaly import detect_anomalies
        a=detect_anomalies(db,user_id,90); text="No unusual spending was detected in the last 90 days." if not a else "\n".join(f"• {x['message']}" for x in a[:5]); return {"answer_text":text,"data_summary":{"count":len(a)},"suggestions":[]}
    if "net worth" in low:
        from app.models.models import Account
        acc=db.query(Account).filter(Account.user_id==user_id,Account.is_active==1).all(); assets=sum(float(a.balance) for a in acc if a.type not in ("loan","credit_card")); liabilities=sum(abs(float(a.balance)) for a in acc if a.type in ("loan","credit_card")); return {"answer_text":f"Estimated net worth: **INR {assets-liabilities:,.0f}**\nAssets: INR {assets:,.0f}\nLiabilities: INR {liabilities:,.0f}","data_summary":{},"suggestions":[]}

    # READ FINANCIAL DATA
    if "balance" in low or "how much money" in low:
        from app.models.models import Account
        acc=db.query(Account).filter(Account.user_id==user_id,Account.is_active==1).all()
        if not acc: return {"answer_text":"No active accounts found. Add an account first and I'll track its balance.","data_summary":{},"suggestions":[]}
        total=sum(float(a.balance) for a in acc); lines="\n".join(f"• {a.name}: INR {float(a.balance):,.2f}" for a in acc)
        return {"answer_text":f"Your total balance is **INR {total:,.2f}**.\n\n{lines}","data_summary":{"total_balance":total},"suggestions":[]}
    if "budget" in low:
        from app.models.models import Budget,Transaction
        month=date.today().strftime("%Y-%m"); bs=db.query(Budget).filter(Budget.user_id==user_id,Budget.month==month).all()
        if not bs: return {"answer_text":"You have no budgets set for this month.","data_summary":{},"suggestions":[]}
        lines=[]
        for b in bs:
            spent=sum(float(t.amount) for t in db.query(Transaction).filter(Transaction.user_id==user_id,Transaction.category_id==b.category_id,Transaction.type=="expense",Transaction.transaction_date.like(f"{month}%")).all()); name=b.category.name if b.category else "Total"; lines.append(f"• {name}: INR {spent:,.0f} / INR {float(b.amount):,.0f} ({spent/float(b.amount)*100:.0f}%)")
        return {"answer_text":"This month's budget status:\n"+"\n".join(lines),"data_summary":{},"suggestions":[]}
    if "subscription" in low or "recurring" in low:
        from app.models.models import RecurringRule
        subs=db.query(RecurringRule).filter(RecurringRule.user_id==user_id,RecurringRule.is_subscription==1).all(); monthly=sum(float(x.expected_amount)*30/x.interval_days for x in subs if x.expected_amount and x.interval_days)
        return {"answer_text":f"You have **{len(subs)}** detected subscriptions costing about **INR {monthly:,.0f}/month** (INR {monthly*12:,.0f}/year).", "data_summary":{"count":len(subs),"monthly":monthly},"suggestions":[]}
    if "goal" in low or "saving for" in low:
        from app.models.models import SavingsGoal
        gs=db.query(SavingsGoal).filter(SavingsGoal.user_id==user_id).all()
        if not gs: return {"answer_text":"You don't have any savings goals yet.","data_summary":{},"suggestions":[]}
        return {"answer_text":"Your goals:\n"+"\n".join(f"• {g.name}: INR {float(g.current_amount):,.0f} / INR {float(g.target_amount):,.0f} ({min(float(g.current_amount)/float(g.target_amount)*100,100):.0f}%)" for g in gs),"data_summary":{},"suggestions":[]}
    if any(x in low for x in ["spend","spent","expense","expenses","income","salary","save","savings"]):
        start,end=_period(low); inc,exp,by,_=_summary(db,user_id,start,end)
        rate=(inc-exp)/inc*100 if inc else 0
        return {"answer_text":f"For **{_format_period(start,end)}**:\nIncome: **INR {inc:,.0f}**\nExpenses: **INR {exp:,.0f}**\nNet: **INR {inc-exp:,.0f}**\nSavings rate: **{rate:.1f}%**", "data_summary":{"income":inc,"expenses":exp,"savings_rate":rate},"suggestions":[]}

    # Local general-finance knowledge, intentionally honest about scope.
    faq={
        "compound interest":"Compound interest means you earn interest on both your original principal and previously earned interest. In FinWise, use it as a planning concept rather than a guaranteed return.",
        "emergency fund":"A common planning target is 3–6 months of essential expenses. FinWise can estimate your coverage from your recorded balances and recent spending.",
        "50/30/20":"The 50/30/20 rule is a budgeting guideline: roughly 50% needs, 30% wants and 20% savings/debt repayment. It is a rule of thumb, not a universal prescription.",
    }
    for key,val in faq.items():
        if key in low: return {"answer_text":val,"data_summary":{},"suggestions":[]}
    return {"answer_text":"I can act on and analyze your FinWise data locally — accounts, balances, transactions, budgets, goals, subscriptions, receipts, forecasts, anomalies and financial health. I don't use an external LLM, so I won't pretend I can answer arbitrary unrelated questions. Try asking me to **create, add, analyze, compare, forecast, or explain something about your finances**.","data_summary":{},"suggestions":[]}
