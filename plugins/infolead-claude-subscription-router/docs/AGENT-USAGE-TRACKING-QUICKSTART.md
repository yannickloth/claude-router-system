# Agent Usage Tracking - Quick Start Guide

## Overview

The agent usage tracking system automatically logs:
1. **Routing recommendations** - What the router recommends for each request
2. **Agent invocations** - Which agents are actually invoked
3. **Compliance status** - Whether routing directives are followed or ignored

## What Gets Logged

### Three Record Types

#### 1. routing_recommendation
Created by: `UserPromptSubmit` hook (existing, unchanged)
```json
{
  "record_type": "routing_recommendation",
  "timestamp": "2026-02-13T10:30:00Z",
  "request_hash": "abc123...",
  "recommendation": {
    "agent": "haiku-general",
    "reason": "Simple task",
    "confidence": 0.85
  },
  "full_analysis": {
    "decision": "escalate",
    "agent": "haiku-general"
  }
}
```

#### 2. request_tracking (NEW)
Created by: Enhanced `SubagentStart` hook
```json
{
  "record_type": "request_tracking",
  "timestamp": "2026-02-13T10:30:05Z",
  "request_hash": "abc123...",
  "routing_decision": "escalate",
  "routing_agent": "haiku-general",
  "actual_handler": "agent",
  "agent_invoked": "haiku-general",
  "compliance_status": "followed",
  "project": "my-project"
}
```

#### 3. agent_event
Created by: `SubagentStart` and `SubagentStop` hooks (existing, unchanged)
```json
{
  "record_type": "agent_event",
  "event": "agent_stop",
  "timestamp": "2026-02-13T10:32:00Z",
  "agent_type": "haiku-general",
  "agent_id": "abc123",
  "model_tier": "haiku",
  "duration_sec": 120
}
```

## Compliance Status Values

- `followed` - Main Claude invoked the recommended agent
- `ignored` - Main Claude invoked a different agent or none
- `no_directive` - Router said "handle directly" (no agent expected)
- `unknown` - Cannot determine (insufficient data)

## Using the Analysis Tools

### View Compliance Report

```bash
cd plugins/infolead-claude-subscription-router/implementation

# Show compliance summary
python3 routing_compliance.py report
```

**Output:**
```
==================================================================
  ROUTING COMPLIANCE REPORT
==================================================================

Total routing recommendations: 150

  Followed:     120 ( 80.0%)
  Ignored:       20
  No directive:   5
  Unknown:        5

Recent ignored directives (sample):
  2026-02-13 14:30 | recommended: haiku-general | actual: sonnet-general
    reason: Simple query task

Compliance by recommended agent:
Agent                    Followed     Ignored     Unknown
--------------------------------------------------------------------
haiku-general                  45          10           2 (79%)
sonnet-general                 35           5           1 (88%)
router                         40           5           2 (85%)
```

### View Ignored Directives Details

```bash
python3 routing_compliance.py ignored
```

Shows detailed list of all ignored routing directives with timestamps, request hashes, and reasons.

### View Compliance by Agent

```bash
python3 routing_compliance.py by-agent
```

Breakdown showing which agents have the best/worst compliance rates.

### Export Data for Analysis

```bash
# JSON format
python3 routing_compliance.py export --format json > compliance.json

# CSV format
python3 routing_compliance.py export --format csv > compliance.csv
```

Use for external analysis in spreadsheets or data tools.

### Integrated with Metrics Collector

```bash
# View compliance alongside other metrics
python3 metrics_collector.py compliance
```

## Query Examples

### Find Specific Request

```bash
# Find all records for a specific request hash
REQUEST_HASH="abc123"
jq -s ".[] | select(.request_hash == \"$REQUEST_HASH\")" \
  ~/.claude/infolead-claude-subscription-router/metrics/*.jsonl
```

### Count Compliance Status

```bash
# Count by compliance status (last 7 days)
jq -s '[.[] | select(.record_type == "request_tracking")] |
       group_by(.compliance_status) |
       map({status: .[0].compliance_status, count: length})' \
  ~/.claude/infolead-claude-subscription-router/metrics/*.jsonl
```

### Find Ignored Directives for Specific Agent

```bash
# Find cases where haiku-general was recommended but not used
jq -s '.[] | select(.record_type == "request_tracking" and
                    .routing_agent == "haiku-general" and
                    .compliance_status == "ignored")' \
  ~/.claude/infolead-claude-subscription-router/metrics/*.jsonl
```

### Calculate Compliance Rate by Project

