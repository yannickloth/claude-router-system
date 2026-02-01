#!/bin/bash
# Usage Dashboard for Claude Router System
# Displays model distribution, estimated costs, and routing efficiency
#
# Usage: usage-dashboard.sh [--today|--week|--month|--all] [--json]
#
# Change Driver: MONITORING_REQUIREMENTS

set -euo pipefail

# Force C locale for consistent decimal handling
export LC_NUMERIC=C

METRICS_DIR="${HOME}/.claude/infolead-router/metrics"
OUTPUT_FORMAT="human"
DATE_RANGE="today"

# Cost estimates per message (rough approximation based on typical usage)
# These are conservative estimates assuming ~2k tokens input, ~1k tokens output per message
declare -A COST_PER_MSG=(
    [haiku]="0.001"    # ~$0.25/MTok input + $1.25/MTok output = ~$0.001 per msg
    [sonnet]="0.012"   # ~$3/MTok input + $15/MTok output = ~$0.012 per msg
    [opus]="0.060"     # ~$15/MTok input + $75/MTok output = ~$0.060 per msg
)

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --today)
            DATE_RANGE="today"
            shift
            ;;
        --week)
            DATE_RANGE="week"
            shift
            ;;
        --month)
            DATE_RANGE="month"
            shift
            ;;
        --all)
            DATE_RANGE="all"
            shift
            ;;
        --json)
            OUTPUT_FORMAT="json"
            shift
            ;;
        -h|--help)
            echo "Usage: usage-dashboard.sh [--today|--week|--month|--all] [--json]"
            echo ""
            echo "Options:"
            echo "  --today   Show today's metrics (default)"
            echo "  --week    Show last 7 days"
            echo "  --month   Show last 30 days"
            echo "  --all     Show all available metrics"
            echo "  --json    Output in JSON format"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Check if metrics directory exists
if [[ ! -d "$METRICS_DIR" ]]; then
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        echo '{"error": "No metrics data found", "metrics_dir": "'"$METRICS_DIR"'"}'
    else
        echo "No metrics data found at $METRICS_DIR"
        echo "Run some agent tasks to generate metrics."
    fi
    exit 0
fi

# Determine which files to process
FILES=()
TODAY=$(date +%Y-%m-%d)
case $DATE_RANGE in
    today)
        if [[ -f "$METRICS_DIR/${TODAY}.jsonl" ]]; then
            FILES+=("$METRICS_DIR/${TODAY}.jsonl")
        fi
        ;;
    week)
        for i in {0..6}; do
            DATE=$(date -d "$TODAY -$i days" +%Y-%m-%d 2>/dev/null || date -v-${i}d +%Y-%m-%d 2>/dev/null || echo "")
            if [[ -n "$DATE" && -f "$METRICS_DIR/${DATE}.jsonl" ]]; then
                FILES+=("$METRICS_DIR/${DATE}.jsonl")
            fi
        done
        ;;
    month)
        for i in {0..29}; do
            DATE=$(date -d "$TODAY -$i days" +%Y-%m-%d 2>/dev/null || date -v-${i}d +%Y-%m-%d 2>/dev/null || echo "")
            if [[ -n "$DATE" && -f "$METRICS_DIR/${DATE}.jsonl" ]]; then
                FILES+=("$METRICS_DIR/${DATE}.jsonl")
            fi
        done
        ;;
    all)
        mapfile -t FILES < <(find "$METRICS_DIR" -name "*.jsonl" -type f 2>/dev/null | sort)
        ;;
esac

