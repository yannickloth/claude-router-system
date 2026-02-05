# Metrics Accessibility Analysis

**Problem:** Users who install the plugin via Claude Code's plugin system cannot access the metrics collector CLI tool.

**Date:** 2026-02-04
**Status:** Analysis complete, recommendations provided

---

## Current State

### Plugin Installation Structure

When users install via Claude Code:
```bash
claude-code install yannickloth/claude-router-system/infolead-claude-subscription-router
```

Files are installed to:
```
~/.claude/plugins/cache/yannickloth-claude-router-system/infolead-claude-subscription-router/1.2.0/
├── agents/
├── config/
├── docs/
├── hooks/
├── implementation/
│   ├── metrics_collector.py  # ✅ Available
│   └── [other modules]
├── scripts/
│   └── overnight-executor.sh
├── plugin.json
├── README.md
└── EXAMPLE.claude.md
```

**Good news:** The `implementation/metrics_collector.py` file IS installed with the plugin.

### Current Metrics Collector Interface

The metrics collector at `implementation/metrics_collector.py`:
- Has a complete CLI with `main()` function
- Supports commands: `compute`, `efficiency`, `dashboard`, `report`, `show`, `work`, `cleanup`
- Works as a standalone Python script
- Stores data in `~/.claude/infolead-router/metrics/`
- Does NOT have a shebang (`#!/usr/bin/env python3`)

### Current User Experience Gap

Users must:
1. Find the installation path
2. Run: `python3 ~/.claude/plugins/cache/.../metrics_collector.py compute`
3. Remember this complex path for every invocation

This is discoverable but inconvenient.

---

## Solution Options

### Option 1: Wrapper Script in Plugin (RECOMMENDED)

**Add:** `scripts/metrics` wrapper script

**Pros:**
- Simple, discoverable path
- Users run: `~/.claude/plugins/cache/.../scripts/metrics compute`
- Or even better: Create symlink to `~/.local/bin/claude-metrics`
- Familiar Unix pattern
- Zero dependencies beyond Python

**Cons:**
- Still requires finding plugin installation path (one-time)

**Implementation:**
```bash
#!/bin/bash
# scripts/metrics - Wrapper for metrics collector

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$(readlink -f "$0")")")}"
exec python3 "$PLUGIN_ROOT/implementation/metrics_collector.py" "$@"
```

Users can then add to their shell profile:
```bash
# ~/.bashrc or ~/.zshrc
alias claude-metrics='~/.claude/plugins/cache/yannickloth-claude-router-system/infolead-claude-subscription-router/*/scripts/metrics'
```

Or install system-wide:
```bash
ln -s ~/.claude/plugins/cache/yannickloth-claude-router-system/infolead-claude-subscription-router/*/scripts/metrics \
      ~/.local/bin/claude-metrics
```

### Option 2: Direct Script Execution (ALSO RECOMMENDED)

**Modify:** Add shebang to `implementation/metrics_collector.py`

**Change:**
```python
#!/usr/bin/env python3
"""
Metrics Collector - Track performance across all 8 solutions
...
```

**Make executable:**
```bash
chmod +x implementation/metrics_collector.py
```

**Pros:**
- No wrapper needed
- Direct execution: `./metrics_collector.py compute`
- Standard Python pattern

**Cons:**
- Still need to find/remember path

**Works well with Option 1:** Wrapper can directly execute the script.

### Option 3: Installation Script (ENHANCED ONBOARDING)

**Add:** `scripts/install-cli-tools.sh`

Creates symlinks for user convenience:

```bash
#!/bin/bash
# scripts/install-cli-tools.sh
# Creates convenient aliases for plugin CLI tools

BIN_DIR="${1:-$HOME/.local/bin}"
PLUGIN_ROOT="$(dirname "$(dirname "$(readlink -f "$0")")")"

mkdir -p "$BIN_DIR"

# Create metrics CLI symlink
ln -sf "$PLUGIN_ROOT/scripts/metrics" "$BIN_DIR/claude-metrics"
echo "✓ Installed: claude-metrics"

# Create overnight executor symlink
ln -sf "$PLUGIN_ROOT/scripts/overnight-executor.sh" "$BIN_DIR/claude-overnight"
echo "✓ Installed: claude-overnight"

echo ""
echo "CLI tools installed to $BIN_DIR"
echo "Ensure $BIN_DIR is in your PATH:"
echo "  export PATH=\"\$PATH:$BIN_DIR\""
```

**User experience:**
```bash
# One-time setup after plugin installation
~/.claude/plugins/cache/.../scripts/install-cli-tools.sh

# Then use anywhere:
claude-metrics efficiency
claude-metrics dashboard
claude-metrics report daily
```

### Option 4: Hook Integration (AUTOMATIC REPORTING)

**Modify:** Add metrics reporting to existing hooks

For example, add to `SessionEnd` hook:
```bash
# hooks/save-session-state.sh (at end)

# Show daily metrics summary if available
if [ -f "$CLAUDE_PLUGIN_ROOT/implementation/metrics_collector.py" ]; then
    python3 "$CLAUDE_PLUGIN_ROOT/implementation/metrics_collector.py" efficiency 2>/dev/null || true
fi
```

**Pros:**
- Passive awareness
- Users see metrics without asking

**Cons:**
- Could be noise in output
- Not interactive access

### Option 5: Claude Agent for Metrics (FUTURE)

**Add:** `.claude-plugin/agents/metrics-reporter.md`

Let users ask Claude to show metrics:
```
User: "Show my routing metrics"
Claude: [spawns metrics-reporter agent]
Agent: [runs metrics_collector.py, formats output]
```

**Pros:**
- Natural language interface
- No CLI knowledge needed
- Can provide analysis and insights

**Cons:**
- More complex implementation
- Requires agent framework

