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
    goal_type: Optional[str] = None
    goal_amount_cents: Optional[int] = None
    goal_date: Optional[date] = None
    note: Optional[str] = None


GoalType = Literal["target_balance", "target_balance_by_date", "monthly_funding"]


class GoalRequest(BaseModel):
    goal_type: Optional[GoalType] = None
    goal_amount_cents: Optional[int] = None
    goal_date: Optional[date] = None


class NoteRequest(BaseModel):
    note: Optional[str] = None


class CategoryBudgetOut(CategoryOut):
    assigned_cents: int = 0
    activity_cents: int = 0
    available_cents: int = 0
    goal_target_cents: Optional[int] = None
    goal_progress_pct: Optional[float] = None
    goal_met: Optional[bool] = None
    goal_needed_this_month_cents: Optional[int] = None


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
    reconciled: bool = False
    source: str
    splits: List[SplitOut] = []


class PayeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class SimpleFinConnectRequest(BaseModel):
    setup_token: str


class SimpleFinStatusOut(BaseModel):
    connected: bool


class LinkableAccountOut(BaseModel):
    simplefin_account_id: str
    name: str
    org: Optional[str] = None
    balance: Optional[str] = None
    linked_account_id: Optional[int] = None


class LinkAccountRequest(BaseModel):
    simplefin_account_id: str
    simplefin_org_name: Optional[str] = None
    account_id: int


class SyncResultOut(BaseModel):
    accounts_synced: int
    transactions_imported: int


class SpendingByCategoryOut(BaseModel):
    category_id: int
    category_name: str
    total_cents: int


class IncomeVsExpenseOut(BaseModel):
    month: str
    income_cents: int
    expense_cents: int


class ReconcileRequest(BaseModel):
    as_of: date
    statement_balance_cents: int


class ReconcileResultOut(BaseModel):
    computed_balance_cents: int
    statement_balance_cents: int
    adjustment_cents: int
    adjustment_transaction_id: Optional[int] = None
