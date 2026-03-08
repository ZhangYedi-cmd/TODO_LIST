You are Claude Code, responsible for UX polish + integration hardening for this TODO LIST app.

Context:
- Read docs/TODOLIST-FEATURES.md first.
- Another agent implemented core functionality before you.

Goal:
Polish UX and close product quality gaps without overengineering.

Must implement:
1) UX polish
- Improve visual hierarchy and readability
- Add clear priority badges and due-date urgency indicators
- Improve empty states and action affordances

2) Interaction polish
- Fast task creation flow (keyboard-friendly)
- Better edit/delete confirmation interactions
- Keep status transition actions obvious

3) Reliability hardening
- Ensure localStorage load/save error safety
- Defensive handling for malformed stored data

4) Documentation
- Update README with:
  - feature list
  - local run steps
  - how persistence works
  - known limitations

5) Validation
- npm run lint
- npm run build
- ensure existing tests remain green

Deliverables:
- Single cohesive local commit
- Final summary with changed files + at least one downside/risk

Constraints:
- Stay inside this worktree only.
- If no remote configured, skip push/PR gracefully.
- Avoid adding heavy dependencies unless necessary.

When completely finished, run:
openclaw system event --text "Done: claude UX TODO polish finished" --mode now
