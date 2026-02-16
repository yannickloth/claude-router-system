#!/bin/bash
# Configuration Management for Router Plugin Hooks
# Functions for loading config files and checking router enabled status
#
# Change Driver: γ_CONF (Configuration Management)
# Purity: 1.0 (single change driver)

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

    # Check for jq availability - required for settings parsing
    if ! command -v jq &> /dev/null; then
        # jq not available - can't check settings, assume enabled (safe default)
        return 0
    fi

    # Check jq version - need 1.6+ for advanced features (used elsewhere)
    # Note: This is a soft check - we only warn if version check fails
    local jq_version
    jq_version=$(jq --version 2>/dev/null | sed -n 's/^jq-\([0-9]*\.[0-9]*\).*/\1/p' || echo "unknown")
    if [ "$jq_version" != "unknown" ]; then
        local major minor
        major=$(echo "$jq_version" | cut -d. -f1)
        minor=$(echo "$jq_version" | cut -d. -f2)
        if [ "$major" -lt 1 ] || ([ "$major" -eq 1 ] && [ "$minor" -lt 6 ]); then
            echo "⚠️  Warning: jq version $jq_version detected. Some features require jq 1.6+. Please upgrade." >&2
        fi
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
