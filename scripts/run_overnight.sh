#!/usr/bin/env bash
# Overnight 10hr arena run — launches in a tmux session for resilience.
#
# Usage:
#   ./scripts/run_overnight.sh          # start the run
#   tmux attach -t overnight_arena      # check on it
#   Ctrl-b d                            # detach (run keeps going)
#
# The run will stop after 500 games OR when the 10hr timeout expires,
# whichever comes first. Partial results are fully usable — the arena
# writes games.jsonl and snapshots incrementally.

set -euo pipefail
cd "$(dirname "$0")/.."

CONFIG="scripts/arena_config_overnight_10hr.json"
TIMEOUT_HOURS=10
TIMEOUT_SECS=$((TIMEOUT_HOURS * 3600))
SESSION_NAME="overnight_arena"
LOG_FILE="arena_runs/overnight_$(date +%Y%m%d_%H%M%S).log"

# Ensure output directory exists
mkdir -p arena_runs

# Kill any existing session with the same name
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

echo "========================================"
echo "  MCTS Laboratory — Overnight Arena Run"
echo "========================================"
echo "Config:   $CONFIG"
echo "Timeout:  ${TIMEOUT_HOURS}h (${TIMEOUT_SECS}s)"
echo "Log:      $LOG_FILE"
echo "tmux:     $SESSION_NAME"
echo ""
echo "To monitor:  tmux attach -t $SESSION_NAME"
echo "To stop:     tmux kill-session -t $SESSION_NAME"
echo "========================================"

# Build the command that runs inside tmux.
# - timeout ensures we don't exceed 10 hours
# - nohup + output redirect ensures nothing is lost
# - tee writes to both terminal and log file
ARENA_CMD="cd $(pwd) && \
echo '=== Overnight arena started at \$(date) ===' && \
timeout ${TIMEOUT_SECS} python scripts/arena.py \
  --config ${CONFIG} \
  --verbose \
  2>&1 | tee ${LOG_FILE}; \
EXIT_CODE=\$?; \
if [ \$EXIT_CODE -eq 124 ]; then \
  echo ''; \
  echo '=== 10hr timeout reached. Run stopped gracefully. ==='; \
  echo '=== Partial results are fully usable. ==='; \
fi; \
echo ''; \
echo '=== Overnight arena finished at \$(date) ==='; \
echo 'Press Enter to close this tmux session.'; \
read"

# Launch in a detached tmux session
tmux new-session -d -s "$SESSION_NAME" "$ARENA_CMD"

echo ""
echo "Overnight run launched in tmux session '$SESSION_NAME'."
echo "Run 'tmux attach -t $SESSION_NAME' to watch progress."
