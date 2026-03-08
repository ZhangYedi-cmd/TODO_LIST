"use client";

import { TASK_STATUS_LABELS, TASK_STATUSES } from "@/constants/tasks";
import type { Task, TaskStatus } from "@/types/task";
import { isDueToday, isOverdue } from "@/utils/taskUtils";

interface TaskCardProps {
  task: Task;
  onEdit: (taskId: string) => void;
  onDelete: (taskId: string) => void;
  onToggleDone: (taskId: string) => void;
  onMoveStatus: (taskId: string, status: TaskStatus) => void;
}

const formatDate = (dateKey: string): string => {
  const date = new Date(`${dateKey}T00:00:00`);
  return Number.isNaN(date.getTime()) ? dateKey : date.toLocaleDateString();
};

export const TaskCard = ({ task, onEdit, onDelete, onToggleDone, onMoveStatus }: TaskCardProps) => {
  const overdue = isOverdue(task);
  const dueToday = isDueToday(task);

  return (
    <article className="space-y-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3
            className={`text-sm font-semibold ${task.status === "done" ? "text-slate-500 line-through" : "text-slate-900"}`}
          >
            {task.title}
          </h3>
          <p className="mt-1 text-xs text-slate-600">Priority: {task.priority}</p>
        </div>
        <select
          value={task.status}
          onChange={(event) => onMoveStatus(task.id, event.target.value as TaskStatus)}
          className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700"
          aria-label={`Move ${task.title} status`}
        >
          {TASK_STATUSES.map((status) => (
            <option key={status} value={status}>
              {TASK_STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </header>

      {task.description ? <p className="text-sm text-slate-700">{task.description}</p> : null}

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
        <span>Updated: {new Date(task.updatedAt).toLocaleString()}</span>
        {task.dueDate ? (
          <span className={overdue ? "font-semibold text-red-600" : dueToday ? "font-semibold text-amber-700" : ""}>
            Due: {formatDate(task.dueDate)}
          </span>
        ) : (
          <span>Due: none</span>
        )}
      </div>

      <footer className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onToggleDone(task.id)}
          className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 transition hover:border-slate-500"
        >
          {task.status === "done" ? "Reopen" : "Mark done"}
        </button>
        <button
          type="button"
          onClick={() => onEdit(task.id)}
          className="rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 transition hover:border-slate-500"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => onDelete(task.id)}
          className="rounded-md border border-red-300 px-2 py-1 text-xs font-medium text-red-700 transition hover:border-red-500"
        >
          Delete
        </button>
      </footer>
    </article>
  );
};
