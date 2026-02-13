# Orchestration vs Directives: Quick Reference

**Created:** 2026-02-13
**Purpose:** Decision guide for choosing routing approach

---

## When to Use Each Approach

### Use **Directive-Based Routing** When:

- ✅ Interactive user session
- ✅ User may want to override routing
- ✅ Request is ambiguous and needs judgment
- ✅ Exploratory workflow (user guiding)
- ✅ Edge cases that need flexibility
- ✅ User experience matters more than compliance
- ✅ One-off requests

**Example Scenarios:**
- "Help me refactor this code" (user may want specific approach)
- "Fix the authentication issue" (needs clarification)
- "Make the UI better" (subjective, needs user input)

### Use **Orchestration-Based Routing** When:

- ✅ Automated workflow (no human in loop)
- ✅ Overnight execution
- ✅ Batch processing
- ✅ API/programmatic access
- ✅ Compliance is critical
- ✅ Chained agent workflows
- ✅ Quota optimization required
- ✅ Determinism required

**Example Scenarios:**
- Overnight work queue execution
- Scheduled analysis tasks
- Multi-step search → analyze → write workflows
- Integration with external systems
- Compliance reporting

---

## Comparison Matrix

| Aspect | Directive-Based | Orchestration-Based |
|--------|----------------|---------------------|
| **Compliance Rate** | 40-60% | 100% |
| **User Flexibility** | High | Low-Medium |
| **Determinism** | Low | High |
| **Implementation Complexity** | Simple | Medium |
| **Interactive UX** | Natural | Rigid |
| **Automation Reliability** | Poor | Excellent |
| **Edge Case Handling** | Claude's judgment | Script logic |
| **Agent Chaining** | Not supported | Supported |
| **State Management** | Claude's context | External files |
| **Quota Optimization** | Limited | Full control |
| **Debugging** | Harder (black box) | Easier (logs) |
| **Override Capability** | Easy | Harder |
| **Metrics Accuracy** | Poor | Excellent |
| **Best For** | Interactive sessions | Automated workflows |

---

## Hybrid Mode (Recommended)

**Automatically choose based on context:**

```python
def select_routing_mode(context):
    # Explicit user preference
    if user_specified_mode:
        return user_specified_mode

    # Automated workflows → orchestration
    if context.is_overnight or context.is_batch:
        return 'orchestration'

    # Chained workflows → orchestration
    if context.has_workflow_chain:
        return 'orchestration'

    # API calls → orchestration
    if context.is_api_request:
        return 'orchestration'

    # Interactive sessions → directive (default)
    return 'directive'
```

**Benefits of Hybrid:**
- ✅ Best of both approaches
- ✅ Preserves interactive UX
- ✅ Enables reliable automation
- ✅ User can override when needed
- ✅ Gradual migration path

---

## Migration Strategy

### Phase 1: Orchestration for Non-Interactive Only
- Overnight execution (already implemented)
- Batch processing
- Scheduled tasks
- **Risk:** Low (doesn't affect interactive UX)
- **Value:** High (solves compliance problem)

### Phase 2: Opt-In Orchestration
- CLI flag: `--orchestrated`
- Config setting: `routing_mode: orchestration`
- Power users can choose
- **Risk:** Low (opt-in only)
- **Value:** Medium (validates approach)

### Phase 3: Data-Driven Rollout
- Measure compliance rates
- Gather user feedback
- Compare quota utilization
- **Risk:** Low (data-driven decisions)
- **Value:** High (optimized defaults)

### Phase 4: Hybrid as Default
- Auto-detect context
- Smart mode selection
- User override always available
- **Risk:** Medium (changes defaults)
- **Value:** Very High (optimal for all use cases)

---

## Implementation Checklist

### Directive-Based (Current)
- [x] Hooks generate routing recommendations
- [x] Recommendations injected into context
- [x] Claude reads and (maybe) follows
- [x] Metrics track recommendations
- [ ] Metrics track compliance (just added)

### Orchestration-Based (New)
- [x] Prototype script created (`orchestrate-request.py`)
- [x] Integration with routing_core.py
- [x] Metrics recording
- [x] Session ID tracking
- [ ] State management (files)
- [ ] Agent chaining support
- [ ] Error handling and retry
- [ ] Interactive mode detection
- [ ] Hybrid mode logic

### Testing
- [x] Basic orchestration tests
- [ ] Compliance measurement tests
- [ ] Agent chaining tests
- [ ] State persistence tests
- [ ] Error handling tests
- [ ] Performance benchmarks

---

## Key Metrics to Track

### Compliance Rate
- **Directive:** How often Claude follows routing directive
- **Orchestration:** Should be 100% by design
- **Measurement:** Compare recommended agent vs actual agent used

### User Satisfaction
- **Directive:** Flexibility and natural interaction
- **Orchestration:** Reliability and predictability
- **Measurement:** User surveys, session length, task completion

### Quota Utilization
- **Directive:** Limited optimization (Claude decides)
- **Orchestration:** Full optimization (script controls)
- **Measurement:** Daily quota usage, overnight execution success rate

### Execution Reliability
- **Directive:** ~50% completion rate (unbounded parallelism)
- **Orchestration:** Target 90%+ (coordinated execution)
- **Measurement:** Task completion metrics, work queue status

### Performance
- **Directive:** Direct Claude invocation (fast)
- **Orchestration:** Script overhead (should be < 500ms)
- **Measurement:** Latency metrics, response time

---

## Decision Tree

```
User Request
    │
    ├─ Is this overnight execution? ──→ YES ──→ Orchestration
    │
    ├─ Is this a batch workflow? ──→ YES ──→ Orchestration
    │
    ├─ Is this an API call? ──→ YES ──→ Orchestration
    │
    ├─ Does it chain multiple agents? ──→ YES ──→ Orchestration
    │
    ├─ Is compliance critical? ──→ YES ──→ Orchestration
    │
    ├─ Did user request orchestration? ──→ YES ──→ Orchestration
    │
    └─ Otherwise ──→ Directive (default)
```

---

## Summary

**Directive-Based:**
- 👍 Great for interactive sessions
- 👍 Flexible and natural
- 👎 Poor compliance (40-60%)
- 👎 Can't optimize quota reliably

**Orchestration-Based:**
- 👍 Perfect for automation
- 👍 100% routing compliance
- 👍 Enables quota optimization
- 👎 Less flexible interactively

**Hybrid (Recommended):**
- 👍 Best of both approaches
- 👍 Auto-selects based on context
- 👍 User can override
- 👍 Gradual migration path

**Recommendation:** Implement hybrid mode with directive as default for interactive sessions and orchestration for automated workflows.
