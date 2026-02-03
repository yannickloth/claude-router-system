#!/bin/bash
# Morning Briefing Hook
# Displays overnight work results, quota status, and priority tasks
#
# Trigger: Session start (morning hours only)
# Change Driver: UX_REQUIREMENTS

set -euo pipefail

# Only run during morning hours (6:00-11:59)
CURRENT_HOUR=$(date +%H)
if [ "$CURRENT_HOUR" -lt 6 ] || [ "$CURRENT_HOUR" -ge 12 ]; then
    exit 0
fi

# Check if already shown today
MARKER_DIR="$HOME/.claude/infolead-router/state"
MARKER_FILE="$MARKER_DIR/.morning-briefing-$(date +%Y%m%d)"
mkdir -p "$MARKER_DIR"

if [ -f "$MARKER_FILE" ]; then
    exit 0
fi

# Check for jq
if ! command -v jq &> /dev/null; then
    exit 0
fi

MEMORY_DIR="$HOME/.claude/infolead-router/memory"
LOGS_DIR="$HOME/.claude/infolead-router/logs"
WORK_LOG="$MEMORY_DIR/completed-work.json"
SESSION_STATE="$MEMORY_DIR/session-state.json"

echo "" >&2
echo "----------------------------------------" >&2
echo "Morning Briefing - $(date '+%A, %B %d')" >&2
echo "----------------------------------------" >&2
echo "" >&2

# ===== Overnight Work Results =====
if [ -f "$WORK_LOG" ]; then
    YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null || echo "")
    if [ -n "$YESTERDAY" ]; then
        COMPLETED_COUNT=$(jq --arg date "$YESTERDAY" '[.[] | select(.completed_at | startswith($date))] | length' "$WORK_LOG" 2>/dev/null || echo "0")

        if [ "$COMPLETED_COUNT" -gt 0 ]; then
            echo "Overnight: $COMPLETED_COUNT tasks completed" >&2
            jq -r --arg date "$YESTERDAY" '.[] | select(.completed_at | startswith($date)) | "  - \(.task_name // .description)"' "$WORK_LOG" 2>/dev/null | head -3 >&2
            echo "" >&2
        fi
    fi
fi

# ===== Work in Progress =====
if [ -f "$SESSION_STATE" ]; then
    WIP_COUNT=$(jq '.work_in_progress | length' "$SESSION_STATE" 2>/dev/null || echo "0")

    if [ "$WIP_COUNT" -gt 0 ]; then
        echo "In progress: $WIP_COUNT tasks" >&2
        jq -r '.work_in_progress[] | "  - \(.task_name // .description)"' "$SESSION_STATE" 2>/dev/null | head -3 >&2
        echo "" >&2
    fi

    # Show current focus
    FOCUS=$(jq -r '.current_focus // ""' "$SESSION_STATE" 2>/dev/null)
    if [ -n "$FOCUS" ] && [ "$FOCUS" != "null" ]; then
        echo "Focus: $FOCUS" >&2
        echo "" >&2
    fi
fi

# ===== Quota Status (if available) =====
QUOTA_FILE="$LOGS_DIR/quota-usage.json"
if [ -f "$QUOTA_FILE" ]; then
    USED=$(jq -r '.daily_usage // 0' "$QUOTA_FILE" 2>/dev/null || echo "0")
    if [ "$USED" -gt 0 ]; then
        echo "Quota used today: $USED messages" >&2
        echo "" >&2
    fi
fi

echo "----------------------------------------" >&2
echo "" >&2

# Mark as shown
touch "$MARKER_FILE"

exit 0
