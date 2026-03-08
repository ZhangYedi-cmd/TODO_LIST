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

    window.localStorage.setItem(TASK_STORAGE_KEY, JSON.stringify(state.tasks));
  }, [state.tasks, hasHydrated]);

  return {
    tasks: state.tasks,
    hasHydrated,
    dispatch,
  };
};
