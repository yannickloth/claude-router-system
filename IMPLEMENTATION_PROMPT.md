# Implementation Prompt: New Router Architecture

**Project:** claude-router-system
**Task:** Implement new router architecture with Haiku pre-routing and work coordination
**Context:** Replacing existing agent architecture (safely committed at c676a34)

---

## Executive Summary

Implement a comprehensive Claude Code router architecture that addresses **eight interconnected challenges** in distributed agent coordination:

1. **Haiku Routing Reliability** - Mechanical escalation system for unlimited-quota model
2. **Parallel Work Completion** - Kanban-style WIP limits for 90%+ completion rate
3. **Multi-Domain Optimization** - Adaptive configuration for LaTeX, dev, knowledge domains
4. **Quota Temporal Optimization** - 24-hour work scheduling to maximize quota utilization
5. **Agent Result Deduplication** - Semantic caching to eliminate 40-50% redundant work
6. **Probabilistic Routing with Validation** - Optimistic execution with quality-based escalation
7. **Cross-Session State Continuity** - Rich state persistence across sessions
8. **Context Management for UX** - Response speed optimization under subscription model

**Cumulative Impact:**
- **80-90% quota savings** through multi-dimensional optimization
- **8-12× throughput improvement** vs baseline
- **90%+ task completion rate** (vs current ~50%)
- **50-70% faster responses** through UX-focused context management
- **70-80% reduction in redundant work** via deduplication and state continuity

The complete architectural specification is in `docs/claude-code-architecture.md`.

---

## Integration Architecture

### UserPromptSubmit Hook (CRITICAL)

**The router system integrates with Claude Code via the UserPromptSubmit hook.**

**Hook location:** `~/.claude/hooks/UserPromptSubmit.sh` (or `.claude/hooks/UserPromptSubmit.sh` for project-level)

**How it works:**

1. User submits a prompt in Claude Code
2. Claude Code executes UserPromptSubmit hook BEFORE processing the request
3. Hook receives user input via `stdin`
4. Hook runs routing logic (Python script)
5. Routing analysis printed to `stdout` (visible to user)
6. Claude sees the routing analysis and uses it to select the appropriate agent

**Implementation:**

```bash
#!/bin/bash
# .claude/hooks/UserPromptSubmit.sh
# Integration point for router system

set -euo pipefail

# Read user request from stdin
USER_REQUEST=$(cat)

# Run routing core (Python implementation)
ROUTER_DIR="$HOME/.claude/infolead-router"
ROUTING_SCRIPT="$ROUTER_DIR/routing_core.py"

# Ensure routing script exists
if [ ! -f "$ROUTING_SCRIPT" ]; then
    echo "⚠️  Router system not installed at $ROUTER_DIR"
    echo "User request: $USER_REQUEST"
    exit 0
fi

# Run routing analysis
python3 "$ROUTING_SCRIPT" <<< "$USER_REQUEST"

# Exit code 0 allows Claude to proceed with the routing decision
exit 0
```

**Routing core (Python):**

```python
# ~/.claude/infolead-router/routing_core.py
import sys
import json
from pathlib import Path

def route_request(user_request: str) -> dict:
    """
    Analyze user request and determine routing.
    Returns routing decision for Claude to use.
    """
    # Load routing rules, agent registry, etc.
    # Apply Haiku escalation checklist
    # Match to agents
    # Return routing recommendation

    routing_decision = {
        "recommended_agent": "sonnet-general",
        "reasoning": "Request requires analysis and judgment",
        "escalation_triggers": [],
        "confidence": "high"
    }

    return routing_decision

def main():
    # Read user request from stdin
    user_request = sys.stdin.read().strip()

    # Route the request
    decision = route_request(user_request)

    # Print routing analysis (visible to user and Claude)
    print(f"🔀 Routing Analysis:")
    print(f"   Agent: {decision['recommended_agent']}")
    print(f"   Reason: {decision['reasoning']}")

    # Store routing decision for metrics
    log_routing_decision(decision)

if __name__ == "__main__":
    main()
```

**Key points:**

- Hook runs BEFORE Claude processes the request (not after via PreToolUse)
- Python script is the actual routing logic implementation
- Output is visible to both user and Claude
- Claude sees the routing analysis and uses it to spawn the appropriate agent
- State files use persistent paths (`~/.claude/infolead-router/`)

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

## Implementation Strategy

The implementation is organized into **4 phases**, progressively building from core infrastructure to advanced optimizations:

- **Phase 1: Foundation** - Core routing, basic coordination, initial caching (Solutions 1, 2, 5-basic, 7-basic)
- **Phase 2: Optimization Layers** - Temporal scheduling, enhanced caching, probabilistic routing, context UX (Solutions 4, 5-enhanced, 6, 8)
- **Phase 3: Domain Integration** - Multi-domain optimization and adaptive coordination (Solutions 3, 2-adaptive, 8-complete)
- **Phase 4: Refinement & Monitoring** - Metrics, testing, continuous optimization

---

## Implementation Task

### Phase 1: Foundation (Priority 1)

Implement core infrastructure for routing, coordination, and basic state management.

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
- Tools: Read, Glob, Grep, Task, AskUserQuestion
- Handles escalations from Haiku pre-router
- Handles complex routing decisions
- Implements domain classification
- Risk assessment for destructive operations
- Asks for clarification when request is ambiguous

**Decision Flow:**
1. Parse intent and assess risk
2. Classify domain (LaTeX / Dev / Knowledge / General)
3. **Check if request is clear enough to route**
   - If ambiguous → Ask user for clarification using AskUserQuestion
   - If clear → Continue to step 4
