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

echo "[$START_TS] task=$TASK_ID agent=$AGENT model=$MODEL reasoning=$REASONING" | tee -a "$LOG_FILE"

set +e
case "$AGENT" in
  codex)
    codex --model "$MODEL" \
      -c "model_reasoning_effort=$REASONING" \
      --dangerously-bypass-approvals-and-sandbox \
      "$PROMPT_CONTENT" 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
    ;;
  claude)
    claude --model "$MODEL" \
      --dangerously-skip-permissions \
      -p "$PROMPT_CONTENT" 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
    ;;
  *)
    echo "Unsupported agent: $AGENT (expected codex|claude)" | tee -a "$LOG_FILE"
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
