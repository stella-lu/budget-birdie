from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budgeting import set_goal
from app.db import get_db
from app.models import Category, CategoryGroup
from app.schemas import CategoryCreate, CategoryGroupCreate, CategoryGroupOut, CategoryOut, GoalRequest, NoteRequest

router = APIRouter(tags=["categories"])


@router.get("/category-groups", response_model=list[CategoryGroupOut])
def list_category_groups(db: Session = Depends(get_db)):
    return db.scalars(select(CategoryGroup).order_by(CategoryGroup.sort_order, CategoryGroup.name)).all()


@router.post("/category-groups", response_model=CategoryGroupOut)
def create_category_group(payload: CategoryGroupCreate, db: Session = Depends(get_db)):
    group = CategoryGroup(name=payload.name, sort_order=payload.sort_order)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()


@router.post("/categories", response_model=CategoryOut)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    category = Category(name=payload.name, group_id=payload.group_id, sort_order=payload.sort_order)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}/goal", response_model=CategoryOut)
def put_goal(category_id: int, payload: GoalRequest, db: Session = Depends(get_db)):
    return set_goal(db, category_id, payload.goal_type, payload.goal_amount_cents, payload.goal_date)


@router.put("/categories/{category_id}/note", response_model=CategoryOut)
def put_note(category_id: int, payload: NoteRequest, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "Category not found")
    category.note = payload.note
    db.commit()
    db.refresh(category)
    return category
