from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category, Transaction
from app.schemas import IncomeVsExpenseOut, SpendingByCategoryOut

router = APIRouter(prefix="/reports", tags=["reports"])


def _default_range(start: Optional[date], end: Optional[date]):
    end = end or date.today()
    start = start or (end - timedelta(days=180))
    return start, end


@router.get("/spending-by-category", response_model=list[SpendingByCategoryOut])
def spending_by_category(start: Optional[date] = None, end: Optional[date] = None, db: Session = Depends(get_db)):
    start, end = _default_range(start, end)
    rows = db.execute(
        select(Category.id, Category.name, func.sum(Transaction.budget_amount_cents))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Category.is_system.is_(False),
            Transaction.is_transfer.is_(False),
            Transaction.budget_amount_cents < 0,
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .group_by(Category.id)
        .order_by(func.sum(Transaction.budget_amount_cents))
    ).all()
    return [
        SpendingByCategoryOut(category_id=r[0], category_name=r[1], total_cents=-r[2])
        for r in rows
    ]


@router.get("/income-vs-expense", response_model=list[IncomeVsExpenseOut])
def income_vs_expense(start: Optional[date] = None, end: Optional[date] = None, db: Session = Depends(get_db)):
    start, end = _default_range(start, end)
    month_expr = func.strftime("%Y-%m", Transaction.date)
    rows = db.execute(
        select(
            month_expr,
            func.sum(func.max(Transaction.amount_cents, 0)),
            func.sum(func.min(Transaction.amount_cents, 0)),
        )
        .where(
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .group_by(month_expr)
        .order_by(month_expr)
    ).all()
    return [
        IncomeVsExpenseOut(month=r[0], income_cents=r[1] or 0, expense_cents=-(r[2] or 0))
        for r in rows
    ]
