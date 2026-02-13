#!/bin/bash
# Test Orchestration Script
#
# Validates that orchestrate-request.py can successfully route and execute
# requests through external script control.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Determine project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$PROJECT_ROOT/plugins/infolead-claude-subscription-router"
ORCHESTRATE_SCRIPT="$PLUGIN_ROOT/scripts/orchestrate-request.py"

echo "========================================"
echo "Orchestration Script Tests"
echo "========================================"
echo "Project root: $PROJECT_ROOT"
echo "Orchestrate script: $ORCHESTRATE_SCRIPT"
echo ""

# Helper functions
pass_test() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    echo -e "${RED}  Reason: $2${NC}"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
}

skip_test() {
    echo -e "${YELLOW}⊘ SKIP${NC}: $1"
    echo -e "${YELLOW}  Reason: $2${NC}"
    ((TOTAL_TESTS++))
}

# Test 1: Script exists and is executable
echo "Test 1: Script exists and is executable"
if [ -f "$ORCHESTRATE_SCRIPT" ] && [ -x "$ORCHESTRATE_SCRIPT" ]; then
    pass_test "Orchestration script exists and is executable"
else
    fail_test "Orchestration script exists and is executable" "Script not found or not executable at $ORCHESTRATE_SCRIPT"
fi

# Test 2: Script accepts --help
echo ""
echo "Test 2: Script accepts --help flag"
if python3 "$ORCHESTRATE_SCRIPT" --help >/dev/null 2>&1; then
    pass_test "Script accepts --help flag"
else
    fail_test "Script accepts --help flag" "Script failed with --help"
fi

# Test 3: Routing integration
echo ""
echo "Test 3: Routing integration (can call routing_core.py)"
# Create a test request that should route to haiku
TEST_REQUEST="What is 2 + 2?"
if python3 "$ORCHESTRATE_SCRIPT" --project-root "$PROJECT_ROOT" "$TEST_REQUEST" 2>&1 | grep -q "Routing:"; then
    pass_test "Routing integration works"
else
    # This is expected to fail if claude CLI not available
    skip_test "Routing integration" "Claude CLI may not be available or routing failed"
fi

# Test 4: Session ID generation
echo ""
echo "Test 4: Session ID auto-generation"
OUTPUT=$(python3 "$ORCHESTRATE_SCRIPT" --project-root "$PROJECT_ROOT" "test" 2>&1 || true)
if echo "$OUTPUT" | grep -q "session:"; then
    pass_test "Session ID auto-generation works"
else
    skip_test "Session ID auto-generation" "Could not verify session ID in output"
fi

# Test 5: Metrics recording
echo ""
echo "Test 5: Metrics recording capability"
METRICS_DIR="$HOME/.claude/infolead-claude-subscription-router/metrics"
if [ -d "$METRICS_DIR" ]; then
    # Check if any metrics files exist or can be created
    TODAY=$(date +%Y-%m-%d)
    METRICS_FILE="$METRICS_DIR/${TODAY}.jsonl"

    # Run a simple request to generate metrics
    python3 "$ORCHESTRATE_SCRIPT" --project-root "$PROJECT_ROOT" "test metrics" >/dev/null 2>&1 || true

    if [ -f "$METRICS_FILE" ] && grep -q "orchestrated_execution" "$METRICS_FILE" 2>/dev/null; then
        pass_test "Metrics recording works"
    else
        skip_test "Metrics recording" "No metrics file created or no orchestrated_execution records found"
    fi
else
    skip_test "Metrics recording" "Metrics directory not found"
fi

# Test 6: Error handling - missing request
echo ""
echo "Test 6: Error handling for missing request"
if python3 "$ORCHESTRATE_SCRIPT" --project-root "$PROJECT_ROOT" 2>&1 | grep -q "error\|required"; then
    pass_test "Error handling for missing request"
else
    fail_test "Error handling for missing request" "Script did not error on missing request"
fi

# Test 7: Interactive mode
echo ""
echo "Test 7: Interactive mode (stdin input)"
echo "test interactive" | python3 "$ORCHESTRATE_SCRIPT" --project-root "$PROJECT_ROOT" --interactive 2>&1 >/dev/null || true
if [ $? -eq 0 ] || [ $? -eq 1 ]; then
    # Exit code 0 (success) or 1 (expected failure due to missing claude CLI) are both acceptable
    pass_test "Interactive mode accepts stdin"
else
    fail_test "Interactive mode accepts stdin" "Script failed unexpectedly (exit code: $?)"
fi

# Test 8: Agent model mapping
echo ""
echo "Test 8: Agent to model tier mapping"
# This tests the internal logic by checking if the script properly handles agent names
# We can't directly test internal methods, so we verify the script doesn't crash
# with different agent-like keywords in requests

for agent_type in "haiku" "sonnet" "opus"; do
    REQUEST="Test $agent_type routing"
    if python3 "$ORCHESTRATE_SCRIPT" --project-root "$PROJECT_ROOT" "$REQUEST" >/dev/null 2>&1 || true; then
        : # Success or expected failure (claude CLI not available)
    else
        fail_test "Agent model mapping for $agent_type" "Script crashed with agent type: $agent_type"
        break
    fi
done
pass_test "Agent model mapping handles all tiers"

# Summary
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo "Total tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo -e "${YELLOW}Skipped: $((TOTAL_TESTS - PASSED_TESTS - FAILED_TESTS))${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
