# Background Agent Write Permissions

**Status:** Production fix for background agent file write denials
**Last updated:** 2026-02-07

---

## Problem

When agents are spawned with `run_in_background: true` via the Task tool, they cannot get interactive permission approvals for Write and Edit tools. The permission prompt has no user to respond to, so all file writes are **auto-denied**.

### Symptoms

- Background agents complete but produce no output files
- Agent logs show `Permission to use Write has been auto-denied in dontAsk mode`
- Foreground agents with the same configuration work correctly
- The problem affects any agent that uses Write or Edit tools when running in the background

### Impact

This was discovered when 14 literature-integrator agents were spawned in parallel. All agents completed their research (web searches, file reads, content development) but none could save results to integration guide files. Only manually-saved content from foreground sessions survived.

---

## Root Cause

Claude Code's permission model requires interactive user approval for Write/Edit operations. Background agents have no interactive terminal, so:

1. Agent calls Write tool
2. Claude Code checks permission
3. No user present to approve
4. Permission auto-denied
5. Agent continues without writing (often silently)

This is a gap in Claude Code's architecture, not a plugin bug.

---

## Solution: Defense in Depth (3 Layers)

The fix uses three independent layers. If any one is buggy or fails, the others catch it.

### Layer 1: `permissionMode: acceptEdits` in Agent Frontmatter

The intended mechanism per Claude Code documentation. Added to all agents that have Write or Edit in their tools list:

| Agent | permissionMode |
|-------|---------------|
| haiku-general | `acceptEdits` |
| sonnet-general | `acceptEdits` |
| opus-general | `acceptEdits` |
| work-coordinator | `acceptEdits` |
| temporal-scheduler | `acceptEdits` |

**Known issue:** Subagent permission inheritance is buggy (see Related GitHub Issues). This layer may not work reliably, which is why Layers 2 and 3 exist.

### Layer 2: PreToolUse Hook (Most Reliable)

A `PreToolUse` hook that programmatically approves Write/Edit tool calls by returning `{"permissionDecision": "allow"}` on stdout.

**Hook:** `hooks/pre-tool-use-write-approve.sh`
**Matcher:** `Write|Edit`
**Timeout:** 5 seconds

This is the most reliable mechanism per community reports and works regardless of `permissionMode` bugs. The hook:
- Reads the tool call JSON from stdin
- Logs the approval to stderr for visibility (`[permissions] Auto-approved Write for subagent`)
- Returns the permission JSON on stdout

### Layer 3: Settings Permissions

`Write(*)` and `Edit(*)` added to the `permissions.allow` array in the target settings file. This is a belt-and-suspenders fallback.

The `setup-hooks-workaround.sh` script handles this automatically for all three scopes:
- `--local` (`.claude/settings.local.json`)
- `--project` (`.claude/settings.json`)
- `--global` (`~/.claude/settings.json`)

---

## Security Considerations

The PreToolUse hook approves **all** Write/Edit calls without path filtering. This is intentional:

- The agents already have Write/Edit in their `tools` frontmatter, meaning the user declared intent for these agents to write files
- This is no different from the interactive behavior (where the user would click "Allow")
- The safety boundary is the agent definition itself, not the permission prompt
- All approvals are logged to stderr for auditability

If you need path-scoped restrictions, implement them in a custom PreToolUse hook that checks `tool_input.file_path` before approving.

---

## Installation

### Automatic (Recommended)

The `setup-hooks-workaround.sh` script installs both the hooks and the permissions:

```bash
cd plugins/infolead-claude-subscription-router

# Choose your scope:
./scripts/setup-hooks-workaround.sh --local      # This user, this project
./scripts/setup-hooks-workaround.sh --project     # All users, this project
./scripts/setup-hooks-workaround.sh --global      # This user, all projects

# Preview first:
./scripts/setup-hooks-workaround.sh --local --dry-run
```

### Manual

Add to your settings file (`settings.local.json`, `settings.json`, or `~/.claude/settings.json`):

```json
{
  "permissions": {
    "allow": [
      "Write(*)",
      "Edit(*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/pre-tool-use-write-approve.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

---

## Verification

```bash
# 1. Test the hook directly
echo '{"tool_name": "Write"}' | hooks/pre-tool-use-write-approve.sh
# Should output: {"permissionDecision": "allow"}

# 2. Verify agent frontmatter
grep -l "permissionMode: acceptEdits" agents/*.md
# Should list 5 agents

# 3. Verify plugin.json has PreToolUse
grep -A5 "PreToolUse" plugin.json
# Should show the hook configuration

# 4. Run tests
./tests/infolead-claude-subscription-router/run_all_tests.sh
```

---

## Reverting

```bash
# Remove hooks and permissions
./scripts/setup-hooks-workaround.sh --local --revert

# Preview what will be removed
./scripts/setup-hooks-workaround.sh --local --revert --dry-run
```

The `permissionMode` in agent frontmatter is harmless if left in place (it's the intended default behavior for these agents).

---

## Related GitHub Issues

| Issue | Title |
|-------|-------|
| [#18950](https://github.com/anthropics/claude-code/issues/18950) | Skills/subagents do not inherit user-level permissions |
| [#10906](https://github.com/anthropics/claude-code/issues/10906) | Plan agent ignores parent settings.json permissions |
| [#11934](https://github.com/anthropics/claude-code/issues/11934) | Sub agents auto-denied in dontAsk mode |
| [#10225](https://github.com/anthropics/claude-code/issues/10225) | Plugin hooks match but never execute |
| [#14410](https://github.com/anthropics/claude-code/issues/14410) | Local plugin hooks match but never execute |

---

## Future Removal

When Claude Code fixes the upstream permission inheritance bugs:

1. Layer 2 (PreToolUse hook) and Layer 3 (settings permissions) can be removed via `--revert`
2. Layer 1 (`permissionMode: acceptEdits`) should be kept as the intended mechanism
3. Monitor the GitHub issues above for resolution

---

## Related Documentation

- [HOOKS-WORKAROUND.md](HOOKS-WORKAROUND.md) - Plugin hook execution bug workaround
- [Claude Code Permissions Docs](https://code.claude.com/docs/en/permissions)
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
