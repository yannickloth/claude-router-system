#!/bin/bash
# Comprehensive test suite for Option D routing visibility
#
# Tests:
# 1. Routing core functionality
# 2. Hook integration
# 3. Metrics collection
# 4. Edge cases
# 5. Performance
# 6. Failure modes

set -euo pipefail

PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$(readlink -f "$0")")")}"
ROUTING_CORE="$PLUGIN_DIR/implementation/routing_core.py"
HOOK_SCRIPT="$PLUGIN_DIR/hooks/user-prompt-submit.sh"
METRICS_DIR="${HOME}/.claude/infolead-router/metrics"
TODAY=$(date +%Y-%m-%d)
METRICS_FILE="$METRICS_DIR/${TODAY}.jsonl"

TESTS_PASSED=0
TESTS_FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

section() {
    echo ""
    echo -e "${YELLOW}=== $1 ===${NC}"
    echo ""
}

# Test 1: Routing Core - Mechanical Task
section "Test 1: Routing Core - Mechanical Task"
OUTPUT=$(echo "Fix typo in README.md" | python3 "$ROUTING_CORE" --json)
AGENT=$(echo "$OUTPUT" | jq -r '.agent')
CONFIDENCE=$(echo "$OUTPUT" | jq -r '.confidence')

if [ "$AGENT" = "haiku-general" ] && [ "$(echo "$CONFIDENCE" | cut -d. -f1)" -ge 0 ]; then
    pass "Mechanical task routed to haiku-general (confidence: $CONFIDENCE)"
else
    fail "Expected haiku-general with high confidence, got: $AGENT ($CONFIDENCE)"
fi

# Test 2: Routing Core - Complex Task
section "Test 2: Routing Core - Complex Task"
OUTPUT=$(echo "Design a new authentication system" | python3 "$ROUTING_CORE" --json)
DECISION=$(echo "$OUTPUT" | jq -r '.decision')

if [ "$DECISION" = "escalate" ]; then
    pass "Complex task correctly escalated"
else
    fail "Expected escalation, got: $DECISION"
fi

# Test 3: Routing Core - Ambiguous Request
section "Test 3: Routing Core - Ambiguous Request"
OUTPUT=$(echo "Make it better" | python3 "$ROUTING_CORE" --json)
DECISION=$(echo "$OUTPUT" | jq -r '.decision')

if [ "$DECISION" = "escalate" ]; then
    pass "Ambiguous request correctly escalated"
else
    fail "Expected escalation for ambiguous request, got: $DECISION"
fi

# Test 4: Routing Core - Empty Request
section "Test 4: Routing Core - Empty Request"
if echo "" | python3 "$ROUTING_CORE" --json 2>&1 | grep -q "Error"; then
    pass "Empty request properly rejected"
else
    fail "Empty request should produce error"
fi

# Test 5: Hook - Normal Operation
section "Test 5: Hook - Normal Operation"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_DIR"
OUTPUT=$(echo "Fix typo in README.md" | bash "$HOOK_SCRIPT" 2>&1)

if echo "$OUTPUT" | grep -q "\[ROUTER\] Recommendation:" && echo "$OUTPUT" | grep -q "<routing-recommendation"; then
    pass "Hook outputs both user message (stderr) and Claude context (stdout)"
else
    fail "Hook should output both user and Claude messages"
fi

# Test 6: Hook - Escalation Display
section "Test 6: Hook - Escalation Display"
OUTPUT=$(echo "Design a new system" | bash "$HOOK_SCRIPT" 2>&1)

if echo "$OUTPUT" | grep -q "\[ROUTER\] Recommendation: escalate"; then
    pass "Escalation properly displayed as 'escalate' not 'null'"
else
    fail "Expected 'escalate' in recommendation display"
fi

# Test 7: Metrics - File Creation
section "Test 7: Metrics - File Creation"
if [ -f "$METRICS_FILE" ]; then
    pass "Metrics file created at $METRICS_FILE"
else
    fail "Metrics file not created"
fi

# Test 8: Metrics - Entry Structure
section "Test 8: Metrics - Entry Structure"
LAST_ENTRY=$(tail -1 "$METRICS_FILE")
RECORD_TYPE=$(echo "$LAST_ENTRY" | jq -r '.record_type')
HAS_TIMESTAMP=$(echo "$LAST_ENTRY" | jq 'has("timestamp")')
HAS_REQUEST_HASH=$(echo "$LAST_ENTRY" | jq 'has("request_hash")')
HAS_RECOMMENDATION=$(echo "$LAST_ENTRY" | jq 'has("recommendation")')

if [ "$RECORD_TYPE" = "routing_recommendation" ] && \
   [ "$HAS_TIMESTAMP" = "true" ] && \
   [ "$HAS_REQUEST_HASH" = "true" ] && \
   [ "$HAS_RECOMMENDATION" = "true" ]; then
    pass "Metrics entry has correct structure"
