#!/bin/bash
# Save Session State Hook
# Persists session state when session ends
#
# Trigger: Session end
# Change Driver: STATE_PERSISTENCE

set -euo pipefail

# Determine plugin root
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"

# Source common functions for dependency checking
COMMON_FUNCTIONS="$PLUGIN_ROOT/hooks/common-functions.sh"
if [ -f "$COMMON_FUNCTIONS" ]; then
    # shellcheck source=common-functions.sh
    source "$COMMON_FUNCTIONS"
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

# Check for jq
if [ -f "$COMMON_FUNCTIONS" ]; then
    if ! check_jq "optional"; then
        echo "[state] Cannot save state: jq not available" >&2
        exit 0
    fi
else
    if ! command -v jq &> /dev/null; then
        echo "[state] Cannot save state: jq not available" >&2
        exit 0
    fi
fi

# Update session state with completion timestamp (with locking for concurrent sessions)
(
    if flock -x -w 5 200; then
        if [ -f "$STATE_FILE" ]; then
            TMP_FILE=$(mktemp)

            # Add ended_at timestamp and update status
            jq --arg ended "$(date -Iseconds)" \
               '.ended_at = $ended | .status = "completed"' \
               "$STATE_FILE" > "$TMP_FILE" 2>/dev/null

            if [ -s "$TMP_FILE" ]; then
                mv "$TMP_FILE" "$STATE_FILE"
                echo "[state] Session state saved" >&2
            else
                rm -f "$TMP_FILE"
                echo "[state] Failed to update state file" >&2
            fi
        else
            # Create minimal end state with project context
            PROJECT_ROOT=$(detect_project_root || echo "global")
            PROJECT_ID=$(get_project_id)

            jq -n \
                --arg status "completed" \
                --arg ended "$(date -Iseconds)" \
                --arg project_id "$PROJECT_ID" \
                --arg project_root "$PROJECT_ROOT" \
                '{
                    status: $status,
                    ended_at: $ended,
                    project: {
                        id: $project_id,
                        root: $project_root
                    }
                }' > "$STATE_FILE"
            echo "[state] Created end state (no active session)" >&2
        fi
    else
        echo "[state] Warning: Failed to acquire state lock, session end not recorded" >&2
    fi
) 200>"$LOCK_FILE"

# Archive session log if it exists (project-specific)
LOGS_DIR=$(get_project_data_dir "logs")
ROUTING_LOG="$LOGS_DIR/routing.log"
ARCHIVE_DIR="$LOGS_DIR/archive"

if [ -f "$ROUTING_LOG" ] && [ -s "$ROUTING_LOG" ]; then
    mkdir -p "$ARCHIVE_DIR"
    ARCHIVE_NAME="routing-$(date +%Y%m%d-%H%M%S).log"
    cp "$ROUTING_LOG" "$ARCHIVE_DIR/$ARCHIVE_NAME"

    # Keep only last 100 lines in active log
    tail -100 "$ROUTING_LOG" > "$ROUTING_LOG.tmp" && mv "$ROUTING_LOG.tmp" "$ROUTING_LOG"
fi

exit 0
