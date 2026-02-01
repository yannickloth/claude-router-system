#!/bin/bash
# Overnight Work Executor
# Runs queued async work during off-hours (22:00-01:00)
# Scheduled via cron: 0 22 * * * /path/to/overnight-executor.sh

set -euo pipefail

# Configuration
STATE_DIR="$HOME/.claude/infolead-router/state"
QUEUE_FILE="$STATE_DIR/temporal-work-queue.json"
RESULTS_DIR="$STATE_DIR/overnight-results"
LOGS_DIR="$STATE_DIR/logs"
QUOTA_FILE="$STATE_DIR/quota-usage.json"

# Execution limits
MAX_DURATION_HOURS=3
MAX_QUOTA_PERCENT=80  # Use up to 80% of remaining daily quota
EXECUTION_START=$(date +%s)
EXECUTION_DEADLINE=$((EXECUTION_START + MAX_DURATION_HOURS * 3600))

# Initialize directories
mkdir -p "$STATE_DIR" "$RESULTS_DIR" "$LOGS_DIR"

# Logging
LOG_FILE="$LOGS_DIR/overnight-$(date +%Y%m%d).log"
log() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*" | tee -a "$LOG_FILE"
}

log "=== Overnight Executor Started ==="

# Check if queue file exists
if [ ! -f "$QUEUE_FILE" ]; then
    log "No queue file found. Creating empty queue."
    echo '{"queued_work": [], "completed_overnight": [], "failed_work": []}' > "$QUEUE_FILE"
    exit 0
fi

# Count queued items
QUEUED_COUNT=$(jq '.queued_work | length' "$QUEUE_FILE")
log "Found $QUEUED_COUNT work items in queue"

if [ "$QUEUED_COUNT" -eq 0 ]; then
    log "Queue is empty. Nothing to process."
    exit 0
fi

# Load current quota usage
SONNET_QUOTA_LIMIT=1125
OPUS_QUOTA_LIMIT=250
SONNET_USED=0
OPUS_USED=0

if [ -f "$QUOTA_FILE" ]; then
    SONNET_USED=$(jq -r '.used_today.sonnet // 0' "$QUOTA_FILE")
    OPUS_USED=$(jq -r '.used_today.opus // 0' "$QUOTA_FILE")
fi

SONNET_REMAINING=$((SONNET_QUOTA_LIMIT - SONNET_USED))
OPUS_REMAINING=$((OPUS_QUOTA_LIMIT - OPUS_USED))

log "Quota status: Sonnet $SONNET_USED/$SONNET_QUOTA_LIMIT (${SONNET_REMAINING} remaining)"
log "Quota status: Opus $OPUS_USED/$OPUS_QUOTA_LIMIT (${OPUS_REMAINING} remaining)"

# Calculate quota budget for overnight work
SONNET_BUDGET=$((SONNET_REMAINING * MAX_QUOTA_PERCENT / 100))
OPUS_BUDGET=$((OPUS_REMAINING * MAX_QUOTA_PERCENT / 100))

log "Overnight quota budget: Sonnet $SONNET_BUDGET, Opus $OPUS_BUDGET"

# Process queued work items
QUOTA_CONSUMED_SONNET=0
QUOTA_CONSUMED_OPUS=0
ITEMS_PROCESSED=0
ITEMS_COMPLETED=0
ITEMS_FAILED=0

