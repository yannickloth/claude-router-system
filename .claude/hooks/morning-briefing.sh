#!/bin/bash
# Morning Briefing Hook
# Displays overnight work results, quota status, and priority tasks
#
# Trigger: Run at session start each morning
# Change Driver: UX_REQUIREMENTS

MEMORY_DIR="$HOME/.claude/infolead-router/memory"
LOGS_DIR="$HOME/.claude/infolead-router/logs"
WORK_LOG="$MEMORY_DIR/completed-work.json"
SESSION_STATE="$MEMORY_DIR/session-state.json"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "☀️  Morning Briefing - $(date '+%A, %B %d, %Y')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ===== Overnight Work Results =====
echo "📋 Overnight Work Results:"
echo ""

if [ -f "$WORK_LOG" ]; then
    # Get work completed in last 24 hours
    YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
    COMPLETED_COUNT=$(jq --arg date "$YESTERDAY" '[.[] | select(.completed_at | startswith($date))] | length' "$WORK_LOG" 2>/dev/null || echo "0")

    if [ "$COMPLETED_COUNT" -gt 0 ]; then
        echo "   ✓ Completed tasks: $COMPLETED_COUNT"
        echo ""

        # Show recent completions
        jq -r --arg date "$YESTERDAY" '.[] | select(.completed_at | startswith($date)) | "   - \(.task_name) (\(.agent))"' "$WORK_LOG" 2>/dev/null | head -5

        if [ "$COMPLETED_COUNT" -gt 5 ]; then
            echo "   ... and $((COMPLETED_COUNT - 5)) more"
        fi
    else
        echo "   No overnight work completed"
    fi
else
    echo "   No work history found"
fi

echo ""

# ===== Quota Status =====
echo "💰 Quota Status:"
echo ""

# Calculate quota usage (simulated - real implementation would query API)
# For now, show placeholder
DAILY_LIMIT=10000
USED=0
REMAINING=$DAILY_LIMIT

if [ -f "$LOGS_DIR/quota-usage.json" ]; then
    USED=$(jq -r '.daily_usage // 0' "$LOGS_DIR/quota-usage.json" 2>/dev/null || echo "0")
    REMAINING=$((DAILY_LIMIT - USED))
fi

PERCENT_USED=$((USED * 100 / DAILY_LIMIT))

echo "   Daily quota: $USED / $DAILY_LIMIT messages ($PERCENT_USED% used)"
echo "   Remaining: $REMAINING messages"

if [ "$PERCENT_USED" -lt 50 ]; then
    echo "   Status: ✓ Plenty available"
elif [ "$PERCENT_USED" -lt 80 ]; then
    echo "   Status: ⚠️  Moderate usage"
else
    echo "   Status: 🔴 High usage - prioritize important work"
fi

echo ""

# ===== Priority Tasks for Today =====
echo "🎯 Priority Tasks:"
echo ""

if [ -f "$SESSION_STATE" ]; then
    # Check for work in progress
    WIP_COUNT=$(jq '.work_in_progress | length' "$SESSION_STATE" 2>/dev/null || echo "0")

    if [ "$WIP_COUNT" -gt 0 ]; then
        echo "   Work in progress: $WIP_COUNT tasks"
        echo ""
        jq -r '.work_in_progress[] | "   [ ] \(.task_name) (started: \(.started_at))"' "$SESSION_STATE" 2>/dev/null
    else
        echo "   No active work in progress"
    fi

    echo ""

    # Check current focus
    FOCUS=$(jq -r '.current_focus // "No focus set"' "$SESSION_STATE" 2>/dev/null)
    echo "   Current focus: $FOCUS"
else
    echo "   No session state found"
    echo "   Suggestion: Start with priority task definition"
fi

echo ""

# ===== Recent Search History =====
SEARCH_HISTORY="$MEMORY_DIR/search-history.json"

if [ -f "$SEARCH_HISTORY" ]; then
    RECENT_SEARCHES=$(jq 'length' "$SEARCH_HISTORY" 2>/dev/null || echo "0")

    if [ "$RECENT_SEARCHES" -gt 0 ]; then
        echo "🔍 Recent Searches (for deduplication):"
        echo ""
        jq -r '.[-3:] | .[] | "   - \(.query) (\(.timestamp))"' "$SEARCH_HISTORY" 2>/dev/null
        echo ""
    fi
fi

# ===== System Health =====
echo "🔧 System Status:"
echo ""

# Check if key directories exist
CHECKS=0
PASSED=0

if [ -d "$MEMORY_DIR" ]; then
    ((CHECKS++))
    ((PASSED++))
else
    echo "   ⚠️  Memory directory missing"
    ((CHECKS++))
fi

if [ -d "$LOGS_DIR" ]; then
    ((CHECKS++))
    ((PASSED++))
else
    echo "   ⚠️  Logs directory missing"
    ((CHECKS++))
fi

# Check index files
PROJECT_ROOT=$(pwd)
if [ -f "$PROJECT_ROOT/.claude-context-index.json" ]; then
    INDEX_AGE=$(find "$PROJECT_ROOT/.claude-context-index.json" -mtime +7 2>/dev/null)
    if [ -n "$INDEX_AGE" ]; then
        echo "   ⚠️  Context index is >7 days old - consider rebuilding"
    else
        ((CHECKS++))
        ((PASSED++))
    fi
else
    echo "   ℹ️  No context index found (run lazy_context_loader.py index)"
    ((CHECKS++))
fi

echo "   Health: $PASSED/$CHECKS checks passed"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Ready to start working. Type your request below."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""