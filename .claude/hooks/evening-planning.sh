#!/bin/bash
# Evening Planning Hook
# Displays overnight work queue at 9 PM
# Shows user what will run overnight and estimated completion time

# Only run during evening hours (21:00-21:59)
CURRENT_HOUR=$(date +%H)
if [ "$CURRENT_HOUR" -ne 21 ]; then
    exit 0
fi

STATE_DIR="$HOME/.claude/infolead-router/state"
QUEUE_FILE="$STATE_DIR/temporal-work-queue.json"

# Check if queue file exists
if [ ! -f "$QUEUE_FILE" ]; then
    exit 0
fi

# Count queued items
QUEUED_COUNT=$(jq '.queued_work | length' "$QUEUE_FILE" 2>/dev/null || echo "0")

if [ "$QUEUED_COUNT" -eq 0 ]; then
    exit 0
fi

# Display overnight work plan
echo ""
echo "🌙 Overnight work scheduled ($QUEUED_COUNT items):"
echo ""

# Show each queued item with details
jq -r '.queued_work[] |
       "  [\(.priority)] \(.description)\n" +
       "      Estimated: \(.estimated_duration_minutes)m, ~\(.estimated_quota) messages\n" +
       "      Scheduled: \(.scheduled_for // "Tonight at 10:00 PM")"' \
    "$QUEUE_FILE"

# Calculate total estimates
TOTAL_DURATION=$(jq '[.queued_work[].estimated_duration_minutes] | add' "$QUEUE_FILE")
TOTAL_QUOTA=$(jq '[.queued_work[].estimated_quota] | add' "$QUEUE_FILE")

echo ""
echo "  Total estimated: ${TOTAL_DURATION}m, ~${TOTAL_QUOTA} messages"
echo ""

# Check for any dependencies
DEPENDENCIES_EXIST=$(jq -r '.queued_work[] | select(.dependencies | length > 0) | .id' "$QUEUE_FILE" 2>/dev/null)

if [ -n "$DEPENDENCIES_EXIST" ]; then
    echo "  ℹ Some items have dependencies and will run in sequence"
    echo ""
fi

# Show any recently completed overnight work
COMPLETED_TODAY=$(jq --arg today "$(date +%Y-%m-%d)" \
    '[.completed_overnight[] | select(.completed_at | startswith($today))] | length' \
    "$QUEUE_FILE")

if [ "$COMPLETED_TODAY" -gt 0 ]; then
    echo "  ✓ $COMPLETED_TODAY items completed last night"
    echo "    Check: $STATE_DIR/overnight-results/"
    echo ""
fi

# Show any failed work that needs attention
FAILED_COUNT=$(jq '[.failed_work[] | select(.retry_count < 3)] | length' "$QUEUE_FILE")

if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "  ⚠ $FAILED_COUNT items from previous attempts will retry tonight"
    echo ""
fi

# Helpful tips on first run
FIRST_RUN_MARKER="$STATE_DIR/.evening-hook-shown"
if [ ! -f "$FIRST_RUN_MARKER" ]; then
    echo "  💡 Tip: Work will execute at 10 PM. Results available tomorrow morning."
    echo "  To cancel queued work, edit: $QUEUE_FILE"
    echo ""
    touch "$FIRST_RUN_MARKER"
fi

exit 0
