#!/usr/bin/env bash
#
# Setup script for infolead-utils plugin hooks
#
# Due to Claude Code plugin hook execution bug, we need to copy hooks
# to .claude/settings.local.json instead of relying on plugin.json
#
# This script:
# 1. Reads hook definitions from plugin.json
# 2. Copies them to .claude/settings.local.json
# 3. Creates backups before modifying
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(cd "$PLUGIN_DIR/../.." && pwd)"
SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.local.json"

echo "=== Infolead Utils Plugin Hook Setup ==="
echo "Plugin dir: $PLUGIN_DIR"
echo "Project root: $PROJECT_ROOT"
echo "Settings file: $SETTINGS_FILE"
echo

# Create .claude directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/.claude"

# Create settings file if it doesn't exist
if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "{}" > "$SETTINGS_FILE"
    echo "Created new settings.local.json"
fi

# Create backup
BACKUP_FILE="$SETTINGS_FILE.backup.$(date +%Y%m%d-%H%M%S)"
cp "$SETTINGS_FILE" "$BACKUP_FILE"
echo "Created backup: $BACKUP_FILE"

# Read hook path from plugin.json
HOOK_PATH=$(jq -r '.hooks.UserPromptSubmit' "$PLUGIN_DIR/plugin.json")
FULL_HOOK_PATH="$PLUGIN_DIR/$HOOK_PATH"

echo "Hook path: $FULL_HOOK_PATH"

# Verify hook exists and is executable
if [[ ! -f "$FULL_HOOK_PATH" ]]; then
    echo "ERROR: Hook not found at $FULL_HOOK_PATH"
    exit 1
fi

if [[ ! -x "$FULL_HOOK_PATH" ]]; then
    echo "ERROR: Hook is not executable: $FULL_HOOK_PATH"
    exit 1
fi

# Update settings.local.json with hook path
jq --arg hook_path "$FULL_HOOK_PATH" \
   '.hooks.UserPromptSubmit = $hook_path' \
   "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp"

mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"

echo
echo "✓ Hook installed successfully"
echo
echo "Current hook configuration:"
jq '.hooks' "$SETTINGS_FILE"
echo
echo "IMPORTANT: Restart Claude Code for changes to take effect"
