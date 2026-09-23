import type {
  Account,
  AccountType,
  BudgetMonth,
  Category,
  CategoryGroup,
  GoalType,
  IncomeVsExpense,
  LinkableAccount,
  Payee,
  SimpleFinStatus,
  SpendingByCategory,
  Split,
  SyncResult,
  Transaction,
} from "./types";

const BASE = "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${options?.method ?? "GET"} ${path} failed: ${res.status} ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listAccounts: () => request<Account[]>("/accounts"),
  createAccount: (name: string, type: AccountType) =>
    request<Account>("/accounts", { method: "POST", body: JSON.stringify({ name, type }) }),

  listCategoryGroups: () => request<CategoryGroup[]>("/category-groups"),
  createCategoryGroup: (name: string, sort_order = 0) =>
    request<CategoryGroup>("/category-groups", { method: "POST", body: JSON.stringify({ name, sort_order }) }),

  listCategories: () => request<Category[]>("/categories"),
  createCategory: (name: string, group_id: number, sort_order = 0) =>
    request<Category>("/categories", { method: "POST", body: JSON.stringify({ name, group_id, sort_order }) }),

  listPayees: () => request<Payee[]>("/payees"),

  getBudgetMonth: (month: string) => request<BudgetMonth>(`/budget/${month}`),
  assignMoney: (category_id: number, month: string, assigned_cents: number) =>
    request(`/budget/assign`, {
      method: "POST",
      body: JSON.stringify({ category_id, month, assigned_cents }),
    }),

  listTransactions: (account_id?: number) =>
    request<Transaction[]>(`/transactions${account_id ? `?account_id=${account_id}` : ""}`),
  createTransaction: (payload: {
    account_id: number;
    date: string;
    payee_name?: string;
    amount_cents?: number;
    category_id?: number | null;
    splits?: Split[];
    transfer_account_id?: number;
  }) => request<Transaction>("/transactions", { method: "POST", body: JSON.stringify(payload) }),
  deleteTransaction: (id: number) => request<{ deleted_ids: number[] }>(`/transactions/${id}`, { method: "DELETE" }),
  undoDeleteTransaction: (id: number) => request<Transaction>(`/transactions/${id}/undo-delete`, { method: "POST" }),

  syncStatus: () => request<SimpleFinStatus>("/sync/status"),
  syncConnect: (setup_token: string) =>
    request<SimpleFinStatus>("/sync/connect", { method: "POST", body: JSON.stringify({ setup_token }) }),
  syncLinkableAccounts: () => request<LinkableAccount[]>("/sync/simplefin-accounts"),
  syncLinkAccount: (simplefin_account_id: string, account_id: number, simplefin_org_name?: string | null) =>
    request("/sync/link", {
      method: "POST",
      body: JSON.stringify({ simplefin_account_id, account_id, simplefin_org_name }),
    }),
  syncRun: () => request<SyncResult>("/sync/run", { method: "POST" }),

  setGoal: (categoryId: number, goal_type: GoalType | null, goal_amount_cents: number | null, goal_date: string | null) =>
    request<Category>(`/categories/${categoryId}/goal`, {
      method: "PUT",
      body: JSON.stringify({ goal_type, goal_amount_cents, goal_date }),
    }),
  setNote: (categoryId: number, note: string | null) =>
    request<Category>(`/categories/${categoryId}/note`, { method: "PUT", body: JSON.stringify({ note }) }),

  reconcileAccount: (accountId: number, as_of: string, statement_balance_cents: number) =>
    request<{
      computed_balance_cents: number;
      statement_balance_cents: number;
      adjustment_cents: number;
      adjustment_transaction_id: number | null;
    }>(`/accounts/${accountId}/reconcile`, {
      method: "POST",
      body: JSON.stringify({ as_of, statement_balance_cents }),
    }),

  spendingByCategory: (start?: string, end?: string) =>
    request<SpendingByCategory[]>(`/reports/spending-by-category${qs({ start, end })}`),
  incomeVsExpense: (start?: string, end?: string) =>
    request<IncomeVsExpense[]>(`/reports/income-vs-expense${qs({ start, end })}`),
};

function qs(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v);
  if (entries.length === 0) return "";
  return "?" + new URLSearchParams(entries as [string, string][]).toString();
}
