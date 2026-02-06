# Infolead Claude Subscription Router

**Intelligent routing architecture for Claude Code with IVP-compliant design, cost optimization, and specialized agent delegation.**

**Plugin name:** `infolead-claude-subscription-router`

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude-Code-blue.svg)](https://github.com/anthropics/claude-code)

---

## What This Plugin Provides

### 🎯 Core Routing System (Phase 1 & 2)
- **Central router**: All requests flow through a single routing decision point
- **Risk assessment**: Automatic evaluation of destructive operations and high-stakes changes
- **Agent matching**: Routes to appropriate agent based on task complexity and domain
- **Cost optimization**: Strategy advisor analyzes execution patterns for cost efficiency
- **Semantic caching**: Deduplication of similar requests with 40-50% hit rate
- **Work coordination**: Parallel work tracking with completion guarantees

### 🎯 Domain Integration (Phase 3)
- **Domain detection**: Automatic detection of project type (LaTeX, software-dev, knowledge-mgmt)
- **Workflow management**: Domain-specific workflows with quality gates and parallelism settings
- **Lazy context loading**: LRU-cached section-level file loading to minimize context overhead
- **Context optimization**: 50k token budget for context, 150k for conversation

### 📊 Monitoring & Metrics (Phase 4)
- **Metrics collection**: Track performance across all 8 optimization solutions
- **Daily/weekly reports**: Automated performance summaries with target assessment
- **Monitoring hooks**: Routing audit, session state capture, morning briefing
- **Usage tracking**: Agent invocation logging with duration, model tier, and cost estimates
- **Integration testing**: Comprehensive test suite for all components

### 🤖 Agent Hierarchy
- **Router agents**: `router`, `router-escalation`, `strategy-advisor`, `planner`
- **General agents**: `haiku-general`, `sonnet-general`, `opus-general`
- **Project agents**: Add your own specialized agents to `.claude/agents/`

### 💰 Cost Optimization
- **Haiku pre-routing**: 30-40% escalation rate saves 60-70% quota
- **Propose-review pattern**: Haiku proposes, Sonnet reviews for bulk mechanical edits
- **Draft-then-evaluate pattern**: Haiku batch-drafts, Sonnet batch-evaluates for content generation (40-60% savings at batch 10+)
- **Semantic deduplication**: 40-50% cache hit rate eliminates redundant work
- **Break-even analysis**: Only use expensive models when justified

### 📐 IVP Architecture
Built on the **Independent Variation Principle** (IVP): separate concerns with different change drivers into independent units.

- **Router** changes when: task understanding evolves
- **Strategy-advisor** changes when: API pricing or optimization strategies change
- **Agents** change when: their specific domain capabilities change

**Reference:** [Independent Variation Principle (DOI 10.5281/zenodo.17677315)](https://doi.org/10.5281/zenodo.17677315)

---

## 🔍 Visibility & Monitoring (NEW in v1.3.0)

### Real-Time Routing Recommendations

Every request now displays routing analysis **before** main Claude processes it:

```
[ROUTER] Recommendation: haiku-general (confidence: 0.95)
[ROUTER] Reason: High-confidence agent match
```

**What you see:**

- ✅ **Agent recommendation**: Which agent the pre-router suggests
- ✅ **Confidence level**: How certain the recommendation is (0.0-1.0)
- ✅ **Reasoning**: Why this agent was chosen

**What happens:**
1. Pre-router analyzes your request using mechanical escalation logic
2. Recommendation is displayed to you (stderr)
3. Recommendation is injected into main Claude's context
4. Main Claude makes final decision with full context
5. Both recommendation and actual decision are logged to metrics

### Advisory System

**Important**: Recommendations are **advisory, not mandatory**.

Main Claude sees the pre-router's recommendation as input but makes the final decision based on:

- Pre-router's recommendation
- Conversation history
- Project context
- Your specific requirements

**Claude can**:
- ✅ Follow the recommendation
- ⚠️  Override (upgrade/downgrade tier)
- ❓ Escalate (ask for clarification)

**You always see both** the recommendation and Claude's decision.

### Metrics Collection

All routing decisions are tracked to:
```
~/.claude/infolead-router/metrics/YYYY-MM-DD.jsonl
```

**What's logged:**

- Timestamp of request
- Request hash (for correlation)
- Recommended agent
- Confidence level
- Reasoning
- Full analysis

**Performance:**
- Average latency: ~108ms per request
- Atomic writes: Safe for concurrent requests
- Daily rotation: New file each day

### Visibility Benefits

**For you:**

- See what the router is thinking
- Verify system is working correctly
- Build trust through transparency
- Understand routing patterns

**For main Claude:**
- Advisory input for routing decisions
- Context for explaining choices
- Override when additional context changes assessment

**For the system:**

- Metrics enable continuous improvement
- Track recommendation accuracy
- Identify patterns for optimization
- Auditable trail of all decisions

### Example: Visible Routing Flow

```
User: "Fix typo in README.md line 42"
     ↓
[Pre-Router analyzes automatically]
     ↓
YOU SEE:
  [ROUTER] Recommendation: haiku-general (confidence: 0.98)
  [ROUTER] Reason: Mechanical syntax fix with explicit file path
     ↓
CLAUDE SEES:
  <routing-recommendation>
    {"decision":"direct","agent":"haiku-general","confidence":0.98}
  </routing-recommendation>
     ↓
CLAUDE RESPONDS:
  "The pre-router correctly identified this as a mechanical task.
   I'll delegate to haiku-general."
     ↓
METRICS LOG:
  {"timestamp":"2026-02-05T17:00:00+01:00",
   "recommendation":{"agent":"haiku-general","confidence":0.98}}
```

### Testing Visibility

```bash
# From plugin directory
cd plugins/infolead-claude-subscription-router

# Test routing recommendations
echo "Fix typo in README.md" | python3 implementation/routing_core.py --json

# Test full hook (with visibility)
export CLAUDE_PLUGIN_ROOT="$PWD"
echo "Fix typo in README.md" | bash hooks/user-prompt-submit.sh

# Check metrics
cat ~/.claude/infolead-router/metrics/$(date +%Y-%m-%d).jsonl | tail -5

# Run comprehensive tests
bash tests/test-routing-visibility.sh
```

### Documentation

- **[OPTION-D-IMPLEMENTATION.md](docs/OPTION-D-IMPLEMENTATION.md)**: Technical implementation details
- **[CLAUDE-ROUTING-ADVISORY.md](docs/CLAUDE-ROUTING-ADVISORY.md)**: Guide for main Claude
- **[IMPLEMENTATION-REVIEW.md](docs/IMPLEMENTATION-REVIEW.md)**: Complete review and test results

---

## Quick Start

### Test the Implementation

```bash
# From the plugin directory
cd plugins/infolead-claude-subscription-router

# 1. List available domains
python3 implementation/domain_adapter.py list

# 2. Detect domain in your project
python3 implementation/domain_adapter.py detect

# 3. View a workflow
python3 implementation/domain_adapter.py workflow latex-research formalization

# 4. Record test metrics
python3 implementation/metrics_collector.py record haiku_routing escalation --value 35

# 5. Generate daily report
python3 implementation/metrics_collector.py report daily

# 6. Run integration tests (from repo root)
cd ../..
./tests/infolead-claude-subscription-router/run_all_tests.sh
```

---

## Installation

### Option 1: Via Claude Code Plugin System (Recommended)

```bash
# Install plugin
/plugin install infolead-claude-subscription-router
```

### Option 2: Manual Installation

```bash
# Clone the marketplace repo
cd ~/.claude
git clone https://github.com/yannickloth/claude-router-system.git marketplace

# Symlink the plugin
ln -s ~/.claude/marketplace/plugins/infolead-claude-subscription-router ~/.claude/plugins/

# Symlink agents to global agents directory
ln -s ~/.claude/plugins/infolead-claude-subscription-router/agents/* ~/.claude/agents/
```

---

## Configuration

### 1. Copy Routing Rules to Your Project

Copy the routing configuration template:

```bash
# From your project root
cp ~/.claude/plugins/infolead-claude-subscription-router/EXAMPLE.claude.md .claude/CLAUDE.md
```

Or add to your **global** `~/.claude/CLAUDE.md` to enable routing for all projects.

### 2. (Optional) Add Project-Specific Agents

Create `.claude/agents/` in your project and add specialized agents:

```bash
mkdir -p .claude/agents
touch .claude/agents/my-domain-agent.md
```

The router will check project-specific agents first before falling back to general agents.

---

## How It Works

### Routing Flow

```
User request
    ↓
router (parse intent, assess risk, match agent)
    ↓
strategy-advisor (cost/benefit analysis)
    ↓
selected agent (execute task)
    ↓
results returned to user
```

### Agent Selection Priority

1. **Project-specific agents** (`.claude/agents/`) - exact domain match
2. **General agents** - based on reasoning complexity:
   - `haiku-general`: Mechanical, no judgment, explicit paths
   - `sonnet-general`: Default for reasoning/analysis
   - `opus-general`: Complex reasoning, proofs, high-stakes

### Cost Optimization Patterns

**Direct execution:**
```
router → agent → results
```

**Propose-review pattern** (for bulk mechanical file edits):
```
router → strategy-advisor
       ↓
haiku-general (propose changes)
       ↓
sonnet-general (review + apply)
       ↓
results
```

**Break-even:** Haiku→Sonnet saves money when success rate > 60%

**Draft-then-evaluate pattern** (for bulk content generation):
```
router → strategy-advisor
       ↓
haiku-general (batch draft N items, 0 Sonnet quota)
       ↓
sonnet-general (batch evaluate all N in 1 message)
       ↓
sonnet-general (fix rejects only)
       ↓
results
```

**Break-even:** Profitable when acceptance rate > 1/N (batch 10: >10%, batch 50: >2%)

**When to use which:**
- **Propose-review**: Modifying existing files (patches, syntax fixes, refactors)
- **Draft-then-evaluate**: Generating new content (docstrings, comments, descriptions)

---

## Architecture Principles

### Independent Variation Principle (IVP)

**Change drivers are the reasons units change.** Units with different change drivers should be separated.

#### Router Agent

**Change Driver Set:** Task understanding evolution, risk categorization, agent capabilities

- Changes when: New types of requests need routing, risk categories evolve, understanding of task patterns improves
- **Does NOT change when:** API pricing changes, optimization strategies evolve

#### Strategy-Advisor Agent

**Change Driver Set:** API pricing models, cost optimization strategies, performance characteristics

- Changes when: Anthropic updates pricing, new optimization patterns discovered, model performance shifts
- **Does NOT change when:** New agent types added, task understanding improves, risk rules change

#### General Agents (haiku/sonnet/opus)

**Change Driver Set:** Model capabilities, safety protocols, output requirements

- Changes when: Model capabilities change, safety best practices evolve, output format standards update
- **Does NOT change when:** Routing logic changes, pricing changes, new domains added

#### Project-Specific Agents

**Change Driver Set:** Domain knowledge, domain-specific tooling, domain best practices

- Changes when: Domain understanding deepens, domain tools evolve, best practices in that domain change
- **Does NOT change when:** Global routing changes, pricing changes, other domains change

**Why this matters:** When API pricing changes, you only update `strategy-advisor`. When task understanding improves, you only update `router`. Changes are isolated and predictable.

---

## Usage Examples

### Basic Request Routing

```
User: "Fix all LaTeX syntax errors in chapter files"

router: Assesses → mechanical task, multiple files, compiler verification
       ↓
strategy-advisor: Recommends propose-review pattern
       ↓
haiku-general: Proposes fixes across 30 files
       ↓
sonnet-general: Reviews, runs nix build, applies changes
       ↓
Results: "Fixed 47 LaTeX errors across 30 files, build passes"
```

### High-Stakes Request

```
User: "Delete all unused files"

router: Assesses → destructive, ambiguous scope, high risk
       ↓
sonnet-general: Analyzes patterns, asks for confirmation
       ↓
User confirms
       ↓
Results: "Found 12 candidates, deleted 8 confirmed unused files"
```

### Complex Reasoning Request

```
User: "Verify this mathematical proof is correct"

router: Assesses → requires deep analysis, high error cost
       ↓
strategy-advisor: Recommends direct-opus (no cheaper path)
       ↓
opus-general: Analyzes proof step-by-step
       ↓
Results: "Proof verified. Found 1 subtle flaw in step 7: [detailed explanation]"
```

### Bulk Content Generation (Draft-Then-Evaluate)

```
User: "Generate docstrings for all 50 functions in src/utils/"

router: Assesses → content generation, high volume, mechanical
       ↓
strategy-advisor: Recommends draft-then-evaluate (batch 50, ~60% acceptance expected)
       ↓
haiku-general: Generates 50 docstring drafts (0 Sonnet quota)
       ↓
sonnet-general: Batch evaluates all 50 in 1 message (1 Sonnet quota)
       ↓
sonnet-general: Fixes 20 rejected drafts (20 Sonnet quota)
       ↓
Results: "Generated 50 docstrings. 30 accepted, 15 refined, 5 replaced."
         "Total: 21 Sonnet messages (58% savings vs 50 direct)"
```

---

## Routing Rules Reference

### Absolute Routing Enforcement

**EVERY user request goes through router. No exceptions.**

```
✅ User request → router → agent
❌ User request → agent (bypasses router)
❌ User request → Claude answers directly
```

Even simple questions route through the system:
- "What's the status?" → router → haiku-general
- "Explain this code" → router → sonnet-general
- "Is this proof valid?" → router → opus-general

**Why:** Consistency, cost optimization, risk assessment

### Risk Assessment

Before routing destructive operations:

1. **Identify scope**: Which files affected?
2. **Assess value**: Is content important?
3. **Check specificity**: Explicit paths or patterns?
4. **Evaluate reversibility**: Can we undo?
5. **Route defensively**:
   - High risk → `sonnet-general` or `opus-general`
   - Low risk + explicit paths → `haiku-general`
   - ANY uncertainty → `sonnet-general`

### Protected Files

**Never route to haiku-general:**
- `.claude/agents/*.md` (agent definitions)
- High-value content (proofs, papers, critical code)
- Ambiguous patterns (user didn't specify exact files)

---

## Extending the System

### Adding Project-Specific Agents

Create `.claude/agents/my-agent.md`:

```markdown
---
name: my-domain-agent
description: Handles X domain tasks with Y capabilities. Use when user requests Z.
model: sonnet
tools: Read, Edit, Write, Bash
---

You are a specialized agent for [domain].

## Capabilities
- [What this agent does]

## Change Driver Set
**This agent changes when:** [list change drivers specific to this domain]
**This agent does NOT change when:** [list unrelated change drivers]

[Rest of agent specification]
```

**Change Driver Set:** Domain knowledge for X, tooling for Y, best practices in Z

The router will automatically discover and use your agent when requests match the description.

### Creating Domain-Specific Plugins

You can create your own plugin that extends this router system:

```
my-domain-plugin/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── domain-agent-1.md
│   └── domain-agent-2.md
└── README.md
```

The router will check both the core general agents and your domain agents.

---

## Cost Optimization Details

### Model Pricing (as of 2026-01)

| Model | Input | Output | Relative Cost |
|-------|--------|--------|---------------|
| Haiku | $0.25/MTok | $1.25/MTok | 1x |
| Sonnet | $3.00/MTok | $15.00/MTok | 12x |
| Opus | $15.00/MTok | $75.00/MTok | 60x |

### Strategy Selection Criteria

**Mechanical Score:** 0.0 (pure judgment) to 1.0 (fully mechanical)

| Task Type | Score | Agent Choice |
|-----------|-------|--------------|
| Exact pattern replacement | 1.0 | haiku-general |
| Syntax fixes (verified) | 0.9 | haiku→sonnet (propose-review) |
| Reference updates | 0.8 | haiku→sonnet (propose-review) |
| Formatting | 0.5 | sonnet-general |
| Style improvements | 0.3 | sonnet-general |
| Pure judgment | 0.1 | sonnet-general or opus-general |

### Propose-Review Break-Even

**Haiku→Sonnet review:**
- Saves money when haiku success rate > 60%
- Typical use cases: 80-90% success rate
- Estimated savings: 60-70% vs direct-sonnet

**Sonnet→Opus review:**
- Saves money when sonnet success rate > 67%
- Typical use cases: 75-85% success rate
- Estimated savings: 40-50% vs direct-opus

---

## Usage Tracking & Cost Analysis

### Metrics Collector CLI

The plugin tracks all agent invocations and computes solution-level metrics:

```bash
cd implementation/

# Run tests to verify setup
python3 metrics_collector.py --test

# Compute all solution metrics with status vs targets
python3 metrics_collector.py compute

# Calculate cost efficiency (savings vs baseline)
python3 metrics_collector.py efficiency

# Live dashboard showing recent agent activity
python3 metrics_collector.py dashboard

# Generate daily report
python3 metrics_collector.py report daily

# Generate weekly report
python3 metrics_collector.py report weekly
```

### Solution Metrics Output

```
═══════════════════════════════════════════════════════════════════
                   Solution Metrics Dashboard
═══════════════════════════════════════════════════════════════════

Solution             Metric                 Value    Target       Status
─────────────────────────────────────────────────────────────────────
haiku_routing        escalation_rate        35.2%    30-40%       ✓ ON TARGET
work_coordination    completion_rate        94.5%    90-100%      ✓ ON TARGET
domain_optimization  detection_accuracy     97.3%    95-100%      ✓ ON TARGET
temporal_optimization quota_utilization     82.1%    80-90%       ✓ ON TARGET
deduplication        cache_hit_rate         45.8%    40-50%       ✓ ON TARGET
probabilistic_routing optimistic_success    89.2%    85-100%      ✓ ON TARGET
state_continuity     save_success           99.1%    98-100%      ✓ ON TARGET
context_ux           avg_response_time      3.2s     0-5s         ✓ ON TARGET
```

### Efficiency Report Output

```text
═══════════════════════════════════════════════════════════════════
                      Routing Efficiency Report
═══════════════════════════════════════════════════════════════════

Model Distribution:
  haiku:   28 invocations  ████████████████████████████
  sonnet:  12 invocations  ████████████
  opus:     2 invocations  ██

Cost Analysis (vs sonnet baseline):
  Actual cost:        52 units
  Baseline cost:     504 units (if all used sonnet)
  Savings:           452 units
  Savings percent:   89.7%
```

### Metrics Storage

- **Project logs**: `.claude/logs/routing.log` - Per-project routing decisions
- **Global metrics**: `~/.claude/infolead-router/metrics/YYYY-MM-DD.jsonl` - Daily aggregated metrics

### Hooks

The plugin uses Claude Code hooks for tracking:

- **SubagentStart**: Logs when agents spawn (timestamp, agent type, ID)
- **SubagentStop**: Logs when agents complete (duration, exit status, model tier)

---

## Troubleshooting

### Hooks Not Executing (Plugin Bug)

**Symptoms:** Routing recommendations don't appear, session hooks don't run, no metrics logged.

**Cause:** Claude Code has a known bug where plugin-defined hooks are matched but never executed.

**Affected issues:**
- [#10225](https://github.com/anthropics/claude-code/issues/10225) - UserPromptSubmit hooks from plugins match but never execute
- [#14410](https://github.com/anthropics/claude-code/issues/14410) - Local plugin hooks match but never execute

**Workaround:** Copy hooks to settings.json:

```bash
cd plugins/infolead-claude-subscription-router

# Choose your scope:
./scripts/setup-hooks-workaround.sh --local    # This user, this project
./scripts/setup-hooks-workaround.sh --project  # All users, this project
./scripts/setup-hooks-workaround.sh --global   # This user, all projects

# Preview first
./scripts/setup-hooks-workaround.sh --local --dry-run

# Revert when bug is fixed
./scripts/setup-hooks-workaround.sh --local --revert
```

See **[docs/HOOKS-WORKAROUND.md](docs/HOOKS-WORKAROUND.md)** for detailed instructions.

---

### "Router not being used"

Check your `.claude/CLAUDE.md`:
- Routing rules copied from `EXAMPLE.claude.md`?
- Absolute routing enforcement section present?
- Global `~/.claude/CLAUDE.md` configured?

### "Agent completed silently"

All agents have **mandatory output requirements**. If an agent produces no output:
- Router will detect and re-route
- Check agent definition for output requirements section
- Verify agent is using correct output patterns

### "Wrong agent selected"

Router logs reasoning before delegating:
```
Routing: sonnet-general
Reason: Requires judgment for ambiguous file patterns
```

Check the routing explanation to understand the decision.

### "Agent doesn't know its tools"

General agents now include explicit tool lists in their prompts. If you encounter this:

- Ensure you have the latest agent definitions
- Check that the agent file includes the "Available Tools" section

### "Agent can't spawn subagents"

**This is by design.** General agents (`haiku-general`, `sonnet-general`, `opus-general`) are execution endpoints—they execute tasks themselves and do not further delegate.

**Workaround for multi-step workflows:** The main session coordinates:

```text
1. Main session spawns agent for Phase 1
2. Collect results
3. Main session spawns agent for Phase 2
4. Repeat as needed
```

See "Multi-Step Workflow Coordination" in `EXAMPLE.claude.md` for detailed patterns.

---

## Known Limitations

### General Agents Are Endpoints

General agents execute tasks directly. They cannot spawn other agents for sub-delegation. This prevents routing chains but means the main session must coordinate multi-phase workflows.

### Model Parameter Behavior

When using the Task tool:

- Agent definitions specify a default `model:` in frontmatter
- The Task tool's `model:` parameter can override this
- Best practice: let agent definitions control their model

### Namespace Resolution

Both short names (`haiku-general`) and fully qualified names (`infolead-claude-subscription-router:haiku-general`) work. Use short names unless you need to disambiguate between plugins with identical agent names.

---

## Contributing

Contributions welcome! Please:

1. **Follow IVP**: Separate concerns by change driver
2. **Document change drivers**: Every new agent must list its change driver set
3. **Test routing**: Verify router correctly identifies when to use new agents
4. **Update examples**: Add usage examples for new capabilities

### Change Driver Documentation Template

When adding new agents or modules:

```markdown
## Change Driver Set

**This [unit] changes when:**
- [Change driver 1]
- [Change driver 2]

**This [unit] does NOT change when:**
- [Unrelated change driver 1]
- [Unrelated change driver 2]

**IVP Compliance:** [Explain how this unit maintains separation of concerns]
```

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built for [Claude Code](https://github.com/anthropics/claude-code)
- Architecture based on [Independent Variation Principle](https://doi.org/10.5281/zenodo.17677315)
- Inspired by cost-conscious LLM orchestration patterns

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yannickloth/claude-router-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yannickloth/claude-router-system/discussions)
- **Claude Code**: [Official Docs](https://github.com/anthropics/claude-code)