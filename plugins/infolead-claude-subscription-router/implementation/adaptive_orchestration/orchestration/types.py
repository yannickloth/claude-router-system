"""
Type definitions for orchestration system.

Defines enums and data classes representing orchestration concepts.
Separated to avoid circular dependencies and achieve single responsibility.

Change Driver: TYPE_DEFINITIONS
Changes when: New orchestration types, modes, or result structures are needed
"""

from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, List, Optional, Any

# Import from routing_core for type consistency
import sys
from pathlib import Path
IMPL_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(IMPL_DIR))
from routing_core import RoutingResult


class ComplexityLevel(Enum):
    """Request complexity classifications."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class OrchestrationMode(Enum):
    """Orchestration strategy modes."""
    SINGLE_STAGE = "single_stage"  # Fast: route → execute
    SINGLE_STAGE_WITH_MONITORING = "single_stage_monitored"  # Moderate: route → execute + monitor
    MULTI_STAGE = "multi_stage"  # Deliberate: interpret → plan → execute


@dataclass
class ComplexityAnalysis:
    """Result of complexity classification."""
    level: ComplexityLevel
    confidence: float
    indicators: List[str]
    recommendation: OrchestrationMode


@dataclass
class OrchestrationResult:
    """Result of orchestration execution."""
    mode: OrchestrationMode
    complexity: ComplexityLevel
    routing_result: Optional[RoutingResult]
    execution_result: Optional[str]
    metadata: Dict[str, Any]
    timestamp: str
