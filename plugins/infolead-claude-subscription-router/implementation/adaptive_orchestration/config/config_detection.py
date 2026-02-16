"""
Project-specific configuration detection.

Walks directory tree to find .claude directory and project-specific config files.
This is separated from config loading to isolate the project detection logic.

Change Driver: PROJECT_DETECTION
Changes when: Project detection rules change (directory structure, file naming)
"""

import os
from pathlib import Path
from typing import Optional


# Default configuration path
DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "adaptive-orchestration.yaml"


def detect_project_config() -> Optional[Path]:
    """
    Detect project-specific config file by walking up from PWD.

    Returns:
        Path to project-specific config, or None if not found
    """
    cwd = Path(os.getcwd())

    # Walk up directory tree looking for .claude directory
    current = cwd
    while current != current.parent:
        claude_dir = current / ".claude"
        if claude_dir.is_dir():
            # Found .claude directory - check for config file
            config_file = claude_dir / "adaptive-orchestration.yaml"
            if config_file.exists():
                return config_file
            # .claude exists but no config - this is the project root
            return None
        current = current.parent

    return None
