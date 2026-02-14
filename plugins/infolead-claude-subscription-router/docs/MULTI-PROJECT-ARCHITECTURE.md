# Multi-Project Architecture (v1.7.0+)

**Status:** Implemented in v1.7.0
**Architecture:** Hybrid (Global Router + Project-Specific State)
**Last updated:** 2026-02-14

---

## Overview

Starting with v1.7.0, the Claude Router System uses a **hybrid architecture** that solves all multi-project problems while maintaining simplicity:

- **Global router logic** (one plugin installation, one set of hooks)
- **Project-specific state/metrics/logs** (complete isolation between projects)
- **Project-aware configuration** (project → global cascade)

This means you can:
- Work on 5 different projects simultaneously without state corruption
- Have project-specific routing rules
- Track metrics separately per project
- Switch between projects instantly without interference

---

## Architecture Decision

We evaluated three approaches:

| Approach | Description | Pros | Cons | Decision |
|----------|-------------|------|------|----------|
| **A: Full Isolation** | Separate router per project | Clean separation | Duplication, config drift | ❌ Rejected |
| **B: Fully Global** | Single global state | Simple | State corruption | ❌ Rejected |
| **C: Hybrid** | Global logic + project state | Best of both | Moderate complexity | ✅ **Chosen** |

**Chosen: Option C (Hybrid)**

### Why Hybrid?

1. **Router logic doesn't need duplication** - routing rules are the same across projects
2. **State MUST be isolated** - work-in-progress from Project A shouldn't appear in Project B
3. **Configuration should cascade** - project-specific overrides, global defaults
4. **Metrics need project context** - for cost tracking and analysis per-project

---

## How It Works

### Project Detection

Every hook detects the current project automatically:

```bash
# In common-functions.sh
detect_project_root() {
    # Walks up from PWD looking for .claude directory
    # Returns: /home/user/code/my-project
}

get_project_id() {
    # Generates stable hash of project root path
    # Returns: "abc123def456" (16-char hex)
}
```

### Storage Structure

```
~/.claude/infolead-claude-subscription-router/
└── projects/
    ├── abc123def456/           # Project A (hashed path ID)
    │   ├── state/
    │   │   └── session-state.json
    │   ├── metrics/
    │   │   └── 2026-02-14.jsonl
    │   └── logs/
    │       ├── routing.log
    │       └── archive/
    ├── 789ghi012jkl/           # Project B
    │   ├── state/
    │   ├── metrics/
    │   └── logs/
    └── global/                 # Fallback (no .claude detected)
        ├── state/
        ├── metrics/
        └── logs/
```

**Key points:**
- Each project gets its own isolated directories
- Project ID is stable hash of project root path
- If no `.claude` directory found, uses "global" fallback
- No risk of state mixing between projects

### Configuration Cascade

Configuration loads in priority order:

```yaml
# Priority 1: Project-specific (highest)
/home/user/code/my-project/.claude/adaptive-orchestration.yaml

# Priority 2: Global user config
~/.claude/adaptive-orchestration.yaml

# Priority 3: Plugin defaults (fallback)
# Built into adaptive_orchestrator.py
```

Example use case:
```bash
# Global: Use defaults for most projects
~/.claude/adaptive-orchestration.yaml:
  force_mode: null

# Project A: Force single-stage for speed-critical project
~/code/speed-app/.claude/adaptive-orchestration.yaml:
  force_mode: "single_stage"

# Project B: Force multi-stage for complex analysis project
~/code/research/.claude/adaptive-orchestration.yaml:
  force_mode: "multi_stage"
```

### Per-Project Enable/Disable

Disable router for specific projects:

```json
# my-project/.claude/settings.json
{
  "plugins": {
    "router": {
      "enabled": false
    }
  }
}
```

When disabled, all hooks exit silently for that project.

---

## Migration from v1.6.x

### For Existing Users

If you're upgrading from v1.6.x (global state), run the migration script **once per project**:

```bash
cd ~/code/project-a
/path/to/plugin/scripts/migrate-to-project-isolation.sh

cd ~/code/project-b
/path/to/plugin/scripts/migrate-to-project-isolation.sh

# etc for all your projects
```

