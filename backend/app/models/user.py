from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Date
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    currency = Column(String(3), default="INR")
    timezone = Column(String(50), default="Asia/Kolkata")
    monthly_salary = Column(DECIMAL(12, 2))
    phone_number = Column(String(30))
    date_of_birth = Column(Date)
    gender = Column(String(30))
    occupation = Column(String(120))
    country = Column(String(80), default="India")
    language = Column(String(10), default="en")
    theme = Column(String(20), default="system")
    profile_photo_path = Column(String(500))
    app_lock_hash = Column(String(255))
    reset_token_hash = Column(String(128))
    reset_token_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("SavingsGoal", back_populates="user", cascade="all, delete-orphan")
    recurring_rules = relationship("RecurringRule", back_populates="user", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
