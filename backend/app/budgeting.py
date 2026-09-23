from datetime import date, datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    RTA_CATEGORY_NAME,
    Account,
    Category,
    CategoryGroup,
    CategoryMovement,
    MonthlyAllocation,
    Payee,
    Transaction,
    TransactionSplit,
)
from app.schemas import TransactionCreate, TransactionUpdate

SYSTEM_GROUP_NAME = "Internal"
PAYMENTS_GROUP_NAME = "Credit Card Payments"


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _get_or_create_group(db: Session, name: str) -> CategoryGroup:
    group = db.scalar(select(CategoryGroup).where(CategoryGroup.name == name))
    if group is None:
        group = CategoryGroup(name=name, sort_order=-1)
        db.add(group)
        db.flush()
    return group


def get_or_create_rta_category(db: Session) -> Category:
    cat = db.scalar(select(Category).where(Category.name == RTA_CATEGORY_NAME, Category.is_system.is_(True)))
    if cat is None:
        group = _get_or_create_group(db, SYSTEM_GROUP_NAME)
        cat = Category(name=RTA_CATEGORY_NAME, group_id=group.id, is_system=True, sort_order=-1)
        db.add(cat)
        db.flush()
    return cat


def get_or_create_payment_category(db: Session, account: Account) -> Category:
    if account.payment_category_id:
        return db.get(Category, account.payment_category_id)
    group = _get_or_create_group(db, PAYMENTS_GROUP_NAME)
    cat = Category(name=f"Payment: {account.name}", group_id=group.id, is_system=True, sort_order=0)
    db.add(cat)
    db.flush()
    account.payment_category_id = cat.id
    db.flush()
    return cat


def get_or_create_payee(db: Session, name: str) -> Payee:
    payee = db.scalar(select(Payee).where(Payee.name == name))
    if payee is None:
        payee = Payee(name=name)
        db.add(payee)
        db.flush()
    return payee


def _next_month(as_of_month: date) -> date:
    return date(as_of_month.year + (1 if as_of_month.month == 12 else 0),
                1 if as_of_month.month == 12 else as_of_month.month + 1, 1)


def _activity_cents(db: Session, category_id: int, before: date) -> int:
    """All transaction/split activity in a category, cumulative up to (excluding) `before`."""
    direct = db.scalar(
        select(func.coalesce(func.sum(Transaction.budget_amount_cents), 0)).where(
            Transaction.category_id == category_id,
            Transaction.date < before,
            Transaction.deleted_at.is_(None),
        )
    )
    split = db.scalar(
        select(func.coalesce(func.sum(TransactionSplit.amount_cents), 0))
        .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
        .where(
            TransactionSplit.category_id == category_id,
            Transaction.date < before,
            Transaction.deleted_at.is_(None),
        )
    )
    return direct + split


def compute_category_activity_cents(db: Session, category_id: int, month: date) -> int:
    """Activity within a single month only (for display), not the cumulative running total."""
    direct = db.scalar(
        select(func.coalesce(func.sum(Transaction.budget_amount_cents), 0)).where(
            Transaction.category_id == category_id,
            Transaction.date >= month,
            Transaction.date < _next_month(month),
            Transaction.deleted_at.is_(None),
        )
    )
    split = db.scalar(
        select(func.coalesce(func.sum(TransactionSplit.amount_cents), 0))
        .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
        .where(
            TransactionSplit.category_id == category_id,
            Transaction.date >= month,
            Transaction.date < _next_month(month),
            Transaction.deleted_at.is_(None),
        )
    )
    return direct + split


def compute_category_available_cents(db: Session, category_id: int, as_of_month: date) -> int:
    assigned = db.scalar(
        select(func.coalesce(func.sum(MonthlyAllocation.assigned_cents), 0)).where(
            MonthlyAllocation.category_id == category_id,
            MonthlyAllocation.month <= as_of_month,
        )
    )
    activity = _activity_cents(db, category_id, _next_month(as_of_month))
    movements_in = db.scalar(
        select(func.coalesce(func.sum(CategoryMovement.amount_cents), 0)).where(
            CategoryMovement.to_category_id == category_id,
            CategoryMovement.month <= as_of_month,
        )
    )
    movements_out = db.scalar(
        select(func.coalesce(func.sum(CategoryMovement.amount_cents), 0)).where(
            CategoryMovement.from_category_id == category_id,
            CategoryMovement.month <= as_of_month,
        )
    )
    return assigned + activity + movements_in - movements_out


