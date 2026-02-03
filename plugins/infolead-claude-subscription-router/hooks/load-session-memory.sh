#!/bin/bash
# Load Session Memory Hook
#
# Loads session memory at Claude Code startup to provide continuity.
# Displays last session focus, active agents, and context summary.
#
# Trigger: Session start
# Change Driver: STATE_PERSISTENCE

set -euo pipefail

MEMORY_DIR="$HOME/.claude/infolead-router/memory"
STATE_FILE="$MEMORY_DIR/session-state.json"

# Check if session state exists
if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

echo "[session] Loading session memory..." >&2

# Extract and display current focus
if command -v jq &> /dev/null; then
    FOCUS=$(jq -r '.current_focus // "Unknown"' "$STATE_FILE" 2>/dev/null)
    if [ "$FOCUS" != "null" ] && [ -n "$FOCUS" ]; then
        echo "[session] Last focus: $FOCUS" >&2
    fi

    # Show active agents
    AGENTS=$(jq -r '.active_agents // [] | join(", ")' "$STATE_FILE" 2>/dev/null)
    if [ "$AGENTS" != "null" ] && [ -n "$AGENTS" ]; then
        echo "[session] Active agents: $AGENTS" >&2
    fi

    # Show context summary
    CONTEXT=$(jq -r '.context_summary // ""' "$STATE_FILE" 2>/dev/null)
    if [ "$CONTEXT" != "null" ] && [ -n "$CONTEXT" ]; then
        echo "[session] Context: $CONTEXT" >&2
    fi

    # Show last updated time
    UPDATED=$(jq -r '.last_updated // ""' "$STATE_FILE" 2>/dev/null)
    if [ "$UPDATED" != "null" ] && [ -n "$UPDATED" ]; then
        echo "[session] Last updated: $UPDATED" >&2
    fi
else
    echo "[session] Session state exists but jq not available" >&2
fi

exit 0
