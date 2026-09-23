from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

AccountType = Literal["checking", "credit", "cash"]


class AccountCreate(BaseModel):
    name: str
    type: AccountType


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    closed: bool
    payment_category_id: Optional[int] = None
    balance_cents: int = 0


class CategoryGroupCreate(BaseModel):
    name: str
    sort_order: int = 0


class CategoryGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_order: int


class CategoryCreate(BaseModel):
    name: str
    group_id: int
    sort_order: int = 0


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    group_id: Optional[int] = None
    is_system: bool
    sort_order: int


class CategoryBudgetOut(CategoryOut):
    assigned_cents: int = 0
    activity_cents: int = 0
    available_cents: int = 0


class CategoryGroupBudgetOut(BaseModel):
    id: int
    name: str
    sort_order: int
    categories: List[CategoryBudgetOut]


class BudgetMonthOut(BaseModel):
    month: date
    ready_to_assign_cents: int
    groups: List[CategoryGroupBudgetOut]


class AssignRequest(BaseModel):
    category_id: int
    month: date
    assigned_cents: int


class SplitIn(BaseModel):
    category_id: int
    amount_cents: int


class TransactionCreate(BaseModel):
    account_id: int
    date: date
    payee_name: Optional[str] = None
    amount_cents: Optional[int] = None
    category_id: Optional[int] = None
    splits: Optional[List[SplitIn]] = None
    transfer_account_id: Optional[int] = None


class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    payee_name: Optional[str] = None
    amount_cents: Optional[int] = None
    category_id: Optional[int] = None
    splits: Optional[List[SplitIn]] = None
    cleared: Optional[bool] = None


class SplitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    amount_cents: int


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    date: date
    payee_id: Optional[int] = None
    payee_name: Optional[str] = None
    amount_cents: int
    category_id: Optional[int] = None
    is_transfer: bool
    transfer_transaction_id: Optional[int] = None
    cleared: bool
    source: str
    splits: List[SplitOut] = []


class PayeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
