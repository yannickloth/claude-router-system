#!/bin/bash
# End-to-End Plugin Integration Test
#
# Creates a fake project, installs the plugin, and verifies:
# 1. Plugin structure is recognized
# 2. Agents are loadable
# 3. Hooks fire correctly when simulated
# 4. State files are created in correct locations
#
# Usage: ./tests/test_e2e_plugin.sh
#
# Note: This does NOT test actual Claude Code execution (requires API key),
# but verifies the plugin would work if loaded by Claude Code.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Get script directory and plugin root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$TESTS_DIR")"
PLUGIN_DIR="$PROJECT_ROOT/plugins/infolead-claude-subscription-router"

# Create isolated test environment
TEST_HOME=$(mktemp -d)
TEST_PROJECT="$TEST_HOME/test-project"
mkdir -p "$TEST_PROJECT"

# Override HOME for complete isolation
export HOME="$TEST_HOME"

cleanup() {
    rm -rf "$TEST_HOME"
}
trap cleanup EXIT

log_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
}

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
    if [[ -n "${2:-}" ]]; then
        echo -e "${RED}      ${NC} $2"
    fi
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
}

# ============================================================================
# PHASE 1: Setup Plugin Installation
# ============================================================================
log_section "Phase 1: Plugin Installation"

setup_plugin() {
    log_test "Installing plugin via symlink"

    # Create Claude Code plugin directory structure
    mkdir -p "$HOME/.claude/plugins"

    # Symlink the plugin (how users would install it)
    ln -s "$PLUGIN_DIR" "$HOME/.claude/plugins/infolead-claude-subscription-router"

    if [[ -L "$HOME/.claude/plugins/infolead-claude-subscription-router" ]]; then
        pass "Plugin symlinked to ~/.claude/plugins/"
    else
        fail "Plugin symlink failed"
        return 1
    fi
}

verify_plugin_structure() {
    log_test "Verifying plugin.json structure"

    local plugin_json="$HOME/.claude/plugins/infolead-claude-subscription-router/plugin.json"

    if [[ ! -f "$plugin_json" ]]; then
        fail "plugin.json not found at $plugin_json"
        return 1
    fi

    # Check required fields
    local name version hooks_path
    name=$(jq -r '.name' "$plugin_json")
    version=$(jq -r '.version' "$plugin_json")
    hooks_path=$(jq -r '.hooks' "$plugin_json")

    if [[ "$name" == "infolead-claude-subscription-router" ]] && \
       [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] && \
       [[ -n "$hooks_path" ]]; then
        pass "plugin.json has valid structure (name=$name, version=$version)"
    else
        fail "plugin.json missing required fields" "name=$name, version=$version, hooks=$hooks_path"
        return 1
    fi
}

verify_hooks_json() {
    log_test "Verifying hooks.json structure"

    # hooks.json is relative to plugin.json location
    local hooks_json="$PLUGIN_DIR/hooks/hooks.json"

    if [[ ! -f "$hooks_json" ]]; then
        fail "hooks.json not found at $hooks_json"
        return 1
    fi

    # Check for SubagentStart and SubagentStop hooks (nested under .hooks key)
    local has_start has_stop
    has_start=$(jq '.hooks | has("SubagentStart")' "$hooks_json")
    has_stop=$(jq '.hooks | has("SubagentStop")' "$hooks_json")

    if [[ "$has_start" == "true" ]] && [[ "$has_stop" == "true" ]]; then
        pass "hooks.json defines SubagentStart and SubagentStop"
    else
        fail "hooks.json missing hook definitions" "SubagentStart=$has_start, SubagentStop=$has_stop"
        return 1
    fi
}

# ============================================================================
# PHASE 2: Agent Definition Verification
# ============================================================================
log_section "Phase 2: Agent Definitions"