4. Match to specialized agents (if available)
5. Select model tier (Haiku / Sonnet / Opus)
6. **If routing decision uncertain → Escalate to router-escalation (Opus)**
7. Route to appropriate agent
8. Verify agent produces output

**Domain Detection:**
- LaTeX: `.tex` files, `nix build`, research citations
- Dev: Code files, tests, git operations
- Knowledge: Notes, markdown, organization tasks
- General: Everything else

**Clarification Examples:**

```yaml
Request: "Optimize the database"
Router: |
  ❓ I need clarification:
  1. What aspect? (Query speed / Storage size / Indexes)
  2. Priority? (Speed vs storage)
  3. Constraints? (Can I modify schema? Add indexes?)

Request: "Fix the bug in auth"
Router: |
  ❓ Which auth component?
  - Login flow?
  - API authentication?
  - Token refresh?
  - Permission checking?

Request: "Make it better"
Router: |
  ❓ Better in what way?
  - Performance?
  - User experience?
  - Code quality?
  - Error handling?
```

**Escalation vs Clarification:**

- **Escalate:** Router uncertain about HOW to route (needs better judgment)
- **Clarify:** REQUEST is ambiguous (needs more info from user)

**Reference:** See `docs/claude-code-architecture.md` section "Solution 3: Multi-Domain Adaptive Architecture"

#### 1.3 Router Escalation Agent (Opus)

**File:** `agents/router-escalation.md`

**Requirements:**
- Model: Opus
- Tools: Read, Glob, Grep, Task, AskUserQuestion
- Handles edge cases where Sonnet router is uncertain about routing
- Deep reasoning about edge case routing decisions
- Makes routing decision and spawns agent directly
- Can ask for clarification if request itself is ambiguous

**When to Use (Escalation):**

- Sonnet uncertain about which agent/tier to use
- Unusual phrasing that could mask destructive intent
- Hidden complexity in seemingly simple requests
- High-stakes routing decisions requiring deep reasoning

**Clarification Capability:**

- Opus can also ask for clarification if needed
- Example: Edge case request that's both complex AND ambiguous
- After clarification, Opus makes routing decision

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

**State File:** `~/.claude/infolead-router/state/work-queue.json`

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

#### 2.3 Basic Semantic Cache (Solution 5 - Initial)

**File:** `utils/semantic-cache.py`

**Requirements:**
- Request hashing for exact duplicate detection
- File modification timestamp tracking
- Simple cache invalidation on file changes
- TTL-based expiration (30 days default)

**State Directory:** `~/.claude/infolead-router/cache/`

**Data Structure:**
```json
{
  "cache_key": "sha256_hash_of_request",
  "request_text": "Find papers on ME/CFS mitochondrial dysfunction",
  "agent_used": "literature-integrator",
  "result": {"papers": ["Smith2024", "Jones2023"]},
  "timestamp": "2026-01-31T10:00:00Z",
  "quota_cost": 15,
  "context_hash": "sha256_of_relevant_files",
  "hit_count": 0
}
```

**Cache Operations:**
- `check_cache(request, context)` → Returns cached result or None
- `store_result(request, result, quota_cost)` → Stores in cache
- `invalidate_on_file_change(file_path)` → Removes stale entries

**Reference:** See `docs/claude-code-architecture.md` section "Solution 5: Agent Result Deduplication"

#### 2.4 Session State Persistence (Solution 7 - Basic)

**File:** `utils/session-state-manager.py`

**Requirements:**
- Capture session state at session end
- Load recent state at session start
- Track search history for deduplication
- Record decisions and rationale

**State Directory:** `~/.claude/infolead-router/memory/`

**Files:**
- `session-state.json` - Current session state
- `search-history.json` - Cross-session search record
- `decisions.json` - Decision log

**Hook:** `hooks/load-session-memory.sh`
```bash
#!/bin/bash
# Loads session memory at startup
MEMORY_DIR="$HOME/.claude/infolead-router/memory"
STATE_FILE="$MEMORY_DIR/session-state.json"

if [ -f "$STATE_FILE" ]; then
    echo "📂 Loading session memory..."
    jq -r '.current_focus' "$STATE_FILE"
fi
```

**Reference:** See `docs/claude-code-architecture.md` section "Solution 7: Cross-Session State Continuity"

### Phase 2: Optimization Layers (Priority 2)

Implement advanced optimization features for quota efficiency and UX.

#### 4.1 Temporal Work Scheduler (Solution 4)

**File:** `agents/temporal-scheduler.md`

**Requirements:**
- Model: Sonnet
- Tools: Read, Write, Bash, Task
- Classify work as synchronous (user needed) vs asynchronous (can run unattended)
- Queue async work for overnight execution
- Estimate quota consumption and duration
- Respect dependencies and deadlines

**State File:** `~/.claude/infolead-router/state/temporal-work-queue.json`

**Data Structure:**
```json
{
  "queued_work": [
    {
      "id": "t1",
      "description": "Search for papers on mitochondrial dysfunction",
      "timing": "async",
      "estimated_quota": 15,
      "estimated_duration_minutes": 20,
      "scheduled_for": "2026-01-31T22:00:00Z",
      "dependencies": [],
      "priority": 7
    }
  ],
  "completed_overnight": [
    {
      "id": "t0",
      "completed_at": "2026-01-31T03:45:00Z",
      "result_path": "/tmp/overnight-results/t0.json"
    }
  ]
}
```

