#!/bin/bash
# UserPromptSubmit Hook - Router System Integration
#
# This hook integrates the router system with Claude Code by analyzing
# every user request BEFORE Claude processes it.
#
# How it works:
# 1. Claude Code executes this hook before processing user request
# 2. Hook receives user input via stdin
# 3. Calls routing_core.py with user request
# 4. Routing analysis printed to stdout (visible to Claude and user)
# 5. Claude sees the routing recommendation and uses it to select agent
#
# Installation:
# - Project-level: .claude/hooks/UserPromptSubmit.sh
# - Global: ~/.claude/hooks/UserPromptSubmit.sh

set -euo pipefail

# Read user request from stdin
USER_REQUEST=$(cat)

# Determine router directory
# Try project-local first, then fall back to global
if [ -f "$(pwd)/implementation/routing_core.py" ]; then
    ROUTER_DIR="$(pwd)"
elif [ -f "$HOME/.claude/infolead-router/implementation/routing_core.py" ]; then
    ROUTER_DIR="$HOME/.claude/infolead-router"
else
    # Router system not installed
    echo "⚠️  Router system not found"
    echo "Expected locations:"
    echo "  - $(pwd)/implementation/routing_core.py (project)"
    echo "  - $HOME/.claude/infolead-router/implementation/routing_core.py (global)"
    echo ""
    echo "User request: $USER_REQUEST"
    exit 0
fi

ROUTING_SCRIPT="$ROUTER_DIR/implementation/routing_core.py"

# Verify routing script exists
if [ ! -f "$ROUTING_SCRIPT" ]; then
    echo "⚠️  Routing script not found: $ROUTING_SCRIPT"
    echo "User request: $USER_REQUEST"
    exit 0
fi

# Run routing analysis
# Note: routing_core.py reads from stdin and outputs human-readable routing analysis
python3 "$ROUTING_SCRIPT" <<< "$USER_REQUEST"

# Exit code 0 allows Claude to proceed with the routing decision
exit 0