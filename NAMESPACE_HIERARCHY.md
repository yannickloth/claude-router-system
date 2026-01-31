# Hierarchical Namespace: `~/.claude/infolead-router/`

**Date:** 2026-01-31
**Status:** ✅ Final
**Design:** Single top-level namespace directory

---

## Final Directory Structure

### Complete Hierarchy

```
~/.claude/
├── infolead-router/                    # Single namespace root
│   ├── state/                          # Persistent state
│   │   └── work-queue.json
│   ├── logs/                           # Log files
│   │   └── haiku-routing-decisions.log
│   ├── cache/                          # Semantic cache
│   │   └── cache_index.json
│   ├── memory/                         # Cross-session memory
│   │   └── active-context.json
│   ├── rules/                          # Domain-specific rules
│   │   └── latex-research.yaml
│   └── domains/                        # Domain configurations
│       └── config files
└── agents/
    └── infolead-router/                # Router-specific agents
        ├── haiku-pre-router.md
        ├── work-coordinator.md
        └── ...
```

### Comparison: Before vs After

#### Before (Flat Namespace)
```
~/.claude/
├── infolead-router-state/
├── infolead-router-logs/
├── infolead-router-cache/
├── infolead-router-memory/
├── infolead-router-rules/
└── infolead-router-domains/
```

#### After (Hierarchical Namespace)
```
~/.claude/
└── infolead-router/              # Single directory
    ├── state/
    ├── logs/
    ├── cache/
    ├── memory/
    ├── rules/
    └── domains/
```

---

## Setup

### One-Line Setup

```bash
mkdir -p ~/.claude/infolead-router/{state,logs,cache,memory,rules,domains} && chmod 700 ~/.claude/infolead-router/{state,cache,memory,rules,domains} && chmod 755 ~/.claude/infolead-router/logs
```

### Detailed Setup

```bash
# Create parent directory
mkdir -p ~/.claude/infolead-router

# Create subdirectories
mkdir -p ~/.claude/infolead-router/state
mkdir -p ~/.claude/infolead-router/logs
mkdir -p ~/.claude/infolead-router/cache
mkdir -p ~/.claude/infolead-router/memory
mkdir -p ~/.claude/infolead-router/rules
mkdir -p ~/.claude/infolead-router/domains

# Set secure permissions
chmod 700 ~/.claude/infolead-router           # Router root
chmod 700 ~/.claude/infolead-router/state     # State (private)
chmod 755 ~/.claude/infolead-router/logs      # Logs (readable)
chmod 700 ~/.claude/infolead-router/cache     # Cache (private)
chmod 700 ~/.claude/infolead-router/memory    # Memory (private)
chmod 700 ~/.claude/infolead-router/rules     # Rules (private)
chmod 700 ~/.claude/infolead-router/domains   # Domains (private)
```

### Agent Namespace Setup

```bash
# Create router agent directory
mkdir -p ~/.claude/agents/infolead-router
chmod 755 ~/.claude/agents/infolead-router

# Note: Individual agent files can be created as needed
# Example: ~/.claude/agents/infolead-router/haiku-pre-router.md
```

---

## Advantages

### 1. Single Namespace Root

**Before:** 6 top-level directories
```bash
ls ~/.claude/ | grep infolead
infolead-router-cache
infolead-router-domains
infolead-router-logs
infolead-router-memory
infolead-router-rules
infolead-router-state
```

**After:** 1 top-level directory
```bash
ls ~/.claude/ | grep infolead
infolead-router
```

### 2. Cleaner Management

```bash
# Backup entire router system
tar -czf router-backup.tar.gz ~/.claude/infolead-router

# Delete entire router system
rm -rf ~/.claude/infolead-router

# Check disk usage
du -sh ~/.claude/infolead-router
```

### 3. Clear Organization

```bash
# All router files in one place
tree ~/.claude/infolead-router
~/.claude/infolead-router
├── state/
│   └── work-queue.json
├── logs/
│   └── haiku-routing-decisions.log
├── cache/
│   └── cache_index.json
├── memory/
│   └── active-context.json
├── rules/
│   └── latex-research.yaml
└── domains/
```

### 4. Standard Compliance

Agents still follow standard Claude Code structure:
```
~/.claude/agents/
├── standard-agent/               # Standard agents
├── another-agent/
└── infolead-router/              # Router agents (namespaced)
    ├── haiku-pre-router.md
    └── work-coordinator.md
```

---

## Path Reference

| Resource | Path |
|----------|------|
| Router root | `~/.claude/infolead-router/` |
| Work queue | `~/.claude/infolead-router/state/work-queue.json` |
| Routing log | `~/.claude/infolead-router/logs/haiku-routing-decisions.log` |
| Cache index | `~/.claude/infolead-router/cache/cache_index.json` |
| Active context | `~/.claude/infolead-router/memory/active-context.json` |
| LaTeX rules | `~/.claude/infolead-router/rules/latex-research.yaml` |
| Domain configs | `~/.claude/infolead-router/domains/` |
| Router agents | `~/.claude/agents/infolead-router/` |

