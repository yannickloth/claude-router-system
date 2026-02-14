#!/usr/bin/env bash
#
# migrate-to-project-isolation.sh
#
# Migrates router system data from global storage to project-specific storage.
# Run this once per project after upgrading to v1.7.0+ (multi-project support).
#
# Change Driver: MIGRATION
# Changes when: Storage architecture changes

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine plugin root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source common functions
COMMON_FUNCTIONS="$PLUGIN_ROOT/hooks/common-functions.sh"
if [ ! -f "$COMMON_FUNCTIONS" ]; then
    echo -e "${RED}[ERROR]${NC} common-functions.sh not found at $COMMON_FUNCTIONS"
    exit 1
fi

# shellcheck source=../hooks/common-functions.sh
source "$COMMON_FUNCTIONS"

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

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Router System Migration to Project Isolation"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "This script migrates router data from global storage (v1.6.x)"
echo "to project-specific storage (v1.7.0+)."
echo ""

# Detect current project
PROJECT_ROOT=$(detect_project_root) || {
    log_error "No .claude directory found. Are you in a Claude Code project?"
    log_info "Navigate to your project directory and run this script again."
    exit 1
}

PROJECT_ID=$(get_project_id)
PROJECT_NAME=$(basename "$PROJECT_ROOT")

log_info "Detected project: $PROJECT_NAME"
log_info "Project root: $PROJECT_ROOT"
log_info "Project ID: $PROJECT_ID"
echo ""

# Old global paths
OLD_STATE_DIR="$HOME/.claude/infolead-claude-subscription-router/state"
OLD_METRICS_DIR="$HOME/.claude/infolead-claude-subscription-router/metrics"
OLD_LOGS_DIR="$HOME/.claude/infolead-claude-subscription-router/logs"

# New project-specific paths
NEW_STATE_DIR=$(get_project_data_dir "state")
NEW_METRICS_DIR=$(get_project_data_dir "metrics")
NEW_LOGS_DIR=$(get_project_data_dir "logs")

log_info "Migration paths:"
echo "  Old (global):"
echo "    State:   $OLD_STATE_DIR"
echo "    Metrics: $OLD_METRICS_DIR"
echo "    Logs:    $OLD_LOGS_DIR"
echo ""
echo "  New (project-specific):"
echo "    State:   $NEW_STATE_DIR"
echo "    Metrics: $NEW_METRICS_DIR"
echo "    Logs:    $NEW_LOGS_DIR"
echo ""

# Check what exists
HAS_OLD_STATE=false
HAS_OLD_METRICS=false
HAS_OLD_LOGS=false

if [ -d "$OLD_STATE_DIR" ] && [ "$(ls -A "$OLD_STATE_DIR" 2>/dev/null)" ]; then
    HAS_OLD_STATE=true
fi

if [ -d "$OLD_METRICS_DIR" ] && [ "$(ls -A "$OLD_METRICS_DIR" 2>/dev/null)" ]; then
    HAS_OLD_METRICS=true
fi

if [ -d "$OLD_LOGS_DIR" ] && [ "$(ls -A "$OLD_LOGS_DIR" 2>/dev/null)" ]; then
    HAS_OLD_LOGS=true
fi

if [ "$HAS_OLD_STATE" = false ] && [ "$HAS_OLD_METRICS" = false ] && [ "$HAS_OLD_LOGS" = false ]; then
    log_info "No old data found to migrate. You're either:"
    log_info "  1. Already using project-specific storage, or"
    log_info "  2. Haven't used the router system yet"
    log_success "Nothing to do!"
    exit 0
fi

echo "Found old data:"
[ "$HAS_OLD_STATE" = true ] && echo "  ✓ State files"
[ "$HAS_OLD_METRICS" = true ] && echo "  ✓ Metrics files"
[ "$HAS_OLD_LOGS" = true ] && echo "  ✓ Log files"
echo ""

log_warn "This will:"
log_warn "  1. COPY data from global storage to project-specific storage"
log_warn "  2. Leave old data in place (not deleted - you can manually remove later)"
log_warn "  3. Tag migrated metrics/logs with project context"
echo ""

read -p "Continue with migration? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi

echo ""
log_info "Starting migration..."

# Migrate state
if [ "$HAS_OLD_STATE" = true ]; then
    log_info "Migrating state files..."

    for state_file in "$OLD_STATE_DIR"/*.json; do
        if [ -f "$state_file" ]; then
            filename=$(basename "$state_file")

            # Add project context to state file
            if command -v jq &> /dev/null; then
                jq --arg project_id "$PROJECT_ID" \
                   --arg project_root "$PROJECT_ROOT" \
                   '.project = {id: $project_id, root: $project_root}' \
                   "$state_file" > "$NEW_STATE_DIR/$filename"
            else
                # Fallback: simple copy without jq
                cp "$state_file" "$NEW_STATE_DIR/$filename"
            fi

            log_success "  ✓ Migrated $filename"
        fi
    done
fi

# Migrate metrics
if [ "$HAS_OLD_METRICS" = true ]; then
    log_info "Migrating metrics files..."

    for metrics_file in "$OLD_METRICS_DIR"/*.jsonl; do
        if [ -f "$metrics_file" ]; then
            filename=$(basename "$metrics_file")

            # Add project context to each JSONL entry
            if command -v jq &> /dev/null; then
                jq --arg project_id "$PROJECT_ID" \
                   --arg project_root "$PROJECT_ROOT" \
                   --arg project_name "$PROJECT_NAME" \
                   '.project = {id: $project_id, root: $project_root, name: $project_name} |
                    .migrated_from_global = true' \
                   "$metrics_file" > "$NEW_METRICS_DIR/$filename"
            else
                # Fallback: simple copy without jq
                cp "$metrics_file" "$NEW_METRICS_DIR/$filename"
            fi

            log_success "  ✓ Migrated $filename"
        fi
    done
fi

# Migrate logs
if [ "$HAS_OLD_LOGS" = true ]; then
    log_info "Migrating log files..."

    for log_file in "$OLD_LOGS_DIR"/*; do
        if [ -f "$log_file" ]; then
            filename=$(basename "$log_file")
            cp "$log_file" "$NEW_LOGS_DIR/$filename"
            log_success "  ✓ Migrated $filename"
        fi
    done

    # Migrate archive if it exists
    if [ -d "$OLD_LOGS_DIR/archive" ]; then
        mkdir -p "$NEW_LOGS_DIR/archive"
        cp -r "$OLD_LOGS_DIR/archive/"* "$NEW_LOGS_DIR/archive/" 2>/dev/null || true
        log_success "  ✓ Migrated log archive"
    fi
fi

echo ""
log_success "Migration complete!"
echo ""
log_info "Next steps:"
echo "  1. Test the router system in this project to verify it works"
echo "  2. If you have OTHER projects, run this script in each one"
echo "  3. After migrating all projects, you can safely delete old data:"
echo "     rm -rf $HOME/.claude/infolead-claude-subscription-router/state"
echo "     rm -rf $HOME/.claude/infolead-claude-subscription-router/metrics"
echo "     rm -rf $HOME/.claude/infolead-claude-subscription-router/logs"
echo ""
log_warn "Keep old data for now - don't delete until all projects are migrated!"
echo ""
