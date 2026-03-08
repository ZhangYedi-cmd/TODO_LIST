import { describe, expect, it, vi } from "vitest";
import type { Task } from "@/types/task";
import { initialTaskState, taskReducer } from "@/state/taskReducer";

const sampleTask: Task = {
  id: "task-1",
  title: "Sample",
  description: "sample desc",
  status: "todo",
  priority: "P2",
  dueDate: "2026-03-10",
  createdAt: "2026-03-08T00:00:00.000Z",
  updatedAt: "2026-03-08T00:00:00.000Z",
};

describe("taskReducer", () => {
  it("hydrates from storage", () => {
    const state = taskReducer(initialTaskState, { type: "hydrate", tasks: [sampleTask] });
    expect(state.tasks).toEqual([sampleTask]);
  });

  it("creates updates and deletes tasks", () => {
    const dateNowSpy = vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-03-08T01:00:00.000Z"));

    const createdState = taskReducer(initialTaskState, {
      type: "create",
      draft: {
        title: "New",
        description: "desc",
        status: "todo",
        priority: "P1",
      },
    });

    expect(createdState.tasks).toHaveLength(1);
    expect(createdState.tasks[0].title).toBe("New");

    const updatedState = taskReducer(createdState, {
      type: "update",
      id: createdState.tasks[0].id,
      draft: {
        title: "Updated",
        description: "desc 2",
        status: "in_progress",
        priority: "P3",
      },
    });

    expect(updatedState.tasks[0].title).toBe("Updated");
    expect(updatedState.tasks[0].status).toBe("in_progress");

    const deletedState = taskReducer(updatedState, {
      type: "delete",
      id: updatedState.tasks[0].id,
    });

    expect(deletedState.tasks).toHaveLength(0);
    dateNowSpy.mockRestore();
  });

  it("handles status actions", () => {
    const hydrated = taskReducer(initialTaskState, { type: "hydrate", tasks: [sampleTask] });

    const done = taskReducer(hydrated, {
      type: "set_status",
      id: "task-1",
      status: "done",
    });
    expect(done.tasks[0].status).toBe("done");
    expect(done.tasks[0].completedAt).toBeTruthy();

    const reopened = taskReducer(done, {
      type: "toggle_done",
      id: "task-1",
    });
    expect(reopened.tasks[0].status).toBe("todo");
    expect(reopened.tasks[0].completedAt).toBeUndefined();
  });
});
