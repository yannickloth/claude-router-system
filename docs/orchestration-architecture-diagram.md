# Orchestration Architecture - Visual Diagrams

**Date:** 2026-02-13
**Purpose:** Visual reference for understanding the architectural differences

---

## Current System: Directive-Based Routing

```
┌─────────────────────────────────────────────────────────────┐
│                        USER REQUEST                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│             UserPromptSubmit Hook (Bash)                    │
│                                                              │
│  1. Read user request                                       │
│  2. Call routing_core.py                                    │
│  3. Generate routing recommendation                         │
│  4. Output to stdout (injected into Claude's context)       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     MAIN CLAUDE AGENT                       │
│                                                              │
│  Context includes:                                          │
│  - User request                                             │
│  - Routing recommendation (as system message)               │
│  - "MANDATORY ACTION REQUIRED" directive                    │
│                                                              │
│  Claude reads directive and decides:                        │
│  - Follow it? (40-60% compliance) ❌                        │
│  - Ignore it? (40-60% of the time)                         │
│  - Apply own judgment                                       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
        ┌──────────────┐        ┌──────────────┐
        │  Follows     │        │  Ignores     │
        │  Directive   │        │  Directive   │
        │  (40-60%)    │        │  (40-60%)    │
        └──────────────┘        └──────────────┘
           Correct                   Wrong
           routing                  routing
```

**Problems:**
- ❌ Non-deterministic - Claude decides whether to follow
- ❌ Low compliance (40-60%)
- ❌ Defeats purpose of mechanical routing
- ❌ Metrics show frequent violations

---

## Proposed System: Orchestration-Based Routing

```
┌─────────────────────────────────────────────────────────────┐
│                        USER REQUEST                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestration Script (Python)                  │
│               RUNS OUTSIDE CLAUDE CONTEXT                   │
│                                                              │
│  1. Receive user request                                    │
│  2. Call routing_core.py --json                             │
│  3. Parse routing decision                                  │
│  4. ENFORCE decision by spawning chosen agent               │
│  5. Monitor execution                                       │
│  6. Capture result                                          │
│  7. Handle escalation if needed                             │
│  8. Record metrics (100% compliance by design)              │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│subprocess.run│    │subprocess.run│    │subprocess.run│
│ ['claude',   │    │ ['claude',   │    │ ['claude',   │
│  '--model',  │    │  '--model',  │    │  '--model',  │
│  'haiku']    │    │  'sonnet']   │    │  'opus']     │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Haiku Agent  │    │Sonnet Agent  │    │ Opus Agent   │
│              │    │              │    │              │
│ Executes     │    │ Executes     │    │ Executes     │
│ request      │    │ request      │    │ request      │
│              │    │              │    │              │
│ (Never sees  │    │ (Never sees  │    │ (Never sees  │
│  routing     │    │  routing     │    │  routing     │
│  decision)   │    │  decision)   │    │  decision)   │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Result     │
                    │  captured    │
                    │   by script  │
                    └──────────────┘
```

**Advantages:**
- ✅ Deterministic - script enforces routing
- ✅ 100% compliance by design
- ✅ Agent never sees routing decision
- ✅ External control over execution
- ✅ Complete metrics capture

---

## Hybrid System: Context-Aware Mode Selection

```
┌─────────────────────────────────────────────────────────────┐
│                        USER REQUEST                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Context Detection                        │
│                                                              │
│  Checks:                                                    │
│  - Is interactive? (stdin.isatty())                         │
│  - Is overnight? (time >= 22:00 or <= 06:00)               │
│  - Is batch? (BATCH_MODE env var)                          │
│  - Is API call? (API_REQUEST env var)                      │
│  - Has workflow chain? (workflow file exists)               │
│  - User preference? (settings.json)                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│   DIRECTIVE MODE      │       │  ORCHESTRATION MODE   │
│   (Interactive)       │       │   (Automated)         │
└───────────┬───────────┘       └───────────┬───────────┘
            │                               │
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│  user-prompt-         │       │  orchestrate-         │
│  submit.sh            │       │  request.py           │
│                       │       │                       │
│  - Generate directive │       │  - Enforce routing    │
│  - Inject into        │       │  - Spawn agent        │
│    Claude context     │       │  - Monitor execution  │
│  - Claude decides     │       │  - Capture result     │
└───────────┬───────────┘       └───────────┬───────────┘
            │                               │
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│   Main Claude         │       │  Spawned Agent        │
│   (Flexible)          │       │  (Controlled)         │
│                       │       │                       │
│   40-60% compliance   │       │  100% compliance      │
└───────────────────────┘       └───────────────────────┘

     Better UX                      Better Compliance
     User override                  Deterministic
     Natural flow                   Reliable automation
```