def compute_ready_to_assign_cents(db: Session, as_of_month: date) -> int:
    """RTA isn't its own ledger — it's whatever hasn't been assigned yet: all income
    that landed in the Ready to Assign category, minus everything ever assigned to a
    real category. Assigning money is 'moving' it out of RTA, so it's never tracked
    as a movement of its own.
    """
    rta = get_or_create_rta_category(db)
    rta_income = _activity_cents(db, rta.id, _next_month(as_of_month))
    total_assigned = db.scalar(
        select(func.coalesce(func.sum(MonthlyAllocation.assigned_cents), 0))
        .join(Category, Category.id == MonthlyAllocation.category_id)
        .where(Category.is_system.is_(False), MonthlyAllocation.month <= as_of_month)
    )
    return rta_income - total_assigned


def compute_goal_status(category: Category, assigned_cents: int, available_cents: int, month: date) -> Optional[dict]:
    """Goal progress for one category in one month. Returns None if the category has
    no goal. `target_cents` is 'how much should be assigned/available by now';
    `needed_this_month_cents` is what's still left to assign this month to stay on track.
    """
    if not category.goal_type or not category.goal_amount_cents:
        return None

    goal_amount = category.goal_amount_cents

    if category.goal_type == "monthly_funding":
        target = goal_amount
        met = assigned_cents >= target
        needed = max(0, target - assigned_cents)
    elif category.goal_type == "target_balance":
        target = goal_amount
        met = available_cents >= target
        needed = max(0, target - available_cents)
    elif category.goal_type == "target_balance_by_date":
        target = goal_amount
        met = available_cents >= target
        if category.goal_date and category.goal_date > month:
            months_remaining = (
                (category.goal_date.year - month.year) * 12 + (category.goal_date.month - month.month) + 1
            )
        else:
            months_remaining = 1
        needed = max(0, target - available_cents) // months_remaining if not met else 0
    else:
        return None

    progress_pct = min(100.0, round((available_cents / target) * 100, 1)) if target > 0 else 0.0

    return {
        "goal_type": category.goal_type,
        "goal_amount_cents": goal_amount,
        "goal_date": category.goal_date,
        "goal_target_cents": target,
        "goal_progress_pct": progress_pct,
        "goal_met": met,
        "goal_needed_this_month_cents": needed,
    }


def set_goal(
    db: Session,
    category_id: int,
    goal_type: Optional[str],
    goal_amount_cents: Optional[int],
    goal_date: Optional[date],
) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "Category not found")
    if category.is_system:
        raise HTTPException(400, "Can't set a goal on a system category")
    category.goal_type = goal_type
    category.goal_amount_cents = goal_amount_cents
    category.goal_date = goal_date
    db.commit()
    db.refresh(category)
    return category


def _lines_for(category_id: Optional[int], amount_cents: int, splits: Optional[List[Tuple[int, int]]]):
    if splits:
        return list(splits)
    if category_id is not None:
        return [(category_id, amount_cents)]
    return []


def apply_credit_card_movements(
    db: Session, txn: Transaction, account: Account, lines: List[Tuple[int, int]], pre_availables: dict
):
    """Redirects available dollars from spending categories into the card's Payment
    category so a charge isn't simultaneously 'available to spend' and undocumented debt.
    Only covers the portion that was actually available before this purchase; the
    overspent portion (if any) is left for the user to cover manually, same as a cash
    overspend. Refunds/credits on a credit account are not auto-reversed (known gap).
    """
    payment_category = get_or_create_payment_category(db, account)
    month = month_start(txn.date)
    for category_id, amount_cents in lines:
        if category_id is None or category_id == payment_category.id or amount_cents >= 0:
            continue
        spend = -amount_cents
        pre_available = pre_availables.get(category_id, 0)
        movement = min(pre_available, spend)
        if movement <= 0:
            continue
        db.add(
            CategoryMovement(
                transaction_id=txn.id,
                from_category_id=category_id,
                to_category_id=payment_category.id,
                month=month,
                amount_cents=movement,
            )
        )
    db.flush()


def _clear_movements(db: Session, transaction_id: int):
    db.query(CategoryMovement).filter(CategoryMovement.transaction_id == transaction_id).delete()


