# Agent Usage Tracking - Design Specification

## Overview

Comprehensive logging system to track routing recommendations, agent invocations, and routing compliance. Enables analysis of whether main Claude follows routing directives.

## Problem Statement

Currently we have:
- `routing_recommendation` records: router's decision for each request
- `agent_event` records: agent start/stop events

**Missing:** Link between routing recommendation and actual agent usage. Cannot answer:
- Did main Claude follow the routing directive?
- How often are routing directives ignored?
- Which types of requests have ignored directives?

## Solution Architecture

### 1. Enhanced Record Types

Add new record type to link requests to agent invocations:

```json
{
  "record_type": "request_tracking",
  "timestamp": "2026-02-13T10:30:00Z",
  "request_hash": "76670770ffc69f35",
  "routing_decision": "escalate",
  "routing_agent": null,
  "routing_confidence": 0.85,
  "actual_handler": "main",
  "agent_invoked": null,
  "agent_id": null,
  "compliance_status": "ignored",
  "metadata": {
    "reason": "Creation/design tasks require planning",
    "user_request_preview": "Design and implement..."
  }
}
```

**compliance_status values:**
- `followed`: Routing directive was followed (agent invoked as recommended)
- `ignored`: Routing directive was ignored (main handled directly or different agent)
- `no_directive`: No agent recommended (decision: direct, agent: null)
- `unknown`: Cannot determine (insufficient data)

### 2. Record Types Summary

| Record Type | Purpose | Created By | Linking Field |
|-------------|---------|------------|---------------|
| `routing_recommendation` | Router's decision | UserPromptSubmit hook | `request_hash` |
| `agent_event` | Agent lifecycle | SubagentStart/Stop hooks | `agent_id` |
| `request_tracking` | Request→Agent link | SubagentStart hook | `request_hash` + `agent_id` |

### 3. Data Flow

```
User Request
    ↓
UserPromptSubmit Hook
    ↓
routing_recommendation record
    {request_hash, decision, agent}
    ↓
Main Claude receives routing directive
    ↓
    ├─→ Follows directive → invokes agent
    │   ↓
    │   SubagentStart Hook
    │   ↓
    │   request_tracking record
    │   {request_hash, compliance_status: "followed"}
    │   ↓
    │   agent_event record (start)
    │
    └─→ Ignores directive → handles directly
        ↓
        (No agent invoked - detectable by absence)
```

### 4. Compliance Detection Logic

**At SubagentStart time:**
1. Receive agent spawn notification
2. Look up most recent `routing_recommendation` for this session
3. Compare recommended agent vs actual agent invoked
4. Write `request_tracking` record with compliance status

**At analysis time:**
1. Find all `routing_recommendation` records
2. For each, look for matching `request_tracking` record
3. If no match within 30 seconds → `compliance_status: "ignored"`

### 5. Hook Integration Points

#### UserPromptSubmit Hook (EXISTING - NO CHANGES)

Already writes `routing_recommendation` record. No changes needed.

#### SubagentStart Hook (ENHANCEMENT REQUIRED)

Current behavior:
- Receives JSON: `{cwd, agent_type, agent_id, transcript_path}`
- Writes `agent_event` record

New behavior:
- KEEP existing agent_event record
- ADD new `request_tracking` record
- Link to routing recommendation via timestamp proximity

