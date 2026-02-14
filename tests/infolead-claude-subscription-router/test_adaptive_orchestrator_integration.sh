#!/usr/bin/env bash
#
# Integration tests for adaptive orchestrator
#
# Tests integration with:
# - routing_core (routing decisions)
# - metrics_collector (metrics recording)
# - config file loading
# - error handling and fallbacks
#
# Usage:
#   ./test_adaptive_orchestrator_integration.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPL_DIR="${SCRIPT_DIR}/../../plugins/infolead-claude-subscription-router/implementation"
TEMP_DIR=$(mktemp -d)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Run test with error handling
run_test() {
    local test_name="$1"
    ((TESTS_RUN++))
    echo ""
    info "Running: $test_name"
}

# ============================================================================
# TEST: Adaptive orchestrator + routing_core integration
# ============================================================================

test_routing_integration() {
    run_test "Adaptive orchestrator integrates with routing_core"

    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" --json <<< "Fix typo in README.md" 2>&1)
    local exit_code=$?

    if [[ $exit_code -eq 0 ]] && echo "$output" | jq -e '.routing' >/dev/null 2>&1; then
        pass "Routing integration works"
    else
        fail "Routing integration failed (exit: $exit_code)"
        echo "$output"
    fi
}

# ============================================================================
# TEST: Metrics collector integration
# ============================================================================

test_metrics_integration() {
    run_test "Adaptive orchestrator records metrics"

    local metrics_dir="$TEMP_DIR/metrics"
    mkdir -p "$metrics_dir"

    # Create temporary Python script to test metrics
    cat > "$TEMP_DIR/test_metrics.py" <<'EOF'
import sys
from pathlib import Path

# Add implementation directory
IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import AdaptiveOrchestrator

metrics_dir = Path(sys.argv[1])
orchestrator = AdaptiveOrchestrator(metrics_dir=metrics_dir)
result = orchestrator.orchestrate("Fix typo in README.md")

# Check if metrics were recorded
metrics_files = list(metrics_dir.glob("*.jsonl"))
print(f"Metrics files created: {len(metrics_files)}")
sys.exit(0 if len(metrics_files) > 0 else 1)
EOF

    python3 "$TEMP_DIR/test_metrics.py" "$metrics_dir" 2>&1
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        pass "Metrics recording works"
    else
        fail "Metrics recording failed"
    fi
}

# ============================================================================
# TEST: Config file loading
# ============================================================================

test_config_loading() {
    run_test "Config file loading affects behavior"

    local config_file="$TEMP_DIR/test-config.yaml"

    # Create config that forces multi_stage mode
    cat > "$config_file" <<EOF
overrides:
  force_mode: multi_stage
EOF

    # Create test script
    cat > "$TEMP_DIR/test_config.py" <<EOF
import sys
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import AdaptiveOrchestrator, OrchestrationMode

config_path = Path(sys.argv[1])
orchestrator = AdaptiveOrchestrator(config_path=config_path)

# Even SIMPLE request should use multi_stage due to force_mode
result = orchestrator.orchestrate("Fix typo in README.md")

if result.mode == OrchestrationMode.MULTI_STAGE:
    print("SUCCESS: force_mode override works")
    sys.exit(0)
else:
    print(f"FAIL: Expected MULTI_STAGE, got {result.mode.value}")
    sys.exit(1)
EOF

    local output
    output=$(python3 "$TEMP_DIR/test_config.py" "$config_file" 2>&1)
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        pass "Config loading works: $output"
    else
        fail "Config loading failed: $output"
    fi
}

# ============================================================================
# TEST: Config fallback on missing file
# ============================================================================

test_config_fallback() {
    run_test "Missing config file falls back to defaults"

    cat > "$TEMP_DIR/test_fallback.py" <<EOF
import sys
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import load_config

nonexistent_config = Path("/tmp/nonexistent-config-12345.yaml")
config = load_config(nonexistent_config)

if config.simple_confidence_threshold == 0.7:
    print("SUCCESS: Defaults loaded")
    sys.exit(0)
else:
    print(f"FAIL: Expected 0.7, got {config.simple_confidence_threshold}")
    sys.exit(1)
EOF

    local output
    output=$(python3 "$TEMP_DIR/test_fallback.py" 2>&1)
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        pass "Config fallback works: $output"
    else
        fail "Config fallback failed: $output"
    fi
}

# ============================================================================
# TEST: Malformed config handling
# ============================================================================

test_malformed_config() {
    run_test "Malformed config falls back gracefully"

    local bad_config="$TEMP_DIR/bad-config.yaml"
    echo "invalid: yaml: syntax: {" > "$bad_config"

    cat > "$TEMP_DIR/test_malformed.py" <<EOF
import sys
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import load_config

bad_config = Path(sys.argv[1])
config = load_config(bad_config)

# Should fall back to defaults
if config.simple_confidence_threshold == 0.7:
    print("SUCCESS: Graceful fallback on malformed YAML")
    sys.exit(0)
else:
    print(f"FAIL: Expected default 0.7, got {config.simple_confidence_threshold}")
    sys.exit(1)
EOF

    local output
    output=$(python3 "$TEMP_DIR/test_malformed.py" "$bad_config" 2>&1)
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        pass "Malformed config handling works"
    else
        fail "Malformed config handling failed: $output"
    fi
}

