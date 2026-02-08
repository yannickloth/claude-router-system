# Project CLAUDE.md Template - Mandatory Router System

Copy this file to your project's `.claude/CLAUDE.md` to configure the mandatory routing system.

---

## Router System Instructions

**MANDATORY: When router hooks provide routing directives, ALWAYS follow them with no interpretation, hesitation, or override.**

Key rules:

1. **When router provides "escalate" decision**: Immediately invoke the router agent with the user's request
2. **When router provides "direct" decision**: Immediately invoke the specified agent with no further analysis
3. **Never ask clarifying questions** when router has made a decision
4. **Never apply your own judgment** to override router decisions
5. **No exceptions** - applies to all requests, all conditions, all contexts

Why this matters: The router system uses mechanical rules to make deterministic routing decisions. Questioning or re-analyzing those decisions defeats the purpose and creates circular indecision. Trust the routing logic and execute it.

How to recognize router directives:

- Look for `<routing-recommendation>` tags in system messages
- Contains explicit `ROUTING DIRECTIVE` text
- Includes `decision`, `reason`, and `confidence` values
- Specifies ACTION INSTRUCTIONS

### Directive Format

```
<routing-recommendation request-hash="abc123...">
ROUTING DIRECTIVE - MANDATORY ACTION REQUIRED. No interpretation allowed.

Decision: escalate | direct
Reason: [reason from routing_core.py]
Confidence: [0.0-1.0]

ACTION INSTRUCTIONS:
- You MUST NOT handle this request directly
- You MUST use the Task tool to invoke a router agent
- You MUST NOT ask clarifying questions
- Execute the action specified below with no hesitation:

{JSON decision object}

IF decision == "escalate": Invoke infolead-claude-subscription-router:router
IF decision == "direct": Invoke the specified agent directly
</routing-recommendation>
```

### Execution Rules

**When decision == "escalate"**:
1. Invoke Task tool with `subagent_type=infolead-claude-subscription-router:router`
2. Pass the user's original request to the router
3. Execute whatever decision the router returns
4. Do NOT ask clarifying questions yourself

**When decision == "direct"**:
1. Invoke Task tool with `subagent_type=<agent-name>`
2. Pass the user's request to that agent
3. Do NOT escalate further or override the decision
4. Do NOT upgrade/downgrade the agent tier

---

## Available Agents

### Router Agents

| Agent | Model | Use when... |
| --- | --- | --- |
| `router` | Sonnet | Entry point for complex routing decisions |
| `router-escalation` | Opus | Edge cases when router is uncertain |
| `strategy-advisor` | Sonnet | Cost/benefit analysis for execution strategy |

### General Agents

| Agent | Model | Use when... |
| --- | --- | --- |
| `haiku-general` | Haiku | Mechanical tasks with no judgment needed |
| `sonnet-general` | Sonnet | Standard reasoning, analysis, implementation |
| `opus-general` | Opus | Complex reasoning, high-stakes architecture |

### Coordination Agents

| Agent | Model | Use when... |
| --- | --- | --- |
| `work-coordinator` | Sonnet | Multi-task coordination, dependency tracking |
| `temporal-scheduler` | Sonnet | Async work queuing, overnight batch processing |

Use short agent names. Full namespace (`infolead-claude-subscription-router:`) only needed for disambiguation.

---

## How It Works

```
User Request
     ↓
[Hook: UserPromptSubmit] ← routing_core.py analyzes request
     ↓
<routing-recommendation> ← Hook outputs binding directive
     ↓
[You: Execute Directive] ← Invoke specified agent (escalate or direct)
     ↓
[Agent: Complete Task] ← Agent handles the request
     ↓
[You: Report Results] ← Tell user what was done
```

The hook executes before you see the request. When you see it, the routing decision is already made. Your job is reliable execution.

---

## Key Principle

**The mechanical router is the decision authority. Your job is execution.**

Do not second-guess routing decisions. Do not apply "extra context." Do not ask clarifying questions. Follow the directive exactly as specified. This consistency is what makes the system reliable and measurable.
