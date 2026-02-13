# Orchestration Implementation Roadmap

**Created:** 2026-02-13
**Target:** 6-week implementation plan
**Goal:** Enable deterministic routing through external orchestration

---

## Overview

This roadmap extends the existing routing system with external orchestration capabilities, focusing on high-value automated workflows while preserving interactive flexibility.

**Key Principle:** Start with proven patterns (overnight execution already uses orchestration), extend gradually based on evidence.

---

## Week 1: Foundation & Validation

**Goal:** Prove orchestration works for basic cases

### Tasks

#### 1.1 Prototype Completion
- [x] Create `orchestrate-request.py` script (DONE)
- [ ] Add command-line interface tests
- [ ] Validate integration with `routing_core.py`
- [ ] Test agent spawning with haiku/sonnet/opus
- [ ] Verify metrics recording

**Success Criteria:**
- Script can route simple requests
- 100% routing compliance in tests
- Metrics capture orchestration mode

**Deliverables:**
- Working `orchestrate-request.py`
- Test suite passing
- Basic documentation

#### 1.2 Testing Infrastructure
- [x] Create test suite (`test_orchestration.sh`) (DONE)
- [ ] Add compliance measurement tests
- [ ] Add performance benchmarks
- [ ] Test error handling

**Test Cases:**
1. Simple routing (haiku/sonnet/opus)
2. Routing fallback (when routing_core fails)
3. Agent execution with timeout
4. Metrics recording
5. Session ID tracking
6. Interactive mode
7. Error handling

**Success Criteria:**
- All tests pass
- Coverage > 80%
- Performance overhead < 500ms

#### 1.3 Documentation
- [x] Architecture analysis (DONE)
- [x] Comparison guide (DONE)
- [x] Implementation roadmap (DONE - this doc)
- [ ] User guide
- [ ] Troubleshooting guide

---

## Week 2: State Management

**Goal:** Enable session continuity and context passing

### Tasks

#### 2.1 State File Design
- [ ] Define state file schema (JSON)
- [ ] Design state lifecycle (create, update, restore)
- [ ] Implement atomic writes (flock)
- [ ] Add state validation
- [ ] Handle state corruption

**State Schema:**
```json
{
  "session_id": "20260213-143000",
  "created_at": "2026-02-13T14:30:00Z",
  "updated_at": "2026-02-13T15:45:00Z",
  "project_root": "/path/to/project",
  "routing_history": [
    {
      "timestamp": "2026-02-13T14:30:00Z",
      "request_hash": "abc123...",
      "agent": "sonnet-general",
      "result": "success"
    }
  ],
  "cached_results": {
    "search_hash_xyz": {
      "query": "ME/CFS mitochondria",
      "results": [...],
      "timestamp": "2026-02-13T14:30:00Z"
    }
  },
  "work_queue": [],
  "context": {
    "active_files": [],
    "recent_edits": [],
    "user_preferences": {}
  }
}
```

#### 2.2 State Persistence
- [ ] Implement save_state() method
- [ ] Implement load_state() method
- [ ] Add state merging (cross-session)
- [ ] Test concurrent access
- [ ] Add state cleanup (old sessions)

#### 2.3 Context Passing
- [ ] Design agent-to-agent context API
- [ ] Implement via environment variables
- [ ] Implement via temporary files
- [ ] Test context inheritance
- [ ] Validate context size limits

**Success Criteria:**
- State persists across orchestrator runs
- No data loss under concurrent access
- Agents can access session context
- State files < 10MB each

---

## Week 3: Agent Chaining

**Goal:** Support multi-agent workflows

### Tasks

#### 3.1 Workflow DSL Design
- [ ] Define workflow YAML/JSON schema
- [ ] Design agent dependencies (DAG)
- [ ] Plan result passing between agents
- [ ] Error handling in chains
- [ ] Partial execution recovery

**Workflow Example:**
```yaml
workflow:
  name: "research-analysis"
  steps:
    - id: search
      agent: haiku-general
      prompt: "Search for papers on {topic}"
      output: search_results

    - id: analyze
      agent: sonnet-general
      depends_on: [search]
      prompt: "Analyze these papers: {search_results}"
      output: analysis

    - id: write
      agent: sonnet-general
      depends_on: [analyze]
      prompt: "Write summary based on: {analysis}"
      output: summary
```

#### 3.2 Chain Executor
- [ ] Implement workflow parser
- [ ] Build dependency resolver (DAG)
- [ ] Add result passing mechanism
- [ ] Implement error recovery
- [ ] Add progress tracking

#### 3.3 Chain Testing
- [ ] Test linear chains (A → B → C)
- [ ] Test parallel chains (A → [B,C] → D)
- [ ] Test conditional chains (A → B or C)
- [ ] Test error recovery
- [ ] Test partial execution

**Success Criteria:**
- Can execute multi-step workflows
- Results flow correctly between agents
- Errors handled gracefully
- Workflows resumable after failure

---

## Week 4: Hybrid Mode Implementation

**Goal:** Auto-select routing mode based on context

### Tasks

