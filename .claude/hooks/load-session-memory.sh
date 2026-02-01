#!/bin/bash
# Load Session Memory Hook
#
# Loads session memory at Claude Code startup to provide continuity.
# Displays last session focus, active agents, and context summary.
#
# This hook integrates with session_state_manager.py to persist state
# across Claude Code restarts.

set -euo pipefail

MEMORY_DIR="$HOME/.claude/infolead-router/memory"
STATE_FILE="$MEMORY_DIR/session-state.json"

# Check if session state exists
if [ ! -f "$STATE_FILE" ]; then
    # No previous session state
    exit 0
fi

echo "📂 Loading session memory..."
echo ""

# Extract and display current focus
if command -v jq &> /dev/null; then
    FOCUS=$(jq -r '.current_focus' "$STATE_FILE" 2>/dev/null || echo "Unknown")
    echo "Last session focus: $FOCUS"

    # Show active agents
    AGENTS=$(jq -r '.active_agents | join(", ")' "$STATE_FILE" 2>/dev/null || echo "None")
    if [ "$AGENTS" != "null" ] && [ "$AGENTS" != "" ]; then
        echo "Active agents: $AGENTS"
    fi

    # Show context summary
    CONTEXT=$(jq -r '.context_summary' "$STATE_FILE" 2>/dev/null || echo "No summary")
    if [ "$CONTEXT" != "null" ] && [ "$CONTEXT" != "" ]; then
        echo "Context: $CONTEXT"
    fi

    # Show last updated time
    UPDATED=$(jq -r '.last_updated' "$STATE_FILE" 2>/dev/null || echo "Unknown")
    if [ "$UPDATED" != "null" ] && [ "$UPDATED" != "" ]; then
        echo "Last updated: $UPDATED"
    fi
else
    # Fallback if jq not available
    echo "Session state exists but jq not available to parse it"
    echo "Install jq for session memory display"
fi

echo ""

exit 0