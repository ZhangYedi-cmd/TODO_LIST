import type { Task, TaskDraft, TaskStatus } from "@/types/task";
import {
  createTask,
  setTaskStatus,
  toggleTaskDone,
  updateTaskFromDraft,
} from "@/utils/taskUtils";

export interface TaskState {
  tasks: Task[];
}

export type TaskAction =
  | { type: "hydrate"; tasks: Task[] }
  | { type: "create"; draft: TaskDraft }
  | { type: "update"; id: string; draft: TaskDraft }
  | { type: "delete"; id: string }
  | { type: "set_status"; id: string; status: TaskStatus }
  | { type: "toggle_done"; id: string };

export const initialTaskState: TaskState = {
  tasks: [],
};

const updateTaskById = (
  tasks: Task[],
  id: string,
  updater: (task: Task) => Task,
): Task[] => {
  return tasks.map((task) => {
    if (task.id !== id) {
      return task;
    }

    return updater(task);
  });
};

export const taskReducer = (state: TaskState, action: TaskAction): TaskState => {
  switch (action.type) {
    case "hydrate": {
      return { tasks: action.tasks };
    }

    case "create": {
      return {
        tasks: [createTask(action.draft), ...state.tasks],
      };
    }

    case "update": {
      return {
        tasks: updateTaskById(state.tasks, action.id, (task) =>
          updateTaskFromDraft(task, action.draft),
        ),
      };
    }

    case "delete": {
      return {
        tasks: state.tasks.filter((task) => task.id !== action.id),
      };
    }

    case "set_status": {
      return {
        tasks: updateTaskById(state.tasks, action.id, (task) =>
          setTaskStatus(task, action.status),
        ),
      };
    }

    case "toggle_done": {
      return {
        tasks: updateTaskById(state.tasks, action.id, (task) => toggleTaskDone(task)),
      };
    }

    default: {
      return state;
    }
  }
};
