#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

node <<'NODE'
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('.clawdbot/active-tasks.json', 'utf8'));
const done = (data.tasks || []).filter(t => t.status === 'done');
for (const t of done) {
  console.log(`${t.id}\t${t.worktree || ''}`);
}
NODE
| while IFS=$'\t' read -r ID WORKTREE; do
  if [[ -n "$WORKTREE" && -d "$WORKTREE" ]]; then
    echo "Removing worktree for $ID: $WORKTREE"
    git worktree remove "$WORKTREE" --force || true
  fi

done

git worktree prune
