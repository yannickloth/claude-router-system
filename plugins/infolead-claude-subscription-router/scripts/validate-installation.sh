#!/usr/bin/env bash
#
# validate-installation.sh
#
# Quick validation script to verify router plugin installation and multi-project support
#
# Usage: ./scripts/validate-installation.sh

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Router Plugin Installation Validation"
echo "═══════════════════════════════════════════════════════════"
echo ""

ISSUES=0

# Check 1: Plugin structure
echo -n "✓ Checking plugin structure... "
if [ -f "$PLUGIN_ROOT/plugin.json" ] && [ -d "$PLUGIN_ROOT/hooks" ] && [ -d "$PLUGIN_ROOT/implementation" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    echo "  Missing required files/directories"
    ISSUES=$((ISSUES + 1))
fi

# Check 2: Common functions
echo -n "✓ Checking common-functions.sh... "
if [ -f "$PLUGIN_ROOT/hooks/common-functions.sh" ]; then
    # Check for new multi-project functions
    if grep -q "detect_project_root" "$PLUGIN_ROOT/hooks/common-functions.sh" && \
       grep -q "get_project_id" "$PLUGIN_ROOT/hooks/common-functions.sh" && \
       grep -q "get_project_data_dir" "$PLUGIN_ROOT/hooks/common-functions.sh"; then
        echo -e "${GREEN}OK (v1.7.0 functions present)${NC}"
    else
        echo -e "${YELLOW}WARNING${NC} - Multi-project functions missing"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${RED}FAILED${NC}"
    ISSUES=$((ISSUES + 1))
fi

# Check 3: Hook scripts
echo -n "✓ Checking hook scripts... "
HOOK_COUNT=$(find "$PLUGIN_ROOT/hooks" -name "*.sh" -type f | wc -l)
if [ "$HOOK_COUNT" -ge 8 ]; then
    echo -e "${GREEN}OK ($HOOK_COUNT scripts found)${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - Expected at least 8 hook scripts, found $HOOK_COUNT"
fi

# Check 4: Hook executability
echo -n "✓ Checking hook permissions... "
NON_EXEC=$(find "$PLUGIN_ROOT/hooks" -name "*.sh" -type f ! -perm -u+x | wc -l)
if [ "$NON_EXEC" -eq 0 ]; then
    echo -e "${GREEN}OK (all scripts executable)${NC}"
else
    echo -e "${RED}FAILED${NC} - $NON_EXEC scripts not executable"
    ISSUES=$((ISSUES + 1))
fi

# Check 5: Dependencies
echo -n "✓ Checking dependencies... "
MISSING=""
command -v python3 &>/dev/null || MISSING="python3 "
command -v jq &>/dev/null || MISSING="${MISSING}jq "
if [ -z "$MISSING" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - Missing: $MISSING"
    echo "  Plugin will show user-friendly error messages"
fi

# Check 6: Python modules
echo -n "✓ Checking Python implementation... "
if [ -f "$PLUGIN_ROOT/implementation/routing_core.py" ] && \
   [ -f "$PLUGIN_ROOT/implementation/adaptive_orchestrator.py" ]; then
    # Check for project-aware config loading
    if grep -q "detect_project_config" "$PLUGIN_ROOT/implementation/adaptive_orchestrator.py"; then
        echo -e "${GREEN}OK (v1.7.0 project config support)${NC}"
    else
        echo -e "${YELLOW}WARNING${NC} - Project config detection not found"
    fi
else
    echo -e "${RED}FAILED${NC}"
    ISSUES=$((ISSUES + 1))
fi

# Check 7: Version
echo -n "✓ Checking plugin version... "
VERSION=$(jq -r '.version' "$PLUGIN_ROOT/plugin.json" 2>/dev/null || echo "unknown")
if [ "$VERSION" = "1.7.1" ]; then
    echo -e "${GREEN}OK (v$VERSION)${NC}"
elif [ "$VERSION" = "unknown" ]; then
    echo -e "${RED}FAILED${NC} - Cannot read version"
    ISSUES=$((ISSUES + 1))
else
    echo -e "${YELLOW}WARNING${NC} - Expected v1.7.1, found v$VERSION"
fi

# Check 8: Migration script
echo -n "✓ Checking migration script... "
if [ -f "$PLUGIN_ROOT/scripts/migrate-to-project-isolation.sh" ] && \
   [ -x "$PLUGIN_ROOT/scripts/migrate-to-project-isolation.sh" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - Migration script missing or not executable"
fi

# Check 9: Documentation
echo -n "✓ Checking documentation... "
if [ -f "$PLUGIN_ROOT/docs/MULTI-PROJECT-ARCHITECTURE.md" ] && \
   [ -f "$PLUGIN_ROOT/CHANGELOG.md" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - Some documentation missing"
fi

# Check 10: Project detection test
echo -n "✓ Testing project detection... "
if [ -f "$PLUGIN_ROOT/hooks/common-functions.sh" ]; then
    # Source functions and test
    # shellcheck source=../hooks/common-functions.sh
    source "$PLUGIN_ROOT/hooks/common-functions.sh"

    PROJECT_ROOT=$(detect_project_root || echo "")
    if [ -n "$PROJECT_ROOT" ]; then
        PROJECT_ID=$(get_project_id)
        echo -e "${GREEN}OK${NC}"
        echo "    Project root: $PROJECT_ROOT"
        echo "    Project ID: $PROJECT_ID"
    else
        echo -e "${YELLOW}INFO${NC} - No .claude directory found (will use 'global' fallback)"
    fi
else
    echo -e "${RED}FAILED${NC}"
    ISSUES=$((ISSUES + 1))
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
if [ $ISSUES -eq 0 ]; then
    echo -e "  ${GREEN}✓ All checks passed!${NC}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo "  1. Test in a real project with Claude Code"
    echo "  2. If upgrading from v1.6.x, run migration script:"
    echo "     $PLUGIN_ROOT/scripts/migrate-to-project-isolation.sh"
    echo "  3. See MULTI-PROJECT-ARCHITECTURE.md for complete guide"
    echo ""
    exit 0
else
    echo -e "  ${RED}✗ Found $ISSUES issue(s)${NC}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Please fix the issues above before using the plugin."
    echo ""
    exit 1
fi
