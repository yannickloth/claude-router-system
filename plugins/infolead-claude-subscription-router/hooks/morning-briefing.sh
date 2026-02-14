#!/bin/bash
#
# morning-briefing.sh
#
# SessionStart hook to display overnight execution results
#
# Trigger: SessionStart
# Change Driver: USER_FEEDBACK
# Changes when: Morning briefing format or display logic changes

set -euo pipefail

# Determine plugin root
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"

# Source common functions for dependency checking
COMMON_FUNCTIONS="$PLUGIN_ROOT/hooks/common-functions.sh"
if [ -f "$COMMON_FUNCTIONS" ]; then
    # shellcheck source=common-functions.sh
    source "$COMMON_FUNCTIONS"

    # Check if router is enabled for this project
    if ! is_router_enabled; then
        # Router disabled for this project - skip silently
        exit 0
    fi

    # Check for jq - required for this hook
    if ! check_jq "required"; then
        # Warning already shown, exit gracefully
        exit 0
    fi
else
    # Fallback check without common functions
    if ! command -v jq &> /dev/null; then
        exit 0
    fi
    # Exit gracefully if common-functions.sh missing
    exit 0
fi

# Use project-specific state directory (hybrid architecture)
STATE_DIR=$(get_project_data_dir "state")
RESULTS_DIR="$STATE_DIR/overnight-results"
QUEUE_FILE="$STATE_DIR/temporal-work-queue.json"

# Only show briefing during morning hours (6 AM - 11 AM)
HOUR=$(date +%H)
if [ "$HOUR" -lt 6 ] || [ "$HOUR" -gt 11 ]; then
    exit 0
fi

# Check if queue file exists
if [ ! -f "$QUEUE_FILE" ]; then
    exit 0
fi

# Check for completed overnight work
COMPLETED_COUNT=$(jq '[.completed_overnight // empty] | length' "$QUEUE_FILE" 2>/dev/null || echo "0")
FAILED_COUNT=$(jq '[.failed_overnight // empty] | length' "$QUEUE_FILE" 2>/dev/null || echo "0")

# If no overnight work completed or failed, exit
if [ "$COMPLETED_COUNT" = "0" ] && [ "$FAILED_COUNT" = "0" ]; then
    exit 0
fi

# Display morning briefing
cat <<EOF

═══════════════════════════════════════════════════════════
🌅 Morning Briefing - Overnight Work Results
═══════════════════════════════════════════════════════════

Date: $(date '+%Y-%m-%d %A')

EOF

# Show completed work
if [ "$COMPLETED_COUNT" -gt 0 ]; then
    echo "✅ Completed overnight: $COMPLETED_COUNT items"
    echo ""

    jq -r '
        .completed_overnight[]? //empty |
        "  ✓ [\(.id)] \(.description)"
        + "\n    Project: \(.project_name // "unknown")"
        + "\n    Result: " + (.result[:100] // "No result")
        + (if (.result | length) > 100 then "..." else "" end)
        + "\n"
    ' "$QUEUE_FILE" 2>/dev/null || true
fi

# Show failed work
if [ "$FAILED_COUNT" -gt 0 ]; then
    echo ""
    echo "❌ Failed overnight: $FAILED_COUNT items"
    echo ""

    jq -r '
        .failed_overnight[]? //empty |
        "  ✗ [\(.id)] \(.description)"
        + "\n    Project: \(.project_name // "unknown")"
        + "\n    Error: " + (.error // "Unknown error")
        + "\n"
    ' "$QUEUE_FILE" 2>/dev/null || true
fi

# Show where to find full results
if [ -d "$RESULTS_DIR" ]; then
    LATEST_RESULT=$(ls -t "$RESULTS_DIR"/results-*.json 2>/dev/null | head -1 || echo "")
    if [ -n "$LATEST_RESULT" ]; then
        echo ""
        echo "Full results: $LATEST_RESULT"
    fi
fi

cat <<EOF

Type '/quota' to see current quota usage

═══════════════════════════════════════════════════════════

EOF

exit 0
