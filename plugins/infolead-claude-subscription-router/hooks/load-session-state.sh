#!/bin/bash
# Load Session State Hook
# Restores session state at Claude Code startup
#
# Trigger: Session start
# Change Driver: STATE_PERSISTENCE

set -euo pipefail

STATE_DIR="$HOME/.claude/infolead-router/state"
STATE_FILE="$STATE_DIR/session-state.json"

# Ensure state directory exists
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

# Check if session state exists
if [ ! -f "$STATE_FILE" ]; then
    # Initialize empty state
    echo '{"status": "new", "started_at": "'"$(date -Iseconds)"'"}' > "$STATE_FILE"
    exit 0
fi

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "[state] Session state exists but jq not available" >&2
    exit 0
fi

# Check if previous session ended cleanly
PREV_STATUS=$(jq -r '.status // "unknown"' "$STATE_FILE" 2>/dev/null)
PREV_ENDED=$(jq -r '.ended_at // ""' "$STATE_FILE" 2>/dev/null)

if [ "$PREV_STATUS" = "active" ] && [ -z "$PREV_ENDED" ]; then
    echo "[state] Previous session did not end cleanly" >&2
    echo "[state] Recovering state from: $STATE_FILE" >&2
fi

# Load work in progress
WIP_COUNT=$(jq '.work_in_progress | length' "$STATE_FILE" 2>/dev/null || echo "0")
if [ "$WIP_COUNT" -gt 0 ]; then
    echo "[state] Work in progress: $WIP_COUNT items" >&2

    # List WIP items
    jq -r '.work_in_progress[] | "  - \(.description // .id)"' "$STATE_FILE" 2>/dev/null >&2 || true
fi

# Load pending decisions
PENDING=$(jq '.pending_decisions | length' "$STATE_FILE" 2>/dev/null || echo "0")
if [ "$PENDING" -gt 0 ]; then
    echo "[state] Pending decisions: $PENDING" >&2
fi

# Update state to active
TMP_FILE=$(mktemp)
jq --arg started "$(date -Iseconds)" \
   '.status = "active" | .started_at = $started | del(.ended_at)' \
   "$STATE_FILE" > "$TMP_FILE" 2>/dev/null && mv "$TMP_FILE" "$STATE_FILE" || rm -f "$TMP_FILE"

exit 0
