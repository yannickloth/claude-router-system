# Release v1.7.0 - Multi-Project Support

**Release Date:** 2026-02-14
**Plugin Version:** 1.7.0
**Architecture:** Hybrid (Global Router + Project-Specific State)

---

## 🎉 What's New

### Multi-Project Support

**Finally!** Work on multiple Claude Code projects simultaneously without state corruption.

The router system now uses a **hybrid architecture**:
- ✅ **Global router logic** - One plugin, shared intelligence
- ✅ **Project-specific state** - Complete isolation per project
- ✅ **Project-aware config** - Override global settings per project

---

## ✨ Key Features

### 1. Automatic Project Detection

The router automatically detects which project you're working in:

```bash
cd ~/frontend  # Router uses frontend's state/metrics
cd ~/backend   # Router uses backend's state/metrics (completely isolated!)
```

No configuration needed - it just works!

### 2. Complete State Isolation

**Before v1.7.0:**
```
All projects → Same global state → State corruption ❌
```

**After v1.7.0:**
```
Each project → Isolated state directory → No corruption ✅
```

Storage structure:
```
~/.claude/infolead-claude-subscription-router/projects/
  ├── abc123/  # Project A
  │   ├── state/   # Session state
  │   ├── metrics/ # Cost tracking
  │   └── logs/    # Agent usage
  └── 789def/  # Project B
      ├── state/
      ├── metrics/
      └── logs/
```

### 3. Per-Project Configuration

Override global settings for specific projects:

```yaml
# Global default: ~/.claude/adaptive-orchestration.yaml
force_mode: null

# Speed-critical project: ~/fast-app/.claude/adaptive-orchestration.yaml
force_mode: "single_stage"

# Research project: ~/research/.claude/adaptive-orchestration.yaml
force_mode: "multi_stage"
```

### 4. Per-Project Enable/Disable

Turn off the router for projects that don't need it:

```json
// my-project/.claude/settings.json
{
  "plugins": {
    "router": {
      "enabled": false
    }
  }
}
```

### 5. Race Condition Prevention

File locking ensures safe concurrent access:
- Work on Project A in Terminal 1
- Work on Project B in Terminal 2
- No state corruption, no conflicts ✅

### 6. Accurate Per-Project Metrics

All metrics now include project context:

```json
{
  "project": {
    "id": "abc123def456",
    "root": "/home/user/code/my-project",
    "name": "my-project"
  },
  "agent_type": "router",
  "model_tier": "sonnet"
}
```

Track costs separately for each project! 💰

---

## 🔧 What Was Fixed

### Critical Issues Resolved

1. ✅ **Multi-project state corruption**
   - Before: Switching projects mixed state
   - After: Complete isolation per project

2. ✅ **Race conditions in concurrent sessions**
   - Before: Multiple sessions could corrupt files
   - After: File locking prevents conflicts

3. ✅ **Hardcoded installation paths**
   - Before: systemd only worked from specific directory
   - After: Works from marketplace, local clone, anywhere

4. ✅ **No project-specific configuration**
   - Before: Only global config
   - After: Project → global → defaults cascade

5. ✅ **No way to disable per-project**
   - Before: All-or-nothing globally
   - After: Fine-grained control per project

---

## 📦 Upgrading from v1.6.x

### Simple 3-Step Migration

**1. Update plugin files:**
```bash
cd /path/to/plugin
git pull origin main
```

**2. Run migration for each project:**
```bash
cd ~/your-project-1
/path/to/plugin/scripts/migrate-to-project-isolation.sh

cd ~/your-project-2
/path/to/plugin/scripts/migrate-to-project-isolation.sh

# Repeat for all your projects
```

**3. Verify and clean up:**
```bash
# Test each project
# Once all work correctly, delete old global data:
rm -rf ~/.claude/infolead-claude-subscription-router/{state,metrics,logs}
```

### What the Migration Script Does

✅ Detects your current project
✅ Copies old global state → new project-specific directories
✅ Adds project context to migrated data
✅ Preserves old data (safe to delete after verifying)
✅ Interactive with clear instructions

---

## 📚 Documentation

### New Documentation

