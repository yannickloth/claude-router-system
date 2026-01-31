# Implementation Prompt: New Router Architecture

**Project:** claude-router-system
**Task:** Implement new router architecture with Haiku pre-routing and work coordination
**Context:** Replacing existing agent architecture (safely committed at c676a34)

---

## Executive Summary

Implement a new Claude Code router architecture that achieves:
- **60-70% quota savings** through Haiku pre-routing
- **90%+ task completion rate** through WIP-limited work coordination
- **Multi-domain optimization** (LaTeX research, software dev, knowledge management)

The complete architectural specification is in `docs/claude-code-architecture.md`.

---

## Project Context

**Repository:** `/home/nicky/code/claude-router-system`

**Current State:**
- Existing router system committed at `c676a34`
- Safe to override existing `agents/` directory
- Documentation available in `docs/` folder

**Key Documentation:**
- `docs/claude-code-architecture.md` - Complete architecture specification
- `docs/claude-code-subscription-model.md` - Quota optimization mathematics
- `docs/claude-code-cost-model.md` - API cost analysis
- `README.md` - Plugin overview
- `EXAMPLE.claude.md` - Example configuration

**Subscription Context:**
- User has Claude Code Max (5x)
- Daily quotas: 1,125 Sonnet, 250 Opus, unlimited Haiku
- Goal: Maximize effective work output within quotas

---

## Implementation Task

### Phase 1: Core Router Infrastructure (Priority 1)

Implement the foundational routing system with Haiku pre-routing.

#### 1.1 Haiku Pre-Router Agent

**File:** `agents/haiku-pre-router.md`

**Requirements:**
- Model: Haiku
- Tools: Read, Glob, Grep, Task
- Implements mechanical escalation checklist with 8 triggers
- Escalates to `router` (Sonnet) when complexity detected
- Direct routes to specialized agents when safe

**Escalation Triggers (ANY true → escalate):**
1. Judgment keywords: "complex", "best", "should I", "recommend", "design", "architecture"
2. Destructive + bulk: "delete"/"remove" + "all"/"multiple"/"*"
3. File operation without explicit path
4. Modifying `.claude/agents/` files
5. Multiple objectives (≥2 "and"/"then")
6. New/novel work: "new", "create", "design"
7. No clear agent match OR confidence <80%
8. Request about routing itself

**Output Format:**
- If escalating: Clear message with reason and context
- If direct routing: Route to most specific agent

**Reference:** See `docs/claude-code-architecture.md` section "Solution 1: Haiku Reliable Routing"

#### 1.2 Main Router Agent (Sonnet)

**File:** `agents/router.md`

**Requirements:**
- Model: Sonnet
- Tools: Read, Glob, Grep, Task
- Handles escalations from Haiku pre-router
- Handles complex routing decisions
- Implements domain classification
- Risk assessment for destructive operations

**Decision Flow:**
1. Parse intent and assess risk
2. Classify domain (LaTeX / Dev / Knowledge / General)
3. Match to specialized agents (if available)
4. Select model tier (Haiku / Sonnet / Opus)
5. Route to appropriate agent
6. Verify agent produces output

**Domain Detection:**
- LaTeX: `.tex` files, `nix build`, research citations
- Dev: Code files, tests, git operations
- Knowledge: Notes, markdown, organization tasks
- General: Everything else

**Reference:** See `docs/claude-code-architecture.md` section "Solution 3: Multi-Domain Adaptive Architecture"

#### 1.3 Router Escalation Agent (Opus)

**File:** `agents/router-escalation.md`

**Requirements:**
- Model: Opus
- Tools: Read, Glob, Grep, Task
- Handles edge cases where Sonnet router is uncertain
- Deep reasoning about ambiguous requests
- Makes routing decision and spawns agent directly

**When to Use:**
- Genuinely ambiguous scope
- Unusual phrasing that could mask destructive intent
- Hidden complexity in seemingly simple requests
- High-stakes decisions requiring deep reasoning

**Reference:** See global `~/.claude/CLAUDE.md` routing rules

### Phase 2: Work Coordination (Priority 2)

