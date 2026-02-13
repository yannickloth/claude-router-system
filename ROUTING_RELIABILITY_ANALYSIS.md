# Routing System Reliability Analysis

**Date:** 2026-02-13
**Issue:** Requests not being reliably analyzed for complexity and routed to appropriate agents
**Status:** System is producing recommendations but main Claude is not following them

---

## Executive Summary

The routing system IS working at the technical level (hooks execute, recommendations generate, metrics log), but **main Claude is not following the routing directives** despite explicit MANDATORY language in both the hook output and CLAUDE.md instructions.

**Root cause:** Gap between directive generation and directive execution - the routing recommendation reaches Claude but isn't being acted upon reliably.

---

## Evidence of Technical Functionality

### 1. Hook Execution: ✅ WORKING

```bash
$ echo "test request" | user-prompt-submit.sh
[ROUTER] Recommendation: escalate (confidence: 1.0)
[ROUTER] Reason: No clear agent match - needs intelligent routing

<routing-recommendation request-hash="55800af817e36f5a">
ROUTING DIRECTIVE - MANDATORY ACTION REQUIRED. No interpretation allowed.
...
IF decision == "escalate": Invoke infolead-claude-subscription-router:router agent
```

- Hook executes successfully
- Generates routing recommendations
- Outputs to both stderr (visible to user) and stdout (injected into Claude context)

### 2. Metrics Collection: ✅ WORKING

**Location:** `~/.claude/infolead-claude-subscription-router/metrics/2026-02-13.jsonl`

**Today's activity:**
- 15 escalation decisions recorded
- 0 direct routing decisions
- Metrics logged consistently with timestamps, request hashes, full analysis

### 3. Routing Logic: ✅ WORKING

**Analysis of escalation reasons (today):**
```
9 requests: "Low confidence match (0.60) - needs verification"
2 requests: "Request contains complexity signal keywords"
2 requests: "Creation/design tasks require planning and judgment"
1 request:  "No clear agent match - needs intelligent routing"
1 request:  "Low confidence match (0.70) - needs verification"
```

The routing logic is correctly identifying:
- Low-confidence matches (below 0.8 threshold)
- Complexity signals
- Creation/design tasks
- Ambiguous requests

### 4. Agent Registry: ✅ EXISTS

**Available agents:**
- `router.md` - Entry point for routing decisions (Sonnet)
- `router-escalation.md` - Complex routing decisions (Opus)
- `work-coordinator.md` - Multi-task coordination (Sonnet)
- `strategy-advisor.md` - Execution strategy selection (Sonnet)
- Plus haiku-pre-router, probabilistic-router, planner, temporal-scheduler

---

## The Gap: Directive Execution

### What SHOULD Happen