**What it does:**
1. Detects current project
2. Copies old global state/metrics/logs to project-specific directories
3. Adds project context to migrated data
4. Leaves old data in place (safe to delete after verifying all projects work)

**Migration script preserves:**
- Session state
- Routing metrics
- Agent usage logs
- Log archives

---

## Hook Behavior Changes

### v1.6.x (Old - Global State)

```bash
# ALL projects wrote to same directory
METRICS_DIR="$HOME/.claude/infolead-claude-subscription-router/metrics"

# Switching projects corrupted state:
cd ~/project-a  # State: "WIP: Feature X"
cd ~/project-b  # State STILL shows: "WIP: Feature X" (WRONG!)
```

### v1.7.0+ (New - Project-Specific)

```bash
# Each project gets isolated directory
METRICS_DIR=$(get_project_data_dir "metrics")
# Returns: ~/.claude/.../projects/abc123/metrics/

# Switching projects works correctly:
cd ~/project-a  # State: "WIP: Feature X" (isolated)
cd ~/project-b  # State: "WIP: Feature Y" (different state, no interference)
```

---

## systemd Overnight Execution

### Multi-Project Queuing

The overnight execution system now understands project context:

```bash
# In Project A
cd ~/code/project-a
/overnight search for React hooks patterns

# In Project B
cd ~/code/project-b
/overnight optimize database queries

# Queued work stored with project context:
~/.claude/.../projects/abc123/state/overnight-queue.json
~/.claude/.../projects/789ghi/state/overnight-queue.json
```

### Installation

systemd service file is now a **template** that gets customized during installation:

```bash
# Template (plugins/.../systemd/claude-overnight-executor.service)
ExecStart=__PLUGIN_ROOT__/scripts/overnight-executor.sh

# After installation (replaces __PLUGIN_ROOT__ with actual path)
ExecStart=/home/user/.claude/marketplace/plugins/.../overnight-executor.sh
```

This supports:
- Marketplace installations (`~/.claude/marketplace/...`)
- Local clones (`/path/to/clone/plugins/...`)
- Any custom installation path

---

## Testing Multi-Project Setup

### Scenario 1: Two Projects Simultaneously

```bash
# Terminal 1: Project A
cd ~/code/frontend
claude-code
# Type: "Add login button"
# Router should use Project A's state/metrics

# Terminal 2: Project B (at same time!)
cd ~/code/backend
claude-code
# Type: "Optimize database queries"
# Router should use Project B's state/metrics (completely isolated)
```

**Expected:**
- No state corruption
- Each project has independent metrics
- Morning briefing shows correct WIP for each project

### Scenario 2: Rapid Project Switching

```bash
cd ~/code/project-a
claude-code
# Do some work...
# Exit

cd ~/code/project-b
claude-code
# Do some work...
# Exit

cd ~/code/project-a
claude-code
# Should resume Project A's state, NOT Project B's
```

**Expected:**
- Session state loads correctly for each project
- No "session did not end cleanly" false positives
- Work-in-progress is project-specific

### Scenario 3: Project-Specific Config

```bash
# Set up different configs
echo 'force_mode: "single_stage"' > ~/code/fast-app/.claude/adaptive-orchestration.yaml
echo 'force_mode: "multi_stage"' > ~/code/complex-app/.claude/adaptive-orchestration.yaml

# Test both
cd ~/code/fast-app
# Router should use single-stage mode

cd ~/code/complex-app
# Router should use multi-stage mode
```

**Expected:**
- Each project uses its own config
- No interference between projects

---

## Metrics and Cost Tracking

### Per-Project Metrics

All metrics now include project context:

```jsonl
{
  "record_type": "routing_recommendation",
  "timestamp": "2026-02-14T10:30:00Z",
  "project": {
    "id": "abc123def456",
    "root": "/home/user/code/my-project",
    "name": "my-project"
  },
  "recommendation": {...}
}
```

### Cross-Project Analysis

While data is stored per-project, you can aggregate:

