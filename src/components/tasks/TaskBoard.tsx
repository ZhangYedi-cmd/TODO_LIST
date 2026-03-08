"use client";

import { TASK_STATUS_LABELS, TASK_STATUSES } from "@/constants/tasks";
import type { Task, TaskStatus } from "@/types/task";
import { sortTasksForBoard } from "@/utils/taskUtils";
import { TaskCard } from "./TaskCard";

interface TaskBoardProps {
  tasks: Task[];
  onEdit: (taskId: string) => void;
  onDelete: (taskId: string) => void;
  onToggleDone: (taskId: string) => void;
  onMoveStatus: (taskId: string, status: TaskStatus) => void;
}

const groupByStatus = (tasks: Task[]): Record<TaskStatus, Task[]> => {
  const groups: Record<TaskStatus, Task[]> = {
    todo: [],
    in_progress: [],
    done: [],
  };

  tasks.forEach((task) => {
    groups[task.status].push(task);
  });

  return {
    todo: sortTasksForBoard(groups.todo),
    in_progress: sortTasksForBoard(groups.in_progress),
    done: sortTasksForBoard(groups.done),
  };
};

export const TaskBoard = ({ tasks, onEdit, onDelete, onToggleDone, onMoveStatus }: TaskBoardProps) => {
  if (tasks.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-600">
        <h2 className="text-base font-semibold text-slate-900">No tasks found</h2>
        <p className="mt-2 text-sm">Create a task or adjust your filters to see results.</p>
      </section>
    );
  }

  const groups = groupByStatus(tasks);

  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      {TASK_STATUSES.map((status) => (
        <div key={status} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-800">{TASK_STATUS_LABELS[status]}</h2>
            <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-600">
              {groups[status].length}
            </span>
          </div>

          {groups[status].length === 0 ? (
            <p className="rounded-md border border-dashed border-slate-300 bg-white p-3 text-xs text-slate-500">
              No tasks in this column.
            </p>
          ) : (
            <div className="space-y-2">
              {groups[status].map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onToggleDone={onToggleDone}
                  onMoveStatus={onMoveStatus}
                />
              ))}
            </div>
          )}
        </div>
      ))}
    </section>
  );
};