def create_transaction(db: Session, payload: TransactionCreate) -> Transaction:
    account = db.get(Account, payload.account_id)
    if account is None:
        raise HTTPException(404, "Account not found")

    if payload.transfer_account_id is not None:
        return _create_transfer(db, payload, account)

    payee = get_or_create_payee(db, payload.payee_name) if payload.payee_name else None

    split_tuples = [(s.category_id, s.amount_cents) for s in payload.splits] if payload.splits else None
    if split_tuples:
        amount_cents = sum(a for _, a in split_tuples)
    else:
        if payload.amount_cents is None:
            raise HTTPException(422, "amount_cents is required when not splitting")
        amount_cents = payload.amount_cents

    category_id = payload.category_id
    if not split_tuples and category_id is None and amount_cents > 0:
        category_id = get_or_create_rta_category(db).id

    lines = _lines_for(category_id if not split_tuples else None, amount_cents, split_tuples)
    month = month_start(payload.date)
    pre_availables = {
        cid: compute_category_available_cents(db, cid, month) for cid, amt in lines if cid and amt < 0
    }

    txn = Transaction(
        account_id=account.id,
        date=payload.date,
        payee_id=payee.id if payee else None,
        amount_cents=amount_cents,
        budget_amount_cents=amount_cents,
        category_id=None if split_tuples else category_id,
        is_transfer=False,
        cleared=True,
        source="manual",
    )
    db.add(txn)
    db.flush()

    if split_tuples:
        for cid, amt in split_tuples:
            db.add(TransactionSplit(transaction_id=txn.id, category_id=cid, amount_cents=amt))
        db.flush()

    if account.type == "credit":
        apply_credit_card_movements(db, txn, account, lines, pre_availables)

    db.commit()
    db.refresh(txn)
    return txn


def _create_transfer(db: Session, payload: TransactionCreate, from_account: Account) -> Transaction:
    to_account = db.get(Account, payload.transfer_account_id)
    if to_account is None:
        raise HTTPException(404, "Transfer target account not found")
    if payload.amount_cents is None:
        raise HTTPException(422, "amount_cents is required for a transfer")

    # Paying down a credit account is categorized to that card's Payment category —
    # it draws the reserve built up by apply_credit_card_movements back down, so its
    # budget-facing sign is the opposite of its account-ledger sign (see Transaction
    # .budget_amount_cents). Transfers out of a credit account (cash advances) and
    # transfers between two cash-basis accounts stay categoryless — a known gap.
    to_category_id = get_or_create_payment_category(db, to_account).id if to_account.type == "credit" else None

    leg_from = Transaction(
        account_id=from_account.id,
        date=payload.date,
        amount_cents=-abs(payload.amount_cents),
        budget_amount_cents=-abs(payload.amount_cents),
        category_id=None,
        is_transfer=True,
        cleared=True,
        source="manual",
    )
    leg_to = Transaction(
        account_id=to_account.id,
        date=payload.date,
        amount_cents=abs(payload.amount_cents),
        budget_amount_cents=-abs(payload.amount_cents) if to_category_id else abs(payload.amount_cents),
        category_id=to_category_id,
        is_transfer=True,
        cleared=True,
        source="manual",
    )
    db.add_all([leg_from, leg_to])
    db.flush()
    leg_from.transfer_transaction_id = leg_to.id
    leg_to.transfer_transaction_id = leg_from.id
    db.commit()
    db.refresh(leg_from)
    return leg_from


def update_transaction(db: Session, transaction_id: int, payload: TransactionUpdate) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(404, "Transaction not found")
    if txn.is_transfer:
        raise HTTPException(400, "Editing transfers isn't supported yet — delete and recreate it")

    account = db.get(Account, txn.account_id)
    _clear_movements(db, txn.id)
    db.query(TransactionSplit).filter(TransactionSplit.transaction_id == txn.id).delete()

    if payload.date is not None:
        txn.date = payload.date
    if payload.payee_name is not None:
        txn.payee_id = get_or_create_payee(db, payload.payee_name).id
    if payload.cleared is not None:
        txn.cleared = payload.cleared

    split_tuples = [(s.category_id, s.amount_cents) for s in payload.splits] if payload.splits else None
    if split_tuples:
        txn.amount_cents = sum(a for _, a in split_tuples)
        txn.budget_amount_cents = txn.amount_cents
        txn.category_id = None
    else:
        if payload.amount_cents is not None:
            txn.amount_cents = payload.amount_cents
            txn.budget_amount_cents = payload.amount_cents
        if payload.category_id is not None:
            txn.category_id = payload.category_id

    db.flush()

    lines = _lines_for(txn.category_id, txn.amount_cents, split_tuples)
    month = month_start(txn.date)
    pre_availables = {
        cid: compute_category_available_cents(db, cid, month) for cid, amt in lines if cid and amt < 0
    }

    if split_tuples:
        for cid, amt in split_tuples:
            db.add(TransactionSplit(transaction_id=txn.id, category_id=cid, amount_cents=amt))
        db.flush()

    if account.type == "credit":
        apply_credit_card_movements(db, txn, account, lines, pre_availables)

    db.commit()
    db.refresh(txn)
    return txn


