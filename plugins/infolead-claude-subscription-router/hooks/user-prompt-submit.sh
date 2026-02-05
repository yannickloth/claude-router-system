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

# Determine router directory
# Use plugin root if set, otherwise derive from script location
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"

# Verify routing script exists
if [ ! -f "$PLUGIN_ROOT/implementation/routing_core.py" ]; then
    # Router system not properly installed - pass through silently
    exit 0
fi

ROUTER_DIR="$PLUGIN_ROOT"

ROUTING_SCRIPT="$ROUTER_DIR/implementation/routing_core.py"
METRICS_DIR="${HOME}/.claude/infolead-claude-subscription-router/metrics"
LOGS_DIR="${HOME}/.claude/infolead-claude-subscription-router/logs"
TODAY=$(date +%Y-%m-%d)
TIMESTAMP=$(date -Iseconds)
REQUEST_HASH=$(echo -n "$USER_REQUEST" | sha256sum | cut -d' ' -f1 | head -c16)

# Ensure directories exist
mkdir -p "$METRICS_DIR" "$LOGS_DIR"

# Verify routing script exists
if [ ! -f "$ROUTING_SCRIPT" ]; then
    exit 0
fi

# Check for python3 availability
if ! command -v python3 &> /dev/null; then
    # Python3 not available - pass through silently
    exit 0
fi

# Run routing analysis with JSON output
ROUTING_OUTPUT=$(python3 "$ROUTING_SCRIPT" --json <<< "$USER_REQUEST" 2>/dev/null || echo '{"error": "routing_failed"}')

# Check if routing succeeded
if echo "$ROUTING_OUTPUT" | jq -e '.error' >/dev/null 2>&1; then
    # Routing failed - pass through silently
    exit 0
fi

# Extract recommendation for display
AGENT=$(echo "$ROUTING_OUTPUT" | jq -r '.agent // "null"')
REASON=$(echo "$ROUTING_OUTPUT" | jq -r '.reason // "no reason provided"')
CONFIDENCE=$(echo "$ROUTING_OUTPUT" | jq -r '.confidence // 0')

# Make display clearer for escalation cases
if [ "$AGENT" = "null" ]; then
    AGENT="escalate"
fi

# Log routing decision to metrics (for tracking recommendations)
METRICS_ENTRY=$(jq -c -n \
    --arg record_type "routing_recommendation" \
    --arg timestamp "$TIMESTAMP" \
    --arg request_hash "$REQUEST_HASH" \
    --arg agent "$AGENT" \
    --arg reason "$REASON" \
    --argjson confidence "$CONFIDENCE" \
    --argjson routing_output "$ROUTING_OUTPUT" \
    '{
        record_type: $record_type,
        timestamp: $timestamp,
        request_hash: $request_hash,
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

# Output routing recommendation to stdout for Claude (advisory input)
# This gets injected into Claude's context as a system message
cat <<EOF
<routing-recommendation request-hash="$REQUEST_HASH">
$ROUTING_OUTPUT
</routing-recommendation>
EOF

exit 0
