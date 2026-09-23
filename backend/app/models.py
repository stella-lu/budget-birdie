import datetime as dt
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

RTA_CATEGORY_NAME = "Ready to Assign"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    type: Mapped[str] = mapped_column(String)  # checking | credit | cash
    closed: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class CategoryGroup(Base):
    __tablename__ = "category_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    categories: Mapped[list["Category"]] = relationship(back_populates="group")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("category_groups.id"), nullable=True)
    name: Mapped[str] = mapped_column(String)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped[Optional["CategoryGroup"]] = relationship(back_populates="categories")


class Payee(Base):
    __tablename__ = "payees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    date: Mapped[dt.date] = mapped_column(Date)
    payee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payees.id"), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    # Usually equal to amount_cents. Differs only for the "pay down the card" leg of a
    # credit-account transfer: amount_cents is +N there (debt going down), but the
    # Payment category's available balance should go DOWN by N (reserve being spent),
    # so that leg's budget-facing sign is the opposite of its account-ledger sign.
    budget_amount_cents: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False)
    transfer_transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id"), nullable=True
    )
    cleared: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String, default="manual")
    # SimpleFIN's transaction id, for dedup on repeated syncs. Null for manual entries.
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    splits: Mapped[list["TransactionSplit"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("account_id", "external_id", name="uq_account_external_id"),)


class TransactionSplit(Base):
    __tablename__ = "transaction_splits"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    amount_cents: Mapped[int] = mapped_column(Integer)

    transaction: Mapped["Transaction"] = relationship(back_populates="splits")


class MonthlyAllocation(Base):
    __tablename__ = "monthly_allocations"
    __table_args__ = (UniqueConstraint("category_id", "month", name="uq_category_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    month: Mapped[dt.date] = mapped_column(Date)  # normalized to the 1st of the month
    assigned_cents: Mapped[int] = mapped_column(Integer, default=0)


class CategoryMovement(Base):
    """Auto-generated when a credit-card purchase redirects available dollars
    from the spending category into that card's Payment category, so the
    same dollars aren't counted as both 'available to spend' and 'debt cover'.
    """

    __tablename__ = "category_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True
    )
    from_category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    to_category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    month: Mapped[dt.date] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class SimpleFinLink(Base):
    """Links a local account to a SimpleFIN Bridge account id, so sync knows which
    remote account feeds which local one and where it left off.
    """

    __tablename__ = "simplefin_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), unique=True)
    simplefin_account_id: Mapped[str] = mapped_column(String)
    simplefin_org_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
