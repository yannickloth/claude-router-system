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

# Check for jq (already confirmed common-functions.sh exists above)
if ! check_jq "optional"; then
    echo "[state] Cannot save state: jq not available" >&2
    exit 0
fi

# Update session state with completion timestamp (with locking for concurrent sessions)
(
    if flock -x -w 5 200; then
        if [ -f "$STATE_FILE" ]; then
            # Use XDG_RUNTIME_DIR for temporary files (user-specific, cleaned on logout)
            if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
                TMP_FILE="$XDG_RUNTIME_DIR/claude-router-state-$$"
            else
                # Fallback to ~/.cache/tmp if XDG_RUNTIME_DIR not set
                mkdir -p "$HOME/.cache/tmp"
                TMP_FILE="$HOME/.cache/tmp/claude-router-state-$$"
            fi

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

        # Archive session log if it exists (project-specific) - INSIDE flock block
        LOGS_DIR=$(get_project_data_dir "logs")
        ROUTING_LOG="$LOGS_DIR/routing.log"
        ARCHIVE_DIR="$LOGS_DIR/archive"

        if [ -f "$ROUTING_LOG" ] && [ -s "$ROUTING_LOG" ]; then
            mkdir -p "$ARCHIVE_DIR"
            ARCHIVE_NAME="routing-$(date +%Y%m%d-%H%M%S).log"
            cp "$ROUTING_LOG" "$ARCHIVE_DIR/$ARCHIVE_NAME"

            # Keep only last 100 lines in active log
            # Use XDG_RUNTIME_DIR for temporary files
            if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
                LOG_TMP="$XDG_RUNTIME_DIR/claude-router-log-$$"
            else
                mkdir -p "$HOME/.cache/tmp"
                LOG_TMP="$HOME/.cache/tmp/claude-router-log-$$"
            fi
            tail -100 "$ROUTING_LOG" > "$LOG_TMP" && mv "$LOG_TMP" "$ROUTING_LOG"
        fi
    else
        echo "[state] Warning: Failed to acquire state lock, session end not recorded" >&2
    fi
) 200>"$LOCK_FILE"

exit 0
