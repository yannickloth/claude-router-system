#!/bin/bash
# Cache Invalidation Hook
# Invalidates semantic cache when files change
#
# Trigger: Post file modification or git operations
# Change Driver: CACHE_MANAGEMENT

set -euo pipefail

CACHE_DIR="$HOME/.claude/infolead-claude-subscription-router/cache"

# Ensure cache directory exists
mkdir -p "$CACHE_DIR"
chmod 700 "$CACHE_DIR"

# Get list of modified files from git (if in a git repo)
MODIFIED_FILES=""
if git rev-parse --git-dir &> /dev/null; then
    MODIFIED_FILES=$(git diff --name-only HEAD 2>/dev/null || echo "")
fi

if [ -z "$MODIFIED_FILES" ]; then
    exit 0
fi

echo "[cache] Files modified - checking cache invalidation..." >&2

# Check if Python cache invalidation module exists
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"
CACHE_MODULE="$PLUGIN_ROOT/implementation/semantic_cache.py"

if [ -f "$CACHE_MODULE" ]; then
    # Use the plugin's cache module
    python3 - "$CACHE_DIR" "$MODIFIED_FILES" <<'EOF' 2>/dev/null || echo "[cache] Cache invalidation skipped (module not ready)" >&2
import sys
from pathlib import Path

cache_dir = Path(sys.argv[1])
modified_files = sys.argv[2].split('\n')
modified_files = [f for f in modified_files if f.strip()]

if not modified_files:
    sys.exit(0)

# Simple cache invalidation: remove entries that reference modified files
cache_index = cache_dir / "cache-index.json"
if cache_index.exists():
    import json
    try:
        with open(cache_index) as f:
            index = json.load(f)

        invalidated = 0
        for file in modified_files:
            if file in index.get("file_references", {}):
                del index["file_references"][file]
                invalidated += 1

        if invalidated > 0:
            with open(cache_index, 'w') as f:
                json.dump(index, f)
            print(f"[cache] Invalidated {invalidated} cache entries", file=sys.stderr)
    except (json.JSONDecodeError, KeyError):
        pass
EOF
else
    # Fallback: simple file-based invalidation
    INVALIDATION_LOG="$CACHE_DIR/invalidation.log"
    (
        flock -x 200
        echo "$(date -Iseconds): Files modified: $MODIFIED_FILES" >> "$INVALIDATION_LOG"
    ) 200>"$INVALIDATION_LOG.lock"
    echo "[cache] Logged file changes for cache review" >&2
fi

exit 0
