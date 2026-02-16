"""
Configuration loading with project-aware cascading.

Loads configuration from YAML files with support for:
- Global user config (~/.claude/adaptive-orchestration.yaml)
- Project-specific config (.claude/adaptive-orchestration.yaml)
- Explicit config file override

Change Driver: CONFIGURATION_LOADING
Changes when: Config loading logic, cascade rules, or file format change
"""

import sys
from pathlib import Path
from typing import Optional
import yaml

from .orchestrator_config import OrchestratorConfig
from .config_detection import detect_project_config, DEFAULT_CONFIG_PATH


def load_config(config_path: Optional[Path] = None, enable_project_cascade: bool = True) -> OrchestratorConfig:
    """
    Load configuration from YAML file with project-aware cascading.

    Configuration cascade (priority order):
    1. Explicit config_path (if provided)
    2. Project-specific config (.claude/adaptive-orchestration.yaml)
    3. Global user config (~/.claude/adaptive-orchestration.yaml)
    4. Default configuration

    Args:
        config_path: Explicit path to config file (overrides cascade)
        enable_project_cascade: Enable project-specific config detection (default: True)

    Returns:
        OrchestratorConfig with loaded or default values
    """
    # Explicit config_path takes precedence
    if config_path is not None:
        if not config_path.exists():
            return OrchestratorConfig()
    else:
        # Try project-specific config first (hybrid architecture)
        if enable_project_cascade:
            project_config = detect_project_config()
            if project_config is not None:
                config_path = project_config
            else:
                # Fall back to global config
                config_path = DEFAULT_CONFIG_PATH
        else:
            config_path = DEFAULT_CONFIG_PATH

    # If final config_path doesn't exist, return defaults
    if not config_path.exists():
        return OrchestratorConfig()

    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        if not config_data:
            return OrchestratorConfig()

        # Validate and extract config
        thresholds = config_data.get('thresholds', {})
        weights = config_data.get('weights', {})
        patterns = config_data.get('patterns', {})
        overrides = config_data.get('overrides', {})

        # Parse custom patterns
        custom_simple = []
        if 'custom_simple' in patterns:
            for item in patterns['custom_simple']:
                if isinstance(item, dict) and 'pattern' in item and 'name' in item:
                    custom_simple.append((item['pattern'], item['name']))

        custom_complex = []
        if 'custom_complex' in patterns:
            for item in patterns['custom_complex']:
                if isinstance(item, dict) and 'pattern' in item and 'name' in item:
                    custom_complex.append((item['pattern'], item['name']))

        # Validate force_mode
        force_mode = overrides.get('force_mode')
        if force_mode and force_mode not in ["single_stage", "single_stage_monitored", "multi_stage", None]:
            print(f"Warning: Invalid force_mode '{force_mode}' in config, ignoring", file=sys.stderr)
            force_mode = None

        return OrchestratorConfig(
            simple_confidence_threshold=float(thresholds.get('simple_confidence', 0.7)),
            complex_confidence_threshold=float(thresholds.get('complex_confidence', 0.6)),
            simple_pattern_weight=float(weights.get('simple_weight', 0.1)),
            complex_pattern_weight=float(weights.get('complex_weight', 0.15)),
            custom_simple_patterns=custom_simple,
            custom_complex_patterns=custom_complex,
            force_mode=force_mode,
        )

    except yaml.YAMLError as e:
        print(f"Error parsing config file {config_path}: {e}", file=sys.stderr)
        print("Falling back to default configuration", file=sys.stderr)
        return OrchestratorConfig()
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}", file=sys.stderr)
        print("Falling back to default configuration", file=sys.stderr)
        return OrchestratorConfig()