**Work Classification:**
- **Synchronous signals**: "help me", "which", "should I", "decide", "review", "edit"
- **Asynchronous signals**: "search for", "find papers", "analyze", "generate report", "batch"

**Overnight Executor:** `scripts/overnight-executor.sh`
```bash
#!/bin/bash
# Runs queued async work during off-hours
# Scheduled via cron: 0 22 * * * (10 PM daily)

QUEUE_FILE="$HOME/.claude/infolead-router/state/temporal-work-queue.json"
RESULTS_DIR="$HOME/.claude/infolead-router/state/overnight-results"

mkdir -p "$RESULTS_DIR"

# Process queued work until quota exhausted or queue empty
jq -r '.queued_work[] | @json' "$QUEUE_FILE" | while read -r work; do
    # Execute work item, store results
    echo "Executing: $(echo "$work" | jq -r '.description')"
    # ... execution logic ...
done
```

**Evening Planning Hook:** `hooks/evening-planning.sh`
```bash
#!/bin/bash
# Runs at 9 PM to prepare overnight work queue
# Shows user what will run overnight

if [ "$(date +%H)" -eq 21 ]; then
    QUEUE="$HOME/.claude/infolead-router/state/temporal-work-queue.json"
    if [ -f "$QUEUE" ]; then
        echo "🌙 Overnight work scheduled:"
        jq -r '.queued_work[] | "  - \(.description) (~\(.estimated_duration_minutes)m)"' "$QUEUE"
    fi
fi
```

**Reference:** See `docs/claude-code-architecture.md` section "Solution 4: Quota Temporal Optimization"

#### 4.2 Enhanced Semantic Cache (Solution 5 - Enhanced)

**Enhancement to:** `utils/semantic-cache.py`

**Additional Requirements:**
- Semantic similarity matching (not just exact hash)
- Embedding generation for requests (using lightweight local model or API)
- Cosine similarity threshold (default 0.85)
- Cache hit statistics and optimization

**Similarity Matching:**
```python
def find_similar_cached_result(
    request_embedding: List[float],
    similarity_threshold: float = 0.85
) -> Optional[CachedResult]:
    """
    Search cache for semantically similar requests.
    Returns best match if similarity >= threshold.
    """
    # Compute cosine similarity with all cached embeddings
    # Return best match above threshold
```

**Cache Statistics:**
- Hit rate tracking (hits / total requests)
- Quota savings from cache hits
- Most frequently cached queries
- Cache size and cleanup recommendations

**Target Metrics:**
- 40-50% cache hit rate in steady state
- 400-500 messages/month saved from cached results

**Reference:** See `docs/claude-code-architecture.md` section "Solution 5: Agent Result Deduplication"

#### 4.3 Probabilistic Router (Solution 6)

**File:** `agents/probabilistic-router.md`

**Requirements:**
- Model: Haiku (for classification) + Sonnet (for validation)
- Tools: Read, Glob, Grep, Task
- Classify request confidence (HIGH/MEDIUM/LOW)
- Optimistically route HIGH confidence requests to Haiku
- Validate Haiku results with lightweight checks
- Auto-escalate to Sonnet if validation fails

**Confidence Classification:**

HIGH confidence (>90% sure Haiku can handle):
- Mechanical, rule-based tasks
- Simple syntax fixes
- Pattern matching operations
- File formatting, whitespace cleanup

MEDIUM confidence (70-90%):
- May need judgment, but worth trying Haiku first
- Simple edits with clear scope
- Basic analysis tasks

LOW confidence (<70%):
- Route directly to Sonnet
- Complex reasoning required
- Ambiguous requirements

**Validation Criteria:**
```yaml
validation_checks:
  - name: "Build still passes"
    condition: "file.endswith('.tex') or file.endswith('.py')"
    validation: "run_build_check"
    escalate_on_failure: true

  - name: "No syntax errors introduced"
    condition: "code_file_modified"
    validation: "run_linter"
    escalate_on_failure: true

  - name: "Changes match request scope"
    condition: "always"
    validation: "diff_analysis"
    escalate_on_failure: true
```

**Routing Decision Format:**
```json
{
  "recommended_model": "haiku",
  "confidence": "high",
  "fallback_model": "sonnet",
  "validation_criteria": ["build_check", "syntax_check"],
  "reasoning": "Simple syntax fix with clear scope"
}
```

**Auto-Escalation:**
```
Haiku execution → Validation → Failed? → Escalate to Sonnet
                              Passed? → Return result
```

**Target Metrics:**
- 60-70% of requests optimistically routed to Haiku
- 85% success rate (15% escalate after validation)
- 35-40% additional quota savings

**Reference:** See `docs/claude-code-architecture.md` section "Solution 6: Probabilistic Routing with Validation"

#### 4.4 Context UX Manager (Solution 8 - Initial)

**File:** `utils/context-optimizer.py`

**Requirements:**
- Monitor context size and composition
- Calculate UX health status (OPTIMAL/ACCEPTABLE/DEGRADED/CRITICAL)
- Estimate response latency based on context size
- Recommend fresh start when UX degrades

**Context Health Thresholds:**
```python
thresholds = {
    "optimal_max": 30000,      # <3s response
    "acceptable_max": 60000,   # <7s response
    "degraded_max": 80000,     # <15s response
    "critical": 80000          # >15s response, recommend restart
}
```

**Health Analysis:**
```python
def analyze_context_health(current_tokens: int) -> ContextMetrics:
    """
    Analyze context from UX perspective.

    Returns:
    - total_tokens: Total context size
    - signal_tokens: Relevant, recent context
    - noise_tokens: Old, irrelevant context
    - response_latency_ms: Estimated response time
    - health_status: OPTIMAL/ACCEPTABLE/DEGRADED/CRITICAL
    """
```

