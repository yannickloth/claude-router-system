#!/bin/bash
# Hook Preamble for Router Plugin
# Standard initialization for all router hooks
# Sources all library modules and performs common setup
#
# Change Driver: γ_INFRA (Hook Infrastructure)
# Purity: 1.0 (single change driver)

# Get the directory where this script lives
HOOK_LIB_DIR="$(dirname "${BASH_SOURCE[0]}")/lib"

# Source all library modules in dependency order
# Note: project-detection.sh must be sourced before project-data.sh and config-management.sh
source "$HOOK_LIB_DIR/dependency-checks.sh"
source "$HOOK_LIB_DIR/project-detection.sh"
source "$HOOK_LIB_DIR/project-data.sh"
source "$HOOK_LIB_DIR/config-management.sh"

# Check if router is enabled for current project
# If disabled, exit silently (no-op for the hook)
if ! is_router_enabled; then
    exit 0
fi
