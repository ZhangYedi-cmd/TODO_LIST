#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  .clawdbot/scripts/spawn-agent.sh \
    --id <task-id> \
    --description <text> \
    --prompt-file <path> \
    [--agent codex|claude] \
    [--model <model>] \
    [--reasoning low|medium|high] \
    [--base-branch main] \
    [--branch feat/<task-id>] \
    [--max-retries 3] \
    [--no-install]
EOF
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$REPO_ROOT" ]]; then
  echo "Not inside a git repository. Run: git init" >&2
  exit 1
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required. Install with: brew install tmux" >&2
  exit 1
fi

TASK_ID=""
DESCRIPTION=""
PROMPT_FILE=""
AGENT="codex"
MODEL="gpt-5.3-codex"
REASONING="high"
BASE_BRANCH="main"
BRANCH=""
MAX_RETRIES="3"
INSTALL_DEPS="1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --id) TASK_ID="$2"; shift 2 ;;
    --description) DESCRIPTION="$2"; shift 2 ;;
    --prompt-file) PROMPT_FILE="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --reasoning) REASONING="$2"; shift 2 ;;
    --base-branch) BASE_BRANCH="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --max-retries) MAX_RETRIES="$2"; shift 2 ;;
    --no-install) INSTALL_DEPS="0"; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$TASK_ID" || -z "$DESCRIPTION" || -z "$PROMPT_FILE" ]]; then
  echo "--id, --description, --prompt-file are required" >&2
  usage
  exit 1
fi

if [[ ! "$AGENT" =~ ^(codex|claude)$ ]]; then
  echo "--agent must be codex or claude" >&2
  exit 1
fi

TASK_SLUG="$(echo "$TASK_ID" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9_-' '-')"
if [[ -z "$TASK_SLUG" ]]; then
  echo "Invalid --id value: $TASK_ID" >&2
  exit 1
fi

if [[ -z "$BRANCH" ]]; then
  BRANCH="feat/${TASK_SLUG}"
fi

if [[ "$PROMPT_FILE" = /* ]]; then
  PROMPT_ABS="$PROMPT_FILE"
else
  PROMPT_ABS="$REPO_ROOT/$PROMPT_FILE"
fi

if [[ ! -f "$PROMPT_ABS" ]]; then
  echo "Prompt file not found: $PROMPT_ABS" >&2
  exit 1
fi

WORKTREE_ROOT="$REPO_ROOT/.clawdbot/worktrees"
WORKTREE_PATH="$WORKTREE_ROOT/$TASK_SLUG"
SESSION_NAME="agent-$TASK_SLUG"
LOG_FILE="$REPO_ROOT/.clawdbot/logs/${TASK_SLUG}.log"
REGISTRY="$REPO_ROOT/.clawdbot/active-tasks.json"

mkdir -p "$WORKTREE_ROOT" "$REPO_ROOT/.clawdbot/logs"

if [[ -d "$WORKTREE_PATH" ]]; then
  echo "Worktree already exists: $WORKTREE_PATH" >&2
  exit 1
fi

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "tmux session already exists: $SESSION_NAME" >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "Branch already exists locally: $BRANCH" >&2
  exit 1
fi

git fetch origin "$BASE_BRANCH" >/dev/null 2>&1 || true
if git rev-parse --verify "origin/$BASE_BRANCH" >/dev/null 2>&1; then
  BASE_REF="origin/$BASE_BRANCH"
else
  BASE_REF="$BASE_BRANCH"
fi

echo "Creating worktree: $WORKTREE_PATH (branch $BRANCH from $BASE_REF)"
git worktree add "$WORKTREE_PATH" -b "$BRANCH" "$BASE_REF"

if [[ "$INSTALL_DEPS" == "1" ]]; then
  echo "Installing dependencies in worktree..."
  (
    cd "$WORKTREE_PATH"
    if command -v pnpm >/dev/null 2>&1; then
      pnpm install
    else
      npm install
    fi
  )
fi

CMD="$REPO_ROOT/.clawdbot/scripts/run-agent.sh '$AGENT' '$MODEL' '$REASONING' '$PROMPT_ABS' '$LOG_FILE' '$TASK_SLUG'"
echo "Launching tmux session: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME" -c "$WORKTREE_PATH" "$CMD"

export REGISTRY TASK_SLUG DESCRIPTION SESSION_NAME AGENT MODEL REASONING WORKTREE_PATH BRANCH MAX_RETRIES PROMPT_ABS
node <<'NODE'
const fs = require('fs');
const path = process.env.REGISTRY;
const now = Date.now();
let data = { version: 1, updatedAt: null, tasks: [] };
if (fs.existsSync(path)) {
  try { data = JSON.parse(fs.readFileSync(path, 'utf8')); } catch {}
}
if (!Array.isArray(data.tasks)) data.tasks = [];
const idx = data.tasks.findIndex(t => t.id === process.env.TASK_SLUG);
const task = {
  id: process.env.TASK_SLUG,
  description: process.env.DESCRIPTION,
  tmuxSession: process.env.SESSION_NAME,
  agent: process.env.AGENT,
  model: process.env.MODEL,
  reasoning: process.env.REASONING,
  worktree: process.env.WORKTREE_PATH,
  branch: process.env.BRANCH,
  promptFile: process.env.PROMPT_ABS,
  retries: 0,
  maxRetries: Number(process.env.MAX_RETRIES || 3),
  status: 'running',
  notifyOnComplete: true,
  startedAt: now,
  updatedAt: now,
  note: 'Spawned by spawn-agent.sh'
};
if (idx >= 0) data.tasks[idx] = { ...data.tasks[idx], ...task };
else data.tasks.push(task);
data.updatedAt = now;
fs.writeFileSync(path, JSON.stringify(data, null, 2));
NODE

echo "Task registered in .clawdbot/active-tasks.json"
echo "- task id:     $TASK_SLUG"
echo "- tmux session:$SESSION_NAME"
echo "- worktree:    $WORKTREE_PATH"
echo "- log file:    $LOG_FILE"
echo "- follow logs: tmux attach -t $SESSION_NAME"
