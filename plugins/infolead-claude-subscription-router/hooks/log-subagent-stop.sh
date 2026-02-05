#!/bin/bash
# Log Subagent Stop Hook
# Logs agent completion with duration, description, and writes metrics for cost analysis
#
# Trigger: SubagentStop (receives JSON on stdin)
# Change Driver: MONITORING_REQUIREMENTS
#
# Input JSON fields:
#   - cwd: working directory
#   - agent_type: type of agent
#   - agent_id: unique identifier for this agent instance
#   - exit_status: how the agent completed
#   - transcript_path: path to transcript file

set -euo pipefail

# Check for jq dependency
if ! command -v jq &> /dev/null; then
    echo "[routing] ERROR: jq is required but not installed" >&2
    exit 1
fi

# Read JSON from stdin once
INPUT=$(cat)

# Parse all fields upfront
CWD=$(jq -r '.cwd // "."' <<< "$INPUT")
AGENT_TYPE=$(jq -r '.agent_type // "unknown"' <<< "$INPUT")
AGENT_ID=$(jq -r '.agent_id // "no-id"' <<< "$INPUT")
EXIT_STATUS=$(jq -r '.exit_status // "unknown"' <<< "$INPUT")
TRANSCRIPT=$(jq -r '.transcript_path // ""' <<< "$INPUT")

# Setup paths
LOGS_DIR="$CWD/.claude/logs"
ROUTING_LOG="$LOGS_DIR/routing.log"
METRICS_DIR="${HOME}/.claude/infolead-claude-subscription-router/metrics"
TODAY=$(date +%Y-%m-%d)
METRICS_FILE="$METRICS_DIR/${TODAY}.jsonl"
PROJECT=$(basename "$CWD")
TIMESTAMP=$(date -Iseconds)
SHORT_AGENT_ID="${AGENT_ID:0:8}"

# Ensure directories exist
mkdir -p "$LOGS_DIR" "$METRICS_DIR"

# Get task description from transcript - available now that task completed
# Transcript format: JSONL with message.content[] containing tool_use entries
DESCRIPTION=""
if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]]; then
    DESCRIPTION=$(timeout 2s jq -rs '
        [.[] | .message?.content? // [] | .[] | select(.type == "tool_use" and .name == "Task") | .input.description // empty]
        | last // ""
    ' "$TRANSCRIPT" 2>/dev/null | head -c 80) || true
fi
[[ -z "$DESCRIPTION" ]] && DESCRIPTION="no description"

# Calculate duration by finding the matching START entry
# Log format: TIMESTAMP | PROJECT | AGENT_TYPE | AGENT_ID | START
DURATION_MS=""
DURATION_SEC=""

if [[ -f "$ROUTING_LOG" ]]; then
    # Use flock to safely read the log file
    START_LINE=$(
        flock -s 200
        grep " | $SHORT_AGENT_ID | START" "$ROUTING_LOG" 2>/dev/null | tail -1 || true
    ) 200>"$ROUTING_LOG.lock"

    if [[ -n "$START_LINE" ]]; then
        # Extract timestamp (first field before |)
        START_TS=$(echo "$START_LINE" | cut -d'|' -f1 | xargs)
        if [[ -n "$START_TS" ]]; then
            # Calculate duration in seconds
            START_EPOCH=$(date -d "$START_TS" +%s 2>/dev/null) || START_EPOCH=""
            END_EPOCH=$(date +%s)
            if [[ -n "$START_EPOCH" ]]; then
                DURATION_SEC=$((END_EPOCH - START_EPOCH))
                DURATION_MS=$((DURATION_SEC * 1000))
            fi
        fi
    fi
fi

# Determine model tier from agent type for cost estimation
# Pricing per million tokens (approximate as of 2025):
#   Haiku:  ~$0.25/MTok input, ~$1.25/MTok output
#   Sonnet: ~$3/MTok input, ~$15/MTok output
#   Opus:   ~$15/MTok input, ~$75/MTok output
determine_model_tier() {
    local agent="$1"
    case "$agent" in
        haiku-general|haiku-pre-router|*-haiku)
            echo "haiku"
            ;;
        opus-general|router-escalation|*-opus)
            echo "opus"
            ;;
        sonnet-general|router|strategy-advisor|*-sonnet)
            echo "sonnet"
            ;;
        # Check for model hints in agent name
        *haiku*)
            echo "haiku"
            ;;
        *opus*)
            echo "opus"
            ;;
        *)
            # Default to sonnet for unknown agents (most common)
            echo "sonnet"
            ;;
    esac
}

MODEL_TIER=$(determine_model_tier "$AGENT_TYPE")

# Log format: TIMESTAMP | PROJECT | AGENT_TYPE | AGENT_ID | STOP | DURATION | DESCRIPTION
LOG_ENTRY="$TIMESTAMP | $PROJECT | $AGENT_TYPE | $SHORT_AGENT_ID | STOP | ${DURATION_SEC:-?}s | $DESCRIPTION"

# Atomic append to project log using flock
(
    flock -x 200
    echo "$LOG_ENTRY" >> "$ROUTING_LOG"
) 200>"$ROUTING_LOG.lock"

# Build metrics JSON (compact format for JSONL - one line per record)
# record_type distinguishes raw events from computed solution metrics
METRICS_JSON=$(jq -c -n \
    --arg record_type "agent_event" \
    --arg event "agent_stop" \
    --arg ts "$TIMESTAMP" \
    --arg project "$PROJECT" \
    --arg agent_type "$AGENT_TYPE" \
    --arg agent_id "$AGENT_ID" \
    --arg model_tier "$MODEL_TIER" \
    --arg exit_status "$EXIT_STATUS" \
    --arg description "$DESCRIPTION" \
    --argjson duration_ms "${DURATION_MS:-null}" \
    --argjson duration_sec "${DURATION_SEC:-null}" \
    '{
        record_type: $record_type,
        event: $event,
        timestamp: $ts,
        project: $project,
        agent_type: $agent_type,
        agent_id: $agent_id,
        model_tier: $model_tier,
        exit_status: $exit_status,
        description: $description,
        duration_ms: $duration_ms,
        duration_sec: $duration_sec
    }')

# Atomic append to global metrics file using flock
(
    flock -x 200
    echo "$METRICS_JSON" >> "$METRICS_FILE"
) 200>"$METRICS_FILE.lock"

# Output to stderr for real-time visibility
if [[ -n "${DURATION_SEC:-}" ]]; then
    echo "[routing] ← $AGENT_TYPE (${DURATION_SEC}s): $DESCRIPTION" >&2
else
    echo "[routing] ← $AGENT_TYPE: $DESCRIPTION" >&2
fi

exit 0
