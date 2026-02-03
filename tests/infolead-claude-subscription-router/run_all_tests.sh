#!/bin/bash
# Run All Tests for Claude Router System
#
# Executes all test suites in order:
# 1. Unit tests (pytest)
# 2. Hook tests (bash)
# 3. E2E plugin integration tests (bash)
#
# Usage: ./tests/run_all_tests.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$TESTS_DIR")"

cd "$PROJECT_ROOT"

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Claude Router System - Complete Test Suite            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

TOTAL_PASSED=0
TOTAL_FAILED=0
SUITES_RUN=0

# ============================================================================
# Suite 1: Unit Tests (pytest)
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Suite 1: Unit Tests (pytest)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

UNIT_OUTPUT=$(mktemp)
if nix-shell -p python312Packages.pytest python312Packages.pyyaml --run "pytest tests/infolead-claude-subscription-router/ -v --tb=short" > "$UNIT_OUTPUT" 2>&1; then
    UNIT_RESULT=$(tail -1 "$UNIT_OUTPUT" | grep -oP '\d+ passed' | grep -oP '\d+' || echo "0")
    echo -e "${GREEN}✓ Unit tests passed: $UNIT_RESULT${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + UNIT_RESULT))
else
    # Extract passed/failed counts
    UNIT_PASSED=$(grep -oP '\d+(?= passed)' "$UNIT_OUTPUT" | head -1 || echo "0")
    UNIT_FAILED=$(grep -oP '\d+(?= failed)' "$UNIT_OUTPUT" | head -1 || echo "0")
    echo -e "${RED}✗ Unit tests: $UNIT_PASSED passed, $UNIT_FAILED failed${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + UNIT_PASSED))
    TOTAL_FAILED=$((TOTAL_FAILED + UNIT_FAILED))
fi
rm -f "$UNIT_OUTPUT"
SUITES_RUN=$((SUITES_RUN + 1))

echo ""

# ============================================================================
# Suite 2: Hook Tests (bash)
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Suite 2: Hook Tests (bash)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

HOOK_OUTPUT=$(mktemp)
if ./tests/infolead-claude-subscription-router/test_hooks.sh > "$HOOK_OUTPUT" 2>&1; then
    HOOK_PASSED=$(grep -oP '\d+(?= passed)' "$HOOK_OUTPUT" | head -1 || echo "10")
    echo -e "${GREEN}✓ Hook tests passed: $HOOK_PASSED${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + HOOK_PASSED))
else
    HOOK_PASSED=$(grep -oP '\d+(?= passed)' "$HOOK_OUTPUT" | head -1 || echo "0")
    HOOK_FAILED=$(grep -oP '\d+(?= failed)' "$HOOK_OUTPUT" | head -1 || echo "0")
    echo -e "${RED}✗ Hook tests: $HOOK_PASSED passed, $HOOK_FAILED failed${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + HOOK_PASSED))
    TOTAL_FAILED=$((TOTAL_FAILED + HOOK_FAILED))
    # Show failures
    grep -A1 "FAIL:" "$HOOK_OUTPUT" | head -20 || true
fi
rm -f "$HOOK_OUTPUT"
SUITES_RUN=$((SUITES_RUN + 1))

echo ""

# ============================================================================
# Suite 3: E2E Plugin Integration Tests (bash)
# ============================================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Suite 3: E2E Plugin Integration Tests (bash)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

E2E_OUTPUT=$(mktemp)
if ./tests/infolead-claude-subscription-router/test_e2e_plugin.sh > "$E2E_OUTPUT" 2>&1; then
    E2E_PASSED=$(grep -oP 'Passed: \K\d+' "$E2E_OUTPUT" | head -1 || echo "12")
    echo -e "${GREEN}✓ E2E tests passed: $E2E_PASSED${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + E2E_PASSED))
else
    E2E_PASSED=$(grep -oP 'Passed: \K\d+' "$E2E_OUTPUT" | head -1 || echo "0")
    E2E_FAILED=$(grep -oP 'Failed: \K\d+' "$E2E_OUTPUT" | head -1 || echo "0")
    echo -e "${RED}✗ E2E tests: $E2E_PASSED passed, $E2E_FAILED failed${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + E2E_PASSED))
    TOTAL_FAILED=$((TOTAL_FAILED + E2E_FAILED))
    # Show failures
    grep -A1 "FAIL:" "$E2E_OUTPUT" | head -20 || true
fi
rm -f "$E2E_OUTPUT"
SUITES_RUN=$((SUITES_RUN + 1))

echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      FINAL RESULTS                            ║${NC}"
echo -e "${BLUE}╠═══════════════════════════════════════════════════════════════╣${NC}"

TOTAL=$((TOTAL_PASSED + TOTAL_FAILED))

if [[ $TOTAL_FAILED -eq 0 ]]; then
    echo -e "${BLUE}║  ${GREEN}✓ ALL $TOTAL TESTS PASSED${NC}                                      ${BLUE}║${NC}"
else
    echo -e "${BLUE}║  ${RED}✗ $TOTAL_FAILED TESTS FAILED${NC}                                         ${BLUE}║${NC}"
fi

echo -e "${BLUE}║                                                               ║${NC}"
echo -e "${BLUE}║  Suites run: $SUITES_RUN                                                   ║${NC}"
echo -e "${BLUE}║  Total passed: $TOTAL_PASSED                                                ║${NC}"
echo -e "${BLUE}║  Total failed: $TOTAL_FAILED                                                 ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"

if [[ $TOTAL_FAILED -gt 0 ]]; then
    exit 1
else
    exit 0
fi
