"use client";

import { useEffect, useRef, useState } from "react";
import { TASK_STATUS_LABELS, TASK_STATUSES } from "@/constants/tasks";
import type { Task, TaskPriority, TaskStatus } from "@/types/task";
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

const PRIORITY_BADGE: Record<TaskPriority, string> = {
  P1: "border border-red-200 bg-red-100 text-red-700",
  P2: "border border-amber-200 bg-amber-100 text-amber-700",
  P3: "border border-slate-200 bg-slate-100 text-slate-600",
};

export const TaskCard = ({ task, onEdit, onDelete, onToggleDone, onMoveStatus }: TaskCardProps) => {
  const overdue = isOverdue(task);
  const dueToday = isDueToday(task);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const confirmTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (confirmTimer.current) clearTimeout(confirmTimer.current);
    };
  }, []);

  const handleDeleteClick = () => {
    if (confirmDelete) {
      if (confirmTimer.current) clearTimeout(confirmTimer.current);
      onDelete(task.id);
    } else {
      setConfirmDelete(true);
      confirmTimer.current = setTimeout(() => setConfirmDelete(false), 3000);
    }
  };

  return (
    <article className="space-y-2.5 rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition hover:shadow-md">
      <header className="flex items-start justify-between gap-2">
        <h3
          className={`flex-1 text-sm font-semibold leading-snug ${
            task.status === "done" ? "text-slate-400 line-through" : "text-slate-900"
          }`}
        >
          {task.title}
        </h3>
        <select
          value={task.status}
          onChange={(event) => onMoveStatus(task.id, event.target.value as TaskStatus)}
          className="shrink-0 rounded-md border border-slate-300 bg-transparent px-2 py-1 text-xs text-slate-700 transition focus:border-slate-500 focus:outline-none"
          aria-label={`Move ${task.title} status`}
        >
          {TASK_STATUSES.map((status) => (
            <option key={status} value={status}>
              {TASK_STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </header>

      <div className="flex flex-wrap items-center gap-1.5">
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${PRIORITY_BADGE[task.priority]}`}>
          {task.priority}
        </span>
        {task.dueDate ? (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              overdue
                ? "border border-red-200 bg-red-100 text-red-700"
                : dueToday
                  ? "border border-amber-200 bg-amber-100 text-amber-700"
                  : "border border-slate-200 bg-slate-100 text-slate-600"
            }`}
          >
            {overdue ? "Overdue · " : dueToday ? "Today · " : "Due "}
            {formatDate(task.dueDate)}
          </span>
        ) : null}
        <span className="ml-auto text-xs text-slate-400">
          {new Date(task.updatedAt).toLocaleDateString()}
        </span>
      </div>

      {task.description ? (
        <p className="text-xs leading-relaxed text-slate-600">{task.description}</p>
      ) : null}

      <footer className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={() => onToggleDone(task.id)}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
            task.status === "done"
              ? "border border-slate-300 text-slate-600 hover:border-slate-400 hover:bg-slate-50"
              : "bg-emerald-600 text-white hover:bg-emerald-700"
          }`}
        >
          {task.status === "done" ? "Reopen" : "Mark done"}
        </button>
        <button
          type="button"
          onClick={() => onEdit(task.id)}
          className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={handleDeleteClick}
          onBlur={() => {
            if (confirmTimer.current) clearTimeout(confirmTimer.current);
            setConfirmDelete(false);
          }}
          className={`ml-auto rounded-md px-2.5 py-1 text-xs font-medium transition ${
            confirmDelete
              ? "border border-red-600 bg-red-600 text-white hover:bg-red-700"
              : "border border-red-200 text-red-600 hover:border-red-400 hover:bg-red-50"
          }`}
        >
          {confirmDelete ? "Confirm?" : "Delete"}
        </button>
      </footer>
    </article>
  );
};
