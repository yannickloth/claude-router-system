#!/usr/bin/env bash
#
# overnight-executor.sh
#
# Executes scheduled overnight work from temporal-work-queue.json
# Invoked by systemd timer at 22:00 (10 PM) nightly
#
# Change Driver: OVERNIGHT_EXECUTION
# Changes when: Execution workflow or environment setup changes

set -euo pipefail

# Configuration
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
IMPL_DIR="$PLUGIN_ROOT/implementation"
STATE_DIR="$HOME/.claude/infolead-claude-subscription-router/state"
RESULTS_DIR="$STATE_DIR/overnight-results"
LOGS_DIR="$HOME/.claude/infolead-claude-subscription-router/logs"
QUEUE_FILE="$STATE_DIR/temporal-work-queue.json"

# Ensure directories exist
mkdir -p "$RESULTS_DIR" "$LOGS_DIR"
chmod 700 "$RESULTS_DIR" "$STATE_DIR"

# Logging
TIMESTAMP=$(date -Iseconds)
LOG_FILE="$LOGS_DIR/overnight-executor.log"

log() {
    echo "[$TIMESTAMP] $*" | tee -a "$LOG_FILE"
}

log "=== Overnight Executor Started ==="
log "Plugin root: $PLUGIN_ROOT"
log "Implementation directory: $IMPL_DIR"
log "State directory: $STATE_DIR"
log "Queue file: $QUEUE_FILE"

# Check if queue file exists
if [ ! -f "$QUEUE_FILE" ]; then
    log "No work queue found at $QUEUE_FILE. Exiting."
    exit 0
fi

# Check Python availability
if ! command -v python3 &> /dev/null; then
    log "ERROR: python3 not found in PATH"
    exit 1
fi

# Check if overnight runner exists
RUNNER_SCRIPT="$IMPL_DIR/overnight_execution_runner.py"
if [ ! -f "$RUNNER_SCRIPT" ]; then
    log "ERROR: Overnight runner not found at $RUNNER_SCRIPT"
    exit 1
fi

# Load scheduled work count using jq (if available)
if command -v jq &> /dev/null; then
    WORK_COUNT=$(jq '.scheduled_async | length' "$QUEUE_FILE" 2>/dev/null || echo "unknown")
    log "Found $WORK_COUNT items scheduled for tonight"

    if [ "$WORK_COUNT" = "0" ]; then
        log "No work to execute. Exiting."
        exit 0
    fi
else
    log "Warning: jq not found, unable to check work count"
fi

# Execute work using Python overnight executor
log "Starting overnight execution..."
log "Command: python3 $RUNNER_SCRIPT --queue-file $QUEUE_FILE --results-dir $RESULTS_DIR --log-file $LOG_FILE"

python3 "$RUNNER_SCRIPT" \
    --queue-file "$QUEUE_FILE" \
    --results-dir "$RESULTS_DIR" \
    --log-file "$LOG_FILE" \
    --max-concurrent 3 \
    --timeout 10800  # 3 hours

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log "=== Overnight Executor Completed Successfully ==="
elif [ $EXIT_CODE -eq 2 ]; then
    log "=== Overnight Executor Completed with Partial Failures ==="
else
    log "=== Overnight Executor Failed (exit code: $EXIT_CODE) ==="
fi

# Print summary (last 20 lines of log)
log ""
log "Recent log output:"
tail -20 "$LOG_FILE"

exit $EXIT_CODE
