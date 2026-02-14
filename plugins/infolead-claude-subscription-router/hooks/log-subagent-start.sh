#!/bin/bash
# Log Subagent Start Hook
# Logs every subagent spawn for routing visibility with atomic writes
# ENHANCED: Links agent invocation to routing recommendation for compliance tracking
#
# Trigger: SubagentStart (receives JSON on stdin)
# Change Driver: MONITORING_REQUIREMENTS
#
# Input JSON fields:
#   - cwd: working directory
#   - agent_type: type of agent being spawned
#   - agent_id: unique identifier for this agent instance
#   - transcript_path: path to transcript file (optional)

set -euo pipefail

# Determine plugin root
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"

# Source common functions for dependency checking
COMMON_FUNCTIONS="$PLUGIN_ROOT/hooks/common-functions.sh"
if [ -f "$COMMON_FUNCTIONS" ]; then
    # shellcheck source=common-functions.sh
    source "$COMMON_FUNCTIONS"
else
    # Exit gracefully if common-functions.sh missing
    exit 0
fi

# Check for jq - required for this hook
if ! check_jq "required"; then
    # Warning already shown, exit gracefully
    exit 0
fi

# Read JSON from stdin once
INPUT=$(cat)

# Parse all fields upfront
CWD=$(jq -r '.cwd // "."' <<< "$INPUT")
AGENT_TYPE=$(jq -r '.agent_type // "unknown"' <<< "$INPUT")
AGENT_ID=$(jq -r '.agent_id // "no-id"' <<< "$INPUT")

# Check if router is enabled for current project
if ! is_router_enabled; then
    # Router disabled - skip silently
    exit 0
fi

# Setup project-specific paths (hybrid architecture)
PROJECT_ROOT=$(detect_project_root || echo "global")
PROJECT_ID=$(get_project_id)
LOGS_DIR=$(get_project_data_dir "logs")
ROUTING_LOG="$LOGS_DIR/routing.log"
METRICS_DIR=$(get_project_data_dir "metrics")
TODAY=$(date +%Y-%m-%d)
METRICS_FILE="$METRICS_DIR/${TODAY}.jsonl"
PROJECT=$(basename "$PROJECT_ROOT")
TIMESTAMP=$(date -Iseconds)
TIMESTAMP_EPOCH=$(date +%s)
SHORT_AGENT_ID="${AGENT_ID:0:8}"

# Note: Description is NOT available at START time (Task call not yet in transcript)
# Description will be logged in STOP hook after task completes

# Log format: TIMESTAMP | PROJECT | AGENT_TYPE | AGENT_ID | START
LOG_ENTRY="$TIMESTAMP | $PROJECT | $AGENT_TYPE | $SHORT_AGENT_ID | START"

# Atomic append using flock for file-level locking
# This prevents interleaved writes from concurrent subagents
(
    flock -x 200
    echo "$LOG_ENTRY" >> "$ROUTING_LOG"
) 200>"$ROUTING_LOG.lock"

# Output to stderr for real-time visibility in terminal
echo "[routing] $PROJECT → $AGENT_TYPE [$SHORT_AGENT_ID]" >&2

# ============================================================================
# COMPLIANCE TRACKING: Link agent invocation to routing recommendation
# ============================================================================

# Get most recent routing recommendation (within last 60 seconds)
# We look backwards through today's metrics to find the matching recommendation
RECENT_ROUTING=""
if [[ -f "$METRICS_FILE" ]]; then
    # Use flock to safely read the metrics file
    RECENT_ROUTING=$(
        flock -s 200
        # Read last 200 lines (to handle high-frequency requests)
        tail -200 "$METRICS_FILE" 2>/dev/null | \
        # Filter to routing_recommendation records only
        jq -r --arg now "$TIMESTAMP_EPOCH" 'select(.record_type == "routing_recommendation") |
               select((($now | tonumber) - (.timestamp | fromdateiso8601)) < 60) |
               @json' 2>/dev/null | \
        tail -1
    ) 200>"$METRICS_FILE.lock" || true
fi

# If we found a recent routing recommendation, create request_tracking record
if [[ -n "$RECENT_ROUTING" ]]; then
    # Parse routing recommendation fields
    REQUEST_HASH=$(echo "$RECENT_ROUTING" | jq -r '.request_hash // ""')
    ROUTING_DECISION=$(echo "$RECENT_ROUTING" | jq -r '.full_analysis.decision // "unknown"')
    ROUTING_AGENT=$(echo "$RECENT_ROUTING" | jq -r '.recommendation.agent // "null"')
    ROUTING_CONFIDENCE=$(echo "$RECENT_ROUTING" | jq -r '.recommendation.confidence // 0')
    ROUTING_REASON=$(echo "$RECENT_ROUTING" | jq -r '.recommendation.reason // ""')

    # Determine compliance status
    COMPLIANCE="unknown"

    if [[ "$ROUTING_DECISION" == "escalate" ]]; then
        # Router recommended escalation
        if [[ "$ROUTING_AGENT" == "escalate" || "$ROUTING_AGENT" == "null" ]]; then
            # Generic escalation - any agent invocation counts as followed
            COMPLIANCE="followed"
        else
            # Specific agent recommendation
            if [[ "$AGENT_TYPE" == "$ROUTING_AGENT" ]]; then
                COMPLIANCE="followed"
            else
                COMPLIANCE="ignored"
            fi
        fi
    elif [[ "$ROUTING_DECISION" == "direct" ]]; then
        # Router said handle directly - agent invocation means ignored
        COMPLIANCE="ignored"
    fi

    # Build request_tracking JSON record (includes project context)
    TRACKING_JSON=$(jq -c -n \
        --arg record_type "request_tracking" \
        --arg timestamp "$TIMESTAMP" \
        --arg request_hash "$REQUEST_HASH" \
        --arg routing_decision "$ROUTING_DECISION" \
        --arg routing_agent "$ROUTING_AGENT" \
        --argjson routing_confidence "$ROUTING_CONFIDENCE" \
        --arg actual_handler "agent" \
        --arg agent_invoked "$AGENT_TYPE" \
        --arg agent_id "$AGENT_ID" \
        --arg compliance "$COMPLIANCE" \
        --arg project "$PROJECT" \
        --arg project_id "$PROJECT_ID" \
        --arg project_root "$PROJECT_ROOT" \
        --arg routing_reason "$ROUTING_REASON" \
        '{
            record_type: $record_type,
            timestamp: $timestamp,
            request_hash: $request_hash,
            routing_decision: $routing_decision,
            routing_agent: $routing_agent,
            routing_confidence: $routing_confidence,
            actual_handler: $actual_handler,
            agent_invoked: $agent_invoked,
            agent_id: $agent_id,
            compliance_status: $compliance,
            project: {
                name: $project,
                id: $project_id,
                root: $project_root
            },
            metadata: {
                routing_reason: $routing_reason
            }
        }')

    # Atomic append to metrics file
    (
        flock -x 200
        echo "$TRACKING_JSON" >> "$METRICS_FILE"
    ) 200>"$METRICS_FILE.lock"

    # Debug output (only if compliance is ignored - worth noting)
    if [[ "$COMPLIANCE" == "ignored" ]]; then
        echo "[routing] WARNING: Routing directive ignored (recommended: $ROUTING_AGENT, actual: $AGENT_TYPE)" >&2
    fi
fi

exit 0
