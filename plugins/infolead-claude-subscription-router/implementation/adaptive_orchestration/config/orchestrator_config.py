"""
Orchestrator configuration data structure.

This module defines the configuration schema for adaptive orchestration.
Separated from loading logic to achieve single responsibility.

Change Driver: CONFIGURATION
Changes when: Configuration schema needs evolve (new settings, thresholds)
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class OrchestratorConfig:
    """Configuration for adaptive orchestrator."""
    # Complexity thresholds
    simple_confidence_threshold: float = 0.7
    complex_confidence_threshold: float = 0.6

    # Pattern weights
    simple_pattern_weight: float = 0.1
    complex_pattern_weight: float = 0.15

    # Custom patterns (add/remove)
    custom_simple_patterns: List[Tuple[str, str]] = field(default_factory=list)
    custom_complex_patterns: List[Tuple[str, str]] = field(default_factory=list)

    # Mode overrides
    force_mode: Optional[str] = None  # "single_stage", "single_stage_monitored", "multi_stage"
