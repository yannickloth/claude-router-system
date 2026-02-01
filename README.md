# Claude Router System

**Intelligent routing architecture for Claude Code with IVP-compliant design, cost optimization, and specialized agent delegation.**

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
- **Router agents**: `router`, `router-escalation`, `strategy-advisor`
- **General agents**: `haiku-general`, `sonnet-general`, `opus-general`
- **Project agents**: Add your own specialized agents to `.claude/agents/`

### 💰 Cost Optimization
- **Haiku pre-routing**: 30-40% escalation rate saves 60-70% quota
- **Propose-review pattern**: Haiku proposes, Sonnet reviews for bulk mechanical tasks
- **Semantic deduplication**: 40-50% cache hit rate eliminates redundant work
- **Break-even analysis**: Only use expensive models when justified

### 📐 IVP Architecture
Built on the **Independent Variation Principle** (IVP): separate concerns with different change drivers into independent units.

- **Router** changes when: task understanding evolves
- **Strategy-advisor** changes when: API pricing or optimization strategies change
- **Agents** change when: their specific domain capabilities change

**Reference:** [Independent Variation Principle (DOI 10.5281/zenodo.17677315)](https://doi.org/10.5281/zenodo.17677315)

---

## Quick Start

### Test the Implementation

```bash
# 1. List available domains
cd /home/nicky/code/claude-router-system
python3 implementation/domain_adapter.py list

# 2. Detect domain in your project
python3 implementation/domain_adapter.py detect

# 3. View a workflow
python3 implementation/domain_adapter.py workflow latex-research formalization

# 4. Record test metrics
python3 implementation/metrics_collector.py record haiku_routing escalation --value 35

# 5. Generate daily report
python3 implementation/metrics_collector.py report daily

# 6. Run integration tests
pytest tests/test_integration.py -v
```

### Phase 3 & 4 Features

See [PHASE_3_4_IMPLEMENTATION.md](PHASE_3_4_IMPLEMENTATION.md) for complete details on:
- Domain configurations (LaTeX, software-dev, knowledge-mgmt)
- Lazy context loading with LRU caching
- Metrics collection and reporting
- Monitoring hooks and integration tests

---

## Installation

### Option 1: Via Claude Code Plugin System (Recommended)

```bash
# Add marketplace
/plugin marketplace add yannickloth/claude-router-system

# Install plugin
/plugin install claude-router-system@yannickloth
```

### Option 2: Manual Installation

```bash
# Clone to your global Claude directory
cd ~/.claude
git clone https://github.com/yannickloth/claude-router-system.git plugins/claude-router-system

# Symlink agents to global agents directory
ln -s ~/.claude/plugins/claude-router-system/agents/* ~/.claude/agents/
```

---

## Configuration

### 1. Copy Routing Rules to Your Project

Copy the routing configuration template:

```bash
# From your project root
cp ~/.claude/plugins/claude-router-system/EXAMPLE.claude.md .claude/CLAUDE.md
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

**Propose-review pattern** (for bulk mechanical tasks):
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

### Viewing Usage Metrics

The plugin tracks all agent invocations and estimates costs:

```bash
# View today's usage dashboard
./scripts/usage-dashboard.sh

# View last 7 days
./scripts/usage-dashboard.sh --week

# View last 30 days
./scripts/usage-dashboard.sh --month

# JSON output for integration
./scripts/usage-dashboard.sh --json
```

### Dashboard Output

```
═══════════════════════════════════════════════════════════════════
                 Claude Router Usage Dashboard
═══════════════════════════════════════════════════════════════════

Period: today
Total Agent Invocations: 42

───────────────────────────────────────────────────────────────────
                      Model Distribution
───────────────────────────────────────────────────────────────────

  haiku      28  ████████████████████████████
  sonnet     12  ████████████
  opus        2  ██

───────────────────────────────────────────────────────────────────
                      Estimated Costs
───────────────────────────────────────────────────────────────────

  Haiku:   $0.0280  (28 invocations @ $0.0010/msg)
  Sonnet:  $0.1440  (12 invocations @ $0.0120/msg)
  Opus:    $0.1200  (2 invocations @ $0.0600/msg)
  ─────────────────────────────
  TOTAL:   $0.2920

───────────────────────────────────────────────────────────────────
                     Cost Optimization
───────────────────────────────────────────────────────────────────

  If all 42 tasks used Sonnet:  $0.5040
  Actual cost with routing:      $0.2920
  Estimated savings:             $0.2120
  Savings percentage:            42.1%
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

Both short names (`haiku-general`) and fully qualified names (`claude-router-system:haiku-general`) work. Use short names unless you need to disambiguate between plugins with identical agent names.

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