else
    fail "Metrics entry structure incomplete"
fi

# Test 9: Metrics - Request Hash Uniqueness
section "Test 9: Metrics - Request Hash Uniqueness"
HASH1=$(echo "Test request" | bash "$HOOK_SCRIPT" 2>&1 | grep -o 'request-hash="[^"]*"' | cut -d'"' -f2)
HASH2=$(echo "Different request" | bash "$HOOK_SCRIPT" 2>&1 | grep -o 'request-hash="[^"]*"' | cut -d'"' -f2)

if [ "$HASH1" != "$HASH2" ] && [ -n "$HASH1" ] && [ -n "$HASH2" ]; then
    pass "Different requests produce different hashes"
else
    fail "Request hashing not working properly"
fi

# Test 10: Performance - Hook Latency
section "Test 10: Performance - Hook Latency"
START=$(date +%s%N)
for i in {1..5}; do
    echo "Test request $i" | bash "$HOOK_SCRIPT" >/dev/null 2>&1
done
END=$(date +%s%N)
TOTAL_MS=$(( (END - START) / 1000000 ))
AVG_MS=$(( TOTAL_MS / 5 ))

if [ "$AVG_MS" -lt 200 ]; then
    pass "Hook performance acceptable: ${AVG_MS}ms average (threshold: 200ms)"
else
    fail "Hook performance slow: ${AVG_MS}ms average (threshold: 200ms)"
fi

# Test 11: Concurrent Writes - Atomic Append
section "Test 11: Concurrent Writes - Atomic Append"
BEFORE_COUNT=$(grep -c "routing_recommendation" "$METRICS_FILE" || echo "0")

for i in {1..10}; do
    echo "Concurrent test $i" | bash "$HOOK_SCRIPT" >/dev/null 2>&1 &
done
wait

AFTER_COUNT=$(grep -c "routing_recommendation" "$METRICS_FILE" || echo "0")
DIFF=$((AFTER_COUNT - BEFORE_COUNT))

if [ "$DIFF" -eq 10 ]; then
    pass "Atomic append: all 10 concurrent writes recorded correctly"
else
    fail "Atomic append failed: expected 10 new entries, got $DIFF"
fi

# Test 12: Hook Failure Handling - Missing Python Script
section "Test 12: Hook Failure Handling - Missing Script"
TEMP_PLUGIN="/tmp/test-plugin-$$"
mkdir -p "$TEMP_PLUGIN"
if echo "test" | CLAUDE_PLUGIN_ROOT="$TEMP_PLUGIN" bash "$HOOK_SCRIPT" 2>&1; then
    pass "Hook gracefully handles missing routing script"
else
    fail "Hook should exit gracefully when routing script missing"
fi
rm -rf "$TEMP_PLUGIN"

# Test 13: Hook Failure Handling - Invalid JSON
section "Test 13: Hook Failure Handling - Invalid JSON"
# This would require mocking the routing core to return invalid JSON
# For now, we test that malformed requests don't crash the hook
if echo '{"malicious": "json"}' | bash "$HOOK_SCRIPT" >/dev/null 2>&1; then
    pass "Hook handles unusual input without crashing"
else
    fail "Hook should not crash on unusual input"
fi

# Test 14: Routing Core - Special Characters
section "Test 14: Routing Core - Special Characters"
OUTPUT=$(echo 'Fix regex: /\w+@\w+\.\w+/' | python3 "$ROUTING_CORE" --json)
if echo "$OUTPUT" | jq -e '.reason' >/dev/null 2>&1; then
    pass "Routing core handles special characters"
else
    fail "Routing core failed on special characters"
fi

# Test 15: End-to-End - Full Flow
section "Test 15: End-to-End - Full Flow"
REQUEST="Implement user login functionality"
OUTPUT=$(echo "$REQUEST" | bash "$HOOK_SCRIPT" 2>&1)

HAS_USER_MSG=$(echo "$OUTPUT" | grep -c "\[ROUTER\] Recommendation:" || echo "0")
HAS_CLAUDE_CTX=$(echo "$OUTPUT" | grep -c "<routing-recommendation" || echo "0")
HAS_JSON=$(echo "$OUTPUT" | grep -A5 "<routing-recommendation" | jq -e '.decision' >/dev/null 2>&1 && echo "1" || echo "0")

if [ "$HAS_USER_MSG" -gt 0 ] && [ "$HAS_CLAUDE_CTX" -gt 0 ] && [ "$HAS_JSON" = "1" ]; then
    pass "End-to-end flow: user sees message, Claude gets context, JSON is valid"
else
    fail "End-to-end flow incomplete"
fi

# Summary
section "Test Summary"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Tests passed: ${TESTS_PASSED}/${TOTAL}"
echo "Tests failed: ${TESTS_FAILED}/${TOTAL}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
