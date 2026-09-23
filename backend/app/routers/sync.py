from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import simplefin
from app.db import get_db
from app.models import SimpleFinLink
from app.schemas import (
    LinkableAccountOut,
    LinkAccountRequest,
    SimpleFinConnectRequest,
    SimpleFinStatusOut,
    SyncResultOut,
)

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status", response_model=SimpleFinStatusOut)
def status():
    return SimpleFinStatusOut(connected=simplefin.is_connected())


@router.post("/connect", response_model=SimpleFinStatusOut)
def connect(payload: SimpleFinConnectRequest):
    simplefin.claim_setup_token(payload.setup_token)
    return SimpleFinStatusOut(connected=True)


@router.get("/simplefin-accounts", response_model=list[LinkableAccountOut])
def linkable_accounts(db: Session = Depends(get_db)):
    return simplefin.list_linkable_accounts(db)


@router.post("/link")
def link_account(payload: LinkAccountRequest, db: Session = Depends(get_db)):
    link = SimpleFinLink(
        account_id=payload.account_id,
        simplefin_account_id=payload.simplefin_account_id,
        simplefin_org_name=payload.simplefin_org_name,
    )
    db.add(link)
    db.commit()
    return {"ok": True}


@router.post("/run", response_model=SyncResultOut)
def run_sync(db: Session = Depends(get_db)):
    return simplefin.sync_all(db)
