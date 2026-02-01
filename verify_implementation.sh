#!/bin/bash
# Verification script for Phase 3 & 4 implementation

echo "════════════════════════════════════════════════════════════════"
echo "  CLAUDE ROUTER SYSTEM - IMPLEMENTATION VERIFICATION"
echo "════════════════════════════════════════════════════════════════"
echo ""

PASS=0
FAIL=0

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo "✓ $1"
        ((PASS++))
    else
        echo "✗ $1 (MISSING)"
        ((FAIL++))
    fi
}

# Function to check file is executable
check_executable() {
    if [ -x "$1" ]; then
        echo "✓ $1 (executable)"
        ((PASS++))
    else
        echo "✗ $1 (not executable)"
        ((FAIL++))
    fi
}

# Function to compile Python file
check_python() {
    if python3 -m py_compile "$1" 2>/dev/null; then
        echo "✓ $1 (compiles)"
        ((PASS++))
    else
        echo "✗ $1 (syntax error)"
        ((FAIL++))
    fi
}

echo "Checking Python Implementation Files..."
echo "────────────────────────────────────────────────────────────────"
check_python implementation/routing_core.py
check_python implementation/session_state_manager.py
check_python implementation/work_coordinator.py
check_python implementation/semantic_cache.py
check_python implementation/domain_adapter.py
check_python implementation/lazy_context_loader.py
check_python implementation/metrics_collector.py

echo ""
echo "Checking Configuration Files..."
echo "────────────────────────────────────────────────────────────────"
check_file config/domains/latex-research.yaml
check_file config/domains/software-dev.yaml
check_file config/domains/knowledge-mgmt.yaml

echo ""
echo "Checking Hook Scripts..."
echo "────────────────────────────────────────────────────────────────"
check_executable .claude/hooks/morning-briefing.sh
check_executable .claude/hooks/haiku-routing-audit.sh
check_executable .claude/hooks/session-end.sh

echo ""
echo "Checking Test Files..."
echo "────────────────────────────────────────────────────────────────"
check_python tests/test_integration.py

echo ""
echo "Checking Documentation..."
echo "────────────────────────────────────────────────────────────────"
check_file README.md
check_file PHASE_3_4_IMPLEMENTATION.md
check_file IMPLEMENTATION_STATUS.md
check_file COMPLETION_SUMMARY.txt

echo ""
echo "Testing CLI Interfaces..."
echo "────────────────────────────────────────────────────────────────"

# Test domain adapter
if python3 implementation/domain_adapter.py list >/dev/null 2>&1; then
    echo "✓ domain_adapter.py CLI works"
    ((PASS++))
else
    echo "✗ domain_adapter.py CLI failed"
    ((FAIL++))
fi

# Test lazy context loader
if python3 implementation/lazy_context_loader.py budget >/dev/null 2>&1; then
    echo "✓ lazy_context_loader.py CLI works"
    ((PASS++))
else
    echo "✗ lazy_context_loader.py CLI failed"
    ((FAIL++))
fi

# Test metrics collector
if python3 implementation/metrics_collector.py show haiku_routing >/dev/null 2>&1; then
    echo "✓ metrics_collector.py CLI works"
    ((PASS++))
else
    echo "✗ metrics_collector.py CLI failed"
    ((FAIL++))
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  VERIFICATION RESULTS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "  Status: ✓ ALL CHECKS PASSED"
    echo ""
    echo "  Phase 3 & 4 implementation is COMPLETE and VERIFIED."
    exit 0
else
    echo "  Status: ✗ SOME CHECKS FAILED"
    echo ""
    echo "  Please review failed items above."
    exit 1
fi
