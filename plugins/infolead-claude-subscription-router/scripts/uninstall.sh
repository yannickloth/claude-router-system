#!/usr/bin/env bash
#
# uninstall.sh
#
# Complete uninstallation script for infolead-claude-subscription-router plugin
#
# Removes:
# - Plugin hooks from settings.json (all scopes)
# - Write/Edit permissions from settings.json (all scopes)
# - Overnight execution system (skills, systemd, state/logs)
# - Plugin symlink (if manually installed)
# - Agent symlinks (if manually installed)
#
# Usage:
#   ./scripts/uninstall.sh [--dry-run] [--keep-data]
#
# Change Driver: INSTALLATION
# Changes when: Installation process or component paths change

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine plugin root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_NAME="infolead-claude-subscription-router"

# Parse arguments
DRY_RUN=false
KEEP_DATA=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --keep-data)
            KEEP_DATA=true
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--keep-data]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be removed without making changes"
            echo "  --keep-data  Keep metrics, state, and logs (only remove installed components)"
            echo ""
            echo "Removes:"
            echo "  • Plugin hooks from settings.json (local, project, global)"
            echo "  • Write/Edit permissions from settings.json (all scopes)"
            echo "  • Overnight execution (skills, systemd, state/logs)"
            echo "  • Plugin symlink (if manually installed)"
            echo "  • Agent symlinks (if manually installed)"
            echo ""
            exit 0
            ;;
    esac
done

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Find project root (look for .claude directory going up)
find_project_root() {
    local dir="$PLUGIN_ROOT"
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.claude" && ! "$dir" =~ /plugins/ ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# Remove hooks and permissions from settings file
remove_from_settings() {
    local settings_file="$1"
    local scope_desc="$2"

    if [[ ! -f "$settings_file" ]]; then
        log_info "No settings file at $settings_file (skipping)"
        return 0
    fi

    log_info "Removing plugin hooks and permissions from $scope_desc"

    if [[ "$DRY_RUN" == "false" ]]; then
        # Create backup
        local backup_file="${settings_file}.backup.$(date +%Y%m%d-%H%M%S)"
        cp "$settings_file" "$backup_file"
        log_info "Created backup: $backup_file"
    fi

    # Use setup-hooks-workaround.sh --revert for consistent removal
    local scope_flag=""
    case "$scope_desc" in
        *local*)
            scope_flag="--local"
            ;;
        *project*)
            scope_flag="--project"
            ;;
        *global*)
            scope_flag="--global"
            ;;
    esac

    if [[ -n "$scope_flag" && -f "$PLUGIN_ROOT/scripts/setup-hooks-workaround.sh" ]]; then
        local revert_args="$scope_flag --revert"
        if [[ "$DRY_RUN" == "true" ]]; then
            revert_args="$revert_args --dry-run"
        fi
        bash "$PLUGIN_ROOT/scripts/setup-hooks-workaround.sh" $revert_args || true
    fi
}

# Remove overnight execution system
remove_overnight_execution() {
    log_info "Removing overnight execution system"

    local systemd_user_dir="$HOME/.config/systemd/user"
    local skills_dir="$HOME/.claude/skills"
    local state_dir="$HOME/.claude/$PLUGIN_NAME/state"
    local logs_dir="$HOME/.claude/$PLUGIN_NAME/logs"
    local metrics_dir="$HOME/.claude/$PLUGIN_NAME/metrics"

    # Stop and disable systemd timer
    if systemctl --user is-enabled claude-overnight-executor.timer &>/dev/null; then
        log_info "Stopping and disabling systemd timer"
        if [[ "$DRY_RUN" == "false" ]]; then
            systemctl --user stop claude-overnight-executor.timer || true
            systemctl --user disable claude-overnight-executor.timer || true
        fi
    fi

    # Remove systemd files
    if [[ -f "$systemd_user_dir/claude-overnight-executor.timer" ]]; then
        log_info "Removing systemd timer: $systemd_user_dir/claude-overnight-executor.timer"
        if [[ "$DRY_RUN" == "false" ]]; then
            rm "$systemd_user_dir/claude-overnight-executor.timer"
        fi
    fi

    if [[ -f "$systemd_user_dir/claude-overnight-executor.service" ]]; then
        log_info "Removing systemd service: $systemd_user_dir/claude-overnight-executor.service"
        if [[ "$DRY_RUN" == "false" ]]; then
            rm "$systemd_user_dir/claude-overnight-executor.service"
        fi
    fi

    # Reload systemd daemon
    if [[ "$DRY_RUN" == "false" ]] && command -v systemctl &>/dev/null; then
        log_info "Reloading systemd user daemon"
        systemctl --user daemon-reload || true
    fi

    # Remove skills
    if [[ -f "$skills_dir/overnight.md" ]]; then
        log_info "Removing skill: overnight.md"
        if [[ "$DRY_RUN" == "false" ]]; then
            rm "$skills_dir/overnight.md"
        fi
    fi

    if [[ -f "$skills_dir/quota.md" ]]; then
        log_info "Removing skill: quota.md"
        if [[ "$DRY_RUN" == "false" ]]; then
            rm "$skills_dir/quota.md"
        fi
    fi

    # Remove state/logs/metrics (unless --keep-data)
    if [[ "$KEEP_DATA" == "false" ]]; then
        for dir in "$state_dir" "$logs_dir" "$metrics_dir"; do
            if [[ -d "$dir" ]]; then
                log_warn "Removing directory: $dir"
                if [[ "$DRY_RUN" == "false" ]]; then
                    rm -rf "$dir"
                fi
            fi
        done

        # Remove parent directory if empty
        local parent_dir="$HOME/.claude/$PLUGIN_NAME"
        if [[ -d "$parent_dir" && -z "$(ls -A "$parent_dir" 2>/dev/null)" ]]; then
            log_info "Removing empty directory: $parent_dir"
            if [[ "$DRY_RUN" == "false" ]]; then
                rmdir "$parent_dir"
            fi
        fi
    else
        log_info "Keeping data directories (--keep-data specified)"
    fi
}

