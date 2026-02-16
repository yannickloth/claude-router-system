"""
Adaptive orchestration coordinator.

Coordinates complexity classification, strategy selection, and execution.
This is the main entry point that ties together all components.

Change Driver: ORCHESTRATION_COORDINATION
Changes when: Orchestration flow or component coordination changes
"""

from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Optional, Any

import sys
IMPL_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(IMPL_DIR))

from ..config.orchestrator_config import OrchestratorConfig
from ..config.config_loader import load_config
from ..complexity.complexity_classifier import ComplexityClassifier
from .types import OrchestrationMode, OrchestrationResult, ComplexityAnalysis
from .strategies import execute_single_stage, execute_single_stage_with_monitoring, execute_multi_stage
from metrics_collector import MetricsCollector


class AdaptiveOrchestrator:
    """
    Adaptive orchestration system that selects optimal strategy based on complexity.

    STRATEGIES:
    1. Single-stage (SIMPLE requests): route → execute
       - Fast path for mechanical operations
       - Minimal overhead

    2. Single-stage with monitoring (MODERATE requests): route → execute + monitor
       - Normal path for typical requests
       - Basic progress tracking

    3. Multi-stage (COMPLEX requests): interpret → plan → execute
       - Deliberate path for ambiguous/complex work
       - Full interpretation and planning
    """

    def __init__(self, metrics_dir: Optional[Path] = None, config: Optional[OrchestratorConfig] = None, config_path: Optional[Path] = None):
        """
        Initialize adaptive orchestrator.

        Args:
            metrics_dir: Directory for metrics storage
            config: OrchestratorConfig object (if None, loads from config_path)
            config_path: Path to config file (defaults to ~/.claude/adaptive-orchestration.yaml)
        """
        # Load configuration
        if config is None:
            config = load_config(config_path)
        self.config = config

        self.classifier = ComplexityClassifier(config=config)
        self.metrics = MetricsCollector(metrics_dir=metrics_dir)

    def orchestrate(self, request: str, context: Optional[Dict] = None) -> OrchestrationResult:
        """
        Orchestrate request using adaptive strategy selection.

        Args:
            request: User's request string
            context: Optional context dict

        Returns:
            OrchestrationResult with execution details
        """
        # Handle empty requests gracefully
        if not request or not request.strip():
            request = ""  # Normalize to empty string

        # Step 1: Classify complexity (fast heuristic, no API call)
        complexity_analysis = self.classifier.classify(request)

        # Step 2: Select orchestration mode (with config override if set)
        if self.config.force_mode:
            mode = OrchestrationMode(self.config.force_mode)
        else:
            mode = complexity_analysis.recommendation

        # Step 3: Execute with selected mode
        if mode == OrchestrationMode.SINGLE_STAGE:
            result = execute_single_stage(request, context)
        elif mode == OrchestrationMode.MULTI_STAGE:
            result = execute_multi_stage(request, context)
        else:  # SINGLE_STAGE_WITH_MONITORING
            result = execute_single_stage_with_monitoring(request, context)

        # Step 4: Record metrics
        self._record_orchestration_metrics(complexity_analysis, mode, result)

        return OrchestrationResult(
            mode=mode,
            complexity=complexity_analysis.level,
            routing_result=result.get("routing"),
            execution_result=result.get("execution"),
            metadata={
                "complexity_confidence": complexity_analysis.confidence,
                "complexity_indicators": complexity_analysis.indicators,
                **result.get("metadata", {})
            },
            timestamp=datetime.now(UTC).isoformat()
        )

    def _record_orchestration_metrics(
        self,
        complexity: ComplexityAnalysis,
        mode: OrchestrationMode,
        result: Dict[str, Any]
    ) -> None:
        """
        Record metrics about orchestration decision and execution.

        Args:
            complexity: Complexity analysis
            mode: Orchestration mode used
            result: Execution result
        """
        # Record complexity classification
        self.metrics.record_metric(
            solution="adaptive_orchestration",
            metric_name="complexity_classification",
            value=1.0,
            metadata={
                "complexity_level": complexity.level.value,
                "confidence": complexity.confidence,
                "indicators": complexity.indicators,
            }
        )

        # Record orchestration mode
        self.metrics.record_metric(
            solution="adaptive_orchestration",
            metric_name=f"mode_{mode.value}",
            value=1.0,
            metadata={
                "complexity_level": complexity.level.value,
            }
        )
