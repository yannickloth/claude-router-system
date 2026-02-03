#!/bin/bash
# Log Subagent Start Hook
# Logs every subagent spawn for routing visibility with atomic writes
#
# Trigger: SubagentStart (receives JSON on stdin)
# Change Driver: MONITORING_REQUIREMENTS
#
# Input JSON fields:
#   - cwd: working directory
#   - agent_type: type of agent being spawned
#   - agent_id: unique identifier for this agent instance
#   - transcript_path: path to transcript file (optional)

set -euo pipefail

# Check for jq dependency
if ! command -v jq &> /dev/null; then
    echo "[routing] ERROR: jq is required but not installed" >&2
    exit 1
fi

# Read JSON from stdin once
INPUT=$(cat)

# Parse all fields upfront
CWD=$(jq -r '.cwd // "."' <<< "$INPUT")
AGENT_TYPE=$(jq -r '.agent_type // "unknown"' <<< "$INPUT")
AGENT_ID=$(jq -r '.agent_id // "no-id"' <<< "$INPUT")

# Setup paths
LOGS_DIR="$CWD/.claude/logs"
ROUTING_LOG="$LOGS_DIR/routing.log"
PROJECT=$(basename "$CWD")
TIMESTAMP=$(date -Iseconds)
SHORT_AGENT_ID="${AGENT_ID:0:8}"

# Ensure logs directory exists (mkdir -p is atomic)
mkdir -p "$LOGS_DIR"

# Note: Description is NOT available at START time (Task call not yet in transcript)
# Description will be logged in STOP hook after task completes

# Log format: TIMESTAMP | PROJECT | AGENT_TYPE | AGENT_ID | START
LOG_ENTRY="$TIMESTAMP | $PROJECT | $AGENT_TYPE | $SHORT_AGENT_ID | START"

# Atomic append using flock for file-level locking
# This prevents interleaved writes from concurrent subagents
(
    flock -x 200
    echo "$LOG_ENTRY" >> "$ROUTING_LOG"
) 200>"$ROUTING_LOG.lock"

# Output to stderr for real-time visibility in terminal
echo "[routing] $PROJECT → $AGENT_TYPE [$SHORT_AGENT_ID]" >&2

exit 0
