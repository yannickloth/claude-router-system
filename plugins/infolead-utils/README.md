# Infolead Utils Plugin

Utility hooks for context enhancement in Claude Code sessions.

## Features

### DateTime Context Injection

Automatically injects the current local date and time into Claude's context before each prompt.

**Hook:** `UserPromptSubmit`
**Purpose:** Provide Claude with accurate, up-to-date timestamp information from the user's local machine (not the server).

**Context injected:**
- Current date (YYYY-MM-DD with weekday)
- Current time (HH:MM:SS)
- Timezone (name and UTC offset)
- Full timestamp string

**Why this matters:**
- Claude's system prompt shows server time, which may differ from user's local time
- Many tasks require accurate local date/time context (scheduling, logs, time-sensitive operations)
- Ensures Claude has user's actual local timezone, not UTC

## Installation

The plugin hooks need to be copied to `.claude/settings.local.json` due to a Claude Code plugin hook execution bug.

Run the setup script:

```bash
./plugins/infolead-utils/scripts/setup-hooks.sh
```

After installation, restart Claude Code for changes to take effect.

## Architecture

This plugin is **orthogonal to the routing plugin** - it has a completely different change driver:

- **Routing plugin**: Changes when routing logic/rules change
- **Utils plugin**: Changes when context enhancement needs change

This separation follows the Independent Variation Principle (IVP).

## Version History

- **1.0.0** (2026-02-11): Initial release with datetime context injection
