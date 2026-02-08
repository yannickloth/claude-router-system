# Claude Router System - Project Configuration

Project-specific overrides for the global CLAUDE.md. These take precedence over global settings.

---

## Router System Instructions

**CRITICAL: This project has a routing plugin. Router directives are MANDATORY and NON-NEGOTIABLE.**

When you see a `<routing-recommendation>` block with a routing directive:

1. **READ the ACTION INSTRUCTIONS** in the directive
2. **EXTRACT decision, agent, and reason** values
3. **EXECUTE the specified action IMMEDIATELY** - no delay, no questions
4. **DO NOT ask for clarification** about the routing decision
5. **DO NOT apply your own judgment** to override the routing

The router system's entire value depends on you following its decisions WITHOUT second-guessing. If the directive says to escalate to the router agent, you MUST invoke it. If it says to route to a specific agent, you MUST invoke that agent.

**What a routing directive looks like:**

```
<routing-recommendation request-hash="abc123">
ROUTING DIRECTIVE - MANDATORY ACTION REQUIRED. No interpretation allowed.

Decision: escalate|direct
Reason: [reason text]
Confidence: [0.0-1.0]

ACTION INSTRUCTIONS:
- You MUST NOT handle this request directly
- You MUST use the Task tool to invoke a router agent
- You MUST NOT ask clarifying questions
- Execute the action specified...

{JSON with decision, agent, reason, confidence}

IF decision == "escalate": Invoke infolead-claude-subscription-router:router
IF decision == "direct": Invoke the specified agent...
</routing-recommendation>
```

**When you see this, act immediately. No hesitation. No questions.**

---

## Project Structure

- Plugin: `plugins/infolead-claude-subscription-router/`
- Tests: `tests/infolead-claude-subscription-router/`
- Implementation: `plugins/infolead-claude-subscription-router/implementation/` (14 modules, 9K+ lines)
- Hooks: `plugins/infolead-claude-subscription-router/hooks/` (10 bash scripts)
- Agents: `plugins/infolead-claude-subscription-router/agents/` (.md with YAML frontmatter)

---

## Known Issues

See `plugins/infolead-claude-subscription-router/docs/` for detailed analysis:

- `test_hooks_path_valid`: false positive (tries to resolve hooks dict as file path)
- `test_hook_scripts_check_jq`: false positive (indirect jq usage detection)
- E2E `verify_hooks_json`: looks for nonexistent `hooks/hooks.json`
- Bash hook test 6: hangs (model tier detection)

These are pre-existing issues, not regressions from recent changes.

---

## Design Principles

This project uses the **Independent Variation Principle (IVP)** throughout its architecture.

See `~/.claude/design-principles.md` for detailed methodology and `plugins/infolead-claude-subscription-router/docs/ARCHITECTURE.md` for how IVP is applied here.
