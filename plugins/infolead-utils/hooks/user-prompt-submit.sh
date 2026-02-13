#!/usr/bin/env bash
#
# UserPromptSubmit Hook - DateTime Context Injection
#
# Purpose: Inject current local date/time into Claude's context before each prompt
#
# This hook runs BEFORE the user's prompt is sent to Claude and injects
# the current date/time from the user's local machine into the context.
#
# Hook contract:
# - Receives prompt content via stdin
# - Outputs enhanced context to stdout
# - Outputs debug info to stderr
#

set -euo pipefail

# Capture current local date/time for context injection
CURRENT_DATETIME=$(date '+%Y-%m-%d %H:%M:%S %Z')
CURRENT_DATE=$(date '+%Y-%m-%d')
CURRENT_TIME=$(date '+%H:%M:%S')
CURRENT_TIMEZONE=$(date '+%Z (UTC%:z)')
CURRENT_WEEKDAY=$(date '+%A')

# Debug output to stderr
echo "[DATETIME-CONTEXT] Injecting current date/time context" >&2
echo "[DATETIME-CONTEXT] Timestamp: $CURRENT_DATETIME" >&2

# Output datetime context to stdout for Claude
cat <<EOF
<current-datetime>
Date: $CURRENT_DATE ($CURRENT_WEEKDAY)
Time: $CURRENT_TIME
Timezone: $CURRENT_TIMEZONE
Full timestamp: $CURRENT_DATETIME

This is the current date and time on your local machine (user's computer) when this prompt was submitted.
</current-datetime>
EOF
