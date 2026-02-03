#!/bin/bash
# Test Suite for Claude Router System Hooks
#
# Tests:
# 1. Basic functionality (start/stop logging)
# 2. Concurrent execution (race conditions)
# 3. Edge cases (missing fields, special characters)
# 4. Duration calculation accuracy
# 5. File locking correctness
#
# Usage: ./tests/test_hooks.sh
#
# Change Driver: TESTING_REQUIREMENTS

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Get script directory and plugin root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$TESTS_DIR")"
PLUGIN_ROOT="$PROJECT_ROOT/plugins/infolead-claude-subscription-router"
HOOKS_DIR="$PLUGIN_ROOT/hooks"

# Create temp directory for tests
TEST_DIR=$(mktemp -d)
TEST_LOGS_DIR="$TEST_DIR/.claude/logs"
TEST_METRICS_DIR="$TEST_DIR/.claude/metrics"
mkdir -p "$TEST_LOGS_DIR" "$TEST_METRICS_DIR"

# Override HOME for metrics file isolation
export HOME="$TEST_DIR"
mkdir -p "$HOME/.claude/infolead-router/metrics"

# Cleanup on exit (invoked via trap)
# shellcheck disable=SC2317,SC2329
cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Test helper functions
log_test() {
    echo -e "${YELLOW}TEST:${NC} $1"
}

pass() {
    echo -e "${GREEN}PASS:${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
}

fail() {
    echo -e "${RED}FAIL:${NC} $1"
    echo -e "${RED}      ${NC} $2"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
}

# Generate test JSON for SubagentStart
make_start_json() {
    local agent_type="${1:-test-agent}"
    local agent_id="${2:-agent-$(date +%s%N)}"
    local cwd="${3:-$TEST_DIR}"
    jq -n \
        --arg cwd "$cwd" \
        --arg agent_type "$agent_type" \
        --arg agent_id "$agent_id" \
        --arg transcript_path "" \
        '{cwd: $cwd, agent_type: $agent_type, agent_id: $agent_id, transcript_path: $transcript_path}'
}

# Generate test JSON for SubagentStop
make_stop_json() {
    local agent_type="${1:-test-agent}"
    local agent_id="${2:-agent-123}"
    local exit_status="${3:-success}"
    local cwd="${4:-$TEST_DIR}"
    jq -n \
        --arg cwd "$cwd" \
        --arg agent_type "$agent_type" \
        --arg agent_id "$agent_id" \
        --arg exit_status "$exit_status" \
        '{cwd: $cwd, agent_type: $agent_type, agent_id: $agent_id, exit_status: $exit_status}'
}

# ============================================================================
# TEST 1: Basic Start Hook Functionality
# ============================================================================
test_start_basic() {
    log_test "Basic start hook creates log entry"

    local agent_id
    agent_id="basic-test-$(date +%s%N)"
    local short_id="${agent_id:0:8}"  # Hook truncates to 8 chars
    local json
    json=$(make_start_json "haiku-general" "$agent_id")

    echo "$json" | "$HOOKS_DIR/log-subagent-start.sh" 2>/dev/null

    local log_file="$TEST_DIR/.claude/logs/routing.log"
    if [[ -f "$log_file" ]] && grep -q "$short_id" "$log_file"; then
        if grep -q "| START" "$log_file"; then
            pass "Start hook creates log with agent_id and START marker"
        else
            fail "Start hook missing START marker" "$(cat "$log_file")"
        fi
    else
        fail "Start hook did not create log entry" "Log file: $log_file, looking for: $short_id"
    fi
}

