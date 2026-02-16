# Implementation Plan: Fix Router System Issues

## Context

The Claude Router System v1.7.1 achieved 10/10 functional quality through rigorous Opus review and iterative fixes. However, a deep architectural analysis revealed significant gaps in **testability**, **code quality**, and **IVP compliance**.

## Current Status

**v1.7.1 Released**:
- Functional: 10/10 ✅
- Tested: 7/10 ⚠️ (33% untested)
- Maintainable: 5/10 ⚠️ (IVP violations)
- Bug-free: 7/10 ⚠️ (3 confirmed bugs)

**Overall Architecture Quality**: 3/10 ❌

## Issues Found (37 Total)

### Category 1: Test Coverage Gaps (12 issues)

**CRITICAL (2)**:
1. **Project Isolation Untested** - The v1.7.1 headline feature has ZERO automated tests
   - `detect_project_root()`, `get_project_id()`, `get_project_data_dir()`, `is_router_enabled()`, `load_config_file()`
   - Cross-project data isolation never verified

2. **6 Core Modules Have No pytest Coverage** (3,745 lines / 33% of codebase)
   - `routing_compliance.py` (643 lines)
   - `probabilistic_router.py` (1,093 lines)
   - `quota_tracker.py` (456 lines)
   - `temporal_scheduler.py` (858 lines)
   - `overnight_execution_runner.py` (332 lines)
   - `context_ux_manager.py` (363 lines)

**HIGH (4)**:
3. Hook compliance tracking logic untested (log-subagent-start.sh lines 80-177)
4. Config cascade completely untested (bash + Python)
5. Multi-stage orchestration untested (adaptive_orchestrator.py)
6. Domain-specific workflow loading untested (domain_adapter.py)

**MEDIUM (6)**:
7. Hook routing directive format not validated
8. Duration calculation not tested
9. Model tier detection not tested
10. Cache invalidation logic not tested
11. Session state locking under concurrent access not tested
12. Morning briefing time-window logic not tested

### Category 2: Code Quality Issues (14 issues)

**BUGS (3)**:
1. **Runtime crash in overnight_execution_runner.py** (HIGH)
   - Line 87: `def create_agent_executor(project_contexts: Dict[str, str]) -> callable:`
   - Line 225: `create_agent_executor(project_contexts, work_items_map)` ← 2 args but expects 1
   - **TypeError when overnight execution runs**

2. **Hardcoded user path** (HIGH)
   - Line 104: `/home/nicky/.local/bin/claude`
   - Fails for every other user

3. **Dead code: load-session-memory.sh** (HIGH)
   - Reads `memory/session-state.json` that nothing writes
   - Only `state/session-state.json` is actually used

**PERFORMANCE (5)**:
4. Multiple jq spawns (3-5 processes per hook instead of 1)
5. Repeated directory walks (detect_project_root called 3+ times per hook, no caching)
6. jq version check on every hook invocation (should cache)
7. Morning briefing hardcoded time zone (uses system local time)
8. Embedded CLI/test code inflates module size (20% of some files)

**SECURITY (1)**:
9. Unsanitized log content (line 136: `$DESCRIPTION` contains user input, pipe chars corrupt logs)

**CODE DUPLICATION (2)**:
10. Hook preamble duplicated 8-12 lines across all 9 hooks (~100 lines total)
11. Metrics format scattered across 3 hooks (JSON construction duplicated)

**ROBUSTNESS (3)**:
12. Compliance tracking 60-second window is arbitrary (could match wrong request)
13. Shebang inconsistency (8 use `#!/bin/bash`, 1 uses `#!/usr/bin/env bash`)
14. Session state has redundant guard checks (dead code in load/save hooks)

### Category 3: IVP Violations (11 issues)

**CRITICAL (1)**:
1. **common-functions.sh bundles 5 change drivers** (Purity = 0.25, should be 1.0)
   - 291 lines, 10 functions
   - Declared driver: `HOOK_INFRASTRUCTURE`
   - Actual drivers: DEPENDENCY_MANAGEMENT, PROJECT_DETECTION, PROJECT_IDENTIFICATION, DATA_LAYOUT, CONFIGURATION_POLICY
   - **Violates IVP-1**: Elements with different Γ in same module

**SEVERE (3)**:
2. **adaptive_orchestrator.py mixes 8 drivers** (Purity = 0.125 - WORST FILE)
   - CONFIGURATION, COMPLEXITY_CLASSIFICATION, ORCHESTRATION_STRATEGY, DOMAIN_ADAPTATION, CLI_INTERFACE, TEST_REQUIREMENTS, ERROR_HANDLING, MONITORING

3. **probabilistic_router.py mixes 5 drivers** (Purity = 0.20)
   - PROBABILISTIC_ROUTING, RESULT_VALIDATION, EXECUTION_STRATEGY, CLI_INTERFACE, TEST_REQUIREMENTS

4. **log-subagent-start.sh mixes 6 drivers** (Purity = 0.167)
   - MONITORING, COMPLIANCE_TRACKING, COMPLIANCE_POLICY, PROJECT_DETECTION, METRICS_COLLECTION, DIRECTIVE_FORMAT

