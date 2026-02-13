# Plugin Hooks Workaround

**Status:** Temporary workaround for Claude Code plugin hook execution bugs
**Affected versions:** Claude Code (as of February 2026)
**Last updated:** 2026-02-06

---

## Problem

Plugin hooks defined in `plugin.json` are matched by Claude Code but **never execute**. This affects all hook types:

- `UserPromptSubmit`
- `SessionStart` / `SessionEnd`
- `SubagentStart` / `SubagentStop`
- `PreToolUse` / `PostToolUse`

### Symptoms

- Hooks appear in Claude Code's hook resolution logs as "matched"
- Hook commands never execute (no log files created, no side effects)
- The `isLocal: true` or plugin-sourced hooks are affected regardless of scope

---

## Known GitHub Issues

This is a confirmed bug affecting multiple users:

| Issue | Title | Status |
|-------|-------|--------|
| [#10225](https://github.com/anthropics/claude-code/issues/10225) | UserPromptSubmit hooks from plugins match but never execute | Open |
| [#14410](https://github.com/anthropics/claude-code/issues/14410) | Local plugin hooks match but never execute (isLocal: true) | Open |
| [#6305](https://github.com/anthropics/claude-code/issues/6305) | Post/PreToolUse Hooks Not Executing | Open |
| [#2891](https://github.com/anthropics/claude-code/issues/2891) | Hooks not executing despite following documentation | Open |
| [#5093](https://github.com/anthropics/claude-code/issues/5093) | Hooks configured but not executing despite being detected | Open |

**Root cause:** Claude Code's plugin system correctly parses and matches hooks but fails to execute the associated commands for plugin-sourced hooks.

---

## Workaround

Copy the hooks from `plugin.json` directly into a settings file. Hooks defined in settings files execute correctly.

**Three installation scopes are available:**

| Scope | Target File | Affects |
|-------|-------------|---------|
| `--local` | `.claude/settings.local.json` | This user only, this project only |
| `--project` | `.claude/settings.json` | All users of this project (committed to git) |
| `--global` | `~/.claude/settings.json` | This user, all projects |

### Automatic Setup

Run the workaround setup script:

```bash
# From the plugin directory
cd plugins/infolead-claude-subscription-router

# Install for this user only, this project only
./scripts/setup-hooks-workaround.sh --local

# Install for all users of this project (committed to git)
./scripts/setup-hooks-workaround.sh --project

# Install for this user, all projects
./scripts/setup-hooks-workaround.sh --global

# Preview changes first (dry-run)
./scripts/setup-hooks-workaround.sh --local --dry-run
./scripts/setup-hooks-workaround.sh --project --dry-run
./scripts/setup-hooks-workaround.sh --global --dry-run
```

### Manual Setup

1. Choose your target file:
   - **Local**: `.claude/settings.local.json` (this user, this project)
   - **Project**: `.claude/settings.json` (all users, this project - committed)
   - **Global**: `~/.claude/settings.json` (this user, all projects)

2. Add or merge the `hooks` section with the following configuration:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/user-prompt-submit.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/log-subagent-start.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/log-subagent-stop.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/load-session-state.sh",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/load-session-memory.sh",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/morning-briefing.sh",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/evening-planning.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/save-session-state.sh",
            "timeout": 5
          }
        ]
      }
    ],
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
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/plugins/infolead-claude-subscription-router/hooks/cache-invalidation.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

3. Replace `/path/to/plugins/infolead-claude-subscription-router` with your actual plugin path:
   - If installed via marketplace: `~/.claude/marketplace/plugins/infolead-claude-subscription-router`
   - If cloned locally: `/path/to/your/clone/plugins/infolead-claude-subscription-router`

4. Restart Claude Code for changes to take effect

### Verifying the Workaround

```bash
# Test that hooks now execute
# Start a new Claude Code session and check for:

# 1. Session start hooks (check for log output)
cat ~/.claude/infolead-claude-subscription-router/logs/session.log

# 2. User prompt submit (routing recommendations should appear)
# Type any prompt and look for [ROUTER] output

# 3. Subagent hooks (spawn any agent and check logs)
cat ~/.claude/infolead-claude-subscription-router/logs/subagents.log
```

---

## Reverting the Workaround

When Claude Code fixes the plugin hook execution bug:

```bash
# Revert based on how you installed
./scripts/setup-hooks-workaround.sh --local --revert
./scripts/setup-hooks-workaround.sh --project --revert
./scripts/setup-hooks-workaround.sh --global --revert

# Preview what will be removed
./scripts/setup-hooks-workaround.sh --local --revert --dry-run
```

The plugin's `plugin.json` hooks will automatically take over once the bug is fixed.

To check if the bug is fixed, monitor the GitHub issues linked above.

---

## Technical Details

### Why This Works

- Hooks in `~/.claude/settings.json` use a different code path than plugin hooks
- The settings.json hooks bypass the plugin hook resolution that has the execution bug
- Both hook sources use the same hook format and command execution

### Path Resolution

The plugin uses `${CLAUDE_PLUGIN_ROOT}` variable in `plugin.json`, which should resolve to the plugin directory. In the workaround, we use absolute paths since settings.json doesn't support this variable.

### Merging with Existing Hooks

If you already have hooks in `~/.claude/settings.json`, merge them carefully:
- Each hook type (e.g., `SessionStart`) is an array
- Add the plugin hooks to the existing arrays, don't replace them
- Order matters: hooks execute in array order

---

## Related Documentation

- [Claude Code Hooks Documentation](https://docs.anthropic.com/claude-code/hooks)
- [Plugin Structure Documentation](https://docs.anthropic.com/claude-code/plugins)
- [plugin.json](../plugin.json) - Original hook definitions

---

## Reporting Issues

If you encounter problems with this workaround:

1. Check that absolute paths are correct
2. Verify hook scripts are executable: `chmod +x hooks/*.sh`
3. Check Claude Code logs for hook execution errors
4. Open an issue at [GitHub Issues](https://github.com/yannickloth/claude-router-system/issues)

For the upstream bug, consider adding your experience to the existing GitHub issues to help Anthropic prioritize the fix.