# ============================================================================
# TEST 2: Basic Stop Hook Functionality
# ============================================================================
test_stop_basic() {
    log_test "Basic stop hook creates log entry"

    local agent_id
    agent_id="stop-test-$(date +%s%N)"
    local short_id="${agent_id:0:8}"  # Hook truncates to 8 chars

    # First create a start entry
    make_start_json "sonnet-general" "$agent_id" | "$HOOKS_DIR/log-subagent-start.sh" 2>/dev/null

    # Wait a moment for duration calculation
    sleep 1

    # Then create stop entry
    make_stop_json "sonnet-general" "$agent_id" "success" | "$HOOKS_DIR/log-subagent-stop.sh" 2>/dev/null

    local log_file="$TEST_DIR/.claude/logs/routing.log"
    if grep -q "$short_id.*STOP" "$log_file"; then
        pass "Stop hook creates log with agent_id and STOP marker"
    else
        fail "Stop hook missing STOP marker or agent_id" "$(grep "$short_id" "$log_file" || echo 'No matching lines')"
    fi
}

# ============================================================================
# TEST 3: Duration Calculation
# ============================================================================
test_duration_calculation() {
    log_test "Duration calculation between start and stop"

    local agent_id
    agent_id="duration-test-$(date +%s%N)"
    local short_id="${agent_id:0:8}"  # Hook truncates to 8 chars

    # Start
    make_start_json "test-agent" "$agent_id" | "$HOOKS_DIR/log-subagent-start.sh" 2>/dev/null

    # Wait exactly 2 seconds
    sleep 2

    # Stop
    make_stop_json "test-agent" "$agent_id" "success" | "$HOOKS_DIR/log-subagent-stop.sh" 2>/dev/null

    local log_file="$TEST_DIR/.claude/logs/routing.log"
    local stop_line
    stop_line=$(grep "$short_id.*STOP" "$log_file" | tail -1)

    # Extract duration (should be ~2s, allow 1-3s range)
    local duration
    duration=$(echo "$stop_line" | grep -oP '\d+(?=s)' | head -1 || echo "0")

    if [[ "$duration" -ge 1 && "$duration" -le 3 ]]; then
        pass "Duration calculated correctly (~${duration}s, expected ~2s)"
    else
        fail "Duration calculation wrong" "Got ${duration}s, expected ~2s. Line: $stop_line"
    fi
}

# ============================================================================
# TEST 4: Concurrent Execution (Race Conditions)
# ============================================================================
test_concurrent_execution() {
    log_test "Concurrent hook execution (10 parallel agents)"

    # Clear log for this test
    true > "$TEST_DIR/.claude/logs/routing.log"

    # Launch 10 agents concurrently
    local pids=()
    for i in {1..10}; do
        (
            local agent_id="concurrent-$i-$$"
            make_start_json "agent-$i" "$agent_id" | "$HOOKS_DIR/log-subagent-start.sh" 2>/dev/null
            sleep 0.1
            make_stop_json "agent-$i" "$agent_id" "success" | "$HOOKS_DIR/log-subagent-stop.sh" 2>/dev/null
        ) &
        pids+=($!)
    done

    # Wait for all to complete
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done

    local log_file="$TEST_DIR/.claude/logs/routing.log"

    # Count START and STOP entries (use wc -l for cleaner output)
    local start_count
    start_count=$(grep "| START" "$log_file" 2>/dev/null | wc -l | tr -d ' ')
    local stop_count
    stop_count=$(grep "| STOP" "$log_file" 2>/dev/null | wc -l | tr -d ' ')

    # Check for line corruption (lines should have expected field count)
    # grep -cv returns count of NON-matching lines; if all lines match, count is 0
    local corrupt_lines
    corrupt_lines=$(grep -cv "^[0-9]" "$log_file" 2>/dev/null || true)
    corrupt_lines="${corrupt_lines:-0}"
    corrupt_lines="${corrupt_lines//[^0-9]/}"  # Strip any non-numeric chars

    if [[ "$start_count" -eq 10 ]] && [[ "$stop_count" -eq 10 ]] && [[ "$corrupt_lines" -eq 0 ]]; then
        pass "All 10 concurrent agents logged correctly (no race conditions)"
    else
        fail "Concurrent execution issue" "Starts: $start_count, Stops: $stop_count, Corrupt: $corrupt_lines"
    fi
}

