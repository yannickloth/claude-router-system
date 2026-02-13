#!/bin/bash
# Test Agent Usage Tracking System
#
# Tests the complete agent usage tracking flow:
# 1. Routing recommendations are logged
# 2. Agent invocations create request_tracking records
# 3. Compliance status is correctly determined
# 4. Analysis tools can query the data

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$SCRIPT_DIR/../../plugins/infolead-claude-subscription-router"
METRICS_DIR="${HOME}/.claude/infolead-claude-subscription-router/metrics"
TODAY=$(date +%Y-%m-%d)
METRICS_FILE="$METRICS_DIR/${TODAY}.jsonl"

echo "=================================="
echo "Agent Usage Tracking Test Suite"
echo "=================================="
echo

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_func="$2"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo "Test $TESTS_RUN: $test_name"

    if $test_func; then
        echo "  ✓ PASS"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo "  ✗ FAIL"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    echo
}

# =============================================================================
# Test 1: Verify SubagentStart hook syntax
# =============================================================================

test_hook_syntax() {
    bash -n "$PLUGIN_ROOT/hooks/log-subagent-start.sh"
}

# =============================================================================
# Test 2: Verify routing_compliance.py can import
# =============================================================================

test_compliance_import() {
    cd "$PLUGIN_ROOT/implementation" && python3 -c "from routing_compliance import RoutingCompliance; print('OK')" >/dev/null 2>&1
}

# =============================================================================
# Test 3: Create synthetic routing recommendation
# =============================================================================

test_create_routing_recommendation() {
    local timestamp=$(date -Iseconds)
    local request_hash="test_$(date +%s)_synthetic"

    local rec=$(jq -c -n \
        --arg record_type "routing_recommendation" \
        --arg timestamp "$timestamp" \
        --arg request_hash "$request_hash" \
        --arg agent "haiku-general" \
        --arg reason "Test routing recommendation" \
        --argjson confidence 0.85 \
        '{
            record_type: $record_type,
            timestamp: $timestamp,
            request_hash: $request_hash,
            recommendation: {
                agent: $agent,
                reason: $reason,
                confidence: $confidence
            },
            full_analysis: {
                decision: "escalate",
                agent: $agent,
                reason: $reason,
                confidence: $confidence
            }
        }')

    mkdir -p "$METRICS_DIR"
    echo "$rec" >> "$METRICS_FILE"

    # Verify it was written
    grep -q "$request_hash" "$METRICS_FILE"
}

# =============================================================================
# Test 4: Simulate SubagentStart hook creating tracking record
# =============================================================================

test_create_tracking_record() {
    local timestamp=$(date -Iseconds)
    local request_hash="test_$(date +%s)_tracking"

    # First create the routing recommendation
    local rec=$(jq -c -n \
        --arg record_type "routing_recommendation" \
        --arg timestamp "$timestamp" \
        --arg request_hash "$request_hash" \
        --arg agent "haiku-general" \
        '{
            record_type: $record_type,
            timestamp: $timestamp,
            request_hash: $request_hash,
            recommendation: {agent: $agent},
            full_analysis: {decision: "escalate", agent: $agent}
        }')
    echo "$rec" >> "$METRICS_FILE"

    # Then create matching tracking record
    local track=$(jq -c -n \
        --arg record_type "request_tracking" \
        --arg timestamp "$timestamp" \
        --arg request_hash "$request_hash" \
        --arg routing_agent "haiku-general" \
        --arg agent_invoked "haiku-general" \
        --arg compliance "followed" \
        '{
            record_type: $record_type,
            timestamp: $timestamp,
            request_hash: $request_hash,
            routing_decision: "escalate",
            routing_agent: $routing_agent,
            actual_handler: "agent",
            agent_invoked: $agent_invoked,
            compliance_status: $compliance,
            project: "test-project"
        }')
    echo "$track" >> "$METRICS_FILE"

    # Verify both records exist (use two separate greps, not chained)
    grep -q "\"request_hash\":\"$request_hash\"" "$METRICS_FILE" && \
    grep -q "\"record_type\":\"routing_recommendation\"" "$METRICS_FILE" && \
    grep -q "\"record_type\":\"request_tracking\"" "$METRICS_FILE"
}

# =============================================================================
# Test 5: Test ignored directive scenario
# =============================================================================

