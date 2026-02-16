"""
Adaptive Orchestration - Intelligently select orchestration strategy based on request complexity.

This package implements adaptive orchestration that chooses between fast single-stage
routing and deliberate multi-stage planning based on request complexity classification.

Public API:
- AdaptiveOrchestrator: Main orchestrator class
- OrchestratorConfig: Configuration schema
- load_config: Configuration loader
- ComplexityClassifier: Complexity classification
- OrchestrationResult, ComplexityAnalysis: Result types
- ComplexityLevel, OrchestrationMode: Enums

Usage:
    from adaptive_orchestration import AdaptiveOrchestrator

    orchestrator = AdaptiveOrchestrator()
    result = orchestrator.orchestrate("Fix typo in README.md")
"""

# Main orchestrator
from .orchestration.adaptive_orchestrator import AdaptiveOrchestrator

# Configuration
from .config.orchestrator_config import OrchestratorConfig
from .config.config_loader import load_config

# Complexity classification
from .complexity.complexity_classifier import ComplexityClassifier

# Types
from .orchestration.types import (
    ComplexityLevel,
    OrchestrationMode,
    ComplexityAnalysis,
    OrchestrationResult
)

# Version
__version__ = "1.0.0"

# Public API
__all__ = [
    # Main class
    "AdaptiveOrchestrator",

    # Configuration
    "OrchestratorConfig",
    "load_config",

    # Classifier
    "ComplexityClassifier",

    # Types
    "ComplexityLevel",
    "OrchestrationMode",
    "ComplexityAnalysis",
    "OrchestrationResult",
]
