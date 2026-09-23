import { useEffect, useState } from "react";
import { api } from "../api";
import { formatCents } from "../money";
import type { IncomeVsExpense, SpendingByCategory } from "../types";

export function ReportsPage() {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [spending, setSpending] = useState<SpendingByCategory[]>([]);
  const [incomeExpense, setIncomeExpense] = useState<IncomeVsExpense[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api.spendingByCategory(start || undefined, end || undefined).then(setSpending).catch((e) => setError(String(e)));
    api.incomeVsExpense(start || undefined, end || undefined).then(setIncomeExpense).catch((e) => setError(String(e)));
  };

  useEffect(load, []);

  const maxSpending = Math.max(1, ...spending.map((s) => s.total_cents));
  const maxFlow = Math.max(1, ...incomeExpense.flatMap((r) => [r.income_cents, r.expense_cents]));

  return (
    <div>
      <h2>Reports</h2>
      {error && <p className="error">{error}</p>}

      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
      >
        <label>
          From <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          To <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <button type="submit">Apply</button>
      </form>

      <div className="category-group">
        <h3>Spending by category</h3>
        {spending.length === 0 && <p className="empty">No spending in this range</p>}
        {spending.map((s) => (
          <div key={s.category_id} className="report-row">
            <span className="report-label">{s.category_name}</span>
            <div className="report-bar">
              <div className="report-bar-fill negative-fill" style={{ width: `${(s.total_cents / maxSpending) * 100}%` }} />
            </div>
            <span className="report-value">{formatCents(s.total_cents)}</span>
          </div>
        ))}
      </div>

      <div className="category-group">
        <h3>Income vs. expense</h3>
        {incomeExpense.length === 0 && <p className="empty">No transactions in this range</p>}
        {incomeExpense.map((r) => (
          <div key={r.month} className="income-expense-row">
            <span className="report-label">{r.month}</span>
            <div className="report-row">
              <div className="report-bar">
                <div className="report-bar-fill positive-fill" style={{ width: `${(r.income_cents / maxFlow) * 100}%` }} />
              </div>
              <span className="report-value positive">{formatCents(r.income_cents)}</span>
            </div>
            <div className="report-row">
              <div className="report-bar">
                <div className="report-bar-fill negative-fill" style={{ width: `${(r.expense_cents / maxFlow) * 100}%` }} />
              </div>
              <span className="report-value negative">{formatCents(r.expense_cents)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
