"use client";

import { TaskBoard } from "@/components/tasks/TaskBoard";
import { TaskFiltersBar } from "@/components/tasks/TaskFiltersBar";
import { TaskForm } from "@/components/tasks/TaskForm";
import { useTaskStore } from "@/hooks/useTaskStore";
import type { TaskDraft, TaskFilters, TaskStatus } from "@/types/task";
import { filterTasks } from "@/utils/taskUtils";
import { useEffect, useMemo, useRef, useState } from "react";

const CREATE_TASK_DRAFT: TaskDraft = {
  title: "",
  description: "",
  status: "todo",
  priority: "P2",
  dueDate: undefined,
};

const INITIAL_FILTERS: TaskFilters = {
  query: "",
  status: "all",
  priority: "all",
  dueBucket: "all",
};

const toDraft = (task: {
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskDraft["priority"];
  dueDate?: string;
}): TaskDraft => ({
  title: task.title,
  description: task.description,
  status: task.status,
  priority: task.priority,
  dueDate: task.dueDate,
});

export default function HomePage() {
  const { tasks, hasHydrated, dispatch } = useTaskStore();
  const [filters, setFilters] = useState<TaskFilters>(INITIAL_FILTERS);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const editFormRef = useRef<HTMLDivElement>(null);

  const editingTask = useMemo(
    () => tasks.find((task) => task.id === editingTaskId) ?? null,
    [tasks, editingTaskId],
  );

  const visibleTasks = useMemo(() => filterTasks(tasks, filters), [tasks, filters]);

  useEffect(() => {
    if (editingTaskId && editFormRef.current) {
      editFormRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [editingTaskId]);

  const handleCreate = (draft: TaskDraft) => {
    dispatch({ type: "create", draft });
  };

  const handleEditSubmit = (draft: TaskDraft) => {
    if (!editingTaskId) {
      return;
    }

    dispatch({ type: "update", id: editingTaskId, draft });
    setEditingTaskId(null);
  };

  const handleDelete = (taskId: string) => {
    dispatch({ type: "delete", id: taskId });
    if (editingTaskId === taskId) setEditingTaskId(null);
  };

  const handleMoveStatus = (taskId: string, status: TaskStatus) => {
    dispatch({ type: "set_status", id: taskId, status });
  };

  const handleToggleDone = (taskId: string) => {
    dispatch({ type: "toggle_done", id: taskId });
  };

  return (
    <main className="min-h-screen bg-slate-100 px-4 py-8 text-slate-900 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-6xl space-y-4">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">My TODO List</h1>
          <p className="text-sm text-slate-500">
            Track tasks across{" "}
            <span className="font-medium text-slate-700">Todo</span>,{" "}
            <span className="font-medium text-blue-700">In Progress</span>, and{" "}
            <span className="font-medium text-green-700">Done</span>.
          </p>
        </header>

        {!hasHydrated ? (
          <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500">
            Restoring saved tasks…
          </p>
        ) : null}

        <TaskForm mode="create" initialDraft={CREATE_TASK_DRAFT} onSubmit={handleCreate} />

        {editingTask ? (
          <div ref={editFormRef} className="rounded-xl border border-blue-200 bg-blue-50 p-3">
            <h2 className="mb-2 text-sm font-semibold text-blue-800">
              Editing: {editingTask.title}
            </h2>
            <TaskForm
              key={editingTask.id}
              mode="edit"
              initialDraft={toDraft(editingTask)}
              onSubmit={handleEditSubmit}
              onCancel={() => setEditingTaskId(null)}
            />
          </div>
        ) : null}

        <TaskFiltersBar filters={filters} onChange={setFilters} />

        <TaskBoard
          tasks={visibleTasks}
          totalTaskCount={tasks.length}
          onEdit={setEditingTaskId}
          onDelete={handleDelete}
          onToggleDone={handleToggleDone}
          onMoveStatus={handleMoveStatus}
        />
      </div>
    </main>
  );
}
