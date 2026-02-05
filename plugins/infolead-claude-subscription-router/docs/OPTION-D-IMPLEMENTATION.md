# Option D Implementation: Hybrid Advisory Routing System

**Status**: ✅ Implemented
**Date**: 2026-02-05
**Version**: 1.3.0

---

## Overview

This document describes the implementation of **Option D: Hybrid - Visible Advisory System** for the Claude Router plugin.

## Problem Statement

The previous routing system had critical issues:

1. **Invisible Operation**: Routing decisions happened silently, creating a "black box"
2. **No Actual Routing**: Pre-router analyzed requests but recommendations were discarded
3. **Stale Metrics**: Only test data was captured, no real usage tracking
4. **User Distrust**: Lack of visibility led to lack of confidence in the system

## Solution: Option D - Hybrid Advisory Routing

### Architecture

```
User Request
     ↓
[UserPromptSubmit Hook] ← Runs BEFORE main Claude sees request
     ↓
[routing_core.py] ← Mechanical escalation logic (existing)
     ↓
[JSON Recommendation] ← Structured routing decision
     ↓
├─→ [User (stderr)] ← Sees: "[ROUTER] Recommendation: haiku-general (confidence: 0.95)"
└─→ [Main Claude (stdout)] ← Receives: <routing-recommendation>...</routing-recommendation>
     ↓
[Main Claude Decision] ← Final routing decision with full context
     ↓
[Execution] ← Delegate to chosen agent
     ↓
[Metrics] ← Track: recommendation vs actual vs outcome
```

### Key Innovations

1. **Dual Output**: Both user and Claude see routing recommendations
2. **Advisory not Mandatory**: Main Claude makes final decision with full context
3. **Full Visibility**: Every routing decision is logged and displayed
4. **Metrics Tracking**: Captures recommendations, actual decisions, and outcomes
5. **No Black Box**: Complete transparency in the routing process

---

## Implementation Details

### Modified Files

#### 1. `hooks/user-prompt-submit.sh` (MAJOR CHANGES)

**Before** (invisible):
```bash
python3 "$ROUTING_SCRIPT" <<< "$USER_REQUEST" 2>/dev/null || true
exit 0
```

**After** (visible):
```bash
# Get JSON recommendation
ROUTING_OUTPUT=$(python3 "$ROUTING_SCRIPT" --json <<< "$USER_REQUEST")

# Extract fields for display
AGENT=$(echo "$ROUTING_OUTPUT" | jq -r '.agent // "unknown"')
REASON=$(echo "$ROUTING_OUTPUT" | jq -r '.reason')
CONFIDENCE=$(echo "$ROUTING_OUTPUT" | jq -r '.confidence')

# Output to stderr (user sees it)
echo "[ROUTER] Recommendation: $AGENT (confidence: $CONFIDENCE)" >&2
echo "[ROUTER] Reason: $REASON" >&2

# Output to stdout (Claude sees it as context)
cat <<EOF
<routing-recommendation request-hash="$REQUEST_HASH">
$ROUTING_OUTPUT
</routing-recommendation>
EOF
```

**Key changes**:
- Captures routing output instead of discarding it
- Displays recommendation to user via stderr
- Injects structured recommendation into Claude's context via stdout
- Logs recommendation to metrics for tracking

#### 2. `implementation/routing_core.py` (MINOR CHANGES)

**Change**: Simplified JSON output format

**Before**:
```json
{
  "request": "...",
  "routing": {
    "decision": "direct",
    "agent": "haiku-general",
    ...
  }
}
```

**After**:
```json
{
  "decision": "direct",
  "agent": "haiku-general",
  "reason": "High-confidence agent match",
  "confidence": 0.95
}
```

**Rationale**: Flatter structure is easier to parse in bash and more concise.

#### 3. New Metrics Collection

**Added to hook**:
- Logs every routing recommendation to `~/.claude/infolead-router/metrics/YYYY-MM-DD.jsonl`
- Includes request hash for correlation with actual agent usage
- Records timestamp, agent recommendation, reason, and confidence

**Metrics format**:
```json
{
  "record_type": "routing_recommendation",
  "timestamp": "2026-02-05T17:00:00+01:00",
  "request_hash": "abc123...",
  "recommendation": {
    "agent": "haiku-general",
    "reason": "High-confidence agent match",
    "confidence": 0.95
  },
  "full_analysis": { ... }
}
```

---

## How It Works

### Step 1: User Submits Request

