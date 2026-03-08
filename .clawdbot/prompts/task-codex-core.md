You are Codex, implementing the core TODO feature set for this Next.js TypeScript app.

Context:
- Read docs/TODOLIST-FEATURES.md first.
- This repo is a fresh Next.js app scaffold.

Goal:
Implement the full core of TODO LIST v1 with production-safe code.

Must implement:
1) Data model
- Task fields: id, title, description, status(todo|in_progress|done), priority(P1|P2|P3), dueDate(optional), createdAt, updatedAt, completedAt(optional)

2) Core behaviors
- Create / edit / delete task
- Mark done / reopen
- Move status between todo / in_progress / done
- Search by keyword (title + description)
- Filter by status / priority / due bucket(today, overdue, all)

3) Persistence
- localStorage persistence
- Safe hydration for Next.js client component

4) UI baseline
- Replace default page with usable task app UI
- Desktop-first but mobile usable
- Empty state + simple validation feedback

5) Quality
- Add tests for core state/filter logic (at least reducer or pure utility tests)
- Keep structure clean (types, utils, components split)

Validation to run:
- npm run lint
- npm run build
- run tests if you add test script

Deliverables:
- Code changes committed locally with a clear commit message
- Leave a concise summary in terminal output: what implemented, file map, risks

Important constraints:
- Stay inside this worktree only.
- If remote push/PR is not available, skip push/PR and still finish with local commit.
- Include at least one downside/risk in your final summary.

When completely finished, run:
openclaw system event --text "Done: codex core TODO implementation finished" --mode now
