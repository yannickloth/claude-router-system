#!/bin/bash
# Common Functions for Router Plugin Hooks
# BACKWARD COMPATIBILITY WRAPPER - Sources hook-preamble.sh
#
# This file is maintained for backward compatibility with existing hooks.
# All functionality has been refactored into IVP-compliant modules in hooks/lib/
#
# Change Driver: γ_INFRA (Hook Infrastructure)

# Source the hook preamble which loads all library modules
source "$(dirname "${BASH_SOURCE[0]}")/hook-preamble.sh"
