#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 6 ]]; then
  echo "Usage: $0 <agent:codex|claude> <model> <reasoning> <prompt_file> <log_file> <task_id>" >&2
  exit 1
fi

AGENT="$1"
MODEL="$2"
REASONING="$3"
PROMPT_FILE="$4"
LOG_FILE="$5"
TASK_ID="$6"

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"
PROMPT_CONTENT="$(cat "$PROMPT_FILE")"
START_TS="$(date '+%Y-%m-%d %H:%M:%S')"

echo "[$START_TS] task=$TASK_ID agent=$AGENT model=$MODEL reasoning=$REASONING" >> "$LOG_FILE"

run_with_tty_log() {
  local -a cmd=("$@")
  if command -v script >/dev/null 2>&1; then
    # macOS style: script -aq <logfile> <command> [args...]
    script -aq "$LOG_FILE" "${cmd[@]}"
    return $?
  fi

  # fallback: no pseudo tty, may fail for interactive CLIs but keeps execution path
  "${cmd[@]}" >> "$LOG_FILE" 2>&1
  return $?
}

set +e
case "$AGENT" in
  codex)
    run_with_tty_log codex exec --model "$MODEL" -c "model_reasoning_effort=$REASONING" --dangerously-bypass-approvals-and-sandbox "$PROMPT_CONTENT"
    EXIT_CODE=$?
    ;;
  claude)
    run_with_tty_log claude --model "$MODEL" --dangerously-skip-permissions -p "$PROMPT_CONTENT"
    EXIT_CODE=$?
    ;;
  *)
    echo "Unsupported agent: $AGENT (expected codex|claude)" >> "$LOG_FILE"
    EXIT_CODE=2
    ;;
esac
set -e

END_TS="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$END_TS] task=$TASK_ID exit_code=$EXIT_CODE" | tee -a "$LOG_FILE"

if command -v openclaw >/dev/null 2>&1; then
  openclaw system event \
    --text "Agent task ${TASK_ID} finished (exit=${EXIT_CODE}). Run check-agents to update registry." \
    --mode now >/dev/null 2>&1 || true
fi

exit "$EXIT_CODE"
