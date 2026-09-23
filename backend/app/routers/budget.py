from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budgeting import (
    assign_money,
    compute_category_activity_cents,
    compute_category_available_cents,
    compute_ready_to_assign_cents,
    month_start,
)
from app.db import get_db
from app.models import CategoryGroup, MonthlyAllocation
from app.schemas import AssignRequest, BudgetMonthOut, CategoryBudgetOut, CategoryGroupBudgetOut

router = APIRouter(prefix="/budget", tags=["budget"])


@router.get("/{month}", response_model=BudgetMonthOut)
def get_budget_month(month: date, db: Session = Depends(get_db)):
    month = month_start(month)
    groups = db.scalars(
        select(CategoryGroup).where(CategoryGroup.name.notin_(["Internal"])).order_by(CategoryGroup.sort_order, CategoryGroup.name)
    ).all()

    group_rows = []
    for group in groups:
        categories = sorted(group.categories, key=lambda c: (c.sort_order, c.name))
        cat_rows = []
        for cat in categories:
            assigned = db.scalar(
                select(MonthlyAllocation.assigned_cents).where(
                    MonthlyAllocation.category_id == cat.id, MonthlyAllocation.month == month
                )
            ) or 0
            activity = compute_category_activity_cents(db, cat.id, month)
            available = compute_category_available_cents(db, cat.id, month)
            cat_rows.append(
                CategoryBudgetOut(
                    id=cat.id,
                    name=cat.name,
                    group_id=cat.group_id,
                    is_system=cat.is_system,
                    sort_order=cat.sort_order,
                    assigned_cents=assigned,
                    activity_cents=activity,
                    available_cents=available,
                )
            )
        group_rows.append(
            CategoryGroupBudgetOut(id=group.id, name=group.name, sort_order=group.sort_order, categories=cat_rows)
        )

    return BudgetMonthOut(
        month=month,
        ready_to_assign_cents=compute_ready_to_assign_cents(db, month),
        groups=group_rows,
    )


@router.post("/assign")
def assign(payload: AssignRequest, db: Session = Depends(get_db)):
    row = assign_money(db, payload.category_id, payload.month, payload.assigned_cents)
    return {"category_id": row.category_id, "month": row.month, "assigned_cents": row.assigned_cents}