User types a request in Claude Code CLI or VS Code extension.

### Step 2: Pre-Routing Analysis (Automatic)

Before main Claude sees the request:
1. `UserPromptSubmit` hook triggers
2. User request is piped to `routing_core.py --json`
3. Routing core applies mechanical escalation checklist:
   - Pattern matching (typo fix, syntax, format, etc.)
   - File path detection
   - Ambiguity detection
   - Risk assessment
4. Returns structured JSON recommendation

### Step 3: Dual Output

**To user (stderr)**:
```
[ROUTER] Recommendation: haiku-general (confidence: 0.95)
[ROUTER] Reason: High-confidence agent match
```

**To Claude (stdout, injected into context)**:
```xml
<routing-recommendation request-hash="a1b2c3">
{
  "decision": "direct",
  "agent": "haiku-general",
  "reason": "High-confidence agent match",
  "confidence": 0.95
}
</routing-recommendation>
```

### Step 4: Metrics Logging

Hook appends to `~/.claude/infolead-router/metrics/2026-02-05.jsonl`:
```json
{"record_type":"routing_recommendation","timestamp":"2026-02-05T17:00:00+01:00","request_hash":"a1b2c3","recommendation":{"agent":"haiku-general","reason":"High-confidence agent match","confidence":0.95},"full_analysis":{...}}
```

### Step 5: Main Claude Receives Context

Main Claude sees:
- Original user request
- Routing recommendation (in context)
- Conversation history
- Project knowledge

### Step 6: Claude Makes Final Decision

Claude evaluates:
1. Pre-router recommendation
2. Confidence level
3. Reasoning provided
4. Additional context (conversation history, project specifics)

Claude decides to:
- ✅ Follow recommendation
- ⚠️  Override (upgrade/downgrade tier)
- ❓ Escalate (ask for clarification)

### Step 7: Execution

Main Claude delegates to chosen agent and explains the decision to the user.

### Step 8: Outcome Tracking

When agent completes:
- `SubagentStop` hook logs completion
- Metrics capture: model tier used, duration, success/failure
- System can correlate: recommendation → actual decision → outcome

---

## Visibility Benefits

### For Users

1. **See Recommendations**: Every routing decision is displayed
2. **Understand Reasoning**: See why pre-router suggested specific agent
3. **Trust Building**: Transparency allows verification
4. **Confidence Scores**: Know how certain the recommendation is

### For Claude (Main Instance)

1. **Advisory Input**: Pre-router provides structured guidance
2. **Context Awareness**: Can override with conversation history
3. **Explain Decisions**: Can reference recommendation when explaining choices
4. **Learn Patterns**: See what pre-router suggests vs what works

### For System Improvement

1. **Metrics Collection**: Track recommendation accuracy
2. **Identify Patterns**: Where does pre-router get it right/wrong?
3. **Feedback Loop**: Improve escalation triggers based on outcomes
4. **Auditability**: Full trail of routing decisions

---

## Example Scenarios

### Scenario 1: Simple Mechanical Task

**User Request**: "Fix typo in README.md line 42: change 'teh' to 'the'"

**User Sees**:
```
[ROUTER] Recommendation: haiku-general (confidence: 0.98)
[ROUTER] Reason: High-confidence mechanical syntax fix with explicit file path
```

**Claude Sees**:
```xml
<routing-recommendation>
{"decision":"direct","agent":"haiku-general","reason":"High-confidence mechanical syntax fix","confidence":0.98}
</routing-recommendation>
```

**Claude's Response**:
```
The pre-router correctly identified this as a mechanical typo fix with an explicit file path.
This is exactly what haiku-general is designed for. I'll delegate to haiku-general.
```

**Outcome**: ✅ Recommendation followed

---

### Scenario 2: Hidden Complexity Detected by Claude

**User Request**: "Update the authentication config"

**User Sees**:
```
[ROUTER] Recommendation: sonnet-general (confidence: 0.75)
[ROUTER] Reason: Moderate confidence - file modification with some reasoning required
```

**Claude Sees**:
```xml
<routing-recommendation>
{"decision":"direct","agent":"sonnet-general","reason":"Moderate confidence match","confidence":0.75}
</routing-recommendation>
```

**Claude's Response**:
```
The pre-router suggests sonnet-general (confidence: 0.75), which makes sense for a config update.
However, I notice this involves the authentication system, which is security-critical.
Given the security implications, I'm upgrading to opus-general for extra careful handling.
```