1. User submits request
2. UserPromptSubmit hook executes
3. Hook outputs routing directive to stdout (injected into Claude's context)
4. Main Claude sees `<routing-recommendation>` with MANDATORY directive
5. Main Claude IMMEDIATELY invokes the specified agent (router or direct agent)
6. NO clarifying questions, NO hesitation, NO override

### What ACTUALLY Happens

1. ✅ User submits request
2. ✅ UserPromptSubmit hook executes
3. ✅ Hook outputs routing directive
4. ❓ Main Claude sees directive... but then what?
5. ❌ Main Claude often handles request directly OR asks questions OR applies own judgment
6. ❌ Routing directive is ignored or treated as "advisory"

### Why This Matters

**From MEMORY.md:**
> "Router System - Now Mandatory (v1.4.1)
> Changed from advisory to mandatory routing - routing directives are binding, non-negotiable"

The system was explicitly upgraded from "advisory" to "mandatory" but the execution gap remains.

---

## Root Cause Analysis

### Problem 1: Directive Recognition

**Question:** Does main Claude reliably see and recognize the `<routing-recommendation>` block?

**Evidence needed:**
- Check if routing directive appears in system messages
- Verify XML tag is being parsed correctly
- Confirm no truncation of hook output

### Problem 2: Instruction Priority

**Current state:**
- Global `~/.claude/CLAUDE.md` says routing directives are MANDATORY
- Project `.claude/CLAUDE.md` reinforces this with CRITICAL/NON-NEGOTIABLE language
- Hook output includes "MANDATORY ACTION REQUIRED"

**But:** Main Claude has conflicting instructions:
- "Answer user's request using tools"
- "Be thorough, check multiple locations"
- "Never create files unless necessary"
- etc.

**Conflict:** When faced with a request + routing directive + general instructions, which takes precedence?

### Problem 3: Circular Dependency

**The meta-problem:**

```
User Request
    ↓
Hook says: "Escalate to router agent"
    ↓
Main Claude thinks: "Should I route this? Let me analyze..."
    ↓
Main Claude decides: "I'll handle it directly" OR "Let me ask a question"
    ↓
Routing directive ignored
```

**Why this happens:** Main Claude is ITSELF acting as a router, even when told not to.

### Problem 4: Low Confidence Threshold

**Current behavior:**
- Keyword matching has 0.8 confidence threshold
- Most matches fall at 0.6-0.7 (below threshold)
- Result: Most requests escalate with "low confidence match"

**From routing_core.py line 434:**
```python
confidence_threshold = 0.7 if USE_LLM_ROUTING else 0.8

if confidence < confidence_threshold:
    return RoutingResult(
        decision=RouterDecision.ESCALATE_TO_SONNET,
        agent=matched_agent,
        reason=f"Low confidence match ({confidence:.2f}) - needs verification",
        confidence=confidence
    )
```

**Issue:** Conservative thresholds cause too many escalations, which may train main Claude to ignore directives as "too cautious".

### Problem 5: LLM Routing Disabled

**From routing_core.py line 302:**
```python
USE_LLM_ROUTING = os.environ.get("ROUTER_USE_LLM", "0") == "1"
```

**Current state:** LLM routing is OFF (defaults to "0")

**Impact:**
- Falls back to keyword matching (less accurate)
- Lower confidence scores
- More escalations
- Less trust in routing decisions

---

## Solutions Ranked by Impact

### 1. Enable LLM-Based Routing (HIGHEST IMPACT)

**Action:**
```bash
export ROUTER_USE_LLM=1
```

**Why this helps:**
- Uses Claude Haiku for semantic understanding
- More accurate agent matching
- Higher confidence scores (uses 0.7 threshold vs 0.8)
- Better handling of ambiguous requests

**Trade-off:**
- Adds ~1-2s latency per request (Haiku API call)
- Adds minor cost (~$0.0001 per request)

**Recommendation:** Enable immediately - the accuracy gain is worth the cost.

### 2. Add Routing Verification Step (HIGH IMPACT)

**Change:** Modify hook to require explicit acknowledgment

**Implementation:**
```bash
# In user-prompt-submit.sh, add:
cat <<EOF

ROUTING ACK REQUIRED:
You MUST respond with one of these exact phrases before any other output:
- "ROUTING: Escalating to router agent"
- "ROUTING: Direct to [agent-name]"

Failure to acknowledge routing will result in request rejection.
EOF
```

**Why this helps:**
- Forces main Claude to explicitly acknowledge directive
- Makes it impossible to "accidentally" ignore routing
- Creates audit trail of routing acknowledgment

### 3. Implement Router-Only Mode (MEDIUM-HIGH IMPACT)

**Concept:** Main Claude NEVER handles requests directly - always routes

**Implementation:**
1. Add to global CLAUDE.md:
```markdown
## Mandatory Routing Protocol

YOU ARE NOT ALLOWED TO HANDLE USER REQUESTS DIRECTLY.

For EVERY user request, you MUST:
1. Wait for UserPromptSubmit hook output
2. Read the routing recommendation
3. Invoke the specified agent IMMEDIATELY
4. NO exceptions, NO questions, NO direct handling

Your ONLY role is routing execution, not task execution.
```

2. Remove tool access from main Claude (except Task tool)

**Why this helps:**
- Eliminates conflicting instructions
- Makes routing the ONLY option
- Clear separation of concerns

**Trade-off:** Breaks ability to have "simple conversations" with Claude directly

### 4. Lower Confidence Threshold (MEDIUM IMPACT)

**Change:** Adjust keyword matching threshold from 0.8 to 0.6

**In routing_core.py:**
```python
confidence_threshold = 0.7 if USE_LLM_ROUTING else 0.6  # was 0.8
```

**Why this helps:**
- More direct routing decisions
- Fewer unnecessary escalations
- Builds trust in routing system

**Trade-off:** Slightly higher risk of incorrect routing

### 5. Add Work-Coordinator as Default Escalation (MEDIUM IMPACT)

**Current:** Escalations go to generic "router" agent

**Proposed:** Escalations go to "work-coordinator" which:
- Breaks request into tasks
- Assigns to appropriate agents
- Tracks completion
- Ensures nothing is dropped

**Why this helps:**
- work-coordinator is designed for exactly this use case
- Built-in task tracking and WIP limits
- Better handling of complex multi-step requests

### 6. Add Routing Metrics Dashboard (LOW-MEDIUM IMPACT)

**Create monitoring tool:**
```bash
python3 -m routing_metrics --summary
```

**Output:**
```
Routing Metrics (Last 7 Days)
============================
Total requests: 247
  - Direct routing: 42 (17%)
  - Escalations: 205 (83%)

Escalation reasons:
  - Low confidence: 156 (76%)
  - Complexity signals: 28 (14%)
  - Multiple objectives: 12 (6%)
  - No clear match: 9 (4%)

Recommendation: Enable LLM routing to improve direct routing rate
```

**Why this helps:**
- Visibility into routing behavior
- Identify patterns in escalations
- Track improvement over time

---

## Recommended Action Plan

### Phase 1: Quick Wins (Immediate)

1. **Enable LLM routing:**
   ```bash
   echo 'export ROUTER_USE_LLM=1' >> ~/.bashrc
   source ~/.bashrc
   ```

2. **Lower confidence threshold:**
   Edit `routing_core.py` line 434 to use 0.6 threshold

3. **Test routing improvements:**
   - Submit 10 test requests
   - Verify higher direct routing rate
   - Check metrics show improved confidence

### Phase 2: Enforcement (1-2 days)

1. **Add routing verification step** to hook output
2. **Update CLAUDE.md** with router-only protocol
3. **Remove non-routing tools** from main Claude config (optional)

### Phase 3: Monitoring (Ongoing)

1. **Create metrics dashboard** script
2. **Track routing reliability** over time
3. **Tune thresholds** based on observed behavior

---

## Specific Routing Recommendation

**For this meta-request about routing reliability:**

**Agent:** `work-coordinator`

**Reason:**
- This is a multi-faceted problem requiring investigation, analysis, and implementation
- work-coordinator can break into tasks:
  1. Enable LLM routing and test
  2. Modify hook for acknowledgment requirement
  3. Update CLAUDE.md with router-only protocol
  4. Create metrics dashboard
  5. Monitor and tune over 1 week
- Needs task tracking to ensure all improvements are completed
- Requires coordination across multiple files and systems

**Confidence:** 0.95

**Decision:** DIRECT (work-coordinator is the right agent for this specific request)

---

## Success Metrics

**How to measure if routing reliability improves:**

1. **Direct routing rate:** Should increase from 0% to 40-60%
2. **Low confidence escalations:** Should decrease from 60% to <20%
3. **User satisfaction:** "Claude understood what I wanted and used the right agent"
4. **Completion rate:** Tasks don't get dropped or forgotten
5. **Routing acknowledgment:** 100% of requests show explicit routing decision

**Target state:** Every request gets analyzed → correct agent assigned → task completed with no manual intervention needed.

---

## Appendix: Current System State

**Plugin version:** 1.4.0
**Hooks installed:** ✅ UserPromptSubmit, SubagentStart, SubagentStop, SessionStart, SessionEnd, PreToolUse, PostToolUse
**LLM routing:** ❌ Disabled (ROUTER_USE_LLM=0)
**Confidence threshold:** 0.8 (keyword) / 0.7 (LLM)
**Today's requests:** 15 analyzed, 15 escalated (100%), 0 direct
**Metrics collection:** ✅ Working
**Available agents:** 8 defined in plugin

**Conclusion:** System is technically sound but execution gap prevents reliable routing. Solutions available and prioritized above.
