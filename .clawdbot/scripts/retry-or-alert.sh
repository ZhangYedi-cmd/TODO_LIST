#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required. Install with: brew install tmux" >&2
  exit 1
fi

node .clawdbot/scripts/check-agents.mjs >/dev/null

mapfile -t RETRY_TASKS < <(node <<'NODE'
const fs = require('fs');
const p = '.clawdbot/active-tasks.json';
const data = JSON.parse(fs.readFileSync(p, 'utf8'));
for (const t of data.tasks || []) {
  if (t.status === 'failed' && Number(t.retries || 0) < Number(t.maxRetries || 3)) {
    console.log([t.id, t.tmuxSession, t.worktree, t.agent, t.model, t.reasoning, t.promptFile, t.retries, t.maxRetries].join('\t'));
  }
}
NODE
)

if [[ ${#RETRY_TASKS[@]} -eq 0 ]]; then
  echo "No failed tasks eligible for retry."
  exit 0
fi

for row in "${RETRY_TASKS[@]}"; do
  IFS=$'\t' read -r ID SESSION WORKTREE AGENT MODEL REASONING PROMPT RETRIES MAX_RETRIES <<< "$row"

  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[$ID] skip: session already alive ($SESSION)"
    continue
  fi

  if [[ ! -d "$WORKTREE" || ! -f "$PROMPT" ]]; then
    echo "[$ID] skip: missing worktree or prompt"
    continue
  fi

  LOG_FILE="$REPO_ROOT/.clawdbot/logs/${ID}.log"
  CMD="$REPO_ROOT/.clawdbot/scripts/run-agent.sh '$AGENT' '$MODEL' '$REASONING' '$PROMPT' '$LOG_FILE' '$ID'"

  echo "[$ID] retrying ($((RETRIES + 1))/$MAX_RETRIES)..."
  tmux new-session -d -s "$SESSION" -c "$WORKTREE" "$CMD"

  export ID
  node <<'NODE'
const fs = require('fs');
const p = '.clawdbot/active-tasks.json';
const data = JSON.parse(fs.readFileSync(p, 'utf8'));
const now = Date.now();
for (const t of data.tasks || []) {
  if (t.id === process.env.ID) {
    t.retries = Number(t.retries || 0) + 1;
    t.status = 'retrying';
    t.updatedAt = now;
    t.note = `Retry spawned (${t.retries}/${t.maxRetries || 3})`;
  }
}
data.updatedAt = now;
fs.writeFileSync(p, JSON.stringify(data, null, 2));
NODE

done

node .clawdbot/scripts/check-agents.mjs