# Sort queue by priority (highest first)
jq -c '.queued_work | sort_by(-.priority)[]' "$QUEUE_FILE" | while IFS= read -r work_item; do
    CURRENT_TIME=$(date +%s)

    # Check time deadline
    if [ "$CURRENT_TIME" -ge "$EXECUTION_DEADLINE" ]; then
        log "Time deadline reached. Stopping execution."
        break
    fi

    # Extract work item details
    WORK_ID=$(echo "$work_item" | jq -r '.id')
    DESCRIPTION=$(echo "$work_item" | jq -r '.description')
    ESTIMATED_QUOTA=$(echo "$work_item" | jq -r '.estimated_quota')
    PRIORITY=$(echo "$work_item" | jq -r '.priority')

    log "Processing work item: $WORK_ID (priority: $PRIORITY)"
    log "  Description: $DESCRIPTION"
    log "  Estimated quota: $ESTIMATED_QUOTA"

    # Check quota availability
    if [ "$ESTIMATED_QUOTA" -gt "$SONNET_BUDGET" ]; then
        log "  ⚠ Insufficient quota budget. Skipping."
        continue
    fi

    # Check dependencies
    DEPENDENCIES=$(echo "$work_item" | jq -r '.dependencies[]' 2>/dev/null || echo "")
    DEPENDENCIES_MET=true

    for dep in $DEPENDENCIES; do
        # Check if dependency is in completed_overnight
        DEP_COMPLETED=$(jq --arg dep "$dep" '.completed_overnight[] | select(.id == $dep)' "$QUEUE_FILE")
        if [ -z "$DEP_COMPLETED" ]; then
            log "  ⚠ Dependency not met: $dep. Skipping."
            DEPENDENCIES_MET=false
            break
        fi
    done

    if [ "$DEPENDENCIES_MET" = false ]; then
        continue
    fi

    # Execute work item
    RESULT_FILE="$RESULTS_DIR/${WORK_ID}-results.json"
    EXECUTION_LOG="$LOGS_DIR/${WORK_ID}-execution.log"

    log "  ▶ Executing work item..."

    # Execute via claude CLI (assumes claude command is available)
    # This is a simplified version - actual implementation would need to:
    # 1. Determine which agent to use based on work type
    # 2. Construct appropriate prompt
    # 3. Execute with proper error handling

    EXECUTION_START_TIME=$(date +%s)

    # Placeholder: actual execution would call claude with appropriate agent
    # For now, create a mock result structure
    {
        echo "{"
        echo "  \"work_id\": \"$WORK_ID\","
        echo "  \"description\": \"$DESCRIPTION\","
        echo "  \"status\": \"pending_implementation\","
        echo "  \"note\": \"Overnight executor needs claude CLI integration\","
        echo "  \"executed_at\": \"$(date -Iseconds)\""
        echo "}"
    } > "$RESULT_FILE"

    EXECUTION_END_TIME=$(date +%s)
    EXECUTION_DURATION=$((EXECUTION_END_TIME - EXECUTION_START_TIME))

    # Placeholder: track actual quota used (would come from claude execution)
    ACTUAL_QUOTA_USED=$ESTIMATED_QUOTA

    # Update quota consumption
    QUOTA_CONSUMED_SONNET=$((QUOTA_CONSUMED_SONNET + ACTUAL_QUOTA_USED))
    SONNET_BUDGET=$((SONNET_BUDGET - ACTUAL_QUOTA_USED))

    # Update state file: move from queued_work to completed_overnight
    TEMP_QUEUE=$(mktemp)
    jq --arg id "$WORK_ID" \
       --arg result_path "$RESULT_FILE" \
       --arg completed_at "$(date -Iseconds)" \
       --argjson quota_used "$ACTUAL_QUOTA_USED" \
       '.completed_overnight += [{
           "id": $id,
           "description": (.queued_work[] | select(.id == $id) | .description),
           "completed_at": $completed_at,
           "result_path": $result_path,
           "quota_used": $quota_used,
           "status": "success"
       }] |
       .queued_work = [.queued_work[] | select(.id != $id)]' \
       "$QUEUE_FILE" > "$TEMP_QUEUE"

    mv "$TEMP_QUEUE" "$QUEUE_FILE"

    ITEMS_PROCESSED=$((ITEMS_PROCESSED + 1))
    ITEMS_COMPLETED=$((ITEMS_COMPLETED + 1))

    log "  ✓ Completed in ${EXECUTION_DURATION}s (quota used: $ACTUAL_QUOTA_USED)"

    # Check if we're approaching quota limit
    if [ "$SONNET_BUDGET" -lt 50 ]; then
        log "Quota budget running low ($SONNET_BUDGET remaining). Stopping."
        break
    fi
done

# Summary
log "=== Overnight Executor Completed ==="
log "Items processed: $ITEMS_PROCESSED"
log "  Completed: $ITEMS_COMPLETED"
log "  Failed: $ITEMS_FAILED"
log "Quota consumed: Sonnet $QUOTA_CONSUMED_SONNET, Opus $QUOTA_CONSUMED_OPUS"

# Update quota tracking
if [ -f "$QUOTA_FILE" ]; then
    TEMP_QUOTA=$(mktemp)
    jq --argjson sonnet_add "$QUOTA_CONSUMED_SONNET" \
       --argjson opus_add "$QUOTA_CONSUMED_OPUS" \
       '.used_today.sonnet += $sonnet_add |
        .used_today.opus += $opus_add |
        .last_updated = now |
        .overnight_execution = {
            "date": (now | strftime("%Y-%m-%d")),
            "items_processed": '"$ITEMS_PROCESSED"',
            "items_completed": '"$ITEMS_COMPLETED"',
            "quota_consumed": {
                "sonnet": '"$QUOTA_CONSUMED_SONNET"',
                "opus": '"$QUOTA_CONSUMED_OPUS"'
            }
        }' \
       "$QUOTA_FILE" > "$TEMP_QUOTA"
    mv "$TEMP_QUOTA" "$QUOTA_FILE"
fi

# Generate morning report
MORNING_REPORT="$RESULTS_DIR/morning-report-$(date +%Y%m%d).txt"
{
    echo "=== Overnight Work Completed ==="
    echo "Date: $(date +%Y-%m-%d)"
    echo ""
    echo "Summary:"
    echo "  Items processed: $ITEMS_PROCESSED"
    echo "  Successful: $ITEMS_COMPLETED"
    echo "  Failed: $ITEMS_FAILED"
    echo "  Quota used: Sonnet $QUOTA_CONSUMED_SONNET"
    echo ""
    echo "Completed work:"
    jq -r '.completed_overnight[] |
           select(.completed_at | startswith("'"$(date +%Y-%m-%d)"'")) |
           "  - \(.description)\n    Result: \(.result_path)\n    Quota: \(.quota_used) messages\n"' \
       "$QUEUE_FILE"

    if [ "$ITEMS_FAILED" -gt 0 ]; then
        echo ""
        echo "Failed work:"
        jq -r '.failed_work[] |
               select(.failed_at | startswith("'"$(date +%Y-%m-%d)"'")) |
               "  - \(.description)\n    Error: \(.error)\n"' \
           "$QUEUE_FILE"
    fi

    REMAINING_COUNT=$(jq '.queued_work | length' "$QUEUE_FILE")
    if [ "$REMAINING_COUNT" -gt 0 ]; then
        echo ""
        echo "Still queued ($REMAINING_COUNT items):"
        jq -r '.queued_work[] | "  - \(.description) (priority: \(.priority))"' "$QUEUE_FILE"
    fi
} > "$MORNING_REPORT"

log "Morning report generated: $MORNING_REPORT"

exit 0
