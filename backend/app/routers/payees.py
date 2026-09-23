from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Payee
from app.schemas import PayeeOut

router = APIRouter(prefix="/payees", tags=["payees"])


@router.get("", response_model=list[PayeeOut])
def list_payees(db: Session = Depends(get_db)):
    return db.scalars(select(Payee).order_by(Payee.name)).all()