# Remove plugin symlink (manual installation)
remove_plugin_symlink() {
    local plugin_link="$HOME/.claude/plugins/$PLUGIN_NAME"

    if [[ -L "$plugin_link" ]]; then
        log_info "Removing plugin symlink: $plugin_link"
        if [[ "$DRY_RUN" == "false" ]]; then
            rm "$plugin_link"
        fi
    elif [[ -d "$plugin_link" && ! -L "$plugin_link" ]]; then
        log_warn "Plugin directory exists but is not a symlink: $plugin_link"
        log_warn "This may be a plugin marketplace installation - use /plugin uninstall instead"
    fi
}

# Remove agent symlinks (manual installation)
remove_agent_symlinks() {
    local agents_dir="$HOME/.claude/agents"

    if [[ ! -d "$agents_dir" ]]; then
        return 0
    fi

    log_info "Checking for agent symlinks in $agents_dir"

    local count=0
    for link in "$agents_dir"/*.md; do
        if [[ -L "$link" ]]; then
            local target=$(readlink "$link")
            if [[ "$target" == *"$PLUGIN_NAME"* ]]; then
                log_info "Removing agent symlink: $(basename "$link")"
                if [[ "$DRY_RUN" == "false" ]]; then
                    rm "$link"
                fi
                ((count++))
            fi
        fi
    done

    if [[ $count -eq 0 ]]; then
        log_info "No agent symlinks found"
    fi
}

# Main uninstall process
main() {
    echo ""
    echo "========================================"
    echo "  Plugin Uninstallation"
    echo "========================================"
    echo ""
    echo "Plugin: $PLUGIN_NAME"
    echo "Root:   $PLUGIN_ROOT"
    echo ""

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    # Confirm
    if [[ "$DRY_RUN" == "false" ]]; then
        echo "This will remove:"
        echo "  • Plugin hooks from all settings files"
        echo "  • Write/Edit permissions from all settings files"
        echo "  • Overnight execution system (skills, systemd)"
        echo "  • Plugin and agent symlinks (if manually installed)"
        if [[ "$KEEP_DATA" == "false" ]]; then
            echo "  • State, logs, and metrics data"
        fi
        echo ""
        read -p "Continue? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Uninstallation cancelled"
            exit 0
        fi
        echo ""
    fi

    # Step 1: Remove hooks and permissions from all scopes
    log_info "Step 1: Removing hooks and permissions from settings files"
    echo ""

    PROJECT_ROOT=$(find_project_root) || true

    if [[ -n "$PROJECT_ROOT" ]]; then
        remove_from_settings "$PROJECT_ROOT/.claude/settings.local.json" "user-local settings"
        echo ""
        remove_from_settings "$PROJECT_ROOT/.claude/settings.json" "project settings"
        echo ""
    fi

    remove_from_settings "$HOME/.claude/settings.json" "global settings"
    echo ""

    # Step 2: Remove overnight execution system
    log_info "Step 2: Removing overnight execution system"
    echo ""
    remove_overnight_execution
    echo ""

    # Step 3: Remove plugin and agent symlinks
    log_info "Step 3: Removing plugin and agent symlinks"
    echo ""
    remove_plugin_symlink
    echo ""
    remove_agent_symlinks
    echo ""

    # Done
    echo "========================================"
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run complete - no changes made"
    else
        log_success "Uninstallation complete!"
        echo ""
        echo "Next steps:"
        echo "  1. Restart Claude Code to apply changes"
        if [[ "$KEEP_DATA" == "false" ]]; then
            echo "  2. All plugin data has been removed"
        else
            echo "  2. Plugin data preserved in ~/.claude/$PLUGIN_NAME/"
        fi
        echo "  3. To reinstall: /plugin install $PLUGIN_NAME"
    fi
    echo "========================================"
    echo ""
}

main "$@"
