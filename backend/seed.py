"""
seed.py - Populates the database with realistic sample data for a demo user.

This script is designed to be run once. It will:
1. Create all database tables if they don't exist.
2. Seed a list of common, system-wide transaction categories.
3. Create a demo user ('demo@finwise.app').
4. Create sample accounts (bank, credit card, cash) for the demo user.
5. Generate ~150 realistic transactions for the past 90 days, including:
   - Salary income
   - Recurring subscriptions (Netflix, Spotify)
   - Common Indian expenses (Swiggy, Zomato, Uber, Amazon, etc.)
6. Set up a few sample budgets and savings goals.

It is idempotent; if the demo user already exists, it will not run again.
"""

import random
from datetime import date, timedelta, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.models import Account, Transaction, Category, Budget, SavingsGoal
from app.core.security import hash_password
from app.services.categorization import categorize_transaction

DEMO_USER_EMAIL = "demo@finwise.app"
DEMO_USER_PASSWORD = "Demo@1234"

SYSTEM_CATEGORIES = [
    "Salary", "Freelance", "Gifts", "Other Income", "Food", "Transport", "Rent",
    "Utilities", "Shopping", "Entertainment", "Health", "Education",
    "Subscriptions", "Loans & EMI", "Savings & Investments", "Cash Withdrawal", "Other"
]


def seed_categories(db: Session):
    """Ensures all system categories exist in the database."""
    existing = {c.name for c in db.query(Category).filter(Category.is_system == 1).all()}
    for cat_name in SYSTEM_CATEGORIES:
        if cat_name not in existing:
            db.add(Category(name=cat_name, is_system=1, is_active=1))
    db.commit()


def create_demo_user(db: Session) -> User:
    """Creates and returns the demo user."""
    hashed_password = hash_password(DEMO_USER_PASSWORD)
    user = User(
        email=DEMO_USER_EMAIL,
        password_hash=hashed_password,
        full_name="Demo User",
        monthly_salary=Decimal("65000.00"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_accounts(db: Session, user_id: int) -> dict:
    """Creates sample accounts and returns a dict mapping name to account object."""
    accounts_data = [
        {"name": "HDFC Bank", "type": "bank", "balance": Decimal("85000.00")},
        {"name": "ICICI Credit Card", "type": "credit_card", "balance": Decimal("-12000.00")},
        {"name": "Cash", "type": "cash", "balance": Decimal("3500.00")},
        {"name": "Paytm Wallet", "type": "wallet", "balance": Decimal("1250.00")},
    ]
    created_accounts = {}
    for acc_data in accounts_data:
        acc = Account(user_id=user_id, **acc_data)
        db.add(acc)
        created_accounts[acc_data["name"]] = acc
    db.commit()
    for acc in created_accounts.values():
        db.refresh(acc)
    return created_accounts


def generate_transactions(db: Session, user_id: int, accounts: dict):
    """Generates a set of realistic transactions for the last 90 days."""
    today = date.today()
    transactions = []

    # --- Recurring Income ---
    for i in range(3):
        d = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        transactions.append(
            TransactionCreate(
                account_id=accounts["HDFC Bank"].id,
                amount=Decimal("65000.00"),
                type="income",
                merchant="Employer Inc.",
                description="Monthly Salary",
                transaction_date=d,
            )
        )

    # --- Recurring Expenses ---
    recurring_expenses = [
        {"d": 5, "amt": 18000, "desc": "House Rent", "acc": "HDFC Bank"},
        {"d": 10, "amt": 149, "desc": "Netflix Subscription", "acc": "ICICI Credit Card"},
        {"d": 15, "amt": 119, "desc": "Spotify Premium", "acc": "ICICI Credit Card"},
        {"d": 20, "amt": 499, "desc": "Airtel Broadband", "acc": "HDFC Bank"},
    ]
    for i in range(3):
        for re in recurring_expenses:
            d = (today - timedelta(days=i * 30)).replace(day=re["d"])
            transactions.append(
                TransactionCreate(
                    account_id=accounts[re["acc"]].id,
                    amount=Decimal(str(re["amt"])),
                    type="expense",
                    description=re["desc"],
                    transaction_date=d,
                )
            )

    # --- Random Daily Expenses ---
    daily_expenses = [
        ("Swiggy", (200, 600)), ("Zomato", (200, 600)), ("Uber", (150, 500)),
        ("Local Kirana", (50, 300)), ("Amazon.in", (500, 5000)),
        ("Myntra", (1000, 4000)), ("Petrol Pump", (500, 2000)),
        ("Starbucks", (300, 800)), ("Blinkit", (200, 700)),
    ]
    for i in range(90):
        if random.random() < 0.6:  # 60% chance of a transaction on any given day
            d = today - timedelta(days=i)
            merchant, (min_amt, max_amt) = random.choice(daily_expenses)
            amount = Decimal(str(random.randint(min_amt, max_amt)))
            account = random.choice([accounts["HDFC Bank"], accounts["ICICI Credit Card"], accounts["Paytm Wallet"]])
            transactions.append(
                TransactionCreate(
                    account_id=account.id,
                    amount=amount,
                    type="expense",
                    merchant=merchant,
                    description=f"Payment to {merchant}",
                    transaction_date=d,
                )
            )

    # --- Create Transaction records ---
    for txn_data in transactions:
        cat_id, confidence = categorize_transaction(
            txn_data.description or "", txn_data.merchant or "", db, user_id
        )
        txn = Transaction(
            user_id=user_id,
            category_id=cat_id,
            confidence_score=confidence,
            **txn_data.model_dump(),
        )
        db.add(txn)
    db.commit()
    print(f"Generated and stored {len(transactions)} transactions.")


def create_budgets_and_goals(db: Session, user_id: int):
    """Creates sample budgets for the current month and a savings goal."""
    # Budget
    food_cat = db.query(Category).filter(Category.name == "Food").first()
    shopping_cat = db.query(Category).filter(Category.name == "Shopping").first()
    month_str = date.today().strftime("%Y-%m")

    if food_cat:
        db.add(Budget(user_id=user_id, category_id=food_cat.id, amount=Decimal("8000"), month=month_str))
    if shopping_cat:
        db.add(Budget(user_id=user_id, category_id=shopping_cat.id, amount=Decimal("5000"), month=month_str))

    # Goal
    db.add(
        SavingsGoal(
            user_id=user_id,
            name="Vacation to Goa",
            target_amount=Decimal("50000"),
            current_amount=Decimal("15000"),
            deadline=date.today() + timedelta(days=180),
        )
    )
    db.commit()
    print("Created sample budgets and savings goal.")


def seed_data():
    """Main function to seed all data."""
    db = SessionLocal()
    try:
        # 1. Create tables if they don't exist.
        # In a real app, this would be handled by Alembic migrations.
        Base.metadata.create_all(bind=engine)
        print("Tables checked/created.")

        # 2. Seed system categories
        seed_categories(db)
        print("System categories seeded.")

        # 3. Check if demo user exists
        user = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()
        if user:
            print(f"Demo user '{DEMO_USER_EMAIL}' already exists. Skipping seeding.")
            return

        # 4. Create demo user, accounts, transactions, etc.
        print("Creating demo user and data...")
        user = create_demo_user(db)
        accounts = create_accounts(db, user.id)
        generate_transactions(db, user.id, accounts)
        create_budgets_and_goals(db, user.id)

        print("\n✅ Database seeding complete!")
        print(f"Login with: {DEMO_USER_EMAIL} / {DEMO_USER_PASSWORD}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()