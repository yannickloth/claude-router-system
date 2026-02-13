#!/usr/bin/env bash
#
# setup-hooks-workaround.sh
#
# Temporary workaround for Claude Code plugin hook execution bug.
# Copies hooks from plugin.json to settings.json (local or global)
#
# See: docs/HOOKS-WORKAROUND.md for details
#
# Usage:
#   ./scripts/setup-hooks-workaround.sh [--local|--global] [--dry-run] [--revert]
#

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

# Parse arguments
DRY_RUN=false
REVERT=false
SCOPE=""  # Will be set to "local", "project", or "global"

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --revert)
            REVERT=true
            ;;
        --local)
            SCOPE="local"
            ;;
        --project)
            SCOPE="project"
            ;;
        --global)
            SCOPE="global"
            ;;
        --help|-h)
            echo "Usage: $0 [--local|--project|--global] [--dry-run] [--revert]"
            echo ""
            echo "Scope (required):"
            echo "  --local     Install to .claude/settings.local.json (this user, this project)"
            echo "  --project   Install to .claude/settings.json (all users, this project)"
            echo "  --global    Install to ~/.claude/settings.json (this user, all projects)"
            echo ""
            echo "Options:"
            echo "  --dry-run   Show what would be done without making changes"
            echo "  --revert    Remove plugin hooks from settings file"
            echo ""
            echo "This script works around Claude Code bug where plugin hooks"
            echo "are matched but never executed. It copies hooks to settings.json."
            echo ""
            echo "Examples:"
            echo "  $0 --local              # This user only, this project"
            echo "  $0 --project            # All users of this project (committed)"
            echo "  $0 --global             # This user, all projects"
            echo "  $0 --local --dry-run    # Preview local installation"
            echo "  $0 --project --revert   # Remove from project settings"
            echo ""
            echo "See: docs/HOOKS-WORKAROUND.md"
            exit 0
            ;;
    esac
done

# Require scope argument
if [[ -z "$SCOPE" ]]; then
    echo -e "${RED}[ERROR]${NC} You must specify --local, --project, or --global"
    echo ""
    echo "  --local     .claude/settings.local.json  (this user, this project)"
    echo "  --project   .claude/settings.json        (all users, this project)"
    echo "  --global    ~/.claude/settings.json      (this user, all projects)"
    echo ""
    echo "Run with --help for more information."
    exit 1
fi

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

# Set paths based on scope
case "$SCOPE" in
    local)
        PROJECT_ROOT=$(find_project_root) || {
            echo -e "${RED}[ERROR]${NC} Could not find project root with .claude directory"
            exit 1
        }
        SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.local.json"
        BACKUP_FILE="$PROJECT_ROOT/.claude/settings.local.json.backup.$(date +%Y%m%d-%H%M%S)"
        SCOPE_DESC="user-local (this user, this project)"
        ;;
    project)
        PROJECT_ROOT=$(find_project_root) || {
            echo -e "${RED}[ERROR]${NC} Could not find project root with .claude directory"
            exit 1
        }
        SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.json"
        BACKUP_FILE="$PROJECT_ROOT/.claude/settings.json.backup.$(date +%Y%m%d-%H%M%S)"
        SCOPE_DESC="project (all users, this project)"
        ;;
    global)
        SETTINGS_FILE="$HOME/.claude/settings.json"
        BACKUP_FILE="$HOME/.claude/settings.json.backup.$(date +%Y%m%d-%H%M%S)"
        SCOPE_DESC="global (this user, all projects)"
        ;;
esac

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

# Check dependencies
check_deps() {
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is required but not installed."
        exit 1
    fi
}

# Ensure settings file exists
ensure_settings_file() {
    if [[ ! -f "$SETTINGS_FILE" ]]; then
        log_warn "Settings file not found. Creating: $SETTINGS_FILE"
        mkdir -p "$(dirname "$SETTINGS_FILE")"
        echo '{}' > "$SETTINGS_FILE"
    fi
}

