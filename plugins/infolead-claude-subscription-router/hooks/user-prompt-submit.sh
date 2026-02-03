#!/bin/bash
# UserPromptSubmit Hook - Router System Integration
#
# Analyzes every user request BEFORE Claude processes it.
# Provides routing recommendation for agent selection.
#
# Trigger: UserPromptSubmit
# Change Driver: ROUTING_LOGIC

set -euo pipefail

# Read user request from stdin
USER_REQUEST=$(cat)

# Determine router directory
# Use plugin root, fall back to global installation
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [ -n "$PLUGIN_ROOT" ] && [ -f "$PLUGIN_ROOT/implementation/routing_core.py" ]; then
    ROUTER_DIR="$PLUGIN_ROOT"
elif [ -f "$HOME/.claude/infolead-router/implementation/routing_core.py" ]; then
    ROUTER_DIR="$HOME/.claude/infolead-router"
else
    # Router system not installed - pass through silently
    exit 0
fi

ROUTING_SCRIPT="$ROUTER_DIR/implementation/routing_core.py"

# Verify routing script exists
if [ ! -f "$ROUTING_SCRIPT" ]; then
    exit 0
fi

# Run routing analysis
# Note: routing_core.py reads from stdin and outputs human-readable routing analysis
python3 "$ROUTING_SCRIPT" <<< "$USER_REQUEST" 2>/dev/null || true

# Exit code 0 allows Claude to proceed with the routing decision
exit 0
