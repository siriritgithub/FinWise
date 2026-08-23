"""
schemas.py - Pydantic models for API requests and responses.
These models are used by FastAPI for data validation, serialization,
and documentation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Literal, Union
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel

# ... other schema classes in the file

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str



# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None
    currency: str
    timezone: str
    monthly_salary: Optional[Decimal] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = "en"
    theme: Optional[str] = "system"
    profile_photo_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    timezone: Optional[str] = Field(None, max_length=50)
    monthly_salary: Optional[Decimal] = Field(None, ge=0)
    phone_number: Optional[str] = Field(None, max_length=30)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=30)
    occupation: Optional[str] = Field(None, max_length=120)
    country: Optional[str] = Field(None, max_length=80)
    language: Optional[Literal["en", "hi"]] = None
    theme: Optional[Literal["light", "dark", "system"]] = None


class AppLockSet(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)


class AppLockVerify(BaseModel):
    pin: str


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    parent_category_id: Optional[int] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    parent_category_id: Optional[int] = None
    is_system: bool

    class Config:
        from_attributes = True


# ── Account ───────────────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str
    type: Literal['bank', 'cash', 'credit_card', 'wallet', 'investment', 'loan']
    balance: Decimal
    currency: str = "INR"


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class AccountOut(BaseModel):
    id: int
    name: str
    type: str
    balance: Decimal
    currency: str
    is_active: bool

    class Config:
        from_attributes = True


# ── Transaction ───────────────────────────────────────────────────────────────

class TransactionBase(BaseModel):
    account_id: int
    amount: Decimal
    type: Literal['income', 'expense', 'transfer']
    category_id: Optional[int] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    transaction_date: Union[date, datetime]


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: Optional[int] = None
    amount: Optional[Decimal] = None
    category_id: Optional[int] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    transaction_date: Optional[date] = None


class TransactionOut(TransactionBase):
    id: int
    confidence_score: Optional[float] = None
    category: Optional[CategoryOut] = None

    class Config:
        from_attributes = True


# ── Other Schemas (Budgets, Goals, etc.) ──────────────────────────────────────

class BudgetCreate(BaseModel):
    category_id: int
    amount: Decimal
    month: str  # YYYY-MM


class BudgetOut(BaseModel):
    id: int
    category_id: int
    amount: Decimal
    month: str
    category: CategoryOut

    class Config:
        from_attributes = True


class GoalCreate(BaseModel):
    name: str
    target_amount: Decimal
    deadline: Optional[date] = None


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    deadline: Optional[date] = None


class GoalOut(GoalCreate):
    id: int
    current_amount: Decimal

    class Config:
        from_attributes = True

# ── Recurring Rules ───────────────────────────────────────────────────────────

class RecurringRuleOut(BaseModel):
    id: int
    merchant_pattern: Optional[str] = None
    category_id: Optional[int] = None
    expected_amount: Optional[Decimal] = None
    interval_days: Optional[int] = None
    next_expected_date: Optional[date] = None
    is_subscription: bool

    class Config:
        from_attributes = True

class RecurringRuleUpdate(BaseModel):
    category_id: Optional[int] = None
    is_subscription: Optional[bool] = None


# ── Receipts ──────────────────────────────────────────────────────────────────

class ReceiptOut(BaseModel):
    id: int
    transaction_id: Optional[int] = None
    file_path: str
    merchant: Optional[str] = None
    total_amount: Optional[Decimal] = None
    receipt_date: Optional[date] = None

    class Config:
        from_attributes = True

class ReceiptExtracted(BaseModel):
    merchant: Optional[str] = None
    total_amount: Optional[Decimal] = None
    receipt_date: Optional[date] = None
    tax_amount: Optional[Decimal] = None
    raw_text: str


# ── Analytics ─────────────────────────────────────────────────────────────────

class MonthSummary(BaseModel):
    total: Decimal
    change: float


class DashboardSummary(BaseModel):
    total_balance: Decimal
    this_month_income: MonthSummary
    this_month_expenses: MonthSummary
    savings_rate: float

    class Config:
        from_attributes = True

class BudgetSummaryItem(BaseModel):
    category_id: Optional[int]
    category_name: str
    budget_amount: float
    spent_amount: float
    remaining: float
    pct_used: float

class GoalPlan(BaseModel):
    months_remaining: Optional[int] = None
    required_monthly: Optional[float] = None
    current_surplus: float
    is_achievable: bool
    tradeoff_suggestions: List[str]

class CashflowForecast(BaseModel):
    days: int
    current_balance: Decimal
    forecast: List[dict]
    assumptions: List[str]

class HealthScoreFactor(BaseModel):
    name: str
    score: float
    max_score: int
    description: str
    tip: Optional[str] = None

class HealthScore(BaseModel):
    total_score: float
    grade: str
    factors: List[HealthScoreFactor]
    disclaimer: str

class AnomalyOut(BaseModel):
    transaction_id: int
    transaction_date: datetime
    merchant: Optional[str] = None
    amount: Decimal
    category_name: Optional[str] = None
    anomaly_type: str
    severity: str
    message: str

class SpendingTrend(BaseModel):
    month: str
    category_name: str
    total_spent: Decimal