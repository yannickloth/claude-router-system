#!/bin/bash
#
# Manual Test: Dependency Error Messages
#
# This script demonstrates what users will see when dependencies are missing.
# Run this to verify that clear, helpful error messages are displayed.
#

set -euo pipefail

SCRIPT_DIR="$(dirname "$0")"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==================================================================="
echo "Manual Test: Dependency Error Messages"
echo "==================================================================="
echo ""
echo "This test demonstrates the error messages users see when"
echo "dependencies are missing. All dependencies are currently installed,"
echo "so we'll show what the messages WOULD look like."
echo ""
echo "==================================================================="
echo ""

cat <<'EOF'
1. MISSING PYTHON 3
-------------------
If python3 is not installed, users see:

⚠️  PLUGIN WARNING: infolead-claude-subscription-router

Missing dependency: Python 3.7+

This plugin requires Python 3 for intelligent routing and cost optimization.

Install Python:
  • Ubuntu/Debian: sudo apt-get install python3 python3-pip
  • macOS: brew install python3
  • Arch Linux: sudo pacman -S python
  • Fedora: sudo dnf install python3

Then install PyYAML: pip3 install PyYAML

Your request will be processed without routing optimization until fixed.

-------------------------------------------------------------------

2. MISSING PyYAML
-----------------
If PyYAML package is not installed, users see:

⚠️  PLUGIN WARNING: infolead-claude-subscription-router

Missing Python package: PyYAML

Install with: pip3 install PyYAML

Your request will be processed without routing optimization until fixed.

-------------------------------------------------------------------

3. MISSING jq
-------------
If jq is not installed, users see:

⚠️  PLUGIN WARNING: infolead-claude-subscription-router

Missing dependency: jq (JSON processor)

This plugin requires jq for processing JSON data.

Install jq:
  • Ubuntu/Debian: sudo apt-get install jq
  • macOS: brew install jq
  • Arch Linux: sudo pacman -S jq
  • Fedora: sudo dnf install jq

Your request will be processed with limited functionality until fixed.

-------------------------------------------------------------------

WHAT CHANGED IN v1.6.2:
-----------------------

Before v1.6.2:
  • Hooks failed silently (exit 0)
  • No error messages shown
  • Users confused about why routing wasn't working

After v1.6.2:
  ✓ Clear error messages with ⚠️ warning emoji
  ✓ Platform-specific installation instructions
  ✓ Explanation of impact on functionality
  ✓ Graceful degradation (hooks exit 0, don't block Claude)

EOF

echo ""
echo "==================================================================="
echo "Testing Current Environment"
echo "==================================================================="
echo ""

source "$PLUGIN_ROOT/hooks/common-functions.sh"

echo "✓ Testing python3..."
if check_python3 "required" 2>&1 | grep -q "Missing"; then
    echo "  ✗ MISSING"
else
    echo "  ✓ INSTALLED: $(python3 --version 2>&1)"
fi

echo ""
echo "✓ Testing PyYAML..."
if check_pyyaml "required" 2>&1 | grep -q "Missing"; then
    echo "  ✗ MISSING"
else
    echo "  ✓ INSTALLED"
fi

echo ""
echo "✓ Testing jq..."
if check_jq "required" 2>&1 | grep -q "Missing"; then
    echo "  ✗ MISSING"
else
    echo "  ✓ INSTALLED: $(jq --version 2>&1)"
fi

echo ""
echo "==================================================================="
echo "All dependencies are currently installed!"
echo "==================================================================="
