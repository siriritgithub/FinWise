from sqlalchemy import (
    Column, Integer, String, DECIMAL, DateTime, Date,
    Enum, ForeignKey, Text, JSON, SmallInteger
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(Enum("bank", "cash", "credit_card", "wallet", "investment", "loan"), nullable=False)
    currency = Column(String(3), default="INR")
    balance = Column(DECIMAL(14, 2), nullable=False, default=0.00)
    credit_limit = Column(DECIMAL(14, 2))
    is_active = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(100), nullable=False)
    parent_category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    is_system = Column(SmallInteger, nullable=False, default=0)
    is_active = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")
    children = relationship("Category", backref="parent", remote_side=[id])
    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")
    recurring_rules = relationship("RecurringRule", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    amount = Column(DECIMAL(14, 2), nullable=False)
    type = Column(Enum("income", "expense", "transfer"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    merchant = Column(String(255))
    description = Column(Text)
    transaction_date = Column(DateTime, nullable=False)
    payment_method = Column(Enum("upi", "card", "cash", "netbanking", "other"), default="other")
    is_recurring = Column(SmallInteger, nullable=False, default=0)
    is_transfer = Column(SmallInteger, nullable=False, default=0)
    parent_transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    confidence_score = Column(DECIMAL(3, 2))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    splits = relationship("Transaction", backref="parent", remote_side=[id])
    receipts = relationship("Receipt", back_populates="transaction")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    amount = Column(DECIMAL(14, 2), nullable=False)
    month = Column(String(7), nullable=False)  # YYYY-MM
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")


class RecurringRule(Base):
    __tablename__ = "recurring_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    merchant_pattern = Column(String(255))
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    expected_amount = Column(DECIMAL(14, 2))
    interval_days = Column(Integer)
    next_expected_date = Column(Date)
    is_subscription = Column(SmallInteger, nullable=False, default=0)
    last_seen_date = Column(Date)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="recurring_rules")
    category = relationship("Category", back_populates="recurring_rules")


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    target_amount = Column(DECIMAL(14, 2), nullable=False)
    current_amount = Column(DECIMAL(14, 2), nullable=False, default=0.00)
    deadline = Column(Date)
    priority = Column(Enum("low", "medium", "high"), default="medium")
    monthly_contribution = Column(DECIMAL(14, 2))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="goals")


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    file_path = Column(String(500), nullable=False)
    merchant = Column(String(255))
    total_amount = Column(DECIMAL(14, 2))
    receipt_date = Column(Date)
    tax_amount = Column(DECIMAL(14, 2))
    ocr_raw_text = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="receipts")
    transaction = relationship("Transaction", back_populates="receipts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="audit_logs")
