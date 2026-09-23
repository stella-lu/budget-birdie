import { useState } from "react";
import { api } from "../api";
import { dollarsToCents, formatCents } from "../money";
import type { CategoryBudget, GoalType } from "../types";

const GOAL_LABELS: Record<GoalType, string> = {
  target_balance: "Target balance",
  target_balance_by_date: "Target balance by date",
  monthly_funding: "Monthly funding",
};

export function GoalEditor({ category, onSaved }: { category: CategoryBudget; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [goalType, setGoalType] = useState<GoalType>(category.goal_type ?? "monthly_funding");
  const [amount, setAmount] = useState(
    category.goal_amount_cents ? (category.goal_amount_cents / 100).toFixed(2) : ""
  );
  const [goalDate, setGoalDate] = useState(category.goal_date ?? "");
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    if (!amount) return;
    try {
      await api.setGoal(
        category.id,
        goalType,
        dollarsToCents(amount),
        goalType === "target_balance_by_date" ? goalDate || null : null
      );
      setEditing(false);
      onSaved();
    } catch (e) {
      setError(String(e));
    }
  };

  const clear = async () => {
    try {
      await api.setGoal(category.id, null, null, null);
      setEditing(false);
      onSaved();
    } catch (e) {
      setError(String(e));
    }
  };

  if (editing) {
    return (
      <div className="goal-editor">
        {error && <p className="error">{error}</p>}
        <select value={goalType} onChange={(e) => setGoalType(e.target.value as GoalType)}>
          {(Object.keys(GOAL_LABELS) as GoalType[]).map((t) => (
            <option key={t} value={t}>
              {GOAL_LABELS[t]}
            </option>
          ))}
        </select>
        <input placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
        {goalType === "target_balance_by_date" && (
          <input type="date" value={goalDate} onChange={(e) => setGoalDate(e.target.value)} />
        )}
        <button type="button" onClick={save}>
          Save
        </button>
        {category.goal_type && (
          <button type="button" onClick={clear}>
            Clear
          </button>
        )}
        <button type="button" onClick={() => setEditing(false)}>
          Cancel
        </button>
      </div>
    );
  }

  if (!category.goal_type) {
    return (
      <button type="button" className="goal-set-link" onClick={() => setEditing(true)}>
        Set goal
      </button>
    );
  }

  return (
    <button type="button" className={`goal-progress ${category.goal_met ? "goal-met" : ""}`} onClick={() => setEditing(true)}>
      <div className="goal-bar">
        <div className="goal-bar-fill" style={{ width: `${category.goal_progress_pct ?? 0}%` }} />
      </div>
      <span>
        {category.goal_met
          ? "Goal met ✓"
          : category.goal_type === "monthly_funding"
            ? `Need ${formatCents(category.goal_needed_this_month_cents ?? 0)} this month`
            : `${formatCents(category.goal_needed_this_month_cents ?? 0)}/mo to reach goal`}
      </span>
    </button>
  );
}
