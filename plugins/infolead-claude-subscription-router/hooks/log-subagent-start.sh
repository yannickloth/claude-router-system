#!/bin/bash
# Log Subagent Start Hook
# Logs every subagent spawn for routing visibility with atomic writes
# IVP Purity: 1.0 (MONITORING only)
#
# Trigger: SubagentStart (receives JSON on stdin)
# Change Driver: MONITORING
#
# Input JSON fields:
#   - cwd: working directory
#   - agent_type: type of agent being spawned
#   - agent_id: unique identifier for this agent instance
#   - transcript_path: path to transcript file (optional)

set -euo pipefail

# Source hook infrastructure
HOOK_DIR="$(dirname "$0")"
if [ -f "$HOOK_DIR/hook-preamble.sh" ]; then
    # shellcheck source=hook-preamble.sh
    source "$HOOK_DIR/hook-preamble.sh"
else
    exit 0
fi

# Check for jq - required for this hook
if ! check_jq "required"; then
    # Warning already shown, exit gracefully
    exit 0
fi

# Read JSON from stdin once
INPUT=$(cat)

# Parse all fields upfront in single jq call (optimization: combine 3 jq processes into 1)
read -r CWD AGENT_TYPE AGENT_ID < <(
    jq -r '[
        .cwd // ".",
        .agent_type // "unknown",
        .agent_id // "no-id"
    ] | @tsv' <<< "$INPUT"
)

# Setup project-specific paths (hybrid architecture)
PROJECT_ROOT=$(detect_project_root || echo "global")
LOGS_DIR=$(get_project_data_dir "logs")
ROUTING_LOG="$LOGS_DIR/routing.log"
PROJECT=$(basename "$PROJECT_ROOT")
TIMESTAMP=$(date -Iseconds)
SHORT_AGENT_ID="${AGENT_ID:0:8}"

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