# ============================================================================
# TEST 5: Special Characters in Agent ID
# ============================================================================
test_special_characters() {
    log_test "Special characters in agent_id handled correctly"

    # Agent IDs with regex-special characters
    # Note: Hook truncates to 8 chars, so use short IDs to ensure uniqueness
    local special_ids=(
        "ag.dots1"
        "ag*star2"
        "ag[brak3"
        "ag(parn4"
        "ag+plus5"
    )

    local all_passed=true
    for agent_id in "${special_ids[@]}"; do
        make_start_json "test" "$agent_id" | "$HOOKS_DIR/log-subagent-start.sh" 2>/dev/null
        make_stop_json "test" "$agent_id" "success" | "$HOOKS_DIR/log-subagent-stop.sh" 2>/dev/null

        local log_file="$TEST_DIR/.claude/logs/routing.log"
        # Use -F for fixed string match (no regex interpretation)
        if ! grep -F "$agent_id" "$log_file" > /dev/null; then
            all_passed=false
            echo "  Failed for: $agent_id"
        fi
    done

    if $all_passed; then
        pass "Special characters in agent_id handled correctly"
    else
        fail "Some special characters not handled" "See above"
    fi
}

# ============================================================================
# TEST 6: Model Tier Detection
# ============================================================================
test_model_tier_detection() {
    log_test "Model tier detection for cost estimation"

    # Test various agent types
    declare -A agent_tiers=(
        ["haiku-general"]="haiku"
        ["sonnet-general"]="sonnet"
        ["opus-general"]="opus"
        ["router"]="sonnet"
        ["router-escalation"]="opus"
        ["custom-haiku-agent"]="haiku"
        ["my-opus-analyzer"]="opus"
        ["unknown-agent"]="sonnet"
    )

    local all_passed=true
    local today
    today=$(date +%Y-%m-%d)
    local metrics_file="$HOME/.claude/infolead-router/metrics/${today}.jsonl"

    # Clear metrics file for this test
    true > "$metrics_file"

    for agent_type in "${!agent_tiers[@]}"; do
        local expected_tier="${agent_tiers[$agent_type]}"
        local agent_id="tier-test-$agent_type-$$"

        make_stop_json "$agent_type" "$agent_id" "success" | "$HOOKS_DIR/log-subagent-stop.sh" 2>/dev/null

        # Check metrics file for model_tier
        local actual_tier
        actual_tier=$(grep "$agent_id" "$metrics_file" 2>/dev/null | jq -r '.model_tier' 2>/dev/null | tail -1)

        if [[ "$actual_tier" != "$expected_tier" ]]; then
            all_passed=false
            echo "  $agent_type: expected $expected_tier, got $actual_tier"
        fi
    done

    if $all_passed; then
        pass "Model tier detection correct for all agent types"
    else
        fail "Model tier detection errors" "See above"
    fi
}

# ============================================================================
# TEST 7: Metrics JSONL Format
# ============================================================================
test_metrics_format() {
    log_test "Metrics file produces valid JSONL"

    local today
    today=$(date +%Y-%m-%d)
    local metrics_file="$HOME/.claude/infolead-router/metrics/${today}.jsonl"

    # Clear and create fresh metrics file for this test
    true > "$metrics_file"

    local agent_id="metrics-test-$$"
    make_stop_json "test-agent" "$agent_id" "success" | "$HOOKS_DIR/log-subagent-stop.sh" 2>/dev/null

    if [[ -f "$metrics_file" ]]; then
        # Validate each line is valid JSON
        local invalid_lines=0
        while read -r line; do
            if ! jq . <<< "$line" > /dev/null 2>&1; then
                invalid_lines=$((invalid_lines + 1))
            fi
        done < "$metrics_file"

        if [[ "$invalid_lines" -eq 0 ]]; then
            # Check required fields exist
            local last_entry
            last_entry=$(tail -1 "$metrics_file")
            local has_fields
            has_fields=$(jq 'has("event") and has("timestamp") and has("agent_type") and has("model_tier")' <<< "$last_entry")

            if [[ "$has_fields" == "true" ]]; then
                pass "Metrics file is valid JSONL with required fields"
            else
                fail "Metrics missing required fields" "$last_entry"
            fi
        else
            fail "Metrics file has $invalid_lines invalid JSON lines" ""
        fi
    else
        fail "Metrics file not created" "$metrics_file"
    fi
}