#### 4.1 Context Detection
- [ ] Detect interactive vs batch mode
- [ ] Detect overnight execution
- [ ] Detect API calls
- [ ] Detect user preferences
- [ ] Implement override mechanism

**Detection Logic:**
```python
def detect_execution_context():
    return {
        'is_interactive': sys.stdin.isatty(),
        'is_overnight': current_hour() >= 22 or current_hour() <= 6,
        'is_batch': os.getenv('BATCH_MODE') == '1',
        'is_api': os.getenv('API_REQUEST') == '1',
        'has_workflow': workflow_file_exists(),
        'user_preference': load_user_preference()
    }
```

#### 4.2 Mode Selection
- [ ] Implement mode selector
- [ ] Add user override mechanism
- [ ] Test mode transitions
- [ ] Validate mode appropriateness
- [ ] Log mode decisions

#### 4.3 Hook Integration
- [ ] Create hybrid hook wrapper
- [ ] Integrate with existing hooks
- [ ] Test both modes
- [ ] Measure compliance rates
- [ ] Compare user experience

**Hook Wrapper:**
```bash
#!/bin/bash
# Hybrid routing hook - selects directive or orchestration mode

# Detect context
if [ "$CLAUDE_BATCH_MODE" = "1" ] || [ "$CLAUDE_OVERNIGHT" = "1" ]; then
    # Orchestration mode
    exec orchestrate-request.py --interactive
else
    # Directive mode (current behavior)
    exec user-prompt-submit.sh
fi
```

**Success Criteria:**
- Hybrid mode works in both contexts
- Mode selection is correct 95%+ of time
- Users can override easily
- No degradation in interactive UX

---

## Week 5: Production Hardening

**Goal:** Make orchestration production-ready

### Tasks

#### 5.1 Error Handling
- [ ] Comprehensive exception handling
- [ ] Graceful degradation
- [ ] Timeout management
- [ ] Circuit breakers
- [ ] Retry logic with backoff

**Error Scenarios:**
- Claude CLI not found → Fallback to directive mode
- Routing script fails → Fallback to sonnet-general
- Agent timeout → Retry once, then fail gracefully
- State corruption → Recover from backup
- Concurrent access → Lock with timeout

#### 5.2 Logging & Monitoring
- [ ] Structured logging
- [ ] Performance metrics
- [ ] Error rate tracking
- [ ] Compliance dashboards
- [ ] Alert conditions

**Metrics to Track:**
- Orchestration overhead (target < 500ms)
- Routing compliance (target > 95%)
- Agent execution success rate (target > 90%)
- State persistence failures (target < 0.1%)
- User override frequency

#### 5.3 Performance Optimization
- [ ] Minimize subprocess overhead
- [ ] Cache routing decisions
- [ ] Lazy state loading
- [ ] Parallel agent execution
- [ ] Resource limits

#### 5.4 Operational Documentation
- [ ] Deployment guide
- [ ] Configuration reference
- [ ] Troubleshooting runbook
- [ ] Monitoring setup
- [ ] Incident response procedures

**Success Criteria:**
- < 1% orchestrator failure rate
- Mean overhead < 500ms
- Clear error messages for all failures
- Operators can diagnose issues quickly
- Automated monitoring in place

---

## Week 6: Validation & Rollout

**Goal:** Validate improvements and deploy

### Tasks

#### 6.1 Compliance Measurement
- [ ] Run A/B test (directive vs orchestration)
- [ ] Measure routing compliance rates
- [ ] Track quota utilization
- [ ] Measure task completion rates
- [ ] Compare user satisfaction

**Metrics Comparison:**
| Metric | Directive | Orchestration | Target |
|--------|-----------|---------------|--------|
| Routing Compliance | 40-60% | ? | > 95% |
| Quota Utilization | 40-60% | ? | > 80% |
| Task Completion | ~50% | ? | > 90% |
| Response Time | baseline | ? | < +500ms |
| User Satisfaction | baseline | ? | >= baseline |

#### 6.2 User Acceptance Testing
- [ ] Beta test with select users
- [ ] Gather feedback
- [ ] Measure adoption
- [ ] Track issues
- [ ] Iterate based on feedback

#### 6.3 Documentation Finalization
- [ ] Update user documentation
- [ ] Create migration guide
- [ ] Update CHANGELOG
- [ ] Write blog post / announcement
- [ ] Update README

#### 6.4 Gradual Rollout
- [ ] Deploy to overnight execution (already done)
- [ ] Enable for batch workflows
- [ ] Offer opt-in for interactive users
- [ ] Monitor metrics closely
- [ ] Roll back if issues detected

**Rollout Phases:**
1. **Week 6:** Overnight execution only (already working)
2. **Week 7:** Batch workflows (low risk)
3. **Week 8:** Opt-in for power users (gather feedback)
4. **Week 9:** Hybrid mode as default (if metrics good)
5. **Week 10:** Full deployment (if no issues)

**Success Criteria:**
- Routing compliance > 95% in orchestration mode
- No degradation in interactive UX
- Quota utilization > 80%
- Task completion rate > 90%
- User satisfaction >= baseline

