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

# Get project name from directory
PROJECT=$(basename "$CWD")

# Log the routing decision
TIMESTAMP=$(date -Iseconds)
echo "$TIMESTAMP | $PROJECT | $AGENT_TYPE | $AGENT_ID" >> "$ROUTING_LOG"

# Also output to stderr for real-time visibility in terminal
echo "[routing] → $AGENT_TYPE" >&2