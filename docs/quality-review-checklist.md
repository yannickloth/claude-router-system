# Quality Review Checklist for Claude Code Architecture Documents

**Version:** 1.0
**Created:** 2026-01-31
**Purpose:** Comprehensive quality criteria for architecture documents and implementation code

---

## 1. File Path & State Management Review

### Persistent vs Ephemeral Storage
- [ ] **NO `/tmp/` for persistent state**: Work queues, session state, configuration
- [ ] **Use appropriate locations**:
  - `~/.claude/state/` - Persistent state (work queues, session data)
  - `~/.claude/logs/` - Log files (with rotation)
  - `~/.claude/cache/` - Cached results (safe to delete)
  - `~/.claude/memory/` - Cross-session memory
  - Project `.claude/` - Project-specific state
- [ ] **Directory creation**: All paths ensure parent directories exist (`mkdir -p`)
- [ ] **Atomic writes**: Critical state files use write-to-temp + rename pattern
- [ ] **Permissions**: Sensitive files are user-only readable (`chmod 600`)
- [ ] **Backup/recovery**: Critical state has recovery mechanisms

---

## 2. Code Quality & Correctness

### Python Code
- [ ] **Syntax validity**: All code blocks are syntactically correct
- [ ] **Type hints**: Functions have proper type annotations
- [ ] **Imports**: All required imports listed
- [ ] **Error handling**: Try/except around I/O operations
- [ ] **Resource cleanup**: Context managers for files, connections
- [ ] **Logging**: Appropriate log levels and messages

### Bash Scripts
- [ ] **Set flags**: `set -euo pipefail` at script start
- [ ] **Variable quoting**: All variables in `"$VAR"` quotes
- [ ] **Error handling**: Check exit codes, handle failures
- [ ] **Path safety**: Use `"$HOME"` not `~`, quote all paths
- [ ] **Shellcheck compliance**: No shellcheck warnings

### JSON Examples
- [ ] **Valid JSON**: All JSON blocks parse correctly
- [ ] **Schema consistency**: Same fields across examples
- [ ] **Realistic data**: Examples reflect actual usage

### Algorithm Correctness
- [ ] **Logic verification**: No off-by-one errors, boundary issues
- [ ] **Edge cases**: Empty inputs, zero values, max values handled
- [ ] **Invariants**: Pre/post-conditions documented and maintained

---

## 3. Architectural Consistency

### IVP Compliance (Independent Variation Principle)

- [ ] **Change driver identification**: Each component has explicit change driver(s) documented
- [ ] **Element separation**: Elements with different change drivers are in different components
- [ ] **Element unification**: Elements with same change driver are in same component
- [ ] **Boundary validation**: Component boundaries defined by assigned change driver set
- [ ] **Minimized change impact**: Modifications to one change driver affect minimal components

### Component Composition

- [ ] **Composability**: Components combine predictably
- [ ] **Testability**: Components testable in isolation

### Data Flow
- [ ] **Explicit state transitions**: State changes are documented
- [ ] **Unidirectional flow**: No circular data dependencies
- [ ] **Immutability**: Shared data is immutable where possible
- [ ] **Ownership**: Clear owner for each piece of state

---

## 4. State Persistence & Recovery

### Crash Recovery
- [ ] **Agent failure**: Work queue recovers from agent crashes
- [ ] **Partial writes**: Atomic writes prevent corruption
- [ ] **Stale state**: Detection and cleanup of abandoned work
- [ ] **Restart resilience**: System recovers cleanly after restart

### Quota Tracking
- [ ] **Persistent quota state**: Daily usage persists across sessions
- [ ] **Reset timing**: Midnight rollover handled correctly
- [ ] **Concurrency**: Multiple sessions don't double-count
- [ ] **Accuracy**: Quota tracking matches actual usage

### Work Queue
- [ ] **Lost work detection**: Identifies incomplete work from previous sessions
- [ ] **Recovery prompts**: User notified of recoverable work
- [ ] **Priority preservation**: Work priority maintained across restarts
- [ ] **Dependency integrity**: Dependency graph preserved

### Cache Management
- [ ] **Invalidation triggers**: File changes trigger appropriate invalidation
- [ ] **Staleness detection**: TTL enforcement
- [ ] **Size limits**: Cache doesn't grow unbounded
- [ ] **Eviction policy**: LRU or appropriate eviction