verify_agents_loadable() {
    log_test "Verifying agent files have valid YAML frontmatter"

    local agents_dir="$PLUGIN_DIR/agents"
    local errors=0

    for agent_file in "$agents_dir"/*.md; do
        local filename=$(basename "$agent_file")

        # Check for YAML frontmatter
        if ! head -1 "$agent_file" | grep -q "^---$"; then
            echo "  Missing frontmatter: $filename"
            errors=$((errors + 1))
            continue
        fi

        # Extract and validate frontmatter
        local frontmatter
        frontmatter=$(sed -n '2,/^---$/p' "$agent_file" | head -n -1)

        # Check required fields
        if ! echo "$frontmatter" | grep -q "^name:"; then
            echo "  Missing 'name' field: $filename"
            errors=$((errors + 1))
        fi
        if ! echo "$frontmatter" | grep -q "^model:"; then
            echo "  Missing 'model' field: $filename"
            errors=$((errors + 1))
        fi
    done

    local agent_count
    agent_count=$(ls -1 "$agents_dir"/*.md 2>/dev/null | wc -l)

    if [[ "$errors" -eq 0 ]]; then
        pass "All $agent_count agent files have valid frontmatter"
    else
        fail "$errors agent files have invalid frontmatter"
    fi
}

verify_general_agents() {
    log_test "Verifying general agents exist (haiku/sonnet/opus)"

    local agents_dir="$PLUGIN_DIR/agents"
    local missing=""

    for agent in "haiku-general" "sonnet-general" "opus-general"; do
        if [[ ! -f "$agents_dir/$agent.md" ]]; then
            missing="$missing $agent"
        fi
    done

    if [[ -z "$missing" ]]; then
        pass "All general agents exist"
    else
        fail "Missing general agents:$missing"
    fi
}

verify_router_agents() {
    log_test "Verifying router agents exist"

    local agents_dir="$PLUGIN_DIR/agents"
    local missing=""

    for agent in "router" "router-escalation"; do
        if [[ ! -f "$agents_dir/$agent.md" ]]; then
            missing="$missing $agent"
        fi
    done

    if [[ -z "$missing" ]]; then
        pass "Router agents exist"
    else
        fail "Missing router agents:$missing"
    fi
}

verify_agent_permission_modes() {
    log_test "Verifying Write/Edit agents have permissionMode: acceptEdits"

    local agents_dir="$PLUGIN_DIR/agents"
    local errors=0

    # These agents have Write/Edit tools and must have permissionMode
    for agent in "haiku-general" "sonnet-general" "opus-general" "work-coordinator" "temporal-scheduler"; do
        local file="$agents_dir/$agent.md"
        if [[ ! -f "$file" ]]; then
            echo "  Missing agent file: $agent.md"
            errors=$((errors + 1))
            continue
        fi

        # Extract frontmatter (between first and second ---)
        local frontmatter
        frontmatter=$(sed -n '2,/^---$/p' "$file" | head -n -1)

        if ! echo "$frontmatter" | grep -q "permissionMode:.*acceptEdits"; then
            echo "  $agent: missing permissionMode: acceptEdits"
            errors=$((errors + 1))
        fi
    done

    # These read-only agents should NOT have permissionMode
    for agent in "router" "router-escalation" "planner" "strategy-advisor" "haiku-pre-router" "probabilistic-router"; do
        local file="$agents_dir/$agent.md"
        if [[ ! -f "$file" ]]; then
            continue
        fi

        local frontmatter
        frontmatter=$(sed -n '2,/^---$/p' "$file" | head -n -1)

        if echo "$frontmatter" | grep -q "permissionMode:"; then
            echo "  $agent: should NOT have permissionMode (read-only)"
            errors=$((errors + 1))
        fi
    done

    if [[ "$errors" -eq 0 ]]; then
        pass "Agent permission modes correctly configured"
    else
        fail "$errors permission mode configuration errors"
    fi
}

simulate_pretooluse_hook() {
    log_test "Simulating PreToolUse hook for Write approval"

    local hooks_dir="$PLUGIN_DIR/hooks"
    local hook_script="$hooks_dir/pre-tool-use-write-approve.sh"

    if [[ ! -f "$hook_script" ]]; then
        fail "PreToolUse hook script not found" "$hook_script"
        return 1
    fi

    local input_json='{"tool_name": "Write", "tool_input": {"file_path": "/tmp/test.txt", "content": "test"}}'
    local output

    output=$(echo "$input_json" | "$hook_script" 2>/dev/null)

    if echo "$output" | jq -e '.permissionDecision == "allow"' > /dev/null 2>&1; then
        pass "PreToolUse hook returns permission approval JSON"
    else
        fail "PreToolUse hook output incorrect" "Got: $output"
    fi
}

# ============================================================================
# PHASE 3: Simulate Claude Code Hook Events
# ============================================================================
log_section "Phase 3: Hook Event Simulation"

setup_test_project() {
    log_test "Setting up test project structure"

    # Create a minimal project that looks like a real project
    mkdir -p "$TEST_PROJECT/.claude"
    echo '{}' > "$TEST_PROJECT/.claude/settings.json"

    # Create some dummy files
    echo "# Test Project" > "$TEST_PROJECT/README.md"
    echo "print('hello')" > "$TEST_PROJECT/main.py"

    if [[ -f "$TEST_PROJECT/README.md" ]]; then
        pass "Test project created at $TEST_PROJECT"
    else
        fail "Failed to create test project"
    fi
}

simulate_agent_lifecycle() {
    log_test "Simulating complete agent lifecycle (start → work → stop)"

    local hooks_dir="$PLUGIN_DIR/hooks"
    local agent_id="e2e-test-$(date +%s)"
    local agent_type="haiku-general"

    # Simulate SubagentStart
    local start_json
    start_json=$(jq -n \
        --arg cwd "$TEST_PROJECT" \
        --arg agent_type "$agent_type" \
        --arg agent_id "$agent_id" \
        --arg transcript_path "" \
        '{cwd: $cwd, agent_type: $agent_type, agent_id: $agent_id, transcript_path: $transcript_path}')

    echo "$start_json" | "$hooks_dir/log-subagent-start.sh" 2>/dev/null

    # Verify start was logged
    local log_file="$TEST_PROJECT/.claude/logs/routing.log"
    if ! grep -q "START" "$log_file" 2>/dev/null; then
        fail "SubagentStart hook did not create log entry"
        return 1
    fi

    # Simulate some work (wait)
    sleep 1

    # Simulate SubagentStop
    local stop_json
    stop_json=$(jq -n \
        --arg cwd "$TEST_PROJECT" \
        --arg agent_type "$agent_type" \
        --arg agent_id "$agent_id" \
        --arg exit_status "success" \
        '{cwd: $cwd, agent_type: $agent_type, agent_id: $agent_id, exit_status: $exit_status}')

    echo "$stop_json" | "$hooks_dir/log-subagent-stop.sh" 2>/dev/null

    # Verify stop was logged
    if grep -q "STOP" "$log_file" 2>/dev/null; then
        pass "Agent lifecycle logged correctly (START → STOP)"
    else
        fail "SubagentStop hook did not create log entry"
    fi
}

verify_metrics_created() {
    log_test "Verifying metrics file created"

    local today
    today=$(date +%Y-%m-%d)
    local metrics_file="$HOME/.claude/infolead-router/metrics/${today}.jsonl"

    if [[ -f "$metrics_file" ]]; then
        # Verify it's valid JSONL
        local valid=true
        while read -r line; do
            if ! jq . <<< "$line" > /dev/null 2>&1; then
                valid=false
                break
            fi
        done < "$metrics_file"

        if $valid; then
            local entry_count
            entry_count=$(wc -l < "$metrics_file")
            pass "Metrics file created with $entry_count entries"
        else
            fail "Metrics file contains invalid JSON"
        fi
    else
        fail "Metrics file not created at $metrics_file"
    fi
}

verify_log_format() {
    log_test "Verifying log file format"

    local log_file="$TEST_PROJECT/.claude/logs/routing.log"

    if [[ ! -f "$log_file" ]]; then
        fail "Log file not found"
        return 1
    fi

    # Check format: TIMESTAMP | PROJECT | AGENT_TYPE | AGENT_ID | ACTION
    local valid_lines invalid_lines
    valid_lines=$(grep -c "^[0-9].*|.*|.*|.*|" "$log_file" 2>/dev/null || echo "0")
    valid_lines="${valid_lines//[^0-9]/}"  # Strip non-numeric
    invalid_lines=$(grep -cv "^[0-9].*|.*|.*|.*|" "$log_file" 2>/dev/null || true)
    invalid_lines="${invalid_lines:-0}"
    invalid_lines="${invalid_lines//[^0-9]/}"  # Strip non-numeric

    if [[ "$invalid_lines" -eq 0 ]] && [[ "$valid_lines" -gt 0 ]]; then
        pass "Log file format is correct ($valid_lines entries)"
    else
        fail "Log file has format issues" "Valid: $valid_lines, Invalid: $invalid_lines"
    fi
}

# ============================================================================
# PHASE 4: Routing Logic Verification
# ============================================================================
log_section "Phase 4: Routing Logic"

test_routing_decisions() {
    log_test "Verifying routing logic produces correct escalation decisions"

    cd "$PLUGIN_DIR/implementation"

    # Test escalation behavior - these should ALWAYS escalate regardless of routing mode
    local test_passed=0
    local test_total=0

    # Complex task -> should escalate
    local result
    result=$(python3 -c "
from routing_core import route_request, RouterDecision
result = route_request('Design a new microservices architecture')
print(result.decision.value)
" 2>/dev/null)

    test_total=$((test_total + 1))
    if [[ "$result" == "escalate" ]]; then
        test_passed=$((test_passed + 1))
    else
        echo "  'Design architecture' -> expected 'escalate', got '$result'"
    fi

    # Destructive operation -> should escalate
    result=$(python3 -c "
from routing_core import route_request, RouterDecision
result = route_request('Delete all temporary files')
print(result.decision.value)
" 2>/dev/null)

    test_total=$((test_total + 1))
    if [[ "$result" == "escalate" ]]; then
        test_passed=$((test_passed + 1))
    else
        echo "  'Delete all files' -> expected 'escalate', got '$result'"
    fi

    # Multi-objective -> should escalate
    result=$(python3 -c "
from routing_core import route_request, RouterDecision
result = route_request('Fix the bug and add tests')
print(result.decision.value)
" 2>/dev/null)

    test_total=$((test_total + 1))
    if [[ "$result" == "escalate" ]]; then
        test_passed=$((test_passed + 1))
    else
        echo "  'Fix bug and add tests' -> expected 'escalate', got '$result'"
    fi

    cd - > /dev/null

    if [[ "$test_passed" -eq "$test_total" ]]; then
        pass "Routing logic correct ($test_passed/$test_total decisions)"
    else
        fail "Routing logic errors" "$test_passed/$test_total correct"
    fi
}

# ============================================================================
# PHASE 5: State Persistence
# ============================================================================
log_section "Phase 5: State Persistence"

test_session_state() {
    log_test "Verifying session state persistence"

    cd "$PLUGIN_DIR/implementation"

    # Create state in one "session"
    python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '.')
from session_state_manager import SessionStateManager

manager = SessionStateManager(memory_dir=Path('$TEST_HOME/.claude/infolead-router/memory'))
manager.update_focus('Testing persistence')
manager.add_active_agent('test-agent')
" 2>/dev/null

    # Read state in another "session"
    local focus
    focus=$(python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '.')
from session_state_manager import SessionStateManager

manager = SessionStateManager(memory_dir=Path('$TEST_HOME/.claude/infolead-router/memory'))
state = manager.get_current_state()
print(state.current_focus)
" 2>/dev/null)

    cd - > /dev/null

    if [[ "$focus" == "Testing persistence" ]]; then
        pass "Session state persists across instances"
    else
        fail "Session state not persisted" "Expected 'Testing persistence', got '$focus'"
    fi
}

# ============================================================================
# Run All Tests
# ============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Claude Router System - End-to-End Integration Tests       ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  Test Home: $TEST_HOME"
echo "║  Plugin:    $PLUGIN_DIR"
echo "╚═══════════════════════════════════════════════════════════════╝"

# Phase 1: Plugin Installation
setup_plugin
verify_plugin_structure
verify_hooks_json

# Phase 2: Agent Definitions
verify_agents_loadable
verify_general_agents
verify_router_agents
verify_agent_permission_modes

# Phase 3: Hook Simulation
setup_test_project
simulate_agent_lifecycle
simulate_pretooluse_hook
verify_metrics_created
verify_log_format

# Phase 4: Routing Logic
test_routing_decisions

# Phase 5: State Persistence
test_session_state

# Summary
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                         RESULTS                               ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "║  ${GREEN}✓ ALL TESTS PASSED${NC}                                          ║"
else
    echo -e "║  ${RED}✗ SOME TESTS FAILED${NC}                                         ║"
fi
echo "║                                                               ║"
echo "║  Passed: $TESTS_PASSED                                                       ║"
echo "║  Failed: $TESTS_FAILED                                                       ║"
echo "║  Total:  $TESTS_RUN                                                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"

if [[ $TESTS_FAILED -gt 0 ]]; then
    exit 1
else
    exit 0
fi