```bash
# Analyze single project
jq 'select(.project.name == "frontend")' ~/.claude/.../projects/*/metrics/*.jsonl

# Aggregate all projects
cat ~/.claude/.../projects/*/metrics/2026-02-14.jsonl | jq -s 'group_by(.project.name)'

# Cost by project
jq -s 'group_by(.project.name) | map({project: .[0].project.name, agents: length})' \
  ~/.claude/.../projects/*/metrics/*.jsonl
```

---

## Troubleshooting

### Problem: "No old data found" during migration

**Cause:** Either:
1. You're already on v1.7.0+ (already migrated)
2. Fresh installation (no old data to migrate)

**Solution:** Nothing to do - you're ready to go!

### Problem: State shows wrong project's work

**Cause:** Hooks not detecting project root correctly

**Debug:**
```bash
cd /your/project
source /path/to/plugin/hooks/common-functions.sh
detect_project_root
# Should print: /your/project
```

**Fix:** Ensure your project has a `.claude/` directory

### Problem: Router disabled unexpectedly

**Check project settings:**
```bash
jq '.plugins.router.enabled' /your/project/.claude/settings.json
# Should return: true or null (default is enabled)
```

### Problem: Metrics mixing between projects

**This should NOT happen in v1.7.0+.** If it does:

1. Check hook versions:
   ```bash
   grep "get_project_data_dir" /path/to/plugin/hooks/*.sh
   # Should find matches - if not, hooks not updated
   ```

2. Verify project detection:
   ```bash
   PWD=/your/project bash -c 'source /path/to/common-functions.sh; get_project_id'
   # Should return consistent 16-char hex ID
   ```

3. Check metrics files:
   ```bash
   ls -la ~/.claude/infolead-claude-subscription-router/projects/
   # Should see multiple project IDs, not empty
   ```

---

## Benefits Summary

✅ **Complete State Isolation**
- No more state corruption when switching projects
- Each project has independent session state

✅ **Accurate Metrics**
- Cost tracking per-project
- No mixing of agent usage between projects

✅ **Project-Specific Configuration**
- Override global settings per-project
- Disable router for specific projects

✅ **Concurrent Sessions**
- Work on multiple projects simultaneously
- No race conditions or lock conflicts

✅ **Clean Migration Path**
- Existing users migrate with one command per project
- Old data preserved until verified

✅ **Flexible Installation**
- Works with marketplace or local installs
- No hardcoded paths

---

## API Compatibility

### For Hook Developers

New functions in `common-functions.sh`:

```bash
detect_project_root()       # Returns: /path/to/project or empty
get_project_id()            # Returns: 16-char hex ID
get_project_data_dir(type)  # Returns: ~/.claude/.../projects/{id}/{type}/
is_router_enabled()         # Returns: 0 if enabled, 1 if disabled
load_config_file(filename)  # Returns: path to config (project → global cascade)
```

### For Python Code

Updated `adaptive_orchestrator.py`:

```python
# Old (v1.6.x)
config = load_config()  # Always global

# New (v1.7.0+)
config = load_config()  # Auto-detects project config, cascades to global
config = load_config(enable_project_cascade=False)  # Force global
```

---

## Version History

- **v1.7.0** - Multi-project support (hybrid architecture)
- **v1.6.2** - Clear dependency error messages
- **v1.6.1** - Configuration support
- **v1.6.0** - Adaptive orchestration
- **v1.5.0** - Agent usage tracking
- **v1.4.1** - Mandatory routing directives
- **v1.0.0** - Initial release

---

## Related Documentation

- [ARCHITECTURE.md](Solution/Architecture/architecture.md) - Overall system design
- [HOOKS-WORKAROUND.md](Solution/Implementation/HOOKS-WORKAROUND.md) - Plugin hook bug workaround
- [BACKGROUND-AGENT-WRITE-PERMISSIONS.md](BACKGROUND-AGENT-WRITE-PERMISSIONS.md) - File write permissions
- [README.md](../README.md) - Plugin overview and quick start

---

## Questions?

- GitHub Issues: https://github.com/yannickloth/claude-router-system/issues
- Docs: All docs in `plugins/infolead-claude-subscription-router/docs/`
