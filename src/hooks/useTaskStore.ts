"use client";

import { useEffect, useReducer, useState } from "react";
import { TASK_STORAGE_KEY } from "@/constants/tasks";
import { initialTaskState, taskReducer } from "@/state/taskReducer";
import { deserializeTasks } from "@/utils/taskUtils";

export const useTaskStore = () => {
  const [state, dispatch] = useReducer(taskReducer, initialTaskState);
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(TASK_STORAGE_KEY);
      if (raw) {
        dispatch({ type: "hydrate", tasks: deserializeTasks(raw) });
      }
    } finally {
      setHasHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    try {
      window.localStorage.setItem(TASK_STORAGE_KEY, JSON.stringify(state.tasks));
    } catch {
      // localStorage may be unavailable (quota exceeded, private browsing restrictions, etc.)
      // Data will remain in-memory for the current session.
    }
  }, [state.tasks, hasHydrated]);

  return {
    tasks: state.tasks,
    hasHydrated,
    dispatch,
  };
};
