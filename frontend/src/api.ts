import type {
  Account,
  AccountType,
  BudgetMonth,
  Category,
  CategoryGroup,
  Payee,
  Split,
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
  deleteTransaction: (id: number) => request<void>(`/transactions/${id}`, { method: "DELETE" }),
};