---

## 5. Security & Privacy

### File Security
- [ ] **Permissions**: Sensitive files are `600` (user-only)
- [ ] **Directory permissions**: State directories are `700`
- [ ] **Log sanitization**: No secrets in logs
- [ ] **Memory files**: Encrypted if containing sensitive data

### Input Validation
- [ ] **Path injection**: User paths sanitized
- [ ] **Command injection**: Shell commands properly quoted
- [ ] **SQL injection**: If using DB, parameterized queries
- [ ] **XSS**: If generating HTML, proper escaping

### Privacy
- [ ] **Data minimization**: Only necessary data collected
- [ ] **Local storage**: Sensitive data stays local
- [ ] **Deletion**: Clear command to delete all state/memory
- [ ] **Audit trail**: User can inspect what's stored

---

## 6. Performance & Scalability

### Large Projects
- [ ] **Context loading**: Scales to 500KB+ files
- [ ] **Lazy loading**: Doesn't load entire project at once
- [ ] **Indexing**: Fast lookup for large file counts (1000+ files)
- [ ] **Streaming**: Large file processing uses streaming

### Memory Management
- [ ] **Cache bounds**: Cache size limits enforced
- [ ] **Memory leaks**: No unbounded growth in long-running agents
- [ ] **Resource cleanup**: Files/connections closed promptly
- [ ] **Garbage collection**: Large objects released when done

### Disk Management
- [ ] **Log rotation**: Logs don't fill disk
- [ ] **Cache cleanup**: Old cache entries removed
- [ ] **Temporary files**: Temp files cleaned up
- [ ] **Quota monitoring**: Disk space monitored

---

## 7. Quota & Cost Model Accuracy

### Subscription Tiers
- [ ] **Quota limits**: Max 5× tier: 1125 Sonnet, 250 Opus verified
- [ ] **Reset timing**: Daily reset at midnight (which timezone?)
- [ ] **Carry-over**: No quota carry-over between days
- [ ] **Unlimited Haiku**: Confirmed unlimited quota

### Savings Calculations
- [ ] **Math verification**: All percentage improvements correct
- [ ] **Baseline assumptions**: Current waste rate justified with data
- [ ] **Overhead accounting**: Agent coordination overhead included
- [ ] **Compounding effects**: Combined savings calculated correctly

### Timing & Patterns
- [ ] **Active hours**: 9 AM - 10 PM realistic for target user
- [ ] **Work duration**: Estimated durations realistic
- [ ] **Overnight capacity**: Can actually complete work overnight
- [ ] **Quota exhaustion**: Handles running out of quota gracefully

---

## 8. User Experience & Usability

### Error Handling
- [ ] **Clear messages**: Errors explain what happened and how to fix
- [ ] **Actionable**: User knows what to do next
- [ ] **Severity levels**: Critical vs warning vs info distinguished
- [ ] **Context**: Error messages include relevant context

### Progress Visibility
- [ ] **No silent failures**: User always knows when something fails
- [ ] **Progress indicators**: Long operations show progress
- [ ] **Completion notifications**: User notified when work completes
- [ ] **Background work**: Can monitor background agents

### Control & Safety
- [ ] **Abort mechanism**: Can cancel long-running operations
- [ ] **Undo capability**: Destructive operations can be undone
- [ ] **Confirmation**: High-risk operations require confirmation
- [ ] **Preview**: Changes can be previewed before applying

### Configuration
- [ ] **Sensible defaults**: Works out-of-box for most users
- [ ] **Easy customization**: Key parameters easily adjustable
- [ ] **Documentation**: All config options documented
- [ ] **Validation**: Config errors caught with helpful messages

---

## 9. Testing & Validation

### Test Coverage
- [ ] **Unit tests**: Each function/algorithm has tests
- [ ] **Integration tests**: End-to-end workflows tested
- [ ] **Edge cases**: Boundary conditions tested
- [ ] **Regression tests**: Previous bugs have test cases

### Test Quality
- [ ] **Realistic data**: Tests use realistic inputs
- [ ] **Failure modes**: Tests verify error handling
- [ ] **Performance**: Load/performance tests for scalability
- [ ] **Cross-platform**: Tests run on Linux/macOS/Windows