**HIGH (4)**:
5. log-subagent-stop.sh mixes MONITORING + COST_OPTIMIZATION (determine_model_tier)
6. user-prompt-submit.sh mixes ROUTING + METRICS_COLLECTION + DIRECTIVE_FORMAT (Purity = 0.25)
7. All 16 Python files mix DOMAIN_LOGIC + CLI_INTERFACE + TEST_REQUIREMENTS
8. Metrics format scattered (3 hooks independently construct JSONL)

**MEDIUM (3)**:
9. load/save-session-state.sh mix STATE_MANAGEMENT + PROJECT_DETECTION + METRICS + LOCKING (Purity = 0.25)
10. morning-briefing.sh mixes MONITORING + TIME_POLICY + PROJECT_DETECTION
11. Embedded tests in production files (20% of some files)

## Your Task

**Create a comprehensive implementation plan to fix ALL 37 issues.**

The plan should:

1. **Organize issues into phases** (e.g., Phase 1: Critical bugs, Phase 2: Tests, Phase 3: IVP refactoring)
2. **Define dependencies** (what must be done before what?)
3. **Estimate effort** for each fix (trivial/low/medium/high)
4. **Propose file structure** for IVP-compliant refactoring
5. **Specify test coverage targets** (what to test, how)
6. **Identify risks** (backward compatibility, migration paths)
7. **Define success criteria** (how do we know we're done?)

## Reference Materials

**Code locations**:
- Plugin: `plugins/infolead-claude-subscription-router/`
- Tests: `tests/infolead-claude-subscription-router/`
- Implementation: `plugins/infolead-claude-subscription-router/implementation/` (16 Python files)
- Hooks: `plugins/infolead-claude-subscription-router/hooks/` (10 bash files)

**Documentation**:
- IVP Formalization: `~/code/PIV-Formalization-ICSA2026/sections/02-IVP-formalization/IVP_formalization.tex`
- Detailed findings: See the Opus architectural review output from the previous session

**IVP Target Metrics**:
- Purity: 1.0 for all modules (currently 0.125-0.25)
- Test coverage: 100% (currently 67%)
- Known bugs: 0 (currently 3)

## Constraints

1. **Backward compatibility**: Must maintain plugin API (hooks, CLI)
2. **No breaking changes**: Users should not need to modify their code
3. **Incremental delivery**: Plan should allow phased releases (v1.7.2, v1.8.0, etc.)
4. **Documentation**: Each phase should update relevant docs

## Desired Output

A structured implementation plan with:

### Phase N: [Name]
**Goals**: What this phase achieves
**Issues Fixed**: List of issue numbers from above
**Changes**:
- File 1: What changes
- File 2: What changes
**Tests Added**:
- Test 1: What it verifies
**Effort**: X person-days
**Risks**: What could go wrong
**Success Criteria**: How we verify completion
**Version**: vX.Y.Z

## Suggested Phases (Adapt as Needed)

1. **Quick Wins** (v1.7.2): Fix 3 bugs, add project isolation tests
2. **Test Foundation** (v1.7.3): Port embedded tests to pytest for 6 modules
3. **IVP Refactoring** (v1.8.0): Split common-functions.sh, extract hook preamble
4. **Python Cleanup** (v1.8.1): Refactor adaptive_orchestrator.py and probabilistic_router.py
5. **Performance & Polish** (v1.8.2): Cache, combine jq calls, sanitize logs
6. **Full IVP Compliance** (v2.0.0): Complete architectural refactoring

## Important Notes

- The system is **currently production-ready and working** (v1.7.1)
- These fixes improve **long-term maintainability**, not immediate functionality
- Focus on **high-value, low-risk** improvements first
- Each phase should be **independently releasable**

---

## Example Expected Output Format

```markdown
# Implementation Plan: Router System Excellence

## Overview
[Executive summary of the plan]

## Phase 1: Critical Bug Fixes (v1.7.2)
**Goal**: Eliminate all known bugs
**Effort**: 2 person-days
**Risk**: Low

### Issues Fixed
- #1: overnight_execution_runner.py signature mismatch
- #2: Hardcoded user path
- #3: load-session-memory.sh dead code

### Changes
1. `overnight_execution_runner.py:225`
   - Fix: Pass only `project_contexts` to `create_agent_executor`

2. `overnight_execution_runner.py:104`
   - Fix: Use `shutil.which('claude')` or `os.path.expanduser('~')`

3. `load-session-memory.sh`
   - Decision: Remove file (dead code) OR fix to write to memory/ directory
   - Recommendation: Remove (simpler)

### Tests Added
- `test_overnight_execution_runner.py`: Test agent executor creation
- Validation: Run overnight execution in test environment

### Success Criteria
- [ ] All 3 bugs fixed
- [ ] No regressions (run full test suite)
- [ ] overnight execution works in test environment

---

## Phase 2: Project Isolation Testing (v1.7.2)
[Continue for each phase...]
```

---

## Questions to Consider

1. Should we fix all bugs in one release or spread across phases?
2. How aggressive should IVP refactoring be? (Big bang vs incremental?)
3. Should we maintain embedded tests during transition to pytest?
4. What's the migration path for `common-functions.sh` split? (Backward compat?)
5. Target release schedule? (Weekly? Bi-weekly?)

---

**Start by creating the implementation plan. Be specific, be thorough, consider dependencies.**
