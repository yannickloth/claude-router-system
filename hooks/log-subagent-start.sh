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

# Read JSON from stdin once
INPUT=$(cat)

# Parse all fields upfront
CWD=$(jq -r '.cwd // "."' <<< "$INPUT")
AGENT_TYPE=$(jq -r '.agent_type // "unknown"' <<< "$INPUT")
AGENT_ID=$(jq -r '.agent_id // "no-id"' <<< "$INPUT")
TRANSCRIPT=$(jq -r '.transcript_path // ""' <<< "$INPUT")

# Setup paths
LOGS_DIR="$CWD/.claude/logs"
ROUTING_LOG="$LOGS_DIR/routing.log"
PROJECT=$(basename "$CWD")
TIMESTAMP=$(date -Iseconds)

# Ensure logs directory exists (mkdir -p is atomic)
mkdir -p "$LOGS_DIR"

# Try to get task description from transcript
# Use timeout to prevent hanging on large transcripts
DESCRIPTION=""
if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]]; then
    # Read transcript with timeout, extract last Task description
    DESCRIPTION=$(timeout 2s jq -r '
        [.[] | select(.type == "tool_use" and .name == "Task") | .input.description // empty]
        | last // ""
    ' "$TRANSCRIPT" 2>/dev/null | head -c 80) || true
fi
[[ -z "$DESCRIPTION" ]] && DESCRIPTION="no description"

# Log format: TIMESTAMP | PROJECT | AGENT_TYPE | AGENT_ID | START | DESCRIPTION
# Including AGENT_ID allows stop hook to calculate duration
LOG_ENTRY="$TIMESTAMP | $PROJECT | $AGENT_TYPE | $AGENT_ID | START | $DESCRIPTION"

# Atomic append using flock for file-level locking
# This prevents interleaved writes from concurrent subagents
(
    flock -x 200
    echo "$LOG_ENTRY" >> "$ROUTING_LOG"
) 200>"$ROUTING_LOG.lock"

# Output to stderr for real-time visibility in terminal
echo "[routing] $PROJECT → $AGENT_TYPE: $DESCRIPTION" >&2

exit 0
