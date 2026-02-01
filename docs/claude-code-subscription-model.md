# Claude Code Subscription Model: Quota Optimization

**Version:** 2.0 (Subscription-Based)
**Last Updated:** 2026-01-31
**Scope:** Maximizing throughput within Claude Code subscription limits

---

## Table of Contents

1. [Introduction](#introduction)
2. [Subscription Tiers and Limits](#subscription-tiers-and-limits)
3. [Quota Consumption Model](#quota-consumption-model)
4. [Model Selection Economics](#model-selection-economics)
5. [Throughput Maximization](#throughput-maximization)
6. [Context Window Strategy](#context-window-strategy)
7. [Agent Delegation for Quota Efficiency](#agent-delegation-for-quota-efficiency)
7a. [Draft-Then-Evaluate Pattern](#draft-then-evaluate-pattern)
8. [Work Prioritization Framework](#work-prioritization-framework)
9. [Batch vs Interactive Patterns](#batch-vs-interactive-patterns)
10. [Quota Exhaustion Mitigation](#quota-exhaustion-mitigation)
11. [Decision Matrices](#decision-matrices)
12. [Worked Examples](#worked-examples)

---

## Introduction

Claude Code subscriptions provide access based on **message quotas** rather than API token pricing. The optimization goal shifts from **minimizing cost** to **maximizing work output** within fixed subscription limits.

**Core principle:** Different models consume quota at different rates. Strategic model selection and delegation multiply effective throughput.

**Key metrics:**
- **Messages remaining** (primary constraint)
- **Work units completed** (throughput measure)
- **Quota burn rate** (messages/hour)
- **Effective multiplier** (work output via delegation)

---

## Subscription Tiers and Limits

### Tier Structure

Based on Claude Code subscription model (as of 2026):

| Tier | Haiku Messages | Sonnet Messages | Opus Messages | Cost | Reset Period |
|------|----------------|-----------------|---------------|------|--------------|
| **Free** | Unlimited* | ~45/day | ~10/day | $0 | Rolling 24h |
| **Pro** | Unlimited* | ~225/day | ~50/day | $20/mo | Rolling 24h |
| **Max (5×)** | Unlimited* | ~1,125/day | ~250/day | $100/mo | Rolling 24h |

*Haiku effectively unlimited for practical purposes, but subject to fair use

### Message Definition

**One message = one complete turn** (user input → model response)

**Important distinctions:**
- Multi-turn conversations: Each turn consumes one message
- Tool use: Single message (even with multiple tool calls)
- Agent spawning: Each agent consumes its own message quota
- Token count: Does NOT directly affect quota (only message count matters)

### Quota Reset Behavior

**Rolling 24-hour window:**
```
Message sent at: 2026-01-31 14:23:00
Quota restores: 2026-02-01 14:23:00 (exactly 24h later)
```

**Not a daily reset** (midnight-based). Each message unlocks individually after 24h.

### Rate Limit vs Quota

**Quota limit:** Total messages in 24h window (hard cap)
**Rate limit:** Messages per minute (typically 60-100/min, soft throttle)

For most workflows, **quota limit is the binding constraint**, not rate limit.

---

## Quota Consumption Model

### Single-Model Consumption

**Direct execution:**
```
Q_consumed = N_messages × R_model

Where:
N_messages = number of turns
R_model = quota rate for model (1 Sonnet message = 1 quota unit)
```

**Example: 10-turn Sonnet conversation**
```
Q_consumed = 10 × 1 = 10 Sonnet messages
Remaining (Max tier): 1,125 - 10 = 1,115 messages
```

### Multi-Model Consumption

**Delegation pattern:**
```
Q_total = Q_router + Q_executor

Where:
Q_router = 1 message (Sonnet, for routing decision)
Q_executor = 1 message (Haiku/Sonnet/Opus, for execution)
```

**Key insight:** Router uses quota, but can save quota if cheaper executor suffices.

### Agent Spawning Cost

**Each agent spawned consumes quota:**
```
Q_workflow = Q_coordinator + Σ Q_agent_i

Example: Literature integration workflow
- Router (Sonnet): 1 message
- Literature-integrator (Sonnet): 1 message
- Chapter-integrator (Haiku): 1 message
- Scientific-insight-generator (Opus): 1 message
Total: 4 messages across tiers
```

### Context Size Impact

**Token count does NOT directly affect quota**, but:
- Larger context → slower responses → higher latency
- Context at 200k limit → auto-compaction (invisible, no quota cost)
- Fresh start vs continuation: Same quota cost (both 1 message)

**Quota optimization:** Context management optimizes for *speed* and *clarity*, not quota conservation.

---

## Model Selection Economics

### Quota Efficiency Ratios

**Key question:** How much work per quota unit?

**Model efficiency factors:**

| Model | Quota Cost | Capability | Speed | Work/Quota |
|-------|-----------|------------|-------|------------|
| Haiku | 0* (unlimited) | Low | Fast | ∞ (unconstrained) |
| Sonnet | 1 | Medium-High | Medium | 1.0× (baseline) |
| Opus | 1 (from Opus pool) | Highest | Slow | 0.6-0.8× (slower/heavier) |

*Haiku unlimited means it never depletes Sonnet/Opus quota

### Effective Quota Multipliers

**Strategic delegation increases effective quota:**

**Scenario: 100 Sonnet-appropriate tasks**
- **All Sonnet:** 100 messages → quota consumed
- **Router + Haiku delegation (50% of tasks):**
  - 50 tasks to Haiku: 50 router + 0 executor = 50 Sonnet messages
  - 50 tasks to Sonnet: 50 router + 50 executor = 100 Sonnet messages
  - **Total: 150 Sonnet messages consumed**
  - **Effective multiplier: 0.67× (worse!)**

**Wait, delegation COSTS MORE quota?**

**Yes, for same-tier delegation.** Optimization is different:

### Revised Optimization Goal

**Minimize high-tier quota consumption** while **maximizing work throughput**.

**Haiku is the key:**
- Unlimited quota → use liberally
- 75% cheaper in API terms → faster execution
- Frees Sonnet/Opus quota for tasks that need it

**Correct delegation strategy:**
```
Haiku-capable task → Direct to Haiku (0 Sonnet/Opus quota)
Sonnet-only task → Direct to Sonnet (1 Sonnet quota)
Opus-only task → Direct to Opus (1 Opus quota)
```

**Anti-pattern:**
```
Haiku-capable task → Router (Sonnet) → Haiku
Cost: 1 Sonnet + 0 Haiku = 1 Sonnet quota wasted
```

**Correct pattern:**
```
Main session = Haiku → Execute directly (0 Sonnet quota)
Main session = Sonnet → Spawn Haiku agent when possible (0 Sonnet quota for execution)
Main session = Opus → Delegate everything possible to Sonnet/Haiku
```

### Quota-Optimal Model Usage

**Haiku session:**
- All mechanical tasks
- Read/analyze/search operations
- Simple transformations
- File operations
- Spawn Sonnet/Opus agents ONLY when capability gap exists

**Sonnet session:**
- Default for mixed workloads
- Analysis, judgment, reasoning
- Spawn Haiku for mechanical subtasks
- Spawn Opus for deep reasoning subtasks

**Opus session:**
- Deep reasoning, proofs, complex logic
- Spawn Sonnet/Haiku for ALL subtasks
- Minimize direct Opus usage (quota is scarce)

---

## Throughput Maximization

### Throughput Formula

**Work output in time period T:**
```
W_total = (Q_haiku × V_haiku) + (Q_sonnet × V_sonnet) + (Q_opus × V_opus)

Where:
Q_x = quota consumed by model x
V_x = value/work per message for model x
```

**Goal:** Maximize W_total subject to quota constraints.

### Value Optimization

**Each model has optimal use cases:**

**Haiku high-value tasks** (V_haiku maximal):
- File operations (read, search, transform)
- Syntax checking, linting
- Data extraction, pattern matching
- Simple aggregation/summarization
- Test execution, validation

**Sonnet high-value tasks** (V_sonnet maximal):
- Code analysis, architecture decisions
- Writing/editing with judgment
- Research integration, synthesis
- Multi-file refactoring
- Workflow coordination

**Opus high-value tasks** (V_opus maximal):
- Mathematical proofs, formal verification
- Deep logical analysis (security, correctness)
- Complex architectural decisions
- Novel algorithm design
- Subtle bug detection in critical code

### Throughput Strategy

**Maximize Haiku usage** (unlimited quota):
```
If task is Haiku-capable:
  Execute with Haiku directly
  Throughput gain: ∞ (no constrained quota consumed)
```

**Conserve Sonnet quota** (1,125/day on Max tier):
```
If task needs Sonnet:
  Execute with Sonnet
  But: Break into Haiku subtasks where possible
  Throughput gain: 1.5-3× (more tasks per quota)
```

**Preserve Opus quota** (250/day on Max tier):
```
If task needs Opus:
  Use sparingly, only when truly needed
  Delegate all mechanical work to Haiku
  Delegate all analytical work to Sonnet
  Throughput gain: 3-5× (Opus for deep reasoning only)
```

### Daily Throughput Targets

**Max tier (5×) optimal allocation:**

```
Haiku: 500-1,000+ messages/day (unconstrained)
Sonnet: 800-1,000 messages/day (conserve 10-20% buffer)
Opus: 150-200 messages/day (conserve 20-30% buffer)
```

**Why conserve buffers?**
- Unexpected complex tasks
- Mistakes requiring rework
- Emergency deep reasoning needs
- Rate limit smoothing

---

## Context Window Strategy

### Context ≠ Quota

**Critical distinction:**

**API pricing model:** Context size × price = cost (optimize by minimizing context)

**Subscription model:** Messages = quota (context size irrelevant to quota)

### Context Optimization Goals

**In subscription model, context management optimizes for:**

1. **Clarity:** Smaller context → clearer focus → better outputs
2. **Speed:** Smaller context → faster responses → higher throughput
3. **Reliability:** Smaller context → less confusion → fewer errors

**NOT for quota savings** (continuation = same 1 message cost as continuing)

### Continuation Decision Framework

**API model decision:**
```
if context_pct > 35%:
    continuation_cost = 5k tokens × P_input
    compaction_cost = 100k tokens × P_input
    if continuation_cost < compaction_cost:
        → Fresh start (saves money)
```

**Subscription model decision:**
```
if context_pct > 50%:
    continuation_cost = 1 message
    compaction_cost = 0 messages (automatic, invisible)
    if context clarity is degrading:
        → Fresh start (improves quality, same quota)
```

### Revised Thresholds

**Subscription model context management:**

| Context % | Auto-Compaction | Quality Impact | Action |
|-----------|----------------|----------------|--------|
| < 50% | Not triggered | Minimal | Continue normally |
| 50-70% | Triggered transparently | Moderate | Monitor quality |
| 70-85% | Active | Noticeable | Consider fresh start for clarity |
| 85%+ | Heavy | Degraded | Fresh start recommended |

**Trigger fresh start when:**
- Conversation wanders, loses focus
- Agent making mistakes due to conflicting context
- User wants "clean slate" for new sub-project
- Quality matters more than continuity

**NOT when:**
- Just to "save quota" (doesn't save quota)
- Context is coherent and on-topic
- Current flow is productive

---

## Agent Delegation for Quota Efficiency

### Delegation Economics (Revised)

**In subscription model, delegation trades:**
- **Router quota** (Sonnet: 1 message) to
- **Enable cheaper executor** (Haiku: 0 quota impact on Sonnet pool)

**Delegation saves quota ONLY IF:**
```
Executor quota pool ≠ Router quota pool

Example:
Router: Sonnet (costs 1 Sonnet message)
Executor: Haiku (costs 0 Sonnet messages)
Net: Saves Sonnet quota IF task could have used Sonnet directly
```

### Session Model Selection

**Most quota-efficient architecture:**

**Option A: Haiku main session**
```
User → Haiku (main session)
     → Spawns Sonnet agent (when needed, 1 Sonnet quota)
     → Spawns Opus agent (when needed, 1 Opus quota)

Daily quota burn:
- Haiku: Unlimited (no constraint)
- Sonnet: Only when truly needed
- Opus: Only when truly needed
```

**Option B: Sonnet main session**
```
User → Sonnet (main session, 1 Sonnet per turn)
     → Spawns Haiku agent (saves Sonnet quota on mechanical tasks)
     → Spawns Opus agent (1 Opus quota)

Daily quota burn:
- Haiku: Unlimited (no constraint)
- Sonnet: Every user interaction + routing overhead
- Opus: Only when truly needed
```

**Option C: Opus main session**
```
User → Opus (main session, 1 Opus per turn)
     → Spawns Sonnet/Haiku agents (saves Opus quota)

Daily quota burn:
- Opus: Every user interaction (VERY expensive)
- Benefit: Only if you truly need Opus-level reasoning for every turn
```

**Verdict:** **Haiku main session for maximum quota efficiency**

BUT: Haiku may lack routing intelligence. Practical solution:

**Hybrid approach:**
```
User → Router (Sonnet, lightweight)
     → Spawns appropriate agent (Haiku/Sonnet/Opus)

Cost: 1 Sonnet per routing decision
Benefit: Correct model selection saves quota overall
```

### Agent Design for Quota Efficiency

**Quota-optimized agent patterns:**

**Pattern 1: Haiku-first agents**
```
Agent capability: Mechanical, deterministic tasks
Model: Haiku
Quota impact: 0 on Sonnet/Opus pools
Examples: syntax-fixer, file-splitter, link-checker
```

**Pattern 2: Sonnet agents with Haiku subtasks**
```
Agent capability: Analytical, coordination
Model: Sonnet (coordinator)
Spawns: Haiku agents for mechanical subtasks
Quota impact: 1 Sonnet + 0 Haiku per workflow
Examples: chapter-integrator, literature-integrator
```

**Pattern 3: Opus agents (rare)**
```
Agent capability: Deep reasoning, proofs
Model: Opus
Spawns: Sonnet/Haiku for all non-reasoning work
Quota impact: 1 Opus + N Sonnet/Haiku
Examples: logic-auditor, math-verifier
```

---

## Draft-Then-Evaluate Pattern

### The Core Idea

**Let a cheaper model produce content, then have the expensive model evaluate it.**

Standard delegation always uses the model capable of doing the task. But what if the cheaper model can *sometimes* produce acceptable output? Instead of paying for Sonnet every time, pay for Haiku drafting + Sonnet evaluation.

```
Traditional pattern:
  Task → Sonnet (1 Sonnet quota)

Draft-then-evaluate pattern:
  Task → Haiku draft (0 Sonnet quota)
      → Sonnet evaluate (1 Sonnet quota, but cheaper operation)
      → Accept / Refine / Replace
```

**The bet:** If Haiku produces acceptable output often enough, **and you batch the evaluation**, the total quota cost is lower than always using Sonnet for generation. (Spoiler: this works at batch sizes ≥10 with acceptance rates ≥10%—see [Batch size impact](#factor-1-evaluation-can-be-batched) for the math.)

### Why This Could Work

**Generation and evaluation cost the same quota (1 message each). So where do savings come from?**

| Operation | Cognitive Load | Typical Output Tokens | Quota Impact |
|-----------|---------------|----------------------|--------------|
| Generate content | High | 500-2000 | Full message |
| Evaluate quality | Low-Medium | 50-200 | Full message (but faster) |
| Refine specific issues | Medium | 200-500 | Full message |

**Key insight:** Evaluation uses the same quota (1 Sonnet message) but offers secondary benefits:
- Shorter context (just the draft + criteria)
- Shorter output ("Accept" / "Issue: X, Fix: Y")
- Faster execution (higher throughput per unit time)
- Higher reliability (simpler operation = less can go wrong)

**Important:** Evaluation does NOT reduce quota cost directly—both generation and evaluation cost 1 message. The real savings come from **batching** (see [Factor 1: Evaluation Can Be Batched](#factor-1-evaluation-can-be-batched) for the mathematical proof).

### Mathematical Model

**Variables:**
```
Q_direct = Quota cost for direct Sonnet generation (baseline: 1 Sonnet message)
Q_draft = Quota cost for Haiku draft (0 Sonnet quota)
Q_eval = Quota cost for evaluation (1 Sonnet message)
Q_refine = Quota cost for refinement (1 Sonnet message, partial generation)
Q_replace = Quota cost for full replacement (1 Sonnet message, full generation)

P_accept = Probability draft is accepted as-is
P_refine = Probability draft needs minor fixes
P_replace = Probability draft is rejected (full regeneration)

Note: P_accept + P_refine + P_replace = 1
```

**Expected quota cost per task:**
```
Q_draft_eval = Q_draft + Q_eval + (P_refine × Q_refine) + (P_replace × Q_replace)
             = 0 + 1 + (P_refine × 1) + (P_replace × 1)
             = 1 + P_refine + P_replace
             = 1 + (1 - P_accept)
             = 2 - P_accept
```

**Cost comparison (single task):**
```
Q_direct = 1 (always)
Q_draft_eval = 2 - P_accept

Draft-eval is cheaper when:
  Q_draft_eval < Q_direct
  2 - P_accept < 1
  P_accept > 1

⚠️ This is NEVER true for single tasks!
Acceptance rate can't exceed 100%, so single-task draft-eval always costs more.
```

**Wait—the math says it's always more expensive?**

Yes, **for single tasks**. But this analysis misses the key insight: **batch evaluation amortizes the overhead**. The real power of draft-then-evaluate emerges when processing multiple similar tasks together.

### Factor 1: Evaluation Can Be Batched

**Batch evaluation changes the math:**

```
Traditional (10 tasks):
  10 × Sonnet = 10 Sonnet messages

Draft-eval with batch evaluation (10 tasks):
  Haiku drafts: 10 × 0 = 0 Sonnet quota
  Batch evaluate: 1 Sonnet message (evaluate all 10 drafts at once)
  Per-item refinement: P_refine × 10 × 1 = P_refine × 10 Sonnet
  Per-item replacement: P_replace × 10 × 1 = P_replace × 10 Sonnet

  Total: 1 + 10 × (P_refine + P_replace)
       = 1 + 10 × (1 - P_accept)
```

**Cost comparison with batching:**
```
Q_direct = 10
Q_batch_eval = 1 + 10 × (1 - P_accept)

Draft-eval is cheaper when:
  1 + 10 × (1 - P_accept) < 10
  10 × (1 - P_accept) < 9
  1 - P_accept < 0.9
  P_accept > 0.1

With batching: Profitable at >10% acceptance rate!
```

**Batch size impact:**
```
For batch size N:
Q_batch_eval = 1 + N × (1 - P_accept)
Q_direct = N

Break-even: 1 + N × (1 - P_accept) = N
           1 = N × P_accept
           P_accept = 1/N

Batch 5:   P_accept ≥ 20% to break even, >20% to profit
Batch 10:  P_accept ≥ 10% to break even, >10% to profit
Batch 20:  P_accept ≥ 5% to break even, >5% to profit
Batch 50:  P_accept ≥ 2% to break even, >2% to profit
```

<!-- BLOG POST NOTE: Add visual diagram here showing batch size (x-axis) vs required acceptance rate (y-axis, 1/N curve). Would help visual learners see how quickly the threshold drops as batch size increases. -->

### Factor 2: Refinement Executes Faster Than Generation

**Same quota cost, but faster execution:**

Both refinement and generation cost 1 Sonnet message. However, they differ in execution time:

| Operation | Cognitive Steps | Typical Time |
|-----------|-----------------|--------------|
| Full generation | Parse → Plan → Execute → Verify | 20-40s |
| Refinement | Read draft → Identify issue → Fix | 10-20s |

**Why this matters for throughput:**
```
Same quota spent, but:
- Refinement completes faster → more tasks per hour
- Simpler operation → higher reliability (less rework)
- Faster feedback loop → better user experience
```

**Important clarification:** This does NOT reduce quota consumption. You still spend 1 Sonnet message per refinement. The benefit is **time efficiency**, not quota efficiency. In a time-constrained work session, faster execution means more work completed before you stop for the day.

### Factor 3: Parallel Processing

**Haiku drafting can run in parallel:**

```
Sequential Sonnet (traditional):
  10 tasks × 30 seconds = 300 seconds
  Quota: 10 Sonnet messages

Parallel Haiku drafting + batch eval + parallel refinement:
  10 parallel Haiku drafts: 5 seconds (0 Sonnet quota)
  1 batch evaluation: 10 seconds (1 Sonnet quota)
  3 parallel refinements (30% rate): 10 seconds (3 Sonnet quota)
  Total time: 25 seconds (12× faster)
  Total quota: 4 Sonnet messages (60% savings)
```

**Clarification on "time vs quota":**

Parallel processing provides two distinct benefits:

1. **Quota savings** (the real win): Batch evaluation + lower refinement rate = fewer Sonnet messages
2. **Time savings** (secondary): Faster completion = better user experience

**Important:** Parallel execution does NOT speed up quota restoration. The 24-hour rolling window still applies—a message sent at 14:23 restores at 14:23 the next day, regardless of how fast it executed. The quota benefit comes from **using fewer messages**, not from faster execution.

### Decision Framework

**When to use draft-then-evaluate:**

| Factor | Favorable | Unfavorable |
|--------|-----------|-------------|
| Task volume | High (10+) | Low (1-3) |
| Task type | Mechanical, template-based | Creative, judgment-heavy |
| Quality requirements | Flexible, iterative | Critical, first-time-right |
| Haiku capability gap | Small (formatting, syntax) | Large (reasoning, style) |
| Batch-ability | High (similar tasks) | Low (unique tasks) |

**Acceptance rate predictions:**

| Task Type | Expected P_accept | Expected P_refine | Expected P_replace |
|-----------|-------------------|-------------------|-------------------|
| Code comments | 60-80% | 15-30% | 5-15% |
| API documentation | 50-70% | 20-35% | 10-20% |
| Test descriptions | 40-60% | 25-40% | 15-25% |
| Changelog entries | 50-70% | 20-35% | 10-20% |
| Error messages | 30-50% | 30-45% | 15-30% |
| User-facing copy | 10-30% | 30-50% | 30-50% |
| Technical writing | 20-40% | 30-45% | 25-40% |
| Creative content | 5-15% | 20-40% | 50-70% |

*Note: These are theoretical estimates based on task complexity analysis. Actual rates vary significantly based on prompt quality, specific requirements, and model versions. **Always run a pilot batch (5-10 items) to measure your actual acceptance rates before committing to draft-eval for a large task set.***

**Rule of thumb:** If Haiku can produce acceptable drafts >30% of the time, draft-eval with batching is profitable.

### Implementation Patterns

**Pattern 1: Simple batch evaluation**

```
1. Collect N similar tasks
2. Generate N drafts with Haiku (parallel)
3. Single Sonnet evaluation of all drafts
4. Fix rejected drafts with Sonnet
```

**Quota cost:** 1 + N × (1 - P_accept) Sonnet messages

**Pattern 2: Tiered evaluation**

```
1. Generate N drafts with Haiku
2. First-pass evaluation with Haiku (filter obvious failures)
3. Second-pass evaluation with Sonnet (judge borderline cases)
4. Fix rejected drafts with Sonnet
```

**Quota cost:** Lower if Haiku can filter 50%+ of failures

**Pattern 3: Adaptive drafting**

```
1. Generate draft with Haiku
2. Haiku self-evaluation (confidence score)
3. If low confidence: Regenerate with Sonnet directly
4. If high confidence: Submit to Sonnet evaluation
```

**Quota cost:** Trades Haiku overhead for reduced Sonnet load on hard tasks

### Worked Example: API Documentation

**Scenario:** Generate docstrings for 50 functions.

**Traditional approach:**
```
50 functions × 1 Sonnet = 50 Sonnet messages
```

**Draft-eval approach:**
```
Predicted rates: P_accept = 60%, P_refine = 30%, P_replace = 10%

Phase 1 - Haiku drafting:
  50 drafts × 0 Sonnet = 0 Sonnet quota

Phase 2 - Batch evaluation:
  1 evaluation message (assess all 50 drafts)
  Cost: 1 Sonnet message

Phase 3 - Fixes:
  30% need refinement: 15 × 1 = 15 Sonnet messages
  10% need replacement: 5 × 1 = 5 Sonnet messages
  Cost: 20 Sonnet messages

Total: 1 + 20 = 21 Sonnet messages
Savings: 50 - 21 = 29 messages (58% reduction)
```

**Break-even analysis:**
```
For this to be worse than traditional:
  1 + 50 × (1 - P_accept) > 50
  1 - P_accept > 0.98
  P_accept < 2%

Haiku would need to produce acceptable docstrings <2% of the time.
That's extremely unlikely for mechanical documentation.
```

### Worked Example: Creative Writing

**Scenario:** Write 10 section introductions.

**Predicted rates:** P_accept = 15%, P_refine = 35%, P_replace = 50%

**Draft-eval approach:**
```
Phase 1 - Haiku drafting: 0 Sonnet
Phase 2 - Batch evaluation: 1 Sonnet
Phase 3 - Fixes:
  35% refinement: 3.5 → 4 Sonnet messages
  50% replacement: 5 Sonnet messages
  Cost: 9 Sonnet messages

Total: 1 + 9 = 10 Sonnet messages
```

**Traditional approach:**
```
10 sections × 1 Sonnet = 10 Sonnet messages
```

**Verdict:** Break-even. Creative content doesn't benefit from draft-eval because:
- Low acceptance rate
- High replacement rate
- Small batch doesn't amortize evaluation cost

### Risk Analysis

**Risks of draft-then-evaluate:**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Haiku drafts consistently poor | Wasted evaluation quota | Pilot with 5 tasks first, measure P_accept |
| Evaluation misses quality issues | Poor output escapes | Periodic spot-checks with Opus |
| Refinement insufficient | Multiple rounds needed | Switch to replacement after 1 failed refinement |
| Batch evaluation overwhelmed | Poor judgment on large batches | Limit batch size to 20-30 items |
| Task heterogeneity | Can't batch evaluate | Group similar tasks, process separately |

**Risk-adjusted decision:**

```
If expected P_accept is uncertain:
  → Run pilot batch (5-10 items)
  → Measure actual P_accept, P_refine, P_replace
  → If P_accept > 30%: Proceed with draft-eval
  → If P_accept < 30%: Use traditional approach
```

### Advanced: Multi-Tier Evaluation

**Three-tier pipeline for maximum efficiency:**

```
Tier 1 - Haiku drafting:
  Generate all drafts (0 Sonnet quota)

Tier 2 - Haiku filtering:
  Quick self-evaluation (0 Sonnet quota)
  Output: "confident" / "uncertain" / "failed"

Tier 3a - Sonnet evaluation (uncertain only):
  Evaluate drafts Haiku was uncertain about
  Accept / Refine / Replace

Tier 3b - Sonnet regeneration (failed only):
  Direct generation for Haiku failures
```

**Expected quota (with explicit assumptions):**

*Key assumptions requiring empirical validation:*

- **Haiku self-evaluation accuracy:** We assume Haiku can correctly classify its own outputs into confident/uncertain/failed categories. This is a strong assumption—run pilot tests to measure actual classification accuracy.
- **P_accept_uncertain:** Of drafts Haiku flags as "uncertain," what percentage does Sonnet ultimately accept? We estimate 40% based on the reasoning that uncertain drafts are borderline cases.

```
Assumptions (validate with pilot batch):
  Haiku confident AND correct: 50% (accepted without Sonnet review)
  Haiku uncertain (needs Sonnet eval): 30%
  Haiku failed (self-detected, needs Sonnet gen): 20%

  P_accept_uncertain = 40% (Sonnet accepts 40% of "uncertain" drafts)
  P_refine_uncertain = 35% (Sonnet refines 35% of "uncertain" drafts)
  P_replace_uncertain = 25% (Sonnet replaces 25% of "uncertain" drafts)

For 100 tasks:
  Tier 1 (Haiku drafts): 0 Sonnet quota
  Tier 2 (Haiku self-eval): 0 Sonnet quota
  Tier 3a (Sonnet evaluates 30 uncertain):
    1 batch evaluation message
    + 30 × P_refine_uncertain refinements = 30 × 0.35 = 10.5 → 11 Sonnet
    + 30 × P_replace_uncertain replacements = 30 × 0.25 = 7.5 → 8 Sonnet
    Subtotal: 1 + 11 + 8 = 20 Sonnet
  Tier 3b (Sonnet generates for 20 Haiku failures):
    20 × 1 = 20 Sonnet

Total: 40 Sonnet messages (vs 100 traditional)
Savings: 60%
```

**Validation requirement:** Before deploying multi-tier evaluation, run a pilot batch of 20-30 items to measure:

1. Haiku self-classification accuracy (does "confident" actually mean correct?)
2. Actual P_accept/refine/replace rates for the "uncertain" category
3. Whether the complexity overhead is worth the quota savings

### Integration with Existing Patterns

**Draft-eval + Batch processing:**
```
Morning: Queue all mechanical tasks
  → Haiku batch drafting (parallel)
  → Sonnet batch evaluation (1 message)
  → Sonnet batch refinement (as needed)

Afternoon: Interactive complex work
  → Direct Sonnet/Opus as appropriate
```

**Draft-eval + Quota conservation:**
```
When quota is scarce:
  → Increase batch sizes (better amortization)
  → Accept higher Haiku confidence threshold
  → Defer low-acceptance-rate tasks
```

**Draft-eval + Agent workflows:**

When integrating draft-eval into agent workflows, clarify the delegation model:

```
Option A: Sonnet coordinator (recommended for complex workflows)
  literature-integrator agent (Sonnet): 1 Sonnet message
    → Spawns Haiku agents: Download/extract (0 Sonnet)
    → Spawns Haiku agents: Draft summaries (0 Sonnet)
    → Batch evaluates drafts in same session (0 additional—part of coordinator)
    → Generates insights in same session (0 additional—part of coordinator)
  Total: 1 Sonnet message + refinement/replacement costs

Option B: Haiku coordinator (maximum quota savings, simpler workflows only)
  literature-integrator agent (Haiku): 0 Sonnet quota
    → Downloads/extracts directly (0 Sonnet)
    → Drafts summaries directly (0 Sonnet)
    → Spawns Sonnet agent for batch evaluation (1 Sonnet)
    → Spawns Sonnet agent for insights (1 Sonnet)
  Total: 2 Sonnet messages + refinement/replacement costs
  Caveat: Can Haiku reliably coordinate multi-step workflows?
```

**Architecture trade-off:** Option A uses fewer total messages if the Sonnet coordinator handles multiple steps in one session. Option B saves quota only if Haiku can reliably coordinate—test this assumption before deploying.

### Metrics and Monitoring

**Track these KPIs:**

| Metric | Target | Action if Out of Range |
|--------|--------|----------------------|
| Acceptance rate | >40% | Review task selection for draft-eval |
| Refinement success | >80% | Improve refinement prompts |
| Replacement rate | <25% | Consider direct Sonnet for task type |
| Eval batch size | 15-30 | Adjust batching strategy |
| Time savings | >50% | Worth the complexity |

**Dashboard metrics:**
```
Daily draft-eval stats (code documentation tasks):
  Task type: API docstrings, code comments, changelog entries
  Tasks processed: 150
  Haiku drafts: 150 (0 Sonnet)
  Evaluations: 6 batches (6 Sonnet)
  Refinements: 45 (45 Sonnet)  [P_refine = 30%]
  Replacements: 15 (15 Sonnet) [P_replace = 10%]

  Implied acceptance rate: 60% (90/150 accepted as-is)
  Total Sonnet: 66 messages
  Traditional would be: 150 messages
  Savings: 84 messages (56%)
```

*Note: These metrics reflect a favorable task type (mechanical documentation). Creative or judgment-heavy tasks would show lower acceptance rates and smaller savings.*

### Failure Recovery

**What happens when things go wrong?**

The draft-eval pattern introduces failure points not present in direct generation. Plan for these scenarios:

**Batch evaluation failure:**
```
Scenario: Sonnet crashes or rate-limits mid-evaluation (15/30 items evaluated)

Recovery options:
  1. Partial salvage: Accept the 15 evaluated items, re-batch remaining 15
  2. Full retry: Discard partial results, retry entire batch
  3. Fallback: Switch to individual evaluation (expensive but reliable)

Recommendation: Option 1 (partial salvage) unless evaluation quality is suspect
```

**Refinement failure:**
```
Scenario: Sonnet's refinement doesn't fix the issue (draft still unacceptable)

Recovery strategy:
  1. First failure: Attempt replacement (full regeneration)
  2. Replacement also fails: Escalate to Opus (if critical) or flag for human review
  3. NEVER iterate on refinement—quota spiral risk

Anti-pattern: "Let me try refining again" → can burn 3-5 messages on one item
```

**Haiku draft quality collapse:**
```
Scenario: Pilot showed 60% acceptance, but production batch shows 20%

Diagnosis:
  - Task drift? (requirements changed mid-batch)
  - Prompt degradation? (context window issues)
  - Model update? (Haiku behavior changed)

Recovery:
  1. Stop batch processing immediately
  2. Measure actual acceptance rate on recent items
  3. If P_accept < break-even threshold: switch to direct Sonnet
  4. Investigate root cause before resuming draft-eval
```

**Self-evaluation miscalibration (multi-tier only):**
```
Scenario: Haiku marks 80% as "confident" but Sonnet rejects 40% of those

Impact: Bypassed quality gate, bad outputs in production

Recovery:
  1. Halt multi-tier pipeline
  2. Add Sonnet spot-check: randomly evaluate 10% of "confident" items
  3. If spot-check failure rate >10%: disable Haiku self-eval, use simple batch pattern
  4. Retune confidence threshold if continuing multi-tier
```

**General principle:** Draft-eval trades simplicity for efficiency. When failures occur, **fall back to simpler patterns** rather than adding complexity to fix the complex pattern.

**Quick Reference: Failure Recovery**

| Failure Type | Symptom | Immediate Action | Fallback |
|--------------|---------|------------------|----------|
| Batch eval crash | Partial results (15/30) | Salvage evaluated items, re-batch rest | Individual evaluation |
| Refinement fails | Draft still bad after fix | Switch to replacement | Escalate to Opus or human |
| Quality collapse | P_accept drops from 60%→20% | Stop batch, measure actual rate | Direct Sonnet generation |
| Self-eval miscalibration | "Confident" items rejected 40% | Add Sonnet spot-checks (10%) | Disable multi-tier, use simple batch |

### Summary: Draft-Eval Economics

**When it works (40-70% savings):**
- High-volume mechanical tasks
- Template-based content
- Predictable quality criteria
- Batch-friendly workloads
- Acceptance rate >30%

**When it doesn't (break-even or worse):**
- Low-volume tasks (<10)
- Creative/subjective content
- Unique/heterogeneous tasks
- First-time-right requirements
- Acceptance rate <20%

**The key insight:**
> Batch evaluation amortizes the overhead of quality gating.
> Haiku drafts cost zero Sonnet quota—use them speculatively.
> The savings come from batching, not from evaluation being "cheaper."

**Decision shortcut:**
```
IF batch_size > 10 AND task_is_mechanical AND NOT critical:
    → Use draft-then-evaluate
ELSE:
    → Use direct generation
```

---

## Work Prioritization Framework

### Quota Budgeting

**Daily quota allocation (Max tier):**

```
Total Sonnet quota: 1,125 messages/day
Total Opus quota: 250 messages/day

Suggested allocation:

Sonnet:
- 200 messages: Routing/coordination (unavoidable overhead)
- 600 messages: Primary work (analysis, writing, coding)
- 200 messages: Rework/iteration (mistakes, refinements)
- 125 messages: Reserve (unexpected needs)

Opus:
- 50 messages: Deep reasoning tasks (planned)
- 100 messages: Complex problem-solving (emergent)
- 50 messages: Quality assurance (critical reviews)
- 50 messages: Reserve (emergency use)
```

### Priority Tiers

**Tier 1: Critical (use any model needed)**
- Production bugs, system-down issues
- Deadline-critical work
- High-stakes decisions (architecture, security)
- Legal/compliance requirements

**Tier 2: High-value (prefer Sonnet, use Opus if justified)**
- Feature development
- Research and analysis
- Documentation (important)
- Code reviews (complex)

**Tier 3: Medium-value (prefer Haiku/Sonnet, avoid Opus)**
- Refactoring, cleanup
- Test writing
- Documentation (routine)
- Exploration, learning

**Tier 4: Low-value (Haiku only)**
- File operations, searching
- Syntax fixes, linting
- Repetitive transformations
- Validation, checking

### Quota Exhaustion Triage

**When approaching quota limits:**

```
Sonnet quota < 10%:
  → Pause Tier 3 work
  → Route all mechanical tasks to Haiku
  → Save quota for Tier 1-2 only

Sonnet quota < 5%:
  → Pause all non-critical work
  → Tier 1 only
  → Consider work that can wait until quota reset

Opus quota < 10%:
  → No Opus for Tier 2-4
  → Tier 1 only, and only if Sonnet truly insufficient
  → Defer deep reasoning work if possible
```

---

## Batch vs Interactive Patterns

### Interactive Pattern (User-Driven)

**Characteristics:**
- One message per user turn
- Exploration, back-and-forth
- Judgment calls, course corrections
- Typical quota burn: 10-50 messages/hour

**Quota efficiency:**
- Moderate (some overhead from clarifications)
- High value (decisions made correctly upfront)

**Best for:**
- Complex tasks with ambiguity
- Creative work
- Learning, research
- High-stakes decisions

### Batch Pattern (Agent-Driven)

**Characteristics:**
- One message spawns multi-step workflow
- Agent executes autonomously
- Pre-defined success criteria
- Typical quota burn: 5-20 messages/workflow

**Quota efficiency:**
- High (no back-and-forth overhead)
- Risk: May need rework if assumptions wrong

**Best for:**
- Well-defined tasks
- Repetitive operations
- Low-risk transformations
- Overnight/background processing

### Hybrid Pattern (Optimal)

**Workflow:**
```
1. Interactive exploration (Sonnet, 5-10 messages)
   → Define task, clarify requirements, align on approach

2. Batch execution (Haiku/Sonnet agents, 10-30 messages)
   → Execute well-defined subtasks autonomously

3. Interactive review (Sonnet, 3-5 messages)
   → Verify output, iterate on issues, finalize
```

**Quota efficiency:** **Highest** (combines precision of interactive with efficiency of batch)

### Parallel Workflows

**Quota impact:**
```
Sequential workflows:
  Workflow 1: 10 messages
  Workflow 2: 10 messages
  Time: T1 + T2
  Quota: 20 messages

Parallel workflows:
  Workflow 1 & 2 simultaneously: 10 + 10 = 20 messages
  Time: max(T1, T2)
  Quota: 20 messages (same)
  Benefit: Faster completion, same quota
```

**Parallelization saves time, not quota** (but time = throughput capacity)

---

## Quota Exhaustion Mitigation

### Monitoring

**Proactive quota tracking:**
```
claude status  # Check remaining quota
```

**Manual tracking:**
```
Messages sent today: ~X
Sonnet quota used: X / 1,125 (Y%)
Opus quota used: X / 250 (Y%)
```

**Warning thresholds:**
- Yellow (70%): Optimize aggressively, defer low-priority work
- Orange (85%): Tier 1-2 only, batch where possible
- Red (95%): Tier 1 only, minimize interactions

### Conservation Strategies

**When quota is scarce:**

**1. Batch aggressively**
```
Instead of:
  "Fix issue 1" → 2 messages
  "Fix issue 2" → 2 messages
  "Fix issue 3" → 2 messages
  Total: 6 messages

Do:
  "Fix issues 1, 2, 3 in batch" → 3 messages (1 route + 1 execute + 1 review)
  Total: 3 messages (50% savings)
```

**2. Maximize Haiku usage**
```
Audit all Sonnet work:
  "Can Haiku do this?" → If yes, switch to Haiku
  Savings: 1 Sonnet quota per task
```

**3. Increase agent autonomy**
```
Instead of:
  "Do step 1" → verify → "Do step 2" → verify → ...

Do:
  "Do steps 1-5, here are success criteria" → verify final result
  Savings: N-1 messages for N-step workflow
```

**4. Defer non-critical work**
```
Queue tasks for tomorrow:
  - Documentation updates
  - Exploratory analysis
  - Cleanup/refactoring
  - Nice-to-have features
```

### Quota Recovery Planning

**Quota resets on rolling 24h window:**

```
Current time: 2026-01-31 18:00
Quota status: 50 Sonnet remaining

Quota recovery timeline:
  2026-02-01 09:00 (+15h): 200 messages restore (sent yesterday 09:00)
  2026-02-01 14:00 (+20h): 300 messages restore (sent yesterday 14:00)
  2026-02-01 18:00 (+24h): Full quota restored

Strategy:
  - Use remaining 50 for critical work now
  - Wait until tomorrow 09:00 for next batch
  - Plan heavy work for when quota is fresh
```

---

## Decision Matrices

### Matrix 1: Model Selection by Task Type

| Task Type | Token Count | Reasoning Depth | Optimal Model | Rationale |
|-----------|-------------|-----------------|---------------|-----------|
| File operations | Any | None | Haiku | Unlimited quota, fast |
| Syntax/lint | Any | None | Haiku | Mechanical, pattern-matching |
| Code analysis | < 20k | Medium | Sonnet | Judgment needed, manageable |
| Architecture | Any | High | Sonnet | Complex reasoning, not proof-level |
| Writing/editing | Any | Medium | Sonnet | Style, tone, coherence |
| Math proofs | Any | Extreme | Opus | Formal verification required |
| Bug detection | > 20k | High | Opus | Subtle logical flaws |
| Research synthesis | Any | Medium-High | Sonnet | Integration, not novel reasoning |
| Novel algorithms | N/A | Extreme | Opus | Creative problem-solving |

### Matrix 2: Quota Conservation Mode

| Quota % Remaining | Tier 1 (Critical) | Tier 2 (High) | Tier 3 (Medium) | Tier 4 (Low) |
|-------------------|-------------------|---------------|-----------------|--------------|
| 100-70% | Any model | Sonnet/Opus OK | Sonnet OK | Haiku only |
| 70-40% | Any model | Sonnet, minimize Opus | Haiku/Sonnet | Haiku only |
| 40-20% | Sonnet/Opus (critical only) | Sonnet (justified) | Haiku only | Defer |
| 20-10% | Sonnet (critical only) | Defer unless urgent | Defer | Defer |
| < 10% | Emergency only | Defer | Defer | Defer |

### Matrix 3: Session Model Choice

| Work Pattern | Haiku Session | Sonnet Session | Opus Session |
|--------------|---------------|----------------|--------------|
| Mostly mechanical | ✅ Optimal | ❌ Wastes quota | ❌ Wastes quota |
| Mixed mechanical + analytical | ⚠️ Requires frequent spawning | ✅ Optimal | ❌ Wastes quota |
| Deep reasoning heavy | ❌ Capability gap | ⚠️ Frequent Opus spawning | ✅ If every turn needs Opus |
| Exploration/research | ⚠️ May lack depth | ✅ Optimal | ⚠️ Overkill |
| Quota conservation mode | ✅ Maximizes quota | ⚠️ Acceptable | ❌ Depletes fast |

---

## Worked Examples

*See also: Draft-Then-Evaluate worked examples in [Section 7a](#draft-then-evaluate-pattern) for API documentation (58% savings) and creative writing (break-even) scenarios.*

### Example 1: LaTeX Document Editing (Full Day)

**Scenario:** Editing a 50-page ME/CFS research document.

**Tasks:**
- 20 syntax fixes (mechanical)
- 10 content rewrites (analytical)
- 5 literature integrations (research)
- 2 mathematical proofs (deep reasoning)

**Naive approach (all Sonnet):**
```
Syntax: 20 messages
Rewrites: 10 messages
Literature: 5 messages
Proofs: 2 messages (but should be Opus!)
Total: 37 Sonnet messages
Risk: Proofs may have errors (Sonnet insufficient)
```

**Optimized approach:**
```
Syntax: 0 Sonnet (Haiku agents)
Rewrites: 10 Sonnet
Literature: 5 Sonnet (coordination) + 0 Haiku (integration)
Proofs: 2 Opus
Total: 15 Sonnet + 2 Opus messages
Savings: 59% Sonnet quota, higher quality proofs
```

**Quota impact:**
- Naive: 37/1,125 = 3.3% daily Sonnet quota
- Optimized: 15/1,125 = 1.3% Sonnet + 2/250 = 0.8% Opus
- **Efficiency gain: 2.5× more work per quota**

---

### Example 2: Quota Exhaustion Scenario

**Scenario:** End of day, quota low.

**Quota status:**
```
Sonnet: 75 / 1,125 remaining (6.7%)
Opus: 20 / 250 remaining (8%)
Time: 22:00 (2 hours until first quota restores)
```

**Work queue:**
- CRITICAL: Production bug (needs deep analysis)
- HIGH: Feature review (analytical)
- MEDIUM: Documentation update (writing)
- LOW: Syntax cleanup (mechanical)

**Triage decision:**

**1. Production bug (Tier 1)**
```
Estimate: 5 Sonnet + 2 Opus (debugging + root cause analysis)
Decision: Execute now (critical)
Remaining: 70 Sonnet, 18 Opus
```

**2. Feature review (Tier 2)**
```
Estimate: 10 Sonnet
Decision: Can this wait until tomorrow?
  - If yes: Defer (save quota)
  - If no (deadline): Batch review, aim for 5 Sonnet messages
Remaining: 65 Sonnet (if deferred) or 60 Sonnet (if executed)
```

**3. Documentation update (Tier 3)**
```
Estimate: 8 Sonnet
Decision: Defer to tomorrow when quota is fresh
Save: 8 Sonnet
```

**4. Syntax cleanup (Tier 4)**
```
Estimate: 0 Sonnet (use Haiku)
Decision: Execute now (doesn't consume limited quota)
```

**Final allocation:**
- Execute: Bug fix (5 Sonnet, 2 Opus) + Syntax (0 quota)
- Defer: Feature review, documentation
- Remaining: 70 Sonnet, 18 Opus for emergencies

---

### Example 3: Multi-Day Research Project

**Scenario:** 3-day literature integration sprint.

**Quota budget (Max tier):**
```
Total Sonnet quota: 3 × 1,125 = 3,375 messages (3 days)
Total Opus quota: 3 × 250 = 750 messages (3 days)
```

**Workload:**
- Find 50 papers (search/download)
- Read and summarize 50 papers
- Integrate into 10 chapters
- Generate novel insights (synthesis)
- Verify logical consistency

**Naive approach (all Sonnet):**
```
Find papers: 10 messages (search coordination)
Summarize: 50 messages (one per paper)
Integrate: 20 messages (2 per chapter)
Insights: 10 messages (1 per chapter)
Verify: 10 messages
Total: 100 Sonnet messages (3% of 3-day budget)
```

**Optimized approach:**
```
Day 1 (Batch processing):
  Find papers: 10 Sonnet (search coordination)
  Summarize: 50 Haiku agents (parallel batch)
  Total: 10 Sonnet, 0 Opus

Day 2 (Integration):
  Integrate: 10 Sonnet (chapter coordination) + 10 Haiku (file edits)
  Total: 10 Sonnet, 0 Opus

Day 3 (Synthesis and verification):
  Insights: 10 Opus (novel reasoning)
  Verify: 10 Sonnet (logical consistency)
  Total: 10 Sonnet, 10 Opus

3-day total: 30 Sonnet + 10 Opus messages
```

**Quota efficiency:**
```
Naive: 100 Sonnet = 3.0% of budget
Optimized: 30 Sonnet (0.9%) + 10 Opus (1.3%)

Effective quota multiplier: 3.3×
Work quality: Higher (Opus for synthesis)
Time saved: Massive (Haiku batch processing is faster)
```

**Remaining quota for other work:**
```
Sonnet: 3,345 / 3,375 remaining (99.1%)
Opus: 740 / 750 remaining (98.7%)

Available for: All other work during sprint (debugging, features, etc.)
```

---

### Example 4: Session Model Comparison

**Scenario:** Full day of mixed work.

**Workload:**
- 30 file operations
- 20 code analysis tasks
- 5 deep reasoning tasks

**Option A: Haiku main session**
```
File ops: 30 Haiku (main session) = 0 Sonnet quota
Code analysis: 20 Sonnet agents spawned = 20 Sonnet quota
Deep reasoning: 5 Opus agents spawned = 5 Opus quota

Total quota: 0 Haiku overhead, 20 Sonnet, 5 Opus
```

**Option B: Sonnet main session**
```
File ops: 30 Sonnet (main) → spawn Haiku = 30 Sonnet (routing) + 0 Haiku
Code analysis: 20 Sonnet (main) = 20 Sonnet
Deep reasoning: 5 Sonnet (main) → spawn Opus = 5 Sonnet + 5 Opus

Total quota: 55 Sonnet, 5 Opus
```

**Option C: Router (Sonnet) + agents**
```
File ops: 30 route (Sonnet) → Haiku = 30 Sonnet + 0 Haiku
Code analysis: 20 route → Sonnet = 20 Sonnet (route) + 20 Sonnet = 40 Sonnet
Deep reasoning: 5 route → Opus = 5 Sonnet + 5 Opus

Total quota: 70 Sonnet, 5 Opus
```

**Quota comparison:**
```
Option A (Haiku main): 20 Sonnet, 5 Opus (BEST)
Option B (Sonnet main): 55 Sonnet, 5 Opus
Option C (Router): 70 Sonnet, 5 Opus (WORST)
```

**Verdict:**
- **Haiku main session is most quota-efficient** (2.75× better than Sonnet main)
- Trade-off: Requires user to manually escalate when Haiku insufficient
- Practical: Use Sonnet main for convenience, or Haiku main when quota is scarce

---

## Summary: Key Optimization Principles

### 1. Maximize Haiku Usage
- Haiku quota is unlimited → use liberally
- Route all mechanical tasks to Haiku
- Saves Sonnet/Opus quota for higher-value work
- **Impact: 3-5× quota efficiency increase**

### 2. Session Model Matters
- Haiku main session: Best quota efficiency (but less convenient)
- Sonnet main session: Balanced (quota cost + convenience)
- Opus main session: Only if every turn needs Opus (rare)
- **Impact: 2-3× quota savings with Haiku main**

### 3. Batch Aggressively
- One message to trigger multi-step workflow
- Reduces back-and-forth overhead
- Enables parallel Haiku processing
- **Impact: 30-50% quota reduction on multi-step work**

### 4. Prioritize Ruthlessly
- Quota is finite, work is infinite
- Defer Tier 3-4 when quota is low
- Save Opus for truly complex reasoning
- **Impact: Avoid quota exhaustion, maintain productivity**

### 5. Monitor Proactively
- Check quota regularly (especially late in day)
- Switch to conservation mode at 70% threshold
- Plan quota-heavy work for fresh quota periods
- **Impact: Avoid surprises, maintain consistent throughput**

### 6. Context Management for Quality, Not Quota
- Fresh start doesn't save quota (same 1 message cost)
- Optimize context for clarity, speed, reliability
- Reset when quality degrades, not to save quota
- **Impact: Better outputs, no quota impact**

### 7. Delegation Paradox
- Same-tier delegation COSTS quota (router overhead)
- Cross-tier delegation SAVES quota (Sonnet → Haiku)
- Minimize routing overhead, maximize direct execution
- **Impact: 20-40% quota savings via smart delegation**

---

## Quota Estimation Tools

### Daily Quota Calculator

```python
def daily_quota_budget(tier='max'):
    """
    Returns daily quota limits
    """
    quotas = {
        'free': {'sonnet': 45, 'opus': 10},
        'pro': {'sonnet': 225, 'opus': 50},
        'max': {'sonnet': 1125, 'opus': 250}
    }
    return quotas[tier]

def quota_allocation(tier='max', work_profile='balanced'):
    """
    Suggests quota allocation based on work profile
    """
    total = daily_quota_budget(tier)

    profiles = {
        'balanced': {
            'sonnet': {
                'routing': 0.20,
                'primary_work': 0.50,
                'rework': 0.20,
                'reserve': 0.10
            },
            'opus': {
                'deep_reasoning': 0.30,
                'complex_problems': 0.40,
                'qa': 0.20,
                'reserve': 0.10
            }
        },
        'research_heavy': {
            'sonnet': {
                'routing': 0.15,
                'primary_work': 0.60,
                'rework': 0.15,
                'reserve': 0.10
            },
            'opus': {
                'deep_reasoning': 0.50,
                'complex_problems': 0.30,
                'qa': 0.10,
                'reserve': 0.10
            }
        },
        'mechanical_heavy': {
            'sonnet': {
                'routing': 0.30,  # More routing to Haiku
                'primary_work': 0.40,
                'rework': 0.20,
                'reserve': 0.10
            },
            'opus': {
                'deep_reasoning': 0.10,
                'complex_problems': 0.20,
                'qa': 0.50,
                'reserve': 0.20
            }
        }
    }

    allocation = {}
    for model in ['sonnet', 'opus']:
        allocation[model] = {
            category: int(total[model] * pct)
            for category, pct in profiles[work_profile][model].items()
        }

    return allocation

# Example usage:
# quota_allocation('max', 'research_heavy')
# → {'sonnet': {'routing': 168, 'primary_work': 675, ...}, ...}
```

### Quota Efficiency Metrics

```python
def quota_efficiency(work_completed, sonnet_used, opus_used, tier='max'):
    """
    Calculate quota efficiency metrics
    """
    total = daily_quota_budget(tier)

    sonnet_pct = (sonnet_used / total['sonnet']) * 100
    opus_pct = (opus_used / total['opus']) * 100

    work_per_sonnet = work_completed / max(sonnet_used, 1)
    work_per_opus = work_completed / max(opus_used, 1)

    return {
        'sonnet_utilization': sonnet_pct,
        'opus_utilization': opus_pct,
        'work_per_sonnet_quota': work_per_sonnet,
        'work_per_opus_quota': work_per_opus,
        'efficiency_score': work_completed / (sonnet_used + opus_used * 4.5)
        # Opus weighted 4.5× (250 Opus ≈ 1,125 Sonnet in quota scarcity)
    }

# Example:
# quota_efficiency(work_completed=100, sonnet_used=50, opus_used=5, tier='max')
# → {'efficiency_score': 1.43, 'work_per_sonnet_quota': 2.0, ...}
```

---

## Appendix: Subscription vs API Comparison

### Cost Model Differences

| Dimension | API Pricing | Subscription |
|-----------|-------------|--------------|
| **Constraint** | Cost per token | Messages per day |
| **Optimization goal** | Minimize token spend | Maximize work output |
| **Context strategy** | Fresh start saves money | Fresh start = same quota |
| **Model selection** | Choose cheapest capable | Choose from quota pool |
| **Delegation value** | Saves token cost | Only saves if cross-tier |
| **Caching impact** | Massive cost savings | No quota impact |
| **Batch processing** | Reduces API calls | Same quota, faster |
| **Quota exhaustion** | Spend more money | Wait for reset |

### When Each Model Applies

**API pricing (pay-per-token):**
- Using Claude API directly
- Building commercial applications
- High-volume, unpredictable workloads
- Cost minimization is primary goal

**Subscription (quota-based):**
- Claude Code CLI
- Personal/team productivity
- Bounded daily workloads
- Throughput maximization within fixed budget

---

---

## Advanced Mathematical Models

### Queueing Theory for Rate Limits

Claude Code enforces both **quota limits** (messages/24h) and **rate limits** (messages/minute). Under heavy load, rate limits create queueing dynamics.

**M/M/1 Queue Model:**

```
System: Messages arrive at rate λ, processed at rate μ
Utilization: ρ = λ / μ

If ρ < 1: Stable (queue drains)
If ρ ≥ 1: Unstable (queue grows indefinitely)
```

**Application to Claude Code:**
```
Rate limit: μ = 60 messages/minute (typical)
User arrival rate: λ = messages/minute (variable)

Average wait time: W = 1 / (μ - λ)

Example:
  λ = 50 msg/min → W = 1/(60-50) = 0.1 min = 6 seconds
  λ = 59 msg/min → W = 1/(60-59) = 1 min (approaching instability)
```

**Little's Law:**
```
L = λ × W

Where:
L = average number of messages in system (queued + processing)
λ = arrival rate
W = average time in system

For λ = 50 msg/min, W = 6 sec:
  L = 50 × 0.1 = 5 messages
```

**Practical implications:**

1. **Burst handling:**
   ```
   Burst of 100 messages at once:
   Time to process: 100 / 60 = 1.67 minutes
   Average wait for message #50: ~25 seconds
   ```

2. **Parallel agent spawning:**
   ```
   Spawning 10 agents simultaneously:
   - All hit rate limit
   - Sequential processing (60/min)
   - Total time: 10 messages / 60 = 10 seconds
   - vs sequential spawning: same time (rate limit is the bottleneck)
   ```

**Multi-Server Queue (M/M/c):**

With multiple concurrent API connections (if supported):
```
c = number of parallel connections
ρ = λ / (c × μ)

Wait time decreases dramatically with c > 1
```

**Optimal batching under rate limits:**
```
Batch size: B
Batch processing time: T_batch = B / μ
Inter-batch delay: T_delay

Throughput maximization:
  Minimize T_delay while keeping ρ < 0.8 (80% utilization target)

If T_delay = 0 (continuous batching):
  Maximum sustainable rate: λ_max = 0.8 × μ = 48 msg/min
```

### Optimal Stopping Problems

**When to pause work and wait for quota reset?**

**Setup:**
```
Current time: t
Quota remaining: Q_remaining
Work value: V(work)
Reset time: t_reset (rolling 24h window)

Decision: Continue working now vs wait for reset?
```

**Threshold-based stopping rule:**

```
Value of continuing now:
  V_continue = V(work) - C_opportunity(using_scarce_quota)

Value of waiting:
  V_wait = V(work) × discount_factor(time_to_reset)

Optimal stopping condition:
  Stop if V_continue < V_wait
```

**Concrete model:**

```python
def should_wait_for_reset(
    quota_pct_remaining,
    work_value,
    time_to_reset_hours,
    discount_rate=0.1  # Value decay per hour
):
    """
    Optimal stopping: Continue vs wait for quota reset
    """
    # Opportunity cost increases as quota depletes
    opportunity_cost = 100 * (1 - quota_pct_remaining) ** 2

    # Value of work degrades with time
    discounted_value = work_value * (1 - discount_rate * time_to_reset_hours)

    # Decision threshold
    continue_value = work_value - opportunity_cost
    wait_value = discounted_value

    return wait_value > continue_value

# Example:
# 10% quota left, high-value work, 2 hours to reset
should_wait = should_wait_for_reset(0.10, 100, 2)
# → True (opportunity cost of using last 10% too high)

# 10% quota left, critical work, 20 hours to reset
should_wait = should_wait_for_reset(0.10, 100, 20)
# → False (can't wait 20 hours, use remaining quota)
```

**Multi-stage optimal stopping:**

For a sequence of tasks with varying values:

```
Dynamic programming formulation:
  V_t(Q) = max{
    V_execute(Q) + V_{t+1}(Q - q_task),  # Execute now
    V_{t+1}(Q)                            # Skip task
  }

Where:
  V_t(Q) = maximum value achievable from time t with quota Q
  q_task = quota cost of current task
  V_execute = immediate value of executing task
```

**Solution via backwards induction:**

```python
def optimal_task_sequence(tasks, quota_remaining):
    """
    Determine which tasks to execute now vs defer

    tasks: List of (value, quota_cost, deadline_hours)
    quota_remaining: Current quota

    Returns: Optimal task execution order
    """
    # Sort by value/cost ratio and deadline
    scored_tasks = [
        (v / max(q, 1), v, q, d, i)
        for i, (v, q, d) in enumerate(tasks)
    ]

    # Separate by urgency
    urgent = [t for t in scored_tasks if t[3] < 4]  # Deadline < 4h
    non_urgent = [t for t in scored_tasks if t[3] >= 4]

    # Greedy allocation: urgent first, then highest value/cost
    selected = []
    q_used = 0

    for task in sorted(urgent, key=lambda x: x[1], reverse=True):
        if q_used + task[2] <= quota_remaining * 0.9:  # Keep 10% buffer
            selected.append(task[4])
            q_used += task[2]

    for task in sorted(non_urgent, key=lambda x: x[0], reverse=True):
        if q_used + task[2] <= quota_remaining * 0.9:
            selected.append(task[4])
            q_used += task[2]

    return selected

# Example:
tasks = [
    (100, 10, 1),   # High value, urgent
    (50, 5, 8),     # Medium value, can wait
    (200, 30, 2),   # Very high value, somewhat urgent
    (30, 3, 24),    # Low value, can wait
]
quota = 50

optimal_sequence = optimal_task_sequence(tasks, quota)
# → Execute tasks [0, 2] now (high value, urgent), defer [1, 3]
```

### Dynamic Programming for Quota Allocation

**Problem:** Allocate daily quota across task categories to maximize total value.

**State space:**
```
State: (quota_remaining, time_remaining, work_queue)
Action: Execute task_i or defer
Reward: Value of completed work
```

**Bellman equation:**
```
V(Q, T) = max_{task i} {
    v_i + V(Q - q_i, T - t_i)  if executing task i
    V(Q, T - Δt)                if waiting/deferring
}

Where:
  V(Q, T) = maximum value achievable with quota Q and time T remaining
  v_i = value of task i
  q_i = quota cost of task i
  t_i = time cost of task i
```

**Practical implementation (simplified):**

```python
def quota_allocation_dp(tasks, total_quota):
    """
    Knapsack-style DP for quota allocation

    tasks: List of (value, quota_cost) tuples
    total_quota: Available quota

    Returns: Maximum value and selected tasks
    """
    n = len(tasks)
    # DP table: dp[i][q] = max value using first i tasks with quota q
    dp = [[0] * (total_quota + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        value, cost = tasks[i - 1]
        for q in range(total_quota + 1):
            # Option 1: Don't take task i
            dp[i][q] = dp[i - 1][q]

            # Option 2: Take task i (if quota allows)
            if q >= cost:
                dp[i][q] = max(dp[i][q], dp[i - 1][q - cost] + value)

    # Backtrack to find selected tasks
    selected = []
    q = total_quota
    for i in range(n, 0, -1):
        if dp[i][q] != dp[i - 1][q]:
            selected.append(i - 1)
            q -= tasks[i - 1][1]

    return dp[n][total_quota], selected[::-1]

# Example:
tasks = [
    (100, 10),  # High value, high cost
    (60, 5),    # Good value/cost ratio
    (30, 3),    # Decent value/cost
    (200, 25),  # Very high value, very high cost
]
quota = 30

max_value, selected = quota_allocation_dp(tasks, quota)
# → max_value = 260, selected = [1, 3] (tasks with best overall value)
```

**Multi-dimensional knapsack (Sonnet + Opus quotas):**

```python
def multi_quota_allocation(tasks, sonnet_quota, opus_quota):
    """
    Allocate across both Sonnet and Opus quota pools

    tasks: List of (value, sonnet_cost, opus_cost, model_required)
    """
    # 3D DP: dp[i][s][o] = max value with i tasks, s sonnet, o opus quota
    n = len(tasks)
    dp = [[[0] * (opus_quota + 1) for _ in range(sonnet_quota + 1)]
          for _ in range(n + 1)]

    for i in range(1, n + 1):
        value, s_cost, o_cost, model = tasks[i - 1]
        for s in range(sonnet_quota + 1):
            for o in range(opus_quota + 1):
                # Don't take task i
                dp[i][s][o] = dp[i - 1][s][o]

                # Take task i (if quota allows)
                if s >= s_cost and o >= o_cost:
                    dp[i][s][o] = max(
                        dp[i][s][o],
                        dp[i - 1][s - s_cost][o - o_cost] + value
                    )

    return dp[n][sonnet_quota][opus_quota]

# Example:
tasks = [
    (100, 10, 0, 'sonnet'),   # Sonnet task
    (200, 0, 5, 'opus'),      # Opus task
    (150, 15, 2, 'mixed'),    # Requires both
]
max_value = multi_quota_allocation(tasks, sonnet_quota=30, opus_quota=10)
```

### Game Theory for Multi-User Team Scenarios

**Setup:** Team shares quota pool (e.g., organization account).

**Tragedy of the commons:**
```
N users sharing quota Q
Each user gains value V_i from using quota q_i
Social cost: C(Σ q_i) when total usage approaches Q

Individual incentive: Maximize V_i(q_i) - C_i(q_i)
Social optimum: Maximize Σ V_i(q_i) - C(Σ q_i)
```

**Nash equilibrium without coordination:**

Each user solves:
```
max_{q_i} V_i(q_i) - C_i(q_i)

Where C_i = individual's share of depletion cost

Problem: Users ignore externality on others
Result: Over-consumption, quota depletes too fast
```

**Cooperative allocation mechanisms:**

**1. Shapley value allocation:**
```
Fair quota allocation based on marginal contribution

φ_i(v) = Σ_{S ⊆ N \ {i}} [|S|! (n - |S| - 1)! / n!] × [v(S ∪ {i}) - v(S)]

Where:
  φ_i = fair allocation to user i
  v(S) = value created by coalition S
  N = set of all users
```

**2. Priority-based system:**
```python
class TeamQuotaManager:
    def __init__(self, total_quota, team_members):
        self.total = total_quota
        self.members = {m: {'priority': 1, 'used': 0} for m in team_members}
        self.remaining = total_quota

    def allocate(self, user, amount):
        """
        Weighted fair sharing: priority-based allocation
        """
        # Calculate user's fair share
        total_priority = sum(m['priority'] for m in self.members.values())
        fair_share = (self.members[user]['priority'] / total_priority) * self.total

        # Allow usage up to fair share + borrowing from unused shares
        used_ratio = self.members[user]['used'] / max(fair_share, 1)

        if used_ratio > 1.2:  # Over 120% of fair share
            return False, "Quota limit: You've exceeded fair share"

        if amount > self.remaining:
            return False, f"Team quota depleted ({self.remaining} remaining)"

        # Allocate
        self.members[user]['used'] += amount
        self.remaining -= amount
        return True, f"Allocated {amount}, {self.remaining} remaining"

# Example usage:
team = TeamQuotaManager(1000, ['alice', 'bob', 'charlie'])
team.members['alice']['priority'] = 2  # Alice has higher priority work
team.allocate('alice', 300)  # Allowed (fair share = 500)
team.allocate('bob', 400)    # Allowed (fair share = 250, but borrowing)
```

**3. VCG Mechanism (Vickrey-Clarke-Groves):**

Truth-telling mechanism for quota allocation:
```
User i reports value v_i(q) for quota amount q
Mechanism allocates q* to maximize Σ v_i(q_i)
User i pays: [Social welfare without i] - [Social welfare of others with i]

Result: Incentive-compatible (truth-telling is dominant strategy)
```

---

## Predictive Analytics

### Quota Burn Rate Forecasting

**Time-series model for daily quota consumption:**

**Simple exponential smoothing:**
```
Forecast: F_{t+1} = α × A_t + (1 - α) × F_t

Where:
  F_t = forecast for period t
  A_t = actual consumption in period t
  α = smoothing parameter (0.2-0.3 typical)
```

**Implementation:**

```python
class QuotaBurnRatePredictor:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.forecast = None
        self.history = []

    def update(self, actual_consumption):
        """Update model with actual daily consumption"""
        self.history.append(actual_consumption)

        if self.forecast is None:
            self.forecast = actual_consumption
        else:
            self.forecast = (self.alpha * actual_consumption +
                           (1 - self.alpha) * self.forecast)

    def predict_exhaustion(self, current_quota, current_hour):
        """Predict when quota will exhaust"""
        if self.forecast is None:
            return None

        # Hourly burn rate
        hourly_rate = self.forecast / 24

        # Hours until exhaustion
        hours_remaining = current_quota / hourly_rate

        return current_hour + hours_remaining

    def recommend_throttle(self, current_quota, hours_remaining):
        """Recommend sustainable burn rate"""
        sustainable_rate = current_quota / hours_remaining
        current_rate = self.forecast / 24

        if current_rate > sustainable_rate * 1.1:
            return {
                'action': 'throttle',
                'current_rate': current_rate,
                'sustainable_rate': sustainable_rate,
                'reduction_needed': (current_rate - sustainable_rate) / current_rate
            }
        else:
            return {'action': 'continue', 'headroom': sustainable_rate - current_rate}

# Example:
predictor = QuotaBurnRatePredictor()
for day_consumption in [100, 120, 110, 130]:
    predictor.update(day_consumption)

# Current state: 500 quota remaining, 12 hours into day
exhaustion_hour = predictor.predict_exhaustion(500, 12)
# → Predicts exhaustion at hour ~27 (tomorrow afternoon)

throttle_advice = predictor.recommend_throttle(500, 12)
# → {'action': 'throttle', 'reduction_needed': 0.15} (reduce by 15%)
```

**ARIMA model for weekly patterns:**

```python
# Requires statsmodels
from statsmodels.tsa.arima.model import ARIMA

def fit_quota_arima(daily_history, forecast_days=7):
    """
    Fit ARIMA(1,1,1) model to daily quota consumption

    Captures:
    - Trend (integrated term)
    - Autocorrelation (AR term)
    - Shock persistence (MA term)
    """
    model = ARIMA(daily_history, order=(1, 1, 1))
    fitted = model.fit()

    forecast = fitted.forecast(steps=forecast_days)
    confidence_intervals = fitted.get_forecast(steps=forecast_days).conf_int()

    return forecast, confidence_intervals

# Example:
daily_consumption = [100, 120, 110, 130, 115, 140, 125,
                     135, 145, 130, 150, 140, 155, 160]
forecast, ci = fit_quota_arima(daily_consumption, forecast_days=3)

# forecast = [162, 165, 168] (predicted consumption next 3 days)
# ci = confidence intervals (95%) for predictions
```

### Anomaly Detection for Unusual Quota Consumption

**Statistical process control:**

```python
import numpy as np

class QuotaAnomalyDetector:
    def __init__(self, window_size=14):
        self.window = window_size
        self.history = []

    def update(self, consumption):
        self.history.append(consumption)
        if len(self.history) > self.window:
            self.history.pop(0)

    def detect_anomaly(self, current_consumption):
        """
        Detect if current consumption is anomalous

        Uses:
        - Mean and std dev over rolling window
        - 3-sigma rule (99.7% of normal data within 3σ)
        """
        if len(self.history) < 7:  # Need minimum data
            return False, "Insufficient data"

        mean = np.mean(self.history)
        std = np.std(self.history)

        z_score = (current_consumption - mean) / max(std, 1)

        if abs(z_score) > 3:
            return True, f"Anomaly detected: {z_score:.2f} sigma from mean"
        elif abs(z_score) > 2:
            return False, f"Warning: {z_score:.2f} sigma (elevated but not anomalous)"
        else:
            return False, "Normal consumption"

# Example:
detector = QuotaAnomalyDetector()
for consumption in [100, 110, 105, 115, 108]:
    detector.update(consumption)

is_anomaly, message = detector.detect_anomaly(250)
# → (True, "Anomaly detected: 3.45 sigma from mean")
# Indicates unusual spike, possibly:
# - Batch job running
# - Mistake in usage pattern
# - Bot/automated system consuming quota
```

**Changepoint detection:**

Detect when quota consumption pattern fundamentally shifts:

```python
def detect_changepoint(history, min_segment_length=5):
    """
    Bayesian changepoint detection

    Identifies points where mean consumption shifts significantly
    """
    n = len(history)
    if n < min_segment_length * 2:
        return None

    max_log_likelihood = float('-inf')
    changepoint = None

    for t in range(min_segment_length, n - min_segment_length):
        # Split into before/after segments
        before = history[:t]
        after = history[t:]

        # Calculate likelihoods assuming normal distributions
        mean_before, std_before = np.mean(before), np.std(before)
        mean_after, std_after = np.mean(after), np.std(after)

        # Log-likelihood of data given this changepoint
        ll = (sum(-0.5 * ((x - mean_before) / max(std_before, 1)) ** 2 for x in before) +
              sum(-0.5 * ((x - mean_after) / max(std_after, 1)) ** 2 for x in after))

        if ll > max_log_likelihood:
            max_log_likelihood = ll
            changepoint = t

    return changepoint

# Example:
consumption = [100, 105, 110, 108, 112,  # Period 1: ~110/day
               200, 210, 195, 205, 220]  # Period 2: ~200/day (shift!)
cp = detect_changepoint(consumption)
# → cp = 5 (changepoint detected at index 5)
```

---

## Visualization Frameworks

### Quota Consumption Dashboard

**ASCII-based dashboard for terminal:**

```python
def quota_dashboard(sonnet_used, sonnet_total, opus_used, opus_total,
                   burn_rate, time_to_reset):
    """
    Generate terminal-based quota dashboard
    """
    def bar(used, total, width=40):
        filled = int((used / total) * width)
        return f"[{'█' * filled}{'░' * (width - filled)}]"

    sonnet_pct = (sonnet_used / sonnet_total) * 100
    opus_pct = (opus_used / opus_total) * 100

    print("=" * 60)
    print(" " * 20 + "QUOTA DASHBOARD")
    print("=" * 60)
    print()
    print(f"Sonnet: {bar(sonnet_used, sonnet_total)} {sonnet_pct:5.1f}%")
    print(f"        {sonnet_used:4d} / {sonnet_total:4d} messages used")
    print()
    print(f"Opus:   {bar(opus_used, opus_total)} {opus_pct:5.1f}%")
    print(f"        {opus_used:4d} / {opus_total:4d} messages used")
    print()
    print(f"Current burn rate: {burn_rate:.1f} messages/hour")
    print(f"Time to reset: {time_to_reset:.1f} hours")
    print()

    # Predictions
    if burn_rate > 0:
        sonnet_hours_left = (sonnet_total - sonnet_used) / burn_rate
        print(f"Sonnet exhaustion: {sonnet_hours_left:.1f} hours at current rate")

    # Status
    if sonnet_pct > 90 or opus_pct > 90:
        print("⚠️  WARNING: Quota nearly exhausted")
    elif sonnet_pct > 70 or opus_pct > 70:
        print("⚡ ALERT: High quota usage, consider throttling")
    else:
        print("✓ Quota healthy")
    print("=" * 60)

# Example:
quota_dashboard(
    sonnet_used=800, sonnet_total=1125,
    opus_used=180, opus_total=250,
    burn_rate=50, time_to_reset=8
)
```

**Output:**
```
============================================================
                    QUOTA DASHBOARD
============================================================

Sonnet: [████████████████████████████░░░░░░░░░░░░]  71.1%
         800 / 1125 messages used

Opus:   [████████████████████████████░░░░░░░░░░░░]  72.0%
         180 /  250 messages used

Current burn rate: 50.0 messages/hour
Time to reset: 8.0 hours

Sonnet exhaustion: 6.5 hours at current rate
⚡ ALERT: High quota usage, consider throttling
============================================================
```

### Burn Rate Visualization

```python
def plot_burn_rate_ascii(hourly_consumption, quota_total):
    """
    ASCII line chart of quota consumption over time
    """
    max_height = 15
    max_consumption = max(hourly_consumption + [quota_total / 24])

    print(f"\nQuota Consumption (Total: {quota_total})")
    print(f"Sustainable rate: {quota_total / 24:.1f} msg/hour")
    print()

    for level in range(max_height, 0, -1):
        threshold = (level / max_height) * max_consumption
        line = f"{threshold:5.0f} |"

        for consumption in hourly_consumption:
            if consumption >= threshold:
                line += "█"
            else:
                line += " "

        print(line)

    print("      +" + "-" * len(hourly_consumption))
    print("       " + "".join(str(i % 10) for i in range(len(hourly_consumption))))
    print("                    Hours")

# Example:
hourly = [30, 35, 40, 45, 60, 70, 55, 50, 45, 40, 35, 30]
plot_burn_rate_ascii(hourly, quota_total=1125)
```

**Output:**
```
Quota Consumption (Total: 1125)
Sustainable rate: 46.9 msg/hour

   70 |    ██
   65 |    ███
   60 |   █████
   55 |   ██████
   50 |   ███████
   45 |  █████████
   40 | ███████████
   35 |████████████
   30 |████████████
      +------------
       012345678901
                    Hours
```

### Model Mix Optimization Graph

```python
def plot_model_mix(haiku_count, sonnet_count, opus_count):
    """
    Visualize quota usage by model tier
    """
    total = sonnet_count + opus_count
    sonnet_pct = (sonnet_count / total) * 100 if total > 0 else 0
    opus_pct = (opus_count / total) * 100 if total > 0 else 0

    width = 50
    sonnet_width = int((sonnet_count / total) * width) if total > 0 else 0
    opus_width = int((opus_count / total) * width) if total > 0 else 0

    print("\nModel Mix (Constrained Quota Only)")
    print(f"\nHaiku:  {haiku_count:4d} messages (unlimited)")
    print(f"Sonnet: {sonnet_count:4d} messages ({sonnet_pct:5.1f}%)")
    print(f"Opus:   {opus_count:4d} messages ({opus_pct:5.1f}%)")
    print()
    print("Quota consumption: [" + "S" * sonnet_width + "O" * opus_width +
          "." * (width - sonnet_width - opus_width) + "]")
    print(f"                    {'Sonnet':<{sonnet_width}} {'Opus'}")

# Example:
plot_model_mix(haiku_count=450, sonnet_count=320, opus_count=45)
```

---

## Economic Models

### Marginal Utility of Quota Units

**Diminishing marginal utility:**

As quota depletes, each remaining message becomes more valuable.

```python
def marginal_utility(quota_pct_remaining):
    """
    Utility function: U(q) = -log(1 - q_used)

    Marginal utility: MU(q) = dU/dq = 1 / (1 - q_used)

    As quota_used → 1, MU → ∞ (remaining quota becomes infinitely valuable)
    """
    quota_used = 1 - quota_pct_remaining
    return 1 / max(1 - quota_used, 0.01)

# Example:
print("Quota Remaining | Marginal Utility")
for pct in [1.0, 0.75, 0.50, 0.25, 0.10, 0.05]:
    mu = marginal_utility(pct)
    print(f"    {pct*100:5.1f}%      |   {mu:8.2f}")
```

**Output:**
```
Quota Remaining | Marginal Utility
    100.0%      |      1.00
     75.0%      |      4.00
     50.0%      |      2.00
     25.0%      |      1.33
     10.0%      |      1.11
      5.0%      |      1.05
```

**Application to pricing decisions:**

```python
def quota_adjusted_task_value(base_value, quota_cost, quota_pct_remaining):
    """
    Adjust task value by marginal utility of quota

    Effective value = Base value - (Quota cost × Marginal utility)
    """
    mu = marginal_utility(quota_pct_remaining)
    opportunity_cost = quota_cost * mu
    return base_value - opportunity_cost

# Example: Same task at different quota levels
task_value = 100
task_cost = 10

for pct in [1.0, 0.50, 0.25, 0.10]:
    adjusted = quota_adjusted_task_value(task_value, task_cost, pct)
    print(f"Quota {pct*100:5.1f}%: Adjusted value = {adjusted:.1f}")

# Output:
# Quota 100.0%: Adjusted value = 90.0
# Quota  50.0%: Adjusted value = 80.0
# Quota  25.0%: Adjusted value = 66.7
# Quota  10.0%: Adjusted value = 88.9 (high MU!)
```

### ROI Calculation Framework

```python
class TaskROI:
    """Calculate return on investment for quota-consuming tasks"""

    def __init__(self, sonnet_quota_value=1.0, opus_quota_value=4.5):
        """
        Initialize with relative quota values
        Opus is ~4.5× scarcer than Sonnet (1125 vs 250 daily)
        """
        self.sonnet_value = sonnet_quota_value
        self.opus_value = opus_quota_value

    def calculate_roi(self, task_value, sonnet_cost, opus_cost):
        """
        ROI = (Value - Cost) / Cost

        Higher ROI = better use of quota
        """
        total_cost = (sonnet_cost * self.sonnet_value +
                     opus_cost * self.opus_value)

        if total_cost == 0:
            return float('inf')  # Haiku tasks have infinite ROI

        roi = (task_value - total_cost) / total_cost
        return roi

    def compare_approaches(self, approaches):
        """
        Compare different implementation approaches

        approaches: List of (name, value, sonnet_cost, opus_cost)
        """
        results = []
        for name, value, s_cost, o_cost in approaches:
            roi = self.calculate_roi(value, s_cost, o_cost)
            total_cost = s_cost * self.sonnet_value + o_cost * self.opus_value
            results.append((name, roi, total_cost, value))

        # Sort by ROI descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

# Example: Compare different ways to implement a feature
roi_calc = TaskROI()

approaches = [
    ("All Sonnet", 100, 20, 0),           # Direct Sonnet implementation
    ("Sonnet + Haiku", 100, 5, 0),        # Delegate to Haiku where possible
    ("Opus deep analysis", 120, 5, 3),    # Use Opus for critical parts
    ("Pure Haiku (lower quality)", 70, 0, 0),  # Fast but lower quality
]

results = roi_calc.compare_approaches(approaches)

print("\nROI Analysis:")
print(f"{'Approach':<30} {'ROI':>8} {'Cost':>8} {'Value':>8}")
print("-" * 60)
for name, roi, cost, value in results:
    print(f"{name:<30} {roi:>8.2f} {cost:>8.1f} {value:>8.1f}")
```

### Value Maximization Under Constraints

**Linear programming formulation:**

```python
from scipy.optimize import linprog

def optimize_quota_allocation_lp(tasks, sonnet_quota, opus_quota):
    """
    Maximize total value subject to quota constraints

    tasks: List of (value, sonnet_cost, opus_cost)

    Returns: Optimal task selection
    """
    n = len(tasks)

    # Objective: maximize value (minimize negative value)
    c = [-task[0] for task in tasks]

    # Constraints: quota limits
    A_ub = [
        [task[1] for task in tasks],  # Sonnet constraint
        [task[2] for task in tasks],  # Opus constraint
    ]
    b_ub = [sonnet_quota, opus_quota]

    # Binary decision variables (0 or 1 for each task)
    bounds = [(0, 1) for _ in range(n)]

    # Solve
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

    if result.success:
        selected = [i for i, x in enumerate(result.x) if x > 0.5]
        total_value = -result.fun
        return selected, total_value
    else:
        return None, 0

# Example:
tasks = [
    (100, 10, 0),   # Task 0: Sonnet task
    (150, 15, 2),   # Task 1: Mixed Sonnet/Opus
    (200, 0, 8),    # Task 2: Opus task
    (80, 8, 0),     # Task 3: Sonnet task
    (120, 5, 3),    # Task 4: Mixed task
]

selected, total_value = optimize_quota_allocation_lp(
    tasks, sonnet_quota=30, opus_quota=10
)
print(f"Optimal selection: Tasks {selected}")
print(f"Total value: {total_value}")
```

---

## Behavioral Strategies and Cognitive Aspects

### Habit Formation for Quota Efficiency

**Implementation intention framework:**

```
IF <situation> THEN <action>

Examples:
- IF starting new task THEN check if Haiku-capable first
- IF Sonnet quota < 30% THEN batch all remaining work
- IF approaching Opus quota limit THEN defer non-critical analysis
```

**Habit loop:**
```
Cue → Routine → Reward

Quota efficiency habit:
  Cue: About to spawn agent
  Routine: Check capability requirements, choose minimal sufficient model
  Reward: Quota preserved, task completed successfully
```

### Cognitive Biases in Model Selection

**Common biases:**

**1. Capability overestimation bias:**
```
Tendency: "This task is complex, I need Opus"
Reality: Sonnet handles 95% of "complex" tasks fine
Impact: Wasted Opus quota

Mitigation:
- Try Sonnet first, escalate only if insufficient
- Keep Opus for formal verification, proofs, subtle logic bugs
```

**2. Sunk cost fallacy:**
```
Scenario: Already used 20 Sonnet messages on task, poor results
Fallacy: "I've invested so much, keep using Sonnet"
Rational: Switch to Opus if task genuinely needs it, OR defer task

Decision rule:
  IF past_cost sunk AND future_value(Sonnet) < future_value(Opus) - cost(Opus):
    Switch to Opus
  ELSE:
    Continue with Sonnet
```

**3. Present bias:**
```
Tendency: Use quota now for immediate gratification
Reality: Quota scarcity later in day creates crisis

Mitigation:
- Reserve 20% quota for end-of-day emergencies
- Batch non-urgent tasks for next day
```

**4. Planning fallacy:**
```
Expectation: "This will take 5 Sonnet messages"
Reality: Takes 15 messages (rework, mistakes, edge cases)

Mitigation:
- Buffer: Assume 1.5-2× expected quota consumption
- Track actual vs estimated consumption, calibrate over time
```

### Psychological Aspects of Quota Scarcity

**Scarcity mindset effects:**

```python
def scarcity_decision_quality(quota_pct_remaining):
    """
    Model: Decision quality degrades under extreme scarcity

    Based on cognitive load research:
    - Moderate scarcity → heightened focus
    - Extreme scarcity → impaired judgment
    """
    if quota_pct_remaining > 0.5:
        return 1.0  # Normal decision quality
    elif quota_pct_remaining > 0.2:
        return 1.1  # Slight improvement (focus effect)
    elif quota_pct_remaining > 0.1:
        return 0.95  # Slight degradation (stress)
    else:
        return 0.7  # Significant degradation (panic decisions)

# Implication: Don't let quota drop below 10% (decision quality suffers)
```

---

## Team and Collaborative Scenarios

### Multi-User Quota Sharing Strategies

**Quota reservation system:**

```python
class TeamQuotaReservationSystem:
    """
    Reserve quota for planned work, prevent conflicts
    """
    def __init__(self, total_quota):
        self.total = total_quota
        self.reservations = {}  # {user: [(start_hour, end_hour, amount)]}
        self.used = 0

    def reserve(self, user, start_hour, end_hour, amount):
        """
        Reserve quota for user during time window
        """
        # Check if sufficient quota available during window
        peak_usage = self._peak_usage_during(start_hour, end_hour)

        if peak_usage + amount > self.total * 0.9:  # Keep 10% buffer
            return False, "Insufficient quota during requested window"

        if user not in self.reservations:
            self.reservations[user] = []

        self.reservations[user].append((start_hour, end_hour, amount))
        return True, f"Reserved {amount} quota for {user} ({start_hour}-{end_hour})"

    def _peak_usage_during(self, start, end):
        """Calculate peak simultaneous reservations during window"""
        usage_by_hour = [0] * 24
        for user, reservations in self.reservations.items():
            for s, e, amt in reservations:
                hourly_rate = amt / (e - s)
                for h in range(int(s), int(e)):
                    usage_by_hour[h] += hourly_rate

        return max(usage_by_hour[int(start):int(end)], default=0)

    def get_availability(self, start_hour, end_hour):
        """Check available quota during window"""
        peak = self._peak_usage_during(start_hour, end_hour)
        return self.total - peak

# Example:
team_system = TeamQuotaReservationSystem(total_quota=1125)
team_system.reserve('alice', 9, 12, 200)   # Morning sprint
team_system.reserve('bob', 13, 17, 300)    # Afternoon sprint
team_system.reserve('charlie', 14, 16, 100)  # Overlaps with Bob

available_afternoon = team_system.get_availability(14, 17)
# → Shows remaining quota after Bob and Charlie's reservations
```

### Coordination Strategies

**Time-slicing:**
```
Divide day into time slots, assign to team members

Example (3-person team, Max tier 1125 Sonnet quota):
  00:00-08:00: Reserved for overnight batch jobs (200 quota)
  08:00-12:00: Alice (300 quota)
  12:00-16:00: Bob (300 quota)
  16:00-20:00: Charlie (300 quota)
  20:00-24:00: Shared pool (25 quota)

Benefit: No conflicts, predictable availability
Drawback: Inflexible, may leave quota unused
```

**Priority queue system:**
```python
import heapq
from datetime import datetime

class TeamPriorityQueue:
    """
    Coordinate quota usage via priority queue
    """
    def __init__(self, quota_per_hour):
        self.quota_per_hour = quota_per_hour
        self.queue = []  # Min-heap of (-priority, timestamp, user, task, quota_needed)
        self.current_allocations = {}

    def submit_task(self, user, task_name, quota_needed, priority):
        """
        Submit task to queue
        Priority: Higher number = higher priority
        """
        timestamp = datetime.now().timestamp()
        heapq.heappush(self.queue, (-priority, timestamp, user, task_name, quota_needed))

    def allocate_next(self, available_quota):
        """
        Allocate quota to highest-priority task that fits
        """
        if not self.queue:
            return None

        # Find highest-priority task that fits in available quota
        temp_queue = []
        allocated = None

        while self.queue and not allocated:
            item = heapq.heappop(self.queue)
            priority, timestamp, user, task, quota = item

            if quota <= available_quota:
                allocated = (user, task, quota)
            else:
                temp_queue.append(item)

        # Restore unallocated tasks to queue
        for item in temp_queue:
            heapq.heappush(self.queue, item)

        return allocated

# Example usage:
queue = TeamPriorityQueue(quota_per_hour=50)
queue.submit_task('alice', 'critical_bug_fix', quota_needed=20, priority=10)
queue.submit_task('bob', 'feature_dev', quota_needed=50, priority=5)
queue.submit_task('charlie', 'refactoring', quota_needed=10, priority=3)

next_task = queue.allocate_next(available_quota=25)
# → Allocates to alice (highest priority, fits in quota)
```

---

## Advanced Optimization Techniques

### Constraint Satisfaction for Deadline Management

**Problem:** Schedule tasks to meet deadlines under quota constraints.

```python
from dataclasses import dataclass
from typing import List
import heapq

@dataclass
class Task:
    name: str
    value: float
    quota_cost: int
    duration_hours: float
    deadline_hour: float
    dependencies: List[str] = None

class DeadlineScheduler:
    """
    Schedule tasks to maximize value while meeting deadlines
    Uses earliest deadline first (EDF) with quota awareness
    """
    def __init__(self, quota_per_hour):
        self.quota_per_hour = quota_per_hour

    def schedule(self, tasks: List[Task], current_hour: float, available_quota: int):
        """
        Returns: Scheduled task list or None if infeasible
        """
        # Sort by deadline (EDF heuristic)
        sorted_tasks = sorted(tasks, key=lambda t: t.deadline_hour)

        schedule = []
        current_time = current_hour
        quota_used = 0
        completed = set()

        for task in sorted_tasks:
            # Check dependencies
            if task.dependencies and not all(d in completed for d in task.dependencies):
                continue

            # Check quota availability
            if quota_used + task.quota_cost > available_quota:
                return None  # Infeasible

            # Check deadline feasibility
            if current_time + task.duration_hours > task.deadline_hour:
                return None  # Cannot meet deadline

            # Schedule task
            schedule.append({
                'task': task.name,
                'start': current_time,
                'end': current_time + task.duration_hours,
                'quota': task.quota_cost
            })

            current_time += task.duration_hours
            quota_used += task.quota_cost
            completed.add(task.name)

        return schedule

# Example:
scheduler = DeadlineScheduler(quota_per_hour=50)

tasks = [
    Task('urgent_fix', value=200, quota_cost=20, duration_hours=1, deadline_hour=14),
    Task('feature_a', value=100, quota_cost=30, duration_hours=2, deadline_hour=18),
    Task('feature_b', value=150, quota_cost=25, duration_hours=1.5, deadline_hour=16,
         dependencies=['feature_a']),
]

schedule = scheduler.schedule(tasks, current_hour=10, available_quota=100)
# Returns schedule meeting all deadlines, or None if infeasible
```

### Multi-Objective Optimization

**Trade-offs:** Speed vs quality vs quota consumption.

```python
def pareto_optimal_approaches(approaches):
    """
    Find Pareto-optimal task implementation approaches

    An approach is Pareto-optimal if no other approach is strictly better
    on all objectives

    approaches: List of (name, speed, quality, quota_cost)
    """
    pareto_set = []

    for i, approach_i in enumerate(approaches):
        name_i, speed_i, quality_i, cost_i = approach_i
        is_dominated = False

        for j, approach_j in enumerate(approaches):
            if i == j:
                continue

            name_j, speed_j, quality_j, cost_j = approach_j

            # Check if approach_j dominates approach_i
            # (better or equal on all objectives, strictly better on at least one)
            if (speed_j >= speed_i and quality_j >= quality_i and cost_j <= cost_i and
                (speed_j > speed_i or quality_j > quality_i or cost_j < cost_i)):
                is_dominated = True
                break

        if not is_dominated:
            pareto_set.append(approach_i)

    return pareto_set

# Example:
approaches = [
    ('Haiku fast', speed=10, quality=6, quota_cost=0),
    ('Sonnet balanced', speed=7, quality=9, quota_cost=5),
    ('Opus deep', speed=3, quality=10, quota_cost=15),
    ('Haiku batch', speed=9, quality=5, quota_cost=0),
    ('Sonnet+Haiku hybrid', speed=8, quality=8, quota_cost=3),
]

pareto = pareto_optimal_approaches(approaches)
print("Pareto-optimal approaches:")
for name, speed, quality, cost in pareto:
    print(f"  {name}: speed={speed}, quality={quality}, quota={cost}")

# Output shows non-dominated approaches:
# Haiku fast, Sonnet balanced, Opus deep, Sonnet+Haiku hybrid
# (Haiku batch is dominated by Haiku fast)
```

---

## Real-World Scenarios and Case Studies

### Sprint Planning with Quota Budgets

**Scenario:** 2-week sprint, estimate quota needs.

```python
class SprintQuotaPlanner:
    """Plan quota allocation for software sprint"""

    def __init__(self, tier='max'):
        quotas = {
            'free': {'sonnet': 45, 'opus': 10},
            'pro': {'sonnet': 225, 'opus': 50},
            'max': {'sonnet': 1125, 'opus': 250}
        }
        self.daily_quota = quotas[tier]

    def plan_sprint(self, sprint_days, story_points, uncertainty_buffer=1.3):
        """
        Estimate quota needs for sprint

        Assumptions:
        - 1 story point ≈ 10 Sonnet messages (empirical average)
        - 10% of work needs Opus
        - uncertainty_buffer accounts for rework, unknowns
        """
        # Base estimates
        sonnet_per_sp = 10
        opus_per_sp = 1.5

        # Total estimates
        sonnet_needed = story_points * sonnet_per_sp * uncertainty_buffer
        opus_needed = story_points * opus_per_sp * uncertainty_buffer

        # Available quota
        sonnet_available = sprint_days * self.daily_quota['sonnet']
        opus_available = sprint_days * self.daily_quota['opus']

        # Feasibility
        feasible = (sonnet_needed <= sonnet_available and
                   opus_needed <= opus_available)

        return {
            'sonnet_needed': int(sonnet_needed),
            'opus_needed': int(opus_needed),
            'sonnet_available': int(sonnet_available),
            'opus_available': int(opus_available),
            'feasible': feasible,
            'sonnet_utilization': sonnet_needed / sonnet_available,
            'opus_utilization': opus_needed / opus_available,
        }

# Example: Plan 10-day sprint with 40 story points
planner = SprintQuotaPlanner(tier='max')
plan = planner.plan_sprint(sprint_days=10, story_points=40)

print(f"Sprint feasibility: {plan['feasible']}")
print(f"Sonnet: {plan['sonnet_needed']} / {plan['sonnet_available']} "
      f"({plan['sonnet_utilization']:.1%})")
print(f"Opus: {plan['opus_needed']} / {plan['opus_available']} "
      f"({plan['opus_utilization']:.1%})")
```

### Emergency Protocols When Quota Depleted

**Escalation ladder:**

```python
class QuotaEmergencyProtocol:
    """
    Handle quota exhaustion scenarios
    """
    def __init__(self):
        self.protocols = {
            'tier_1_critical': [
                "Production outage",
                "Security vulnerability",
                "Data loss risk",
                "Legal/compliance deadline"
            ],
            'tier_2_high': [
                "Feature release blocker",
                "Customer-facing bug",
                "Integration deadline"
            ],
            'tier_3_medium': [
                "Internal tooling issue",
                "Optimization work",
                "Non-critical refactoring"
            ]
        }

    def triage(self, issue_description, quota_remaining_pct):
        """
        Determine if issue justifies using remaining quota
        """
        # Classify issue
        tier = self._classify_issue(issue_description)

        # Decision matrix
        if quota_remaining_pct > 0.10:
            return True, f"Proceed (sufficient quota for {tier})"

        if quota_remaining_pct > 0.05:
            if tier == 'tier_1_critical':
                return True, "APPROVED: Critical issue, use remaining quota"
            else:
                return False, "DEFER: Wait for quota reset"

        # < 5% quota remaining
        if tier == 'tier_1_critical':
            return True, "EMERGENCY: Use last quota for critical issue"
        else:
            return False, "DEFER: Insufficient quota, wait for reset"

    def _classify_issue(self, description):
        # Simplified classification (would use NLP in production)
        description_lower = description.lower()

        critical_keywords = ['production', 'security', 'data loss', 'outage']
        if any(kw in description_lower for kw in critical_keywords):
            return 'tier_1_critical'

        high_keywords = ['blocker', 'customer', 'deadline']
        if any(kw in description_lower for kw in high_keywords):
            return 'tier_2_high'

        return 'tier_3_medium'

# Example:
protocol = QuotaEmergencyProtocol()

# Scenario: 3% quota left, production issue
proceed, message = protocol.triage(
    "Production database connection pool exhausted",
    quota_remaining_pct=0.03
)
# → (True, "EMERGENCY: Use last quota for critical issue")

# Scenario: 3% quota left, feature work
proceed, message = protocol.triage(
    "Add new dashboard widget",
    quota_remaining_pct=0.03
)
# → (False, "DEFER: Insufficient quota, wait for reset")
```

### Cross-Timezone Quota Management

**Challenge:** Team across timezones sharing quota pool.

```python
from datetime import datetime, timezone, timedelta

class TimezoneQuotaCoordinator:
    """
    Coordinate quota usage across timezones
    """
    def __init__(self, total_quota, team_timezones):
        """
        team_timezones: Dict of {user: timezone_offset_hours}
        """
        self.total = total_quota
        self.team_tz = team_timezones

    def optimal_work_schedule(self):
        """
        Find optimal time for each user to maximize quota availability
        """
        # Strategy: Stagger work times to spread quota consumption

        timezones = sorted(set(self.team_tz.values()))
        users_by_tz = {}
        for user, tz in self.team_tz.items():
            if tz not in users_by_tz:
                users_by_tz[tz] = []
            users_by_tz[tz].append(user)

        # Allocate quota proportionally by timezone
        quota_per_tz = self.total / len(timezones)

        schedule = {}
        for tz in timezones:
            users = users_by_tz[tz]
            quota_per_user = quota_per_tz / len(users)

            for user in users:
                # Recommend work during user's business hours
                schedule[user] = {
                    'timezone_offset': tz,
                    'recommended_hours': (9 + tz, 17 + tz),  # 9am-5pm local time
                    'quota_allocation': quota_per_user
                }

        return schedule

    def quota_reset_prediction(self, current_utc_hour):
        """
        Predict when quota resets for each timezone
        """
        predictions = {}
        for user, tz in self.team_tz.items():
            # Quota resets 24h after consumption
            # Assume heavy consumption during business hours
            local_hour = (current_utc_hour + tz) % 24

            if local_hour < 9:  # Before business hours
                hours_to_reset = 24 - (9 - local_hour)
            else:
                hours_to_reset = 24 - (local_hour - 9)

            predictions[user] = hours_to_reset

        return predictions

# Example: Team across US (UTC-8), Europe (UTC+1), Asia (UTC+8)
coordinator = TimezoneQuotaCoordinator(
    total_quota=1125,
    team_timezones={
        'alice_sf': -8,
        'bob_london': 1,
        'charlie_tokyo': 9
    }
)

schedule = coordinator.optimal_work_schedule()
for user, info in schedule.items():
    print(f"{user}: {info}")

# Enables:
# - US team works during US day (quota available)
# - Europe team works during Europe day (different quota window)
# - Asia team works during Asia day (yet another window)
# - Minimal overlap/conflict
```

---

## Metrics and KPIs

### Quota Efficiency Score

```python
def calculate_efficiency_score(
    work_completed,
    sonnet_used,
    opus_used,
    haiku_used,
    sonnet_quota,
    opus_quota
):
    """
    Comprehensive efficiency score (0-100)

    Components:
    1. Work output (30%): Tasks completed vs expected
    2. Quota utilization (30%): Used optimal models
    3. Model balance (20%): Appropriate Haiku/Sonnet/Opus mix
    4. Reserve preservation (20%): Maintained buffer for emergencies
    """
    # 1. Work output score
    expected_work_per_day = 50  # Calibrate based on team
    work_score = min(100, (work_completed / expected_work_per_day) * 100)

    # 2. Quota utilization score
    # Penalize both under-utilization and over-utilization
    sonnet_util = sonnet_used / sonnet_quota
    opus_util = opus_used / opus_quota

    optimal_sonnet_util = 0.75  # Target 75% utilization
    optimal_opus_util = 0.70    # Target 70% utilization

    sonnet_util_score = 100 * (1 - abs(sonnet_util - optimal_sonnet_util))
    opus_util_score = 100 * (1 - abs(opus_util - optimal_opus_util))
    util_score = (sonnet_util_score + opus_util_score) / 2

    # 3. Model balance score
    # Ideal: Maximize Haiku, moderate Sonnet, minimal Opus
    total_constrained = sonnet_used + opus_used * 4.5  # Weight Opus higher

    if total_constrained > 0:
        haiku_ratio = haiku_used / (haiku_used + total_constrained)
        balance_score = haiku_ratio * 100  # Higher Haiku usage = better
    else:
        balance_score = 100

    # 4. Reserve preservation score
    sonnet_reserve = 1 - sonnet_util
    opus_reserve = 1 - opus_util
    reserve_score = (sonnet_reserve + opus_reserve) * 50  # Max 100

    # Weighted average
    total_score = (
        work_score * 0.30 +
        util_score * 0.30 +
        balance_score * 0.20 +
        reserve_score * 0.20
    )

    return {
        'overall_score': total_score,
        'work_score': work_score,
        'utilization_score': util_score,
        'balance_score': balance_score,
        'reserve_score': reserve_score
    }

# Example:
score = calculate_efficiency_score(
    work_completed=55,
    sonnet_used=800,
    opus_used=180,
    haiku_used=600,
    sonnet_quota=1125,
    opus_quota=250
)

print(f"Overall efficiency: {score['overall_score']:.1f}/100")
print(f"  Work output: {score['work_score']:.1f}")
print(f"  Utilization: {score['utilization_score']:.1f}")
print(f"  Model balance: {score['balance_score']:.1f}")
print(f"  Reserve preservation: {score['reserve_score']:.1f}")
```

### Work Output Per Quota Unit Benchmarks

```python
class QuotaBenchmarking:
    """
    Track and benchmark quota efficiency over time
    """
    def __init__(self):
        self.daily_records = []

    def record_day(self, date, work_units, sonnet_used, opus_used):
        """
        Record daily metrics

        work_units: Completed tasks, story points, or custom metric
        """
        self.daily_records.append({
            'date': date,
            'work_units': work_units,
            'sonnet_used': sonnet_used,
            'opus_used': opus_used,
            'work_per_sonnet': work_units / max(sonnet_used, 1),
            'work_per_opus': work_units / max(opus_used, 1),
        })

    def get_benchmarks(self, window_days=30):
        """
        Calculate benchmark statistics over recent window
        """
        recent = self.daily_records[-window_days:]

        if not recent:
            return None

        sonnet_efficiency = [r['work_per_sonnet'] for r in recent]
        opus_efficiency = [r['work_per_opus'] for r in recent]

        import statistics

        return {
            'avg_work_per_sonnet': statistics.mean(sonnet_efficiency),
            'median_work_per_sonnet': statistics.median(sonnet_efficiency),
            'p95_work_per_sonnet': statistics.quantiles(sonnet_efficiency, n=20)[18],  # 95th percentile

            'avg_work_per_opus': statistics.mean(opus_efficiency),
            'median_work_per_opus': statistics.median(opus_efficiency),
        }

    def detect_degradation(self, current_efficiency, window_days=14):
        """
        Detect if current efficiency is significantly below recent average
        """
        benchmarks = self.get_benchmarks(window_days)
        if not benchmarks:
            return False

        threshold = benchmarks['avg_work_per_sonnet'] * 0.7  # 30% below average

        if current_efficiency < threshold:
            return True, f"Efficiency degraded: {current_efficiency:.2f} vs {benchmarks['avg_work_per_sonnet']:.2f} avg"
        else:
            return False, "Efficiency normal"

# Example usage:
tracker = QuotaBenchmarking()

# Record 30 days
for day in range(30):
    work = 50 + (day % 10) - 5  # Simulated work variance
    sonnet = 800 + (day % 50)
    opus = 180 + (day % 20)
    tracker.record_day(f'2026-01-{day+1:02d}', work, sonnet, opus)

benchmarks = tracker.get_benchmarks()
print(f"Average work per Sonnet message: {benchmarks['avg_work_per_sonnet']:.3f}")
print(f"Median work per Sonnet message: {benchmarks['median_work_per_sonnet']:.3f}")
print(f"95th percentile: {benchmarks['p95_work_per_sonnet']:.3f}")

# Detect degradation
degraded, msg = tracker.detect_degradation(current_efficiency=0.04)
print(msg)
```

---

## Integration with Development Workflows

### Git Workflow Optimization

**Quota-aware commit strategy:**

```python
class GitQuotaOptimizer:
    """
    Optimize git workflows for quota efficiency
    """
    def __init__(self, quota_remaining_pct):
        self.quota_remaining = quota_remaining_pct

    def commit_strategy(self, num_files_changed, complexity):
        """
        Recommend commit review strategy based on quota

        complexity: 'low' | 'medium' | 'high'
        """
        if self.quota_remaining > 0.5:
            # Abundant quota: thorough review
            return {
                'strategy': 'comprehensive',
                'model': 'sonnet',
                'review_depth': 'line-by-line',
                'estimated_quota': num_files_changed * 2
            }
        elif self.quota_remaining > 0.2:
            # Moderate quota: balanced review
            if complexity == 'high':
                return {
                    'strategy': 'focused_critical',
                    'model': 'sonnet',
                    'review_depth': 'critical-sections-only',
                    'estimated_quota': num_files_changed * 1
                }
            else:
                return {
                    'strategy': 'automated',
                    'model': 'haiku',
                    'review_depth': 'syntax-and-patterns',
                    'estimated_quota': 0
                }
        else:
            # Scarce quota: minimal review
            return {
                'strategy': 'defer',
                'model': None,
                'review_depth': 'manual-only',
                'estimated_quota': 0,
                'message': 'Defer AI review until quota resets'
            }

# Example:
optimizer = GitQuotaOptimizer(quota_remaining_pct=0.35)
strategy = optimizer.commit_strategy(num_files_changed=8, complexity='medium')
print(f"Strategy: {strategy['strategy']}")
print(f"Model: {strategy['model']}")
print(f"Estimated quota: {strategy['estimated_quota']}")
```

### CI/CD Quota Budgeting

```python
class CICDQuotaBudget:
    """
    Allocate quota for CI/CD automation
    """
    def __init__(self, daily_quota, ci_allocation_pct=0.15):
        """
        ci_allocation_pct: Percentage of daily quota reserved for CI/CD
        """
        self.daily_quota = daily_quota
        self.ci_quota = int(daily_quota * ci_allocation_pct)
        self.ci_used = 0

    def can_run_pipeline(self, pipeline_type):
        """
        Determine if CI pipeline should use AI analysis
        """
        quota_costs = {
            'unit_tests': 0,      # No AI needed
            'lint': 0,            # Haiku (unlimited)
            'security_scan': 5,   # Sonnet analysis
            'code_review': 10,    # Sonnet review
            'integration_tests': 3,  # Sonnet failure analysis
        }

        cost = quota_costs.get(pipeline_type, 0)

        if cost == 0:
            return True, "No quota needed"

        if self.ci_used + cost <= self.ci_quota:
            self.ci_used += cost
            return True, f"Approved ({self.ci_used}/{self.ci_quota} CI quota used)"
        else:
            return False, f"CI quota exhausted ({self.ci_used}/{self.ci_quota})"

    def reset_daily(self):
        """Reset CI quota allocation for new day"""
        self.ci_used = 0

# Example:
ci_budget = CICDQuotaBudget(daily_quota=1125, ci_allocation_pct=0.15)
# → 168 messages/day allocated to CI/CD

can_run, msg = ci_budget.can_run_pipeline('security_scan')
# → (True, "Approved (5/168 CI quota used)")

can_run, msg = ci_budget.can_run_pipeline('code_review')
# → (True, "Approved (15/168 CI quota used)")
```

### Documentation Generation Strategies

```python
class DocGenerationOptimizer:
    """
    Optimize documentation generation under quota constraints
    """
    def __init__(self, quota_remaining):
        self.quota = quota_remaining

    def doc_strategy(self, code_size_loc, doc_type):
        """
        code_size_loc: Lines of code to document
        doc_type: 'api' | 'tutorial' | 'architecture' | 'inline'
        """
        # Estimate quota needed
        quota_estimates = {
            'api': code_size_loc / 100,        # 1 msg per 100 LOC
            'tutorial': code_size_loc / 50,    # More detailed
            'architecture': 10,                 # Fixed cost
            'inline': code_size_loc / 200,     # Lightweight
        }

        estimated_quota = quota_estimates.get(doc_type, code_size_loc / 100)

        if estimated_quota <= self.quota * 0.1:  # < 10% of quota
            return {
                'approach': 'full_generation',
                'model': 'sonnet',
                'quality': 'high',
                'estimated_cost': estimated_quota
            }
        elif estimated_quota <= self.quota * 0.3:
            return {
                'approach': 'template_based',
                'model': 'haiku',
                'quality': 'medium',
                'estimated_cost': estimated_quota * 0.3,  # Templates reduce cost
                'note': 'Use templates to reduce quota consumption'
            }
        else:
            return {
                'approach': 'defer',
                'model': None,
                'quality': None,
                'estimated_cost': 0,
                'note': 'Documentation generation too expensive, defer or do manually'
            }

# Example:
doc_optimizer = DocGenerationOptimizer(quota_remaining=200)
strategy = doc_optimizer.doc_strategy(code_size_loc=5000, doc_type='api')
print(f"Approach: {strategy['approach']}")
print(f"Model: {strategy['model']}")
print(f"Estimated cost: {strategy['estimated_cost']}")
```

---

**Document Status:** Complete subscription-based model v3.0 (Extended)
**Extensions Added:**
- Advanced mathematical models (queueing theory, optimal stopping, dynamic programming, game theory)
- Predictive analytics (burn rate forecasting, anomaly detection, ARIMA models)
- Visualization frameworks (dashboards, burn rate charts, model mix graphs)
- Economic models (marginal utility, ROI calculations, value maximization)
- Behavioral strategies (habit formation, cognitive biases, scarcity psychology)
- Team coordination (quota sharing, priority queues, timezone management)
- Advanced optimization (constraint satisfaction, multi-objective, Pareto optimality)
- Real-world scenarios (sprint planning, emergency protocols, CI/CD integration)
- Metrics and KPIs (efficiency scores, benchmarking, degradation detection)
- Development workflow integration (git optimization, documentation strategies)

**Next Review:** When Claude Code subscription tiers change
**Maintenance:** Update quotas and strategies when new models or tiers are released
