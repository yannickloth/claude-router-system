#!/usr/bin/env bash
#
# pre-tool-use-write-approve.sh
#
# PreToolUse hook that auto-approves Write and Edit tool calls for subagents.
#
# Background agents cannot get interactive permission approval because there
# is no user present to respond to the permission prompt. This hook
# programmatically grants permission for file operations that the agent is
# already authorized to perform via its tools frontmatter.
#
# Trigger: PreToolUse (matcher: Write|Edit)
# Change Driver: PERMISSION_MANAGEMENT
#
# Returns JSON on stdout: {"permissionDecision": "allow"}
# Logs approval to stderr for terminal visibility.
#
# See: docs/BACKGROUND-AGENT-WRITE-PERMISSIONS.md

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
        # Router disabled - pass through without auto-approval
        echo '{"permissionDecision": "ask"}'
        exit 0
    fi
fi

# Read input from stdin (tool name and parameters as JSON)
INPUT=$(cat)

# Extract tool name for logging (optional - graceful if jq unavailable)
TOOL_NAME="unknown"
if command -v jq &> /dev/null; then
    TOOL_NAME=$(jq -r '.tool_name // "unknown"' <<< "$INPUT" 2>/dev/null || echo "unknown")
fi

# Log approval for visibility (consistent with [routing] pattern in other hooks)
echo "[permissions] Auto-approved $TOOL_NAME for subagent" >&2

# Return permission approval (Claude Code PreToolUse protocol)
echo '{"permissionDecision": "allow"}'

exit 0
