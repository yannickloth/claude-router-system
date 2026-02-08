# Project CLAUDE.md Template

Copy this file to your project's `.claude/CLAUDE.md` to enable routing.

---

## Agent Routing

**ABSOLUTE RULE: Every user request goes through the router agent. No exceptions.**

Main Claude session does NOT execute user requests directly. Everything delegates:

```text
User request → router → agent
```

Never answer directly, never "just a quick answer," never bypass routing — even for simple questions.

## Multi-Step Workflow Coordination

Main session coordinates multi-phase workflows. This is valid, not a routing violation:

```text
Phase 1: router → agent(s) → results
Phase 2: main session triages results → router → next agent(s)
Repeat until complete
```

The main session orchestrates but never executes tasks itself.

## Available Agents

### Router Agents

| Agent | Model | Use when... |
| --- | --- | --- |
| `router` | Sonnet | Entry point for all requests |
| `router-escalation` | Opus | Edge cases when router is uncertain |
| `strategy-advisor` | Sonnet | Cost/benefit analysis for execution strategy |

### General Agents

| Agent | Model | Use when... |
| --- | --- | --- |
| `haiku-general` | Haiku | Mechanical tasks, no judgment needed |
| `sonnet-general` | Sonnet | Default for reasoning, analysis, judgment |
| `opus-general` | Opus | Complex reasoning, high-stakes decisions |

### Coordination Agents

| Agent | Model | Use when... |
| --- | --- | --- |
| `work-coordinator` | Sonnet | Multi-task coordination, dependency tracking |
| `temporal-scheduler` | Sonnet | Async work queuing, overnight batch processing |

Use short agent names. Namespace prefix (`infolead-claude-subscription-router:`) only needed for disambiguation.

Router checks project `.claude/agents/` first for specialized agents before falling back to general agents.
