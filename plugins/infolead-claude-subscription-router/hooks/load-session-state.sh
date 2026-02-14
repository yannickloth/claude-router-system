#!/bin/bash
# Load Session State Hook
# Restores session state at Claude Code startup
#
# Trigger: Session start
# Change Driver: STATE_PERSISTENCE

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

# Check if router is enabled for this project
if ! is_router_enabled; then
    # Router disabled for this project - skip silently
    exit 0
fi

# Use project-specific state directory (hybrid architecture)
STATE_DIR=$(get_project_data_dir "state")
STATE_FILE="$STATE_DIR/session-state.json"
LOCK_FILE="$STATE_FILE.lock"

# Check if session state exists
if [ ! -f "$STATE_FILE" ]; then
    # Initialize empty state with project context
    PROJECT_ROOT=$(detect_project_root || echo "global")
    PROJECT_ID=$(get_project_id)

    # Use flock for atomic initialization
    (
        flock -x 200
        # Double-check after acquiring lock
        if [ ! -f "$STATE_FILE" ]; then
            jq -n \
                --arg status "new" \
                --arg started "$(date -Iseconds)" \
                --arg project_id "$PROJECT_ID" \
                --arg project_root "$PROJECT_ROOT" \
                '{
                    status: $status,
                    started_at: $started,
                    project: {
                        id: $project_id,
                        root: $project_root
                    },
                    work_in_progress: [],
                    pending_decisions: []
                }' > "$STATE_FILE"
        fi
    ) 200>"$LOCK_FILE"
    exit 0
fi

# Check for jq
if [ -f "$COMMON_FUNCTIONS" ]; then
    if ! check_jq "optional"; then
        echo "[state] Session state exists but jq not available" >&2
        exit 0
    fi
else
    if ! command -v jq &> /dev/null; then
        echo "[state] Session state exists but jq not available" >&2
        exit 0
    fi
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

# Update state to active (with locking for concurrent sessions)
(
    if flock -x -w 5 200; then
        # Use XDG_RUNTIME_DIR for temporary files (user-specific, cleaned on logout)
        if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
            TMP_FILE="$XDG_RUNTIME_DIR/claude-router-state-$$"
        else
            # Fallback to ~/.cache/tmp if XDG_RUNTIME_DIR not set
            mkdir -p "$HOME/.cache/tmp"
            TMP_FILE="$HOME/.cache/tmp/claude-router-state-$$"
        fi

        jq --arg started "$(date -Iseconds)" \
           '.status = "active" | .started_at = $started | del(.ended_at)' \
           "$STATE_FILE" > "$TMP_FILE" 2>/dev/null && mv "$TMP_FILE" "$STATE_FILE" || rm -f "$TMP_FILE"
    else
        echo "[state] Warning: Failed to acquire state lock, skipping update" >&2
    fi
) 200>"$LOCK_FILE"

exit 0
