# Before & After: Router System Architecture

## Current State (v1.7.1) vs Target State (v2.0.0)

---

## 1. File Organization

### BEFORE (Current)

```
hooks/
  common-functions.sh         # 291 lines, Purity = 0.25
                              # 5 change drivers mixed!
  user-prompt-submit.sh       # Purity = 0.25
  log-subagent-start.sh       # Purity = 0.167
  log-subagent-stop.sh        # Mixed MONITORING + COST
  [7 other hooks]             # Varying purity

implementation/
  adaptive_orchestrator.py    # 865 lines, Purity = 0.125 (WORST!)
                              # 8 change drivers in 1 file
  probabilistic_router.py     # 1,093 lines, Purity = 0.20
                              # 3 subsystems + CLI + tests
  [14 other modules]          # All mix domain + CLI + tests
```

### AFTER (Target)

```
hooks/
  lib/
    dependency-checks.sh      # Purity = 1.0, Γ = {γ_DEP}
    project-detection.sh      # Purity = 1.0, Γ = {γ_PROJ}
    project-data.sh           # Purity = 1.0, Γ = {γ_DATA}
    config-management.sh      # Purity = 1.0, Γ = {γ_CONF}
  hook-preamble.sh            # Purity = 1.0, Γ = {γ_INFRA}
  user-prompt-submit.sh       # Purity = 1.0, Γ = {γ_ROUTE}
  log-subagent-start.sh       # Purity = 1.0, Γ = {γ_MONITOR}
  track-compliance.sh         # Purity = 1.0, Γ = {γ_COMPLY}
  [other hooks refactored]    # All Purity = 1.0

implementation/
  config/
    orchestrator_config.py    # Purity = 1.0
    config_detection.py       # Purity = 1.0
  complexity/
    classifier.py             # Purity = 1.0
  orchestration/
    adaptive_orchestrator.py  # Purity = 1.0 (domain only)
    strategies.py             # Purity = 1.0
  routing/
    probabilistic_router.py   # Purity = 1.0 (domain only)
    result_validator.py       # Purity = 1.0
    optimistic_executor.py    # Purity = 1.0
  cli/
    main.py                   # Single CLI entry point
  [other modules refactored]  # All pure domain logic

tests/
  [All embedded tests moved]  # No tests in production code
```

---

## 2. Test Coverage

### BEFORE

```
Total Code:        11,194 lines
Tested:             7,449 lines (67%)
Untested:           3,745 lines (33%)

Project Isolation: ZERO tests (v1.7.1 feature!)
6 Core Modules:    NO pytest coverage
Embedded Tests:    Exist but never run
```

### AFTER

```
Total Code:        ~12,000 lines (after refactoring)
Tested:            12,000 lines (100%)
Untested:               0 lines (0%)

Project Isolation: Full test suite
All Modules:       pytest coverage
Embedded Tests:    Removed (replaced with pytest)
```

---

## 3. Known Issues

### BEFORE

**Bugs**: 3
1. Runtime crash in overnight_execution_runner.py
2. Hardcoded user path
3. Dead code in load-session-memory.sh

**Performance**: 5 issues
- Multiple jq spawns (3-5 per hook)
- Repeated directory walks (no caching)
- jq version check every invocation
- Embedded code bloat (20% of files)
- Inflated modules (domain + CLI + tests)

**Security**: 1 issue
- Unsanitized log content

**Duplication**: 2 issues
- Hook preamble (~100 lines duplicated)
- Metrics format (3 hooks duplicate logic)

### AFTER

**Bugs**: 0
**Performance**: Optimized
- 1 jq call per hook (3-5x faster)
- Cached directory walks
- One-time jq version check
- No embedded code
- Pure domain modules

**Security**: Hardened
- All log content sanitized

**Duplication**: Eliminated
- Shared hook-preamble.sh
- Shared emit-metric.sh

---

## 4. IVP Compliance

### BEFORE

| File | Purity | Drivers | Verdict |
|------|--------|---------|---------|
| adaptive_orchestrator.py | 0.125 | 8 | ❌ WORST |
| log-subagent-start.sh | 0.167 | 6 | ❌ SEVERE |
| probabilistic_router.py | 0.20 | 5 | ❌ SEVERE |
| common-functions.sh | 0.25 | 4 | ❌ CRITICAL |
| user-prompt-submit.sh | 0.25 | 4 | ❌ VIOLATION |
| session state hooks | 0.25 | 4 | ❌ VIOLATION |

**Average Purity**: 0.20
**IVP Compliant**: 0 files

### AFTER

| File | Purity | Drivers | Verdict |
|------|--------|---------|---------|
| dependency-checks.sh | 1.0 | 1 | ✅ PERFECT |
| project-detection.sh | 1.0 | 1 | ✅ PERFECT |
| project-data.sh | 1.0 | 1 | ✅ PERFECT |
| config-management.sh | 1.0 | 1 | ✅ PERFECT |
| orchestrator_config.py | 1.0 | 1 | ✅ PERFECT |
| [ALL OTHER FILES] | 1.0 | 1 | ✅ PERFECT |

**Average Purity**: 1.0
**IVP Compliant**: ALL files

---

## 5. Maintainability

### BEFORE

**Change Scenarios**:

1. **Add new dependency (e.g., require Python 3.11)**
   - Touch: `common-functions.sh` (DEPENDENCY_MANAGEMENT)
   - Risk: Could accidentally break PROJECT_DETECTION or DATA_LAYOUT
   - Lines changed: ~20 in 291-line file

2. **Change project detection logic**
   - Touch: `common-functions.sh` (PROJECT_DETECTION)
   - Risk: Could accidentally break DEPENDENCY_MANAGEMENT
   - Lines changed: ~30 in 291-line file

