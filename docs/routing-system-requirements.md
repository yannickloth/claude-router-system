# Claude Code Routing System Requirements

**Version:** 1.0
**Created:** 2026-01-31
**Purpose:** Comprehensive functional and non-functional requirements for the Claude Code routing and agent coordination system

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Functional Requirements](#2-functional-requirements)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [Constraints](#4-constraints)
5. [Acceptance Criteria](#5-acceptance-criteria)
6. [Traceability Matrix](#6-traceability-matrix)

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for the Claude Code routing system, which optimizes agent coordination, quota utilization, and task completion across multiple domains (LaTeX research, software development, knowledge management).

### 1.2 Scope

The system encompasses:
- Request routing and agent selection
- State persistence and cross-session continuity
- Quota management and temporal optimization
- Security and privacy protections
- Performance and scalability optimizations
- User experience and visibility

### 1.3 Intended Audience

- System architects
- Implementation developers
- Quality assurance engineers
- Users configuring routing behavior

### 1.4 Document Conventions

- **MUST**: Mandatory requirement
- **SHOULD**: Recommended requirement
- **MAY**: Optional requirement
- **Checklist Reference**: [QRC-X.Y] refers to Quality Review Checklist item X.Y

---

## 2. Functional Requirements

### FR-1: Routing & Agent Selection

#### FR-1.1: Mandatory Router Pass-Through

**Requirement:** Every user request MUST be processed by the router agent before execution.

**Rationale:** Ensures consistent routing decisions, prevents capable models from bypassing cost optimization.

**Acceptance Criteria:**
- Zero direct responses from main session to user requests
- All requests logged with routing decision
- Router invoked even for "obvious" or "simple" requests

**Checklist Reference:** [QRC-3.2] Architectural Consistency - Component Composition

---

#### FR-1.2: Three-Tier Routing Architecture

**Requirement:** The system MUST support three-tier routing with Haiku pre-routing, Sonnet main routing, and Opus escalation.

**Rationale:** Unlimited Haiku quota enables cost-free routing for 60-70% of requests. Three-outcome model (ROUTE, ESCALATE, CLARIFY) handles all request scenarios.

**Router Decision Outcomes:**

1. **ROUTE** - Spawn agent to execute task
2. **ESCALATE** - Pass to higher-tier router for better judgment
3. **CLARIFY** - Ask user for clarification via AskUserQuestion tool

**Acceptance Criteria:**

- Haiku pre-router executes mechanical escalation checklist
- Escalation triggers are verifiable boolean checks
- No subjective "complexity assessment" required by Haiku
- Sonnet router handles all escalated cases OR asks for clarification
- Opus router handles Sonnet escalations OR asks for clarification
- Clarification used when request is ambiguous (not when routing is uncertain)

**Checklist Reference:** [QRC-7.1] Quota & Cost Model Accuracy

---

#### FR-1.3: Haiku Escalation Checklist

**Requirement:** Haiku pre-router MUST escalate to Sonnet router if ANY of the following triggers activate:

1. **Destructive operations detected**
   - Keywords: delete, remove, drop, truncate, destroy, wipe
   - Patterns involving: rm, unlink, DROP TABLE, etc.

2. **No explicit file path mentioned**
   - Request contains patterns/wildcards instead of specific paths
   - Example: "delete all .tmp files" vs "delete /tmp/foo.txt"

3. **Agent match confidence < 0.7**
   - Semantic similarity to available agents below threshold
   - Multiple equally-scored agent candidates

4. **Protected file modification**
   - Paths: `.claude/agents/*.md`, `.claude/CLAUDE.md`, config files
   - Any files affecting system behavior

5. **Ambiguous scope**
   - Vague quantity: "many", "some", "most"
   - Undefined target: "fix errors" without file specification

6. **Multi-step coordination needed**
   - Request implies workflow: "analyze and then implement"
   - Dependencies between subtasks

**Acceptance Criteria:**
- Each trigger is a boolean function with clear logic
- False positive rate (unnecessary escalations) < 30%
- False negative rate (missed escalations) = 0% for destructive operations
- Trigger logic is testable with unit tests

**Checklist Reference:** [QRC-2.4] Algorithm Correctness - Logic Verification

---

#### FR-1.4: Agent Selection Priority

**Requirement:** Router MUST select agents in the following priority order:

1. **Project-specific specialized agents** (`.claude/agents/`)
   - Match request to agent descriptions using semantic similarity
   - Threshold: confidence ≥ 0.7 for exact match

2. **General agents** (when no specialized match)
   - `haiku-general`: Mechanical operations, explicit paths, no judgment
   - `sonnet-general`: Default for reasoning, analysis, judgment
   - `opus-general`: Complex reasoning, proofs, high-stakes decisions

**Acceptance Criteria:**
- Specialized agents checked before general agents
- General agent tier selection based on documented criteria
- Router logs agent selection rationale

**Checklist Reference:** [QRC-3.3] Architectural Consistency - Data Flow

---

#### FR-1.5: Protected File Routing Rules

**Requirement:** Modifications to protected files MUST route to sonnet-general or opus-general, NEVER haiku-general.

**Protected file patterns:**
- `.claude/agents/*.md` (agent definitions)
- `.claude/CLAUDE.md` (routing configuration)
- `.claude/settings.json` (system configuration)
- Any files in `.claude/` directory

**Rationale:** These files affect system behavior and require careful judgment.

**Acceptance Criteria:**
- Haiku-general cannot be selected for protected file edits
- Router enforces this rule even if user explicitly requests haiku
- Logging shows when protected file rule triggers

**Checklist Reference:** [QRC-5.1] Security - File Security

---

#### FR-1.6: Router Escalation for Uncertainty

**Requirement:** If Sonnet router is uncertain about routing decision, it MUST escalate to `router-escalation` (Opus).

**Uncertainty triggers:**
- Request seems simple but might have hidden complexity
- Unusual phrasing that could mask destructive intent
- Genuinely ambiguous scope

**Acceptance Criteria:**
- Escalation rate to Opus < 5% of total requests
- Escalation decision includes documented rationale
- Router-escalation makes final decision and spawns agent directly

**Checklist Reference:** [QRC-8.1] User Experience - Error Handling

---

#### FR-1.7: Router Clarification Capability

**Requirement:** Router agents MUST use AskUserQuestion tool when request requirements are genuinely ambiguous.

**Clarification triggers:**

1. Requirements are vague or undefined ("make it better", "optimize", "clean up")
2. Multiple valid interpretations exist ("fix the auth" - which auth mechanism?)
3. Scope is unspecified ("update the docs" - which docs? how?)
4. User choice needed ("use approach A or B?" - user must decide)
5. Missing critical information for routing decision

**Acceptance Criteria:**

- Router uses AskUserQuestion when request is ambiguous
- After clarification, router re-analyzes and routes
- Clarification rate < 15% of total requests (most requests are clear enough)
- Clarification questions are specific and actionable

**Distinction from escalation:**

- **Escalation** = router uncertain about HOW to route (needs better judgment)
- **Clarification** = REQUEST is ambiguous (needs more information from user)

**Examples:**

```yaml
CLARIFY:
  - "Make it better" → Ask: Better how? Performance? UX? Code quality?
  - "Fix the auth" → Ask: Which auth system? Login? API tokens? OAuth?
  - "Clean up the code" → Ask: Which files? What criteria? Format? Architecture?

ESCALATE:
  - "Delete some old files" → Opus decides which files qualify as "old"
  - Edge case routing decision → Opus applies deeper reasoning
```

**Checklist Reference:** [QRC-8.1] User Experience - Error Handling

---

### FR-2: State Persistence & Recovery

#### FR-2.1: Persistent State Locations

**Requirement:** System MUST use appropriate persistent locations for all state, NEVER `/tmp/` for persistent data.

**Directory structure:**

- `~/.claude/infolead-router/state/` - Persistent state (work queues, session data)
- `~/.claude/infolead-router/logs/` - Log files with rotation
- `~/.claude/infolead-router/cache/` - Cached results (safe to delete)
- `~/.claude/infolead-router/memory/` - Cross-session memory
- `~/.claude/infolead-router/rules/` - Domain-specific rules
- `~/.claude/infolead-router/domains/` - Domain configurations
- `<project>/.claude/` - Project-specific state

**Acceptance Criteria:**

- Zero usage of `/tmp/` for persistent state
- All state directories created with `mkdir -p`
- Parent directory existence verified before writes
- Namespace uses `infolead-router` prefix for clear ownership

**Checklist Reference:** [QRC-1.1] File Path & State Management - Persistent vs Ephemeral Storage

---

#### FR-2.2: Atomic State Writes

**Requirement:** Critical state files MUST use atomic write operations (write to temp + rename).

**Files requiring atomic writes:**

- Work queue: `~/.claude/infolead-router/state/work-queue.json`
- Session state: `~/.claude/infolead-router/state/sessions/<session-id>.json`
- Cache index: `~/.claude/infolead-router/cache/index.json`
- Memory files: `~/.claude/infolead-router/memory/*.json`

**Acceptance Criteria:**
- All critical state writes use pattern: write to `.tmp` file, then `mv` to final location
- Interrupted writes do not corrupt existing state
- Recovery from partial writes is automatic

**Checklist Reference:** [QRC-1.2] State Management - Atomic Writes

---

#### FR-2.3: Work Queue Crash Recovery

**Requirement:** System MUST recover cleanly from agent crashes and restarts.

**Recovery capabilities:**
- Detect stale work (started >1h ago, no progress)
- Identify incomplete work from previous sessions
- Preserve work priority and dependencies across restarts
- Prompt user for recovery decisions

**Acceptance Criteria:**
- Restart after crash shows recoverable work
- User can choose to resume, abandon, or reschedule work
- Work dependencies remain intact after recovery
- No lost work items (all tracked until explicitly abandoned)

**Checklist Reference:** [QRC-4.1] State Persistence - Crash Recovery

---

#### FR-2.4: Cross-Session State Continuity

**Requirement:** System MUST persist session state to enable seamless continuation across sessions.

**State persistence includes:**
- Work items (queued, active, completed)
- Search history (queries, results, timestamps)
- Decisions made (with rationale)
- File modifications (with purpose)
- Quota usage tracking
- Session linkage (parent, related sessions)

**Acceptance Criteria:**
- New session can load previous session state
- Search deduplication works across sessions (15-25% reduction in redundant work)
- Decision history accessible in new sessions
- Session state files use schema versioning for evolution

**Checklist Reference:** [QRC-4.3] State Persistence - Work Queue

---

#### FR-2.5: State Postcondition Verification

**Requirement:** System MUST verify postconditions after every state write and agent execution to ensure consistency in the parallel agent environment.

**Rationale:** In a parallel agent system where multiple agents can write to shared state (work queue, kanban board), agents can crash mid-execution leaving inconsistent state. Postcondition verification detects and recovers from these failures.

**1. Write Postconditions (verified BEFORE finalizing every state write, under exclusive lock):**

- **Timing**: Postconditions MUST be verified while holding exclusive lock, BEFORE committing write
- **Atomicity**: Invariant check and write commit MUST be atomic (both succeed or both fail)
- **Data integrity**: Written data matches intended data (checksum/content verification)
- **Business rules**: Work queue invariants hold (see Kanban invariants below)
- **Referential integrity**: All work item IDs reference valid entities
- **Security constraints**: File permissions maintained (600 for state files)

**2. Agent Output Postconditions (verified when receiving agent responses):**

- **Output existence**: Agent produces usable output (not silent completion)
- **Scope match**: Output matches request scope and requirements
- **File integrity**: Modified files exist and are uncorrupted
- **State consistency**: State updates are consistent with completed work

**3. Kanban Invariants (MUST ALWAYS be true):**

```python
# Invariants checked on every work queue read/write
assert len(active) <= wip_limit, "WIP limit exceeded"
assert len(set(active_ids) & set(queued_ids) & set(completed_ids)) == 0, "Work in multiple states"
assert all(dep in completed for work in active for dep in work.dependencies), "Unsatisfied dependencies"
assert all_work_ids_unique(active + queued + completed), "Duplicate work IDs"
```

**4. Recovery Requirements:**

- **Detection**: Postcondition violations detected on every state read
- **Automatic recovery**: Attempt automatic fix when safe (e.g., rebuild index, remove duplicates)
- **Manual intervention**: Require user decision for unrecoverable violations (e.g., conflicting work items)
- **State backups**: Maintain rolling backup (last 3 versions) for rollback

**Acceptance Criteria:**

- Postcondition checks execute on 100% of state writes (zero bypass)
- Violation detection rate >99% (verified via fault injection testing)
- Automatic recovery succeeds for >80% of common failure modes (stale work, duplicate IDs)
- Manual intervention prompts are clear and actionable
- Recovery operations logged with full context

**Backup Requirements:**
- State backups maintain 3 versions with atomic rotation
- **Rotation Protocol** (performed under exclusive lock):
  1. Acquire exclusive lock on state file
  2. Write new state to temp file
  3. Rotate backups: `mv backup.2 → backup.3`, `mv backup.1 → backup.2`
  4. Copy current state to `backup.1` (before overwriting)
  5. Rename temp file to state file
  6. Release lock
- Backup rotation MUST coordinate with state writes (no concurrent rotation)
- All backup files maintain same permissions as state file (600)

**Cross-references:**
- See FR-5.3 (Agent Output Quality Verification) for agent-level output validation
- See FR-7.1 (Kanban WIP Limits) for work queue management
- See NFR-3.3 (Fault Isolation) for failure containment strategies

**Checklist Reference:** [QRC-2.5] State Postcondition Verification

---

#### FR-2.6: Atomic Work Claiming

**Requirement:** Work item claiming MUST be atomic with respect to WIP limit checking.

**Implementation:**
- Read state, check WIP limit, update work item status, and write state MUST occur under single exclusive lock
- No "check-then-act" pattern allowed for WIP limit enforcement
- Atomic claim operation returns success/failure indicator

**Race Condition Prevention:**
```python
def claim_work_atomic(work_id: str, agent_id: str) -> bool:
    """
    Atomically claim work item if WIP limit permits.
    Returns True if claim succeeded, False if WIP limit reached.
    """
    with locked_state_file(WORK_QUEUE_PATH, 'r+') as f:
        state = json.load(f)

        # Check WIP limit under lock
        active_count = len(state['active'])
        if active_count >= state['wip_limit']:
            return False  # WIP limit reached

        # Find and claim work item
        for i, item in enumerate(state['queued']):
            if item['id'] == work_id:
                work_item = state['queued'].pop(i)
                work_item['agent'] = agent_id
                work_item['started'] = datetime.now().isoformat()
                state['active'].append(work_item)

                # Write back (still under lock)
                f.seek(0)
                f.truncate()
                json.dump(state, f)
                return True

        return False  # Work item not found
```

**Acceptance Criteria:**
- Concurrent agents cannot both claim work that would exceed WIP limit
- Work item cannot transition QUEUED → ACTIVE for multiple agents simultaneously
- WIP limit invariant holds under any concurrent access pattern

**Related:** FR-2.5 (Postcondition Verification), FR-7.1 (Kanban WIP Limits)

---

#### FR-2.7: File Locking Protocol

**Requirement:** All state file read-modify-write operations MUST acquire exclusive file locks to prevent concurrent access conflicts.

**Why Locking is Required:**
Atomic writes (write-to-temp + rename) prevent crash corruption but do NOT prevent race conditions. Multiple agents can simultaneously:
1. Read the same state
2. Make conflicting decisions
3. Overwrite each other's changes (lost updates)

**Locking Implementation:**

```python
import fcntl
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def locked_state_file(path: Path, mode: str = 'r+'):
    """Acquire exclusive lock on state file for read-modify-write operations."""
    with open(path, mode) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
        try:
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Locking Requirements:**

- **Exclusive locks** for read-modify-write operations (work claiming, status updates, quota updates)
- **Minimum lock duration**: Acquire → read → modify → write → release (no early release)
- **Blocking mode with timeout**: Default 30s timeout to prevent indefinite blocking
- **Lock timeout handling**: Clear error message with retry guidance
- **Read-only operations**: Can use shared locks (`LOCK_SH`) for improved concurrency

**Operations Requiring Locks:**
- `claim_work()` - Check WIP limit + update work status
- `complete_work()` - Move work from active → completed
- `add_work()` - Verify ID uniqueness + append to queue
- `update_quota()` - Read quota + increment + write
- Recovery operations - Re-verify staleness + perform action
- Backup rotation - Coordinate with state writes

**Acceptance Criteria:**
- 100% of read-modify-write operations use file locking
- Lock acquisition failures provide clear error messages
- No lost updates under concurrent access
- Deadlock-free (all locks acquired in consistent order)

**Related:** FR-2.6 (Atomic Work Claiming), FR-2.5 (Postcondition Verification)

---

#### FR-2.8: Lock Timeout and Stale Lock Recovery

**Requirement:** Handle stale locks from crashed processes to prevent indefinite blocking.

**Problem:**
If an agent crashes while holding a file lock, the lock may not be released (platform-dependent). On POSIX systems, advisory locks are usually auto-released, but timeout + recovery ensures robustness.

**Lock Timeout Implementation:**

```python
import time
import psutil  # For PID validation

def acquire_lock_with_timeout(f, timeout: float = 30.0) -> bool:
    """Acquire lock with timeout. Returns False if timeout exceeded."""
    start = time.monotonic()
    while True:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            if time.monotonic() - start > timeout:
                return False
            time.sleep(0.1)
```

**Stale Lock Detection:**

When lock acquisition times out:
1. Read lock holder PID from `<state-file>.lock` file
2. Check if PID is still running using `psutil.pid_exists(pid)`
3. If PID is dead, remove stale lock file and retry
4. If PID is alive, report clear error: "State file locked by process {pid}, retry later"

**Lock Holder Tracking:**

```python
def acquire_lock_with_tracking(path: Path) -> None:
    lock_file = path.with_suffix('.lock')

    # Write our PID
    lock_file.write_text(str(os.getpid()))

    # Acquire lock with timeout
    with open(path, 'r+') as f:
        if not acquire_lock_with_timeout(f, timeout=30.0):
            holder_pid = int(lock_file.read_text())
            if not psutil.pid_exists(holder_pid):
                lock_file.unlink()  # Remove stale lock
                # Retry acquisition
            else:
                raise LockTimeoutError(f"Locked by PID {holder_pid}")
```

**Acceptance Criteria:**
- Lock acquisition never blocks indefinitely
- Stale locks from crashed processes are automatically recovered
- Active locks from running processes are respected (no forced override)
- Clear error messages when lock held by active process

**Related:** FR-2.7 (File Locking Protocol)

---

### FR-3: Security & Privacy

#### FR-3.1: File Permissions

**Requirement:** Sensitive state files MUST have restrictive permissions.

**Permission requirements:**
- State files: `chmod 600` (user read/write only)
- State directories: `chmod 700` (user access only)
- Cache files: `chmod 644` (user write, world read acceptable)

**Acceptance Criteria:**
- All state files created with `chmod 600`
- State directories created with `chmod 700`
- Automated verification of permissions on startup

**Checklist Reference:** [QRC-5.1] Security - File Security

---

#### FR-3.2: Log Sanitization

**Requirement:** Log files MUST NOT contain sensitive data (secrets, credentials, private information).

**Sanitization rules:**
- Redact patterns: API keys, passwords, tokens, email addresses
- Replace with placeholder: `<REDACTED>`
- Log sanitization applied before write

**Acceptance Criteria:**
- Regex patterns catch common secret formats
- Automated tests verify sanitization
- User can audit logs without exposing secrets

**Checklist Reference:** [QRC-5.1] Security - Log Sanitization

---

#### FR-3.3: Input Validation

**Requirement:** System MUST validate and sanitize all user-provided inputs.

**Validation requirements:**
- **Path injection**: Sanitize file paths, reject directory traversal (`../`)
- **Command injection**: Properly quote all shell command arguments
- **Pattern safety**: Validate glob patterns before expansion

**Acceptance Criteria:**
- Path traversal attempts rejected
- Shell commands use proper quoting (`"$VAR"`)
- Glob patterns validated before use

**Checklist Reference:** [QRC-5.2] Security - Input Validation

---

#### FR-3.4: Privacy & Data Minimization

**Requirement:** System MUST collect only necessary data and provide deletion capabilities.

**Privacy requirements:**
- Collect minimum data needed for functionality
- Sensitive data stored locally only
- User can delete all state/memory with single command
- User can inspect all stored data

**Acceptance Criteria:**
- `claude clear-state` command deletes all persistent state
- `claude inspect-state` command shows all stored data
- No external transmission of sensitive data

**Checklist Reference:** [QRC-5.3] Security - Privacy

---

### FR-4: Performance & Scalability

#### FR-4.1: Large Project Support

**Requirement:** System MUST scale to large projects (500KB+ files, 1000+ files).

**Scalability requirements:**
- Lazy loading: Don't load entire project at once
- Fast lookup: File indexing for 1000+ files
- Streaming: Large file processing uses streaming
- Context limits: Don't exceed model context windows

**Acceptance Criteria:**
- Projects with 1000+ files indexed in <2s
- Large files (>500KB) processed via streaming
- Context loading selective (only relevant files)

**Checklist Reference:** [QRC-6.1] Performance - Large Projects

---

#### FR-4.2: Memory Management

**Requirement:** System MUST enforce bounded memory usage.

**Memory management requirements:**
- Cache size limits enforced
- No unbounded growth in long-running agents
- Resource cleanup (files, connections) prompt
- Large objects released after use

**Acceptance Criteria:**
- Cache size limited (configurable, default 1GB)
- LRU eviction when cache limit reached
- Memory usage stable over 8+ hour sessions

**Checklist Reference:** [QRC-6.2] Performance - Memory Management

---

#### FR-4.3: Disk Management

**Requirement:** System MUST prevent unbounded disk usage growth.

**Disk management requirements:**
- Log rotation (max 100MB per log file, max 10 files)
- Cache cleanup (TTL-based, max age 7 days)
- Temporary file cleanup (on exit and startup)
- Disk space monitoring (warn if <1GB available)

**Acceptance Criteria:**
- Logs rotate automatically
- Cache cleaned up daily
- Temp files removed on clean exit
- Warning shown if disk space low

**Checklist Reference:** [QRC-6.3] Performance - Disk Management

---

### FR-5: User Experience

#### FR-5.1: Visibility & Monitoring

**Requirement:** System MUST provide real-time visibility into agent execution.

**Visibility requirements:**
- Progress indicators for long-running operations
- Background agent monitoring (no "fire and forget")
- Milestone reporting ("Now analyzing chapter 6...")
- Completion notifications

**Acceptance Criteria:**
- All operations >30s show progress indicators
- Background agents report status every 60s
- User can monitor all active agents
- Completion notifications include results summary

**Checklist Reference:** [QRC-8.2] User Experience - Progress Visibility

---

#### FR-5.2: Error Handling

**Requirement:** System MUST provide clear, actionable error messages.

**Error message requirements:**
- Explain what happened
- Explain why it happened
- Explain how to fix it
- Include relevant context (file paths, agent names, etc.)

**Acceptance Criteria:**
- Every error includes all four elements
- Severity levels distinguished (critical/warning/info)
- No silent failures
- Errors logged with full context

**Checklist Reference:** [QRC-8.1] User Experience - Error Handling

---

#### FR-5.3: Agent Output Quality Verification

**Requirement:** Every agent execution MUST produce verifiable output.

**Output verification requirements:**
- Agent returns results directly, OR
- Agent provides file path to results, OR
- Agent reports modified files, OR
- Agent provides status/summary of actions

**Unacceptable patterns:**
- Agent completes silently
- Agent says "done" without showing what was done
- Agent produces output but doesn't indicate location

**Acceptance Criteria:**
- Router verifies agent output before reporting completion
- If no usable output, router re-routes with explicit output requirements
- All agent executions logged with output type and location

**Cross-references:**
- See FR-2.5 (State Postcondition Verification) for state-level verification

**Checklist Reference:** [QRC-8.2] User Experience - Progress Visibility

---

#### FR-5.4: Control & Safety

**Requirement:** System MUST provide user control over operations.

**Control requirements:**
- Abort mechanism for long-running operations (Ctrl+C)
- Confirmation required for high-risk operations
- Preview capability for destructive changes
- Undo capability where feasible

**Acceptance Criteria:**
- Ctrl+C gracefully stops agents
- Destructive operations prompt for confirmation
- Preview mode available for file changes
- Undo history maintained where applicable

**Checklist Reference:** [QRC-8.3] User Experience - Control & Safety

---

#### FR-5.6: Configuration

**Requirement:** System MUST provide sensible defaults with easy customization.

**Configuration requirements:**
- Works out-of-box for most users
- Key parameters easily adjustable (WIP limits, cache size, log level)
- All config options documented
- Config errors caught with helpful messages

**Acceptance Criteria:**
- Zero-config startup for basic usage
- Config file with comments explaining all options
- Invalid config rejected with clear error message
- Config validation on startup

**Checklist Reference:** [QRC-8.4] User Experience - Configuration

---

### FR-6: Quota Management

#### FR-6.1: Quota Tracking

**Requirement:** System MUST accurately track API quota usage across sessions.

**Quota tracking requirements:**
- Track usage by model (Haiku, Sonnet, Opus)
- Persist quota state across sessions
- Reset quota at midnight (user's local timezone)
- Prevent double-counting in concurrent sessions

**Acceptance Criteria:**
- Quota state persists across sessions
- Daily reset occurs at midnight (user timezone)
- Concurrent sessions use atomic quota updates (increment under lock, not read-modify-write)
- Quota display shows usage vs limits (e.g., "850/1125 Sonnet")

**Checklist Reference:** [QRC-4.2] State Persistence - Quota Tracking

---

#### FR-6.2: Quota Limit Enforcement

**Requirement:** System MUST enforce subscription tier quota limits.

**Subscription tier quotas (Max 5× tier):**
- Sonnet: 1,125 messages/day
- Opus: 250 messages/day
- Haiku: Unlimited

**Acceptance Criteria:**
- Requests rejected when quota exhausted
- Clear error message showing quota status
- Suggestion to upgrade tier or wait for reset
- Grace period: allow 5% overage with warning

**Checklist Reference:** [QRC-7.1] Quota & Cost Model Accuracy - Subscription Tiers

---

#### FR-6.3: Temporal Quota Optimization

**Requirement:** System SHOULD enable overnight work scheduling to utilize unused quota.

**Temporal optimization requirements:**
- Classify work as blocking vs non-blocking
- Non-blocking work can be queued for overnight execution
- Evening dashboard shows queueable work
- Overnight execution with progress monitoring

**Acceptance Criteria:**
- User can review evening queue at 9-10 PM
- Non-blocking work identified automatically
- Overnight execution monitored (not fire-and-forget)
- Results available in morning

**Checklist Reference:** [QRC-7.3] Quota & Cost Model Accuracy - Timing & Patterns

---

#### FR-6.4: Quota Exhaustion Handling

**Requirement:** System MUST handle quota exhaustion gracefully.

**Exhaustion handling:**
- Detect approaching quota limit (80% warning, 95% critical)
- Suggest work prioritization or deferral
- Queue non-blocking work for next day
- Preserve work state for continuation after reset

**Acceptance Criteria:**
- Warning at 80% quota usage
- Critical warning at 95% quota usage
- Work queue preserved when quota exhausted
- User can defer work to next day

**Checklist Reference:** [QRC-7.3] Quota & Cost Model Accuracy - Quota Exhaustion

---

### FR-7: Work Coordination

#### FR-7.1: Kanban-Style WIP Limits

**Requirement:** System MUST enforce work-in-progress limits to ensure task completion.

**WIP limit requirements:**
- Default WIP limit: 3 concurrent tasks
- Adaptive WIP adjustment based on completion rate
- Work queue with priority ordering
- Dependency tracking

**Acceptance Criteria:**
- Maximum 3 tasks active concurrently (default)
- New work blocked until slots available
- High completion rate (>2 tasks/hour) → increase WIP to 4
- High stall rate (>30%) → reduce WIP to 1

**Cross-references:**
- See FR-2.5 (State Postcondition Verification) for WIP limit invariant checking

**Checklist Reference:** [QRC-3.3] Architectural Consistency - Data Flow

---

#### FR-7.2: Work Queue Management

**Requirement:** System MUST maintain work queue with priority and dependencies.

**Work queue schema:**
```json
{
  "wip_limit": 3,
  "active": [{"id": "w1", "agent": "...", "started": "..."}],
  "queued": [{"id": "w2", "priority": 8, "dependencies": ["w1"]}],
  "completed": ["w0"]
}
```

**Acceptance Criteria:**
- Work items tracked with unique IDs
- Priority ordering (1-10 scale)
- Dependency graph prevents out-of-order execution
- Completed work retained for deduplication

**Checklist Reference:** [QRC-4.3] State Persistence - Work Queue

---

#### FR-7.3: Stale Work Detection

**Requirement:** System MUST detect and handle stale or abandoned work.

**Stale work criteria:**
- Active >1 hour with no progress updates
- Agent crashed or disconnected
- Session terminated without completion

**Acceptance Criteria:**
- Stale work detected on startup
- User prompted to resume, abandon, or reschedule
- Stale work marked in work queue
- Automated cleanup of stale work >24h old

**Checklist Reference:** [QRC-4.1] State Persistence - Crash Recovery

---

### FR-8: Deduplication & Caching

#### FR-8.1: Semantic Search Deduplication

**Requirement:** System SHOULD cache and deduplicate search operations.

**Deduplication requirements:**
- Cache search results by query hash
- Semantic similarity matching for similar queries
- TTL-based invalidation (default 7 days)
- File change invalidation for file-based searches

**Acceptance Criteria:**
- Similar queries (>0.8 similarity) reuse cached results
- Cache hit rate >40% for search operations
- Invalid cache entries removed automatically
- Cache miss logs reason (TTL expired, invalidated, no match)

**Checklist Reference:** [QRC-4.4] State Persistence - Cache Management

---

#### FR-8.2: Result Reuse

**Requirement:** System SHOULD reuse previous agent results when applicable.

**Result reuse scenarios:**
- Literature searches (papers on same topic)
- Code analysis (same file analyzed multiple times)
- Content generation (similar sections across chapters)

**Acceptance Criteria:**
- Result cache tracks query, agent, timestamp, result
- Reuse prompted to user ("Found similar search from 2 days ago, reuse?")
- User can override and force fresh execution
- Cache invalidation on file changes

**Checklist Reference:** [QRC-3.3] Architectural Consistency - Data Flow

---

### FR-9: Domain-Specific Adaptations

#### FR-9.1: Domain Classification

**Requirement:** System SHOULD classify requests by domain to apply appropriate optimizations.

**Supported domains:**
- LaTeX research (quality > speed, citations critical)
- Software development (test coverage, type safety, linting)
- Knowledge management (organization, discoverability, links)

**Acceptance Criteria:**
- Domain detected from project structure or user configuration
- Domain-specific agents loaded on demand
- Domain configuration overrides general defaults
- Multi-domain projects supported (per-request classification)

**Checklist Reference:** [QRC-12] Domain-Specific Criteria

---

#### FR-9.2: LaTeX Research Domain

**Requirement:** LaTeX research domain MUST enforce quality and correctness requirements.

**LaTeX-specific requirements:**
- Citation integrity (all claims cited)
- Build verification (LaTeX compiles)
- Link checking (internal references valid)
- Medical content review (extra scrutiny)

**Acceptance Criteria:**
- Pre-commit hook runs LaTeX build
- Citation validation before commit
- Link checker runs on document changes
- Medical claims flagged for review

**Checklist Reference:** [QRC-12.1] Domain-Specific - LaTeX Research

---

#### FR-9.3: Software Development Domain

**Requirement:** Software development domain MUST enforce code quality requirements.

**Software dev requirements:**
- Test suite execution on changes
- Type checking (if applicable)
- Linting and code style
- Security vulnerability scanning

**Acceptance Criteria:**
- Tests run automatically on code changes
- Type errors block commit
- Linter enforces style guide
- Dependency vulnerabilities reported

**Checklist Reference:** [QRC-12.2] Domain-Specific - Software Development

---

---

## 3. Non-Functional Requirements

### NFR-1: IVP Compliance

#### NFR-1.1: Change Driver Separation

**Requirement:** All components MUST adhere to the Independent Variation Principle (IVP).

**IVP definition:** Separate elements with different change drivers into distinct units; unify elements with the same change driver within a single unit.

**Change driver examples:**
- API pricing changes
- Task understanding evolution
- Risk assessment rules
- Domain capabilities
- User preferences
- Performance characteristics

**Acceptance Criteria:**
- Each component has documented change driver(s)
- Elements with different drivers are in different components
- Elements with same driver are in same component
- Component boundaries verified during design review

**Checklist Reference:** [QRC-3.1] Architectural Consistency - IVP Compliance

---

#### NFR-1.2: IVP Compliance Examples

**Compliant:**
- Router (intent/risk/agent-matching) - unified by "task understanding evolution"
- Strategy-advisor (cost/optimization) - unified by "pricing/performance changes"
- Separate domain agents - separated by "domain capabilities"

**Non-compliant:**
- Mixing cost optimization with routing logic (different drivers)
- Combining medical logic and LaTeX logic in same agent (different domains)
- Embedding pricing models in router (changes for different reasons)

**Acceptance Criteria:**
- Design review validates change driver assignment
- Violations rejected in code review
- Refactoring plan created for violations

**Checklist Reference:** [QRC-3.1] Architectural Consistency - IVP Compliance

---

### NFR-2: Monitoring & Observability

#### NFR-2.1: Logging

**Requirement:** System MUST provide comprehensive logging for debugging and auditing.

**Logging requirements:**
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Log rotation (max 100MB per file, 10 files retained)
- Performance logging (operation duration, quota usage)

**Acceptance Criteria:**
- All major operations logged
- Logs parseable by standard tools (jq, grep)
- Log level configurable via environment variable
- Sensitive data sanitized before logging

**Checklist Reference:** [QRC-2.1] Code Quality - Logging

---

#### NFR-2.2: Metrics Collection

**Requirement:** System SHOULD collect metrics for performance monitoring.

**Metrics to collect:**
- Routing decisions (Haiku vs Sonnet, escalations)
- Agent execution times
- Quota usage by model and operation
- Cache hit rates
- Work completion rates

**Acceptance Criteria:**
- Metrics persisted to `~/.claude/logs/metrics.json`
- Daily metrics summary available
- Metrics used to tune adaptive algorithms (WIP limits, cache TTL)

**Checklist Reference:** [QRC-6] Performance & Scalability

---

#### NFR-2.3: Debugging Support

**Requirement:** System MUST support debugging failed operations.

**Debugging features:**
- Verbose mode (detailed operation logging)
- Replay capability (re-run failed operation with logging)
- State inspection (view work queue, cache, session state)
- Dry-run mode (simulate without executing)

**Acceptance Criteria:**
- `--verbose` flag enables detailed logging
- Failed operations include debugging hints
- `claude inspect` command shows system state
- `--dry-run` shows what would be executed

**Checklist Reference:** [QRC-8.1] User Experience - Error Handling

---

### NFR-3: Error Handling

#### NFR-3.1: Error Recovery

**Requirement:** System MUST recover gracefully from errors.

**Error recovery strategies:**
- Automatic retry with exponential backoff (network errors)
- Fallback to alternative agents (if primary fails)
- Partial completion preservation (don't lose progress)
- User notification with recovery options

**Acceptance Criteria:**
- Transient errors retried automatically (max 3 attempts)
- Persistent errors fall back or escalate
- User informed of all errors with recovery options
- No silent failures

**Checklist Reference:** [QRC-8.1] User Experience - Error Handling

---

#### NFR-3.2: Input Validation

**Requirement:** System MUST validate all inputs before processing.

**Validation requirements:**
- File paths exist and are accessible
- Agent names are valid
- Work priorities in valid range (1-10)
- JSON schema validation for structured inputs

**Acceptance Criteria:**
- Invalid inputs rejected with clear error messages
- Edge cases handled (empty strings, null values, out-of-range)
- Validation errors include suggestions for correction

**Checklist Reference:** [QRC-5.2] Security - Input Validation

---

#### NFR-3.3: Fault Isolation

**Requirement:** System MUST isolate faults to prevent cascading failures.

**Fault isolation:**
- Agent failures don't crash router
- Cache corruption doesn't prevent execution
- Log write failures don't block operations
- State corruption has recovery mechanisms

**Acceptance Criteria:**
- Agent crash doesn't terminate session
- Corrupted cache file is rebuilt automatically
- Log write failures logged to stderr
- State corruption triggers recovery prompt

**Cross-references:**
- See FR-2.5 (State Postcondition Verification) for state corruption detection

**Checklist Reference:** [QRC-4.1] State Persistence - Crash Recovery

---

### NFR-4: Code Quality

#### NFR-4.1: Python Code Standards

**Requirement:** All Python code MUST meet quality standards.

**Standards:**
- Type hints on all functions
- Docstrings for all public functions
- Error handling (try/except around I/O)
- Resource cleanup (context managers)
- PEP 8 compliance

**Acceptance Criteria:**
- Mypy type checking passes
- Pylint score ≥ 8.0
- All I/O operations wrapped in try/except
- Files/connections use context managers

**Checklist Reference:** [QRC-2.1] Code Quality - Python Code

---

#### NFR-4.2: Bash Script Standards

**Requirement:** All Bash scripts MUST meet quality standards.

**Standards:**
- `set -euo pipefail` at script start
- All variables quoted (`"$VAR"`)
- Error handling (check exit codes)
- Path safety (`"$HOME"` not `~`)
- Shellcheck compliance

**Acceptance Criteria:**
- Shellcheck passes with zero warnings
- All variables properly quoted
- Script exits on first error (via `set -e`)
- No unbound variables (via `set -u`)

**Checklist Reference:** [QRC-2.2] Code Quality - Bash Scripts

---

#### NFR-4.3: JSON Schema Validation

**Requirement:** All JSON examples and data MUST be valid.

**Validation requirements:**
- All JSON examples parse correctly
- Schema consistency across examples
- Realistic data in examples

**Acceptance Criteria:**
- All JSON validated with `jq`
- Schema definitions exist for all JSON structures
- Examples match schema

**Checklist Reference:** [QRC-2.3] Code Quality - JSON Examples

---

### NFR-5: Testing

#### NFR-5.1: Test Coverage

**Requirement:** System SHOULD have comprehensive test coverage.

**Test requirements:**
- Unit tests for all algorithms
- Integration tests for end-to-end workflows
- Edge case tests (empty inputs, max values)
- Regression tests for known bugs

**Acceptance Criteria:**
- Code coverage ≥ 70%
- All public functions have unit tests
- Critical workflows have integration tests
- Known bugs have regression tests

**Checklist Reference:** [QRC-9.1] Testing & Validation - Test Coverage

---

#### NFR-5.2: Test Quality

**Requirement:** Tests MUST use realistic data and verify error handling.

**Test quality requirements:**
- Realistic input data
- Failure mode verification
- Performance tests for scalability claims
- Cross-platform testing (Linux, macOS, Windows)

**Acceptance Criteria:**
- Tests use production-like data
- Error paths tested
- Performance benchmarks exist
- Tests pass on all platforms

**Checklist Reference:** [QRC-9.2] Testing & Validation - Test Quality

---

### NFR-6: Documentation

#### NFR-6.1: Code Documentation

**Requirement:** Complex logic MUST be documented inline.

**Documentation requirements:**
- Non-obvious algorithms explained
- Assumptions made explicit
- Edge cases and gotchas documented
- References to papers/docs

**Acceptance Criteria:**
- All complex functions have explanation comments
- Assumptions documented in docstrings
- Edge cases noted in comments
- External references linked

**Checklist Reference:** [QRC-10.1] Documentation Quality - Code Documentation

---

#### NFR-6.2: User Documentation

**Requirement:** System MUST provide user-facing documentation.

**User documentation:**
- Getting started guide
- Examples for each feature
- Troubleshooting guide
- FAQ

**Acceptance Criteria:**
- Quick start guide exists
- All features have examples
- Common problems documented with solutions
- FAQ covers frequent questions

**Checklist Reference:** [QRC-10.2] Documentation Quality - User Documentation

---

#### NFR-6.3: API Documentation

**Requirement:** All public APIs MUST be documented.

**API documentation:**
- Function signatures with type hints
- Side effects documented
- Preconditions specified
- Exceptions listed

**Acceptance Criteria:**
- All public functions have docstrings
- Side effects noted in docstrings
- Preconditions documented
- Possible exceptions listed

**Checklist Reference:** [QRC-10.3] Documentation Quality - API Documentation

---

### NFR-7: Performance

#### NFR-7.1: Response Time

**Requirement:** System SHOULD provide sub-5s response time for most operations.

**Performance targets:**
- Routing decision: <500ms
- Work queue update: <100ms
- Cache lookup: <50ms
- Session state load: <1s

**Acceptance Criteria:**
- 90th percentile routing time <500ms
- Work queue operations <100ms
- Cache lookups <50ms
- Session restore <1s

**Checklist Reference:** [QRC-6] Performance & Scalability

---

#### NFR-7.2: Throughput

**Requirement:** System SHOULD achieve 8-12× throughput improvement over baseline.

**Throughput metrics:**
- Tasks completed per day
- Quota utilization efficiency
- Parallel work capacity
- Cache hit rate contribution

**Acceptance Criteria:**
- 8-12× tasks/day vs baseline
- 80-90% quota utilization
- WIP limit maintained
- 40%+ cache hit rate

**Checklist Reference:** [QRC-7.2] Quota & Cost Model Accuracy - Savings Calculations

---

---

## 4. Constraints

### C-1: Platform Constraints

**Constraint:** System MUST run on Linux and macOS, SHOULD support Windows.

**Implications:**
- File path handling must be cross-platform
- Shell scripts must use portable constructs
- Line endings handled correctly (CRLF vs LF)

---

### C-2: Python Version

**Constraint:** System MUST support Python 3.9+.

**Implications:**
- Type hints use 3.9+ syntax
- No Python 3.10+ exclusive features (unless backported)
- Dependencies compatible with Python 3.9

---

### C-3: External Dependencies

**Constraint:** System SHOULD minimize external dependencies.

**Rationale:** Reduce installation complexity and security surface.

**Acceptable dependencies:**
- Standard library preferred
- Well-maintained third-party libraries (requests, pydantic, etc.)
- No abandonware or unmaintained packages

---

### C-4: API Constraints

**Constraint:** System MUST respect Claude API rate limits and quotas.

**API limits:**
- Subscription tier quotas (enforced by Anthropic)
- Rate limits (handled with backoff)
- Context window limits (200k tokens for Claude Sonnet 4.5)

**Implications:**
- Quota tracking must be accurate
- Rate limit errors handled gracefully
- Context optimization critical

---

### C-5: Backwards Compatibility

**Constraint:** System SHOULD maintain backwards compatibility for state files.

**Rationale:** Users should not lose state on system upgrades.

**Implications:**
- State schema versioning required
- Migration scripts for schema changes
- Old schema versions supported for 2+ releases

---

---

## 5. Acceptance Criteria

### 5.1 Functional Acceptance

**System is functionally acceptable if:**

1. ✅ All FR-1 routing requirements pass
   - Mandatory router pass-through enforced (0% bypass rate)
   - Haiku escalation checklist functional (0% false negatives for destructive ops)
   - Protected files routed correctly (100% compliance)

2. ✅ All FR-2 state persistence requirements pass
   - No persistent state in `/tmp/` (automated scan)
   - Atomic writes for critical state (verified)
   - Crash recovery functional (tested)

3. ✅ All FR-3 security requirements pass
   - File permissions correct (`600` for state files)
   - Log sanitization functional (no secrets in logs)
   - Input validation prevents injection attacks

4. ✅ All FR-5 UX requirements pass
   - Real-time visibility for all operations
   - Clear error messages (all errors actionable)
   - Agent output verification (no silent completions)

5. ✅ All FR-6 quota requirements pass
   - Quota tracking accurate (within 1% of actual)
   - Quota limits enforced
   - Graceful exhaustion handling

---

### 5.2 Non-Functional Acceptance

**System is non-functionally acceptable if:**

1. ✅ IVP compliance verified
   - All components have documented change drivers
   - No mixed-driver components

2. ✅ Performance targets met
   - Response time <5s for 90% of operations
   - Throughput improvement 8-12× vs baseline
   - Cache hit rate >40%

3. ✅ Code quality standards met
   - Python: Mypy passes, Pylint ≥8.0
   - Bash: Shellcheck passes
   - JSON: All examples valid

4. ✅ Test coverage adequate
   - Code coverage ≥70%
   - All critical paths tested
   - Regression tests for known bugs

5. ✅ Documentation complete
   - User guide exists
   - API documentation complete
   - Troubleshooting guide available

---

### 5.3 Integration Acceptance

**System integration is acceptable if:**

1. ✅ End-to-end workflows functional
   - User request → routing → execution → output
   - Work queue → agent execution → completion
   - Session → state persistence → restoration

2. ✅ Domain-specific adaptations functional
   - LaTeX: Build verification, citation checking
   - Software dev: Test execution, linting
   - Knowledge: Link checking, organization

3. ✅ Cross-session continuity functional
   - Search deduplication across sessions (15-25% reduction)
   - Decision history accessible
   - State restoration seamless

---

---

## 6. Traceability Matrix

### Functional Requirements to Checklist

| Requirement                   | Checklist Items | Priority |
| ----------------------------- | --------------- | -------- |
| FR-1.1: Mandatory Router      | QRC-3.2         | CRITICAL |
| FR-1.2: Three-Tier Routing    | QRC-7.1         | HIGH     |
| FR-1.3: Haiku Escalation      | QRC-2.4         | HIGH     |
| FR-1.5: Protected Files       | QRC-5.1         | CRITICAL |
| FR-1.7: Router Clarification  | QRC-8.1         | HIGH     |
| FR-2.1: Persistent Locations | QRC-1.1 | CRITICAL |
| FR-2.2: Atomic Writes | QRC-1.2 | CRITICAL |
| FR-2.3: Crash Recovery | QRC-4.1 | HIGH |
| FR-2.4: Cross-Session State | QRC-4.3 | MEDIUM |
| FR-2.5: Postcondition Verification | QRC-2.5 | CRITICAL |
| FR-2.6: Atomic Work Claiming | QRC-2.5 | CRITICAL |
| FR-2.7: File Locking Protocol | QRC-2.5 | CRITICAL |
| FR-2.8: Lock Timeout and Recovery | QRC-2.5 | HIGH |
| FR-3.1: File Permissions | QRC-5.1 | CRITICAL |
| FR-3.2: Log Sanitization | QRC-5.1 | HIGH |
| FR-3.3: Input Validation | QRC-5.2 | CRITICAL |
| FR-4.1: Large Projects | QRC-6.1 | MEDIUM |
| FR-4.2: Memory Management | QRC-6.2 | HIGH |
| FR-4.3: Disk Management | QRC-6.3 | MEDIUM |
| FR-5.1: Visibility | QRC-8.2 | HIGH |
| FR-5.2: Error Handling | QRC-8.1 | HIGH |
| FR-5.3: Output Verification | QRC-8.2 | HIGH |
| FR-6.1: Quota Tracking | QRC-4.2 | HIGH |
| FR-6.2: Quota Limits | QRC-7.1 | HIGH |

### Non-Functional Requirements to Checklist

| Requirement | Checklist Items | Priority |
|-------------|----------------|----------|
| NFR-1.1: IVP Compliance | QRC-3.1 | HIGH |
| NFR-2.1: Logging | QRC-2.1 | MEDIUM |
| NFR-3.1: Error Recovery | QRC-8.1 | HIGH |
| NFR-3.2: Input Validation | QRC-5.2 | CRITICAL |
| NFR-4.1: Python Standards | QRC-2.1 | MEDIUM |
| NFR-4.2: Bash Standards | QRC-2.2 | MEDIUM |
| NFR-4.3: JSON Validation | QRC-2.3 | LOW |
| NFR-5.1: Test Coverage | QRC-9.1 | MEDIUM |
| NFR-6.1: Code Docs | QRC-10.1 | LOW |
| NFR-6.2: User Docs | QRC-10.2 | MEDIUM |
| NFR-7.1: Response Time | QRC-6 | MEDIUM |

---

## 7. Verification Methods

### 7.1 Automated Verification

**Items verifiable via automation:**

- File path usage (`grep -r '/tmp/' src/`)
- File permissions (`find ~/.claude -type f -not -perm 600`)
- Python syntax (`python -m py_compile`)
- Bash syntax (`shellcheck`)
- JSON validity (`jq . <file>`)
- Type checking (`mypy`)
- Linting (`pylint`)
- Test coverage (`pytest --cov`)

### 7.2 Manual Verification

**Items requiring manual verification:**

- Routing decision correctness (sample validation)
- Error message clarity (user testing)
- Documentation completeness (review)
- IVP compliance (architecture review)

### 7.3 Integration Testing

**Integration test scenarios:**

1. **End-to-end routing**: User request → Haiku → escalation → Sonnet → agent execution
2. **Crash recovery**: Kill agent mid-execution, restart, verify recovery prompt
3. **Cross-session continuity**: Complete work in session 1, restore in session 2, verify deduplication
4. **Quota exhaustion**: Consume quota, verify graceful handling
5. **Protected file routing**: Request haiku-general for agent file, verify rejection

---

## 8. Maintenance & Evolution

### 8.1 Requirement Updates

**This document SHOULD be updated when:**

- New features are planned
- Requirements change based on user feedback
- Architectural changes affect requirements
- New constraints are discovered

### 8.2 Traceability Updates

**Traceability matrix MUST be updated when:**

- New requirements added
- Checklist items added/removed
- Requirement priorities change

### 8.3 Review Schedule

**Requirements review cadence:**

- Quarterly: Full requirements review
- After major releases: Update based on lessons learned
- On architectural changes: Ensure requirements still valid

---

## Appendix A: Glossary

**Agent:** A specialized component that executes specific tasks (e.g., `haiku-general`, `chapter-integrator`)

**Change Driver:** An independent factor that would cause a component to change (per IVP)

**IVP:** Independent Variation Principle - architectural principle for component separation

**Router:** Component that interprets user requests and selects appropriate agent

**WIP Limit:** Work-in-progress limit - maximum number of concurrent active tasks

**Quota:** Daily message limit per subscription tier (Sonnet: 1,125, Opus: 250)

**Protected Files:** Configuration files that affect system behavior (`.claude/agents/*.md`, etc.)

**State Persistence:** Saving system state to disk for cross-session continuity

**Temporal Optimization:** Scheduling work across time to maximize quota utilization

---

## Appendix B: References

1. Quality Review Checklist: `/home/nicky/code/claude-router-system/docs/quality-review-checklist.md`
2. Architecture Document: `/home/nicky/code/claude-router-system/docs/claude-code-architecture.md`
3. Global Routing Config: `~/.claude/CLAUDE.md`
4. IVP Reference: https://doi.org/10.5281/zenodo.17677315

---

**End of Requirements Document**
