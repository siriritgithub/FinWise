from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import csv, io
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.models import Transaction, Account
from app.schemas.schemas import TransactionCreate, TransactionUpdate, TransactionOut
from app.services.categorization import categorize_transaction, batch_categorize

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _assert_account_owned(account_id: int, user_id: int, db: Session):
    acc = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return acc


@router.get("", response_model=List[TransactionOut])
def list_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if start_date:
        q = q.filter(Transaction.transaction_date >= start_date)
    if end_date:
        q = q.filter(Transaction.transaction_date <= end_date)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if type:
        q = q.filter(Transaction.type == type)
    if search:
        like = f"%{search}%"
        q = q.filter(
            Transaction.merchant.ilike(like) | Transaction.description.ilike(like)
        )
    offset = (page - 1) * page_size
    return q.order_by(Transaction.transaction_date.desc()).offset(offset).limit(page_size).all()


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    body: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    acc = _assert_account_owned(body.account_id, current_user.id, db)

    # Auto-categorize if no category provided
    cat_id = body.category_id
    confidence = None
    if not cat_id:
        cat_id, confidence = categorize_transaction(
            body.description or "", body.merchant or "", db, current_user.id
        )

    txn = Transaction(
        user_id=current_user.id,
        category_id=cat_id,
        confidence_score=confidence,
        **{k: v for k, v in body.model_dump().items() if k != "category_id"},
    )
    db.add(txn)

    # Update account balance
    if body.type == "income":
        acc.balance = float(acc.balance) + float(body.amount)
    elif body.type == "expense":
        acc.balance = float(acc.balance) - float(body.amount)

    db.commit()
    db.refresh(txn)
    return txn


@router.put("/{txn_id}", response_model=TransactionOut)
def update_transaction(
    txn_id: int,
    body: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == current_user.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    account = _assert_account_owned(txn.account_id, current_user.id, db)
    old_amount, old_type = float(txn.amount), txn.type
    # Reverse old balance impact first.
    if old_type == "income": account.balance = float(account.balance) - old_amount
    elif old_type == "expense": account.balance = float(account.balance) + old_amount
    data = body.model_dump(exclude_none=True)
    if "account_id" in data:
        account = _assert_account_owned(data["account_id"], current_user.id, db)
    for field, value in data.items():
        setattr(txn, field, value)
    if txn.type == "income": account.balance = float(account.balance) + float(txn.amount)
    elif txn.type == "expense": account.balance = float(account.balance) - float(txn.amount)
    db.commit(); db.refresh(txn)
    return txn


@router.delete("/{txn_id}", status_code=204)
def delete_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == current_user.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    account = _assert_account_owned(txn.account_id, current_user.id, db)
    if txn.type == "income": account.balance = float(account.balance) - float(txn.amount)
    elif txn.type == "expense": account.balance = float(account.balance) + float(txn.amount)
    db.delete(txn); db.commit()


@router.post("/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    account_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    CSV columns expected: date, description, amount, type (income/expense), merchant (optional)
    Returns preview of first 5 rows + total count.
    """
    acc = _assert_account_owned(account_id, current_user.id, db)
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    rows = list(reader)

    imported = 0
    errors = []
    for i, row in enumerate(rows):
        try:
            from datetime import datetime
            txn_date = datetime.strptime(row.get("date", "").strip(), "%Y-%m-%d")
            amount = float(row.get("amount", "0").replace(",", ""))
            txn_type = row.get("type", "expense").strip().lower()
            merchant = row.get("merchant", "").strip() or None
            description = row.get("description", "").strip() or None

            duplicate = db.query(Transaction).filter(
                Transaction.user_id == current_user.id,
                Transaction.account_id == account_id,
                Transaction.amount == amount,
                Transaction.type == txn_type,
                Transaction.transaction_date == txn_date,
                Transaction.merchant == merchant,
            ).first()
            if duplicate:
                errors.append({"row": i + 1, "error": "Potential duplicate transaction skipped"})
                continue
            cat_id, confidence = categorize_transaction(
                description or "", merchant or "", db, current_user.id
            )
            txn = Transaction(
                user_id=current_user.id,
                account_id=account_id,
                amount=amount,
                type=txn_type,
                merchant=merchant,
                description=description,
                transaction_date=txn_date,
                category_id=cat_id,
                confidence_score=confidence,
            )
            db.add(txn)
            if txn_type == "income": acc.balance = float(acc.balance) + amount
            elif txn_type == "expense": acc.balance = float(acc.balance) - amount
            imported += 1
        except Exception as e:
            errors.append({"row": i + 1, "error": str(e)})

    db.commit()
    return {"imported": imported, "errors": errors, "preview": rows[:5]}


@router.post("/categorize-batch")
def categorize_batch(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txns = db.query(Transaction).filter(Transaction.user_id == current_user.id).all()
    updated = batch_categorize(txns, db, current_user.id)
    return {"updated": updated}
