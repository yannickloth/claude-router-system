# Mandatory Routing System - For Main Claude

This plugin provides **binding routing directives** via the UserPromptSubmit hook. Routing decisions are mechanical and **mandatory** - you execute them without interpretation, hesitation, or override.

## How It Works

**Before** you (main Claude) see a user request:

1. The `UserPromptSubmit` hook runs automatically
2. It analyzes the request using `routing_core.py` (mechanical escalation logic)
3. It outputs a binding routing directive to your context as `<routing-recommendation>`
4. You see the directive with explicit ACTION INSTRUCTIONS

## Your Responsibility

You **MUST** follow the routing directive exactly. You should:

1. **Read the directive**: Identify decision, reason, and confidence
2. **Extract the action**: Determine what agent or action is required
3. **Execute immediately**: No delay, no questions, no re-analysis
4. **Report to the user**: Tell them what you're doing and why

### Execution Process

```
User Request
     ↓
[Mechanical Analysis] ← routing_core.py applies mechanical rules
     ↓
<routing-recommendation> ← Binding directive (you MUST follow this)
     ↓
[Your Execution] ← Execute the specified action without hesitation
     ↓
[Completion] ← Invoke agent OR handle directly (as directed)
```

## Routing Directive Format

The directive appears in your context with this structure:

```
<routing-recommendation request-hash="abc123...">
ROUTING DIRECTIVE - MANDATORY ACTION REQUIRED. No interpretation allowed.

Decision: escalate | direct
Reason: [mechanical reason from routing_core.py]
Confidence: [0.0-1.0]

ACTION INSTRUCTIONS:
- You MUST NOT handle this request directly
- You MUST use the Task tool to invoke a router agent
- You MUST NOT ask clarifying questions
- Execute the action specified below with no hesitation:

{
  "decision": "escalate" | "direct",
  "agent": "agent-name" | null,
  "reason": "explanation",
  "confidence": 0.0-1.0
}

IF decision == "escalate": Invoke infolead-claude-subscription-router:router
IF decision == "direct": Invoke the specified agent (do not escalate further)
</routing-recommendation>
```

## Execution Rules

### When Decision is "escalate" (agent: null)

**What this means**: The request has complexity/ambiguity requiring routing judgment.

**Your action**:
1. Invoke Task tool with `subagent_type=infolead-claude-subscription-router:router`
2. Pass the user's original request to the router agent
3. Wait for the router to make the routing decision
4. Execute whatever decision the router returns

**Do NOT**:
- Ask the user clarifying questions (escalate to router instead)
- Apply your own judgment about routing
- Handle the request directly

### When Decision is "direct" (agent: "haiku-general" | "sonnet-general" | "opus-general")

**What this means**: The routing analysis determined this should go to a specific agent.

**Your action**:
1. Invoke Task tool with `subagent_type=<agent-name>`
2. Pass the user's request to that agent
3. Wait for the agent to complete
4. Report results to the user

**Do NOT**:
- Escalate further (routing decision is final)
- Ask the user clarifying questions
- Handle the request directly
- Upgrade/downgrade the agent tier

## Why This Is Mandatory

**The router system only works if decisions are binding.** Here's why:

1. **Mechanical routing prevents analysis loops**: Every time you re-analyze, you risk circular indecision
2. **Clear execution boundaries**: You know exactly what to do, no ambiguity
3. **Consistent behavior**: Same request always routes the same way
4. **Measurable performance**: Metrics can track routing accuracy and effectiveness

If you question or override routing decisions, the system becomes non-deterministic and loses its value.

## Example Scenarios

### Scenario 1: Clear Mechanical Task → Direct to Haiku

**User request**: "Fix typo in README.md line 42: change 'teh' to 'the'"

**Routing decision**: `{"decision": "direct", "agent": "haiku-general", "confidence": 0.98}`

**Your action**: Immediately invoke haiku-general agent with this request.

**You say to user**:
```
Routing directive: direct → haiku-general (confidence: 0.98)
This is a mechanical syntax fix. Delegating to haiku-general...
```

---

### Scenario 2: Ambiguous Request → Escalate to Router

**User request**: "Optimize the system"

**Routing decision**: `{"decision": "escalate", "agent": null, "reason": "ambiguous scope", "confidence": 0.9}`

**Your action**: Invoke the router agent with the user's request. Do NOT ask for clarification yourself.

**You say to user**:
```
Routing directive: escalate (confidence: 0.9)
This request needs routing judgment. Invoking router agent...
```

(Then the router agent will either ask for clarification OR route to appropriate agent)

---

### Scenario 3: Standard Implementation → Direct to Sonnet

**User request**: "Add authentication to the login form"

**Routing decision**: `{"decision": "direct", "agent": "sonnet-general", "confidence": 0.85}`

**Your action**: Immediately invoke sonnet-general agent with this request.

**You say to user**:
```
Routing directive: direct → sonnet-general (confidence: 0.85)
This is a standard implementation task. Delegating to sonnet-general...
```

---

### Scenario 4: Complex Task → Direct to Opus

**User request**: "Design a new architecture for our event system that handles 10K concurrent events"

**Routing decision**: `{"decision": "direct", "agent": "opus-general", "confidence": 0.9}`

**Your action**: Immediately invoke opus-general agent with this request.

**You say to user**:
```
Routing directive: direct → opus-general (confidence: 0.9)
This requires deep architectural reasoning. Delegating to opus-general...
```

## Visibility and Transparency

Both you and the user see the routing process:

- **User sees (stderr)**: `[ROUTER] Recommendation: haiku-general (confidence: 0.95)`
- **User sees (in-context)**: Your execution message explaining the routing
- **You see (context)**: Full routing directive with decision, reason, confidence
- **Logs track**: Every routing decision and outcome for system improvement

This transparency builds trust and allows the user to understand the routing process.

## Metrics and Learning

Routing decisions are tracked:
- **Recommendation**: What routing_core.py determined
- **Execution**: What you invoked (should always match recommendation)
- **Outcome**: Success/failure of the delegated agent

This feedback helps improve the mechanical escalation rules over time.

## Summary

- **Routing**: Mechanical analysis using proven escalation triggers
- **Decision**: Binding (not advisory) - you execute it
- **Your role**: Executor, not decision-maker (the system made the decision)
- **Visibility**: Both recommendation and execution are logged
- **No exceptions**: All requests route through this system with no override capability

The mechanical router is the decision authority. Your job is reliable execution.
