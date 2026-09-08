"""
Remaining routers: categories, budgets, recurring, goals, receipts, analytics, chat.
All in one file for brevity; split into separate files if the project grows.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import os, shutil, uuid
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.models import (
    Category, Budget, RecurringRule, SavingsGoal, Receipt, Transaction, Account
)
from app.schemas.schemas import (
    CategoryCreate, CategoryOut,
    BudgetCreate, BudgetOut, BudgetSummaryItem,
    RecurringRuleOut, RecurringRuleUpdate,
    GoalCreate, GoalUpdate, GoalOut, GoalPlan, DashboardSummary,
    ReceiptOut, ReceiptExtracted,
    ChatRequest, ChatResponse,
    CashflowForecast, HealthScore, AnomalyOut, SpendingTrend,
)

settings = get_settings()

# ── Categories ────────────────────────────────────────────────────────────────
categories_router = APIRouter(prefix="/categories", tags=["categories"])


@categories_router.get("", response_model=List[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Category).filter(
        (Category.user_id == current_user.id) | (Category.is_system == 1),
        Category.is_active == 1,
    ).all()


@categories_router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    body: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = Category(user_id=current_user.id, **body.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@categories_router.put("/{cat_id}", response_model=CategoryOut)
def update_category(
    cat_id: int,
    body: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = db.query(Category).filter(
        Category.id == cat_id, Category.user_id == current_user.id
    ).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    cat.name = body.name
    cat.parent_category_id = body.parent_category_id
    db.commit()
    db.refresh(cat)
    return cat


@categories_router.delete("/{cat_id}", status_code=204)
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cat = db.query(Category).filter(
        Category.id == cat_id, Category.user_id == current_user.id, Category.is_system == 0
    ).first()
    if not cat:
        raise HTTPException(404, "Category not found or is a system category")
    cat.is_active = 0
    db.commit()


# ── Budgets ───────────────────────────────────────────────────────────────────
budgets_router = APIRouter(prefix="/budgets", tags=["budgets"])


@budgets_router.get("", response_model=List[BudgetOut])
def list_budgets(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Budget).filter(Budget.user_id == current_user.id)
    if month:
        q = q.filter(Budget.month == month)
    return q.all()


@budgets_router.post("", response_model=BudgetOut, status_code=201)
def create_budget(
    body: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = Budget(user_id=current_user.id, **body.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@budgets_router.put("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    body: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id, Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(404, "Budget not found")
    for field, value in body.model_dump().items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return budget


@budgets_router.delete("/{budget_id}", status_code=204)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budget = db.query(Budget).filter(
        Budget.id == budget_id, Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(404, "Budget not found")
    db.delete(budget)
    db.commit()


@budgets_router.get("/summary")
def budget_summary(
    month: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id, Budget.month == month
    ).all()

    result = []
    for b in budgets:
        spent = db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == b.category_id,
            Transaction.type == "expense",
            Transaction.transaction_date.like(f"{month}%"),
        ).all()
        spent_total = sum(float(t.amount) for t in spent)
        cat_name = b.category.name if b.category else "Total"
        result.append({
            "category_id": b.category_id,
            "category_name": cat_name,
            "budget_amount": float(b.amount),
            "spent_amount": spent_total,
            "remaining": float(b.amount) - spent_total,
            "pct_used": round(spent_total / float(b.amount) * 100, 1) if b.amount else 0,
        })
    return result


# ── Recurring ─────────────────────────────────────────────────────────────────
recurring_router = APIRouter(prefix="/recurring", tags=["recurring"])


@recurring_router.get("/rules", response_model=List[RecurringRuleOut])
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(RecurringRule).filter(RecurringRule.user_id == current_user.id).all()


@recurring_router.post("/detect")
def detect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.recurring import detect_recurring
    count = detect_recurring(db, current_user.id)
    return {"rules_created_or_updated": count}


@recurring_router.put("/rules/{rule_id}", response_model=RecurringRuleOut)
def update_rule(
    rule_id: int,
    body: RecurringRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(RecurringRule).filter(
        RecurringRule.id == rule_id, RecurringRule.user_id == current_user.id
    ).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@recurring_router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(RecurringRule).filter(
        RecurringRule.id == rule_id, RecurringRule.user_id == current_user.id
    ).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    db.delete(rule)
    db.commit()


@recurring_router.get("/subscriptions")
def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rules = db.query(RecurringRule).filter(
        RecurringRule.user_id == current_user.id,
        RecurringRule.is_subscription == 1,
    ).all()
    result = []
    for r in rules:
        monthly = (
            float(r.expected_amount) * 30 / r.interval_days
            if r.expected_amount and r.interval_days else 0
        )
        result.append({
            "id": r.id,
            "merchant": r.merchant_pattern,
            "expected_amount": float(r.expected_amount) if r.expected_amount else 0,
            "interval_days": r.interval_days,
            "next_expected_date": r.next_expected_date,
            "last_seen_date": r.last_seen_date,
            "monthly_cost": round(monthly, 2),
            "annual_cost": round(monthly * 12, 2),
        })
    return result


# ── Goals ─────────────────────────────────────────────────────────────────────
goals_router = APIRouter(prefix="/goals", tags=["goals"])


@goals_router.get("", response_model=List[GoalOut])
def list_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(SavingsGoal).filter(SavingsGoal.user_id == current_user.id).all()


@goals_router.post("", response_model=GoalOut, status_code=201)
def create_goal(
    body: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = SavingsGoal(user_id=current_user.id, **body.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@goals_router.put("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: int,
    body: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal


@goals_router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id
    ).first()
    if not goal:
        raise HTTPException(404, "Goal not found")
    db.delete(goal)
    db.commit()


# ── Goal Planning ─────────────────────────────────────────────────────────────

@goals_router.get("/{goal_id}/plan")
def goal_plan(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a data-driven, deadline-aware savings plan for a goal.

    The plan considers:

    - Goal target amount
    - Current progress
    - Goal deadline
    - Days remaining
    - Recent income
    - Recent expenses
    - Current monthly surplus
    - Existing budgets
    - Budget priorities
    - Recent spending patterns

    It returns:

    - Remaining goal amount
    - Progress percentage
    - Days/months remaining
    - Required monthly contribution
    - Average monthly income
    - Average monthly expenses
    - Current surplus
    - Available savings capacity
    - Savings capacity before deadline
    - Monthly gap
    - Deadline shortfall
    - Achievability
    - Projected completion
    - Budget-based suggestions
    - Human-readable trade-off suggestions
    """

    from dateutil.relativedelta import relativedelta

    # =========================================================
    # 1. FIND GOAL
    # =========================================================

    goal = (
        db.query(SavingsGoal)
        .filter(
            SavingsGoal.id == goal_id,
            SavingsGoal.user_id == current_user.id,
        )
        .first()
    )

    if not goal:
        raise HTTPException(
            status_code=404,
            detail="Goal not found",
        )

    # =========================================================
    # 2. BASIC GOAL INFORMATION
    # =========================================================

    target_amount = float(
        goal.target_amount or 0
    )

    current_amount = float(
        goal.current_amount or 0
    )

    remaining_amount = max(
        target_amount - current_amount,
        0,
    )

    today = date.today()

    # =========================================================
    # 3. DEADLINE CALCULATION
    # =========================================================

    days_remaining = None
    months_remaining = None
    required_monthly = None
    required_by_deadline = 0.0
    required_monthly_equivalent = None

    if goal.deadline:

        days_remaining = (
            goal.deadline - today
        ).days

        # The actual amount still required before the deadline.
        required_by_deadline = remaining_amount

        # -----------------------------------------------------
        # Deadline already passed
        # -----------------------------------------------------

        if days_remaining <= 0:

            months_remaining = 0

            required_monthly = (
                remaining_amount
                if remaining_amount > 0
                else 0
            )

            required_monthly_equivalent = required_monthly

        # -----------------------------------------------------
        # Future deadline
        # -----------------------------------------------------

        else:

            delta = relativedelta(
                goal.deadline,
                today,
            )

            # A partial month counts as one planning month
            # for display.
            months_remaining = (
                delta.years * 12
                + delta.months
            )

            if delta.days > 0:
                months_remaining += 1

            months_remaining = max(
                months_remaining,
                1,
            )

            # IMPORTANT:
            # Use exact days for the real monthly-equivalent
            # pace needed to hit the deadline.
            #
            # Example:
            # INR 15,000 due in 8 days
            # = 15,000 / (8 / 30)
            # = INR 56,250 monthly-equivalent pace.
            deadline_months_exact = max(
                days_remaining / 30.0,
                1 / 30.0,
            )

            required_monthly_equivalent = (
                remaining_amount / deadline_months_exact
                if remaining_amount > 0
                else 0
            )

            # Keep required_monthly aligned with the real
            # deadline pace instead of treating a partial
            # month as a full month.
            required_monthly = required_monthly_equivalent

    # =========================================================
    # 4. LAST 90 DAYS TRANSACTIONS
    # =========================================================

    cutoff = (
        today
        - timedelta(days=90)
    )

    recent_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= cutoff,
        )
        .all()
    )

    # =========================================================
    # 5. INCOME / EXPENSE CALCULATION
    # =========================================================

    total_income = sum(
        float(transaction.amount or 0)
        for transaction in recent_transactions
        if transaction.type == "income"
    )

    total_expenses = sum(
        float(transaction.amount or 0)
        for transaction in recent_transactions
        if transaction.type == "expense"
    )

    # 90-day average converted to monthly average.
    average_monthly_income = (
        total_income / 3
    )

    average_monthly_expenses = (
        total_expenses / 3
    )

    # =========================================================
    # 6. CURRENT MONTHLY SURPLUS
    # =========================================================

    current_surplus = (
        average_monthly_income
        - average_monthly_expenses
    )

    # A negative surplus cannot be treated as
    # available savings.
    available_surplus = max(
        current_surplus,
        0,
    )

    # =========================================================
    # 7. RECOMMENDED MONTHLY SAVINGS
    # =========================================================

    recommended_monthly = round(
        available_surplus,
        2,
    )

    # =========================================================
    # 8. SAVINGS CAPACITY BEFORE DEADLINE
    # =========================================================

    savings_capacity_by_deadline = None

    if (
        goal.deadline
        and days_remaining is not None
        and days_remaining > 0
    ):

        # Approximate monthly surplus converted
        # into the number of days remaining.
        savings_capacity_by_deadline = round(
            available_surplus
            * (days_remaining / 30),
            2,
        )

    # =========================================================
    # 9. ACHIEVABILITY
    # =========================================================

    if remaining_amount <= 0:

        # Goal is already completed.
        is_achievable = True

    elif not goal.deadline:

        # No deadline:
        # We can only determine whether the
        # monthly surplus can support the
        # required contribution.
        is_achievable = (
            required_monthly is not None
            and available_surplus >= required_monthly
        )

    elif (
        days_remaining is not None
        and days_remaining <= 0
    ):

        # Deadline has passed.
        is_achievable = False

    else:

        # IMPORTANT:
        # Compare the amount that can realistically
        # be saved before the deadline with the
        # remaining goal amount.

        is_achievable = (
            savings_capacity_by_deadline is not None
            and savings_capacity_by_deadline
            >= remaining_amount
        )

    # =========================================================
    # 10. MONTHLY GAP
    # =========================================================

    monthly_gap = 0.0

    if required_monthly is not None:

        monthly_gap = max(
            required_monthly
            - available_surplus,
            0,
        )

    monthly_gap = round(
        monthly_gap,
        2,
    )

    # =========================================================
    # 11. DEADLINE SHORTFALL
    # =========================================================

    deadline_shortfall = 0.0

    if (
        goal.deadline
        and remaining_amount > 0
        and savings_capacity_by_deadline is not None
    ):

        deadline_shortfall = max(
            remaining_amount
            - savings_capacity_by_deadline,
            0,
        )

    deadline_shortfall = round(
        deadline_shortfall,
        2,
    )

    # =========================================================
    # 12. CURRENT MONTH BUDGETS
    # =========================================================

    current_month = today.strftime(
        "%Y-%m"
    )

    budgets = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.month == current_month,
        )
        .all()
    )

    # =========================================================
    # 13. SPENDING BY CATEGORY
    # =========================================================

    category_spending = {}

    for transaction in recent_transactions:

        if transaction.type != "expense":
            continue

        category_id = (
            transaction.category_id
        )

        category_name = (
            transaction.category.name
            if transaction.category
            else "Other"
        )

        key = (
            category_id,
            category_name,
        )

        category_spending[key] = (
            category_spending.get(
                key,
                0,
            )
            + float(
                transaction.amount or 0
            )
        )

    # Highest spending first.
    spending_candidates = sorted(
        category_spending.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    # =========================================================
    # 14. BUDGET-BASED SUGGESTIONS
    # =========================================================

    budget_suggestions = []

    # We need to improve monthly savings if:
    #
    # 1. Monthly contribution is too high
    # OR
    # 2. Deadline shortfall exists.

    adjustment_needed = monthly_gap

    if deadline_shortfall > 0:

        if (
            days_remaining is not None
            and days_remaining > 0
        ):

            deadline_months = (
                days_remaining / 30
            )

            if deadline_months > 0:

                deadline_adjustment = (
                    deadline_shortfall
                    / deadline_months
                )

                adjustment_needed = max(
                    adjustment_needed,
                    deadline_adjustment,
                )

    # ---------------------------------------------------------
    # Analyze existing budgets
    # ---------------------------------------------------------

    if (
        adjustment_needed > 0
        and budgets
    ):

        remaining_adjustment = (
            adjustment_needed
        )

        for (
            (category_id, category_name),
            total_90_days,
        ) in spending_candidates:

            if remaining_adjustment <= 0:
                break

            # Convert 90-day spending into
            # approximate monthly spending.
            monthly_spending = (
                total_90_days / 3
            )

            # Find the matching category budget.
            matching_budget = next(
                (
                    budget
                    for budget in budgets
                    if budget.category_id
                    == category_id
                ),
                None,
            )

            if not matching_budget:
                continue

            budget_amount = float(
                matching_budget.amount or 0
            )

            # -------------------------------------------------
            # Safe reduction
            # -------------------------------------------------
            #
            # Never recommend cutting more than
            # 20% of the recent monthly spending
            # from a category.

            suggested_reduction = min(
                monthly_spending * 0.20,
                remaining_adjustment,
            )

            # Protect high-priority budgets.
            if (
                matching_budget.priority
                == "high"
            ):
                suggested_reduction *= 0.50

            suggested_reduction = round(
                max(
                    suggested_reduction,
                    0,
                ),
                2,
            )

            if suggested_reduction <= 0:
                continue

            budget_suggestions.append(
                {
                    "category": category_name,
                    "priority": (
                        matching_budget.priority
                    ),
                    "current_monthly_spending": round(
                        monthly_spending,
                        2,
                    ),
                    "budget": round(
                        budget_amount,
                        2,
                    ),
                    "suggested_reduction": (
                        suggested_reduction
                    ),
                }
            )

            remaining_adjustment = round(
                remaining_adjustment
                - suggested_reduction,
                2,
            )

    # =========================================================
    # 15. PROJECTED COMPLETION
    # =========================================================

    projected_months = None
    projected_completion_date = None

    if (
        remaining_amount > 0
        and available_surplus > 0
    ):

        projected_months = (
            remaining_amount
            / available_surplus
        )

        projected_months = round(
            projected_months,
            1,
        )

        projected_days = max(
            int(
                projected_months * 30
            ),
            1,
        )

        projected_completion_date = (
            today
            + timedelta(
                days=projected_days
            )
        )

    # =========================================================
    # 16. PROGRESS PERCENTAGE
    # =========================================================

    if target_amount > 0:

        progress_percentage = (
            current_amount
            / target_amount
        ) * 100

    else:

        progress_percentage = 100

    progress_percentage = round(
        min(
            max(
                progress_percentage,
                0,
            ),
            100,
        ),
        2,
    )

    # =========================================================
    # 17. HUMAN-READABLE SUGGESTIONS
    # =========================================================

    suggestions = []

    # ---------------------------------------------------------
    # Goal completed
    # ---------------------------------------------------------

    if remaining_amount <= 0:

        suggestions.append(
            "This goal has already been fully funded."
        )

    # ---------------------------------------------------------
    # No deadline
    # ---------------------------------------------------------

    elif not goal.deadline:

        if available_surplus > 0:

            suggestions.append(
                f"Your current savings capacity is "
                f"approximately INR "
                f"{available_surplus:,.0f} per month."
            )

            suggestions.append(
                f"Consider contributing around INR "
                f"{available_surplus:,.0f} per month "
                "toward this goal."
            )

        else:

            suggestions.append(
                "You currently do not have a positive "
                "monthly savings surplus."
            )

            suggestions.append(
                "Reduce expenses or increase income "
                "before committing to a monthly goal contribution."
            )

    # ---------------------------------------------------------
    # Deadline passed
    # ---------------------------------------------------------

    elif (
        days_remaining is not None
        and days_remaining <= 0
    ):

        suggestions.append(
            "The goal deadline has passed."
        )

        suggestions.append(
            "Consider updating the deadline or "
            "increasing the amount you can save."
        )

    # ---------------------------------------------------------
    # Goal achievable
    # ---------------------------------------------------------

    elif is_achievable:

        suggestions.append(
            f"You can potentially save approximately "
            f"INR "
            f"{savings_capacity_by_deadline:,.0f} "
            "before the deadline based on your "
            "recent savings pattern."
        )

        suggestions.append(
            f"You need approximately INR "
            f"{remaining_amount:,.0f} to complete "
            "this goal."
        )

        suggestions.append(
            "Your current savings pattern is sufficient "
            "to reach this goal by the deadline."
        )

        if (
            required_monthly is not None
            and available_surplus
            > required_monthly
        ):

            extra = (
                available_surplus
                - required_monthly
            )

            suggestions.append(
                f"You have approximately INR "
                f"{extra:,.0f} of additional monthly "
                "surplus after the required contribution."
            )

    # ---------------------------------------------------------
    # Goal NOT achievable
    # ---------------------------------------------------------

    else:

        if (
            required_monthly is not None
            and available_surplus
            < required_monthly
        ):

            suggestions.append(
                f"You need approximately INR "
                f"{required_monthly:,.0f} per month "
                f"but currently have about INR "
                f"{available_surplus:,.0f} available."
            )

        if savings_capacity_by_deadline is not None:

            suggestions.append(
                f"Based on your current savings pattern, "
                f"you could save approximately INR "
                f"{savings_capacity_by_deadline:,.0f} "
                "before the deadline."
            )

        if deadline_shortfall > 0:

            suggestions.append(
                f"You have a deadline shortfall of "
                f"approximately INR "
                f"{deadline_shortfall:,.0f}."
            )

        suggestions.append(
            "Consider reducing discretionary spending, "
            "increasing income, or extending the goal deadline."
        )

        if projected_completion_date:

            suggestions.append(
                f"At your current savings rate, "
                f"the goal is projected to be completed "
                f"around "
                f"{projected_completion_date.strftime('%d %b %Y')}."
            )

    # =========================================================
    # 18. ADD BUDGET SUGGESTIONS TO TEXT
    # =========================================================

    for item in budget_suggestions:

        suggestions.append(
            f"Consider reducing "
            f"{item['category']} spending by "
            f"approximately INR "
            f"{item['suggested_reduction']:,.0f} "
            "per month."
        )

    # If we still have a gap and couldn't find
    # a suitable budget category.
    if (
        not is_achievable
        and adjustment_needed > 0
        and not budget_suggestions
    ):

        suggestions.append(
            "No suitable budget category was found "
            "for a safe spending reduction. "
            "Consider increasing income or adjusting "
            "the goal deadline."
        )

    # =========================================================
    # 19. FINAL RESPONSE
    # =========================================================

    return {
        # -----------------------------------------------------
        # Goal
        # -----------------------------------------------------

        "goal": goal,

        # -----------------------------------------------------
        # Basic amounts
        # -----------------------------------------------------

        "target_amount": round(
            target_amount,
            2,
        ),

        "current_amount": round(
            current_amount,
            2,
        ),

        "remaining_amount": round(
            remaining_amount,
            2,
        ),

        "progress_percentage": (
            progress_percentage
        ),

        # -----------------------------------------------------
        # Deadline
        # -----------------------------------------------------

        "deadline": (
            goal.deadline
            if goal.deadline
            else None
        ),

        "days_remaining": (
            days_remaining
        ),

        "months_remaining": (
            months_remaining
        ),

        # -----------------------------------------------------
        # Required savings
        # -----------------------------------------------------

        "required_monthly": (
            round(
                required_monthly,
                2,
            )
            if required_monthly is not None
            else None
        ),

        "required_by_deadline": round(
            required_by_deadline,
            2,
        ),

        "required_monthly_equivalent": (
            round(
                required_monthly_equivalent,
                2,
            )
            if required_monthly_equivalent is not None
            else None
        ),

        # -----------------------------------------------------
        # Financial history
        # -----------------------------------------------------

        "average_monthly_income": round(
            average_monthly_income,
            2,
        ),

        "average_monthly_expenses": round(
            average_monthly_expenses,
            2,
        ),

        "current_surplus": round(
            current_surplus,
            2,
        ),

        "available_surplus": round(
            available_surplus,
            2,
        ),

        # -----------------------------------------------------
        # Savings planning
        # -----------------------------------------------------

        "recommended_monthly": round(
            recommended_monthly,
            2,
        ),

        "savings_capacity_by_deadline": (
            savings_capacity_by_deadline
        ),

        "monthly_gap": round(
            monthly_gap,
            2,
        ),

        "deadline_shortfall": round(
            deadline_shortfall,
            2,
        ),

        # -----------------------------------------------------
        # Achievability
        # -----------------------------------------------------

        "is_achievable": (
            is_achievable
        ),

        # -----------------------------------------------------
        # Projection
        # -----------------------------------------------------

        "projected_months": (
            projected_months
        ),

        "projected_completion_date": (
            projected_completion_date
        ),

        # -----------------------------------------------------
        # Budget intelligence
        # -----------------------------------------------------

        "budget_suggestions": (
            budget_suggestions
        ),

        # -----------------------------------------------------
        # Human-readable advice
        # -----------------------------------------------------

        "tradeoff_suggestions": (
            suggestions
        ),
    }

# ── Receipts ──────────────────────────────────────────────────────────────────
receipts_router = APIRouter(prefix="/receipts", tags=["receipts"])


@receipts_router.post("/upload", status_code=201)
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.ocr import process_receipt, validate_file

    # Validate file type BEFORE saving to disk
    validate_file(file.filename or "", file.content_type or "")

    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # process_receipt raises HTTPException with clear message on failure
    extracted = process_receipt(file_path)

    receipt = Receipt(
        user_id=current_user.id,
        file_path=file_path,
        merchant=extracted.get("merchant"),
        total_amount=extracted.get("total_amount"),
        receipt_date=extracted.get("receipt_date"),
        tax_amount=extracted.get("tax_amount"),
        ocr_raw_text=extracted.get("raw_text"),
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return {
        "id": receipt.id,
        "transaction_id": receipt.transaction_id,
        "file_path": receipt.file_path,
        "merchant": receipt.merchant,
        "total_amount": receipt.total_amount,
        "receipt_date": receipt.receipt_date,
        "tax_amount": receipt.tax_amount,
        "ocr_raw_text": receipt.ocr_raw_text,
        "created_at": receipt.created_at,
    }


@receipts_router.get("", response_model=List[ReceiptOut])
def list_receipts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Receipt).filter(Receipt.user_id == current_user.id).all()


@receipts_router.get("/{receipt_id}", response_model=ReceiptOut)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(Receipt).filter(
        Receipt.id == receipt_id, Receipt.user_id == current_user.id
    ).first()
    if not r:
        raise HTTPException(404, "Receipt not found")
    return r


@receipts_router.delete("/{receipt_id}", status_code=204)
def delete_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(Receipt).filter(
        Receipt.id == receipt_id, Receipt.user_id == current_user.id
    ).first()
    if not r:
        raise HTTPException(404, "Receipt not found")
    db.delete(r)
    db.commit()


@receipts_router.post("/{receipt_id}/link-transaction")
def link_transaction(
    receipt_id: int,
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = db.query(Receipt).filter(
        Receipt.id == receipt_id, Receipt.user_id == current_user.id
    ).first()
    if not r:
        raise HTTPException(404, "Receipt not found")
    r.transaction_id = transaction_id
    db.commit()
    return {"message": "Linked"}


# ── Analytics ─────────────────────────────────────────────────────────────────
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/dashboard-summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Provides key metrics for the main user dashboard."""
    from app.services import analytics as analytics_service
    return analytics_service.get_dashboard_summary(db, current_user.id)


@analytics_router.get("/cashflow")
def cashflow(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.forecasting import build_forecast
    return build_forecast(db, current_user.id, days)


@analytics_router.get("/health-score")
def health_score(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.health_score import compute_health_score
    return compute_health_score(db, current_user.id)


@analytics_router.get("/anomalies")
def anomalies(
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.anomaly import detect_anomalies
    return detect_anomalies(db, current_user.id, days)


@analytics_router.get("/spending-trends")
def spending_trends(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import timedelta
    from app.models.models import Transaction, Category

    cutoff = date.today() - timedelta(days=months * 30)
    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        Transaction.transaction_date >= cutoff,
    ).all()

    # Group by month + category
    data: dict = {}
    for t in txns:
        month = t.transaction_date.strftime("%Y-%m")
        cat_name = t.category.name if t.category else "Other"
        key = (month, cat_name)
        data[key] = data.get(key, 0) + float(t.amount)

    return [
        {"month": k[0], "category_name": k[1], "total_spent": round(v, 2)}
        for k, v in sorted(data.items())
    ]


# ── Portfolio intelligence ────────────────────────────────────────────────────
@analytics_router.get("/net-worth")
def net_worth(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accounts = db.query(Account).filter(Account.user_id == current_user.id, Account.is_active == 1).all()
    assets = sum(float(a.balance) for a in accounts if a.type not in ("loan", "credit_card"))
    liabilities = sum(abs(float(a.balance)) for a in accounts if a.type in ("loan", "credit_card"))
    return {"assets": round(assets,2), "liabilities": round(liabilities,2), "net_worth": round(assets-liabilities,2)}

@analytics_router.get("/emergency-fund")
def emergency_fund(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=90)
    tx = db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.type == "expense", Transaction.transaction_date >= cutoff).all()
    monthly = sum(float(t.amount) for t in tx) / 3 if tx else 0
    balances = sum(float(a.balance) for a in db.query(Account).filter(Account.user_id == current_user.id, Account.is_active == 1).all())
    months = balances / monthly if monthly else 0
    return {"monthly_essential_estimate": round(monthly,2), "available_balance": round(balances,2), "months_covered": round(months,2), "target_3_months": round(monthly*3,2), "target_6_months": round(monthly*6,2)}

@analytics_router.get("/budget-recommendations")
def budget_recommendations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=90)
    tx = db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.type == "expense", Transaction.transaction_date >= cutoff).all()
    groups = {}
    for t in tx:
        name = t.category.name if t.category else "Other"
        groups[name] = groups.get(name, 0) + float(t.amount)
    return [{"category":name,"average_monthly":round(total/3,2),"recommended_budget":round(total/3*1.10,2),"buffer":round(total/3*.10,2),"reason":"90-day average plus a 10% variability buffer"} for name,total in sorted(groups.items(), key=lambda x:-x[1])[:12]]

@analytics_router.get("/what-if")
def what_if(reduction: float = Query(..., gt=0), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start=date.today().replace(day=1)
    tx=db.query(Transaction).filter(Transaction.user_id==current_user.id,Transaction.transaction_date>=start).all()
    income=sum(float(t.amount) for t in tx if t.type=="income"); expense=sum(float(t.amount) for t in tx if t.type=="expense")
    days=max(date.today().day,1); monthly=expense/days*30
    current=max(0,income-monthly); projected=max(0,income-max(0,monthly-reduction))
    return {"reduction":reduction,"current_monthly_savings":round(current,2),"projected_monthly_savings":round(projected,2),"annual_improvement":round(reduction*12,2)}

@analytics_router.get("/monthly-report")
def monthly_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today=date.today(); start=today.replace(day=1); prev_end=start-timedelta(days=1); prev_start=prev_end.replace(day=1)
    def totals(a,b):
        tx=db.query(Transaction).filter(Transaction.user_id==current_user.id,Transaction.transaction_date>=a,Transaction.transaction_date<datetime.combine(b+timedelta(days=1),datetime.min.time())).all()
        return sum(float(t.amount) for t in tx if t.type=="income"),sum(float(t.amount) for t in tx if t.type=="expense")
    inc,exp=totals(start,today); pinc,pexp=totals(prev_start,prev_end)
    return {"month":today.strftime("%Y-%m"),"income":round(inc,2),"expenses":round(exp,2),"savings":round(inc-exp,2),"savings_rate":round((inc-exp)/inc*100,2) if inc else 0,"expense_change_pct":round((exp-pexp)/pexp*100,2) if pexp else 0,"income_change_pct":round((inc-pinc)/pinc*100,2) if pinc else 0}


# ── Savings Planning ───────────────────────────────────────────────────────────

@analytics_router.get("/savings-plan")
def savings_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Build a practical monthly savings plan from the user's real FinWise data.

    Uses:
      - Last 90 days of income and expenses
      - Current account balances
      - Current-month spending pace
      - Active savings goals and their deadlines
      - Existing budget limits

    The endpoint does not create or modify transactions, budgets, or goals.
    It only calculates recommendations from the user's data.
    """

    today = date.today()
    month_start = today.replace(day=1)

    # ---------------------------------------------------------
    # 1. Recent financial history
    # ---------------------------------------------------------
    cutoff = today - timedelta(days=90)

    recent_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= cutoff,
        )
        .all()
    )

    total_90d_income = sum(
        float(t.amount or 0)
        for t in recent_transactions
        if t.type == "income"
    )

    total_90d_expenses = sum(
        float(t.amount or 0)
        for t in recent_transactions
        if t.type == "expense"
    )

    average_monthly_income = total_90d_income / 3
    average_monthly_expenses = total_90d_expenses / 3
    historical_surplus = average_monthly_income - average_monthly_expenses

    # ---------------------------------------------------------
    # 2. Current-month actuals
    # ---------------------------------------------------------
    current_month_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= month_start,
        )
        .all()
    )

    current_month_income = sum(
        float(t.amount or 0)
        for t in current_month_transactions
        if t.type == "income"
    )

    current_month_expenses = sum(
        float(t.amount or 0)
        for t in current_month_transactions
        if t.type == "expense"
    )

    days_elapsed = max(today.day, 1)

    # Project the current month's spending pace to a 30-day month.
    projected_current_month_expenses = (
        current_month_expenses / days_elapsed * 30
    )

    current_month_surplus = current_month_income - current_month_expenses

    # If current-month income is not available yet, use the 90-day average.
    planning_income = (
        current_month_income
        if current_month_income > 0
        else average_monthly_income
    )

    # For expense planning, use the higher of historical average and
    # current-month spending pace. This makes the recommendation conservative.
    planning_expenses = max(
        average_monthly_expenses,
        projected_current_month_expenses
        if current_month_expenses > 0
        else average_monthly_expenses,
    )

    planning_surplus = max(
        planning_income - planning_expenses,
        0,
    )

    # ---------------------------------------------------------
    # 3. Current account balance
    # ---------------------------------------------------------
    accounts = (
        db.query(Account)
        .filter(
            Account.user_id == current_user.id,
            Account.is_active == 1,
        )
        .all()
    )

    current_balance = sum(
        float(account.balance or 0)
        for account in accounts
    )

    # ---------------------------------------------------------
    # 4. Active savings goals
    # ---------------------------------------------------------
    goals = (
        db.query(SavingsGoal)
        .filter(
            SavingsGoal.user_id == current_user.id,
        )
        .all()
    )

    goal_plans = []
    required_goal_contribution = 0.0
    goal_amount_required_by_deadlines = 0.0

    for goal in goals:
        target = float(goal.target_amount or 0)
        current = float(goal.current_amount or 0)
        remaining = max(target - current, 0)

        if remaining <= 0:
            continue

        goal_required_monthly = None
        goal_required_monthly_equivalent = None
        goal_days_remaining = None
        goal_months_remaining = None
        goal_required_by_deadline = 0.0

        if goal.deadline:
            goal_days_remaining = (goal.deadline - today).days
            goal_required_by_deadline = remaining

            if goal_days_remaining > 0:
                # Use the exact number of remaining days for the
                # monthly-equivalent pace.
                goal_months_remaining = max(
                    goal_days_remaining / 30,
                    1 / 30,
                )

                goal_required_monthly_equivalent = (
                    remaining / goal_months_remaining
                )
                goal_required_monthly = (
                    goal_required_monthly_equivalent
                )

                goal_amount_required_by_deadlines += remaining

            else:
                goal_months_remaining = 0
                goal_required_monthly_equivalent = remaining
                goal_required_monthly = remaining
                goal_amount_required_by_deadlines += remaining

        elif goal.monthly_contribution:
            goal_required_monthly = float(
                goal.monthly_contribution
            )
            goal_required_monthly_equivalent = goal_required_monthly

        if goal_required_monthly is None:
            # No deadline/contribution: do not force an arbitrary amount
            # into the monthly savings commitment.
            goal_required_monthly = 0.0

        if goal_required_monthly_equivalent is None:
            goal_required_monthly_equivalent = goal_required_monthly

        goal_required_monthly = max(goal_required_monthly, 0)
        goal_required_monthly_equivalent = max(
            goal_required_monthly_equivalent,
            0,
        )

        required_goal_contribution += goal_required_monthly

        goal_plans.append({
            "id": goal.id,
            "name": goal.name,
            "priority": goal.priority,
            "target_amount": round(target, 2),
            "current_amount": round(current, 2),
            "remaining_amount": round(remaining, 2),
            "deadline": goal.deadline,
            "days_remaining": goal_days_remaining,
            "required_by_deadline": round(
                goal_required_by_deadline,
                2,
            ),
            "required_monthly": round(
                goal_required_monthly,
                2,
            ),
            "required_monthly_equivalent": round(
                goal_required_monthly_equivalent,
                2,
            ),
        })

    required_goal_contribution = round(
        required_goal_contribution,
        2,
    )

    goal_amount_required_by_deadlines = round(
        goal_amount_required_by_deadlines,
        2,
    )

    # ---------------------------------------------------------
    # 5. Recommended savings
    # ---------------------------------------------------------
    # Keep a 10% cushion instead of recommending 100% of the
    # calculated surplus. This leaves room for normal variability.
    safe_surplus = max(
        planning_surplus * 0.90,
        0,
    )

    recommended_savings = min(
        safe_surplus,
        planning_surplus,
    )

    # Goal commitments have priority. If existing goal deadlines
    # require more than the safe recommendation, show the pressure
    # rather than pretending the plan is comfortable.
    goal_pressure = max(
        required_goal_contribution - recommended_savings,
        0,
    )

    # Amount that can reasonably remain available for discretionary
    # spending after the recommended savings contribution.
    safe_to_spend = max(
        planning_income
        - planning_expenses
        - recommended_savings,
        0,
    )

    # Savings available after accounting for required goal contributions.
    available_after_goals = max(
        recommended_savings - required_goal_contribution,
        0,
    )

    # ---------------------------------------------------------
    # 6. Savings rate
    # ---------------------------------------------------------
    if planning_income > 0:
        savings_rate = (
            recommended_savings
            / planning_income
            * 100
        )
    else:
        savings_rate = 0.0

    # ---------------------------------------------------------
    # 7. Current-month spending pace
    # ---------------------------------------------------------
    current_month_savings = (
        current_month_income - current_month_expenses
    )

    # ---------------------------------------------------------
    # 8. Financial status
    # ---------------------------------------------------------
    if planning_income <= 0:
        financial_status = "no_income_data"
    elif planning_surplus <= 0:
        financial_status = "needs_attention"
    elif goal_pressure > 0:
        financial_status = "goal_pressure"
    elif savings_rate >= 20:
        financial_status = "healthy"
    elif savings_rate >= 10:
        financial_status = "stable"
    else:
        financial_status = "improvable"

    # ---------------------------------------------------------
    # 9. Recommendations
    # ---------------------------------------------------------
    recommendations = []

    if planning_income <= 0:
        recommendations.append(
            "Add income transactions so FinWise can calculate a "
            "personalized savings target."
        )
    elif planning_surplus <= 0:
        recommendations.append(
            "Your planned expenses currently consume your estimated "
            "monthly income. Reduce discretionary spending or increase income "
            "before setting an aggressive savings target."
        )
    else:
        recommendations.append(
            f"Based on your recent cash flow, aim to save approximately "
            f"INR {recommended_savings:,.0f} per month."
        )

    if safe_to_spend > 0:
        recommendations.append(
            f"After planned expenses and savings, approximately "
            f"INR {safe_to_spend:,.0f} remains as flexible monthly spending."
        )

    if required_goal_contribution > 0:
        recommendations.append(
            f"Your active goal deadlines require a combined "
            f"monthly-equivalent savings pace of approximately "
            f"INR {required_goal_contribution:,.0f}."
        )

    if goal_amount_required_by_deadlines > 0:
        recommendations.append(
            f"You currently need to fund approximately "
            f"INR {goal_amount_required_by_deadlines:,.0f} "
            f"across goals with deadlines."
        )

    if goal_pressure > 0:
        recommendations.append(
            f"Your active goal commitments are approximately "
            f"INR {goal_pressure:,.0f} above the safer savings amount. "
            "Consider reducing discretionary expenses, increasing income, "
            "or extending a goal deadline."
        )

    if savings_rate < 20 and planning_surplus > 0:
        recommendations.append(
            "A gradual increase in your savings rate can strengthen your "
            "financial buffer without requiring a sudden spending cut."
        )

    if current_month_expenses > 0 and projected_current_month_expenses > average_monthly_expenses * 1.10:
        recommendations.append(
            "Your current-month spending pace is more than 10% above your "
            "recent average. Review discretionary categories before increasing savings."
        )

    if not recommendations:
        recommendations.append(
            "Continue tracking transactions and review this plan regularly."
        )

    # ---------------------------------------------------------
    # 10. Goal-specific planning details
    # ---------------------------------------------------------
    goal_plans.sort(
        key=lambda item: (
            0 if item["priority"] == "high" else
            1 if item["priority"] == "medium" else 2,
            item["days_remaining"]
            if item["days_remaining"] is not None
            else 999999,
        )
    )

    # ---------------------------------------------------------
    # 11. Final response
    # ---------------------------------------------------------
    return {
        "generated_for": today,

        "financial_status": financial_status,

        "monthly_income": round(
            planning_income,
            2,
        ),

        "average_monthly_income": round(
            average_monthly_income,
            2,
        ),

        "monthly_expenses": round(
            planning_expenses,
            2,
        ),

        "average_monthly_expenses": round(
            average_monthly_expenses,
            2,
        ),

        "monthly_surplus": round(
            planning_surplus,
            2,
        ),

        "historical_surplus": round(
            historical_surplus,
            2,
        ),

        "current_month_income": round(
            current_month_income,
            2,
        ),

        "current_month_expenses": round(
            current_month_expenses,
            2,
        ),

        "current_month_savings": round(
            current_month_savings,
            2,
        ),

        "projected_current_month_expenses": round(
            projected_current_month_expenses,
            2,
        ),

        "current_balance": round(
            current_balance,
            2,
        ),

        "recommended_savings": round(
            recommended_savings,
            2,
        ),

        "savings_rate": round(
            savings_rate,
            2,
        ),

        "safe_to_spend": round(
            safe_to_spend,
            2,
        ),

        "required_goal_contribution": round(
            required_goal_contribution,
            2,
        ),

        "goal_amount_required_by_deadlines": round(
            goal_amount_required_by_deadlines,
            2,
        ),

        "available_after_goals": round(
            available_after_goals,
            2,
        ),

        "goal_pressure": round(
            goal_pressure,
            2,
        ),

        "goals": goal_plans,

        "recommendations": recommendations,
    }


