#!/usr/bin/env bash
#
# update.sh
#
# Update script for infolead-claude-subscription-router plugin
#
# Updates:
# - Plugin code (git pull if in repo)
# - Hooks in settings.json (all scopes where currently installed)
# - Skills (if changed)
# - Systemd services (if changed and currently installed)
#
# Usage:
#   ./scripts/update.sh [--dry-run] [--skip-git] [--force]
#
# Change Driver: INSTALLATION
# Changes when: Update process or component paths change

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
SKIP_GIT=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --skip-git)
            SKIP_GIT=true
            ;;
        --force)
            FORCE=true
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--skip-git] [--force]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be updated without making changes"
            echo "  --skip-git   Don't check for or pull git updates"
            echo "  --force      Force update hooks/permissions even if unchanged"
            echo ""
            echo "Updates:"
            echo "  • Plugin code (git pull if in repo)"
            echo "  • Hooks in settings.json (all scopes where currently installed)"
            echo "  • Skills (if changed and installed)"
            echo "  • Systemd services (if changed and installed)"
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

# Check if plugin is in a git repository
is_git_repo() {
    git -C "$PLUGIN_ROOT" rev-parse --git-dir >/dev/null 2>&1
}

# Update plugin code via git
update_git_repo() {
    if [[ "$SKIP_GIT" == "true" ]]; then
        log_info "Skipping git update (--skip-git specified)"
        return 0
    fi

    if ! is_git_repo; then
        log_info "Plugin is not in a git repository (skipping git update)"
        return 0
    fi

    log_info "Checking for plugin updates"

    if [[ "$DRY_RUN" == "false" ]]; then
        local current_commit=$(git -C "$PLUGIN_ROOT" rev-parse HEAD)

        # Fetch updates
        log_info "Fetching latest changes"
        git -C "$PLUGIN_ROOT" fetch origin || {
            log_warn "Failed to fetch updates - continuing with current version"
            return 0
        }

        # Check if updates available
        local remote_commit=$(git -C "$PLUGIN_ROOT" rev-parse origin/main 2>/dev/null || \
                             git -C "$PLUGIN_ROOT" rev-parse origin/master 2>/dev/null || \
                             echo "$current_commit")

        if [[ "$current_commit" == "$remote_commit" ]]; then
            log_success "Plugin is already up to date"
            return 0
        fi

        # Pull updates
        log_info "Pulling latest changes"
        git -C "$PLUGIN_ROOT" pull || {
            log_error "Failed to pull updates"
            return 1
        }

        local new_commit=$(git -C "$PLUGIN_ROOT" rev-parse HEAD)
        log_success "Updated from $current_commit to $new_commit"

        # Show changelog
        echo ""
        log_info "Changes:"
        git -C "$PLUGIN_ROOT" log --oneline "$current_commit..$new_commit" | head -10
        echo ""
    else
        log_info "[DRY RUN] Would check for and pull git updates"
    fi
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

# Check if plugin hooks are installed in settings file
has_plugin_hooks() {
    local settings_file="$1"

    if [[ ! -f "$settings_file" ]]; then
        return 1
    fi

    grep -q "$PLUGIN_NAME" "$settings_file" 2>/dev/null
}

# Update hooks in settings file
update_settings_hooks() {
    local settings_file="$1"
    local scope_desc="$2"
    local scope_flag="$3"

    if [[ ! -f "$settings_file" ]]; then
        return 0
    fi

    if ! has_plugin_hooks "$settings_file" && [[ "$FORCE" == "false" ]]; then
        log_info "Plugin not installed in $scope_desc (skipping)"
        return 0
    fi

    log_info "Updating hooks and permissions in $scope_desc"

    if [[ "$DRY_RUN" == "false" ]]; then
        # Create backup
        local backup_file="${settings_file}.backup.$(date +%Y%m%d-%H%M%S)"
        cp "$settings_file" "$backup_file"
        log_info "Created backup: $backup_file"
    fi

    # Use setup-hooks-workaround.sh for consistent update
    if [[ -f "$PLUGIN_ROOT/scripts/setup-hooks-workaround.sh" ]]; then
        # First revert old hooks
        local revert_args="$scope_flag --revert"
        if [[ "$DRY_RUN" == "true" ]]; then
            revert_args="$revert_args --dry-run"
        fi
        bash "$PLUGIN_ROOT/scripts/setup-hooks-workaround.sh" $revert_args 2>/dev/null || true

        # Then install new hooks
        local install_args="$scope_flag"
        if [[ "$DRY_RUN" == "true" ]]; then
            install_args="$install_args --dry-run"
        fi
        bash "$PLUGIN_ROOT/scripts/setup-hooks-workaround.sh" $install_args || {
            log_warn "Failed to update hooks in $scope_desc"
            return 1
        }
    fi
}

# Update skills if they've changed
update_skills() {
    local skills_dir="$HOME/.claude/skills"

    if [[ ! -d "$skills_dir" ]]; then
        log_info "Skills directory not found (overnight execution not installed)"
        return 0
    fi

    log_info "Checking for skill updates"

    local updated=0

    for skill in overnight quota; do
        local source="$PLUGIN_ROOT/skills/${skill}.md"
        local dest="$skills_dir/${skill}.md"

        if [[ ! -f "$source" ]]; then
            continue
        fi

        if [[ ! -f "$dest" ]]; then
            if [[ "$FORCE" == "true" ]]; then
                log_info "Installing missing skill: $skill.md"
                if [[ "$DRY_RUN" == "false" ]]; then
                    cp "$source" "$dest"
                fi
                ((updated++))
            fi
            continue
        fi

        # Check if files differ
        if ! cmp -s "$source" "$dest"; then
            log_info "Updating skill: $skill.md"
            if [[ "$DRY_RUN" == "false" ]]; then
                cp "$source" "$dest"
            fi
            ((updated++))
        fi
    done

    if [[ $updated -eq 0 ]]; then
        log_success "Skills are up to date"
    else
        log_success "Updated $updated skill(s)"
    fi
}

# Update systemd services if they've changed
update_systemd_services() {
    local systemd_user_dir="$HOME/.config/systemd/user"

    if [[ ! -d "$systemd_user_dir" ]]; then
        log_info "Systemd user directory not found (overnight execution not installed)"
        return 0
    fi

    log_info "Checking for systemd service updates"

    local updated=0
    local needs_reload=false

    for file in service timer; do
        local filename="claude-overnight-executor.$file"
        local source="$PLUGIN_ROOT/systemd/$filename"
        local dest="$systemd_user_dir/$filename"

        if [[ ! -f "$source" ]]; then
            continue
        fi

        if [[ ! -f "$dest" ]]; then
            if [[ "$FORCE" == "true" ]]; then
                log_info "Installing missing systemd file: $filename"
                if [[ "$DRY_RUN" == "false" ]]; then
                    cp "$source" "$dest"
                    needs_reload=true
                fi
                ((updated++))
            fi
            continue
        fi

        # Check if files differ
        if ! cmp -s "$source" "$dest"; then
            log_info "Updating systemd file: $filename"
            if [[ "$DRY_RUN" == "false" ]]; then
                # Stop timer before updating
                if [[ "$file" == "timer" ]]; then
                    systemctl --user stop claude-overnight-executor.timer 2>/dev/null || true
                fi
                cp "$source" "$dest"
                needs_reload=true
            fi
            ((updated++))
        fi
    done

    if [[ "$needs_reload" == "true" && "$DRY_RUN" == "false" ]]; then
        log_info "Reloading systemd daemon"
        systemctl --user daemon-reload

        # Restart timer if it was running
        if systemctl --user is-enabled claude-overnight-executor.timer &>/dev/null; then
            log_info "Restarting timer"
            systemctl --user restart claude-overnight-executor.timer
        fi
    fi

    if [[ $updated -eq 0 ]]; then
        log_success "Systemd services are up to date"
    else
        log_success "Updated $updated systemd file(s)"
    fi
}

# Main update process
main() {
    echo ""
    echo "========================================"
    echo "  Plugin Update"
    echo "========================================"
    echo ""
    echo "Plugin: $PLUGIN_NAME"
    echo "Root:   $PLUGIN_ROOT"
    echo ""

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    # Step 1: Update plugin code
    log_info "Step 1: Updating plugin code"
    echo ""
    update_git_repo
    echo ""

    # Step 2: Update hooks in all scopes where currently installed
    log_info "Step 2: Updating hooks and permissions in settings files"
    echo ""

    PROJECT_ROOT=$(find_project_root) || true

    if [[ -n "$PROJECT_ROOT" ]]; then
        update_settings_hooks "$PROJECT_ROOT/.claude/settings.local.json" \
                              "user-local settings" \
                              "--local"
        echo ""
        update_settings_hooks "$PROJECT_ROOT/.claude/settings.json" \
                              "project settings" \
                              "--project"
        echo ""
    fi

    update_settings_hooks "$HOME/.claude/settings.json" \
                          "global settings" \
                          "--global"
    echo ""

    # Step 3: Update skills
    log_info "Step 3: Updating skills"
    echo ""
    update_skills
    echo ""

    # Step 4: Update systemd services
    log_info "Step 4: Updating systemd services"
    echo ""
    update_systemd_services
    echo ""

    # Done
    echo "========================================"
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run complete - no changes made"
    else
        log_success "Update complete!"
        echo ""
        echo "Next steps:"
        echo "  1. Restart Claude Code for hook changes to take effect"
        echo "  2. Check CHANGELOG.md for any breaking changes"
        echo "  3. Review updated documentation if needed"
    fi
    echo "========================================"
    echo ""
}

main "$@"