Implement WIP-limited work coordination to ensure task completion.

#### 2.1 Work Coordinator Agent

**File:** `agents/work-coordinator.md`

**Requirements:**
- Model: Sonnet
- Tools: Read, Write, Bash, Task
- Manages work queue with WIP limits (default: 3)
- Priority-based scheduling
- Dependency tracking
- Progress monitoring

**State File:** `/tmp/work-queue.json`

**Data Structure:**
```json
{
  "wip_limit": 3,
  "active": [
    {
      "id": "w1",
      "description": "Task description",
      "agent": "agent-name",
      "priority": 8,
      "started": "2026-01-31T10:00:00Z",
      "estimated_complexity": 3
    }
  ],
  "queued": [
    {
      "id": "w2",
      "description": "Task description",
      "priority": 6,
      "dependencies": ["w1"],
      "estimated_complexity": 2
    }
  ],
  "completed": ["w0"]
}
```

**Scheduling Algorithm:**
1. Check WIP capacity (active < wip_limit)
2. Select highest-priority eligible work (dependencies satisfied)
3. Prioritize work that unblocks others
4. Start work and update state
5. Monitor progress and detect stalls

**User Interface:**
```
📊 Work Status
═══════════════

Active (2/3):
  ⏳ [w1] Task description (agent-name, 15m elapsed)
  ⏳ [w2] Task description (agent-name, 8m elapsed)

Queued (2):
  📋 [w3] Priority 8 - Task description (blocked: needs w1)
  📋 [w4] Priority 6 - Task description

Completed (1):
  ✅ [w0] Task description
```

**Reference:** See `docs/claude-code-architecture.md` section "Solution 2: Parallel Work with Completion Guarantees"

#### 2.2 Adaptive WIP Adjustment

**Integration into Work Coordinator:**

Track metrics:
- Completion rate (tasks/hour)
- Stall rate (tasks stalled >1h / total tasks)

Adjust WIP limit:
- Stall rate >30% → WIP = 1 (focus mode)
- Completion rate >2.0 AND stall rate <10% → WIP = 4 (high throughput)
- Otherwise → WIP = 3 (balanced default)

### Phase 3: Domain-Specific Optimization (Priority 3)

Implement domain-specific configurations and rules.

#### 3.1 Domain Configurations

**Create files in:** `config/domains/`

- `config/domains/latex-research.yaml`
- `config/domains/software-dev.yaml`
- `config/domains/knowledge-mgmt.yaml`

**Configuration Schema:**
```yaml
domain: latex-research
workflows:
  literature_integration:
    phases: ["search", "assess", "integrate", "verify"]
    quality_gates: ["build_check", "citation_verify", "link_check"]
    parallelism: "low"  # 1-2 concurrent
  formalization:
    phases: ["analyze", "model", "verify", "document"]
    quality_gates: ["math_verify", "logic_audit"]
    parallelism: "sequential"
  bulk_editing:
    phases: ["propose", "review", "apply"]
    quality_gates: ["build_check", "diff_review"]
    parallelism: "high"  # 3-4 concurrent

default_agents:
  syntax: "haiku-general"
  integration: "sonnet + specialized"
  verification: "opus (math/logic)"

context_strategy:
  large_files: "split_into_chapters"
  citations: "lazy_load_bibtex"
  cross_references: "index_based"
```

**Reference:** See `docs/claude-code-architecture.md` domain configurations

#### 3.2 Rules Engine

**Create files in:** `config/rules/`

- `config/rules/global.yaml` (always applied)
- `config/rules/latex-research.yaml`
- `config/rules/software-dev.yaml`
- `config/rules/knowledge-mgmt.yaml`