---

## Risk Management

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Script complexity grows unmanageable | Medium | Medium | Keep script simple, delegate to modules |
| State corruption | Low | High | Atomic writes, backups, validation |
| Agent communication failure | Medium | Medium | Use files/env vars, test thoroughly |
| Performance degradation | Medium | Medium | Benchmark, optimize, set targets |
| Claude CLI unavailable | Low | High | Fallback to directive mode |

### User Experience Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Reduced flexibility frustrates users | High | Medium | Keep directive mode available, easy override |
| Debugging becomes harder | Medium | Medium | Rich logging, clear error messages |
| Learning curve too steep | Low | Low | Good docs, gradual rollout |
| Orchestration feels "rigid" | Medium | High | Hybrid mode, user choice |

### Rollback Plan

If orchestration causes issues:
1. **Immediate:** Disable orchestration via config flag
2. **Short-term:** Revert to directive-only mode
3. **Investigation:** Analyze logs, metrics, user feedback
4. **Fix:** Address root cause
5. **Re-deploy:** With fixes, gradual rollout again

---

## Success Metrics

### Primary Metrics

1. **Routing Compliance**
   - Current: 40-60% (directive mode)
   - Target: > 95% (orchestration mode)
   - Measurement: Daily compliance reports

2. **Quota Utilization**
   - Current: 40-60% (expires unused)
   - Target: > 80% (overnight execution)
   - Measurement: Daily quota usage tracking

3. **Task Completion**
   - Current: ~50% (unbounded parallelism)
   - Target: > 90% (coordinated execution)
   - Measurement: Work queue completion rates

### Secondary Metrics

4. **Performance Overhead**
   - Target: < 500ms mean orchestration overhead
   - Measurement: Latency tracking

5. **Error Rate**
   - Target: < 1% orchestrator failures
   - Measurement: Error logs, metrics

6. **User Satisfaction**
   - Target: No degradation from baseline
   - Measurement: User surveys, session metrics

---

## Dependencies

### External Dependencies
- ✅ Claude CLI in PATH
- ✅ Python 3.8+
- ✅ Bash 4.0+
- ✅ jq (for JSON processing)
- ✅ flock (for file locking)

### Internal Dependencies
- ✅ `routing_core.py` (routing decisions)
- ✅ `metrics_collector.py` (metrics tracking)
- ✅ Hook system (integration point)
- [ ] State management module
- [ ] Workflow engine

### Infrastructure
- [x] Metrics directory (`~/.claude/.../metrics/`)
- [x] State directory (`~/.claude/.../state/`)
- [ ] Workflow directory (`~/.claude/.../workflows/`)
- [ ] Backup directory (`~/.claude/.../backups/`)

---

## Deliverables Checklist

### Code
- [x] `orchestrate-request.py` (Week 1)
- [ ] State management module (Week 2)
- [ ] Workflow engine (Week 3)
- [ ] Hybrid mode hook (Week 4)
- [ ] Error handling & monitoring (Week 5)

### Tests
- [x] Basic orchestration tests (Week 1)
- [ ] State persistence tests (Week 2)
- [ ] Workflow execution tests (Week 3)
- [ ] Hybrid mode tests (Week 4)
- [ ] Integration tests (Week 5)
- [ ] Performance benchmarks (Week 6)

### Documentation
- [x] Architecture analysis (Week 1)
- [x] Comparison guide (Week 1)
- [x] Implementation roadmap (Week 1)
- [ ] User guide (Week 4)
- [ ] Troubleshooting guide (Week 5)
- [ ] Migration guide (Week 6)

### Deployment
- [ ] Configuration schema (Week 4)
- [ ] Monitoring setup (Week 5)
- [ ] Rollout plan (Week 6)
- [ ] Rollback procedures (Week 6)

---

## Next Steps

**Immediate (This Week):**
1. ✅ Complete prototype (`orchestrate-request.py`)
2. ✅ Create test suite
3. ✅ Write architecture documentation
4. [ ] Validate basic orchestration works
5. [ ] Test with overnight execution pattern

**Short-term (Next 2 Weeks):**
1. [ ] Implement state management
2. [ ] Add workflow chaining
3. [ ] Test hybrid mode
4. [ ] Measure compliance improvements

**Medium-term (Weeks 4-6):**
1. [ ] Production hardening
2. [ ] Performance optimization
3. [ ] User acceptance testing
4. [ ] Gradual rollout

---

## Conclusion

This roadmap provides a **structured, low-risk path** to implement external orchestration while preserving the flexibility users value in interactive sessions.

**Key principles:**
- ✅ Start with proven patterns (overnight execution)
- ✅ Extend gradually based on evidence
- ✅ Preserve interactive UX
- ✅ Enable reliable automation
- ✅ Measure everything
- ✅ Rollback if needed

**Expected outcome:** Hybrid routing system that combines the flexibility of directive-based routing for interactive work with the reliability of orchestration for automated workflows, achieving 95%+ routing compliance where it matters most.
