#!/bin/bash
# Test Suite for Project Isolation (v1.7.1 Feature)
#
# Tests:
# 1. detect_project_root() - Walk up tree to find .claude
# 2. get_project_id() - SHA256 hash of project path
# 3. get_project_data_dir() - Create project-specific dirs
# 4. is_router_enabled() - Check settings.json
# 5. load_config_file() - 3-level config cascade
# 6. Cross-project isolation - Verify data separation
#
# Usage: ./tests/infolead-claude-subscription-router/test_project_isolation.sh
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
COMMON_FUNCTIONS="$HOOKS_DIR/common-functions.sh"

# Verify common-functions.sh exists
if [ ! -f "$COMMON_FUNCTIONS" ]; then
    echo -e "${RED}FATAL:${NC} common-functions.sh not found at $COMMON_FUNCTIONS"
    exit 1
fi

# Source common functions
# shellcheck source=/dev/null
source "$COMMON_FUNCTIONS"

# Create temp directory for tests
TEST_ROOT=$(mktemp -d)

# Cleanup on exit
cleanup() {
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

# Test helper functions
log_test() {
    echo -e "${YELLOW}TEST $TESTS_RUN:${NC} $1"
}

pass() {
    echo -e "${GREEN}PASS:${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
}

fail() {
    echo -e "${RED}FAIL:${NC} $1"
    if [ -n "${2:-}" ]; then
        echo -e "${RED}      ${NC} $2"
    fi
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
}

# ============================================================================
# TEST 1: detect_project_root() - Basic functionality
# ============================================================================
test_detect_project_root_basic() {
    log_test "detect_project_root() - finds .claude in current dir"

    local test_dir="$TEST_ROOT/project1"
    mkdir -p "$test_dir/.claude"

    cd "$test_dir" || return 1
    local result
    result=$(detect_project_root)

    if [ "$result" = "$test_dir" ]; then
        pass "Detected project root in current directory"
    else
        fail "Failed to detect project root" "Expected: $test_dir, Got: $result"
    fi
}

# ============================================================================
# TEST 2: detect_project_root() - Walk up tree
# ============================================================================
test_detect_project_root_nested() {
    log_test "detect_project_root() - walks up to find .claude"

    local project_root="$TEST_ROOT/project2"
    local nested_dir="$project_root/src/components/deeply/nested"
    mkdir -p "$project_root/.claude"
    mkdir -p "$nested_dir"

    cd "$nested_dir" || return 1
    local result
    result=$(detect_project_root)

    if [ "$result" = "$project_root" ]; then
        pass "Detected project root 5 levels up"
    else
        fail "Failed to walk up tree" "Expected: $project_root, Got: $result"
    fi
}

# ============================================================================
# TEST 3: detect_project_root() - No .claude found (return global)
# ============================================================================
test_detect_project_root_global() {
    log_test "detect_project_root() - returns 'global' when no .claude"

    local test_dir="$TEST_ROOT/no-claude-dir"
    mkdir -p "$test_dir"

    cd "$test_dir" || return 1
    local result
    result=$(detect_project_root) || result="global"

    if [ "$result" = "global" ]; then
        pass "Correctly returned 'global' for non-project directory"
    else
        fail "Should return 'global'" "Got: $result"
    fi
}

# ============================================================================
# TEST 4: get_project_id() - Generates consistent SHA256 hash
# ============================================================================
test_get_project_id_consistent() {
    log_test "get_project_id() - generates consistent SHA256 hash"

    local test_dir="$TEST_ROOT/project3"
    mkdir -p "$test_dir/.claude"

    cd "$test_dir" || return 1
    local id1 id2
    id1=$(get_project_id)
    id2=$(get_project_id)

    # Check format (should be 16-char hex string - truncated SHA256)
    if ! [[ "$id1" =~ ^[a-f0-9]{16}$ ]]; then
        fail "Project ID format invalid" "Expected 16-char hex, got: $id1"
        return
    fi

    # Check consistency
    if [ "$id1" = "$id2" ]; then
        pass "Project ID is consistent across calls"
    else
        fail "Project ID inconsistent" "First: $id1, Second: $id2"
    fi
}

# ============================================================================
# TEST 5: get_project_id() - Different projects get different IDs
# ============================================================================
test_get_project_id_unique() {
    log_test "get_project_id() - different projects have different IDs"

    local proj_a="$TEST_ROOT/projectA"
    local proj_b="$TEST_ROOT/projectB"
    mkdir -p "$proj_a/.claude" "$proj_b/.claude"

    cd "$proj_a" || return 1
    local id_a
    id_a=$(get_project_id)

    cd "$proj_b" || return 1
    local id_b
    id_b=$(get_project_id)

    if [ "$id_a" != "$id_b" ]; then
        pass "Different projects have unique IDs"
    else
        fail "Project IDs should be unique" "Both got: $id_a"
    fi
}

# ============================================================================
# TEST 6: get_project_data_dir() - Creates project-specific directories
# ============================================================================
test_get_project_data_dir() {
    log_test "get_project_data_dir() - creates project-specific dirs"

    local test_dir="$TEST_ROOT/project4"
    mkdir -p "$test_dir/.claude"

    # Override HOME to test directory
    export HOME="$TEST_ROOT"

    cd "$test_dir" || return 1
    local data_dir
    data_dir=$(get_project_data_dir "state")

    # Verify directory was created
    if [ -d "$data_dir" ]; then
        pass "Created project data directory: $data_dir"
    else
        fail "Failed to create data directory" "Expected: $data_dir"
        return
    fi

    # Verify it contains project ID
    local project_id
    project_id=$(get_project_id)
    if [[ "$data_dir" == *"$project_id"* ]]; then
        pass "Data directory includes project ID"
    else
        fail "Data directory missing project ID" "Path: $data_dir, ID: $project_id"
    fi
}

# ============================================================================
# TEST 7: Cross-project isolation - Verify data separation
# ============================================================================
test_cross_project_isolation() {
    log_test "Cross-project isolation - data directories are separate"

    local proj_x="$TEST_ROOT/projectX"
    local proj_y="$TEST_ROOT/projectY"
    mkdir -p "$proj_x/.claude" "$proj_y/.claude"

    export HOME="$TEST_ROOT"

    cd "$proj_x" || return 1
    local data_x
    data_x=$(get_project_data_dir "metrics")

    cd "$proj_y" || return 1
    local data_y
    data_y=$(get_project_data_dir "metrics")

    if [ "$data_x" != "$data_y" ]; then
        pass "Projects have isolated data directories"
    else
        fail "Projects share data directory" "Both: $data_x"
        return
    fi

    # Write test data to each project
    echo "project X data" > "$data_x/test.txt"
    echo "project Y data" > "$data_y/test.txt"

    # Verify isolation
    local content_x content_y
    content_x=$(cat "$data_x/test.txt")
    content_y=$(cat "$data_y/test.txt")

    if [ "$content_x" = "project X data" ] && [ "$content_y" = "project Y data" ]; then
        pass "Data is properly isolated between projects"
    else
        fail "Data isolation broken" "X: $content_x, Y: $content_y"
    fi
}

# ============================================================================
# TEST 8: is_router_enabled() - Checks settings.json correctly
# ============================================================================
test_is_router_enabled_true() {
    log_test "is_router_enabled() - returns true when enabled"

    local test_dir="$TEST_ROOT/project5"
    mkdir -p "$test_dir/.claude"

    # Create settings.json with router enabled
    cat > "$test_dir/.claude/settings.json" <<EOF
{
  "plugins": {
    "router": {
      "enabled": true
    }
  }
}
EOF

    cd "$test_dir" || return 1

    if is_router_enabled; then
        pass "Correctly detected enabled router"
    else
        fail "Should detect enabled router" "settings.json: $(cat "$test_dir/.claude/settings.json")"
    fi
}

# ============================================================================
# TEST 9: is_router_enabled() - Returns false when disabled
# ============================================================================
test_is_router_enabled_false() {
    log_test "is_router_enabled() - returns false when disabled"

    local test_dir="$TEST_ROOT/project6"
    mkdir -p "$test_dir/.claude"

    # Create settings.json with router disabled
    cat > "$test_dir/.claude/settings.json" <<EOF
{
  "plugins": {
    "router": {
      "enabled": false
    }
  }
}
EOF

    cd "$test_dir" || return 1

    if is_router_enabled; then
        fail "Should detect disabled router"
    else
        pass "Correctly detected disabled router"
    fi
}

# ============================================================================
# TEST 10: load_config_file() - 3-level config cascade
# ============================================================================
test_config_cascade() {
    log_test "load_config_file() - 3-level config cascade precedence"

    local test_dir="$TEST_ROOT/project7"
    mkdir -p "$test_dir/.claude"

    export HOME="$TEST_ROOT"

    # Create global config
    mkdir -p "$HOME/.claude"
    cat > "$HOME/.claude/router-config.json" <<EOF
{
  "max_tier": "opus",
  "global_setting": "global_value"
}
EOF

    # Create project-local config (should override global)
    cat > "$test_dir/.claude/router-config.json" <<EOF
{
  "max_tier": "sonnet",
  "project_setting": "project_value"
}
EOF

    cd "$test_dir" || return 1

    # load_config_file returns the path to the highest-priority config file
    local config_path
    config_path=$(load_config_file "router-config.json" 2>/dev/null)

    if [ -z "$config_path" ]; then
        fail "Config file not found" "load_config_file returned empty"
        return
    fi

    # Verify it returned the project-local path (not global)
    if [[ "$config_path" == "$test_dir/.claude/router-config.json" ]]; then
        pass "Config cascade: project-local path takes precedence"
    else
        fail "Config cascade broken" "Expected: $test_dir/.claude/router-config.json, Got: $config_path"
        return
    fi

    # Verify content is correct (project-local values)
    local max_tier
    max_tier=$(jq -r '.max_tier // "unknown"' "$config_path" 2>/dev/null)

    if [ "$max_tier" = "sonnet" ]; then
        pass "Config content: project-local overrides global values"
    else
        fail "Config content incorrect" "Expected max_tier=sonnet, got: $max_tier"
    fi
}

# ============================================================================
# Run all tests
# ============================================================================
echo "========================================================================"
echo "Project Isolation Test Suite (v1.7.1 Feature)"
echo "========================================================================"
echo ""

test_detect_project_root_basic
test_detect_project_root_nested
test_detect_project_root_global
test_get_project_id_consistent
test_get_project_id_unique
test_get_project_data_dir
test_cross_project_isolation
test_is_router_enabled_true
test_is_router_enabled_false
test_config_cascade

echo ""
echo "========================================================================"
echo "Test Results"
echo "========================================================================"
echo -e "Total:  $TESTS_RUN"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}SOME TESTS FAILED${NC}"
    exit 1
fi
