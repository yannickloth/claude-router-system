#!/bin/bash
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

# Source hook infrastructure
HOOK_DIR="$(dirname "$0")"
if [ -f "$HOOK_DIR/hook-preamble.sh" ]; then
    # shellcheck source=hook-preamble.sh
    source "$HOOK_DIR/hook-preamble.sh"
else
    exit 0
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
