#!/bin/bash
# Session End Hook
# Captures session state when session ends
#
# Trigger: Session termination
# Change Driver: STATE_PERSISTENCE

MEMORY_DIR="$HOME/.claude/infolead-router/memory"
STATE_FILE="$MEMORY_DIR/session-state.json"

# Ensure memory directory exists
mkdir -p "$MEMORY_DIR"

# Update session state with completion timestamp if it exists
if [ -f "$STATE_FILE" ]; then
    # Use temporary file for atomic update
    TMP_FILE=$(mktemp)

    # Add ended_at timestamp and status
    jq --arg ended "$(date -Iseconds)" \
       '.ended_at = $ended | .status = "completed"' \
       "$STATE_FILE" > "$TMP_FILE"

    # Atomic rename
    mv "$TMP_FILE" "$STATE_FILE"

    echo ""
    echo "💾 Session state saved"
    echo "   Session ended: $(date)"
    echo ""
else
    echo "ℹ️  No active session state to save"
fi
