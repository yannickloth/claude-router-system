#!/bin/bash
# Project Detection for Router Plugin Hooks
# Functions for detecting project root and generating project IDs
#
# Change Driver: γ_PROJ (Project Detection Logic)
# Purity: 1.0 (single change driver)

# Cache for project root detection (optimization to avoid repeated traversals)
_PROJECT_ROOT_CACHE=""

# Detect current project root directory
# Looks for .claude directory going up from PWD
# Usage: detect_project_root
# Returns: Prints project root path to stdout, or empty if not found
# Exit code: 0 if found, 1 if not found
detect_project_root() {
    # Return cached result if available (optimization: avoid repeated tree walks)
    if [ -n "$_PROJECT_ROOT_CACHE" ]; then
        echo "$_PROJECT_ROOT_CACHE"
        return 0
    fi
    # Start from current directory (PWD set by Claude Code)
    local dir="${PWD:-$(pwd)}"

    # If CLAUDE_PROJECT_ROOT is set (future Claude Code feature), validate and use it
    if [ -n "${CLAUDE_PROJECT_ROOT:-}" ]; then
        # Validate path exists
        if [ ! -d "$CLAUDE_PROJECT_ROOT" ]; then
            echo "⚠️  Warning: CLAUDE_PROJECT_ROOT set but directory does not exist: $CLAUDE_PROJECT_ROOT" >&2
            # Fall through to auto-detection
        else
            # Validate contains .claude directory
            if [ ! -d "$CLAUDE_PROJECT_ROOT/.claude" ]; then
                echo "⚠️  Warning: CLAUDE_PROJECT_ROOT set but does not contain .claude directory: $CLAUDE_PROJECT_ROOT" >&2
                # Fall through to auto-detection
            else
                # Path traversal protection: ensure it's an absolute path
                case "$CLAUDE_PROJECT_ROOT" in
                    /*)
                        # Absolute path - safe to use
                        echo "$CLAUDE_PROJECT_ROOT"
                        return 0
                        ;;
                    *)
                        echo "⚠️  Warning: CLAUDE_PROJECT_ROOT must be absolute path, got: $CLAUDE_PROJECT_ROOT" >&2
                        # Fall through to auto-detection
                        ;;
                esac
            fi
        fi
    fi

    # Walk up directory tree looking for .claude directory
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.claude" ]; then
            # Cache the result before returning (optimization)
            _PROJECT_ROOT_CACHE="$dir"
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