# ============================================================================
# TEST 8: Missing/Empty Fields Handling
# ============================================================================
test_missing_fields() {
    log_test "Graceful handling of missing JSON fields"

    # Minimal JSON with missing fields
    local minimal_json='{"cwd": "'"$TEST_DIR"'"}'

    # Should not crash
    if echo "$minimal_json" | "$HOOKS_DIR/log-subagent-start.sh" 2>/dev/null; then
        local log_file="$TEST_DIR/.claude/logs/routing.log"
        if grep -q "unknown" "$log_file"; then
            pass "Missing fields default to 'unknown'"
        else
            pass "Hook handles missing fields gracefully"
        fi
    else
        fail "Hook crashed on missing fields" ""
    fi
}

# ============================================================================
# TEST 9: Lock File Cleanup
# ============================================================================
test_lock_file_cleanup() {
    log_test "Lock files don't accumulate"

    # Run several hooks
    for i in {1..5}; do
        make_start_json "test" "lock-test-$i" | "$HOOKS_DIR/log-subagent-start.sh" 2>/dev/null
    done

    # Count lock files
    local lock_count
    lock_count=$(find "$TEST_DIR" -name "*.lock" 2>/dev/null | wc -l)

    # Lock files should exist (they're used by flock) but shouldn't grow unbounded
    # With flock on a single file, there should be at most 1-2 lock files
    if [[ "$lock_count" -le 3 ]]; then
        pass "Lock files managed correctly ($lock_count files)"
    else
        fail "Too many lock files accumulating" "$lock_count lock files found"
    fi
}

# ============================================================================
# TEST 10: stderr Output Format
# ============================================================================
test_stderr_output() {
    log_test "stderr output has correct format for terminal visibility"

    local agent_id="stderr-test-$$"

    # Capture stderr
    local start_stderr
    start_stderr=$(make_start_json "haiku-general" "$agent_id" | "$HOOKS_DIR/log-subagent-start.sh" 2>&1 >/dev/null)
    local stop_stderr
    stop_stderr=$(make_stop_json "haiku-general" "$agent_id" "success" | "$HOOKS_DIR/log-subagent-stop.sh" 2>&1 >/dev/null)

    if [[ "$start_stderr" == *"[routing]"* && "$start_stderr" == *"→"* ]]; then
        if [[ "$stop_stderr" == *"[routing]"* && "$stop_stderr" == *"←"* ]]; then
            pass "stderr output formatted correctly for terminal"
        else
            fail "Stop stderr format wrong" "$stop_stderr"
        fi
    else
        fail "Start stderr format wrong" "$start_stderr"
    fi
}

# ============================================================================
# Run all tests
# ============================================================================
echo ""
echo "========================================"
echo "Claude Router System - Hook Test Suite"
echo "========================================"
echo ""

test_start_basic
test_stop_basic
test_duration_calculation
test_concurrent_execution
test_special_characters
test_model_tier_detection
test_metrics_format
test_missing_fields
test_lock_file_cleanup
test_stderr_output

echo ""
echo "========================================"
echo "Results: $TESTS_PASSED passed, $TESTS_FAILED failed (of $TESTS_RUN total)"
echo "========================================"

if [[ $TESTS_FAILED -gt 0 ]]; then
    exit 1
else
    exit 0
fi