**Fresh Start Recommendation:**

Trigger when:
1. Context in CRITICAL state (>80k tokens)
2. Noise ratio >60% (context bloat)
3. Estimated latency >10s (user frustration)

**User Message:**
```
⚠️  Context health: DEGRADED (75,000 tokens, ~12s response time)

Recommendation: Start fresh session for better UX
- Current: 12s responses, 65% noise
- Fresh start: 3s responses, focused context

Continuation prompt:
Continue [task]. State: [summary]. Files: [list]. Next: [steps].
```

**Target Metrics:**
- 30% faster initial responses through lazy loading
- Sub-5s response time maintained longer in session

**Reference:** See `docs/claude-code-architecture.md` section "Solution 8: Context Management for UX"

### Phase 3: Domain Integration (Priority 3)

Implement domain-specific configurations, advanced context management, and adaptive coordination.

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

#### 3.3 Advanced Context Management (Solution 8 - Complete)

**Enhancement to:** `utils/context-optimizer.py`

**Additional Features:**
- Lazy loading strategy with LRU cache
- Metadata indexing for fast section lookup
- Section-level file loading (don't load entire 200KB file for one chapter)
- Context budget management (50k for context, 150k for conversation)

**Lazy Loading Strategy:**
```python
class LazyContextLoader:
    def __init__(self, context_budget: int = 50000):
        self.context_budget = context_budget
        self.loaded_sections = {}  # LRU cache
        self.metadata_index = {}   # File → sections mapping

    def load_section(self, file_path: str, section: str):
        """Load only requested section, not entire file"""
        if section in self.loaded_sections:
            return self.loaded_sections[section]  # Cache hit

        # Load section from file, update LRU cache
        # Evict oldest if budget exceeded

    def build_metadata_index(self, project_root: str):
        """Index all LaTeX chapters, code modules, etc."""
        # Parse files to extract section boundaries
        # Build searchable index
```

**Section-Level Loading:**
- LaTeX: Load by chapter/section markers
- Code: Load by class/function boundaries
- Markdown: Load by heading structure

**Target Metrics:**
- 50-70% response time improvement through lazy loading
- 80-90% signal-to-noise ratio maintained

**Reference:** See `docs/claude-code-architecture.md` section "Solution 8: Context Management for UX"

#### 3.4 Adaptive WIP Coordination (Solution 2 - Enhanced)

**Enhancement to:** `agents/work-coordinator.md`

**Additional Features:**
- Dynamic WIP adjustment based on metrics
- Stall detection and recovery
- Throughput optimization

**Adaptive Algorithm:**
```python
def adjust_wip_limit(metrics: WorkMetrics):
    """
    Dynamically adjust WIP limit based on observed performance.

    Metrics tracked:
    - completion_rate: Tasks completed per hour
    - stall_rate: Percentage of tasks stalled >1h
    - context_switching_cost: Time lost to switching
    """

    if metrics.stall_rate > 0.30:
        # Too much parallel work, focus needed
        return 1  # Focus mode

    if metrics.completion_rate > 2.0 and metrics.stall_rate < 0.10:
        # High throughput, low stalls → can handle more
        return 4  # High throughput mode

    # Balanced default
    return 3
```

**Stall Detection:**
- Track task start time
- Alert if task active >1 hour without progress
- Suggest intervention or re-planning

**Target Metrics:**
- 90%+ task completion rate
- Optimal WIP discovered automatically per domain

**Reference:** See `docs/claude-code-architecture.md` section "Solution 2: Parallel Work with Completion Guarantees"

#### 3.5 Cross-Session State (Solution 7 - Complete)

**Enhancement to:** `utils/session-state-manager.py`

**Additional Features:**
- Session linking (track related sessions)
- Rich decision records with alternatives considered
- File modification history with purpose tracking
- Work item persistence across sessions

**Session Linking:**
```python
@dataclass
class SessionState:
    session_id: str
    parent_session: Optional[str]  # Link to previous session
    created_at: datetime
    current_focus: str
    work_in_progress: List[WorkItem]
    search_history: List[SearchRecord]
    decisions: List[DecisionRecord]
    file_modifications: List[FileModification]
```

**Cross-Session Deduplication:**
```python
def check_duplicate_search(query: str, session_state: SessionState) -> Optional[SearchRecord]:
    """
    Check if similar search performed in this or parent sessions.
    Returns cached search results if found.
    """
    # Check current session
    # Check parent sessions (up to 3 levels)
    # Use semantic similarity for matching
```

**Session-End Hook:** `hooks/session-end.sh`
```bash
#!/bin/bash
# Captures session state at session end
STATE_FILE="$HOME/.claude/infolead-router/memory/session-state.json"

# Update session state with completion timestamp
jq '.ended_at = now | .status = "completed"' "$STATE_FILE" > "$STATE_FILE.tmp"
mv "$STATE_FILE.tmp" "$STATE_FILE"

echo "💾 Session state saved"
```

**Target Metrics:**
- 25-40% cross-session efficiency gain
- 200-300 messages/month saved from eliminated context rebuilding

**Reference:** See `docs/claude-code-architecture.md` section "Solution 7: Cross-Session State Continuity"

### Phase 4: Refinement & Monitoring (Priority 4)

Implement comprehensive monitoring, testing, and continuous optimization across all 8 solutions.

#### 4.1 Metrics Collection System

**File:** `utils/metrics-collector.py`

**Requirements:**
- Track metrics for all 8 solutions
- Daily/weekly aggregation
- Performance visualization
- Optimization recommendations

**Metrics by Solution:**

**Solution 1 (Haiku Routing):**
- Escalation rate (target: 30-40%)
- False negative rate (Haiku should have escalated)
- Quota savings vs direct Sonnet routing

**Solution 2 (Work Coordination):**
- Completion rate (target: >90%)
- Stall rate (target: <10%)
- Average WIP limit used
- Tasks completed per hour

**Solution 3 (Domain Optimization):**
- Domain detection accuracy (target: >95%)
- Rule enforcement rate (target: 100%)
- Context size by domain
- Quality gate failures

**Solution 4 (Temporal Optimization):**
- Quota utilization rate (target: 80-90%)
- Overnight work completion rate
- Work classification accuracy
- Quota waste (unused at midnight)

**Solution 5 (Deduplication):**
- Cache hit rate (target: 40-50%)
- Quota saved from cache hits
- Cache size and growth
- Similarity matching accuracy

**Solution 6 (Probabilistic Routing):**
- Optimistic routing success rate (target: 85%)
- Escalation after validation rate
- Quota savings vs conservative routing
- Validation cost overhead

**Solution 7 (State Continuity):**
- Cross-session search dedup rate
- Session state persistence success
- State corruption incidents
- Context rebuilding time saved

**Solution 8 (Context UX):**
- Average response latency by context size
- Fresh start recommendations triggered
- Signal-to-noise ratio
- User-perceived speed improvement

**Dashboard Output:**
```
📊 Claude Router System Metrics (Week of 2026-01-31)
═══════════════════════════════════════════════════

Solution 1: Haiku Routing
  Escalation rate: 35% (✓ within 30-40% target)
  Quota savings: 720 messages this week
  False negatives: 2 (flagged for review)

Solution 2: Work Coordination
  Completion rate: 94% (✓ >90% target)
  Average WIP: 2.8 tasks
  Throughput: 3.2 tasks/hour

Solution 3: Domain Optimization
  Detection accuracy: 97% (✓ >95%)
  Rules enforced: 100%
  Context reduction: 38% average

Solution 4: Temporal Optimization
  Quota utilization: 86% (✓ 80-90% target)
  Overnight completions: 15 tasks
  Quota waste: 14% (vs 40% baseline)

Solution 5: Deduplication
  Cache hit rate: 47% (✓ 40-50% target)
  Quota saved: 450 messages
  Cache size: 245 MB

Solution 6: Probabilistic Routing
  Optimistic success: 83% (target: 85%)
  Quota savings: 380 messages
  Validation overhead: 25 messages

Solution 7: State Continuity
  Cross-session dedup: 32%
  State save success: 98%
  Time saved: 4.2 hours

Solution 8: Context UX
  Avg response time: 4.1s (✓ <5s)
  Fresh starts recommended: 3
  Signal-to-noise: 84%

Cumulative Impact:
  Total quota savings: 82% vs naive baseline
  Throughput improvement: 9.5× vs baseline
  Overall completion rate: 94%
```

#### 4.2 Hooks

**Create in:** `hooks/`

**Haiku Routing Audit Hook:** `hooks/haiku-routing-audit.sh`
```bash
#!/bin/bash
# Monitors Haiku routing decisions

HAIKU_LOG="$HOME/.claude/infolead-router/logs/haiku-routing-decisions.log"
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

**Week 1: Foundation Phase (Solutions 1, 2, 5-basic, 7-basic)**

- Haiku pre-routing: >50% quota savings on routing operations (Solution 1)
- WIP limiting: Prevent >3 concurrent tasks, maintain focus (Solution 2)
- Basic caching: 10-15% cache hit rate (Solution 5)
- Session state: Memory persists across restarts (Solution 7)
- Task completion rate: >80% (up from ~50% baseline)

**Week 2: Optimization Phase (Solutions 4, 5-enhanced, 6, 8-initial)**

- Temporal scheduling: 20-30% of work shifted to off-peak hours (Solution 4)
- Enhanced caching: 40-50% cache hit rate (Solution 5)
- Probabilistic routing: 35-40% additional execution quota savings (Solution 6)
- Context management: 30% faster responses through initial optimizations (Solution 8)
- Combined routing savings: 60-70% vs baseline

**Week 3: Domain Integration (Solutions 3, 2-adaptive, 8-complete)**

- Domain detection: >95% accuracy (Solution 3)
- Rule enforcement: 100% of domain-specific rules applied (Solution 3)
- Adaptive WIP: Dynamic adjustment working correctly (Solution 2)
- Advanced context: 50-70% response time improvement (Solution 8)
- Quality issues: 80-90% reduction in domain-specific errors

**Week 4: Stable Operation (All 8 solutions)**

- **Cumulative quota savings**: 80-90% vs naive baseline
- **Throughput improvement**: 8-12× vs baseline
- **Task completion rate**: >90%
- **Response speed**: Sub-5s for most operations
- **Quota utilization**: 80-90% (vs 50-60% baseline waste)
- **Cross-session efficiency**: 25-40% reduction in duplicate work
- **Cache effectiveness**: 40-50% hit rate, 400-500 messages/month saved
- **Context health**: 80-90% signal-to-noise ratio

**Qualitative Indicators:**

- User can work full day without quota exhaustion
- Minimal context rebuilding between sessions
- Fast, focused responses throughout session
- Overnight work completes automatically
- Quality gates prevent errors before they occur

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

### 6. Temporal Scheduling (Solution 4)

**CRITICAL:** Overnight executor must handle failures gracefully. Don't defer time-sensitive work.

✅ **Good:** Check work timing classification, defer only async work, handle execution errors

❌ **Bad:** Blindly defer all work, crash on first error, lose work on failure

**Additional Considerations:**
- Don't defer work with hard deadlines (e.g., "by tomorrow morning")
- Account for quota prediction accuracy (don't over-promise overnight capacity)
- Handle partial completion (some tasks succeed, some fail)

### 7. Cache Invalidation (Solution 5)

**CRITICAL:** Cache MUST invalidate when files change. Stale cache is worse than no cache.

✅ **Good:** Track file modification times, invalidate on any dependency change, periodic cleanup

❌ **Bad:** Never invalidate cache, serve stale results, cache sensitive data

**Additional Considerations:**
- Don't cache credentials, API keys, or PII
- TTL must vary by agent type (literature searches: 30 days, code analysis: 1 day)
- Cache size limits to prevent unbounded growth

### 8. Probabilistic Routing Validation (Solution 6)

**CRITICAL:** Validation must be cheap. Don't waste quota on expensive validation checks.

✅ **Good:** Fast syntax checks, diff analysis, lightweight build verification

❌ **Bad:** Full integration tests for validation, redundant analysis, expensive checks

**Additional Considerations:**
- Failed optimistic routes must not lose work (rollback or escalate cleanly)
- Confidence thresholds must be calibrated to user's risk tolerance
- Track success rates and adjust classification over time

### 9. Cross-Session State Security (Solution 7)

**CRITICAL:** State corruption must not break sessions. Session state must be pruned.

✅ **Good:** Validate state on load, prune old sessions, handle corrupted state gracefully

❌ **Bad:** Crash on invalid state, grow unbounded, leak data across users

**Additional Considerations:**
- Session state files are user-local only (no cross-user leakage)
- Regular cleanup of old sessions (keep last 30 days)
- State recovery from partial corruption

### 10. Context UX Management (Solution 8)

**CRITICAL:** Fresh start must preserve critical context. Don't break user workflow.

✅ **Good:** Generate complete continuation prompt, preserve active work, smooth transition

❌ **Bad:** Lose context on restart, break ongoing work, force user to rebuild state

**Additional Considerations:**
- Lazy loading must not break functionality (load dependencies as needed)
- Signal/noise analysis must account for user's workflow patterns
- Fresh start recommendation timing (not in middle of complex task)

---

## File Structure

After implementation, the project should look like:

```
claude-router-system/
├── agents/
│   ├── haiku-pre-router.md           # Solution 1: Mechanical pre-router
│   ├── router.md                      # Solution 1: Sonnet router with domain detection
│   ├── router-escalation.md           # Solution 1: Opus edge case handler
│   ├── work-coordinator.md            # Solution 2: WIP-limited coordination
│   ├── temporal-scheduler.md          # Solution 4: Async work scheduling
│   ├── probabilistic-router.md        # Solution 6: Optimistic routing with validation
│   └── [domain-specific agents]
├── utils/
│   ├── semantic-cache.py              # Solution 5: Agent result deduplication
│   ├── session-state-manager.py       # Solution 7: Cross-session state persistence
│   ├── context-optimizer.py           # Solution 8: UX-driven context management
│   └── metrics-collector.py           # Comprehensive metrics tracking
├── config/
│   ├── domains/                       # Solution 3: Domain configurations
│   │   ├── latex-research.yaml
│   │   ├── software-dev.yaml
│   │   └── knowledge-mgmt.yaml
│   └── rules/                         # Solution 3: Enforcement rules
│       ├── global.yaml
│       ├── latex-research.yaml
│       ├── software-dev.yaml
│       └── knowledge-mgmt.yaml
├── hooks/
│   ├── haiku-routing-audit.sh         # Solution 1: Routing monitoring
│   ├── load-session-memory.sh         # Solution 7: Session start hook
│   ├── session-end.sh                 # Solution 7: Session end hook
│   └── evening-planning.sh            # Solution 4: Overnight work preparation
├── scripts/
│   ├── overnight-executor.sh          # Solution 4: Async work execution
│   └── context-manager.py             # Solution 8: Lazy loading utility
├── docs/
│   ├── claude-code-architecture.md    # Complete 8-solution architecture
│   ├── claude-code-subscription-model.md
│   └── claude-code-cost-model.md
├── README.md
├── EXAMPLE.claude.md
├── LICENSE
└── IMPLEMENTATION_PROMPT.md           # This file
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

1. `docs/claude-code-architecture.md` - Complete 8-solution architecture (READ FIRST)
2. `docs/claude-code-subscription-model.md` - Quota optimization mathematics
3. `docs/claude-code-cost-model.md` - API cost analysis
4. `README.md` - Current plugin structure
5. Global `~/.claude/CLAUDE.md` - User's routing rules

**Implementation Patterns by Solution:**

- **Solution 1 (Haiku Routing)**: `docs/claude-code-architecture.md` Section "Solution 1: Haiku Reliable Routing"
  - Escalation checklist implementation
  - Two-tier routing architecture
  - Audit hooks and monitoring

- **Solution 2 (Work Coordination)**: `docs/claude-code-architecture.md` Section "Solution 2: Parallel Work with Completion Guarantees"
  - Kanban-style WIP limits
  - Priority-based scheduling
  - Adaptive WIP adjustment

- **Solution 3 (Domain Optimization)**: `docs/claude-code-architecture.md` Section "Solution 3: Multi-Domain Adaptive Architecture"
  - Domain detection and classification
  - Rules engine and enforcement
  - Domain-specific configurations

- **Solution 4 (Temporal Optimization)**: `docs/claude-code-architecture.md` Section "Solution 4: Quota Temporal Optimization"
  - Work timing classification
  - Overnight execution system
  - Quota utilization maximization

- **Solution 5 (Deduplication)**: `docs/claude-code-architecture.md` Section "Solution 5: Agent Result Deduplication"
  - Semantic similarity matching
  - Cache invalidation strategies
  - Request embedding and comparison

- **Solution 6 (Probabilistic Routing)**: `docs/claude-code-architecture.md` Section "Solution 6: Probabilistic Routing with Validation"
  - Confidence classification
  - Optimistic execution patterns
  - Validation and auto-escalation

- **Solution 7 (State Continuity)**: `docs/claude-code-architecture.md` Section "Solution 7: Cross-Session State Continuity"
  - Session state schema
  - Cross-session deduplication
  - State persistence and recovery

- **Solution 8 (Context UX)**: `docs/claude-code-architecture.md` Section "Solution 8: Context Management for UX"
  - UX-driven thresholds
  - Lazy loading strategies
  - Fresh start recommendations

---

## Testing Requirements

**Test Cases by Solution:**

**Solution 1 (Haiku Routing):**
- Simple request → Haiku routes directly (0 Sonnet quota used)
- Complex request → Haiku escalates to Sonnet
- Destructive request → Proper risk assessment and escalation
- Edge cases → Router-escalation handles ambiguity correctly
- Target: 30-40% escalation rate, >95% correct routing

**Solution 2 (Work Coordination):**
- Multiple tasks → WIP limit enforced (never >3 concurrent)
- Priority ordering → Highest priority work starts first
- Dependencies → Blocked work waits for dependencies
- Completion → Freed slots trigger new work
- Target: >90% completion rate, adaptive WIP working

**Solution 3 (Domain Optimization):**
- Domain detection → Correctly classifies LaTeX/dev/knowledge
- Rule enforcement → Quality gates block bad changes
- Context optimization → Per-domain strategies applied
- Target: >95% detection accuracy, 100% rule enforcement

**Solution 4 (Temporal Optimization):**
- Work classification → Correctly identifies sync vs async
- Overnight queue → Async work deferred to off-peak
- Execution → Overnight work completes before morning
- Dependencies → Deferred work respects dependencies
- Target: 20-30% work shifted overnight, 80-90% quota utilization

**Solution 5 (Deduplication):**
- Exact duplicates → Cache hit, no redundant work
- Similar requests → Semantic matching works (>0.85 similarity)
- File changes → Cache invalidates correctly
- TTL expiration → Old cache entries cleaned up
- Target: 40-50% cache hit rate, no stale results

**Solution 6 (Probabilistic Routing):**
- High confidence → Haiku executes successfully
- Validation failure → Auto-escalate to Sonnet
- Medium confidence → Try Haiku with careful validation
- Low confidence → Route directly to Sonnet
- Target: 85% optimistic success rate, 35-40% quota savings

**Solution 7 (State Continuity):**
- Session end → State persists correctly
- Session start → Previous state loaded
- Cross-session dedup → Duplicate searches avoided
- State corruption → Graceful degradation
- Target: 25-40% cross-session efficiency gain

**Solution 8 (Context UX):**
- Context health → Correctly classifies OPTIMAL/DEGRADED/CRITICAL
- Fresh start → Triggered at right time with complete continuation
- Lazy loading → Load only needed sections
- Response time → Measurably faster with optimizations
- Target: 50-70% response time improvement, 80-90% signal-to-noise

---

## Expected Outcomes

**Week 1 (Foundation):**
- Solutions 1, 2, 5-basic, 7-basic operational
- Haiku pre-routing: >50% quota savings on routing
- Work coordinator: WIP limiting working, >80% completion rate
- Basic caching: 10-15% cache hit rate
- Session state: Memory persists across restarts

**Week 2 (Optimization Layers):**
- Solutions 4, 5-enhanced, 6, 8-initial added
- Temporal scheduling: 20-30% work shifted to off-peak
- Enhanced caching: 40-50% cache hit rate
- Probabilistic routing: 35-40% additional quota savings
- Context UX: 30% faster initial responses
- Combined savings: 60-70% vs baseline

**Week 3 (Domain Integration):**
- Solutions 3, 2-adaptive, 8-complete added
- Domain detection: >95% accuracy, rules 100% enforced
- Adaptive WIP: Dynamic adjustment working
- Advanced context: 50-70% response time improvement
- Quality: 80-90% reduction in domain-specific errors

**Month 1 (Stable - All 8 Solutions):**
- **Cumulative quota savings**: 80-90% vs naive baseline
- **Throughput improvement**: 8-12× vs baseline
- **Task completion rate**: >90%
- **Response speed**: Sub-5s for most operations
- **Quota utilization**: 80-90% (vs 50-60% waste at baseline)
- **Cross-session efficiency**: 25-40% reduction in duplicate work
- **Cache effectiveness**: 40-50% hit rate
- **Context health**: 80-90% signal-to-noise ratio
- **Quality**: 80-90% reduction in errors
- Architecture validated, documented, production-ready

---

## Implementation Checklist

### Phase 1: Foundation
- [ ] **Solution 1**: Create `agents/haiku-pre-router.md` with escalation checklist
- [ ] **Solution 1**: Update `agents/router.md` with domain detection
- [ ] **Solution 1**: Create `agents/router-escalation.md` for edge cases
- [ ] **Solution 1**: Create `hooks/haiku-routing-audit.sh` for monitoring
- [ ] **Solution 2**: Create `agents/work-coordinator.md` with WIP limits
- [ ] **Solution 2**: Implement work queue state management (`/tmp/work-queue.json`)
- [ ] **Solution 5**: Create `utils/semantic-cache.py` (basic version)
- [ ] **Solution 5**: Set up cache directory `~/.claude/cache/`
- [ ] **Solution 7**: Create `utils/session-state-manager.py` (basic version)
- [ ] **Solution 7**: Create `hooks/load-session-memory.sh`
- [ ] **Solution 7**: Set up memory directory `~/.claude/memory/`
- [ ] Test Phase 1 components with sample requests
- [ ] Verify: >50% routing quota savings, WIP limiting works

### Phase 2: Optimization Layers
- [ ] **Solution 4**: Create `agents/temporal-scheduler.md`
- [ ] **Solution 4**: Create `scripts/overnight-executor.sh`
- [ ] **Solution 4**: Create `hooks/evening-planning.sh`
- [ ] **Solution 4**: Set up temporal work queue (`/tmp/temporal-work-queue.json`)
- [ ] **Solution 5**: Enhance `utils/semantic-cache.py` with similarity matching
- [ ] **Solution 5**: Add embedding generation and cosine similarity
- [ ] **Solution 6**: Create `agents/probabilistic-router.md`
- [ ] **Solution 6**: Implement validation criteria and auto-escalation
- [ ] **Solution 8**: Create `utils/context-optimizer.py` (initial version)
- [ ] **Solution 8**: Implement context health analysis
- [ ] Test Phase 2 components
- [ ] Verify: 40-50% cache hit rate, temporal scheduling working, probabilistic routing >85% success

### Phase 3: Domain Integration
- [ ] **Solution 3**: Create domain configs in `config/domains/`
- [ ] **Solution 3**: Create rules in `config/rules/`
- [ ] **Solution 3**: Implement domain classifier in router
- [ ] **Solution 2**: Enhance work coordinator with adaptive WIP adjustment
- [ ] **Solution 8**: Enhance `utils/context-optimizer.py` with lazy loading
- [ ] **Solution 8**: Create `scripts/context-manager.py` for lazy loading
- [ ] **Solution 7**: Enhance `utils/session-state-manager.py` with session linking
- [ ] **Solution 7**: Create `hooks/session-end.sh`
- [ ] Test Phase 3 components
- [ ] Verify: >95% domain detection, adaptive WIP working, lazy loading effective

### Phase 4: Refinement & Monitoring
- [ ] Create `utils/metrics-collector.py` for all 8 solutions
- [ ] Implement comprehensive metrics dashboard
- [ ] Create test suite covering all 8 solutions
- [ ] Performance tuning and optimization
- [ ] Documentation updates (README, architecture, user guide)
- [ ] Integration testing across all components
- [ ] Verify cumulative metrics: 80-90% quota savings, 8-12× throughput

### Documentation
- [ ] Update README.md with complete 8-solution architecture
- [ ] Document all agent definitions and capabilities
- [ ] Create user guide covering all features
- [ ] Add troubleshooting guide for common issues
- [ ] Write migration guide from previous architecture
- [ ] Document metrics and monitoring system

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

Implementation succeeds when:

- **Quota efficiency**: User can work full day without quota exhaustion (80-90% savings vs naive baseline)
- **Throughput**: 8-12× more work completed with same quota
- **Completion**: Tasks complete at >90% rate (vs ~50% baseline)
- **Quality**: 80-90% reduction in errors through automated gates
- **Speed**: Sub-5s responses throughout session via context UX optimization
- **Continuity**: Minimal duplicate work across sessions (25-40% cross-session efficiency gain)
- **Utilization**: 80-90% of daily quota used productively (vs 50-60% waste)

---

## Summary: 8-Solution Architecture

This implementation addresses eight interconnected challenges through coordinated solutions:

1. **Solution 1: Haiku Reliable Routing** - Mechanical escalation checklist enables unlimited-quota Haiku to handle 60-70% of routing
2. **Solution 2: Parallel Work Completion** - Kanban-style WIP limits ensure 90%+ completion rate with adaptive adjustment
3. **Solution 3: Multi-Domain Optimization** - Domain-adaptive configs optimize for LaTeX research, software dev, and knowledge management
4. **Solution 4: Quota Temporal Optimization** - 24-hour work scheduling utilizes overnight quota for async work (80-90% utilization)
5. **Solution 5: Agent Result Deduplication** - Semantic caching eliminates 40-50% of redundant searches and analysis
6. **Solution 6: Probabilistic Routing** - Optimistic execution with validation saves 35-40% additional quota
7. **Solution 7: Cross-Session State Continuity** - Rich state persistence enables 25-40% cross-session efficiency gain
8. **Solution 8: Context Management for UX** - Response speed optimization through lazy loading and UX-driven thresholds

**Cumulative Impact: 80-90% quota savings, 8-12× throughput improvement, 90%+ completion rate**

**Next Steps:**
1. Read complete architecture: `/home/nicky/code/claude-router-system/docs/claude-code-architecture.md`
2. Start with Phase 1 (Foundation): Solutions 1, 2, 5-basic, 7-basic
3. Test incrementally before proceeding to next phase
4. Monitor metrics to validate improvements

**Ready to implement? Start with Phase 1 and work incrementally. Good luck!**
