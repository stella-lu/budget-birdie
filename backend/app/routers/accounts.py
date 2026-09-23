from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budgeting import account_balance_cents, get_or_create_payment_category
from app.db import get_db
from app.models import Account
from app.schemas import AccountCreate, AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.scalars(select(Account)).all()
    out = []
    for a in accounts:
        item = AccountOut.model_validate(a)
        item.balance_cents = account_balance_cents(db, a.id)
        out.append(item)
    return out


@router.post("", response_model=AccountOut)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account = Account(name=payload.name, type=payload.type)
    db.add(account)
    db.flush()
    if account.type == "credit":
        get_or_create_payment_category(db, account)
    db.commit()
    db.refresh(account)
    item = AccountOut.model_validate(account)
    item.balance_cents = 0
    return item
