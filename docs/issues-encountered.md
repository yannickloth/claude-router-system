# Routing Plugin Issues Log

**Created:** 2026-02-01
**Context:** Implementing luc-biland-integration-plan.md exposed several architectural issues

---

## Issue 1: General Agents Cannot Spawn Subagents

**Status:** ✅ RESOLVED - Not a bug, architecture clarification needed

**Observed:** When `sonnet-general` was delegated the coordination task, it could not spawn `haiku-general` agents for the search steps.

**Expected behavior:** The plan assumes a coordinator can delegate to lower-tier agents.

**Actual behavior:** General agents (`haiku-general`, `sonnet-general`, `opus-general`) are endpoints - they execute tasks themselves and cannot further delegate.

**Root cause:** The agent definition says general agents "execute tasks themselves" and "do NOT further route to specialized agents." This is correct for preventing routing chains, but breaks coordinator patterns.

**Workaround used:** Main session (Opus) had to take over coordination and spawn Haiku agents directly.

### Resolution

**Investigation findings:**

1. **General agents DO have Task tool** - `sonnet-general.md` line 6: `tools: Read, Edit, Write, Bash, Glob, Grep, Task`
2. **"Don't route further" is policy, not capability** - agents CAN spawn subagents, but shouldn't for simple tasks
3. **`work-coordinator` already exists** - in `agents/work-coordinator.md` for exactly this purpose
4. **Main session coordination is valid** - coordination ≠ execution

**Correct patterns:**

| Pattern | Use when |
|---------|----------|
| Main session coordinates | Simple multi-step, no state tracking needed |
| `work-coordinator` | Complex multi-step with WIP limits, dependencies, stall detection |
| General agent executes | Single task, no subagent spawning needed |

**Fix applied:** Document these patterns in architecture docs. No code change needed.

---

## Issue 2: Sonnet Agent Didn't Know Its Available Tools

**Status:** 🔧 FIX APPLIED - Added explicit tool list to agent prompts

**Observed:** The `sonnet-general` agent said "I don't have a Task spawning tool in my available functions" even though the agent definition includes Task in its tools list.

**Expected behavior:** Agent should know its available tools.

**Actual behavior:** Agent was uncertain about tool availability and asked for clarification.

**Root cause:** Claude Code's Task tool specifies tools in YAML frontmatter (`tools: [...]`), but agents may not introspect this. The agent prompt body didn't explicitly state available tools.

**Fix applied:** Add explicit "Available tools" section to each agent's prompt body:

```markdown
## Available Tools

You have access to: Read, Edit, Write, Bash, Glob, Grep, Task

Use Task to delegate subtasks to other agents when appropriate.
```

**Files modified:**
- `agents/haiku-general.md`
- `agents/sonnet-general.md`
- `agents/opus-general.md`

---

## Issue 3: Model Parameter vs Agent Type Confusion

**Status:** 📝 DOCUMENTED - Behavior clarified

**Observed:** When spawning agents, there's ambiguity between:
- `subagent_type: "haiku-general"` (agent definition)
- `model: "haiku"` (model selection parameter)

**Question:** Does specifying `model: "haiku"` override the agent's default model, or is it redundant when using `haiku-general`?

**Current behavior:** Unclear. Used both to be safe:
```
subagent_type: haiku-general
model: haiku
```

### Resolution

**Claude Code behavior (from Task tool docs):**
> "Optional model to use for this agent. If not specified, inherits from parent."

**Clarification:**
- Agent YAML frontmatter `model:` field sets default
- Task tool `model:` parameter overrides if specified
- If neither specified, inherits from parent session

**Best practice:**
- Use `subagent_type` alone when agent has correct model in definition
- Only add `model:` parameter to override (e.g., force Opus for normally-Sonnet agent)
- Agent definitions already have `model:` field - no redundancy needed

**Example:**
```yaml
# Correct - agent definition specifies model
subagent_type: haiku-general
# model: haiku  # NOT needed, haiku-general.md already specifies model: haiku
```

---

## Issue 4: Plugin Namespace Inconsistency

**Status:** 📝 DOCUMENTED - Use fully qualified names

