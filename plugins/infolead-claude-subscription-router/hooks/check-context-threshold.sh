#!/bin/bash
# UserPromptSubmit Hook - Context Threshold Monitoring
#
# Monitors context usage and warns when approaching 100K token limit.
# Triggers at 70% capacity (70,000 tokens) to give user time to wrap up.
#
# Trigger: UserPromptSubmit
# Change Driver: CONTEXT_MANAGEMENT
# Changes when: Threshold logic, warning message format, or estimation method changes

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

# Use project-specific state directory
STATE_DIR=$(get_project_data_dir "state")
STATE_FILE="$STATE_DIR/session-state.json"
SESSION_FLAGS_FILE="$STATE_DIR/session-flags.json"

# Context threshold configuration
CONTEXT_LIMIT=100000
THRESHOLD_PERCENT=70
THRESHOLD_TOKENS=$((CONTEXT_LIMIT * THRESHOLD_PERCENT / 100))

# Check if we've already warned this session
if [ -f "$SESSION_FLAGS_FILE" ]; then
    ALREADY_WARNED=$(jq -r '.context_threshold_warned // false' "$SESSION_FLAGS_FILE" 2>/dev/null || echo "false")
    if [ "$ALREADY_WARNED" = "true" ]; then
        # Already warned, skip
        exit 0
    fi
fi

# Estimate current context usage via transcript analysis
# Method: Count turns in conversation and estimate average tokens per turn
# This is approximate but sufficient for threshold warning

# Get session transcript directory (Claude Code stores in ~/.cache/claude/transcripts/)
TRANSCRIPT_DIR="$HOME/.cache/claude/transcripts"
if [ ! -d "$TRANSCRIPT_DIR" ]; then
    # No transcripts found - probably early in session
    exit 0
fi

# Find most recent transcript file (active session)
LATEST_TRANSCRIPT=$(find "$TRANSCRIPT_DIR" -name "*.jsonl" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

if [ -z "$LATEST_TRANSCRIPT" ] || [ ! -f "$LATEST_TRANSCRIPT" ]; then
    # No active transcript found
    exit 0
fi

# Count conversation turns (approximate context usage)
# Each turn typically includes: user message + assistant response + tool calls + system messages
# Conservative estimate: 1000 tokens per turn average (includes code, responses, tool outputs)
TURN_COUNT=$(wc -l < "$LATEST_TRANSCRIPT" 2>/dev/null || echo "0")

# Estimate tokens (conservative)
ESTIMATED_TOKENS=$((TURN_COUNT * 1000))

# Check if we've crossed the threshold
if [ "$ESTIMATED_TOKENS" -ge "$THRESHOLD_TOKENS" ]; then
    # Mark as warned for this session
    if [ -f "$SESSION_FLAGS_FILE" ]; then
        # Update existing flags
        TMP_FILE="$SESSION_FLAGS_FILE.tmp.$$"
        jq '.context_threshold_warned = true | .context_warned_at = $now' \
           --arg now "$(date -Iseconds)" \
           "$SESSION_FLAGS_FILE" > "$TMP_FILE" 2>/dev/null && mv "$TMP_FILE" "$SESSION_FLAGS_FILE" || rm -f "$TMP_FILE"
    else
        # Create new flags file
        jq -n \
            --arg now "$(date -Iseconds)" \
            '{
                context_threshold_warned: true,
                context_warned_at: $now
            }' > "$SESSION_FLAGS_FILE"
    fi

    # Calculate usage percentage
    USAGE_PERCENT=$((ESTIMATED_TOKENS * 100 / CONTEXT_LIMIT))

    # Display warning to user (stderr for immediate visibility)
    cat >&2 <<EOF

⚠️  CONTEXT THRESHOLD WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current context usage: ~${ESTIMATED_TOKENS} tokens (${USAGE_PERCENT}% of ${CONTEXT_LIMIT} limit)

You are approaching Claude's context window limit. Consider:

1. Wrap up current conversation and start a new session
2. Create a continuation prompt to preserve important context
3. Save work-in-progress state before switching sessions

To create a continuation prompt:
  "Please create a continuation prompt summarizing our session"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

    # Output context suggestion to Claude (stdout)
    cat <<EOF
<context-threshold-notice>
CONTEXT USAGE: ~${ESTIMATED_TOKENS} tokens (${USAGE_PERCENT}% of ${CONTEXT_LIMIT})

User has been notified about high context usage. If they request a continuation prompt:
1. Summarize key discussion points and decisions made
2. List work in progress and next steps
3. Include relevant file paths and code snippets
4. Format as a clear, concise prompt for the next session

Do NOT proactively create a continuation prompt unless requested.
</context-threshold-notice>
EOF
fi

exit 0
