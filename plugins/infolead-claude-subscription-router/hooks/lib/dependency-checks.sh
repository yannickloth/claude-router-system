#!/bin/bash
# Dependency Checks for Router Plugin Hooks
# Functions for checking runtime dependencies (Python, PyYAML, jq)
#
# Change Driver: γ_DEP (Dependency Management)
# Purity: 1.0 (single change driver)

# Check for Python 3 availability
# Usage: check_python3 [required|optional]
# Returns: 0 if available, 1 if not available
# Side effect: Prints warning message if missing and required
check_python3() {
    local requirement="${1:-required}"

    if ! command -v python3 &> /dev/null; then
        if [ "$requirement" = "required" ]; then
            cat >&2 <<'EOF'
⚠️  PLUGIN WARNING: infolead-claude-subscription-router

Missing dependency: Python 3.7+

This plugin requires Python 3 for intelligent routing and cost optimization.

Install Python:
  • Ubuntu/Debian: sudo apt-get install python3 python3-pip
  • macOS: brew install python3
  • Arch Linux: sudo pacman -S python
  • Fedora: sudo dnf install python3

Then install PyYAML: pip3 install PyYAML

Your request will be processed without routing optimization until fixed.
EOF
        fi
        return 1
    fi
    return 0
}

# Check for PyYAML Python package
# Usage: check_pyyaml [required|optional]
# Returns: 0 if available, 1 if not available
# Side effect: Prints warning message if missing and required
check_pyyaml() {
    local requirement="${1:-required}"

    if ! python3 -c "import yaml" 2>/dev/null; then
        if [ "$requirement" = "required" ]; then
            cat >&2 <<'EOF'
⚠️  PLUGIN WARNING: infolead-claude-subscription-router

Missing Python package: PyYAML

Install with: pip3 install PyYAML

Your request will be processed without routing optimization until fixed.
EOF
        fi
        return 1
    fi
    return 0
}

# Check for jq availability
# Usage: check_jq [required|optional]
# Returns: 0 if available, 1 if not available
# Side effect: Prints warning message if missing
check_jq() {
    local requirement="${1:-required}"

    if ! command -v jq &> /dev/null; then
        if [ "$requirement" = "required" ]; then
            cat >&2 <<'EOF'
⚠️  PLUGIN WARNING: infolead-claude-subscription-router

Missing dependency: jq (JSON processor)

This plugin requires jq for processing JSON data.

Install jq:
  • Ubuntu/Debian: sudo apt-get install jq
  • macOS: brew install jq
  • Arch Linux: sudo pacman -S jq
  • Fedora: sudo dnf install jq

Your request will be processed with limited functionality until fixed.
EOF
        elif [ "$requirement" = "optional" ]; then
            echo "⚠️  Note: jq not installed. Some features may have limited functionality." >&2
        fi
        return 1
    fi
    return 0
}

# Check all dependencies for routing hooks
# Usage: check_routing_dependencies
# Returns: 0 if all available, 1 if any missing
# Side effect: Prints appropriate warning messages
check_routing_dependencies() {
    local all_ok=0

    if ! check_python3 "required"; then
        all_ok=1
    fi

    if ! check_pyyaml "required"; then
        all_ok=1
    fi

    if ! check_jq "required"; then
        all_ok=1
    fi

    return $all_ok
}
