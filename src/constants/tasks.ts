import type { DueBucket, TaskPriority, TaskStatus } from "@/types/task";

export const TASK_STATUSES: TaskStatus[] = ["todo", "in_progress", "done"];
export const TASK_PRIORITIES: TaskPriority[] = ["P1", "P2", "P3"];
export const DUE_BUCKETS: DueBucket[] = ["all", "today", "overdue"];

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "Todo",
  in_progress: "In Progress",
  done: "Done",
};

export const DUE_BUCKET_LABELS: Record<DueBucket, string> = {
  all: "All deadlines",
  today: "Due today",
  overdue: "Overdue",
};

export const TASK_STORAGE_KEY = "todo-list.v1.tasks";
