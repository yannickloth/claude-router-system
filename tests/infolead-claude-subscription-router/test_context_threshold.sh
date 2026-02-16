#!/bin/bash
# Test suite for context threshold monitoring hook
#
# Tests:
# 1. Hook script exists and is executable
# 2. Hook script has valid bash syntax
# 3. Hook is registered in plugin.json
# 4. Load session state hook clears session flags

set -euo pipefail

TEST_DIR="$(dirname "$0")"
PLUGIN_ROOT="$(cd "$TEST_DIR/../../plugins/infolead-claude-subscription-router" && pwd)"
HOOK_SCRIPT="$PLUGIN_ROOT/hooks/check-context-threshold.sh"
LOAD_SESSION_SCRIPT="$PLUGIN_ROOT/hooks/load-session-state.sh"
PLUGIN_JSON="$PLUGIN_ROOT/plugin.json"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    echo "✓ PASS"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo "✗ FAIL"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

echo "Context Threshold Hook Test Suite"
echo "=================================="
echo ""

# Test 1: Hook script exists and is executable
echo -n "Testing: Hook script exists and executable ... "
if [ -f "$HOOK_SCRIPT" ] && [ -x "$HOOK_SCRIPT" ]; then
    pass
else
    fail
fi

# Test 2: Hook script has valid bash syntax
echo -n "Testing: Hook has valid bash syntax ... "
if bash -n "$HOOK_SCRIPT" 2>/dev/null; then
    pass
else
    fail
fi

# Test 3: Hook is registered in plugin.json under UserPromptSubmit
echo -n "Testing: Hook registered in plugin.json ... "
if jq -e '.hooks.UserPromptSubmit[]?.hooks[]? | select(.command | contains("check-context-threshold.sh"))' "$PLUGIN_JSON" >/dev/null 2>&1; then
    pass
elif ! command -v jq &>/dev/null; then
    echo "(jq not available, skipping)"
    pass
else
    fail
fi

# Test 4: Load session state clears session flags
echo -n "Testing: Session flags cleared on load ... "
if grep -q "session-flags.json" "$LOAD_SESSION_SCRIPT" && grep -q "rm -f" "$LOAD_SESSION_SCRIPT"; then
    pass
else
    fail
fi

# Test 5: Hook has proper error handling
echo -n "Testing: Hook has proper error handling ... "
if grep -q "set -euo pipefail" "$HOOK_SCRIPT"; then
    pass
else
    fail
fi

# Test 6: Hook sources hook-preamble.sh
echo -n "Testing: Hook sources preamble ... "
if grep -q "source.*hook-preamble.sh" "$HOOK_SCRIPT"; then
    pass
else
    fail
fi

# Test 7: Hook checks for jq dependency
echo -n "Testing: Hook checks jq dependency ... "
if grep -q "check_jq" "$HOOK_SCRIPT"; then
    pass
else
    fail
fi

# Test 8: Hook uses project-specific state directory
echo -n "Testing: Hook uses project state dir ... "
if grep -q "get_project_data_dir" "$HOOK_SCRIPT"; then
    pass
else
    fail
fi

# Test 9: Hook defines threshold constants
echo -n "Testing: Hook defines thresholds ... "
if grep -q "CONTEXT_LIMIT=" "$HOOK_SCRIPT" && grep -q "THRESHOLD_PERCENT=" "$HOOK_SCRIPT"; then
    pass
else
    fail
fi

# Test 10: Hook warns only once logic present
echo -n "Testing: Hook warn-once logic present ... "
if grep -q "context_threshold_warned" "$HOOK_SCRIPT"; then
    pass
else
    fail
fi

echo ""
echo "=================================="
echo "Results: $TESTS_PASSED passed, $TESTS_FAILED failed"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo "✓ All tests passed"
    exit 0
else
    echo "✗ Some tests failed"
    exit 1
fi
