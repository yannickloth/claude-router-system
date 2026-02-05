#!/bin/bash
# Evening Planning Hook
# Displays overnight work queue at 9 PM
# Shows user what will run overnight and estimated completion time
#
# Trigger: Session start (only activates during 9 PM hour)
# Change Driver: TEMPORAL_OPTIMIZATION

set -euo pipefail

# Only run during evening hours (21:00-21:59)
CURRENT_HOUR=$(date +%H)
if [ "$CURRENT_HOUR" -ne 21 ]; then
    exit 0
fi

STATE_DIR="$HOME/.claude/infolead-claude-subscription-router/state"
QUEUE_FILE="$STATE_DIR/temporal-work-queue.json"

# Check if queue file exists
if [ ! -f "$QUEUE_FILE" ]; then
    exit 0
fi

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "[evening] Work queue exists but jq not available to parse" >&2
    exit 0
fi

# Count queued items
QUEUED_COUNT=$(jq '.queued_work | length' "$QUEUE_FILE" 2>/dev/null || echo "0")

if [ "$QUEUED_COUNT" -eq 0 ]; then
    exit 0
fi

# Display overnight work plan
echo "" >&2
echo "[evening] Overnight work scheduled ($QUEUED_COUNT items):" >&2
echo "" >&2

# Show each queued item with details
jq -r '.queued_work[] |
       "  [\(.priority)] \(.description)\n" +
       "      Estimated: \(.estimated_duration_minutes)m, ~\(.estimated_quota) messages\n" +
       "      Scheduled: \(.scheduled_for // "Tonight at 10:00 PM")"' \
    "$QUEUE_FILE" >&2 || true

# Calculate total estimates
TOTAL_DURATION=$(jq '[.queued_work[].estimated_duration_minutes] | add // 0' "$QUEUE_FILE" 2>/dev/null || echo "0")
TOTAL_QUOTA=$(jq '[.queued_work[].estimated_quota] | add // 0' "$QUEUE_FILE" 2>/dev/null || echo "0")

echo "" >&2
echo "  Total estimated: ${TOTAL_DURATION}m, ~${TOTAL_QUOTA} messages" >&2
echo "" >&2

# Check for any dependencies
DEPENDENCIES_EXIST=$(jq -r '.queued_work[] | select(.dependencies | length > 0) | .id' "$QUEUE_FILE" 2>/dev/null || true)

if [ -n "$DEPENDENCIES_EXIST" ]; then
    echo "  Note: Some items have dependencies and will run in sequence" >&2
    echo "" >&2
fi

# Show any recently completed overnight work
COMPLETED_TODAY=$(jq --arg today "$(date +%Y-%m-%d)" \
    '[.completed_overnight // [] | .[] | select(.completed_at | startswith($today))] | length' \
    "$QUEUE_FILE" 2>/dev/null || echo "0")

if [ "$COMPLETED_TODAY" -gt 0 ]; then
    echo "  Completed last night: $COMPLETED_TODAY items" >&2
    echo "    Check: $STATE_DIR/overnight-results/" >&2
    echo "" >&2
fi

# Show any failed work that needs attention
FAILED_COUNT=$(jq '[.failed_work // [] | .[] | select(.retry_count < 3)] | length' "$QUEUE_FILE" 2>/dev/null || echo "0")

if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "  Retrying tonight: $FAILED_COUNT items from previous attempts" >&2
    echo "" >&2
fi

exit 0
