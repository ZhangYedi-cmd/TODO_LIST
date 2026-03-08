export type TaskStatus = "todo" | "in_progress" | "done";

export type TaskPriority = "P1" | "P2" | "P3";

export type DueBucket = "all" | "today" | "overdue";

export type StatusFilter = "all" | TaskStatus;

export type PriorityFilter = "all" | TaskPriority;

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  dueDate?: string;
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

export interface TaskDraft {
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  dueDate?: string;
}

export interface TaskFilters {
  query: string;
  status: StatusFilter;
  priority: PriorityFilter;
  dueBucket: DueBucket;
}