# Generate hooks JSON with absolute paths
generate_hooks_json() {
    cat <<EOF
{
  "UserPromptSubmit": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${PLUGIN_ROOT}/hooks/user-prompt-submit.sh",
          "timeout": 10
        }
      ]
    }
  ],
  "SubagentStart": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${PLUGIN_ROOT}/hooks/log-subagent-start.sh",
          "timeout": 5
        }
      ]
    }
  ],
  "SubagentStop": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${PLUGIN_ROOT}/hooks/log-subagent-stop.sh",
          "timeout": 5
        }
      ]
    }
  ],
  "SessionStart": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${PLUGIN_ROOT}/hooks/load-session-state.sh",
          "timeout": 5
        },
        {
          "type": "command",
          "command": "${PLUGIN_ROOT}/hooks/load-session-memory.sh",
          "timeout": 5
        }
      ]
    }
  ],
  "SessionEnd": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${PLUGIN_ROOT}/hooks/save-session-state.sh",
          "timeout": 5
        }
      ]
    }
  ],
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "${PLUGIN_ROOT}/hooks/pre-tool-use-write-approve.sh",
          "timeout": 5
        }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "${PLUGIN_ROOT}/hooks/cache-invalidation.sh",
          "timeout": 10
        }
      ]
    }
  ]
}
EOF
}

# Merge hooks into settings file
merge_hooks() {
    local new_hooks
    new_hooks=$(generate_hooks_json)

    # Use Python for reliable JSON merging
    python3 << PYTHON
import json
import sys

settings_file = "$SETTINGS_FILE"
dry_run = $( [[ "$DRY_RUN" == "true" ]] && echo "True" || echo "False" )

# Read current settings
with open(settings_file, 'r') as f:
    settings = json.load(f)

# Parse new hooks
new_hooks = json.loads('''$new_hooks''')

# Get or create hooks section
current_hooks = settings.get('hooks', {})

# Track changes
changes = []

# Merge each hook type
for hook_type, hook_configs in new_hooks.items():
    if hook_type not in current_hooks:
        current_hooks[hook_type] = []
        changes.append(f"  + Added {hook_type} hooks")

    # Check if plugin hooks already exist (by checking command path)
    existing_commands = set()
    for config in current_hooks[hook_type]:
        for hook in config.get('hooks', []):
            existing_commands.add(hook.get('command', ''))

    for new_config in hook_configs:
        for hook in new_config.get('hooks', []):
            if hook.get('command') not in existing_commands:
                # Add as new config (append to existing array)
                current_hooks[hook_type].append(new_config)
                changes.append(f"  + Added hook: {hook.get('command', 'unknown').split('/')[-1]}")
                break

settings['hooks'] = current_hooks

if not changes:
    print("No changes needed - hooks already configured")
    sys.exit(0)

print("Changes to be made:")
for change in changes:
    print(change)

if dry_run:
    print("\n[DRY RUN] No changes written")
else:
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')
    print(f"\nSettings updated: {settings_file}")
PYTHON
}

# Merge Write/Edit permissions into settings file
merge_permissions() {
    python3 << PYTHON
import json
import sys

settings_file = "$SETTINGS_FILE"
dry_run = $( [[ "$DRY_RUN" == "true" ]] && echo "True" || echo "False" )

# Read current settings
with open(settings_file, 'r') as f:
    settings = json.load(f)

# Required permissions for background agent file writes
required_permissions = ["Write(*)", "Edit(*)"]

# Get or create permissions section
permissions = settings.setdefault('permissions', {})
allow_list = permissions.setdefault('allow', [])

# Track changes
changes = []

for perm in required_permissions:
    if perm not in allow_list:
        allow_list.append(perm)
        changes.append(f"  + Added permission: {perm}")

if not changes:
    print("No permission changes needed - Write/Edit already allowed")
    sys.exit(0)

settings['permissions']['allow'] = allow_list

print("Permission changes to be made:")
for change in changes:
    print(change)

if dry_run:
    print("\n[DRY RUN] No changes written")
else:
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')
    print(f"\nPermissions updated: {settings_file}")
PYTHON
}

