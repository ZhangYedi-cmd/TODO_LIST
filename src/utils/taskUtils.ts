import type {
  Task,
  TaskDraft,
  TaskFilters,
  TaskPriority,
  TaskStatus,
} from "@/types/task";

const DATE_ONLY_REGEX = /^\d{4}-\d{2}-\d{2}$/;

const PRIORITY_ORDER: Record<TaskPriority, number> = {
  P1: 1,
  P2: 2,
  P3: 3,
};

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === "object" && value !== null;
};

const isTaskStatus = (value: unknown): value is TaskStatus => {
  return value === "todo" || value === "in_progress" || value === "done";
};

const isTaskPriority = (value: unknown): value is TaskPriority => {
  return value === "P1" || value === "P2" || value === "P3";
};

const toIsoString = (timestamp: number): string => new Date(timestamp).toISOString();

const toDateKey = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export const makeTaskId = (): string => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `task-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

export const normalizeDueDate = (value?: string): string | undefined => {
  if (!value) {
    return undefined;
  }

  const trimmed = value.trim();
  return DATE_ONLY_REGEX.test(trimmed) ? trimmed : undefined;
};

export const createTask = (
  draft: TaskDraft,
  options?: { now?: number; id?: string },
): Task => {
  const now = options?.now ?? Date.now();
  const createdAt = toIsoString(now);
  const status = draft.status;

  return {
    id: options?.id ?? makeTaskId(),
    title: draft.title.trim(),
    description: draft.description.trim(),
    status,
    priority: draft.priority,
    dueDate: normalizeDueDate(draft.dueDate),
    createdAt,
    updatedAt: createdAt,
    completedAt: status === "done" ? createdAt : undefined,
  };
};

export const setTaskStatus = (
  task: Task,
  status: TaskStatus,
  now: number = Date.now(),
): Task => {
  const updatedAt = toIsoString(now);

  if (status === "done") {
    return {
      ...task,
      status,
      updatedAt,
      completedAt: task.completedAt ?? updatedAt,
    };
  }

  return {
    ...task,
    status,
    updatedAt,
    completedAt: undefined,
  };
};

export const updateTaskFromDraft = (
  task: Task,
  draft: TaskDraft,
  now: number = Date.now(),
): Task => {
  const withStatus = setTaskStatus(task, draft.status, now);

  return {
    ...withStatus,
    title: draft.title.trim(),
    description: draft.description.trim(),
    priority: draft.priority,
    dueDate: normalizeDueDate(draft.dueDate),
  };
};

export const toggleTaskDone = (task: Task, now: number = Date.now()): Task => {
  if (task.status === "done") {
    return setTaskStatus(task, "todo", now);
  }

  return setTaskStatus(task, "done", now);
};

export const matchesKeyword = (task: Task, query: string): boolean => {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return true;
  }

  const haystack = `${task.title} ${task.description}`.toLowerCase();
  return haystack.includes(normalized);
};

export const isDueToday = (task: Task, now: Date = new Date()): boolean => {
  return Boolean(task.dueDate && task.dueDate === toDateKey(now));
};

export const isOverdue = (task: Task, now: Date = new Date()): boolean => {
  if (!task.dueDate) {
    return false;
  }

  return task.status !== "done" && task.dueDate < toDateKey(now);
};

export const filterTasks = (
  tasks: Task[],
  filters: TaskFilters,
  now: Date = new Date(),
): Task[] => {
  return tasks.filter((task) => {
    if (!matchesKeyword(task, filters.query)) {
      return false;
    }

    if (filters.status !== "all" && task.status !== filters.status) {
      return false;
    }

    if (filters.priority !== "all" && task.priority !== filters.priority) {
      return false;
    }

    if (filters.dueBucket === "today" && !isDueToday(task, now)) {
      return false;
    }

    if (filters.dueBucket === "overdue" && !isOverdue(task, now)) {
      return false;
    }

    return true;
  });
};

export const sortTasksForBoard = (tasks: Task[]): Task[] => {
  return [...tasks].sort((a, b) => {
    const priorityDiff = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
    if (priorityDiff !== 0) {
      return priorityDiff;
    }

    return a.updatedAt < b.updatedAt ? 1 : -1;
  });
};

const toStringOrEmpty = (value: unknown): string => {
  return typeof value === "string" ? value : "";
};

export const normalizeTask = (value: unknown): Task | null => {
  if (!isRecord(value)) {
    return null;
  }

  const id = toStringOrEmpty(value.id).trim();
  const title = toStringOrEmpty(value.title).trim();
  const description = toStringOrEmpty(value.description).trim();
  const createdAt = toStringOrEmpty(value.createdAt);
  const updatedAt = toStringOrEmpty(value.updatedAt);

  if (!id || !title || !createdAt || !updatedAt) {
    return null;
  }

  if (!isTaskStatus(value.status) || !isTaskPriority(value.priority)) {
    return null;
  }

  const dueDate = normalizeDueDate(toStringOrEmpty(value.dueDate));
  const completedAtRaw = toStringOrEmpty(value.completedAt);

  return {
    id,
    title,
    description,
    status: value.status,
    priority: value.priority,
    dueDate,
    createdAt,
    updatedAt,
    completedAt: completedAtRaw || undefined,
  };
};

export const deserializeTasks = (raw: string): Task[] => {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .map((value) => normalizeTask(value))
      .filter((task): task is Task => Boolean(task));
  } catch {
    return [];
  }
};
