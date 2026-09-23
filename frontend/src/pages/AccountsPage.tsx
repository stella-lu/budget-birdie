import { useEffect, useState } from "react";
import { api } from "../api";
import { formatCents } from "../money";
import type { Account, AccountType } from "../types";

export function AccountsPage({ onSelect }: { onSelect: (accountId: number) => void }) {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [name, setName] = useState("");
  const [type, setType] = useState<AccountType>("checking");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api.listAccounts().then(setAccounts).catch((e) => setError(String(e)));
  };

  useEffect(load, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api.createAccount(name.trim(), type);
      setName("");
      load();
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <div>
      <h2>Accounts</h2>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Balance</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((a) => (
            <tr key={a.id} className="clickable" onClick={() => onSelect(a.id)}>
              <td>{a.name}</td>
              <td>{a.type}</td>
              <td className={a.balance_cents < 0 ? "negative" : "positive"}>{formatCents(a.balance_cents)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <form onSubmit={handleCreate} className="inline-form">
        <input placeholder="Account name" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={type} onChange={(e) => setType(e.target.value as AccountType)}>
          <option value="checking">Checking</option>
          <option value="credit">Credit</option>
          <option value="cash">Cash</option>
        </select>
        <button type="submit">Add account</button>
      </form>
    </div>
  );
}
