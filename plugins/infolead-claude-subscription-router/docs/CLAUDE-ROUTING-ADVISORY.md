# Advisory Routing System - For Main Claude

This plugin provides **visible, advisory routing recommendations** via the UserPromptSubmit hook.

## How It Works

**Before** you (main Claude) see a user request:

1. The `UserPromptSubmit` hook runs
2. It analyzes the request using `routing_core.py` (mechanical escalation logic)
3. It outputs a routing recommendation to your context as `<routing-recommendation>`
4. You see the recommendation as advisory input

## Your Role

You are **NOT required** to follow the routing recommendation blindly. You should:

1. **Read the recommendation**: See what the pre-router suggested
2. **Evaluate its reasoning**: Does the recommendation make sense?
3. **Make the final decision**: You have the context and judgment to decide
4. **Explain your decision**: Tell the user what you're doing and why

### Decision Process

```
User Request
     ↓
[Pre-Router Analysis] ← Mechanical checklist (runs automatically)
     ↓
<routing-recommendation> ← Advisory input (you see this)
     ↓
[Your Decision] ← Final routing decision (you make this)
     ↓
[Execution] ← Delegate to chosen agent OR handle directly
```

## Routing Recommendation Format

The recommendation appears in your context as:

```xml
<routing-recommendation request-hash="abc123...">
{
  "decision": "escalate" | "direct",
  "agent": "haiku-general" | "sonnet-general" | "opus-general" | null,
  "reason": "explanation of recommendation",
  "confidence": 0.0-1.0
}
</routing-recommendation>
```

## Interpretation Guide

### High Confidence Direct Routing (confidence > 0.8)

**Recommendation**: `{"decision": "direct", "agent": "haiku-general", "confidence": 0.95}`

**Interpretation**: The pre-router is confident this is a mechanical task suitable for Haiku.

**Your options**:
- ✅ Follow recommendation: Delegate to haiku-general agent
- ⚠️  Upgrade tier: If you see complexity the pre-router missed, use sonnet/opus instead
- ❌ Handle directly: Only if genuinely trivial (rare - usually still delegate)

### Escalation Recommendation

**Recommendation**: `{"decision": "escalate", "agent": null, "reason": "ambiguous scope"}`

**Interpretation**: The pre-router detected complexity/ambiguity requiring judgment.

**Your options**:
- ✅ Use your judgment: Analyze the request and choose appropriate agent
- ✅ Delegate to router agent: If routing decision itself is complex, use the router agent
- ✅ Ask for clarification: If request is genuinely ambiguous, use AskUserQuestion

### Low Confidence Recommendations (confidence < 0.7)

**Recommendation**: `{"decision": "direct", "agent": "sonnet-general", "confidence": 0.6}`

**Interpretation**: Pre-router made a guess but isn't sure.

**Your action**: Treat as escalation - use your judgment to make the final decision.

## When to Follow vs Override

### Follow the Recommendation When:

- High confidence (> 0.8)
- Reasoning makes sense
- No additional context that changes the assessment
- Mechanical task with explicit file paths → haiku-general
- Standard implementation task → sonnet-general

### Override the Recommendation When:

- You see hidden complexity the pre-router missed
- You have additional context (conversation history, project knowledge)
- Security/data integrity concerns
- User's actual intent differs from literal request
- The request is part of a multi-turn conversation

### Always Explain Your Decision

**Example - Following Recommendation**:
```
The pre-router recommends haiku-general for this syntax fix (confidence: 0.95).
I agree - this is a mechanical task with an explicit file path.
Let me delegate to haiku-general.
```

**Example - Overriding Recommendation**:
```
The pre-router suggests haiku-general (confidence: 0.85), but I notice this file
is part of the authentication system. Given the security implications, I'm upgrading
to sonnet-general for more careful analysis.
```

**Example - Escalating When Recommended**:
```
The pre-router flagged this as requiring judgment (escalation recommended).
I agree - "optimize performance" is vague and could mean many things.
Let me ask the user for clarification first.
```

## Metrics and Learning

Your routing decisions are tracked:
- Recommendation: What pre-router suggested
- Actual: What you chose
- Outcome: Success/failure of the delegated agent

This feedback helps improve the pre-router's mechanical escalation rules over time.

## Visibility

Both you and the user see the routing recommendation:
- **User sees (stderr)**: `[ROUTER] Recommendation: haiku-general (confidence: 0.95)`
- **You see (context)**: Full JSON recommendation with reasoning
- **Logs capture**: Both recommendation and your actual decision

This transparency builds trust and allows the user to understand the routing process.

## Important: You Still Have Agency

The pre-router is **advisory, not mandatory**. Key points:

1. **You make the final decision**: Pre-router provides input, you decide
2. **You have more context**: Conversation history, user intent, project knowledge
3. **You can handle simple queries**: If truly trivial, you can answer directly (rare)
4. **You should explain reasoning**: User sees both recommendation and your decision

## Example Scenarios

### Scenario 1: Clear Mechanical Task

**Request**: "Fix typo in README.md line 42: change 'teh' to 'the'"

**Recommendation**: `{"decision": "direct", "agent": "haiku-general", "confidence": 0.98}`

**Your decision**: Follow recommendation - this is exactly what haiku-general is for.

**Your response**:
```
The pre-router correctly identified this as a mechanical syntax fix.
I'll delegate to haiku-general to make this change.
```

---

### Scenario 2: Hidden Complexity

**Request**: "Update the auth configuration"

**Recommendation**: `{"decision": "direct", "agent": "sonnet-general", "confidence": 0.75}`

**Your decision**: The recommendation seems reasonable, but you notice this is a security-critical file. Upgrade to opus-general.

**Your response**:
```
The pre-router suggests sonnet-general, but I notice this involves authentication
configuration, which has security implications. I'm upgrading to opus-general for
extra careful handling of this security-sensitive change.
```

---

### Scenario 3: Ambiguous Request

**Request**: "Make it faster"

**Recommendation**: `{"decision": "escalate", "reason": "ambiguous scope - unclear what 'it' refers to"}`

**Your decision**: Agree with escalation - need clarification.

**Your response**:
```
The pre-router correctly flagged this as ambiguous. Before I can route effectively,
I need to clarify: What specifically should be optimized? The build process? Runtime
performance? A specific function? The UI responsiveness?
```

---

### Scenario 4: Multi-turn Context

**Request**: "Now add tests for that function" (referring to a function from 3 messages ago)

**Recommendation**: `{"decision": "escalate", "reason": "unclear referent"}`

**Your decision**: You have conversation context - "that function" is clear from history.

**Your response**:
```
The pre-router flagged "that function" as ambiguous (it doesn't have conversation
context), but from our discussion, I know you're referring to the `validateUser`
function we just implemented. I'll delegate to sonnet-general to add tests.
```

## Summary

- **Pre-router**: Fast, mechanical analysis with escalation triggers
- **You**: Final decision-maker with full context and judgment
- **Visibility**: Both recommendation and decision are logged and displayed
- **Learning**: Metrics track accuracy and improve the system
- **Flexibility**: You can follow, override, or escalate based on your assessment

The pre-router is a tool to help you, not a constraint on your agency.