### Validation
- [ ] **JSON schema**: JSON examples validated
- [ ] **Python syntax**: Code blocks checked with Python parser
- [ ] **Bash linting**: Scripts checked with shellcheck
- [ ] **Math verification**: Calculations verified independently

---

## 10. Documentation Quality

### Code Documentation
- [ ] **Complex logic**: Non-obvious algorithms explained
- [ ] **Assumptions**: Implicit assumptions made explicit
- [ ] **Gotchas**: Edge cases and pitfalls documented
- [ ] **References**: Links to relevant papers/docs

### User Documentation
- [ ] **Getting started**: Quick start guide exists
- [ ] **Examples**: Concrete examples for each feature
- [ ] **Troubleshooting**: Common problems and solutions
- [ ] **FAQ**: Frequently asked questions answered

### API Documentation
- [ ] **Function signatures**: Parameters and return types documented
- [ ] **Side effects**: State changes documented
- [ ] **Preconditions**: Required conditions documented
- [ ] **Exceptions**: Possible errors documented

---

## 11. Implementation Feasibility

### Timeline Realism
- [ ] **Effort estimation**: Time estimates justified
- [ ] **Dependencies**: External dependencies identified
- [ ] **Risk factors**: Known risks documented
- [ ] **Contingency**: Backup plans for blockers

### Technical Dependencies
- [ ] **Libraries**: All external libs documented with versions
- [ ] **Services**: External service requirements listed
- [ ] **Platform**: OS/Python version requirements stated
- [ ] **Compatibility**: Breaking changes documented

### Migration
- [ ] **Upgrade path**: How to upgrade from previous version
- [ ] **Data migration**: State/config migration scripts
- [ ] **Backwards compatibility**: Compatibility guarantees stated
- [ ] **Rollback plan**: How to revert if needed

---

## 12. Domain-Specific Criteria

### For LaTeX Research Domain
- [ ] **Build verification**: Changes trigger build checks
- [ ] **Citation integrity**: BibTeX references validated
- [ ] **Link checking**: Internal references validated
- [ ] **Medical content**: Extra scrutiny for medical claims

### For Software Development
- [ ] **Test suite**: Changes run tests
- [ ] **Type checking**: Type errors caught
- [ ] **Linting**: Code style enforced
- [ ] **Security**: Dependency vulnerabilities checked

### For Knowledge Management
- [ ] **Link integrity**: Broken links detected
- [ ] **Orphan detection**: Unreferenced files found
- [ ] **Taxonomy**: Classification is consistent
- [ ] **Search**: Content is searchable

---

## Immediate Action Items (Critical)

### File Path Fixes
- [ ] Replace ALL `/tmp/` with appropriate persistent locations
- [ ] Document rationale for each path choice
- [ ] Ensure directory creation before writes

### Atomic Operations
- [ ] Work queue uses atomic writes (write to `.tmp` + `mv`)
- [ ] Cache index uses atomic writes
- [ ] Memory files use atomic writes

### Security Hardening
- [ ] All state files have `chmod 600` in creation scripts
- [ ] All directories have `chmod 700` in creation scripts
- [ ] Bash scripts have proper quoting
- [ ] Add `set -euo pipefail` to all bash scripts

### Error Handling
- [ ] All Python I/O wrapped in try/except
- [ ] Bash scripts check exit codes
- [ ] User-facing errors have actionable messages
- [ ] Logging added for debugging

### Validation
- [ ] Run all JSON through `jq` validation
- [ ] Check all Python with `python -m py_compile`
- [ ] Check all bash with `shellcheck`
- [ ] Verify all math calculations

---

## Usage

This checklist should be applied:

1. **During design**: Before writing code
2. **During implementation**: As code is written
3. **Before commit**: Pre-commit verification
4. **During review**: Peer/self review
5. **Before release**: Final quality gate

For each item:
- ✅ = Verified and passing
- ⚠️ = Needs attention
- ❌ = Failing, must fix
- N/A = Not applicable to this component

---

## Continuous Improvement

This checklist should evolve:
- Add items when new failure modes discovered
- Remove items that prove unnecessary
- Reorganize based on frequency of issues
- Update with lessons learned from production

**Maintenance**: Review quarterly, update based on actual issues encountered.