def delete_transaction(db: Session, transaction_id: int) -> List[int]:
    """Soft-deletes (excluded from all balance/activity queries, row kept for undo).
    Returns the ids of every transaction affected (the transfer pair, if any) so the
    caller can offer to undo all of them together.
    """
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(404, "Transaction not found")
    now = datetime.utcnow()
    _clear_movements(db, txn.id)
    txn.deleted_at = now
    affected = [txn.id]
    if txn.transfer_transaction_id:
        pair = db.get(Transaction, txn.transfer_transaction_id)
        if pair is not None:
            _clear_movements(db, pair.id)
            pair.deleted_at = now
            affected.append(pair.id)
    db.commit()
    return affected


def undo_delete_transaction(db: Session, transaction_id: int) -> List[Transaction]:
    txn = db.get(Transaction, transaction_id)
    if txn is None or txn.deleted_at is None:
        raise HTTPException(404, "No deleted transaction with that id")

    ids = [txn.id] + ([txn.transfer_transaction_id] if txn.transfer_transaction_id else [])
    restored = []
    for tid in ids:
        t = db.get(Transaction, tid)
        if t is None:
            continue
        t.deleted_at = None
        db.flush()
        restored.append(t)

        if not t.is_transfer:
            account = db.get(Account, t.account_id)
            if account.type == "credit":
                splits = db.scalars(select(TransactionSplit).where(TransactionSplit.transaction_id == t.id)).all()
                split_tuples = [(s.category_id, s.amount_cents) for s in splits] if splits else None
                lines = _lines_for(t.category_id, t.amount_cents, split_tuples)
                month = month_start(t.date)
                # Recompute "available before this purchase" the same way create_transaction
                # would — this transaction's own effect is already excluded since it's still
                # marked deleted_at at the moment of this calc... but we just cleared it above,
                # so exclude it explicitly by subtracting its own contribution isn't needed:
                # simplest correct approach is to temporarily re-flag it, compute, then restore.
                t.deleted_at = datetime.utcnow()
                db.flush()
                pre_availables = {
                    cid: compute_category_available_cents(db, cid, month) for cid, amt in lines if cid and amt < 0
                }
                t.deleted_at = None
                db.flush()
                apply_credit_card_movements(db, t, account, lines, pre_availables)

    db.commit()
    for t in restored:
        db.refresh(t)
    return restored


def assign_money(db: Session, category_id: int, month: date, assigned_cents: int) -> MonthlyAllocation:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "Category not found")
    if category.is_system:
        raise HTTPException(400, "Can't assign directly to a system category")
    month = month_start(month)
    row = db.scalar(
        select(MonthlyAllocation).where(
            MonthlyAllocation.category_id == category_id, MonthlyAllocation.month == month
        )
    )
    if row is None:
        row = MonthlyAllocation(category_id=category_id, month=month, assigned_cents=assigned_cents)
        db.add(row)
    else:
        row.assigned_cents = assigned_cents
    db.commit()
    db.refresh(row)
    return row


def account_balance_cents(db: Session, account_id: int, as_of: Optional[date] = None) -> int:
    conditions = [Transaction.account_id == account_id, Transaction.deleted_at.is_(None)]
    if as_of is not None:
        conditions.append(Transaction.date <= as_of)
    return db.scalar(select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(*conditions))


def reconcile_account(db: Session, account_id: int, as_of: date, statement_balance_cents: int) -> dict:
    """Compares the account's computed balance (as of a date) against the real bank
    statement balance. If they differ, records the gap as an uncategorized adjustment
    transaction (so the account balance and reality line back up — what caused the gap
    is on the user to figure out, same as YNAB) and marks everything through that date
    reconciled so this reconciliation doesn't have to be redone.
    """
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(404, "Account not found")

    computed = account_balance_cents(db, account_id, as_of=as_of)
    diff = statement_balance_cents - computed

    adjustment = None
    if diff != 0:
        adjustment = Transaction(
            account_id=account_id,
            date=as_of,
            amount_cents=diff,
            budget_amount_cents=diff,
            category_id=None,
            is_transfer=False,
            cleared=True,
            reconciled=True,
            source="reconcile",
        )
        db.add(adjustment)
        db.flush()

    db.query(Transaction).filter(
        Transaction.account_id == account_id,
        Transaction.date <= as_of,
        Transaction.deleted_at.is_(None),
    ).update({"reconciled": True})
    db.commit()

    return {
        "computed_balance_cents": computed,
        "statement_balance_cents": statement_balance_cents,
        "adjustment_cents": diff,
        "adjustment_transaction_id": adjustment.id if adjustment else None,
    }