# ── AI Financial Insights ─────────────────────────────────────────────────────
@analytics_router.get("/insights")
def financial_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate explainable, data-driven financial insights.

    This endpoint intentionally uses the user's FinWise data directly instead
    of inventing advice. It combines:
      - current balance
      - current-month income/expenses
      - recent spending trends
      - budget usage
      - cash-flow forecast
      - anomalies
      - emergency-fund coverage
    """

    from app.services.forecasting import build_forecast

    today = date.today()
    month_start = today.replace(day=1)
    previous_month_end = month_start - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)
    last_90_days = today - timedelta(days=90)

    # ---------------------------------------------------------
    # Current month transactions
    # ---------------------------------------------------------
    current_tx = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= month_start,
        )
        .all()
    )

    income = sum(
        float(t.amount or 0)
        for t in current_tx
        if t.type == "income"
    )

    expenses = sum(
        float(t.amount or 0)
        for t in current_tx
        if t.type == "expense"
    )

    savings = income - expenses
    savings_rate = (savings / income * 100) if income else 0

    # ---------------------------------------------------------
    # Previous month comparison
    # ---------------------------------------------------------
    previous_tx = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= previous_month_start,
            Transaction.transaction_date < month_start,
        )
        .all()
    )

    previous_income = sum(
        float(t.amount or 0)
        for t in previous_tx
        if t.type == "income"
    )

    previous_expenses = sum(
        float(t.amount or 0)
        for t in previous_tx
        if t.type == "expense"
    )

    expense_change_pct = (
        (expenses - previous_expenses) / previous_expenses * 100
        if previous_expenses
        else 0
    )

    income_change_pct = (
        (income - previous_income) / previous_income * 100
        if previous_income
        else 0
    )

    # ---------------------------------------------------------
    # Spending by category — last 90 days
    # ---------------------------------------------------------
    recent_tx = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense",
            Transaction.transaction_date >= last_90_days,
        )
        .all()
    )

    category_totals = {}

    for transaction in recent_tx:
        category_name = (
            transaction.category.name
            if transaction.category
            else "Other"
        )
        category_totals[category_name] = (
            category_totals.get(category_name, 0)
            + float(transaction.amount or 0)
        )

    top_categories = [
        {
            "category": name,
            "total_90_days": round(total, 2),
            "average_monthly": round(total / 3, 2),
        }
        for name, total in sorted(
            category_totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
    ]

    # ---------------------------------------------------------
    # Current account balance
    # ---------------------------------------------------------
    accounts = (
        db.query(Account)
        .filter(
            Account.user_id == current_user.id,
            Account.is_active == 1,
        )
        .all()
    )

    current_balance = sum(
        float(account.balance or 0)
        for account in accounts
    )

    # ---------------------------------------------------------
    # Cash-flow forecast
    # ---------------------------------------------------------
    forecast = build_forecast(
        db,
        current_user.id,
        30,
    )

    forecast_rows = forecast.get("forecast", [])

    ending_balance = (
        float(forecast_rows[-1]["predicted_balance"])
        if forecast_rows
        else current_balance
    )

    lowest_balance = (
        min(
            float(row["predicted_balance"])
            for row in forecast_rows
        )
        if forecast_rows
        else current_balance
    )

    low_balance_days = sum(
        1
        for row in forecast_rows
        if row.get("is_low_balance")
    )

    # ---------------------------------------------------------
    # Anomalies
    # ---------------------------------------------------------
    from app.services.anomaly import detect_anomalies

    anomaly_result = detect_anomalies(
        db,
        current_user.id,
        90,
    )

    anomaly_count = len(anomaly_result or [])

    # ---------------------------------------------------------
    # Emergency fund
    # ---------------------------------------------------------
    monthly_expense_estimate = (
        sum(float(t.amount or 0) for t in recent_tx) / 3
        if recent_tx
        else 0
    )

    emergency_months = (
        current_balance / monthly_expense_estimate
        if monthly_expense_estimate > 0
        else 0
    )

    # ---------------------------------------------------------
    # Generate explainable insights
    # ---------------------------------------------------------
    insights = []

    if income > 0 and savings_rate >= 20:
        insights.append({
            "type": "positive",
            "priority": "high",
            "title": "Strong savings rate",
            "message": (
                f"You're saving {savings_rate:.1f}% of your income "
                "this month, which is a healthy positive cash-flow signal."
            ),
        })
    elif income > 0 and savings_rate < 0:
        insights.append({
            "type": "warning",
            "priority": "high",
            "title": "Expenses exceed income",
            "message": (
                f"You're currently spending about INR "
                f"{abs(savings):,.0f} more than your income this month."
            ),
        })
    elif income > 0:
        insights.append({
            "type": "neutral",
            "priority": "medium",
            "title": "Positive monthly cash flow",
            "message": (
                f"Your current monthly surplus is approximately "
                f"INR {savings:,.0f}."
            ),
        })

    if expense_change_pct > 10:
        insights.append({
            "type": "warning",
            "priority": "high",
            "title": "Spending increased",
            "message": (
                f"Expenses are up {expense_change_pct:.1f}% "
                "compared with the previous month."
            ),
        })
    elif expense_change_pct < -10:
        insights.append({
            "type": "positive",
            "priority": "medium",
            "title": "Spending decreased",
            "message": (
                f"Expenses are down {abs(expense_change_pct):.1f}% "
                "compared with the previous month."
            ),
        })

    if top_categories:
        top = top_categories[0]
        insights.append({
            "type": "info",
            "priority": "medium",
            "title": "Largest spending category",
            "message": (
                f"{top['category']} is your largest spending category "
                f"over the last 90 days at approximately "
                f"INR {top['total_90_days']:,.0f}."
            ),
        })

    if low_balance_days > 0:
        insights.append({
            "type": "warning",
            "priority": "high",
            "title": "Cash-flow risk detected",
            "message": (
                f"The 30-day forecast falls below the INR 3,000 "
                f"safety threshold on {low_balance_days} day(s)."
            ),
        })
    else:
        insights.append({
            "type": "positive",
            "priority": "medium",
            "title": "Cash-flow looks stable",
            "message": (
                "The projected balance stays above the INR 3,000 "
                "safety threshold over the forecast period."
            ),
        })

    if anomaly_count > 0:
        insights.append({
            "type": "warning",
            "priority": "medium",
            "title": "Review unusual transactions",
            "message": (
                f"FinWise detected {anomaly_count} spending "
                "anomaly review flag(s) in the last 90 days."
            ),
        })

    if emergency_months >= 6:
        insights.append({
            "type": "positive",
            "priority": "medium",
            "title": "Strong emergency coverage",
            "message": (
                f"Your current balance represents approximately "
                f"{emergency_months:.1f} months of recent spending."
            ),
        })
    elif 3 <= emergency_months < 6:
        insights.append({
            "type": "positive",
            "priority": "low",
            "title": "Emergency fund is developing",
            "message": (
                f"You currently have around {emergency_months:.1f} "
                "months of spending coverage."
            ),
        })
    elif emergency_months > 0:
        insights.append({
            "type": "warning",
            "priority": "medium",
            "title": "Build your emergency fund",
            "message": (
                f"Current coverage is about {emergency_months:.1f} months. "
                "Consider building toward a larger cash reserve."
            ),
        })

    # ---------------------------------------------------------
    # Simple action suggestions
    # ---------------------------------------------------------
    actions = []

    if top_categories:
        actions.append(
            f"Review your {top_categories[0]['category']} spending "
            "before setting next month's budget."
        )

    if expense_change_pct > 10:
        actions.append(
            "Compare this month's largest expenses with last month "
            "and identify the main source of the increase."
        )

    if low_balance_days > 0:
        actions.append(
            "Keep extra cash available before the forecasted "
            "low-balance dates."
        )

    if savings_rate < 20 and income > 0:
        actions.append(
            "Try increasing your monthly savings rate gradually "
            "by reducing one discretionary category."
        )

    if not actions:
        actions.append(
            "Continue tracking transactions and review your "
            "cash-flow forecast regularly."
        )

    return {
        "generated_for": today,
        "summary": {
            "current_balance": round(current_balance, 2),
            "monthly_income": round(income, 2),
            "monthly_expenses": round(expenses, 2),
            "monthly_savings": round(savings, 2),
            "savings_rate": round(savings_rate, 2),
            "income_change_pct": round(income_change_pct, 2),
            "expense_change_pct": round(expense_change_pct, 2),
            "projected_ending_balance": round(ending_balance, 2),
            "lowest_projected_balance": round(lowest_balance, 2),
            "emergency_months": round(emergency_months, 2),
            "anomaly_count": anomaly_count,
        },
        "top_spending_categories": top_categories,
        "insights": insights,
        "recommended_actions": actions,
    }


# ── Chat ──────────────────────────────────────────────────────────────────────
chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.get("/status")
def chat_status():
    """Return AI provider connectivity status for the frontend indicator."""
    provider = (settings.LLM_PROVIDER or "ollama").lower()
    if provider == "groq":
        from app.services.llm import check_groq_status
        online = check_groq_status()
        return {
            "ollama_enabled": False,
            "ollama_online": online,
            "model": settings.GROQ_MODEL,
            "provider": "groq",
        }
    from app.services.llm import check_ollama_status
    online = check_ollama_status()
    return {
        "ollama_enabled": settings.OLLAMA_ENABLED,
        "ollama_online": online,
        "model": settings.OLLAMA_MODEL,
        "provider": "ollama",
    }


@chat_router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import Conversation, ChatMessage as ChatMessageModel
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .limit(50)
        .all()
    )
    result = []
    for c in convs:
        last = (
            db.query(ChatMessageModel)
            .filter(ChatMessageModel.conversation_id == c.id)
            .order_by(ChatMessageModel.id.desc())
            .first()
        )
        result.append({
            "id": c.id,
            "title": c.title,
            "updated_at": c.updated_at,
            "last_message": (last.content[:80] if last else None),
        })
    return result


@chat_router.post("/conversations", status_code=201)
def create_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import Conversation
    conv = Conversation(user_id=current_user.id, title=None)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id}


@chat_router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import Conversation, ChatMessage as ChatMessageModel
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    msgs = (
        db.query(ChatMessageModel)
        .filter(ChatMessageModel.conversation_id == conversation_id)
        .order_by(ChatMessageModel.id.asc())
        .all()
    )
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at} for m in msgs]


@chat_router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.models import Conversation
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    db.delete(conv)
    db.commit()


@chat_router.post("")
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.llm import answer_with_llm
    from app.models.models import Conversation, ChatMessage as ChatMessageModel

    
    # Resolve or create conversation
    if body.conversation_id is not None:
        conv = db.query(Conversation).filter(
            Conversation.id == body.conversation_id,
            Conversation.user_id == current_user.id,
        ).first()
        if not conv:
            raise HTTPException(404, "Conversation not found")
    else:
        title = body.message.strip()[:40]
        if len(body.message.strip()) > 40:
            title += "..."
        conv = Conversation(user_id=current_user.id, title=title)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # Load history from DB (last 20 messages)
    past = (
    db.query(ChatMessageModel)
    .filter(ChatMessageModel.conversation_id == conv.id)
    .order_by(ChatMessageModel.id.desc())
    .limit(20)
    .all()
    )
    past.reverse()
    history = [{"role": m.role, "content": m.content} for m in past]

    # Save user message
    db.add(ChatMessageModel(conversation_id=conv.id, role="user", content=body.message))
    db.commit()

    # Call AI
    result = answer_with_llm(db, current_user.id, body.message, history)

    # Save assistant reply
    answer = result.get("answer_text", "")
    db.add(ChatMessageModel(conversation_id=conv.id, role="assistant", content=answer))

    # Update conversation timestamp
    conv.updated_at = datetime.utcnow()
    db.commit()

    result["conversation_id"] = conv.id
    return result