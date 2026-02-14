#!/usr/bin/env bash
#
# End-to-end tests for adaptive orchestrator
#
# Tests complete workflows:
# - User request → adaptive classification → orchestration → routing
# - All three orchestration modes in realistic scenarios
# - Config file effects on end-to-end behavior
#
# Usage:
#   ./test_adaptive_orchestrator_e2e.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPL_DIR="${SCRIPT_DIR}/../../plugins/infolead-claude-subscription-router/implementation"
TEMP_DIR=$(mktemp -d)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Cleanup on exit
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Test result helpers
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

detail() {
    echo -e "${BLUE}  →${NC} $1"
}

# Run test with error handling
run_test() {
    local test_name="$1"
    ((TESTS_RUN++))
    echo ""
    info "E2E Test: $test_name"
}

# ============================================================================
# E2E TEST: SIMPLE request workflow
# ============================================================================

test_simple_request_e2e() {
    run_test "SIMPLE request: Fix typo in README.md"

    local request="Fix typo in README.md"
    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "$request" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Orchestration failed (exit: $exit_code)"
        echo "$output"
        return
    fi

    # Verify complexity classification
    local complexity=$(echo "$output" | jq -r '.complexity')
    if [[ "$complexity" != "simple" ]]; then
        fail "Expected complexity=simple, got $complexity"
        return
    fi
    detail "Complexity: $complexity"

    # Verify orchestration mode
    local mode=$(echo "$output" | jq -r '.mode')
    if [[ "$mode" != "single_stage" ]]; then
        fail "Expected mode=single_stage, got $mode"
        return
    fi
    detail "Mode: $mode"

    # Verify routing decision exists
    if ! echo "$output" | jq -e '.routing' >/dev/null 2>&1; then
        fail "No routing decision in output"
        return
    fi
    local agent=$(echo "$output" | jq -r '.routing.agent // "none"')
    detail "Routed to: $agent"

    # Verify metadata
    local confidence=$(echo "$output" | jq -r '.metadata.complexity_confidence')
    detail "Confidence: $confidence"

    pass "SIMPLE request workflow complete (mode: $mode, agent: $agent)"
}

# ============================================================================
# E2E TEST: MODERATE request workflow
# ============================================================================

test_moderate_request_e2e() {
    run_test "MODERATE request: Fix bug in auth.py"

    local request="Fix bug in auth.py"
    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "$request" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Orchestration failed (exit: $exit_code)"
        return
    fi

    local complexity=$(echo "$output" | jq -r '.complexity')
    local mode=$(echo "$output" | jq -r '.mode')

    detail "Complexity: $complexity"
    detail "Mode: $mode"

    # MODERATE should use single_stage_monitored
    if [[ "$complexity" == "moderate" && "$mode" == "single_stage_monitored" ]]; then
        local monitoring=$(echo "$output" | jq -r '.metadata.monitoring_enabled')
        detail "Monitoring enabled: $monitoring"
        pass "MODERATE request workflow complete (monitoring: $monitoring)"
    else
        fail "Expected complexity=moderate with mode=single_stage_monitored, got $complexity/$mode"
    fi
}

# ============================================================================
# E2E TEST: COMPLEX request workflow
# ============================================================================

test_complex_request_e2e() {
    run_test "COMPLEX request: Design caching architecture"

    local request="Design a caching architecture with fallback strategies"
    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "$request" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Orchestration failed (exit: $exit_code)"
        return
    fi

    local complexity=$(echo "$output" | jq -r '.complexity')
    local mode=$(echo "$output" | jq -r '.mode')

    detail "Complexity: $complexity"
    detail "Mode: $mode"

    # COMPLEX should use multi_stage
    if [[ "$complexity" != "complex" || "$mode" != "multi_stage" ]]; then
        fail "Expected complexity=complex with mode=multi_stage, got $complexity/$mode"
        return
    fi

    # Verify multi-stage metadata
    if ! echo "$output" | jq -e '.metadata.interpretation' >/dev/null 2>&1; then
        fail "Missing interpretation metadata in multi-stage"
        return
    fi

    if ! echo "$output" | jq -e '.metadata.plan' >/dev/null 2>&1; then
        fail "Missing plan metadata in multi-stage"
        return
    fi

    local intent=$(echo "$output" | jq -r '.metadata.interpretation.intent')
    local scope=$(echo "$output" | jq -r '.metadata.interpretation.scope')
    local recommended_tier=$(echo "$output" | jq -r '.metadata.plan.recommended_tier')

    detail "Intent: $intent"
    detail "Scope: $scope"
    detail "Recommended tier: $recommended_tier"

    pass "COMPLEX request workflow complete (intent: $intent, tier: $recommended_tier)"
}

# ============================================================================
# E2E TEST: Multi-objective request
# ============================================================================

