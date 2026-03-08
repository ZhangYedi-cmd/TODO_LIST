import { describe, expect, it } from "vitest";
import type { Task } from "@/types/task";
import {
  createTask,
  deserializeTasks,
  filterTasks,
  isDueToday,
  isOverdue,
  setTaskStatus,
  toggleTaskDone,
} from "@/utils/taskUtils";

const baseTask: Task = {
  id: "1",
  title: "Write docs",
  description: "Ship the release notes",
  status: "todo",
  priority: "P2",
  dueDate: "2026-03-08",
  createdAt: "2026-03-07T10:00:00.000Z",
  updatedAt: "2026-03-07T10:00:00.000Z",
};

describe("taskUtils", () => {
  it("creates tasks with required fields", () => {
    const task = createTask(
      {
        title: "  New task  ",
        description: "  details  ",
        status: "todo",
        priority: "P1",
      },
      { now: Date.parse("2026-03-08T00:00:00.000Z"), id: "task-123" },
    );

    expect(task).toMatchObject({
      id: "task-123",
      title: "New task",
      description: "details",
      status: "todo",
      priority: "P1",
      createdAt: "2026-03-08T00:00:00.000Z",
      updatedAt: "2026-03-08T00:00:00.000Z",
    });
  });

  it("transitions done and reopen correctly", () => {
    const done = setTaskStatus(baseTask, "done", Date.parse("2026-03-09T00:00:00.000Z"));
    expect(done.status).toBe("done");
    expect(done.completedAt).toBe("2026-03-09T00:00:00.000Z");

    const reopened = toggleTaskDone(done, Date.parse("2026-03-10T00:00:00.000Z"));
    expect(reopened.status).toBe("todo");
    expect(reopened.completedAt).toBeUndefined();
  });

  it("filters by keyword status priority and due bucket", () => {
    const now = new Date(2026, 2, 8, 9, 0, 0);
    const tasks: Task[] = [
      baseTask,
      {
        ...baseTask,
        id: "2",
        title: "Bugfix API",
        description: "Backend",
        priority: "P1",
        dueDate: "2026-03-07",
      },
      {
        ...baseTask,
        id: "3",
        title: "Done task",
        status: "done",
        dueDate: "2026-03-07",
        completedAt: "2026-03-07T12:00:00.000Z",
      },
    ];

    expect(isDueToday(tasks[0], now)).toBe(true);
    expect(isOverdue(tasks[1], now)).toBe(true);
    expect(isOverdue(tasks[2], now)).toBe(false);

    const filtered = filterTasks(
      tasks,
      {
        query: "api",
        status: "all",
        priority: "P1",
        dueBucket: "overdue",
      },
      now,
    );

    expect(filtered).toHaveLength(1);
    expect(filtered[0].id).toBe("2");
  });

  it("deserializes and drops invalid localStorage entries", () => {
    const raw = JSON.stringify([
      {
        ...baseTask,
      },
      {
        id: "",
        title: "invalid",
      },
    ]);

    const tasks = deserializeTasks(raw);
    expect(tasks).toHaveLength(1);
    expect(tasks[0].id).toBe("1");
  });
});
