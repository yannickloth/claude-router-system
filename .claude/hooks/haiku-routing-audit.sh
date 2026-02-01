#!/bin/bash
# Haiku Routing Audit Hook
# Monitors Haiku routing decisions for quality assurance
#
# Trigger: After each routing decision
# Change Driver: MONITORING_REQUIREMENTS

LOGS_DIR="$HOME/.claude/infolead-router/logs"
HAIKU_LOG="$LOGS_DIR/haiku-routing-decisions.log"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Log routing decision (expects environment variables or args)
REQUEST="${1:-$REQUEST}"
AGENT="${2:-$AGENT}"
DECISION="${3:-$DECISION}"

if [ -n "$REQUEST" ] && [ -n "$AGENT" ]; then
    echo "$(date -Iseconds): $DECISION → $AGENT | Request: $REQUEST" >> "$HAIKU_LOG"
fi

# Check for potential mis-routes
if [[ "$AGENT" == "haiku-general" ]]; then
    # Check for risky keywords that should have escalated
    if [[ "$REQUEST" =~ (delete|remove|drop|destroy|refactor|design|architect) ]]; then
        echo "⚠️  WARNING: Haiku routed risky request to haiku-general"
        echo "   Request: $REQUEST"
        echo "   This may need review"

        # Record warning in separate log
        WARNING_LOG="$LOGS_DIR/routing-warnings.log"
        echo "$(date -Iseconds): POTENTIAL_MISROUTE | $REQUEST → $AGENT" >> "$WARNING_LOG"
    fi
fi

# Weekly audit (runs on Mondays)
if [ "$(date +%u)" -eq 1 ]; then
    if [ -f "$HAIKU_LOG" ]; then
        echo ""
        echo "📊 Weekly Haiku Routing Audit:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Count last week's routes
        WEEK_AGO=$(date -d "7 days ago" -Iseconds)
        TOTAL_ROUTES=$(awk -v since="$WEEK_AGO" '$1 >= since' "$HAIKU_LOG" | wc -l)
        ESCALATIONS=$(grep "ESCALATE_TO_SONNET" "$HAIKU_LOG" | awk -v since="$WEEK_AGO" '$1 >= since' | wc -l)

        if [ "$TOTAL_ROUTES" -gt 0 ]; then
            ESCALATION_RATE=$((ESCALATIONS * 100 / TOTAL_ROUTES))

            echo "   Total routes: $TOTAL_ROUTES"
            echo "   Escalations: $ESCALATIONS ($ESCALATION_RATE%)"

            # Check if within target (30-40%)
            if [ "$ESCALATION_RATE" -ge 30 ] && [ "$ESCALATION_RATE" -le 40 ]; then
                echo "   Status: ✓ Within target range (30-40%)"
            elif [ "$ESCALATION_RATE" -lt 30 ]; then
                echo "   Status: ⚠️  Below target (may be over-escalating)"
            else
                echo "   Status: ⚠️  Above target (may be under-escalating)"
            fi

            # Record metric
            METRICS_SCRIPT="$(dirname "$0")/../../implementation/metrics_collector.py"
            if [ -f "$METRICS_SCRIPT" ]; then
                python3 "$METRICS_SCRIPT" record haiku_routing escalation_rate --value "$ESCALATION_RATE" 2>/dev/null
            fi
        fi

        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
    fi
fi
