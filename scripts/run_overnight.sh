#!/usr/bin/env bash
# Overnight 10hr arena run — launches in tmux if available, otherwise nohup.
#
# Usage:
#   ./scripts/run_overnight.sh          # start the run
#
# If tmux is available:
#   tmux attach -t overnight_arena      # check on it
#   Ctrl-b d                            # detach (run keeps going)
#
# If using nohup fallback:
#   tail -f arena_runs/overnight_*.log  # watch progress
#   kill $(cat arena_runs/overnight.pid) # stop the run
#
# The run stops after 300 games OR when the 10hr timeout expires,
# whichever comes first. Partial results are fully usable — the arena
# writes games.jsonl and snapshots incrementally.

set -euo pipefail
cd "$(dirname "$0")/.."

CONFIG="scripts/arena_config_overnight_10hr.json"
TIMEOUT_HOURS=10
TIMEOUT_SECS=$((TIMEOUT_HOURS * 3600))
SESSION_NAME="overnight_arena"
LOG_FILE="arena_runs/overnight_$(date +%Y%m%d_%H%M%S).log"
PID_FILE="arena_runs/overnight.pid"

# Ensure output directory exists
mkdir -p arena_runs

echo "========================================"
echo "  MCTS Laboratory — Overnight Arena Run"
echo "========================================"
echo "Config:   $CONFIG"
echo "Timeout:  ${TIMEOUT_HOURS}h (${TIMEOUT_SECS}s)"
echo "Log:      $LOG_FILE"

# Use GNU timeout on Linux, gtimeout on macOS (coreutils), or a fallback
find_timeout_cmd() {
    if command -v gtimeout &>/dev/null; then
        echo "gtimeout"
    elif timeout --version &>/dev/null 2>&1; then
        echo "timeout"
    else
        echo ""
    fi
}

TIMEOUT_CMD=$(find_timeout_cmd)

# Build the core arena command
if [ -n "$TIMEOUT_CMD" ]; then
    ARENA_CMD="$TIMEOUT_CMD ${TIMEOUT_SECS} python scripts/arena.py --config ${CONFIG} --verbose"
else
    # No timeout command available — run without timeout, rely on num_games limit
    echo "WARNING: Neither 'timeout' nor 'gtimeout' found. Run will stop at num_games limit only."
    echo "         Install coreutils for timeout support: brew install coreutils"
    ARENA_CMD="python scripts/arena.py --config ${CONFIG} --verbose"
fi

if command -v tmux &>/dev/null; then
    # ---- tmux mode ----
    echo "Mode:     tmux"
    echo ""
    echo "To monitor:  tmux attach -t $SESSION_NAME"
    echo "To stop:     tmux kill-session -t $SESSION_NAME"
    echo "========================================"

    # Kill any existing session with the same name
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

    TMUX_CMD="cd $(pwd) && \
echo '=== Overnight arena started at \$(date) ===' && \
${ARENA_CMD} 2>&1 | tee ${LOG_FILE}; \
EXIT_CODE=\${PIPESTATUS[0]:-\$?}; \
if [ \$EXIT_CODE -eq 124 ]; then \
  echo ''; \
  echo '=== 10hr timeout reached. Run stopped gracefully. ==='; \
  echo '=== Partial results are fully usable. ==='; \
fi; \
echo ''; \
echo '=== Overnight arena finished at \$(date) ==='; \
echo 'Press Enter to close this tmux session.'; \
read"

    tmux new-session -d -s "$SESSION_NAME" "$TMUX_CMD"

    echo ""
    echo "Overnight run launched in tmux session '$SESSION_NAME'."
    echo "Run 'tmux attach -t $SESSION_NAME' to watch progress."
else
    # ---- nohup mode ----
    echo "Mode:     nohup (tmux not found)"
    echo "PID file: $PID_FILE"
    echo ""
    echo "To monitor:  tail -f $LOG_FILE"
    echo "To stop:     kill \$(cat $PID_FILE)"
    echo "========================================"

    echo "=== Overnight arena started at $(date) ===" > "$LOG_FILE"

    nohup bash -c "${ARENA_CMD} 2>&1; \
EXIT_CODE=\$?; \
if [ \$EXIT_CODE -eq 124 ]; then \
  echo ''; \
  echo '=== 10hr timeout reached. Run stopped gracefully. ==='; \
  echo '=== Partial results are fully usable. ==='; \
fi; \
echo ''; \
echo '=== Overnight arena finished at \$(date) ===' ; \
rm -f ${PID_FILE}" >> "$LOG_FILE" 2>&1 &

    NOHUP_PID=$!
    echo "$NOHUP_PID" > "$PID_FILE"

    echo ""
    echo "Overnight run launched in background (PID: $NOHUP_PID)."
    echo "Run 'tail -f $LOG_FILE' to watch progress."
fi
