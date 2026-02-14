#!/bin/bash
# Common Functions for Router Plugin Hooks
# Source this file in hooks that need dependency checking
#
# Change Driver: HOOK_INFRASTRUCTURE

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

# Detect current project root directory
# Looks for .claude directory going up from PWD
# Usage: detect_project_root
# Returns: Prints project root path to stdout, or empty if not found
# Exit code: 0 if found, 1 if not found
detect_project_root() {
    # Start from current directory (PWD set by Claude Code)
    local dir="${PWD:-$(pwd)}"

    # If CLAUDE_PROJECT_ROOT is set (future Claude Code feature), use it
    if [ -n "${CLAUDE_PROJECT_ROOT:-}" ]; then
        echo "$CLAUDE_PROJECT_ROOT"
        return 0
    fi

    # Walk up directory tree looking for .claude directory
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.claude" ]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done

    # Not found - return empty
    return 1
}

# Get project identifier (hash of project root path)
# This creates a stable, unique ID for each project
# Usage: get_project_id
# Returns: Prints 16-character hex ID to stdout
get_project_id() {
    local project_root
    project_root=$(detect_project_root)

    if [ -z "$project_root" ]; then
        # No project detected - use "global" as fallback
        echo "global"
        return 0
    fi

    # Generate stable hash of project root path
    echo -n "$project_root" | sha256sum | cut -d' ' -f1 | head -c16
}

# Get project-specific directory for plugin data
# Usage: get_project_data_dir <subdir>
# Example: get_project_data_dir "state" → ~/.claude/.../projects/abc123/state/
# Returns: Prints path to stdout and ensures directory exists
get_project_data_dir() {
    local subdir="$1"
    local project_id
    project_id=$(get_project_id)

    local base_dir="$HOME/.claude/infolead-claude-subscription-router"
    local project_dir="$base_dir/projects/$project_id/$subdir"

    # Ensure directory exists with proper permissions
    mkdir -p "$project_dir"
    chmod 700 "$project_dir"

    echo "$project_dir"
}

# Check if router is enabled for current project
# Reads .claude/settings.json and .claude/settings.local.json
# Usage: is_router_enabled
# Returns: 0 if enabled (default), 1 if explicitly disabled
is_router_enabled() {
    local project_root
    project_root=$(detect_project_root)

    # If no project detected, router is enabled globally
    if [ -z "$project_root" ]; then
        return 0
    fi

    # Check project settings (takes precedence)
    local settings_files=(
        "$project_root/.claude/settings.local.json"
        "$project_root/.claude/settings.json"
    )

    for settings_file in "${settings_files[@]}"; do
        if [ -f "$settings_file" ]; then
            # Check for "plugins.router.enabled": false
            # Note: Use 'if . == null' to avoid treating boolean false as falsy
            local enabled
            enabled=$(jq -r 'if .plugins.router.enabled == null then "true" elif .plugins.router.enabled == false then "false" else "true" end' "$settings_file" 2>/dev/null)

            if [ "$enabled" = "false" ]; then
                return 1  # Explicitly disabled
            fi
        fi
    done

    # Default: enabled
    return 0
}

# Load project-specific or global config file
# Looks for config in project first, falls back to global
# Usage: load_config_file <filename>
# Example: load_config_file "adaptive-orchestration.yaml"
# Returns: Prints path to config file, or empty if not found
load_config_file() {
    local filename="$1"
    local project_root
    project_root=$(detect_project_root)

    # Priority 1: Project-specific config
    if [ -n "$project_root" ] && [ -f "$project_root/.claude/$filename" ]; then
        echo "$project_root/.claude/$filename"
        return 0
    fi

    # Priority 2: Global plugin config
    local plugin_root="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"
    if [ -f "$plugin_root/config/$filename" ]; then
        echo "$plugin_root/config/$filename"
        return 0
    fi

    # Priority 3: Global user config
    if [ -f "$HOME/.claude/infolead-claude-subscription-router/$filename" ]; then
        echo "$HOME/.claude/infolead-claude-subscription-router/$filename"
        return 0
    fi

    # Not found
    return 1
}