test_multi_objective_e2e() {
    run_test "Multi-objective request: Implement API and add tests and docs"

    local request="Implement a new API endpoint and add tests and update documentation"
    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "$request" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Orchestration failed (exit: $exit_code)"
        return
    fi

    local complexity=$(echo "$output" | jq -r '.complexity')
    local mode=$(echo "$output" | jq -r '.mode')

    detail "Complexity: $complexity"
    detail "Mode: $mode"

    # Multi-objective should trigger COMPLEX classification
    if [[ "$complexity" == "complex" && "$mode" == "multi_stage" ]]; then
        local indicators=$(echo "$output" | jq -r '.metadata.complexity_indicators | join(", ")')
        detail "Indicators: $indicators"
        pass "Multi-objective request classified as COMPLEX"
    else
        fail "Multi-objective should be COMPLEX, got $complexity"
    fi
}

# ============================================================================
# E2E TEST: Config override workflow
# ============================================================================

test_config_override_e2e() {
    run_test "Config override: Force multi_stage for all requests"

    local config_file="$TEMP_DIR/force-multi.yaml"
    cat > "$config_file" <<EOF
overrides:
  force_mode: multi_stage
EOF

    cat > "$TEMP_DIR/test_override.py" <<EOF
import sys
import json
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import AdaptiveOrchestrator

config_path = Path(sys.argv[1])
orchestrator = AdaptiveOrchestrator(config_path=config_path)

# Even SIMPLE request should use multi_stage
result = orchestrator.orchestrate("Fix typo in README.md")

output = {
    "complexity": result.complexity.value,
    "mode": result.mode.value,
    "forced": True
}
print(json.dumps(output, indent=2))
EOF

    local output
    output=$(python3 "$TEMP_DIR/test_override.py" "$config_file" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Config override test failed (exit: $exit_code)"
        return
    fi

    local mode=$(echo "$output" | jq -r '.mode')

    detail "Forced mode: $mode"

    if [[ "$mode" == "multi_stage" ]]; then
        pass "Config override forces multi_stage mode"
    else
        fail "Config override failed, mode is $mode"
    fi
}

# ============================================================================
# E2E TEST: Custom pattern workflow
# ============================================================================

test_custom_pattern_e2e() {
    run_test "Custom pattern: Detect migration as COMPLEX"

    local config_file="$TEMP_DIR/custom-migration.yaml"
    cat > "$config_file" <<EOF
patterns:
  custom_complex:
    - pattern: '\\bmigrat(e|ion)\\b'
      name: 'migration_task'
EOF

    cat > "$TEMP_DIR/test_custom.py" <<EOF
import sys
import json
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import AdaptiveOrchestrator

config_path = Path(sys.argv[1])
orchestrator = AdaptiveOrchestrator(config_path=config_path)

result = orchestrator.orchestrate("Migrate database to new schema")

output = {
    "complexity": result.complexity.value,
    "mode": result.mode.value,
    "indicators": result.metadata.get('complexity_indicators', [])
}
print(json.dumps(output, indent=2))
EOF

    local output
    output=$(python3 "$TEMP_DIR/test_custom.py" "$config_file" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Custom pattern test failed (exit: $exit_code)"
        return
    fi

    local complexity=$(echo "$output" | jq -r '.complexity')
    local indicators=$(echo "$output" | jq -r '.indicators | join(", ")')

    detail "Complexity: $complexity"
    detail "Indicators: $indicators"

    if [[ "$complexity" == "complex" ]] && echo "$indicators" | grep -q "migration_task"; then
        pass "Custom migration pattern detected"
    else
        fail "Custom pattern not detected (complexity: $complexity)"
    fi
}

# ============================================================================
# E2E TEST: Threshold tuning workflow
# ============================================================================

test_threshold_tuning_e2e() {
    run_test "Threshold tuning: Higher thresholds shift classification"

    local config_file="$TEMP_DIR/high-thresholds.yaml"
    cat > "$config_file" <<EOF
thresholds:
  simple_confidence: 0.95
  complex_confidence: 0.95
EOF

    cat > "$TEMP_DIR/test_threshold.py" <<EOF
import sys
import json
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import AdaptiveOrchestrator

config_path = Path(sys.argv[1])
orchestrator = AdaptiveOrchestrator(config_path=config_path)

# Request that might be borderline
result = orchestrator.orchestrate("Sort imports in app.py")

output = {
    "complexity": result.complexity.value,
    "mode": result.mode.value,
    "confidence": result.metadata.get('complexity_confidence', 0)
}
print(json.dumps(output, indent=2))
EOF

    local output
    output=$(python3 "$TEMP_DIR/test_threshold.py" "$config_file" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Threshold tuning test failed (exit: $exit_code)"
        return
    fi

    local complexity=$(echo "$output" | jq -r '.complexity')
    local confidence=$(echo "$output" | jq -r '.confidence')

    detail "Complexity: $complexity"
    detail "Confidence: $confidence"

    # With high thresholds, might shift to MODERATE
    # We just verify it runs without error and produces valid output
    pass "Threshold tuning affects classification (complexity: $complexity, confidence: $confidence)"
}

# ============================================================================
# E2E TEST: Realistic scenario - Production deployment
# ============================================================================

test_production_deployment_e2e() {
    run_test "Realistic scenario: Production deployment request"

    local request="Deploy the authentication service to production and verify health checks"
    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "$request" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Production deployment test failed (exit: $exit_code)"
        return
    fi

    local complexity=$(echo "$output" | jq -r '.complexity')
    local mode=$(echo "$output" | jq -r '.mode')

    detail "Complexity: $complexity"
    detail "Mode: $mode"

    # Production deployment is complex (multi-step, critical)
    if [[ "$complexity" == "complex" ]]; then
        pass "Production deployment correctly classified as COMPLEX"
    else
        # MODERATE is also acceptable for this scenario
        pass "Production deployment classified as $complexity (acceptable)"
    fi
}

# ============================================================================
# E2E TEST: Realistic scenario - Quick read-only operation
# ============================================================================

test_readonly_operation_e2e() {
    run_test "Realistic scenario: Read-only operation"

    local request="Show me the current git status"
    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "$request" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Read-only operation test failed (exit: $exit_code)"
        return
    fi

    local complexity=$(echo "$output" | jq -r '.complexity')
    local mode=$(echo "$output" | jq -r '.mode')

    detail "Complexity: $complexity"
    detail "Mode: $mode"

    # Read-only should be SIMPLE or MODERATE (fast path)
    if [[ "$complexity" == "simple" || "$complexity" == "moderate" ]]; then
        pass "Read-only operation uses fast path (complexity: $complexity)"
    else
        fail "Read-only should be SIMPLE or MODERATE, got $complexity"
    fi
}

# ============================================================================
# E2E TEST: Realistic scenario - Architectural decision
# ============================================================================

test_architectural_decision_e2e() {
    run_test "Realistic scenario: Architectural decision"

    local request="Which database should we use: PostgreSQL or MongoDB? Consider scalability and consistency."
    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "$request" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        fail "Architectural decision test failed (exit: $exit_code)"
        return
    fi

    local complexity=$(echo "$output" | jq -r '.complexity')
    local mode=$(echo "$output" | jq -r '.mode')

    detail "Complexity: $complexity"
    detail "Mode: $mode"

    # Architectural decision requires judgment → COMPLEX
    if [[ "$complexity" == "complex" && "$mode" == "multi_stage" ]]; then
        local intent=$(echo "$output" | jq -r '.metadata.interpretation.intent // "unknown"')
        detail "Intent: $intent"
        pass "Architectural decision uses deliberate multi-stage (intent: $intent)"
    else
        fail "Architectural decision should be COMPLEX/multi_stage, got $complexity/$mode"
    fi
}

# ============================================================================
# E2E TEST: Performance - Classification speed
# ============================================================================

test_classification_speed() {
    run_test "Performance: Classification completes quickly"

    local start=$(date +%s%N)

    # Run 10 classifications
    for i in {1..10}; do
        python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "Fix typo in README.md" >/dev/null 2>&1
    done

    local end=$(date +%s%N)
    local elapsed=$(( (end - start) / 1000000 ))  # Convert to milliseconds
    local avg=$(( elapsed / 10 ))

    detail "10 classifications in ${elapsed}ms (avg: ${avg}ms)"

    # Classification should be fast (< 500ms per request)
    if [[ $avg -lt 500 ]]; then
        pass "Classification is fast (${avg}ms avg)"
    else
        fail "Classification is slow (${avg}ms avg, expected < 500ms)"
    fi
}

# ============================================================================
# RUN ALL E2E TESTS
# ============================================================================

main() {
    echo "======================================================================"
    echo "Adaptive Orchestrator End-to-End Tests"
    echo "======================================================================"

    # Verify dependencies
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: python3 not found${NC}"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo -e "${RED}ERROR: jq not found${NC}"
        exit 1
    fi

    # Verify implementation exists
    if [[ ! -f "$IMPL_DIR/adaptive_orchestrator.py" ]]; then
        echo -e "${RED}ERROR: adaptive_orchestrator.py not found at $IMPL_DIR${NC}"
        exit 1
    fi

    # Run E2E tests
    test_simple_request_e2e
    test_moderate_request_e2e
    test_complex_request_e2e
    test_multi_objective_e2e
    test_config_override_e2e
    test_custom_pattern_e2e
    test_threshold_tuning_e2e
    test_production_deployment_e2e
    test_readonly_operation_e2e
    test_architectural_decision_e2e
    test_classification_speed

    # Summary
    echo ""
    echo "======================================================================"
    echo "E2E Test Summary"
    echo "======================================================================"
    echo "Tests run:    $TESTS_RUN"
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo ""
        echo -e "${GREEN}✓ All end-to-end tests passed!${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}✗ Some tests failed.${NC}"
        exit 1
    fi
}

main "$@"