- **[MULTI-PROJECT-ARCHITECTURE.md](plugins/infolead-claude-subscription-router/docs/MULTI-PROJECT-ARCHITECTURE.md)**
  - Complete architecture guide
  - Testing scenarios
  - Troubleshooting
  - API reference

- **[MULTI-PROJECT-FIXES-SUMMARY.md](MULTI-PROJECT-FIXES-SUMMARY.md)**
  - Executive summary of all changes
  - Files modified
  - Migration guide

### Updated Documentation

- **[CHANGELOG.md](plugins/infolead-claude-subscription-router/CHANGELOG.md)**
  - Complete v1.7.0 changelog

- **[README.md](plugins/infolead-claude-subscription-router/README.md)**
  - Added multi-project section

---

## 🧪 Testing

### Recommended Test Scenarios

**Scenario 1: Two Projects Simultaneously**
```bash
# Terminal 1
cd ~/frontend && claude-code

# Terminal 2 (at same time!)
cd ~/backend && claude-code

# Expected: Complete isolation, no state mixing ✅
```

**Scenario 2: Rapid Project Switching**
```bash
cd ~/project-a && claude-code  # Work...
cd ~/project-b && claude-code  # Work...
cd ~/project-a && claude-code  # Resumes A's state ✅
```

**Scenario 3: Project-Specific Config**
```bash
# Set up different configs per project
echo 'force_mode: "single_stage"' > ~/fast-app/.claude/adaptive-orchestration.yaml
echo 'force_mode: "multi_stage"' > ~/complex-app/.claude/adaptive-orchestration.yaml

# Verify each uses its own config
```

---

## ⚠️ Known Limitations

### Overnight Execution (Deferred to v1.7.1+)

Multi-project queue support for overnight execution is not yet implemented in v1.7.0.

**Current behavior:**
- Overnight work uses global queue
- No project context preserved

**Workaround:**
- Manually manage separate overnight queues per project

**Future (v1.7.1+):**
- Each project will have isolated overnight queue
- Executor will run tasks in correct project context

---

## 🎯 Benefits Summary

### For Users

✅ **No More State Corruption**
- Work on 5 projects simultaneously
- Each maintains separate work-in-progress

✅ **Accurate Cost Tracking**
- See exactly how much each project costs
- Metrics separated by project

✅ **Project-Specific Customization**
- Different routing strategies per project
- Disable router for projects that don't need it

✅ **Instant Project Switching**
- No manual config changes
- Router auto-detects which project you're in

✅ **Safe Upgrades**
- Migration preserves all data
- Can revert if needed

### For System

✅ **Race Condition Free**
- File locking prevents corruption
- Multiple sessions coexist safely

✅ **Installation Flexibility**
- Works from any location
- No hardcoded paths

✅ **Clean Architecture**
- Hybrid model (global logic + project state)
- Follows IVP design principle

---

## 📊 Files Changed

### Core Changes

- **7 hook files** updated for project isolation
- **1 Python file** updated for project-aware config
- **2 systemd files** updated for flexible paths
- **3 new files** created (migration script, docs, summary)
- **2 metadata files** updated (plugin.json, CHANGELOG.md)

### Lines of Code

- **~400 lines** added to hooks (project detection, isolation)
- **~50 lines** added to Python (config cascade)
- **~200 lines** migration script
- **~1500 lines** documentation

---

## 🚀 What's Next

### v1.7.1+ Roadmap

- **Overnight execution multi-project support**
  - Per-project overnight queues
  - Executor runs tasks in correct project context

- **Cross-project metrics dashboard**
  - Aggregate metrics across all projects
  - Cost comparison between projects

- **Project templates**
  - Starter configs for common project types
  - One-command project setup

---

## 🙏 Feedback

Found a bug? Have a suggestion?

- **Issues:** https://github.com/yannickloth/claude-router-system/issues
- **Docs:** `plugins/infolead-claude-subscription-router/docs/`

---

## 🏁 Bottom Line

**The Claude Router System is now production-ready for multi-project use!**

All critical multi-project issues have been **completely resolved**. You can now:

✅ Work on multiple projects simultaneously
✅ Switch between projects instantly
✅ Track costs accurately per project
✅ Customize routing per project
✅ Upgrade safely from v1.6.x

**Ready to upgrade? Start with the migration script!** 🚀