# Remove plugin permissions from settings file
revert_permissions() {
    python3 << PYTHON
import json
import sys

settings_file = "$SETTINGS_FILE"
dry_run = $( [[ "$DRY_RUN" == "true" ]] && echo "True" || echo "False" )

# Read current settings
with open(settings_file, 'r') as f:
    settings = json.load(f)

# Permissions added by this plugin
plugin_permissions = {"Write(*)", "Edit(*)"}

allow_list = settings.get('permissions', {}).get('allow', [])
if not allow_list:
    print("No permissions found to revert")
    sys.exit(0)

changes = []
new_allow = []
for perm in allow_list:
    if perm in plugin_permissions:
        changes.append(f"  - Removed permission: {perm}")
    else:
        new_allow.append(perm)

if not changes:
    print("No plugin permissions found to remove")
    sys.exit(0)

settings['permissions']['allow'] = new_allow

print("Permission changes to be made:")
for change in changes:
    print(change)

if dry_run:
    print("\n[DRY RUN] No changes written")
else:
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')
    print(f"\nPermissions updated: {settings_file}")
PYTHON
}

# Remove plugin hooks from settings file
revert_hooks() {
    python3 << PYTHON
import json
import sys

settings_file = "$SETTINGS_FILE"
plugin_root = "$PLUGIN_ROOT"
dry_run = $( [[ "$DRY_RUN" == "true" ]] && echo "True" || echo "False" )

# Read current settings
with open(settings_file, 'r') as f:
    settings = json.load(f)

if 'hooks' not in settings:
    print("No hooks found in settings file")
    sys.exit(0)

# Track removals
changes = []

# Filter out hooks with plugin paths
for hook_type, hook_configs in list(settings['hooks'].items()):
    filtered_configs = []
    for config in hook_configs:
        filtered_hooks = []
        for hook in config.get('hooks', []):
            cmd = hook.get('command', '')
            if plugin_root not in cmd:
                filtered_hooks.append(hook)
            else:
                changes.append(f"  - Removed: {cmd.split('/')[-1]}")

        if filtered_hooks:
            config['hooks'] = filtered_hooks
            filtered_configs.append(config)

    if filtered_configs:
        settings['hooks'][hook_type] = filtered_configs
    else:
        del settings['hooks'][hook_type]
        changes.append(f"  - Removed empty hook type: {hook_type}")

# Remove empty hooks section
if not settings.get('hooks'):
    if 'hooks' in settings:
        del settings['hooks']
    changes.append("  - Removed empty hooks section")

if not changes:
    print("No plugin hooks found to remove")
    sys.exit(0)

print("Changes to be made:")
for change in changes:
    print(change)

if dry_run:
    print("\n[DRY RUN] No changes written")
else:
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')
    print(f"\nSettings updated: {settings_file}")
PYTHON
}

# Main
main() {
    echo ""
    echo "========================================"
    echo "  Plugin Hooks Workaround Setup"
    echo "========================================"
    echo ""
    echo "Plugin: infolead-claude-subscription-router"
    echo "Root:   $PLUGIN_ROOT"
    echo "Scope:  $SCOPE_DESC"
    echo "Target: $SETTINGS_FILE"
    echo ""

    check_deps
    ensure_settings_file

    if [[ "$REVERT" == "true" ]]; then
        log_info "Reverting workaround (removing plugin hooks and permissions)"

        if [[ "$DRY_RUN" == "false" ]]; then
            log_info "Creating backup: $BACKUP_FILE"
            cp "$SETTINGS_FILE" "$BACKUP_FILE"
        fi

        revert_hooks
        echo ""
        revert_permissions
    else
        log_info "Setting up workaround (copying hooks and permissions to $SCOPE_DESC settings)"
        log_warn "This is a temporary fix for Claude Code issue #10225, #14410"
        echo ""

        if [[ "$DRY_RUN" == "false" ]]; then
            log_info "Creating backup: $BACKUP_FILE"
            cp "$SETTINGS_FILE" "$BACKUP_FILE"
        fi

        merge_hooks
        echo ""
        log_info "Adding Write/Edit permissions for background agent file operations"
        merge_permissions
    fi

    echo ""
    if [[ "$DRY_RUN" == "false" ]]; then
        log_success "Done! Restart Claude Code for changes to take effect."
    fi
    echo ""
    echo "Related issues:"
    echo "  - https://github.com/anthropics/claude-code/issues/10225"
    echo "  - https://github.com/anthropics/claude-code/issues/14410"
    echo ""
}

main "$@"
