# Context Threshold Monitoring

## Overview

The context threshold monitoring feature warns users when they approach Claude's 100K token context window limit. This helps prevent unexpected conversation truncation and allows users to create continuation prompts before losing important context.

## Implementation

### Hook: `check-context-threshold.sh`

**Trigger:** UserPromptSubmit (fires on every user message)

**Threshold:** 70% of 100K tokens (70,000 tokens)

**Estimation Method:**
- Counts conversation turns in the active transcript file (`~/.cache/claude/transcripts/*.jsonl`)
- Conservative estimate: 1,000 tokens per turn average
- Includes user messages, assistant responses, tool calls, and system messages

### Session State Management

**Session Flags File:** `~/.claude/infolead-claude-subscription-router/projects/{project-id}/state/session-flags.json`

The hook uses a session flag (`context_threshold_warned`) to ensure the warning is only shown once per session. This flag is cleared when a new session starts via the `load-session-state.sh` hook.

### Warning Display

When the threshold is crossed, users see:

```
⚠️  CONTEXT THRESHOLD WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current context usage: ~70000 tokens (70% of 100000 limit)

You are approaching Claude's context window limit. Consider:

1. Wrap up current conversation and start a new session
2. Create a continuation prompt to preserve important context
3. Save work-in-progress state before switching sessions

To create a continuation prompt:
  "Please create a continuation prompt summarizing our session"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Claude Context

The hook also provides context to Claude (via stdout) so Claude knows the user has been warned and can assist if they request a continuation prompt:

```xml
<context-threshold-notice>
CONTEXT USAGE: ~70000 tokens (70% of 100000)

User has been notified about high context usage. If they request a continuation prompt:
1. Summarize key discussion points and decisions made
2. List work in progress and next steps
3. Include relevant file paths and code snippets
4. Format as a clear, concise prompt for the next session

Do NOT proactively create a continuation prompt unless requested.
</context-threshold-notice>
```

## Configuration

### Adjusting the Threshold

Edit `/plugins/infolead-claude-subscription-router/hooks/check-context-threshold.sh`:

```bash
CONTEXT_LIMIT=100000          # Total context window
THRESHOLD_PERCENT=70          # Warn at 70%
```

### Disabling the Feature

Remove the hook from `plugin.json`:

```json
"UserPromptSubmit": [
  {
    "matcher": "*",
    "hooks": [
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/user-prompt-submit.sh",
        "timeout": 10
      }
      // Remove the check-context-threshold.sh entry
    ]
  }
]
```

## Testing

Run the test suite:

```bash
./tests/infolead-claude-subscription-router/test_context_threshold.sh
```

Tests verify:
1. Hook script exists and is executable
2. Hook has valid bash syntax
3. Hook is registered in plugin.json
4. Session flags are cleared on session start
5. Hook has proper error handling
6. Hook sources hook infrastructure
7. Hook checks for jq dependency
8. Hook uses project-specific state directory
9. Hook defines threshold constants
10. Hook implements warn-once logic

## Architecture

### Change Driver

**Change Driver:** `CONTEXT_MANAGEMENT`

Changes when:
- Threshold logic changes
- Warning message format changes
- Token estimation method changes

### Dependencies

- `hook-preamble.sh`: Hook infrastructure and common functions
- `jq`: JSON parsing for session flags
- `get_project_data_dir()`: Project-specific state directory
- `check_jq()`: Dependency validation

### IVP Compliance

This feature follows the Independent Variation Principle (IVP):
- **Single change driver:** All code responds to context management requirements
- **Isolated from routing:** No routing logic mixed in
- **Isolated from quota tracking:** Separate concern from API usage
- **Clean integration:** Uses existing hook infrastructure without modification

## Limitations

1. **Token estimation is approximate:** Uses turn count heuristic rather than actual token counting
2. **Conservative estimates:** Better to warn early than too late
3. **No transcript size limit:** Assumes transcript files are reasonably sized
4. **Single warning per session:** Won't warn again if user continues past threshold

## Future Enhancements

Potential improvements (not currently implemented):

1. **Actual token counting:** Use tokenizer to count real tokens
2. **Progressive warnings:** Warn at 70%, 85%, 95%
3. **Auto-summarization:** Automatically create continuation prompt at 90%
4. **Context compression:** Summarize older parts of conversation to free space
5. **Smart threshold:** Adjust based on conversation type (code vs. discussion)
