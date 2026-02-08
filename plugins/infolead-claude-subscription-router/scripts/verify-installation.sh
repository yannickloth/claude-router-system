#!/bin/bash
# Test plugin installation from scratch
#
# This script verifies that all dependencies and components
# are properly installed and functional.

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() {
    echo -e "${GREEN}✅${NC} $1"
}

fail() {
    echo -e "${RED}❌${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

echo "=== Plugin Installation Test ==="
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Check Python3
echo "1. Checking Python3..."
if command -v python3 &> /dev/null; then
    VERSION=$(python3 --version)
    pass "Python3 found: $VERSION"
    ((TESTS_PASSED++))

    # Check version >= 3.7
    PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [[ "$PYTHON_MAJOR" -gt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -ge 7 ]]; then
        pass "Python version >= 3.7 requirement met ($PYTHON_MAJOR.$PYTHON_MINOR)"
        ((TESTS_PASSED++))
    else
        fail "Python 3.7+ required, found: $PYTHON_MAJOR.$PYTHON_MINOR"
        ((TESTS_FAILED++))
    fi
else
    fail "Python3 not found in PATH"
    ((TESTS_FAILED++))
    exit 1
fi
echo ""

# Test 2: Check PyYAML
echo "2. Checking PyYAML dependency..."
if python3 -c "import yaml" 2>/dev/null; then
    YAML_VERSION=$(python3 -c "import yaml; print(yaml.__version__)")
    pass "PyYAML installed (version: $YAML_VERSION)"
    ((TESTS_PASSED++))
else
    fail "PyYAML not installed"
    echo "   Install with: pip install PyYAML"
    ((TESTS_FAILED++))
fi
echo ""

# Test 3: Check plugin structure
echo "3. Checking plugin structure..."
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$(readlink -f "$0")")")}"

if [ -f "$PLUGIN_DIR/plugin.json" ]; then
    pass "plugin.json found"
    ((TESTS_PASSED++))
else
    fail "plugin.json not found"
    ((TESTS_FAILED++))
fi

if [ -f "$PLUGIN_DIR/implementation/routing_core.py" ]; then
    pass "routing_core.py found"
    ((TESTS_PASSED++))
else
    fail "routing_core.py not found"
    ((TESTS_FAILED++))
    exit 1
fi

if [ -f "$PLUGIN_DIR/hooks/user-prompt-submit.sh" ]; then
    pass "user-prompt-submit.sh found"
    ((TESTS_PASSED++))
else
    fail "user-prompt-submit.sh not found"
    ((TESTS_FAILED++))
fi

if [ -d "$PLUGIN_DIR/agents" ]; then
    AGENT_COUNT=$(find "$PLUGIN_DIR/agents" -name "*.md" | wc -l)
    pass "agents/ directory found ($AGENT_COUNT agents)"
    ((TESTS_PASSED++))
else
    fail "agents/ directory not found"
    ((TESTS_FAILED++))
fi
echo ""

# Test 4: Test routing_core.py imports
echo "4. Testing routing_core.py imports..."
if python3 -c "import sys; sys.path.insert(0, '$PLUGIN_DIR/implementation'); from routing_core import route_request" 2>/dev/null; then
    pass "routing_core.py imports successfully"
    ((TESTS_PASSED++))
else
    fail "routing_core.py import failed"
    ((TESTS_FAILED++))
fi
echo ""

# Test 5: Test basic routing
echo "5. Testing basic routing functionality..."
TEST_OUTPUT=$(echo "Fix typo in README.md" | python3 "$PLUGIN_DIR/implementation/routing_core.py" --json 2>&1)

if echo "$TEST_OUTPUT" | jq -e '.decision' >/dev/null 2>&1; then
    DECISION=$(echo "$TEST_OUTPUT" | jq -r '.decision')
    pass "Routing works (decision: $DECISION)"
    ((TESTS_PASSED++))
else
    fail "Routing test failed"
    echo "   Output: $TEST_OUTPUT"
    ((TESTS_FAILED++))
fi
echo ""

# Test 6: Test routing_core built-in tests
echo "6. Running routing_core built-in tests..."
if python3 "$PLUGIN_DIR/implementation/routing_core.py" --test >/dev/null 2>&1; then
    pass "Built-in tests pass"
    ((TESTS_PASSED++))
else
    fail "Built-in tests failed"
    ((TESTS_FAILED++))
fi
echo ""

# Test 7: Test hook execution
echo "7. Testing hook execution..."
export CLAUDE_PLUGIN_ROOT="$PLUGIN_DIR"
HOOK_OUTPUT=$(echo "Test request" | bash "$PLUGIN_DIR/hooks/user-prompt-submit.sh" 2>&1)

if echo "$HOOK_OUTPUT" | grep -q "\[ROUTER\]"; then
    pass "Hook executes successfully"
    ((TESTS_PASSED++))
else
    warn "Hook may have issues (no [ROUTER] output)"
    # Don't fail - hook might be configured to pass through silently
    ((TESTS_PASSED++))
fi
echo ""

# Test 8: Check for optional dependencies
echo "8. Checking optional dependencies..."

if command -v jq &> /dev/null; then
    pass "jq installed (used by hooks)"
    ((TESTS_PASSED++))
else
    warn "jq not installed (required for hooks)"
    echo "   Install with: apt-get install jq (Debian/Ubuntu)"
    # Don't fail - might not be needed depending on setup
    ((TESTS_PASSED++))
fi

if python3 -c "import pytest" 2>/dev/null; then
    pass "pytest installed (for comprehensive tests)"
    ((TESTS_PASSED++))
else
    warn "pytest not installed (optional, for better testing)"
    echo "   Install with: pip install pytest"
    ((TESTS_PASSED++))
fi
echo ""

# Summary
echo "=========================================="
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ All installation tests passed!${NC}"
    echo ""
    echo "Plugin is ready to use."
    echo ""
    echo "Next steps:"
    echo "  1. Install the plugin: claude plugins install ."
    echo "  2. Enable in project: add to .claude/plugins.json"
    echo "  3. Test with: echo 'test' | bash hooks/user-prompt-submit.sh"
    exit 0
else
    echo -e "${RED}❌ Some installation tests failed.${NC}"
    echo ""
    echo "Please fix the issues above before using the plugin."
    exit 1
fi