# ============================================================================
# TEST: Custom pattern integration
# ============================================================================

test_custom_patterns() {
    run_test "Custom patterns are applied during classification"

    local config_file="$TEMP_DIR/custom-patterns.yaml"

    cat > "$config_file" <<EOF
patterns:
  custom_complex:
    - pattern: '\\bmigrate\\b'
      name: 'migration_task'
EOF

    cat > "$TEMP_DIR/test_custom_patterns.py" <<EOF
import sys
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import AdaptiveOrchestrator, ComplexityLevel

config_path = Path(sys.argv[1])
orchestrator = AdaptiveOrchestrator(config_path=config_path)

result = orchestrator.orchestrate("Migrate database schema")

# Should be COMPLEX due to custom pattern
if result.complexity == ComplexityLevel.COMPLEX:
    indicators = result.metadata.get('complexity_indicators', [])
    if any('migration_task' in ind for ind in indicators):
        print("SUCCESS: Custom pattern detected")
        sys.exit(0)
    else:
        print(f"FAIL: Pattern not in indicators: {indicators}")
        sys.exit(1)
else:
    print(f"FAIL: Expected COMPLEX, got {result.complexity.value}")
    sys.exit(1)
EOF

    local output
    output=$(python3 "$TEMP_DIR/test_custom_patterns.py" "$config_file" 2>&1)
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        pass "Custom patterns work: $output"
    else
        fail "Custom patterns failed: $output"
    fi
}

# ============================================================================
# TEST: JSON output mode
# ============================================================================

test_json_output() {
    run_test "JSON output mode produces valid JSON"

    local output
    output=$(echo "Fix typo in README.md" | python3 "$IMPL_DIR/adaptive_orchestrator.py" --json 2>&1)
    local exit_code=$?

    if [[ $exit_code -eq 0 ]] && echo "$output" | jq -e '.' >/dev/null 2>&1; then
        local mode=$(echo "$output" | jq -r '.mode')
        local complexity=$(echo "$output" | jq -r '.complexity')
        pass "JSON output valid (mode: $mode, complexity: $complexity)"
    else
        fail "JSON output invalid"
        echo "$output"
    fi
}

# ============================================================================
# TEST: Human-readable output mode
# ============================================================================

test_human_output() {
    run_test "Human-readable output mode works"

    local output
    output=$(echo "Fix typo in README.md" | python3 "$IMPL_DIR/adaptive_orchestrator.py" 2>&1)
    local exit_code=$?

    if [[ $exit_code -eq 0 ]] && echo "$output" | grep -q "Adaptive Orchestration"; then
        pass "Human-readable output works"
    else
        fail "Human-readable output failed"
        echo "$output"
    fi
}

# ============================================================================
# TEST: Error handling for empty input
# ============================================================================

test_empty_input() {
    run_test "Empty input is handled gracefully"

    local output
    output=$(python3 "$IMPL_DIR/adaptive_orchestrator.py" 2>&1 <<< "")
    local exit_code=$?

    # Should exit with error for empty input
    if [[ $exit_code -ne 0 ]] && echo "$output" | grep -qi "error"; then
        pass "Empty input rejected with error message"
    else
        fail "Empty input handling incorrect (exit: $exit_code)"
    fi
}

# ============================================================================
# TEST: Workflow integration (classify → orchestrate → route)
# ============================================================================

test_full_workflow() {
    run_test "Full workflow: classify → orchestrate → route"

    cat > "$TEMP_DIR/test_workflow.py" <<EOF
import sys
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import AdaptiveOrchestrator, ComplexityLevel, OrchestrationMode

orchestrator = AdaptiveOrchestrator()

# Test SIMPLE request
result = orchestrator.orchestrate("Fix typo in README.md")
assert result.complexity == ComplexityLevel.SIMPLE
assert result.mode == OrchestrationMode.SINGLE_STAGE
assert result.routing_result is not None

# Test COMPLEX request
result = orchestrator.orchestrate("Design authentication architecture")
assert result.complexity == ComplexityLevel.COMPLEX
assert result.mode == OrchestrationMode.MULTI_STAGE
assert 'interpretation' in result.metadata
assert 'plan' in result.metadata

print("SUCCESS: Full workflow works for SIMPLE and COMPLEX requests")
sys.exit(0)
EOF

    local output
    output=$(python3 "$TEMP_DIR/test_workflow.py" 2>&1)
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        pass "Full workflow works: $output"
    else
        fail "Full workflow failed: $output"
    fi
}

# ============================================================================
# RUN ALL TESTS
# ============================================================================

main() {
    echo "======================================================================"
    echo "Adaptive Orchestrator Integration Tests"
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

    # Run tests
    test_routing_integration
    test_metrics_integration
    test_config_loading
    test_config_fallback
    test_malformed_config
    test_custom_patterns
    test_json_output
    test_human_output
    test_empty_input
    test_full_workflow

    # Summary
    echo ""
    echo "======================================================================"
    echo "Test Summary"
    echo "======================================================================"
    echo "Tests run:    $TESTS_RUN"
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo ""
        echo -e "${GREEN}All integration tests passed!${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}Some tests failed.${NC}"
        exit 1
    fi
}

main "$@"
