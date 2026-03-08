"use client";

import { TASK_PRIORITIES, TASK_STATUS_LABELS, TASK_STATUSES } from "@/constants/tasks";
import type { TaskDraft } from "@/types/task";
import { useState } from "react";

interface TaskFormProps {
  mode: "create" | "edit";
  initialDraft: TaskDraft;
  onSubmit: (draft: TaskDraft) => void;
  onCancel?: () => void;
}

export const TaskForm = ({ mode, initialDraft, onSubmit, onCancel }: TaskFormProps) => {
  const [draft, setDraft] = useState<TaskDraft>(initialDraft);
  const [error, setError] = useState<string>("");

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!draft.title.trim()) {
      setError("Title is required.");
      return;
    }

    onSubmit({
      ...draft,
      dueDate: draft.dueDate || undefined,
    });

    if (mode === "create") {
      setDraft(initialDraft);
    }
    setError("");
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <label htmlFor={`task-title-${mode}`} className="mb-1 block text-sm font-medium text-slate-700">
          Title
        </label>
        <input
          id={`task-title-${mode}`}
          value={draft.title}
          onChange={(event) => {
            if (error) {
              setError("");
            }
            setDraft((prev) => ({ ...prev, title: event.target.value }));
          }}
          placeholder="What needs to be done?"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none ring-0 transition focus:border-slate-500"
        />
      </div>

      <div>
        <label
          htmlFor={`task-description-${mode}`}
          className="mb-1 block text-sm font-medium text-slate-700"
        >
          Description
        </label>
        <textarea
          id={`task-description-${mode}`}
          value={draft.description}
          onChange={(event) => setDraft((prev) => ({ ...prev, description: event.target.value }))}
          placeholder="Optional details"
          rows={3}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500"
        />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label htmlFor={`task-status-${mode}`} className="mb-1 block text-sm font-medium text-slate-700">
            Status
          </label>
          <select
            id={`task-status-${mode}`}
            value={draft.status}
            onChange={(event) =>
              setDraft((prev) => ({ ...prev, status: event.target.value as TaskDraft["status"] }))
            }
            className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500"
          >
            {TASK_STATUSES.map((status) => (
              <option key={status} value={status}>
                {TASK_STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor={`task-priority-${mode}`} className="mb-1 block text-sm font-medium text-slate-700">
            Priority
          </label>
          <select
            id={`task-priority-${mode}`}
            value={draft.priority}
            onChange={(event) =>
              setDraft((prev) => ({ ...prev, priority: event.target.value as TaskDraft["priority"] }))
            }
            className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500"
          >
            {TASK_PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>
                {priority}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor={`task-due-date-${mode}`} className="mb-1 block text-sm font-medium text-slate-700">
            Due date
          </label>
          <input
            id={`task-due-date-${mode}`}
            type="date"
            value={draft.dueDate ?? ""}
            onChange={(event) => setDraft((prev) => ({ ...prev, dueDate: event.target.value }))}
            className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500"
          />
        </div>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="submit"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          {mode === "create" ? "Add task" : "Save changes"}
        </button>
        {mode === "edit" && onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400"
          >
            Cancel
          </button>
        ) : null}
      </div>
    </form>
  );
};
