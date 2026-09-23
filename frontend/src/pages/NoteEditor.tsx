import { useState } from "react";
import { api } from "../api";
import type { CategoryBudget } from "../types";

export function NoteEditor({ category, onSaved }: { category: CategoryBudget; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(category.note ?? "");
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    try {
      await api.setNote(category.id, value.trim() || null);
      setEditing(false);
      onSaved();
    } catch (e) {
      setError(String(e));
    }
  };

  if (editing) {
    return (
      <div className="note-editor">
        {error && <p className="error">{error}</p>}
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Note for this category…"
          rows={2}
        />
        <div className="inline-form">
          <button type="button" onClick={save}>
            Save
          </button>
          <button type="button" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (!category.note) {
    return (
      <button type="button" className="goal-set-link" onClick={() => setEditing(true)}>
        Add note
      </button>
    );
  }

  return (
    <button type="button" className="note-text" onClick={() => setEditing(true)} title="Click to edit">
      {category.note}
    </button>
  );
}
