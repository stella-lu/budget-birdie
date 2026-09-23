"""SimpleFIN Bridge client — https://www.simplefin.org/protocol.html

Setup is a one-time flow: the user pastes a "setup token" (obtained from their
SimpleFIN Bridge account after linking BoA/Chase/Wealthfront) which we exchange
for a permanent access URL. That URL embeds HTTP Basic Auth credentials, so it's
stored in the macOS Keychain (see app.keychain), never in the database or a file.
"""

import base64
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import keychain
from app.budgeting import (
    apply_credit_card_movements,
    compute_category_available_cents,
    get_or_create_payee,
    get_or_create_rta_category,
    month_start,
)
from app.models import Account, SimpleFinLink, Transaction

DEFAULT_LOOKBACK_DAYS = 30


def is_connected() -> bool:
    return keychain.get_secret() is not None


def claim_setup_token(setup_token: str) -> None:
    try:
        claim_url = base64.b64decode(setup_token.strip()).decode("utf-8")
    except Exception as e:
        raise HTTPException(422, "That doesn't look like a valid SimpleFIN setup token") from e

    resp = httpx.post(claim_url, timeout=30)
    if resp.status_code != 200 or not resp.text.strip():
        raise HTTPException(
            502, f"SimpleFIN rejected the setup token (HTTP {resp.status_code}). "
            "Setup tokens are single-use — generate a fresh one from SimpleFIN Bridge."
        )
    access_url = resp.text.strip()
    keychain.set_secret(access_url)


def _access_url() -> str:
    url = keychain.get_secret()
    if not url:
        raise HTTPException(400, "Not connected to SimpleFIN yet — connect it first")
    return url


def fetch_remote_accounts(start_date: Optional[date] = None) -> List[dict]:
    """Raw account list from SimpleFIN, each with its own embedded transactions."""
    params = {}
    if start_date:
        params["start-date"] = int(datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    resp = httpx.get(f"{_access_url()}/accounts", params=params, timeout=60)
    if resp.status_code != 200:
        raise HTTPException(502, f"SimpleFIN request failed: HTTP {resp.status_code}")
    data = resp.json()
    if data.get("errors"):
        raise HTTPException(502, f"SimpleFIN reported errors: {data['errors']}")
    return data.get("accounts", [])


def _cents(amount_str: str) -> int:
    return int((Decimal(amount_str) * 100).to_integral_value())


def _import_transaction(db: Session, account: Account, remote_txn: dict) -> Optional[Transaction]:
    external_id = remote_txn["id"]
    existing = db.scalar(
        select(Transaction).where(Transaction.account_id == account.id, Transaction.external_id == external_id)
    )
    if existing:
        return None  # already imported on a prior sync

    txn_date = datetime.fromtimestamp(remote_txn["posted"], tz=timezone.utc).date()
    amount_cents = _cents(remote_txn["amount"])
    payee_name = remote_txn.get("payee") or remote_txn.get("description") or "Unknown"

    category_id = None
    if amount_cents > 0:
        category_id = get_or_create_rta_category(db).id

    pre_availables = {}
    if category_id and amount_cents < 0:
        pre_availables[category_id] = compute_category_available_cents(db, category_id, month_start(txn_date))

    payee = get_or_create_payee(db, payee_name)
    txn = Transaction(
        account_id=account.id,
        date=txn_date,
        payee_id=payee.id,
        amount_cents=amount_cents,
        budget_amount_cents=amount_cents,
        category_id=category_id,
        is_transfer=False,
        cleared=True,
        source="simplefin",
        external_id=external_id,
    )
    db.add(txn)
    db.flush()

    if account.type == "credit" and category_id:
        apply_credit_card_movements(db, txn, account, [(category_id, amount_cents)], pre_availables)

    return txn


def sync_all(db: Session) -> dict:
    links = db.scalars(select(SimpleFinLink)).all()
    if not links:
        return {"accounts_synced": 0, "transactions_imported": 0}

    oldest_sync = min((link.last_synced_at for link in links if link.last_synced_at), default=None)
    start_date = (
        oldest_sync.date() if oldest_sync else date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    )
    remote_accounts = {a["id"]: a for a in fetch_remote_accounts(start_date=start_date)}

    imported = 0
    synced = 0
    for link in links:
        remote = remote_accounts.get(link.simplefin_account_id)
        if remote is None:
            continue
        account = db.get(Account, link.account_id)
        for remote_txn in remote.get("transactions", []):
            txn = _import_transaction(db, account, remote_txn)
            if txn:
                imported += 1
        link.last_synced_at = datetime.now(timezone.utc)
        synced += 1
        db.commit()

    return {"accounts_synced": synced, "transactions_imported": imported}


def list_linkable_accounts(db: Session) -> List[dict]:
    """Remote SimpleFIN accounts alongside whether (and to what) they're already linked."""
    remote_accounts = fetch_remote_accounts()
    linked_by_remote_id = {link.simplefin_account_id: link for link in db.scalars(select(SimpleFinLink)).all()}

    out = []
    for remote in remote_accounts:
        link = linked_by_remote_id.get(remote["id"])
        out.append(
            {
                "simplefin_account_id": remote["id"],
                "name": remote.get("name", "Unnamed account"),
                "org": (remote.get("org") or {}).get("name"),
                "balance": remote.get("balance"),
                "linked_account_id": link.account_id if link else None,
            }
        )
    return out
