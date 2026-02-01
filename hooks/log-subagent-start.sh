#!/bin/bash
# Log Subagent Start Hook
# Logs every subagent spawn for routing visibility
#
# Trigger: SubagentStart (receives JSON on stdin)
# Change Driver: MONITORING_REQUIREMENTS

# Read JSON from stdin
INPUT=$(cat)

# Get cwd from hook input (project directory)
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
LOGS_DIR="$CWD/.claude/logs"
ROUTING_LOG="$LOGS_DIR/routing.log"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Parse JSON
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // "unknown"')
AGENT_ID=$(echo "$INPUT" | jq -r '.agent_id // "no-id"')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // ""')

# Get project name from directory
PROJECT=$(basename "$CWD")

# Try to get task description from transcript (last Task tool call)
DESCRIPTION=""
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
    # Get the description from the most recent Task tool invocation
    DESCRIPTION=$(jq -r '[.[] | select(.type == "tool_use" and .name == "Task") | .input.description // empty] | last // ""' "$TRANSCRIPT" 2>/dev/null | head -c 80)
fi
[ -z "$DESCRIPTION" ] && DESCRIPTION="no description"

# Log the routing decision
TIMESTAMP=$(date -Iseconds)
echo "$TIMESTAMP | $PROJECT | $AGENT_TYPE | $DESCRIPTION" >> "$ROUTING_LOG"

# Also output to stderr for real-time visibility in terminal
echo "[routing] $PROJECT → $AGENT_TYPE: $DESCRIPTION" >&2