**Outcome**: ⚠️  Recommendation overridden (upgraded to opus)

---

### Scenario 3: Escalation Recommendation

**User Request**: "Make it faster"

**User Sees**:
```
[ROUTER] Recommendation: escalate (confidence: 0.0)
[ROUTER] Reason: Ambiguous request - unclear scope and target
```

**Claude Sees**:
```xml
<routing-recommendation>
{"decision":"escalate","agent":null,"reason":"Ambiguous request","confidence":0.0}
</routing-recommendation>
```

**Claude's Response**:
```
The pre-router correctly flagged this as ambiguous. Before routing, I need clarification:
What specifically should be optimized?
- Build process performance?
- Runtime execution speed?
- UI responsiveness?
- A specific function or component?
```

**Outcome**: ❓ Escalated for clarification (followed recommendation)

---

## Metrics and Tracking

### Metrics Files

**Location**: `~/.claude/infolead-router/metrics/YYYY-MM-DD.jsonl`

**Record Types**:

1. **routing_recommendation**: Pre-router's suggestion
2. **agent_event**: Agent start/stop (existing)
3. **routing_compliance** (future): Match recommendation vs actual

### Example Metrics Queries

**Count recommendations by agent**:
```bash
jq -r 'select(.record_type=="routing_recommendation") | .recommendation.agent' \
  ~/.claude/infolead-router/metrics/2026-02-05.jsonl | sort | uniq -c
```

**Find low-confidence recommendations**:
```bash
jq 'select(.record_type=="routing_recommendation" and .recommendation.confidence < 0.7)' \
  ~/.claude/infolead-router/metrics/2026-02-05.jsonl
```

**Track escalations**:
```bash
jq -r 'select(.record_type=="routing_recommendation" and .recommendation.decision=="escalate") | .timestamp' \
  ~/.claude/infolead-router/metrics/2026-02-05.jsonl
```

---

## Testing

### Manual Test

```bash
# From plugin directory
export CLAUDE_PLUGIN_ROOT="$PWD"

# Test routing core directly
echo "Fix typo in README.md" | python3 implementation/routing_core.py --json

# Test full hook
echo "Fix typo in README.md" | bash hooks/user-prompt-submit.sh
```

### Expected Output

**From routing_core.py**:
```json
{
  "decision": "direct",
  "agent": "haiku-general",
  "reason": "High-confidence agent match",
  "confidence": 0.95
}
```

**From hook (stdout)**:
```xml
<routing-recommendation request-hash="...">
{
  "decision": "direct",
  "agent": "haiku-general",
  "reason": "High-confidence agent match",
  "confidence": 0.95
}
</routing-recommendation>
```

**From hook (stderr)**:
```
[ROUTER] Recommendation: haiku-general (confidence: 0.95)
[ROUTER] Reason: High-confidence agent match
```

---

## Future Enhancements

### Phase 2: Compliance Tracking

Add a mechanism to track when Claude follows vs overrides recommendations:

1. Capture what agent was recommended
2. Capture what agent was actually invoked
3. Capture outcome (success/failure/error)
4. Compute compliance rate and accuracy

**Metric**: `routing_compliance_rate = (followed_recommendations / total_recommendations)`

### Phase 3: Adaptive Escalation

Use collected metrics to improve escalation triggers:

1. Identify patterns where pre-router was wrong
2. Adjust confidence thresholds
3. Add new escalation patterns
4. Remove overly conservative triggers

### Phase 4: Agent Performance Feedback

Link routing recommendations to agent outcomes:

1. Did recommended agent succeed?
2. Was upgrade/downgrade justified?
3. Which agents have highest success rate for which tasks?
4. Optimize routing based on empirical performance data

---

## Documentation Updates Needed

1. **README.md**: Add "Visibility Features" section
2. **Architecture.md**: Document Option D implementation
3. **CLAUDE.md Template**: Update with advisory routing guidance
4. **Metrics Guide**: Document new metrics collection

---

## Summary

**Option D provides**:
- ✅ Full visibility into routing decisions
- ✅ Advisory recommendations (not mandatory)
- ✅ Real metrics collection
- ✅ User confidence through transparency
- ✅ Claude retains agency and context awareness
- ✅ Foundation for continuous improvement

**Next steps**:
1. Test in real usage
2. Collect metrics
3. Monitor compliance rate
4. Iterate on escalation triggers
5. Add compliance tracking (Phase 2)