3. **Add compliance tracking rule**
   - Touch: `log-subagent-start.sh` (6 drivers mixed)
   - Risk: Could break MONITORING
   - Lines changed: ~40 in 179-line file

4. **Refactor orchestration strategy**
   - Touch: `adaptive_orchestrator.py` (8 drivers mixed)
   - Risk: Could break CONFIG, COMPLEXITY, CLI, or TESTS
   - Lines changed: ~100 in 865-line file

**Total Risk**: HIGH - Every change risks breaking unrelated functionality

### AFTER

**Change Scenarios**:

1. **Add new dependency (e.g., require Python 3.11)**
   - Touch: `dependency-checks.sh` ONLY
   - Risk: ZERO (file has single responsibility)
   - Lines changed: ~20 in 80-line file

2. **Change project detection logic**
   - Touch: `project-detection.sh` ONLY
   - Risk: ZERO (file has single responsibility)
   - Lines changed: ~30 in 60-line file

3. **Add compliance tracking rule**
   - Touch: `track-compliance.sh` ONLY
   - Risk: ZERO (separate from monitoring)
   - Lines changed: ~40 in 100-line file

4. **Refactor orchestration strategy**
   - Touch: `adaptive_orchestrator.py` ONLY (domain logic)
   - Risk: ZERO (config, complexity, CLI are separate)
   - Lines changed: ~100 in 300-line file

**Total Risk**: LOW - Changes are isolated by design

---

## 6. Code Quality Metrics

### BEFORE

```
┌──────────────────────────┬─────────┬────────┐
│ Metric                   │ Current │ Target │
├──────────────────────────┼─────────┼────────┤
│ Test Coverage            │   67%   │  100%  │
│ Average Purity           │  0.20   │  1.0   │
│ Known Bugs               │    3    │   0    │
│ Code Duplication         │  ~10%   │  <5%   │
│ Embedded Tests (LOC)     │  800+   │   0    │
│ Files > 500 lines        │   7     │   2    │
│ Max File Size            │ 1,093   │  500   │
│ Functions > 100 lines    │   12    │   0    │
└──────────────────────────┴─────────┴────────┘
```

### AFTER

```
┌──────────────────────────┬─────────┬────────┐
│ Metric                   │ Target  │ Status │
├──────────────────────────┼─────────┼────────┤
│ Test Coverage            │  100%   │   ✅   │
│ Average Purity           │  1.0    │   ✅   │
│ Known Bugs               │   0     │   ✅   │
│ Code Duplication         │  <5%    │   ✅   │
│ Embedded Tests (LOC)     │   0     │   ✅   │
│ Files > 500 lines        │   2     │   ✅   │
│ Max File Size            │  500    │   ✅   │
│ Functions > 100 lines    │   0     │   ✅   │
└──────────────────────────┴─────────┴────────┘
```

---

## 7. Migration Path

### Phase 1: Bug Fixes (v1.7.2)
- Fix 3 bugs
- No architectural changes
- Backward compatible

### Phase 2: Test Foundation (v1.7.3)
- Add project isolation tests
- Port embedded tests to pytest
- No code changes
- Backward compatible

### Phase 3: Hook Refactoring (v1.8.0)
- Split common-functions.sh
- Extract hook-preamble.sh
- **Backward compat wrapper** maintains old API

### Phase 4: Python Refactoring (v1.8.1)
- Split adaptive_orchestrator.py
- Split probabilistic_router.py
- **Deprecation warnings** for old imports

### Phase 5: Performance (v1.8.2)
- Optimize jq calls
- Cache directory walks
- Internal only, no API changes

### Phase 6: Full IVP (v2.0.0)
- Complete architectural refactoring
- All modules Purity = 1.0
- Clean breaks from legacy

---

## 8. Success Criteria

### v1.7.2 (Quick Wins)
- [ ] 0 known bugs
- [ ] Project isolation tested

### v1.8.0 (IVP Foundation)
- [ ] common-functions.sh split (Purity 0.25 → 1.0)
- [ ] Hook preamble extracted
- [ ] 80% test coverage

### v1.8.2 (Optimization)
- [ ] jq calls optimized (3-5x faster)
- [ ] 90% test coverage

### v2.0.0 (Excellence)
- [ ] 100% test coverage
- [ ] Purity = 1.0 for ALL files
- [ ] 0 code duplication
- [ ] 0 embedded tests
- [ ] All files < 500 lines

---

## 9. Risk vs Reward

### Current Architecture (Keep As-Is)
**Pros**:
- Works (10/10 functional quality)
- No migration effort

**Cons**:
- Hard to maintain (Purity 0.20)
- Brittle (33% untested)
- Technical debt accumulates

**Long-term Cost**: HIGH

### Target Architecture (Refactor)
**Pros**:
- Easy to maintain (Purity 1.0)
- Robust (100% tested)
- Pays off technical debt

**Cons**:
- Migration effort (~2-3 weeks)
- Some API changes (mitigated)

**Long-term Cost**: LOW

---

## 10. Bottom Line

### Current State
✅ **Functional**: Perfect (10/10)
⚠️ **Tested**: Incomplete (7/10)
❌ **Maintainable**: Poor (3/10)

→ **Works great until you need to change it**

### Target State
✅ **Functional**: Perfect (10/10)
✅ **Tested**: Complete (10/10)
✅ **Maintainable**: Excellent (10/10)

→ **Works great AND easy to evolve**

---

**Recommendation**: Proceed with refactoring in incremental phases.
The system is production-ready NOW, but will become harder to maintain over time without architectural improvements.
