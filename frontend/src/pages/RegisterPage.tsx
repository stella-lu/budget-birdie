import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { dollarsToCents, formatCents } from "../money";
import type { Account, Category, Transaction } from "../types";

interface SplitRow {
  category_id: number | "";
  amount: string;
}

export function RegisterPage({ accountId, accounts }: { accountId: number; accounts: Account[] }) {
  const account = accounts.find((a) => a.id === accountId);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [undoTarget, setUndoTarget] = useState<number | null>(null);
  const [reconciling, setReconciling] = useState(false);
  const [reconcileDate, setReconcileDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [reconcileBalance, setReconcileBalance] = useState("");
  const [reconcileResult, setReconcileResult] = useState<string | null>(null);
  const payeeInputRef = useRef<HTMLInputElement>(null);

  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [payee, setPayee] = useState("");
  const [direction, setDirection] = useState<"outflow" | "inflow">("outflow");
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [isTransfer, setIsTransfer] = useState(false);
  const [transferTo, setTransferTo] = useState<number | "">("");
  const [isSplit, setIsSplit] = useState(false);
  const [splits, setSplits] = useState<SplitRow[]>([
    { category_id: "", amount: "" },
    { category_id: "", amount: "" },
  ]);

  const load = () => {
    api.listTransactions(accountId).then(setTransactions).catch((e) => setError(String(e)));
    api.listCategories().then(setCategories).catch((e) => setError(String(e)));
  };

  useEffect(load, [accountId]);

  // "n" jumps to the payee field to start a new transaction, unless already typing somewhere.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if (!typing && e.key === "n") {
        e.preventDefault();
        payeeInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const resetForm = () => {
    setPayee("");
    setAmount("");
    setCategoryId("");
    setIsTransfer(false);
    setTransferTo("");
    setIsSplit(false);
    setSplits([
      { category_id: "", amount: "" },
      { category_id: "", amount: "" },
    ]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isTransfer) {
        if (!transferTo || !amount) return;
        await api.createTransaction({
          account_id: accountId,
          date,
          amount_cents: dollarsToCents(amount),
          transfer_account_id: Number(transferTo),
        });
      } else if (isSplit) {
        const rows = splits.filter((s) => s.category_id !== "" && s.amount !== "");
        if (rows.length < 2) {
          setError("A split needs at least two categorized rows");
          return;
        }
        await api.createTransaction({
          account_id: accountId,
          date,
          payee_name: payee || undefined,
          splits: rows.map((s) => ({
            category_id: Number(s.category_id),
            amount_cents: -dollarsToCents(s.amount),
          })),
        });
      } else {
        if (!amount) return;
        const cents = dollarsToCents(amount);
        await api.createTransaction({
          account_id: accountId,
          date,
          payee_name: payee || undefined,
          amount_cents: direction === "outflow" ? -cents : cents,
          category_id: categoryId === "" ? null : Number(categoryId),
        });
      }
      resetForm();
      load();
    } catch (err) {
      setError(String(err));
    }
  };

  const handleDelete = async (id: number) => {
    await api.deleteTransaction(id);
    setUndoTarget(id);
    load();
  };

  const handleUndo = async () => {
    if (undoTarget === null) return;
    await api.undoDeleteTransaction(undoTarget);
    setUndoTarget(null);
    load();
  };

  const handleReconcile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reconcileBalance) return;
    try {
      const result = await api.reconcileAccount(accountId, reconcileDate, dollarsToCents(reconcileBalance));
      setReconcileResult(
        result.adjustment_cents === 0
          ? "Already matched — no adjustment needed."
          : `Added a ${formatCents(result.adjustment_cents)} adjustment to match your statement.`
      );
      setReconciling(false);
      setReconcileBalance("");
      load();
    } catch (err) {
      setError(String(err));
    }
  };

  const categoryName = (id: number | null) => categories.find((c) => c.id === id)?.name ?? (id ? `#${id}` : "—");

  return (
    <div>
      <h2>{account?.name ?? "Account"}</h2>
      {error && <p className="error">{error}</p>}

      {undoTarget !== null && (
        <div className="undo-banner">
          <span>Transaction deleted.</span>
          <button type="button" onClick={handleUndo}>
            Undo
          </button>
        </div>
      )}

      <div className="inline-form">
        <button type="button" onClick={() => setReconciling(!reconciling)}>
          {reconciling ? "Cancel reconcile" : "Reconcile"}
        </button>
        {reconcileResult && <span>{reconcileResult}</span>}
      </div>

      {reconciling && (
        <form onSubmit={handleReconcile} className="register-form">
          <label>
            As of <input type="date" value={reconcileDate} onChange={(e) => setReconcileDate(e.target.value)} />
          </label>
          <label>
            Statement balance{" "}
            <input placeholder="0.00" value={reconcileBalance} onChange={(e) => setReconcileBalance(e.target.value)} />
          </label>
          <button type="submit">Reconcile</button>
        </form>
      )}

      <form onSubmit={handleSubmit} className="register-form">
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        {!isTransfer && (
          <input placeholder="Payee (press 'n' to jump here)" value={payee} onChange={(e) => setPayee(e.target.value)} ref={payeeInputRef} />
        )}

        <label>
          <input type="checkbox" checked={isTransfer} onChange={(e) => setIsTransfer(e.target.checked)} />
          Transfer
        </label>

        {isTransfer ? (
          <>
            <select value={transferTo} onChange={(e) => setTransferTo(Number(e.target.value))}>
              <option value="">To account…</option>
              {accounts.filter((a) => a.id !== accountId).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            <input placeholder="0.00" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </>
        ) : (
          <>
            <label>
              <input
                type="checkbox"
                checked={isSplit}
                onChange={(e) => setIsSplit(e.target.checked)}
              />
              Split
            </label>
            {isSplit ? (
              <div className="splits">
                {splits.map((s, i) => (
                  <div key={i} className="split-row">
                    <select
                      value={s.category_id}
                      onChange={(e) => {
                        const next = [...splits];
                        next[i] = { ...s, category_id: Number(e.target.value) };
                        setSplits(next);
                      }}
                    >
                      <option value="">Category…</option>
                      {categories.filter((c) => !c.is_system).map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                    <input
                      placeholder="0.00"
                      value={s.amount}
                      onChange={(e) => {
                        const next = [...splits];
                        next[i] = { ...s, amount: e.target.value };
                        setSplits(next);
                      }}
                    />
                  </div>
                ))}
                <button type="button" onClick={() => setSplits([...splits, { category_id: "", amount: "" }])}>
                  + Add split
                </button>
              </div>
            ) : (
              <>
                <select value={direction} onChange={(e) => setDirection(e.target.value as "outflow" | "inflow")}>
                  <option value="outflow">Outflow</option>
                  <option value="inflow">Inflow</option>
                </select>
                <input placeholder="0.00" value={amount} onChange={(e) => setAmount(e.target.value)} />
                <select value={categoryId} onChange={(e) => setCategoryId(Number(e.target.value))}>
                  <option value="">Category (defaults to Ready to Assign for income)…</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </>
            )}
          </>
        )}

        <button type="submit">Add transaction</button>
      </form>

      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Payee</th>
            <th>Category</th>
            <th>Amount</th>
            <th>R</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((t) => (
            <tr key={t.id}>
              <td>{t.date}</td>
              <td>{t.is_transfer ? "Transfer" : t.payee_name ?? "—"}</td>
              <td>{t.splits.length > 0 ? "Split" : categoryName(t.category_id)}</td>
              <td className={t.amount_cents < 0 ? "negative" : "positive"}>{formatCents(t.amount_cents)}</td>
              <td className="positive" title={t.reconciled ? "Reconciled" : ""}>
                {t.reconciled ? "✓" : ""}
              </td>
              <td>
                <button onClick={() => handleDelete(t.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
