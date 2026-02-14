---
name: overnight
description: Queue work for overnight execution to maximize quota utilization
model: haiku
tools: Bash, Read, Write
permissionMode: acceptEdits
---

# Overnight Work Queue Skill

Queue asynchronous work (searches, analysis, batch processing) for overnight execution to maximize quota utilization.

## How It Works

When you queue work using `/overnight`, the system:
1. Classifies the work as async-capable (must not require user interaction)
2. Estimates quota usage and duration
3. Adds to overnight queue with priority and dependencies
4. Schedules for execution at 22:00 (10 PM) via systemd timer
5. Results available in the morning via morning briefing hook

## Usage Examples

```bash
/overnight search for papers on mitochondrial dysfunction in ME/CFS
/overnight analyze all chapters for missing citations
/overnight generate summary statistics from case study data
/overnight run comprehensive test suite and report failures
```

## Implementation

```bash
#!/bin/bash
set -euo pipefail

# Parse user request (everything after /overnight)
WORK_REQUEST="$@"

if [ -z "$WORK_REQUEST" ]; then
    echo "❌ Error: Please specify work to queue"
    echo ""
    echo "Usage: /overnight <work description>"
    echo ""
    echo "Examples:"
    echo "  /overnight search for papers on immune dysfunction"
    echo "  /overnight analyze codebase for technical debt"
    exit 1
fi

# Paths
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/code/claude-router-system/plugins/infolead-claude-subscription-router}"
IMPL_DIR="$PLUGIN_ROOT/implementation"
STATE_DIR="$HOME/.claude/infolead-claude-subscription-router/state"
QUEUE_FILE="$STATE_DIR/temporal-work-queue.json"

# Ensure state directory exists
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"

# Capture project context
PROJECT_PATH="$(pwd)"
PROJECT_NAME="$(basename "$PROJECT_PATH")"

# Generate work ID
WORK_ID="t$(date +%s)"

# Call Python temporal scheduler to add work to queue
QUEUE_RESULT=$(python3 "$IMPL_DIR/temporal_scheduler.py" add \
    "$WORK_REQUEST" \
    --timing async \
    --project-path "$PROJECT_PATH" \
    --project-name "$PROJECT_NAME" \
    --quota 15 \
    --duration 20 \
    --priority 5 \
    2>&1)

if [ $? -eq 0 ]; then
    # Extract work ID from result (format: "Added work: <id> (async)")
    WORK_ID=$(echo "$QUEUE_RESULT" | sed -n 's/^Added work: \([a-zA-Z0-9_]*\).*/\1/p' || echo "unknown")

    # Success output
    cat <<EOF

✓ Work queued for overnight execution:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ID:          $WORK_ID
  Project:     $PROJECT_NAME ($PROJECT_PATH)
  Task:        $WORK_REQUEST
  Estimated:   ~20 minutes, ~15 Sonnet messages
  Scheduled:   Tonight at 22:00
  Results:     $STATE_DIR/overnight-results/results-*.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Type '/quota' to see tonight's full overnight schedule

EOF
else
    echo "❌ Error queueing work: $QUEUE_RESULT"
    exit 1
fi
```

## Output Format

```
✓ Work queued for overnight execution:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ID:          t1707862543
  Project:     claude-router-system
  Task:        Search for papers on mitochondrial dysfunction
  Estimated:   ~20 minutes, ~15 Sonnet messages
  Scheduled:   Tonight at 22:00
  Results:     ~/.claude/.../overnight-results/t1707862543-results.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Type '/quota' to see tonight's full overnight schedule
```

## Notes

- Work must be async-capable (no user interaction required)
- Overnight execution starts at 22:00 (10 PM) via systemd timer
- Results available in morning briefing at next session start
- Maximum 3-hour execution window (timeout protection)
- Work with dependencies executes in correct order (DAG)
