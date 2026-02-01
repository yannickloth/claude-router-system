#!/bin/bash
# Log Subagent Stop Hook
# Logs agent completion with duration and writes metrics for cost analysis
#
# Trigger: SubagentStop (receives JSON on stdin)
# Change Driver: MONITORING_REQUIREMENTS

set -euo pipefail

# Read JSON from stdin
INPUT=$(cat)

# Get cwd from hook input (project directory)
CWD=$(jq -r '.cwd // "."' <<< "$INPUT")
LOGS_DIR="$CWD/.claude/logs"
ROUTING_LOG="$LOGS_DIR/routing.log"

# Global metrics directory
METRICS_DIR="${HOME}/.claude/infolead-router/metrics"
TODAY=$(date +%Y-%m-%d)
METRICS_FILE="$METRICS_DIR/${TODAY}.jsonl"

# Ensure directories exist
mkdir -p "$LOGS_DIR" "$METRICS_DIR"

# Parse JSON
AGENT_TYPE=$(jq -r '.agent_type // "unknown"' <<< "$INPUT")
AGENT_ID=$(jq -r '.agent_id // "no-id"' <<< "$INPUT")
EXIT_STATUS=$(jq -r '.exit_status // "unknown"' <<< "$INPUT")

# Get project name from directory
PROJECT=$(basename "$CWD")

# Calculate duration by finding the matching start entry
TIMESTAMP=$(date -Iseconds)
DURATION_MS=""
DURATION_SEC=""

# Look for the start timestamp in the log
if [[ -f "$ROUTING_LOG" ]]; then
    START_LINE=$(grep "| $AGENT_ID\$" "$ROUTING_LOG" 2>/dev/null | tail -1 || true)
    if [[ -n "$START_LINE" ]]; then
        START_TS=$(echo "$START_LINE" | cut -d'|' -f1 | xargs)
        if [[ -n "$START_TS" ]]; then
            # Calculate duration in seconds using date
            START_EPOCH=$(date -d "$START_TS" +%s 2>/dev/null || echo "")
            END_EPOCH=$(date +%s)
            if [[ -n "$START_EPOCH" ]]; then
                DURATION_SEC=$((END_EPOCH - START_EPOCH))
                DURATION_MS=$((DURATION_SEC * 1000))
            fi
        fi
    fi
fi

# Determine model tier from agent type for cost estimation
# Pricing per million tokens (MTok):
#   Haiku:  ~$0.25/MTok input, ~$1.25/MTok output
#   Sonnet: ~$3/MTok input, ~$15/MTok output
#   Opus:   ~$15/MTok input, ~$75/MTok output
MODEL_TIER="unknown"
case "$AGENT_TYPE" in
    *haiku*|haiku-general|haiku-pre-router)
        MODEL_TIER="haiku"
        ;;
    *opus*|opus-general|router-escalation)
        MODEL_TIER="opus"
        ;;
    *sonnet*|sonnet-general|router|strategy-advisor|*)
        # Default to sonnet for most agents
        MODEL_TIER="sonnet"
        ;;
esac

# Log completion to project-specific log
echo "$TIMESTAMP | $PROJECT | $AGENT_TYPE | $AGENT_ID | STOP | ${DURATION_SEC:-?}s | $EXIT_STATUS" >> "$ROUTING_LOG"

# Write metrics to global JSONL file for aggregation
# Using atomic write pattern: write to temp file, then rename
TEMP_FILE=$(mktemp)
jq -n \
    --arg ts "$TIMESTAMP" \
    --arg project "$PROJECT" \
    --arg agent_type "$AGENT_TYPE" \
    --arg agent_id "$AGENT_ID" \
    --arg model_tier "$MODEL_TIER" \
    --arg exit_status "$EXIT_STATUS" \
    --arg duration_ms "${DURATION_MS:-null}" \
    --arg duration_sec "${DURATION_SEC:-null}" \
    '{
        event: "agent_stop",
        timestamp: $ts,
        project: $project,
        agent_type: $agent_type,
        agent_id: $agent_id,
        model_tier: $model_tier,
        exit_status: $exit_status,
        duration_ms: (if $duration_ms == "null" then null else ($duration_ms | tonumber) end),
        duration_sec: (if $duration_sec == "null" then null else ($duration_sec | tonumber) end)
    }' >> "$TEMP_FILE"

# Append to daily metrics file (atomic append)
cat "$TEMP_FILE" >> "$METRICS_FILE"
rm -f "$TEMP_FILE"

# Output to stderr for real-time visibility
if [[ -n "${DURATION_SEC:-}" ]]; then
    echo "[routing] ← $AGENT_TYPE (${DURATION_SEC}s) [$EXIT_STATUS]" >&2
else
    echo "[routing] ← $AGENT_TYPE [$EXIT_STATUS]" >&2
fi