**LaTeX Research Rules Example:**
```yaml
rules:
  quality_gates:
    - name: "Build verification required"
      trigger: "after_file_edit"
      condition: "file.endswith('.tex')"
      action: "run_nix_build"
      blocking: true

    - name: "Citation integrity check"
      trigger: "after_citation_add"
      condition: "text.contains('\\cite{')"
      action: "verify_bibtex_entry_exists"
      blocking: true

  agent_constraints:
    - name: "Haiku not for medical content"
      condition: "file.contains('appendix-i') or file.contains('case-data')"
      constraint: "min_model = sonnet"
      reason: "Medical content requires careful judgment"

    - name: "Opus for formalization"
      condition: "task.contains('formalize') or task.contains('causal model')"
      constraint: "required_model = opus"
      reason: "Formalization requires deep reasoning"

  context_optimization:
    - name: "Chapter-based context loading"
      condition: "file.size > 100KB"
      action: "load_by_chapter"
      parameters:
        max_chapters_in_context: 3
```

### Phase 4: Supporting Infrastructure (Priority 4)

Implement hooks, memory system, and monitoring.

#### 4.1 Hooks

**Create in:** `hooks/`

**Haiku Routing Audit Hook:** `hooks/haiku-routing-audit.sh`
```bash
#!/bin/bash
# Monitors Haiku routing decisions

HAIKU_LOG="/tmp/haiku-routing-decisions.log"
echo "$(date): $REQUEST → $AGENT" >> "$HAIKU_LOG"

# Check for potential mis-routes
if [[ "$AGENT" == "haiku-general" ]] && [[ "$REQUEST" == *"delete"* ]]; then
    echo "⚠️  WARNING: Haiku routed deletion to haiku-general"
    echo "   Request: $REQUEST"
fi

# Weekly audit
if [ "$(date +%u)" -eq 1 ]; then
    echo "📊 Weekly Haiku Routing Audit:"
    echo "   Total routes: $(wc -l < "$HAIKU_LOG")"
    echo "   Escalations: $(grep -c "ESCALATING" "$HAIKU_LOG")"
fi
```

**Session Memory Hook:** `hooks/load-session-memory.sh`
```bash
#!/bin/bash
# Loads session memory at startup

MEMORY_DIR="$HOME/.claude/memory"
ACTIVE_CONTEXT="$MEMORY_DIR/active-context.json"

if [ -f "$ACTIVE_CONTEXT" ]; then
    echo "📂 Loading session memory..."
    FOCUS=$(jq -r '.active_context.current_focus' "$ACTIVE_CONTEXT")
    WIP_COUNT=$(jq '.active_context.work_in_progress | length' "$ACTIVE_CONTEXT")
    echo "   Current focus: $FOCUS"
    echo "   Work in progress: $WIP_COUNT tasks"
fi
```

#### 4.2 Memory System

**Create directory:** `~/.claude/memory/`

**Files:**
- `active-context.json` - Current WIP
- `completed-work.json` - Recent completions
- `domain-preferences.json` - User preferences per domain
- `session-continuations.json` - Session links

**Schema:** See `docs/claude-code-architecture.md` memory system section

#### 4.3 Context Manager

**Utility script:** `scripts/context-manager.py`

Implements:
- Lazy loading with LRU cache
- Metadata indexing
- Section-level file loading
- Context budget management (50k tokens for context, 150k for conversation)

**Reference:** See `docs/claude-code-architecture.md` lazy loading section

---

## Implementation Strategy

### Recommended Approach

**Option A: Incremental (Lower Risk)**
1. Implement Phase 1 (core routing)
2. Test with real requests
3. Add Phase 2 (work coordination)
4. Test completion rates
5. Add Phase 3-4 (domains, rules, infrastructure)

**Option B: Complete Rewrite (Faster)**
1. Study all documentation in `docs/`
2. Implement all phases at once
3. Comprehensive testing
4. Single large commit

**Recommendation:** Option A (incremental) for production stability

### Testing Requirements

**Must test:**
1. Haiku escalation accuracy (target: 30-40% escalation rate)
2. Work coordinator prevents >3 concurrent tasks
3. Domain detection works correctly
4. Rules enforce quality gates
5. Quota savings measurable

**Test Cases:**
- Simple request → Haiku direct route (0 Sonnet quota)
- Complex request → Haiku escalates to Sonnet
- Destructive request → Proper risk assessment
- Multiple tasks → WIP limiting works
- LaTeX file edit → Build verification runs
- Domain switching → Correct config loaded

### Success Metrics