**Implementation strategy:**
```bash
# Get most recent routing recommendation (within last 60 seconds)
RECENT_ROUTING=$(tail -100 "$METRICS_DIR/${TODAY}.jsonl" | \
  jq -r 'select(.record_type == "routing_recommendation") |
         select((now - (.timestamp | fromdateiso8601)) < 60)' | \
  tail -1)

if [[ -n "$RECENT_ROUTING" ]]; then
  REQUEST_HASH=$(echo "$RECENT_ROUTING" | jq -r '.request_hash')
  ROUTING_AGENT=$(echo "$RECENT_ROUTING" | jq -r '.recommendation.agent')
  ROUTING_DECISION=$(echo "$RECENT_ROUTING" | jq -r '.full_analysis.decision')

  # Determine compliance
  if [[ "$ROUTING_DECISION" == "escalate" && "$ROUTING_AGENT" != "escalate" ]]; then
    # Directive: invoke specific agent
    if [[ "$AGENT_TYPE" == "$ROUTING_AGENT" ]]; then
      COMPLIANCE="followed"
    else
      COMPLIANCE="ignored"
    fi
  elif [[ "$ROUTING_DECISION" == "escalate" && "$ROUTING_AGENT" == "escalate" ]]; then
    # Directive: escalate to router
    COMPLIANCE="followed"  # Any agent invocation counts as escalation
  else
    COMPLIANCE="no_directive"
  fi

  # Write request_tracking record
  jq -c -n \
    --arg record_type "request_tracking" \
    --arg timestamp "$TIMESTAMP" \
    --arg request_hash "$REQUEST_HASH" \
    --arg routing_decision "$ROUTING_DECISION" \
    --arg routing_agent "$ROUTING_AGENT" \
    --arg actual_handler "agent" \
    --arg agent_invoked "$AGENT_TYPE" \
    --arg agent_id "$AGENT_ID" \
    --arg compliance "$COMPLIANCE" \
    '{...}' >> "$METRICS_FILE"
fi
```

#### SubagentStop Hook (NO CHANGES)

Already captures duration and completion. No changes needed.

### 6. Analysis Queries

#### Query 1: Routing Compliance Rate

```bash
# Count routing recommendations
TOTAL_RECOMMENDATIONS=$(jq -s '[.[] | select(.record_type == "routing_recommendation")] | length' metrics/*.jsonl)

# Count followed directives
FOLLOWED=$(jq -s '[.[] | select(.record_type == "request_tracking" and .compliance_status == "followed")] | length' metrics/*.jsonl)

# Calculate compliance rate
echo "scale=1; $FOLLOWED * 100 / $TOTAL_RECOMMENDATIONS" | bc
```

#### Query 2: Ignored Directives

```bash
# Show all ignored directives
jq -s '.[] | select(.record_type == "request_tracking" and .compliance_status == "ignored")' metrics/*.jsonl
```

#### Query 3: Join Routing → Agent

```bash
# For each routing recommendation, show what actually happened
jq -s '
  [.[] | select(.record_type == "routing_recommendation")] as $recommendations |
  [.[] | select(.record_type == "request_tracking")] as $tracking |
  $recommendations | map({
    request_hash,
    recommended: .recommendation.agent,
    actual: ($tracking | map(select(.request_hash == .request_hash)) | .[0].agent_invoked // "none")
  })
' metrics/*.jsonl
```

### 7. New Analysis Tool

Create `plugins/infolead-claude-subscription-router/implementation/routing_compliance.py`:

```python
"""
Routing Compliance Analysis Tool

Analyzes whether main Claude follows routing directives.
"""

from pathlib import Path
from datetime import datetime, timedelta, UTC
import json
from typing import List, Dict, Optional
from dataclasses import dataclass

METRICS_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "metrics"

@dataclass
class ComplianceReport:
    total_recommendations: int
    followed: int
    ignored: int
    no_directive: int
    unknown: int
    compliance_rate: float
    ignored_examples: List[Dict]

def analyze_compliance(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> ComplianceReport:
    """Analyze routing compliance for a date range."""
    if start_date is None:
        start_date = datetime.now(UTC) - timedelta(days=7)
    if end_date is None:
        end_date = datetime.now(UTC)

    recommendations = []
    tracking = []

    # Read all relevant records
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        log_file = METRICS_DIR / f"{date_str}.jsonl"

        if log_file.exists():
            with open(log_file) as f:
                for line in f:
                    record = json.loads(line)
                    if record.get('record_type') == 'routing_recommendation':
                        recommendations.append(record)
                    elif record.get('record_type') == 'request_tracking':
                        tracking.append(record)

        current += timedelta(days=1)

    # Count compliance statuses
    followed = sum(1 for t in tracking if t.get('compliance_status') == 'followed')
    ignored = sum(1 for t in tracking if t.get('compliance_status') == 'ignored')
    no_directive = sum(1 for t in tracking if t.get('compliance_status') == 'no_directive')

    # Find untracked recommendations (likely ignored)
    tracked_hashes = {t.get('request_hash') for t in tracking}
    untracked = [r for r in recommendations if r.get('request_hash') not in tracked_hashes]
    unknown = len(untracked)

    total = len(recommendations)
    compliance_rate = (followed / total * 100) if total > 0 else 0

    # Get examples of ignored directives
    ignored_records = [t for t in tracking if t.get('compliance_status') == 'ignored'][:10]

    return ComplianceReport(
        total_recommendations=total,
        followed=followed,
        ignored=ignored,
        no_directive=no_directive,
        unknown=unknown,
        compliance_rate=compliance_rate,
        ignored_examples=ignored_records
    )

def main():
    """CLI interface."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 routing_compliance.py <report|details>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "report":
        report = analyze_compliance()
        print()
        print("=" * 70)
        print("  ROUTING COMPLIANCE REPORT")
        print("=" * 70)
        print()
        print(f"Total routing recommendations: {report.total_recommendations}")
        print(f"  Followed:     {report.followed} ({report.compliance_rate:.1f}%)")
        print(f"  Ignored:      {report.ignored}")
        print(f"  No directive: {report.no_directive}")
        print(f"  Unknown:      {report.unknown}")
        print()

        if report.ignored > 0:
            print("Recent ignored directives:")
            for ex in report.ignored_examples[:5]:
                print(f"  - {ex.get('timestamp')}: recommended {ex.get('routing_agent')}, "
                      f"got {ex.get('agent_invoked')}")
        print()

    elif command == "details":
        # Show detailed breakdown
        report = analyze_compliance()
        print(json.dumps(report.ignored_examples, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 8. Testing Strategy

#### Test Case 1: Directive Followed

```
1. User submits request
2. Router recommends haiku-general
3. Main Claude invokes haiku-general
4. Verify: request_tracking.compliance_status == "followed"
```

#### Test Case 2: Directive Ignored

```
1. User submits request
2. Router recommends haiku-general
3. Main Claude handles directly (no agent invoked)
4. Verify: No request_tracking record (detectable by analysis)
```

#### Test Case 3: No Directive

```
1. User submits request
2. Router says "direct" (no agent recommendation)
3. Main Claude handles directly
4. Verify: No request_tracking record (expected, not ignored)
```

#### Test Case 4: Agent Mismatch

```
1. User submits request
2. Router recommends haiku-general
3. Main Claude invokes sonnet-general
4. Verify: request_tracking.compliance_status == "ignored"
```

### 9. Limitations and Trade-offs

**Limitation 1: Timestamp-based linking**
- Request and agent spawn linked by temporal proximity (<60s)
- Could miss if delay between recommendation and invocation
- Mitigation: Use conservative 60s window

**Limitation 2: No request content in agent spawn**
- SubagentStart hook doesn't receive user request
- Cannot verify if agent was invoked for correct request
- Mitigation: Timestamp + session context is sufficient

**Limitation 3: Main handler detection**
- If main Claude handles directly, no agent event fires
- Can only detect by absence (no tracking record)
- Mitigation: Analysis tool identifies these cases

### 10. Implementation Checklist

- [x] Design record schema
- [ ] Enhance SubagentStart hook to write request_tracking records
- [ ] Create routing_compliance.py analysis tool
- [ ] Add compliance queries to metrics_collector.py
- [ ] Test all compliance scenarios
- [ ] Document query patterns
- [ ] Update plugin.json version

### 11. Future Enhancements

**Phase 2: Request content tracking**
- Store request preview in routing_recommendation
- Enable filtering by request type
- Query: "Show compliance for code review requests"

**Phase 3: Session-level tracking**
- Link all records within a session
- Track multi-turn conversations
- Analyze directive persistence across turns

**Phase 4: Real-time alerts**
- Detect ignored directives in real-time
- Alert user when compliance drops below threshold
- Suggest CLAUDE.md improvements

## Change Driver

**Changes when:** MONITORING_REQUIREMENTS
- Need to track different compliance metrics
- New analysis queries required
- Routing directive format changes