---

## Implementation Paths

### work_coordinator.py

```python
# Default state file
state_file = Path.home() / ".claude" / "infolead-router" / "state" / "work-queue.json"
```

### semantic_cache.py

```python
# Default cache directory
cache_dir = Path.home() / ".claude" / "infolead-router" / "cache"
```

---

## Migration

### From Flat Namespace

If migrating from flat `infolead-router-*` structure:

```bash
cd ~/.claude

# Create new hierarchy
mkdir -p infolead-router/{state,logs,cache,memory,rules,domains}

# Migrate data
[ -d infolead-router-state ] && mv infolead-router-state/* infolead-router/state/ 2>/dev/null
[ -d infolead-router-logs ] && mv infolead-router-logs/* infolead-router/logs/ 2>/dev/null
[ -d infolead-router-cache ] && mv infolead-router-cache/* infolead-router/cache/ 2>/dev/null
[ -d infolead-router-memory ] && mv infolead-router-memory/* infolead-router/memory/ 2>/dev/null
[ -d infolead-router-rules ] && mv infolead-router-rules/* infolead-router/rules/ 2>/dev/null
[ -d infolead-router-domains ] && mv infolead-router-domains/* infolead-router/domains/ 2>/dev/null

# Remove old directories (after verifying migration)
rmdir infolead-router-state infolead-router-logs infolead-router-cache infolead-router-memory infolead-router-rules infolead-router-domains 2>/dev/null

# Set permissions
chmod 700 infolead-router/{state,cache,memory,rules,domains}
chmod 755 infolead-router/logs
```

### From /tmp/ Paths

If migrating from old `/tmp/` paths:

```bash
# Copy any existing data
[ -f /tmp/work-queue.json ] && cp /tmp/work-queue.json ~/.claude/infolead-router/state/
[ -f /tmp/haiku-routing-decisions.log ] && cp /tmp/haiku-routing-decisions.log ~/.claude/infolead-router/logs/
```

---

## Verification

### Check Structure

```bash
# Verify directory exists
ls -ld ~/.claude/infolead-router

# Check subdirectories
tree ~/.claude/infolead-router

# Check permissions
ls -la ~/.claude/infolead-router/
```

### Test Implementation

```python
from pathlib import Path
from work_coordinator import WorkCoordinator
from semantic_cache import SemanticCache

# Test work coordinator
coord = WorkCoordinator()
print(f"State file: {coord.state_file}")
assert "infolead-router/state" in str(coord.state_file)

# Test semantic cache
cache = SemanticCache(Path.home() / ".claude" / "infolead-router" / "cache")
print(f"Cache dir: {cache.cache_dir}")
assert "infolead-router/cache" in str(cache.cache_dir)

print("✅ All paths use hierarchical structure")
```

---

## Future Extensions

### Adding New Subsystems

```bash
# Future infolead subsystems follow same pattern
~/.claude/
├── infolead-router/          # Router system
├── infolead-agents/          # Future: Agent management system
└── infolead-workflows/       # Future: Workflow system
```

### Adding New Resources

```bash
# Add new resource to router
mkdir -p ~/.claude/infolead-router/metrics
chmod 700 ~/.claude/infolead-router/metrics
```

---

## Benefits Summary

| Benefit | Before | After |
|---------|--------|-------|
| Top-level directories | 6 | 1 |
| Backup command | 6 tar commands | 1 tar command |
| Delete command | 6 rm commands | 1 rm command |
| Permission management | 6 chmod commands | 1 chmod (parent) + children |
| Clarity | Flat list | Clear hierarchy |

---

## Rationale

### Why Hierarchical?

1. **Single point of management**: One directory to backup/restore/delete
2. **Clear ownership**: `~/.claude/infolead-router/` obviously belongs to router
3. **Cleaner namespace**: Reduces clutter in `~/.claude/`
4. **Standard practice**: Matches common filesystem organization patterns
5. **Future-proof**: Easy to add new router resources under same parent

### Why Not Flat?

Flat structure (`infolead-router-state/`, `infolead-router-logs/`, etc.):
- ❌ Clutters `~/.claude/` directory
- ❌ Harder to manage as single unit
- ❌ More verbose paths
- ❌ No clear grouping

Hierarchical structure (`infolead-router/{state,logs,cache,...}`):
- ✅ Clean `~/.claude/` directory
- ✅ Single directory to manage
- ✅ Shorter, clearer paths
- ✅ Natural grouping

---

## Status

- ✅ All implementation files updated
- ✅ All documentation updated
- ✅ Tests still passing (paths are parameterized)
- ✅ Migration guides complete
- ✅ No conflicts with standard Claude Code
- ✅ Hierarchical structure implemented

**Design:** Final - Single namespace root `~/.claude/infolead-router/`

---

**Created:** 2026-01-31
**Last Updated:** 2026-01-31
**Status:** Production-ready
