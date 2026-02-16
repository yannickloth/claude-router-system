#!/bin/bash
# UserPromptSubmit Hook - Router System Integration
#
# Analyzes every user request BEFORE Claude processes it.
# Provides VISIBLE routing recommendation as advisory input to main Claude.
#
# Trigger: UserPromptSubmit
# Change Driver: ROUTING_LOGIC

set -euo pipefail

# Read user request from stdin
USER_REQUEST=$(cat)

# Source hook infrastructure
HOOK_DIR="$(dirname "$0")"
if [ -f "$HOOK_DIR/hook-preamble.sh" ]; then
    # shellcheck source=hook-preamble.sh
    source "$HOOK_DIR/hook-preamble.sh"
else
    exit 0
fi

# Verify routing script exists
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$HOOK_DIR")}"
if [ ! -f "$PLUGIN_ROOT/implementation/routing_core.py" ]; then
    # Router system not properly installed - pass through silently
    exit 0
fi

ROUTER_DIR="$PLUGIN_ROOT"
ROUTING_SCRIPT="$ROUTER_DIR/implementation/routing_core.py"

# Use project-specific directories (hybrid architecture)
METRICS_DIR=$(get_project_data_dir "metrics")
LOGS_DIR=$(get_project_data_dir "logs")
PROJECT_ROOT=$(detect_project_root || echo "global")
PROJECT_ID=$(get_project_id)

TODAY=$(date +%Y-%m-%d)
TIMESTAMP=$(date -Iseconds)
REQUEST_HASH=$(echo -n "$USER_REQUEST" | sha256sum | cut -d' ' -f1 | head -c16)

# Check all routing dependencies (python3, PyYAML, jq)
# If any are missing, show clear error messages and exit gracefully
if ! check_routing_dependencies; then
    # Dependencies missing - warning already shown, exit gracefully
    exit 0
fi

# Run routing analysis with JSON output
ROUTING_OUTPUT=$(python3 "$ROUTING_SCRIPT" --json <<< "$USER_REQUEST" 2>/dev/null || echo '{"error": "routing_failed"}')

# Check if routing succeeded
if echo "$ROUTING_OUTPUT" | jq -e '.error' >/dev/null 2>&1; then
    # Routing failed - pass through silently
    exit 0
fi

# Extract recommendation fields in single jq call (optimization: combine 3 jq processes into 1)
read -r AGENT REASON CONFIDENCE < <(
    jq -r '[
        .agent // "null",
        .reason // "no reason provided",
        .confidence // 0
    ] | @tsv' <<< "$ROUTING_OUTPUT"
)

# Make display clearer for escalation cases
if [ "$AGENT" = "null" ]; then
    AGENT="escalate"
fi

# Log routing decision to metrics (for tracking recommendations)
# Include project context for multi-project isolation
METRICS_ENTRY=$(jq -c -n \
    --arg record_type "routing_recommendation" \
    --arg timestamp "$TIMESTAMP" \
    --arg request_hash "$REQUEST_HASH" \
    --arg project_id "$PROJECT_ID" \
    --arg project_root "$PROJECT_ROOT" \
    --arg agent "$AGENT" \
    --arg reason "$REASON" \
    --argjson confidence "$CONFIDENCE" \
    --argjson routing_output "$ROUTING_OUTPUT" \
    '{
        record_type: $record_type,
        timestamp: $timestamp,
        request_hash: $request_hash,
        project: {
            id: $project_id,
            root: $project_root
        },
        recommendation: {
            agent: $agent,
            reason: $reason,
            confidence: $confidence
        },
        full_analysis: $routing_output
    }')

# Atomic append to metrics file with timeout
(
    # Try to acquire lock with 5 second timeout
    if flock -x -w 5 200; then
        echo "$METRICS_ENTRY" >> "$METRICS_DIR/${TODAY}.jsonl"
    else
        # Lock timeout - log to stderr but don't fail the hook
        echo "[ROUTER] Warning: Failed to acquire metrics lock, skipping logging" >&2
    fi
) 200>"$METRICS_DIR/${TODAY}.jsonl.lock"

# Output visible routing recommendation to stderr (user sees it)
echo "[ROUTER] Recommendation: $AGENT (confidence: $CONFIDENCE)" >&2
echo "[ROUTER] Reason: $REASON" >&2

# Extract decision from routing output (already have ROUTING_OUTPUT parsed above)
DECISION=$(jq -r '.decision // "unknown"' <<< "$ROUTING_OUTPUT")

# Output routing recommendation to stdout for Claude (advisory input)
# This gets injected into Claude's context as a system message
# Includes UNAMBIGUOUS routing directive with explicit action required
cat <<EOF
<routing-recommendation request-hash="$REQUEST_HASH">
ROUTING DIRECTIVE - MANDATORY ACTION REQUIRED. No interpretation allowed.

Decision: $DECISION
Reason: $REASON
Confidence: $CONFIDENCE

ACTION INSTRUCTIONS:
- You MUST NOT handle this request directly
- You MUST use the Task tool to invoke a router agent
- You MUST NOT ask clarifying questions
- Execute the action specified below with no hesitation:

$ROUTING_OUTPUT

IF decision == "escalate": Invoke infolead-claude-subscription-router:router agent with the user's request
IF decision == "direct": Invoke the specified agent directly (do not escalate further)
</routing-recommendation>
EOF

exit 0
