"use client";

import {
  DUE_BUCKET_LABELS,
  TASK_PRIORITIES,
  TASK_STATUS_LABELS,
  TASK_STATUSES,
} from "@/constants/tasks";
import type { TaskFilters } from "@/types/task";

interface TaskFiltersBarProps {
  filters: TaskFilters;
  onChange: (nextFilters: TaskFilters) => void;
}

const CLEARED_FILTERS: TaskFilters = {
  query: "",
  status: "all",
  priority: "all",
  dueBucket: "all",
};

export const TaskFiltersBar = ({ filters, onChange }: TaskFiltersBarProps) => {
  const hasActiveFilters =
    filters.query !== "" ||
    filters.status !== "all" ||
    filters.priority !== "all" ||
    filters.dueBucket !== "all";

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <div className="md:col-span-2">
          <label htmlFor="task-search" className="mb-1 block text-sm font-medium text-slate-700">
            Search
          </label>
          <input
            id="task-search"
            value={filters.query}
            onChange={(event) => onChange({ ...filters, query: event.target.value })}
            placeholder="Search title or description…"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500"
          />
        </div>

        <div>
          <label htmlFor="status-filter" className="mb-1 block text-sm font-medium text-slate-700">
            Status
          </label>
          <select
            id="status-filter"
            value={filters.status}
            onChange={(event) =>
              onChange({ ...filters, status: event.target.value as TaskFilters["status"] })
            }
            className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500"
          >
            <option value="all">All statuses</option>
            {TASK_STATUSES.map((status) => (
              <option key={status} value={status}>
                {TASK_STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="priority-filter" className="mb-1 block text-sm font-medium text-slate-700">
            Priority
          </label>
          <select
            id="priority-filter"
            value={filters.priority}
            onChange={(event) =>
              onChange({ ...filters, priority: event.target.value as TaskFilters["priority"] })
            }
            className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm text-slate-900 outline-none transition focus:border-slate-500"
          >
            <option value="all">All priorities</option>
            {TASK_PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>
                {priority}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {Object.entries(DUE_BUCKET_LABELS).map(([bucket, label]) => {
          const active = filters.dueBucket === bucket;
          return (
            <button
              key={bucket}
              type="button"
              onClick={() =>
                onChange({
                  ...filters,
                  dueBucket: bucket as TaskFilters["dueBucket"],
                })
              }
              className={`rounded-full border px-3 py-1 text-sm transition ${
                active
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-300 text-slate-700 hover:border-slate-500"
              }`}
            >
              {label}
            </button>
          );
        })}

        {hasActiveFilters ? (
          <button
            type="button"
            onClick={() => onChange(CLEARED_FILTERS)}
            className="ml-auto rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-500 transition hover:border-slate-500 hover:text-slate-700"
          >
            Clear filters
          </button>
        ) : null}
      </div>
    </section>
  );
};