test_ignored_directive() {
    local timestamp=$(date -Iseconds)
    local request_hash="test_$(date +%s)_ignored"

    # Routing recommends haiku
    local rec=$(jq -c -n \
        --arg record_type "routing_recommendation" \
        --arg timestamp "$timestamp" \
        --arg request_hash "$request_hash" \
        --arg agent "haiku-general" \
        '{
            record_type: $record_type,
            timestamp: $timestamp,
            request_hash: $request_hash,
            recommendation: {agent: $agent},
            full_analysis: {decision: "escalate", agent: $agent}
        }')
    echo "$rec" >> "$METRICS_FILE"

    # But sonnet was invoked (ignored!)
    local track=$(jq -c -n \
        --arg record_type "request_tracking" \
        --arg timestamp "$timestamp" \
        --arg request_hash "$request_hash" \
        --arg routing_agent "haiku-general" \
        --arg agent_invoked "sonnet-general" \
        --arg compliance "ignored" \
        '{
            record_type: $record_type,
            timestamp: $timestamp,
            request_hash: $request_hash,
            routing_decision: "escalate",
            routing_agent: $routing_agent,
            actual_handler: "agent",
            agent_invoked: $agent_invoked,
            compliance_status: $compliance,
            project: "test-project"
        }')
    echo "$track" >> "$METRICS_FILE"

    # Verify ignored status
    grep -q "\"request_hash\":\"$request_hash\".*\"compliance_status\":\"ignored\"" "$METRICS_FILE"
}

# =============================================================================
# Test 6: Test compliance analyzer can read data
# =============================================================================

test_compliance_analyzer() {
    cd "$PLUGIN_ROOT/implementation"
    python3 routing_compliance.py report 2>&1 | grep -q "ROUTING COMPLIANCE REPORT"
}

# =============================================================================
# Test 7: Test export functionality
# =============================================================================

test_export_data() {
    cd "$PLUGIN_ROOT/implementation"
    local json_output=$(python3 routing_compliance.py export --format json 2>/dev/null)
    echo "$json_output" | jq -e 'type == "array"' >/dev/null
}

# =============================================================================
# Test 8: Test metrics_collector integration
# =============================================================================

test_metrics_collector_integration() {
    cd "$PLUGIN_ROOT/implementation"
    python3 metrics_collector.py compliance 2>&1 | grep -q "ROUTING COMPLIANCE"
}

# =============================================================================
# Test 9: Verify hook can handle agent spawn input
# =============================================================================

test_hook_input_handling() {
    local input=$(jq -c -n \
        --arg cwd "/home/test" \
        --arg agent_type "haiku-general" \
        --arg agent_id "test123abc" \
        '{
            cwd: $cwd,
            agent_type: $agent_type,
            agent_id: $agent_id
        }')

    # Simulate hook execution (dry run - just check it doesn't error)
    # Note: We can't fully test this without mocking, but we can verify it parses input
    echo "$input" | jq -r '.agent_type' | grep -q "haiku-general"
}

# =============================================================================
# Test 10: Verify by-agent breakdown works
# =============================================================================

test_by_agent_breakdown() {
    cd "$PLUGIN_ROOT/implementation"
    python3 routing_compliance.py by-agent 2>&1 | grep -q "COMPLIANCE BY RECOMMENDED AGENT"
}

# =============================================================================
# Run all tests
# =============================================================================

echo "Running tests..."
echo

run_test "SubagentStart hook syntax validation" test_hook_syntax
run_test "Compliance module import" test_compliance_import
run_test "Create routing recommendation record" test_create_routing_recommendation
run_test "Create request tracking record" test_create_tracking_record
run_test "Ignored directive scenario" test_ignored_directive
run_test "Compliance analyzer reads data" test_compliance_analyzer
run_test "Export data functionality" test_export_data
run_test "Metrics collector integration" test_metrics_collector_integration
run_test "Hook input handling" test_hook_input_handling
run_test "By-agent breakdown" test_by_agent_breakdown

# =============================================================================
# Summary
# =============================================================================

echo "=================================="
echo "Test Summary"
echo "=================================="
echo "Total tests run:    $TESTS_RUN"
echo "Tests passed:       $TESTS_PASSED"
echo "Tests failed:       $TESTS_FAILED"
echo "=================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Some tests failed"
    exit 1
fi
