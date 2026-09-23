from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budgeting import create_transaction, delete_transaction, update_transaction
from app.db import get_db
from app.models import Payee, Transaction
from app.schemas import TransactionCreate, TransactionOut, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _to_out(db: Session, txn: Transaction) -> TransactionOut:
    out = TransactionOut.model_validate(txn)
    if txn.payee_id:
        payee = db.get(Payee, txn.payee_id)
        out.payee_name = payee.name if payee else None
    return out


@router.get("", response_model=list[TransactionOut])
def list_transactions(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    stmt = select(Transaction).order_by(Transaction.date.desc(), Transaction.id.desc())
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    return [_to_out(db, t) for t in db.scalars(stmt).all()]


@router.post("", response_model=TransactionOut)
def create(payload: TransactionCreate, db: Session = Depends(get_db)):
    txn = create_transaction(db, payload)
    return _to_out(db, txn)


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update(transaction_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)):
    txn = update_transaction(db, transaction_id, payload)
    return _to_out(db, txn)


@router.delete("/{transaction_id}", status_code=204)
def delete(transaction_id: int, db: Session = Depends(get_db)):
    delete_transaction(db, transaction_id)