**Decision Logic:**

```python
def select_mode(context):
    # Priority 1: Explicit user preference
    if context.user_specified_mode:
        return context.user_specified_mode

    # Priority 2: Automated workflows
    if context.is_overnight:
        return 'orchestration'
    if context.is_batch:
        return 'orchestration'
    if context.is_api_request:
        return 'orchestration'

    # Priority 3: Complex workflows
    if context.has_workflow_chain:
        return 'orchestration'

    # Priority 4: Compliance-critical tasks
    if context.requires_high_compliance:
        return 'orchestration'

    # Default: Interactive directive mode
    return 'directive'
```

---

## Data Flow Comparison

### Directive Mode: Information Flow

```
User Request
    │
    ├─→ Hook (bash) ──→ routing_core.py ──→ Recommendation
    │                                              │
    │                                              ▼
    └──────────────────────────────────→ Claude Context
                                              │
                                              ▼
                                         Claude decides
                                              │
                        ┌─────────────────────┴─────────────────────┐
                        ▼                                           ▼
                   Follows directive                          Ignores directive
                   (40-60% of time)                          (40-60% of time)
```

### Orchestration Mode: Control Flow

```
User Request
    │
    ▼
Orchestration Script (Python)
    │
    ├─→ routing_core.py ──→ Routing Decision
    │                              │
    │                              ▼
    │                       Parse decision
    │                              │
    │                              ▼
    └─→ subprocess.run(['claude', '--model', MODEL])
                    │
                    ▼
              Spawned Agent
              (Executes request)
              (No routing decision visible)
                    │
                    ▼
              Result captured
                    │
                    ▼
         Script returns result
        (100% compliance guaranteed)
```

---

## State Management Architecture

### Current: In-Memory State (Lost After Session)

```
┌──────────────┐
│   Session 1  │
│              │
│ - Search A   │
│ - Analysis X │
│ - Decision Y │
└──────────────┘
       │
       ▼
  Session ends
       │
       ▼
   State LOST ❌
       │
       ▼
┌──────────────┐
│   Session 2  │
│              │
│ - Re-search A │ ← Duplicate work!
│ - Re-analysis │
└──────────────┘
```

### Proposed: Persistent State (Cross-Session Continuity)

```
┌──────────────┐
│   Session 1  │
│              │
│ - Search A   │──┐
│ - Analysis X │  │
│ - Decision Y │  │
└──────────────┘  │
                  │
                  ▼
        ┌──────────────────┐
        │  State File      │
        │  (JSON/JSONL)    │
        │                  │
        │  - routing_hist  │
        │  - cached_results│
        │  - work_queue    │
        │  - context       │
        └──────────────────┘
                  │
                  ▼
┌──────────────┐  │
│   Session 2  │  │
│              │◄─┘
│ - Load state │
│ - Reuse A    │ ← No duplicate work! ✅
│ - Continue   │
└──────────────┘
```

**State Schema:**

```json
{
  "session_id": "20260213-143000",
  "routing_history": [
    {"request": "...", "agent": "sonnet", "result": "success"}
  ],
  "cached_results": {
    "search_hash_abc": {
      "query": "mitochondria research",
      "results": [...],
      "timestamp": "2026-02-13T14:30:00Z"
    }
  },
  "work_queue": [],
  "context": {
    "active_files": ["chapter-3.tex"],
    "recent_edits": [...],
    "user_preferences": {}
  }
}
```

---

## Agent Chaining Architecture

### Current: Single-Agent Execution

```
User: "Search for papers and analyze them"
    │
    ▼
┌──────────────┐
│ Main Claude  │
│              │
│ 1. Search    │
│ 2. Analyze   │
│              │
│ (All in one  │
│  agent call) │
└──────────────┘

Problems:
- ❌ Can't optimize each step separately
- ❌ Failure means restart everything
- ❌ No intermediate checkpointing
- ❌ Wrong model tier for all steps
```

### Proposed: Multi-Agent Workflow

