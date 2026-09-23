import { useEffect, useState } from "react";
import { api } from "../api";
import { GoalEditor } from "./GoalEditor";
import { NoteEditor } from "./NoteEditor";
import { dollarsToCents, formatCents } from "../money";
import type { BudgetMonth } from "../types";

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

function monthLabel(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

export function BudgetPage({ month, setMonth }: { month: string; setMonth: (m: string) => void }) {
  const [budget, setBudget] = useState<BudgetMonth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newGroupName, setNewGroupName] = useState("");
  const [newCategoryName, setNewCategoryName] = useState<Record<number, string>>({});

  const load = () => {
    api
      .getBudgetMonth(month)
      .then(setBudget)
      .catch((e) => setError(String(e)));
  };

  useEffect(load, [month]);

  // [ / ] step between months, unless the user is typing somewhere.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if (typing) return;
      if (e.key === "[") setMonth(shiftMonth(month, -1));
      if (e.key === "]") setMonth(shiftMonth(month, 1));
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [month, setMonth]);

  const handleAssign = async (categoryId: number, value: string) => {
    try {
      await api.assignMoney(categoryId, month, dollarsToCents(value));
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleAddGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;
    try {
      await api.createCategoryGroup(newGroupName.trim());
      setNewGroupName("");
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleAddCategory = async (groupId: number) => {
    const name = (newCategoryName[groupId] ?? "").trim();
    if (!name) return;
    try {
      await api.createCategory(name, groupId);
      setNewCategoryName({ ...newCategoryName, [groupId]: "" });
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  if (error) return <p className="error">{error}</p>;
  if (!budget) return <p>Loading…</p>;

  return (
    <div>
      <div className="month-nav">
        <button onClick={() => setMonth(shiftMonth(month, -1))}>← Prev</button>
        <h2>{monthLabel(month)}</h2>
        <button onClick={() => setMonth(shiftMonth(month, 1))}>Next →</button>
      </div>

      <div className={`rta-banner ${budget.ready_to_assign_cents < 0 ? "negative" : "positive"}`}>
        <span>Ready to Assign</span>
        <strong>{formatCents(budget.ready_to_assign_cents)}</strong>
      </div>

      {budget.groups.map((group) => (
        <div key={group.id} className="category-group">
          <h3>{group.name}</h3>
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Assigned</th>
                <th>Activity</th>
                <th>Available</th>
                <th>Goal</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {group.categories.map((cat) => (
                <tr key={cat.id}>
                  <td>{cat.name}</td>
                  <td>
                    {cat.is_system ? (
                      formatCents(cat.assigned_cents)
                    ) : (
                      <input
                        type="text"
                        defaultValue={(cat.assigned_cents / 100).toFixed(2)}
                        onBlur={(e) => handleAssign(cat.id, e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                      />
                    )}
                  </td>
                  <td className={cat.activity_cents < 0 ? "negative" : ""}>{formatCents(cat.activity_cents)}</td>
                  <td className={cat.available_cents < 0 ? "negative" : "positive"}>
                    {formatCents(cat.available_cents)}
                  </td>
                  <td>{!cat.is_system && <GoalEditor category={cat} onSaved={load} />}</td>
                  <td>{!cat.is_system && <NoteEditor category={cat} onSaved={load} />}</td>
                </tr>
              ))}
              {group.categories.length === 0 && (
                <tr>
                  <td colSpan={6} className="empty">
                    No categories yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              handleAddCategory(group.id);
            }}
          >
            <input
              placeholder="New category…"
              value={newCategoryName[group.id] ?? ""}
              onChange={(e) => setNewCategoryName({ ...newCategoryName, [group.id]: e.target.value })}
            />
            <button type="submit">+ Add category</button>
          </form>
        </div>
      ))}

      <form onSubmit={handleAddGroup} className="inline-form">
        <input placeholder="New category group…" value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)} />
        <button type="submit">+ Add group</button>
      </form>
    </div>
  );
}