```bash
# Compliance rate per project
jq -s '[.[] | select(.record_type == "request_tracking")] |
       group_by(.project) |
       map({
         project: .[0].project,
         total: length,
         followed: ([.[] | select(.compliance_status == "followed")] | length),
         rate: ([.[] | select(.compliance_status == "followed")] | length) / length * 100
       })' \
  ~/.claude/infolead-claude-subscription-router/metrics/*.jsonl
```

## How It Works

### Flow Diagram

```
1. User submits request
   ↓
2. UserPromptSubmit hook runs
   ↓
3. Router analyzes request
   ↓
4. routing_recommendation record written
   {request_hash: "abc123", recommended_agent: "haiku-general"}
   ↓
5. Main Claude receives routing directive
   ↓
6a. IF Claude follows directive:
      - Invokes haiku-general agent
      - SubagentStart hook runs
      - Links to recommendation via request_hash
      - Creates request_tracking record
        {compliance_status: "followed"}
   ↓
6b. IF Claude ignores directive:
      - Invokes different agent (or none)
      - SubagentStart hook runs (if agent invoked)
      - Creates request_tracking record
        {compliance_status: "ignored"}
      - OR no tracking record (if no agent invoked)
```

### Linking Logic

The `SubagentStart` hook links agent invocations to routing recommendations by:

1. Reading the most recent `routing_recommendation` record (within last 60 seconds)
2. Comparing recommended agent vs actual agent invoked
3. Determining compliance status:
   - `followed` if agents match
   - `ignored` if agents differ
   - `no_directive` if router said "direct"

## File Locations

- **Metrics data:** `~/.claude/infolead-claude-subscription-router/metrics/YYYY-MM-DD.jsonl`
- **Analysis tool:** `plugins/infolead-claude-subscription-router/implementation/routing_compliance.py`
- **Enhanced hook:** `plugins/infolead-claude-subscription-router/hooks/log-subagent-start.sh`
- **Tests:** `tests/infolead-claude-subscription-router/test_agent_usage_tracking.sh`

## Testing

```bash
# Run compliance analyzer tests
cd plugins/infolead-claude-subscription-router/implementation
python3 routing_compliance.py --test

# Run full tracking system tests
cd /home/nicky/code/claude-router-system
./tests/infolead-claude-subscription-router/test_agent_usage_tracking.sh
```

## Troubleshooting

### No tracking records appearing

**Check:**
1. Is the hook properly installed? Run `./scripts/setup-hooks-workaround.sh`
2. Are agents being invoked? Check `agent_event` records
3. Are routing recommendations being created? Check for `routing_recommendation` records

### Compliance always shows "unknown"

**Possible causes:**
- Time gap >60s between recommendation and agent invocation
- Request hash mismatch
- Missing routing recommendation

**Debug:**
```bash
# Check recent recommendations
tail -50 ~/.claude/infolead-claude-subscription-router/metrics/$(date +%Y-%m-%d).jsonl | \
  jq 'select(.record_type == "routing_recommendation")'

# Check recent tracking
tail -50 ~/.claude/infolead-claude-subscription-router/metrics/$(date +%Y-%m-%d).jsonl | \
  jq 'select(.record_type == "request_tracking")'
```

### High "ignored" rate

**Investigate:**
1. Are routing recommendations accurate?
2. Is main Claude receiving the routing directive?
3. Check CLAUDE.md instructions - are they clear?

```bash
# See which recommendations are being ignored most
python3 routing_compliance.py by-agent
```

## Integration with Existing Tools

### Works with metrics_collector.py

The compliance analysis is integrated into the main metrics collector:

```bash
# View all metrics including compliance
python3 metrics_collector.py dashboard

# View compliance specifically
python3 metrics_collector.py compliance
```

### Works with existing reports

Compliance data appears in daily/weekly reports automatically once integrated.

## Next Steps

After analyzing compliance data, you may want to:

1. **Improve routing accuracy** - If compliance is high but outcomes are poor, routing logic may need tuning
2. **Strengthen directives** - If compliance is low, CLAUDE.md instructions may need clarification
3. **Analyze patterns** - Look for request types with consistently ignored directives
4. **Track trends** - Monitor compliance rate over time to measure improvement

## Reference

For detailed design and implementation details, see:
- `docs/AGENT-USAGE-TRACKING.md` - Full design specification
- `implementation/routing_compliance.py` - Analysis tool source code
- `hooks/log-subagent-start.sh` - Enhanced hook implementation