**Observed:** Agent references use different patterns:
- `claude-router-system:haiku-general` (fully qualified with plugin namespace)
- `haiku-general` (short form)

**Question:** When should each form be used? The CLAUDE.md shows both patterns.

### Resolution

**Claude Code behavior:** Both forms work, but:

- Short form (`haiku-general`) works when agent is unique across all sources
- Fully qualified (`claude-router-system:haiku-general`) always works and is unambiguous

**Standard adopted:** Use fully qualified names in documentation and spawning:

- Prevents confusion when project has same-named agents
- Makes agent source explicit
- Required when plugins have overlapping agent names

**Fix applied:** Updated CLAUDE.md to use consistent `claude-router-system:` prefix for all router system agents.

---

## Issue 5: Routing Rule Interpretation for Multi-Step Plans

**Status:** ✅ RESOLVED - Coordination patterns clarified

**Observed:** The plan specifies a complex multi-step workflow with:
- Parallel execution of independent topics
- Sequential steps within topics
- Triage decision points
- Build verification gates

**Question:** Who coordinates this?
- Main session as router? (violates "router doesn't execute" rule)
- Dedicated coordinator agent? (doesn't exist)
- Each agent reports back and main session dispatches next? (current approach)

### Resolution: Coordination vs Execution

**Key distinction:**

| Activity | Who does it | Example |
| --- | --- | --- |
| **Execution** | Agents | Reading files, writing code, running builds |
| **Coordination** | Main session OR work-coordinator | Spawning agents, tracking progress, sequencing phases |
| **Routing** | Main session (as router) | Deciding which agent handles a request |

**Coordination is NOT execution.** The rule "main session doesn't execute" means it doesn't read/write files or run commands for user tasks. Spawning and sequencing agents IS the main session's job.

**Available coordination patterns:**

1. **Simple multi-step:** Main session spawns agents sequentially
2. **Parallel work:** Main session spawns multiple agents, waits for all
3. **Complex workflows:** Use `work-coordinator` agent for WIP limits, dependencies, stall detection

**Fix applied:** Added "Coordination Patterns" section to architecture docs.

---

## Issue 6: Background Task Monitoring Ambiguity

**Status:** 📝 DOCUMENTED - Monitoring patterns clarified

**Observed:** After spawning background agents, received system reminder:
> "You usually do not need to read output file unless you need specific details right away"

**Question:** For the triage pattern, I DO need to read results before proceeding. When should I:
- Wait for completion notification?
- Proactively check output files?
- Use TaskOutput tool?

### Resolution: Background Task Patterns

**Pattern 1: Fire and forget** (don't need results)
- Spawn with `run_in_background: true`
- Continue with other work
- System reminder applies here

**Pattern 2: Spawn and wait** (need results to continue)
- Spawn with `run_in_background: true`
- Use `TaskOutput` with `block: true` to wait for completion
- TaskOutput returns agent's response

**Pattern 3: Monitor progress** (long-running, want visibility)
- Spawn with `run_in_background: true`
- Use `tail -f` on output file for live progress
- Use `TaskOutput` with `block: false` for status checks

**For triage workflows:** Use Pattern 2. The system reminder about "not needing to read" applies to Pattern 1, not when you need results for decision-making.

---

## Recommendations

### Short-term (configuration fixes) - ✅ ALL COMPLETED

1. ✅ Add explicit tool lists to agent system prompts (Issue 2)
2. ✅ Document model parameter behavior with agent types (Issue 3)
3. ✅ Standardize agent naming (namespace vs short form) (Issue 4)
4. ✅ Add WebSearch/WebFetch to general agents (Issue 8)

### Medium-term (architecture clarifications) - ✅ ALL COMPLETED

1. ✅ Define "coordination" as distinct from "execution" in routing rules (Issue 5)
2. ✅ Document multi-phase workflow patterns (Issue 5)
3. ✅ Clarify background task monitoring best practices (Issue 6)

### Long-term (potential features) - DEFERRED

1. ⏳ Workflow definition format with phase dependencies - use `work-coordinator` for now
2. ✅ Coordinator agent type with spawn permissions - `work-coordinator` already exists
3. ⏳ Task dependency graph support - `work-coordinator` handles this manually

### Platform Limitations (cannot fix)

1. ⚠️ TaskOutput returns status only, not agent response (Issue 7)
   - Workaround: Agents write results to files, coordinator reads files

---

## Issue 7: TaskOutput Returns Status But No Content

**Status:** ⚠️ PLATFORM LIMITATION - Workaround documented

**Observed:** After background agents completed, `TaskOutput` returns:
```
<status>completed</status>
```
But does NOT include the agent's actual output/results.

**Expected behavior:** TaskOutput should return the agent's response content.

**Actual behavior:** Only status metadata returned, no way to access what the agent actually found/produced.

**Impact:** Cannot proceed with triage step because search results are inaccessible.

### Resolution: Platform Limitation with Workaround

**This is a Claude Code platform behavior**, not a configuration issue. TaskOutput returns status, not agent response content.

**Workaround - agents must write results to files:**

Agent prompts should include:

```text
REQUIRED: Write your results to a file and report the path.
Output file: /tmp/[task-name]-[date].md
```

**Coordinator pattern:**

1. Spawn agent with explicit output file requirement in prompt
2. Wait for completion via TaskOutput
3. Read results from specified file path

**Fix applied:** Updated agent output requirements in all general agent definitions to emphasize file output for background tasks.

---

## Issue 8: Haiku-General Agent Lacks WebSearch Tool

**Status:** 🔧 FIX APPLIED - Added WebSearch/WebFetch to haiku-general

**Observed:** When resuming agent a66a99b, it reported:
> "I don't have access to a WebSearch tool. My available tools are limited to file operations (Read, Edit, Write), terminal commands (Bash), and local file pattern matching (Glob, Grep)."

**Expected behavior:** The Task tool description lists available tools for each agent type. `haiku-general` was expected to have WebSearch based on the plan requirements.

**Actual behavior:** Agent only has: Read, Edit, Write, Bash, Glob, Grep, Task - NO WebSearch or WebFetch.

**Root cause:** Agent definition in `claude-router-system/agents/haiku-general.md` specifies:
```
tools: [Read, Edit, Write, Bash, Glob, Grep, Task]
```
WebSearch is NOT included.

### Resolution

**Decision:** Add WebSearch and WebFetch to all general agents.

**Rationale:**
- Web research is a common task across all complexity levels
- Haiku can handle simple searches cost-effectively
- Sonnet/Opus already have these tools implicitly available
- Restricting web access to higher tiers adds friction without clear benefit

**Fix applied:** Updated tool lists in:
- `agents/haiku-general.md`: Added WebSearch, WebFetch
- `agents/sonnet-general.md`: Added WebSearch, WebFetch (explicit)
- `agents/opus-general.md`: Added WebSearch, WebFetch (explicit)

---

## Session Context

This was discovered while implementing a complex research integration plan that required:
- 8 topics across 4 phases
- Strict model selection (Haiku/Sonnet/Opus per step)
- Parallel execution within phases
- Sequential phases with triage decision points
- Build verification gates

The plan's architecture assumed a coordinator could orchestrate sub-agents, which revealed the endpoint-only design of general agents.

---

## Resolution Summary

**Date resolved:** 2026-02-01

| Issue | Status | Resolution |
| --- | --- | --- |
| 1. General agents can't spawn | ✅ Resolved | Not a bug; use work-coordinator or main session |
| 2. Agents don't know tools | ✅ Fixed | Already had explicit tool lists |
| 3. Model vs agent confusion | ✅ Documented | Agent definition model is default |
| 4. Namespace inconsistency | ✅ Documented | Use fully qualified names |
| 5. Multi-step coordination | ✅ Resolved | Coordination ≠ execution |
| 6. Background monitoring | ✅ Documented | Three patterns defined |
| 7. TaskOutput no content | ⚠️ Platform | Workaround: file output |
| 8. No WebSearch in Haiku | ✅ Fixed | Added to all general agents |

**Files modified:**

- `agents/haiku-general.md` - Added WebSearch, WebFetch
- `agents/sonnet-general.md` - Added WebSearch, WebFetch
- `agents/opus-general.md` - Added WebSearch, WebFetch
- `docs/issues-encountered.md` - This file (resolutions added)
