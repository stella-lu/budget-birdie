export type AccountType = "checking" | "credit" | "cash";

export interface Account {
  id: number;
  name: string;
  type: AccountType;
  closed: boolean;
  payment_category_id: number | null;
  balance_cents: number;
}

export interface CategoryGroup {
  id: number;
  name: string;
  sort_order: number;
}

export interface Category {
  id: number;
  name: string;
  group_id: number | null;
  is_system: boolean;
  sort_order: number;
}

export interface CategoryBudget extends Category {
  assigned_cents: number;
  activity_cents: number;
  available_cents: number;
}

export interface CategoryGroupBudget {
  id: number;
  name: string;
  sort_order: number;
  categories: CategoryBudget[];
}

export interface BudgetMonth {
  month: string;
  ready_to_assign_cents: number;
  groups: CategoryGroupBudget[];
}

export interface Split {
  id?: number;
  category_id: number;
  amount_cents: number;
}

export interface Transaction {
  id: number;
  account_id: number;
  date: string;
  payee_id: number | null;
  payee_name: string | null;
  amount_cents: number;
  category_id: number | null;
  is_transfer: boolean;
  transfer_transaction_id: number | null;
  cleared: boolean;
  source: string;
  splits: Split[];
}

export interface Payee {
  id: number;
  name: string;
}

export interface SimpleFinStatus {
  connected: boolean;
}

export interface LinkableAccount {
  simplefin_account_id: string;
  name: string;
  org: string | null;
  balance: string | null;
  linked_account_id: number | null;
}

export interface SyncResult {
  accounts_synced: number;
  transactions_imported: number;
}
