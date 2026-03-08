# TODO List

A keyboard-friendly personal task manager built with Next.js and TypeScript. Tasks are persisted locally in the browser — no backend required.

---

## Features

### Task management (CRUD)
- **Create** tasks with title (required), description, priority, status, and optional due date
- **Edit** any field inline via a dedicated edit panel
- **Delete** with a two-click inline confirmation (no disruptive browser dialogs)
- **Complete** tasks with one click ("Mark done" / "Reopen")

### Kanban board
- Three columns: **Todo**, **In Progress**, **Done**
- Cards sorted by priority (P1 → P2 → P3) then by most-recently updated
- Color-coded columns and priority badges for at-a-glance scanning

### Priority levels
| Badge | Meaning |
|-------|---------|
| **P1** | High — do it now |
| **P2** | Medium — do it soon |
| **P3** | Low — do it eventually |

### Due-date urgency indicators
- Red badge: task is **overdue**
- Amber badge: task is **due today**
- Normal: future due date or no date set

### Filters & search
- Full-text search across title and description
- Filter by status (Todo / In Progress / Done)
- Filter by priority (P1 / P2 / P3)
- Quick-filter for **Due today** or **Overdue** tasks
- "Clear filters" button appears whenever any filter is active

### Keyboard shortcuts
| Shortcut | Action |
|----------|--------|
| `⌘ ↵` / `Ctrl ↵` | Submit the focused form (create or edit) |
| `Esc` | Cancel the edit form |

---

## Local development

**Prerequisites:** Node.js 18+ and npm.

```bash
# Install dependencies
npm install

# Start the dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Other useful commands

```bash
npm run build   # Production build
npm run lint    # ESLint check
npm test        # Unit tests (Vitest)
```

---

## How persistence works

Tasks are stored in **`localStorage`** under the key `todo-list.v1.tasks` as a JSON array.

- Data is saved automatically after every state change.
- On page load, the stored JSON is parsed and validated field-by-field. Malformed or missing entries are silently skipped — the app never crashes on corrupt data.
- If `localStorage` is unavailable (e.g. quota exceeded, certain private-browsing modes), the app falls back gracefully and keeps data in memory for the current session. A warning is not surfaced to the user; this is a known limitation.

---

## Known limitations

| Limitation | Detail |
|-----------|--------|
| **No cross-device sync** | Data lives in one browser's localStorage only |
| **No collaboration** | Single-user only; no sharing or multi-user support |
| **No cloud backup** | Clearing site data / switching browsers loses tasks |
| **Storage quota** | Browsers typically cap localStorage at ~5 MB; very large task lists may silently fail to save |
| **No offline PWA** | The app requires a network connection to load Next.js assets |

---

## Tech stack

- [Next.js 15](https://nextjs.org/) (App Router, `"use client"`)
- [TypeScript](https://www.typescriptlang.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Vitest](https://vitest.dev/) for unit tests
