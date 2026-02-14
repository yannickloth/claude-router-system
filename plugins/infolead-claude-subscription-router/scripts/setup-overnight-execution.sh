#!/usr/bin/env bash
#
# setup-overnight-execution.sh
#
# One-time setup script for overnight execution system
#
# Installs:
# - Skills (/overnight, /quota) to ~/.claude/skills/
# - Systemd service and timer to ~/.config/systemd/user/
# - Morning briefing hook (via setup-hooks-workaround.sh)
#
# Change Driver: INSTALLATION
# Changes when: Installation process or component paths change

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SKILLS_DIR="$HOME/.claude/skills"
STATE_DIR="$HOME/.claude/infolead-claude-subscription-router/state"
LOGS_DIR="$HOME/.claude/infolead-claude-subscription-router/logs"

echo "═══════════════════════════════════════════════════════════"
echo "Claude Code Overnight Execution - Setup"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "This script will install:"
echo "  • Skills: /overnight, /quota"
echo "  • Systemd timer: claude-overnight-executor.timer"
echo "  • Morning briefing hook: SessionStart"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "Step 1: Creating directories..."
mkdir -p "$SKILLS_DIR" "$SYSTEMD_USER_DIR" "$STATE_DIR" "$LOGS_DIR"
chmod 700 "$STATE_DIR" "$LOGS_DIR"
echo "  ✓ Directories created"

echo ""
echo "Step 2: Installing skills..."
cp "$PLUGIN_ROOT/skills/overnight.md" "$SKILLS_DIR/"
cp "$PLUGIN_ROOT/skills/quota.md" "$SKILLS_DIR/"
echo "  ✓ Skills installed to $SKILLS_DIR"

echo ""
echo "Step 3: Installing systemd service and timer..."
# Replace __PLUGIN_ROOT__ placeholder with actual plugin path
sed "s|__PLUGIN_ROOT__|$PLUGIN_ROOT|g" "$PLUGIN_ROOT/systemd/claude-overnight-executor.service" > "$SYSTEMD_USER_DIR/claude-overnight-executor.service"
cp "$PLUGIN_ROOT/systemd/claude-overnight-executor.timer" "$SYSTEMD_USER_DIR/"
echo "  ✓ Systemd files installed to $SYSTEMD_USER_DIR"
echo "    Plugin root: $PLUGIN_ROOT"

echo ""
echo "Step 4: Reloading systemd user daemon..."
systemctl --user daemon-reload
echo "  ✓ Systemd daemon reloaded"

echo ""
echo "Step 5: Enabling overnight executor timer..."
systemctl --user enable claude-overnight-executor.timer
systemctl --user start claude-overnight-executor.timer
echo "  ✓ Timer enabled and started"

echo ""
echo "Step 6: Installing morning briefing hook..."
# Check if setup-hooks-workaround.sh exists
if [ -f "$PLUGIN_ROOT/scripts/setup-hooks-workaround.sh" ]; then
    echo "  Running setup-hooks-workaround.sh to install morning-briefing hook..."
    "$PLUGIN_ROOT/scripts/setup-hooks-workaround.sh"
    echo "  ✓ Morning briefing hook installed"
else
    echo "  ⚠️  Warning: setup-hooks-workaround.sh not found"
    echo "     You may need to manually register morning-briefing.sh hook"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Installation Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Verify installation
echo "Verification:"
echo ""

if systemctl --user is-enabled claude-overnight-executor.timer &>/dev/null; then
    echo "  ✓ Systemd timer enabled"
else
    echo "  ✗ Systemd timer not enabled"
fi

if systemctl --user is-active claude-overnight-executor.timer &>/dev/null; then
    echo "  ✓ Systemd timer active"
else
    echo "  ✗ Systemd timer not active"
fi

if [ -f "$SKILLS_DIR/overnight.md" ]; then
    echo "  ✓ /overnight skill installed"
else
    echo "  ✗ /overnight skill missing"
fi

if [ -f "$SKILLS_DIR/quota.md" ]; then
    echo "  ✓ /quota skill installed"
else
    echo "  ✗ /quota skill missing"
fi

echo ""
echo "Next overnight execution:"
systemctl --user list-timers claude-overnight-executor.timer | grep claude-overnight || echo "  (Timer information not available)"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Quick Start Guide"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "1. Queue work for overnight:"
echo "   /overnight search for papers on mitochondrial dysfunction"
echo ""
echo "2. Check tonight's schedule:"
echo "   /quota"
echo ""
echo "3. View overnight results (next morning):"
echo "   Claude Code will show morning briefing at session start"
echo ""
echo "4. Manual execution (testing):"
echo "   $PLUGIN_ROOT/scripts/overnight-executor.sh"
echo ""
echo "5. Check logs:"
echo "   tail -f $LOGS_DIR/overnight-executor.log"
echo ""
echo "6. View systemd logs:"
echo "   journalctl --user -u claude-overnight-executor.service"
echo ""
echo "═══════════════════════════════════════════════════════════"
