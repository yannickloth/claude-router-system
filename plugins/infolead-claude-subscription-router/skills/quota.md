---
name: quota
description: Show quota status, usage forecast, and overnight work schedule
model: haiku
tools: Bash, Read
---

# Quota Status Skill

Display current quota usage, remaining quota, and tonight's overnight work schedule.

## Usage

```bash
/quota              # Show status and tonight's schedule
/quota forecast     # Show quota utilization forecast
/quota history      # Show last 7 days of quota usage
```

## Implementation

```bash
#!/bin/bash
set -euo pipefail

# Parse subcommand
SUBCOMMAND="${1:-status}"

# Paths
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/code/claude-router-system/plugins/infolead-claude-subscription-router}"
IMPL_DIR="$PLUGIN_ROOT/implementation"
STATE_DIR="$HOME/.claude/infolead-claude-subscription-router/state"
QUEUE_FILE="$STATE_DIR/temporal-work-queue.json"

case "$SUBCOMMAND" in
    status|"")
        # Get current quota status
        QUOTA_STATUS=$(python3 "$IMPL_DIR/quota_tracker.py" status --format json 2>/dev/null || echo '{}')

        # Get tonight's scheduled work
        TONIGHT_WORK=$(python3 "$IMPL_DIR/temporal_scheduler.py" list-scheduled \
            --queue-file "$QUEUE_FILE" \
            --format json 2>/dev/null || echo '{"scheduled": [], "total_duration": 0, "total_quota": 0}')

        # Parse data
        HAIKU_USED=$(echo "$QUOTA_STATUS" | jq -r '.haiku.used // 0')
        SONNET_USED=$(echo "$QUOTA_STATUS" | jq -r '.sonnet.used // 0')
        SONNET_LIMIT=$(echo "$QUOTA_STATUS" | jq -r '.sonnet.limit // 1125')
        SONNET_PERCENT=$(echo "$QUOTA_STATUS" | jq -r '.sonnet.percent // 0')
        OPUS_USED=$(echo "$QUOTA_STATUS" | jq -r '.opus.used // 0')
        OPUS_LIMIT=$(echo "$QUOTA_STATUS" | jq -r '.opus.limit // 250')
        OPUS_PERCENT=$(echo "$QUOTA_STATUS" | jq -r '.opus.percent // 0')

        SCHEDULED_COUNT=$(echo "$TONIGHT_WORK" | jq -r '.scheduled | length')
        TOTAL_DURATION=$(echo "$TONIGHT_WORK" | jq -r '.total_duration // 0')
        TOTAL_QUOTA=$(echo "$TONIGHT_WORK" | jq -r '.total_quota // 0')

        # Calculate hours until reset (midnight)
        CURRENT_HOUR=$(date +%H)
        HOURS_UNTIL_RESET=$(( 24 - CURRENT_HOUR ))

        # Display status
        cat <<EOF

Quota Status ($(date +%Y-%m-%d))
═════════════════════════════════════════════════════════

Current Usage:
  Haiku:  $HAIKU_USED used (unlimited)
  Sonnet: $SONNET_USED/$SONNET_LIMIT (${SONNET_PERCENT}%) $([ $SONNET_PERCENT -gt 80 ] && echo "[⚠️  HIGH]" || echo "[OK]")
  Opus:   $OPUS_USED/$OPUS_LIMIT (${OPUS_PERCENT}%) $([ $OPUS_PERCENT -gt 80 ] && echo "[⚠️  HIGH]" || echo "[OK]")

EOF

        if [ "$SCHEDULED_COUNT" -gt 0 ]; then
            cat <<EOF
Tonight's Overnight Schedule ($SCHEDULED_COUNT items):
EOF
            echo "$TONIGHT_WORK" | jq -r '.scheduled[] | "  [\(.priority)] \(.description) (\(.estimated_duration_minutes)m, ~\(.estimated_quota) msgs) - \(.project_name)"'

            cat <<EOF

Total: ${TOTAL_DURATION} minutes, ~${TOTAL_QUOTA} Sonnet messages
Quota after overnight: $(( SONNET_USED + TOTAL_QUOTA ))/$SONNET_LIMIT ($(( (SONNET_USED + TOTAL_QUOTA) * 100 / SONNET_LIMIT ))%)

EOF
        else
            cat <<EOF
Tonight's Overnight Schedule: No work queued

💡 Queue some overnight work to utilize remaining quota:
   /overnight <work description>

EOF
        fi

        echo "Hours until reset: ${HOURS_UNTIL_RESET}h"
        echo "═════════════════════════════════════════════════════════"
        echo ""
        ;;

    forecast)
        # Show quota utilization forecast
        python3 "$IMPL_DIR/quota_tracker.py" forecast \
            --queue-file "$QUEUE_FILE"
        ;;

    history)
        # Show last 7 days of quota usage
        python3 "$IMPL_DIR/quota_tracker.py" history --days 7
        ;;

    *)
        echo "❌ Unknown subcommand: $SUBCOMMAND"
        echo ""
        echo "Usage: /quota [status|forecast|history]"
        exit 1
        ;;
esac
```

## Output Format

```
Quota Status (2026-02-13)
═════════════════════════════════════════════════════════

Current Usage:
  Haiku:  125 used (unlimited)
  Sonnet: 450/1125 (40%) [OK]
  Opus:   50/250 (20%) [OK]

Tonight's Overnight Schedule (3 items):
  [8] Literature search: immune dysfunction (20m, ~15 msgs) - research-project
  [7] Analysis: treatment approaches (25m, ~20 msgs) - research-project
  [6] Generate bibliography for chapter 3 (15m, ~10 msgs) - research-project

Total: 60 minutes, ~45 Sonnet messages
Quota after overnight: 495/1125 (44%)

Hours until reset: 5h
═════════════════════════════════════════════════════════
```

## Notes

- Quota limits reset daily at midnight (00:00)
- Reserve buffers: 10% Sonnet, 20% Opus
- High usage warning (>80%) helps plan overnight work
- Forecast shows projected quota utilization