**Quantitative:**
- Routing quota savings: >50% in Week 1, >60% by Week 2
- Task completion rate: >80% in Week 1, >90% by Week 2
- Quality issues (build breaks): <5% by Week 2
- Context size reduction: >30% through lazy loading

**Qualitative:**
- User reports faster workflows
- Fewer abandoned tasks
- Quota lasts through full work day
- High-quality outputs with fewer errors

---

## Critical Implementation Notes

### 1. Haiku Escalation Checklist

**CRITICAL:** The checklist must be mechanically executable. Don't ask Haiku to "judge" or "assess" - give it pattern matching.

✅ **Good:** `if "complex" in request or "design" in request → escalate`

❌ **Bad:** `if request seems complex → escalate`

### 2. WIP Limit Enforcement

**CRITICAL:** Work coordinator must PREVENT starting new work when at limit, not just warn.

✅ **Good:** `if active_count >= wip_limit: return None  # Cannot start`

❌ **Bad:** `if active_count >= wip_limit: print("Warning")  # Still starts`

### 3. Output Verification

**CRITICAL:** Every agent must produce verifiable output. Router must check.

✅ **Good:** Agent returns file path OR results OR status report

❌ **Bad:** Agent completes silently with no indication of what was done

### 4. Domain Rules Enforcement

**CRITICAL:** Rules must override agent suggestions, not just recommend.

✅ **Good:** `if rule.requires_opus: agent = "opus-general"  # Forced`

❌ **Bad:** `if rule.prefers_opus: suggest("Consider opus")  # Optional`

### 5. Memory Persistence

**CRITICAL:** Session-end hook may not fire. Need daily backup.

✅ **Good:** Cron job backups + session-end hook

❌ **Bad:** Rely only on session-end hook

---

## File Structure

After implementation, the project should look like:

```
claude-router-system/
├── agents/
│   ├── haiku-pre-router.md          # NEW: Mechanical pre-router
│   ├── router.md                     # UPDATED: Sonnet router with domain detection
│   ├── router-escalation.md          # NEW: Opus edge case handler
│   ├── work-coordinator.md           # NEW: WIP-limited coordination
│   └── [other specialized agents]
├── config/
│   ├── domains/
│   │   ├── latex-research.yaml       # NEW: LaTeX domain config
│   │   ├── software-dev.yaml         # NEW: Dev domain config
│   │   └── knowledge-mgmt.yaml       # NEW: KM domain config
│   └── rules/
│       ├── global.yaml               # NEW: Global rules
│       ├── latex-research.yaml       # NEW: LaTeX rules
│       ├── software-dev.yaml         # NEW: Dev rules
│       └── knowledge-mgmt.yaml       # NEW: KM rules
├── hooks/
│   ├── haiku-routing-audit.sh        # NEW: Routing monitoring
│   └── load-session-memory.sh        # NEW: Memory loading
├── scripts/
│   └── context-manager.py            # NEW: Lazy loading utility
├── docs/
│   ├── claude-code-architecture.md   # Architecture spec
│   ├── claude-code-subscription-model.md  # Quota math
│   └── claude-code-cost-model.md     # API cost analysis
├── README.md
├── EXAMPLE.claude.md
├── LICENSE
└── IMPLEMENTATION_PROMPT.md          # This file
```

---

## Questions to Address During Implementation

1. **Agent Definition Format:** Should we use YAML or Markdown for agent definitions?
   - Current: Markdown
   - Consideration: YAML might be easier to parse programmatically

2. **State Persistence:** Where should work coordinator state live?
   - Suggested: `/tmp/work-queue.json` (ephemeral, daily reset)
   - Alternative: `~/.claude/state/work-queue.json` (persistent)

3. **Hook Execution:** How are hooks triggered in Claude Code?
   - Need to verify hook execution model
   - May need to adapt implementation

4. **Domain Classification:** Automatic vs manual override?
   - Suggested: Automatic with manual override command
   - Command: `switch-domain [latex|dev|knowledge|general]`

5. **Memory Schema:** JSON vs YAML vs custom format?
   - Suggested: JSON (easy parsing, jq support)
   - Alternative: YAML (more readable)

