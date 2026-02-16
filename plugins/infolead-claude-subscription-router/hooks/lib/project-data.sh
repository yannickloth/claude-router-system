#!/bin/bash
# Project Data Directory Management for Router Plugin Hooks
# Functions for managing project-specific data directories
#
# Change Driver: γ_DATA (Project Data Storage)
# Purity: 1.0 (single change driver)

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
