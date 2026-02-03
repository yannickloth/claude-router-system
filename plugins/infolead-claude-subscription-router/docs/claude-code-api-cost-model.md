# Claude Code Cost Model: Mathematical Analysis

**Version:** 1.0
**Last Updated:** 2026-01-31
**Scope:** Operational cost structure within Claude Code (not API pricing itself)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Base Cost Model](#base-cost-model)
3. [Context Window Dynamics](#context-window-dynamics)
4. [Agent Delegation Economics](#agent-delegation-economics)
5. [Caching Effects](#caching-effects)
6. [Multi-Turn Conversation Costs](#multi-turn-conversation-costs)
7. [Tool Use Overhead](#tool-use-overhead)
8. [Execution Mode Comparison](#execution-mode-comparison)
9. [Optimization Strategies](#optimization-strategies)
10. [Decision Matrices](#decision-matrices)
11. [Worked Examples](#worked-examples)

---

## Introduction

This document provides a mathematical framework for understanding and optimizing costs in Claude Code. We model the total operational cost as:

```
C_total = C_input + C_output + C_overhead + C_opportunity
```

Where:
- **C_input**: Cost of input tokens (prompts, context, cached content)
- **C_output**: Cost of output tokens (responses, generated content)
- **C_overhead**: System overhead (compaction, agent spawning, tool use)
- **C_opportunity**: Lost value from suboptimal routing decisions

---

## Base Cost Model

### Model Tier Pricing (Relative Units)

Using Haiku as baseline (cost = 1.0):

| Model | Input Cost (relative) | Output Cost (relative) | Cache Write | Cache Read |
|-------|----------------------|------------------------|-------------|------------|
| Haiku | 1.0 | 1.0 | 1.25 | 0.10 |
| Sonnet | 4.0 | 20.0 | 5.0 | 0.40 |
| Opus | 20.0 | 100.0 | 25.0 | 2.0 |

### Token Cost Formula

For a single API call:

```
C_call = (T_input × P_input) + (T_cache_write × P_cache_write) +
         (T_cache_read × P_cache_read) + (T_output × P_output)
```

Where:
- T_input: Fresh input tokens (not cached)
- T_cache_write: Tokens being written to cache
- T_cache_read: Tokens being read from cache
- T_output: Output tokens generated
- P_*: Price per token for each category

### Effective Cost Ratios

When comparing models for the same task:

```
Ratio(Sonnet/Haiku) = 4.0 (input) to 20.0 (output)
Ratio(Opus/Sonnet) = 5.0 (input) to 5.0 (output)
Ratio(Opus/Haiku) = 20.0 (input) to 100.0 (output)
```

**Key Insight:** Output cost differences are dramatically larger than input cost differences. Tasks with high output-to-input ratios favor cheaper models even more strongly.

---

## Context Window Dynamics

### Context Growth Model

For a conversation with N turns:

```
T_context(n) = T_system + T_CLAUDE_md + Σ(T_user_i + T_assistant_i) for i=1 to n
```

Where:
- T_system: System prompt (typically 5k-10k tokens, cached)
- T_CLAUDE_md: Project configuration (1k-50k tokens, cached)
- T_user_i: User input on turn i
- T_assistant_i: Assistant output on turn i

### Compaction Cost

Claude Code auto-compacts at approximately 100k tokens. The compaction cost is:

```
C_compact = (T_context × P_input) + (T_summary × P_output)
```

Where:
- T_context: Current context size (~100k at compaction)
- T_summary: Summary generation output (~5k-10k tokens)
- This happens transparently at ~50% of the 200k displayed limit

**For Sonnet at compaction threshold:**

```
C_compact_sonnet = (100,000 × 4) + (7,500 × 20)
                 = 400,000 + 150,000
                 = 550,000 cost units
```

### Fresh Start Cost

Starting a new session with continuation prompt:

```
C_fresh_start = (T_system × P_cache_read) + (T_CLAUDE_md × P_cache_read) +
                (T_continuation × P_input) + (T_first_response × P_output)
```

Where:
- T_system: ~10k (cached, read cost)
- T_CLAUDE_md: ~20k (cached, read cost)
- T_continuation: ~5k (fresh input)
- T_first_response: ~2k (output)

**For Sonnet fresh start:**

```
C_fresh_start_sonnet = (10,000 × 0.4) + (20,000 × 0.4) + (5,000 × 4) + (2,000 × 20)
                     = 4,000 + 8,000 + 20,000 + 40,000
                     = 72,000 cost units
```

### Break-Even Analysis

Compaction becomes more expensive than fresh start when:

```
C_compact > C_fresh_start
(T_context × P_input) + (T_summary × P_output) > (T_continuation × P_input) + overhead
```

For Sonnet:
```
550,000 > 72,000 (fresh start is 7.6× cheaper)
```

**Decision Rule:** When context reaches 35-40% (70k-80k tokens), fresh start is almost always cheaper than waiting for auto-compaction at 100k.

---

## Agent Delegation Economics

### Direct Execution vs Delegation

**Direct execution cost:**
```
C_direct = T_input × P_model + T_output × P_model
```

**Delegation cost:**
```
C_delegate = (T_routing × P_router_input + T_routing_output × P_router_output) +
             (T_task × P_agent_input + T_result × P_agent_output)
```

### Delegation Efficiency

Delegation is cost-effective when:

```
C_delegate < C_direct
```

Expanding:

```
(T_r_in × P_r_in + T_r_out × P_r_out) + (T_task × P_agent + T_out × P_agent) <
(T_input × P_expensive + T_out × P_expensive)
```

### Example: Opus → Sonnet Delegation

Task: Analyze 10k token document, generate 2k token output

**Direct (Opus):**
```
C_opus_direct = (10,000 × 20) + (2,000 × 100) = 200,000 + 200,000 = 400,000
```

**Delegated (Opus routes to Sonnet):**
```
C_routing = (1,000 × 20) + (200 × 100) = 20,000 + 20,000 = 40,000
C_execution = (10,000 × 4) + (2,000 × 20) = 40,000 + 40,000 = 80,000
C_total = 40,000 + 80,000 = 120,000
```

**Savings: 70%** (280,000 cost units saved)

### Delegation Overhead Threshold

Routing adds overhead. Delegation is beneficial when task cost exceeds routing cost by factor k:

```
C_task_expensive > k × C_routing

Where k ≈ 1.5-2.0 (accounts for coordination overhead)
```

For very short tasks (< 500 tokens input/output), delegation overhead may exceed savings.

---

## Caching Effects

### Cache Hit Economics

Prompt caching dramatically changes cost structure:

**Without cache:**
```
C_no_cache = T_total × P_input
```

**With cache (first call):**
```
C_first_call = T_cacheable × P_cache_write + T_unique × P_input
```

**With cache (subsequent calls):**
```
C_cached_call = T_cacheable × P_cache_read + T_unique × P_input
```

### Cache ROI

Cache becomes beneficial after N calls when:

```
N × (T_cache × P_input) > (T_cache × P_cache_write) + N × (T_cache × P_cache_read)
```

Solving for N:

```
N > P_cache_write / (P_input - P_cache_read)
```

**For Sonnet:**
```
N > 5.0 / (4.0 - 0.4) = 5.0 / 3.6 ≈ 1.4 calls
```

Cache pays for itself after just 2 calls for Sonnet.

### Effective Cost Reduction

With high cache hit rate (r = 0.8):

```
C_effective = r × (T_total × P_cache_read) + (1-r) × (T_total × P_input)
C_effective = 0.8 × (T × 0.4) + 0.2 × (T × 4.0)
C_effective = 0.32T + 0.8T = 1.12T

Savings: (4.0T - 1.12T) / 4.0T = 72% reduction
```

**Caching is highly effective for:**
- Repeated context (system prompts, CLAUDE.md)
- Multi-turn conversations
- Agent systems with shared context

---

## Multi-Turn Conversation Costs

### Linear Growth Model

For N-turn conversation without caching:

```
C_total(N) = Σ[i=1 to N] (C_system + C_history(i) + C_new_input(i) + C_output(i))
```

Where C_history(i) grows linearly:
```
C_history(i) = Σ[j=1 to i-1] (T_user(j) + T_assistant(j)) × P_input
```

Total cost grows quadratically: O(N²)

### Cached Growth Model

With prompt caching:

```
C_total_cached(N) = C_cache_write(system) +
                    Σ[i=1 to N] (C_cache_read(system) + C_history(i) + C_new(i) + C_out(i))
```

History still grows linearly, so total cost is O(N), but with much lower constant factor.

### Comparative Example: 10-Turn Conversation

**Assumptions:**
- System + CLAUDE.md: 30k tokens (cacheable)
- Each user input: 500 tokens
- Each assistant output: 1,000 tokens
- Using Sonnet

**Without caching:**
```
Turn 1: (30,000 + 500) × 4 + 1,000 × 20 = 122,000 + 20,000 = 142,000
Turn 2: (30,000 + 500 + 1,000 + 500) × 4 + 1,000 × 20 = 128,000 + 20,000 = 148,000
...
Turn 10: (30,000 + 13,500) × 4 + 1,000 × 20 = 174,000 + 20,000 = 194,000

Total ≈ 1,640,000 cost units
```

**With caching:**
```
Turn 1: (30,000 × 5) + 500 × 4 + 1,000 × 20 = 150,000 + 2,000 + 20,000 = 172,000
Turn 2: (30,000 × 0.4) + (1,500) × 4 + 1,000 × 20 = 12,000 + 6,000 + 20,000 = 38,000
...
Turn 10: (30,000 × 0.4) + 13,500 × 4 + 1,000 × 20 = 12,000 + 54,000 + 20,000 = 86,000

Total ≈ 630,000 cost units
```

**Savings: 62%** (1,010,000 cost units saved)

---

## Tool Use Overhead

### Tool Call Cost Model

Each tool use incurs:

```
C_tool = C_planning + C_execution + C_integration
```

Where:
- **C_planning**: Output tokens to formulate tool call (~50-200 tokens)
- **C_execution**: Tool execution time (varies, often negligible cost)
- **C_integration**: Input tokens to read tool results + output tokens to respond

### Tool Call Pattern

**Single tool call:**
```
C_single = T_plan × P_out + T_result × P_in + T_response × P_out
```

**Parallel tool calls (N tools):**
```
C_parallel = T_plan_all × P_out + Σ(T_result_i × P_in) + T_response × P_out
```

**Sequential tool calls:**
```
C_sequential = Σ[i=1 to N] (T_plan_i × P_out + T_result_i × P_in + T_response_i × P_out)
```

### Efficiency Comparison

**Example: Read 3 files**

**Parallel:**
```
Planning: 150 tokens
Results: 3 × 2,000 = 6,000 tokens
Response: 500 tokens

C_parallel_sonnet = 150 × 20 + 6,000 × 4 + 500 × 20 = 3,000 + 24,000 + 10,000 = 37,000
```

**Sequential:**
```
Turn 1: 100 × 20 + 2,000 × 4 + 200 × 20 = 2,000 + 8,000 + 4,000 = 14,000
Turn 2: 100 × 20 + 2,000 × 4 + 200 × 20 = 2,000 + 8,000 + 4,000 = 14,000
Turn 3: 100 × 20 + 2,000 × 4 + 300 × 20 = 2,000 + 8,000 + 6,000 = 16,000

C_sequential = 14,000 + 14,000 + 16,000 = 44,000
```

**Parallel is 16% cheaper** and completes in 1 turn instead of 3.

### Tool Use Strategy

**Use parallel tool calls when:**
- Operations are independent
- All tools likely to succeed
- Results can be synthesized together
- Time and cost savings matter

**Use sequential tool calls when:**
- Later calls depend on earlier results
- Need to make decisions between steps
- Risk of failure requires adaptive strategy

---

## Execution Mode Comparison

### Foreground vs Background

**Foreground execution:**
```
C_foreground = C_agent_execution
User sees: Real-time progress, can interrupt, interactive
```

**Background execution:**
```
C_background = C_agent_execution + C_monitoring + C_status_checks

Where:
C_monitoring = N_checks × (T_check × P_in + T_status × P_out)
```

### Cost Analysis

Background execution adds monitoring overhead but enables parallelism.

**Single task:**
- Foreground: C_task
- Background: C_task + C_monitoring

Foreground is cheaper for single tasks.

**Parallel tasks:**
- Sequential foreground: C_task1 + C_task2 + C_task3
- Parallel background: max(C_task1, C_task2, C_task3) + C_monitoring

Background is cheaper when tasks can truly run in parallel.

### Visibility Tax

Monitoring background tasks costs tokens:

```
C_visibility = N_updates × (T_check_in × P_in + T_update × P_out)
```

For N=10 status checks during background task:
```
C_visibility = 10 × (100 × 4 + 200 × 20) = 10 × (400 + 4,000) = 44,000
```

This is non-trivial overhead, so background should be used strategically.

---

## Optimization Strategies

### 1. Model Selection Strategy

**Decision tree:**

```
Task requires deep reasoning or proof? → Opus
  |
  No → Task requires judgment, analysis, or trade-offs? → Sonnet
         |
         No → Task is mechanical with explicit inputs? → Haiku
```

**Cost impact example (10k input, 2k output):**

- Haiku: (10,000 × 1) + (2,000 × 1) = 12,000
- Sonnet: (10,000 × 4) + (2,000 × 20) = 80,000 (6.7× more expensive)
- Opus: (10,000 × 20) + (2,000 × 100) = 400,000 (33× more expensive)

**Wrong model costs 6-33× more** for the same task.

### 2. Context Management Strategy

**Monitoring formula:**

```
Context_percentage = (Tokens_used / 200,000) × 100
```

**Action thresholds:**

- **< 35%**: Continue normally
- **35-39%**: Monitor, mention to user
- **40-44%**: Calculate compaction vs fresh start costs, inform user
- **45%+**: Generate continuation prompt immediately

**Why these thresholds?**

Auto-compaction happens at ~100k (50% displayed, but effectively 100% of usable limit before compaction). At 45% (90k tokens), you're very close to expensive auto-compaction. Fresh start is almost always cheaper.

### 3. Caching Strategy

**Maximize cache hits:**

1. **Structure prompts consistently**: Put cacheable content (system, CLAUDE.md) at the beginning
2. **Reuse context**: Keep stable context across turns
3. **Agent design**: Share common context across agent calls

**Cache efficiency metric:**

```
Cache_efficiency = T_cached / (T_cached + T_uncached)

Target: > 80% for multi-turn conversations
```

### 4. Delegation Strategy

**Delegation decision formula:**

```
Should_delegate = (C_expensive_model - C_cheap_model) > C_routing_overhead
```

Simplified:
```
Delegate if: (T_in + T_out) × (P_expensive - P_cheap) > 1,500

Where 1,500 ≈ typical routing overhead in cost units
```

**Example (Opus considering Sonnet delegation):**

```
Task: 10k input, 2k output
Savings: (10,000 + 2,000) × (20 - 4) = 12,000 × 16 = 192,000
Routing overhead: ~40,000
Net benefit: 152,000 (delegation strongly beneficial)
```

### 5. Tool Use Strategy

**Prefer parallel tool calls:**

```
Efficiency_gain = (C_sequential - C_parallel) / C_sequential
                ≈ 10-20% for typical cases
```

**When to use tools:**

- Tool result cheaper than generating: Read file vs regenerate from memory
- Tool provides ground truth: File content vs hallucinated content
- Tool enables automation: Bash vs manual operations

**When to avoid tools:**

- Information already in context (cache hit)
- Result is derivable without external data
- Tool overhead exceeds value (very short reads)

---

## Decision Matrices

### Matrix 1: Model Selection

| Input Size | Output Size | Reasoning Depth | Recommended Model | Reasoning |
|------------|-------------|-----------------|-------------------|-----------|
| < 5k | < 1k | Mechanical | Haiku | Low cost, sufficient capability |
| < 20k | < 5k | Analysis | Sonnet | Balanced cost/performance |
| > 20k | > 5k | Analysis | Sonnet | Output cost dominates |
| Any | Any | Deep/Proof | Opus | Capability requirement |
| < 5k | > 10k | Creative | Sonnet/Opus | Output cost dominates, need quality |

### Matrix 2: Context Management

| Context % | Continuation Cost | Compaction Cost | Recommendation |
|-----------|-------------------|-----------------|----------------|
| < 35% | Higher | N/A (not triggered) | Continue |
| 35-39% | Similar | N/A | Monitor, continue |
| 40-44% | Lower | N/A | Inform user, likely switch |
| 45-49% | Much lower | Imminent | Generate continuation prompt |
| 50%+ | Much lower | Triggered/imminent | Fresh start essential |

### Matrix 3: Delegation Decision

| Current Model | Task Complexity | Input+Output Size | Delegate To | Savings |
|---------------|-----------------|-------------------|-------------|---------|
| Opus | Mechanical | Any | Haiku | 95%+ |
| Opus | Analytical | > 5k | Sonnet | 70-80% |
| Opus | Deep reasoning | Any | None | N/A |
| Sonnet | Mechanical | > 5k | Haiku | 75%+ |
| Sonnet | Analytical | Any | None | N/A |

---

## Worked Examples

### Example 1: Document Analysis Task

**Scenario:** Analyze a 50k token LaTeX document for citation errors.

**Option A: Direct with Sonnet**
```
Input: 50,000 tokens (document)
Output: 3,000 tokens (analysis)
C_direct = (50,000 × 4) + (3,000 × 20) = 200,000 + 60,000 = 260,000
```

**Option B: Delegate to Haiku**
```
Routing (Sonnet):
  Input: 1,000 tokens (task description)
  Output: 200 tokens (routing decision)
  C_route = (1,000 × 4) + (200 × 20) = 4,000 + 4,000 = 8,000

Execution (Haiku):
  Input: 50,000 tokens (document)
  Output: 3,000 tokens (analysis)
  C_exec = (50,000 × 1) + (3,000 × 1) = 50,000 + 3,000 = 53,000

C_total = 8,000 + 53,000 = 61,000
```

**Savings: 77%** (199,000 cost units saved)

**Decision: Delegate to Haiku** (citation checking is mechanical pattern matching)

---

### Example 2: Multi-Turn Research Session

**Scenario:** 20-turn conversation researching ME/CFS treatments.

**Initial context:**
- System prompt: 10k tokens (cacheable)
- CLAUDE.md: 30k tokens (cacheable)
- Per turn: 800 input, 1,500 output

**Without cache:**
```
Turn 1: (40,000 + 800) × 4 + 1,500 × 20 = 163,200 + 30,000 = 193,200
Turn 20: (40,000 + 38,000) × 4 + 1,500 × 20 = 312,000 + 30,000 = 342,000

Total (sum of arithmetic series): ≈ 5,352,000
```

**With cache:**
```
Turn 1: (40,000 × 5) + 800 × 4 + 1,500 × 20 = 200,000 + 3,200 + 30,000 = 233,200
Turn 2-20: (40,000 × 0.4) + (growing history) × 4 + 1,500 × 20
  ≈ 16,000 + 3,200 + varying history + 30,000 per turn

Total: ≈ 1,850,000
```

**Savings: 65%** (3,502,000 cost units saved)

**Plus: Context hits 50% at turn ~15**

**Without management:** Auto-compaction costs 550,000
**With management:** Fresh start at turn 12 costs 72,000

**Additional savings: 478,000** cost units

**Total optimization: 3,980,000 cost units saved (74% reduction)**

---

### Example 3: Parallel File Processing

**Scenario:** Extract data from 5 log files (2k tokens each)

**Option A: Sequential reads**
```
Each turn: 100 × 20 + 2,000 × 4 + 300 × 20 = 2,000 + 8,000 + 6,000 = 16,000
Total: 5 × 16,000 = 80,000
Turns: 5
```

**Option B: Parallel reads**
```
Planning: 200 × 20 = 4,000
Results: 5 × 2,000 × 4 = 40,000
Response: 800 × 20 = 16,000
Total: 60,000
Turns: 1
```

**Savings: 25%** (20,000 cost units saved)
**Time savings: 80%** (5 turns → 1 turn)

**Decision: Use parallel reads** (independent operations, all likely to succeed)

---

### Example 4: Agent Routing Decision

**Scenario:** User asks "Fix LaTeX syntax errors in chapter 5"

**Option A: Sonnet-general does it directly**
```
Read file: 8,000 × 4 = 32,000
Fix content: 500 × 20 = 10,000
Write file: included in output
Total: ~42,000
```

**Option B: Router delegates to syntax-fixer (Haiku)**
```
Routing:
  Parse request: 200 × 4 + 100 × 20 = 800 + 2,000 = 2,800

Syntax-fixer execution:
  Read: 8,000 × 1 = 8,000
  Fix: 500 × 1 = 500
  Write: 0 (write operation)
  Report: 200 × 1 = 200
  Total: 8,700

C_total = 2,800 + 8,700 = 11,500
```

**Savings: 73%** (30,500 cost units saved)

**Decision: Delegate to specialized agent** (exact match, mechanical task)

---

## Summary: Key Optimization Principles

1. **Route to the cheapest capable model**
   - Haiku for mechanical tasks: 95% cost savings vs Opus
   - Sonnet for analysis: 80% savings vs Opus
   - Opus only for deep reasoning/proofs

2. **Manage context proactively**
   - Monitor percentage continuously
   - Fresh start at 40-45% saves 7-8× vs auto-compaction
   - Context growth is O(N), so plan ahead

3. **Leverage caching aggressively**
   - Cache pays for itself after 2 calls
   - Structure prompts for maximum cache reuse
   - 60-75% cost reduction in multi-turn conversations

4. **Parallelize tool use**
   - 15-25% savings for independent operations
   - Faster execution (single turn vs multiple)
   - Better user experience

5. **Delegate strategically**
   - Specialized agents save 70-90% on matched tasks
   - Router overhead (~2-5% of task cost) is negligible
   - Wrong model costs 6-33× more

6. **Background execution for parallelism**
   - Use when truly parallel work is needed
   - Monitor cost: 10-15% overhead
   - Foreground for interactive/judgment tasks

---

## Cost Estimation Tools

### Quick Cost Estimator

```python
def estimate_cost(model, input_tokens, output_tokens, cached_tokens=0):
    """
    Returns cost in relative units (Haiku = 1.0 baseline)
    """
    prices = {
        'haiku': {'input': 1.0, 'output': 1.0, 'cache_read': 0.1},
        'sonnet': {'input': 4.0, 'output': 20.0, 'cache_read': 0.4},
        'opus': {'input': 20.0, 'output': 100.0, 'cache_read': 2.0}
    }

    p = prices[model]
    uncached = input_tokens - cached_tokens

    cost = (uncached * p['input']) + (cached_tokens * p['cache_read']) + (output_tokens * p['output'])
    return cost

# Example usage:
# estimate_cost('sonnet', 10000, 2000, 5000)
# → (5000 × 4.0) + (5000 × 0.4) + (2000 × 20.0) = 20000 + 2000 + 40000 = 62000
```

### Delegation Savings Calculator

```python
def delegation_savings(expensive_model, cheap_model, input_tokens, output_tokens):
    """
    Calculate savings from delegating to cheaper model
    """
    direct_cost = estimate_cost(expensive_model, input_tokens, output_tokens)
    routing_cost = estimate_cost(expensive_model, 1000, 200)  # routing overhead
    delegated_cost = estimate_cost(cheap_model, input_tokens, output_tokens)

    total_delegated = routing_cost + delegated_cost
    savings = direct_cost - total_delegated
    savings_percent = (savings / direct_cost) * 100

    return {
        'direct': direct_cost,
        'delegated': total_delegated,
        'savings': savings,
        'savings_percent': savings_percent
    }

# Example:
# delegation_savings('opus', 'haiku', 10000, 2000)
# → {'savings_percent': 95.0, ...}
```

---

## References and Further Reading

- **Claude API Documentation**: Pricing and caching behavior
- **Independent Variation Principle**: https://doi.org/10.5281/zenodo.17677315
- **Context Efficiency Guide**: `.claude/context-efficiency.md` (if available)
- **Strategy Advisor Agent**: `.claude/agents/strategy-advisor.md`

---

**Document Status:** Complete mathematical model v1.0
**Next Review:** When API pricing changes or new models are released
**Maintenance:** Update formulas and examples when Claude Code behavior changes