```
User: "Search for papers and analyze them"
    │
    ▼
Orchestration Script
    │
    ├─→ Step 1: Search (Haiku agent)
    │       │
    │       ▼
    │   Execute search
    │       │
    │       ▼
    │   Save results to file ✅
    │       │
    │       ▼
    ├─→ Step 2: Analyze (Sonnet agent)
    │       │
    │       ▼
    │   Load search results
    │       │
    │       ▼
    │   Execute analysis
    │       │
    │       ▼
    │   Save analysis to file ✅
    │       │
    │       ▼
    └─→ Step 3: Report (Haiku agent)
            │
            ▼
        Load analysis
            │
            ▼
        Format report
            │
            ▼
        Return to user

Advantages:
- ✅ Right model for each step (cost optimization)
- ✅ Checkpointing at each step
- ✅ Resumable on failure
- ✅ Results reusable across sessions
```

**Workflow Definition (YAML):**

```yaml
workflow:
  name: "research-pipeline"
  steps:
    - id: search
      agent: haiku-general
      prompt: "Search arxiv for: {topic}"
      output: search_results.json
      timeout: 300

    - id: analyze
      agent: sonnet-general
      depends_on: [search]
      prompt: "Analyze papers in {search_results}"
      output: analysis.md
      timeout: 1800

    - id: report
      agent: haiku-general
      depends_on: [analyze]
      prompt: "Format report from {analysis}"
      output: report.pdf
      timeout: 300
```

---

## Metrics & Observability

### Current: Limited Metrics

```
┌──────────────┐
│ Hook outputs │
│ recommenda-  │
│ tion to      │
│ stderr       │
└──────┬───────┘
       │
       ▼
User sees: "[ROUTER] Recommendation: sonnet"
       │
       ▼
┌──────────────┐
│ Main Claude  │
│ executes     │
│ (maybe with  │
│  sonnet,     │
│  maybe not)  │
└──────┬───────┘
       │
       ▼
    Result
       │
       ▼
No compliance tracking ❌
No execution metrics ❌
Can't measure if directive followed ❌
```

### Proposed: Complete Observability

```
┌──────────────┐
│ Orchestration│
│ Script       │
└──────┬───────┘
       │
       ├─→ METRICS.jsonl (append)
       │   {
       │     "type": "routing_decision",
       │     "request_hash": "abc123",
       │     "decision": "sonnet",
       │     "confidence": 0.95,
       │     "timestamp": "..."
       │   }
       │
       ├─→ METRICS.jsonl (append)
       │   {
       │     "type": "agent_execution",
       │     "agent": "sonnet-general",
       │     "exit_code": 0,
       │     "duration_ms": 4523,
       │     "compliance": true,
       │     "timestamp": "..."
       │   }
       │
       └─→ METRICS.jsonl (append)
           {
             "type": "orchestration_complete",
             "request_hash": "abc123",
             "routing_compliance": true, ✅
             "total_duration_ms": 4721,
             "timestamp": "..."
           }

Can now measure:
✅ Routing compliance (100%)
✅ Execution duration
✅ Agent performance
✅ Error rates
✅ Quota utilization
```

---

## Summary: Why This Architecture Works

### Separation of Concerns

```
┌─────────────────────────────────────────────────────────────┐
│                  ROUTING LOGIC LAYER                        │
│                  (routing_core.py)                          │
│                                                              │
│  Responsibility: Decide which agent should handle request   │
│  Change driver: Routing rules, agent capabilities           │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATION LAYER (NEW)                      │
│              (orchestrate-request.py)                       │
│                                                              │
│  Responsibility: Enforce routing decision                   │
│  Change driver: Coordination patterns, state management     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  EXECUTION LAYER                            │
│                  (Claude agents)                            │
│                                                              │
│  Responsibility: Execute user request                       │
│  Change driver: Task requirements, domain knowledge         │
└─────────────────────────────────────────────────────────────┘
```

**Each layer:**
- ✅ Has single responsibility
- ✅ Changes for different reasons
- ✅ Can be tested independently
- ✅ Follows Independent Variation Principle (IVP)

**Benefits:**
- ✅ Routing logic stays mechanical and testable
- ✅ Orchestration handles coordination concerns
- ✅ Agents focus on task execution
- ✅ Clean separation enables hybrid mode
- ✅ Each layer optimized for its purpose

---

**Conclusion:** The orchestration architecture provides deterministic routing where needed (automation) while preserving flexibility where valued (interaction), achieving the best of both approaches through clean separation of concerns.