if [[ ${#FILES[@]} -eq 0 ]]; then
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        echo '{"error": "No metrics data for specified period", "period": "'"$DATE_RANGE"'"}'
    else
        echo "No metrics data for specified period ($DATE_RANGE)"
    fi
    exit 0
fi

# Aggregate metrics using jq (filter to agent_stop events only)
COMBINED_DATA=$(cat "${FILES[@]}" 2>/dev/null | jq -c 'select(.event == "agent_stop")' 2>/dev/null || echo "")

if [[ -z "$COMBINED_DATA" ]]; then
    if [[ "$OUTPUT_FORMAT" == "json" ]]; then
        echo '{"error": "Empty metrics files"}'
    else
        echo "Metrics files are empty"
    fi
    exit 0
fi

# Calculate statistics
STATS=$(echo "$COMBINED_DATA" | jq -s '
    # Count by model tier
    group_by(.model_tier) |
    map({
        model: .[0].model_tier,
        count: length,
        total_duration_sec: (map(.duration_sec // 0) | add),
        avg_duration_sec: (map(.duration_sec // 0) | add / length)
    }) |
    {
        by_model: .,
        total_agents: (map(.count) | add),

        # Agent type breakdown
        agent_types: (
            [.[] | .model] as $models |
            input |
            group_by(.agent_type) |
            map({
                agent: .[0].agent_type,
                count: length
            }) |
            sort_by(-.count) |
            .[0:10]
        )
    }
' 2>/dev/null <<< "$COMBINED_DATA
$COMBINED_DATA" || echo '{"error": "Failed to parse metrics"}')

# If first parse failed, try simpler approach
if echo "$STATS" | jq -e '.error' >/dev/null 2>&1; then
    # Simpler aggregation
    STATS=$(echo "$COMBINED_DATA" | jq -s '
        {
            total_agents: length,
            by_model: (group_by(.model_tier) | map({
                model: .[0].model_tier,
                count: length,
                total_duration_sec: (map(.duration_sec // 0) | add),
                avg_duration_sec: ((map(.duration_sec // 0) | add) / length)
            })),
            agent_types: (group_by(.agent_type) | map({
                agent: .[0].agent_type,
                count: length
            }) | sort_by(-.count) | .[0:10])
        }
    ')
fi

# Calculate cost estimates
HAIKU_COUNT=$(echo "$STATS" | jq -r '.by_model[] | select(.model == "haiku") | .count // 0')
SONNET_COUNT=$(echo "$STATS" | jq -r '.by_model[] | select(.model == "sonnet") | .count // 0')
OPUS_COUNT=$(echo "$STATS" | jq -r '.by_model[] | select(.model == "opus") | .count // 0')

# Default to 0 if empty
HAIKU_COUNT=${HAIKU_COUNT:-0}
SONNET_COUNT=${SONNET_COUNT:-0}
OPUS_COUNT=${OPUS_COUNT:-0}

# Calculate costs
HAIKU_COST=$(echo "$HAIKU_COUNT * ${COST_PER_MSG[haiku]}" | bc -l 2>/dev/null || echo "0")
SONNET_COST=$(echo "$SONNET_COUNT * ${COST_PER_MSG[sonnet]}" | bc -l 2>/dev/null || echo "0")
OPUS_COST=$(echo "$OPUS_COUNT * ${COST_PER_MSG[opus]}" | bc -l 2>/dev/null || echo "0")
TOTAL_COST=$(echo "$HAIKU_COST + $SONNET_COST + $OPUS_COST" | bc -l 2>/dev/null || echo "0")

# Calculate hypothetical cost if everything used Sonnet
TOTAL_COUNT=$(echo "$STATS" | jq -r '.total_agents // 0')
SONNET_ONLY_COST=$(echo "$TOTAL_COUNT * ${COST_PER_MSG[sonnet]}" | bc -l 2>/dev/null || echo "0")
SAVINGS=$(echo "$SONNET_ONLY_COST - $TOTAL_COST" | bc -l 2>/dev/null || echo "0")

if [[ "$OUTPUT_FORMAT" == "json" ]]; then
    # JSON output
    echo "$STATS" | jq \
        --arg period "$DATE_RANGE" \
        --arg haiku_cost "$HAIKU_COST" \
        --arg sonnet_cost "$SONNET_COST" \
        --arg opus_cost "$OPUS_COST" \
        --arg total_cost "$TOTAL_COST" \
        --arg savings "$SAVINGS" \
        --arg sonnet_only_cost "$SONNET_ONLY_COST" \
        '. + {
            period: $period,
            cost_estimates: {
                haiku: ($haiku_cost | tonumber),
                sonnet: ($sonnet_cost | tonumber),
                opus: ($opus_cost | tonumber),
                total: ($total_cost | tonumber),
                hypothetical_sonnet_only: ($sonnet_only_cost | tonumber),
                estimated_savings: ($savings | tonumber)
            }
        }'
else
    # Human-readable output
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "                 Claude Router Usage Dashboard"
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    echo "Period: $DATE_RANGE"
    echo "Total Agent Invocations: $TOTAL_COUNT"
    echo ""
    echo "───────────────────────────────────────────────────────────────────"
    echo "                      Model Distribution"
    echo "───────────────────────────────────────────────────────────────────"
    echo ""

    # Model breakdown with bar chart
    echo "$STATS" | jq -r '.by_model[] | "\(.model): \(.count) invocations"' | while read -r line; do
        MODEL=$(echo "$line" | cut -d: -f1)
        COUNT=$(echo "$line" | grep -oE '[0-9]+' | head -1)

        # Calculate bar width (max 40 chars)
        if [[ "$TOTAL_COUNT" -gt 0 ]]; then
            BAR_WIDTH=$(echo "scale=0; $COUNT * 40 / $TOTAL_COUNT" | bc 2>/dev/null || echo "0")
        else
            BAR_WIDTH=0
        fi
        BAR=$(printf '%*s' "$BAR_WIDTH" '' | tr ' ' '█')

        printf "  %-8s %4d  %s\n" "$MODEL" "$COUNT" "$BAR"
    done

    echo ""
    echo "───────────────────────────────────────────────────────────────────"
    echo "                      Estimated Costs"
    echo "───────────────────────────────────────────────────────────────────"
    echo ""
    printf "  Haiku:   \$%.4f  (%d invocations @ \$%.4f/msg)\n" "$HAIKU_COST" "$HAIKU_COUNT" "${COST_PER_MSG[haiku]}"
    printf "  Sonnet:  \$%.4f  (%d invocations @ \$%.4f/msg)\n" "$SONNET_COST" "$SONNET_COUNT" "${COST_PER_MSG[sonnet]}"
    printf "  Opus:    \$%.4f  (%d invocations @ \$%.4f/msg)\n" "$OPUS_COST" "$OPUS_COUNT" "${COST_PER_MSG[opus]}"
    echo "  ─────────────────────────────"
    printf "  TOTAL:   \$%.4f\n" "$TOTAL_COST"
    echo ""
    echo "───────────────────────────────────────────────────────────────────"
    echo "                     Cost Optimization"
    echo "───────────────────────────────────────────────────────────────────"
    echo ""
    printf "  If all %d tasks used Sonnet:  \$%.4f\n" "$TOTAL_COUNT" "$SONNET_ONLY_COST"
    printf "  Actual cost with routing:      \$%.4f\n" "$TOTAL_COST"
    printf "  Estimated savings:             \$%.4f\n" "$SAVINGS"

    if [[ $(echo "$SONNET_ONLY_COST > 0" | bc -l 2>/dev/null || echo "0") -eq 1 ]]; then
        SAVINGS_PCT=$(echo "scale=1; $SAVINGS * 100 / $SONNET_ONLY_COST" | bc -l 2>/dev/null || echo "0")
        printf "  Savings percentage:            %.1f%%\n" "$SAVINGS_PCT"
    fi

    echo ""
    echo "───────────────────────────────────────────────────────────────────"
    echo "                     Top Agent Types"
    echo "───────────────────────────────────────────────────────────────────"
    echo ""
    echo "$STATS" | jq -r '.agent_types[]? | "  \(.agent): \(.count)"' | head -10

    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    echo "Note: Cost estimates are approximate based on typical token usage."
    echo "Actual costs may vary. Check your Anthropic dashboard for precise billing."
    echo ""
fi