---

## References

**Essential Reading Before Implementation:**
1. `docs/claude-code-architecture.md` - Complete architecture (READ FIRST)
2. `docs/claude-code-subscription-model.md` - Quota optimization mathematics
3. `README.md` - Current plugin structure
4. Global `~/.claude/CLAUDE.md` - User's routing rules

**Implementation Patterns:**
- Escalation checklist: `docs/claude-code-architecture.md` Section "Solution 1"
- Work coordination: `docs/claude-code-architecture.md` Section "Solution 2"
- Domain configs: `docs/claude-code-architecture.md` Section "Solution 3"
- Lazy loading: `docs/claude-code-architecture.md` "Context Optimization"
- Memory system: `docs/claude-code-architecture.md` "Memory System"

---

## Expected Outcomes

**Week 1 (Foundation):**
- Haiku pre-routing operational
- 50%+ quota savings on routing
- Work coordinator limiting WIP to 3
- Basic domain detection

**Week 2 (Optimization):**
- Domain-specific rules enforced
- 60-70% quota savings achieved
- 80-90% task completion rate
- Context size reduced 30%+

**Week 3 (Refinement):**
- Adaptive WIP adjustment working
- Memory persistence across sessions
- Metrics collection and dashboards
- 90%+ task completion rate

**Month 1 (Stable):**
- 4-6× throughput improvement demonstrated
- Quality issues reduced 80-90%
- Architecture validated and documented
- Ready for production use

---

## Implementation Checklist

### Phase 1: Core Router
- [ ] Create `agents/haiku-pre-router.md` with escalation checklist
- [ ] Update `agents/router.md` with domain detection
- [ ] Create `agents/router-escalation.md` for edge cases
- [ ] Test routing accuracy with sample requests
- [ ] Verify quota savings (target: >50%)

### Phase 2: Work Coordination
- [ ] Create `agents/work-coordinator.md`
- [ ] Implement work queue state management
- [ ] Add WIP limit enforcement (default: 3)
- [ ] Test with parallel tasks
- [ ] Verify completion rate improvement

### Phase 3: Domain Optimization
- [ ] Create domain configs in `config/domains/`
- [ ] Create rules in `config/rules/`
- [ ] Implement domain classifier in router
- [ ] Test domain switching
- [ ] Verify domain-specific optimizations

### Phase 4: Infrastructure
- [ ] Create hooks in `hooks/`
- [ ] Set up memory directory `~/.claude/memory/`
- [ ] Implement context manager script
- [ ] Test memory persistence
- [ ] Verify context size reduction

### Testing & Validation
- [ ] Haiku escalation rate in 30-40% range
- [ ] WIP limit never exceeded
- [ ] Domain detection >95% accurate
- [ ] Rules enforced correctly
- [ ] Quota savings measured and verified

### Documentation
- [ ] Update README.md with new architecture
- [ ] Document agent descriptions
- [ ] Create user guide for new features
- [ ] Add troubleshooting guide
- [ ] Write migration guide from old architecture

---

## Getting Started

**Step 1:** Read the architecture document
```bash
cd /home/nicky/code/claude-router-system
cat docs/claude-code-architecture.md
```

**Step 2:** Review current structure
```bash
ls -la agents/
cat README.md
```

**Step 3:** Start implementation (Phase 1)
Begin with Haiku pre-router as it's the foundation for quota savings.

**Step 4:** Test early and often
Create test cases for each component before moving to next phase.

---

## Support & Context

**User Background:**
- Working on ME/CFS research project (LaTeX-heavy)
- Has Claude Code Max (5x) subscription
- Needs quota optimization for daily work
- Comfortable with technical implementation
- Values mathematical rigor and practical results

**Project Goals:**
- Maximize work output within subscription quotas
- Ensure high task completion rates
- Maintain quality through automated gates
- Support multiple work domains efficiently

**Success Definition:**
Implementation succeeds when user can work full day without quota exhaustion, tasks complete at >90% rate, and quality issues drop >80%.

---

**Ready to implement? Start with Phase 1 and work incrementally. Good luck!**