---

## Recommended Approach

**Implement Options 1 + 2 + 3 together:**

1. **Add shebang to `metrics_collector.py`** (Option 2)
   - Makes it directly executable
   - Standard Python practice

2. **Create `scripts/metrics` wrapper** (Option 1)
   - Provides clean entry point
   - Sets up environment correctly

3. **Create `scripts/install-cli-tools.sh`** (Option 3)
   - One-time setup convenience
   - Creates `claude-metrics` command

4. **Update README with installation instructions**
   - Document the installation process
   - Show example commands

**Result:**
- Discoverable: Files are in plugin directory
- Convenient: One-time setup creates `claude-metrics` command
- Progressive: Works at 3 levels (direct Python, wrapper, installed command)

---

## Implementation Checklist

### Phase 1: Make Executable (5 minutes)

- [x] Add shebang to `implementation/metrics_collector.py`
- [x] Make file executable: `chmod +x implementation/metrics_collector.py`
- [x] Test direct execution: `./metrics_collector.py --test`

### Phase 2: Wrapper Script (10 minutes)

- [ ] Create `scripts/metrics` wrapper
- [ ] Make wrapper executable
- [ ] Test wrapper: `scripts/metrics efficiency`

### Phase 3: Installation Helper (15 minutes)

- [ ] Create `scripts/install-cli-tools.sh`
- [ ] Test installation script
- [ ] Verify `claude-metrics` works after install

### Phase 4: Documentation (20 minutes)

- [ ] Update `README.md` with "CLI Tools" section
- [ ] Add installation instructions
- [ ] Document all metrics commands
- [ ] Add troubleshooting section

### Phase 5: Optional Enhancements (30 minutes)

- [ ] Add `SessionEnd` hook for passive metrics (Option 4)
- [ ] Plan future agent integration (Option 5)
- [ ] Add bash completion script

---

## Example Documentation (for README)

```markdown
## CLI Tools

The plugin includes several command-line tools for monitoring and management.

### Installation

**One-time setup:**
```bash
# Find your plugin installation
PLUGIN_PATH=~/.claude/plugins/cache/yannickloth-claude-router-system/infolead-claude-subscription-router/*/

# Install CLI tools to ~/.local/bin
$PLUGIN_PATH/scripts/install-cli-tools.sh

# Ensure ~/.local/bin is in PATH
export PATH="$PATH:$HOME/.local/bin"
```

### Metrics Collector

Track routing efficiency and cost savings:

```bash
# Compute all solution metrics
claude-metrics compute

# Show routing efficiency
claude-metrics efficiency

# Daily report
claude-metrics report daily

# Weekly report
claude-metrics report weekly

# Live dashboard
claude-metrics dashboard

# Show specific solution
claude-metrics show haiku_routing

# Run tests
claude-metrics --test
```

### Overnight Executor

For scheduled async work (set up via cron):

```bash
# Run manually
claude-overnight

# Or schedule via cron
crontab -e
# Add: 0 22 * * * claude-overnight
```

### Direct Access (without installation)

You can also run tools directly:

```bash
# Metrics
python3 ~/.claude/plugins/cache/.../implementation/metrics_collector.py efficiency

# Or if executable
~/.claude/plugins/cache/.../implementation/metrics_collector.py efficiency
```
```

---

## Migration Path

### For Current Users (Dev with Source)

No change needed. Continue using:
```bash
cd implementation/
python3 metrics_collector.py compute
```

Or upgrade to installed version:
```bash
scripts/install-cli-tools.sh
claude-metrics compute  # New way
```

### For New Users (Plugin Install)

Guided setup in README:
```bash
# After: claude-code install yannickloth/claude-router-system/...
# Run:
~/.claude/plugins/cache/.../scripts/install-cli-tools.sh
```

---

## Alternative Considerations

### Why Not a Dedicated Package?

**Considered:** Publishing `claude-router-metrics` to PyPI

**Rejected because:**
- Adds dependency management
- Requires separate installation step
- Plugin already includes the code
- Would need version sync between package and plugin

### Why Not /metrics Skill?

**Skills** in Claude Code are slash commands (like `/help`). They're defined in plugin.json.

**Considered:** Adding `/metrics` skill

**Rejected because:**
- Skills are for interactive Claude features
- Metrics are better suited for standalone CLI
- Would couple metrics reporting to active Claude sessions
- CLI allows cron jobs, scripts, external monitoring

**Could add later** as complementary interface (Option 5 above).

---

## Cost-Benefit Analysis

### Option 1+2+3 (Recommended)

**Cost:**
- 2 new files (metrics wrapper, install script)
- 1 line change (shebang)
- 30 minutes implementation
- 20 minutes documentation

**Benefit:**
- Professional user experience
- Discoverable and convenient
- Works for all installation methods
- No external dependencies
- Enables automation (cron, scripts)

### Do Nothing

**Cost:**
- Zero implementation time

**Benefit:**
- Zero benefit
- Users find metrics_collector.py unusable
- Metrics feature goes unused
- No feedback on router performance

**Verdict:** Options 1+2+3 are well worth the minimal implementation cost.

---

## Next Steps

1. Review this analysis
2. Approve approach (Options 1+2+3)
3. Implement changes (see checklist above)
4. Test with fresh plugin installation
5. Update README
6. Tag new version (1.3.0?)

---

## Files to Create/Modify

### New Files
- `scripts/metrics` (wrapper)
- `scripts/install-cli-tools.sh` (installer)

### Modified Files
- `implementation/metrics_collector.py` (add shebang)
- `README.md` (document CLI tools)
- `plugin.json` (bump version to 1.3.0)

### Testing
- Test direct Python execution
- Test wrapper script
- Test installer script
- Test after plugin reinstall
- Verify metrics commands work