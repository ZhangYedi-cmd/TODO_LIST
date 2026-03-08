"use client";

import { TASK_STATUS_LABELS, TASK_STATUSES } from "@/constants/tasks";
import type { Task, TaskStatus } from "@/types/task";
import { sortTasksForBoard } from "@/utils/taskUtils";
import { TaskCard } from "./TaskCard";

interface TaskBoardProps {
  tasks: Task[];
  totalTaskCount: number;
  onEdit: (taskId: string) => void;
  onDelete: (taskId: string) => void;
  onToggleDone: (taskId: string) => void;
  onMoveStatus: (taskId: string, status: TaskStatus) => void;
}

const COLUMN_STYLE: Record<TaskStatus, { wrapper: string; header: string; count: string }> = {
  todo: {
    wrapper: "border-slate-200 bg-slate-50",
    header: "text-slate-700",
    count: "bg-slate-200 text-slate-700",
  },
  in_progress: {
    wrapper: "border-blue-200 bg-blue-50",
    header: "text-blue-800",
    count: "bg-blue-100 text-blue-700",
  },
  done: {
    wrapper: "border-green-200 bg-green-50",
    header: "text-green-800",
    count: "bg-green-100 text-green-700",
  },
};

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

export const TaskBoard = ({
  tasks,
  totalTaskCount,
  onEdit,
  onDelete,
  onToggleDone,
  onMoveStatus,
}: TaskBoardProps) => {
  if (tasks.length === 0) {
    return (
      <section className="rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center">
        <p className="text-2xl">📋</p>
        <h2 className="mt-3 text-base font-semibold text-slate-900">
          {totalTaskCount === 0 ? "No tasks yet" : "No matching tasks"}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {totalTaskCount === 0
            ? "Add your first task above to get started."
            : "Try adjusting your search or filters above."}
        </p>
      </section>
    );
  }

  const groups = groupByStatus(tasks);

  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      {TASK_STATUSES.map((status) => {
        const style = COLUMN_STYLE[status];
        return (
          <div key={status} className={`rounded-xl border p-3 ${style.wrapper}`}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className={`text-sm font-semibold ${style.header}`}>
                {TASK_STATUS_LABELS[status]}
              </h2>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style.count}`}>
                {groups[status].length}
              </span>
            </div>

            {groups[status].length === 0 ? (
              <p className="rounded-md border border-dashed border-slate-300 bg-white/60 p-3 text-xs text-slate-400">
                Nothing here yet.
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
        );
      })}
    </section>
  );
};
