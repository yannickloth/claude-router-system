"""
Fast heuristic-based complexity classifier.

Uses pattern matching and keyword analysis to classify request complexity
WITHOUT making API calls. This ensures minimal latency overhead.

Change Driver: COMPLEXITY_CLASSIFICATION
Changes when: Classification algorithms or decision logic change
"""

import re
from typing import Optional

from ..config.orchestrator_config import OrchestratorConfig
from ..orchestration.types import ComplexityLevel, ComplexityAnalysis, OrchestrationMode
from .complexity_patterns import SIMPLE_INDICATORS, COMPLEX_INDICATORS, MULTI_OBJECTIVE_MARKERS


class ComplexityClassifier:
    """
    Fast heuristic-based complexity classifier.

    Uses pattern matching and keyword analysis to classify request complexity
    WITHOUT making API calls. This ensures minimal latency overhead.
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """
        Initialize classifier with optional configuration.

        Args:
            config: OrchestratorConfig with custom patterns and thresholds
        """
        self.config = config or OrchestratorConfig()

        # Merge custom patterns with defaults
        self.simple_indicators = list(SIMPLE_INDICATORS)
        self.simple_indicators.extend(self.config.custom_simple_patterns)

        self.complex_indicators = list(COMPLEX_INDICATORS)
        self.complex_indicators.extend(self.config.custom_complex_patterns)

    def has_explicit_file_path(self, request: str) -> bool:
        """
        Check if request contains explicit file paths.

        Args:
            request: User's request string

        Returns:
            True if explicit file paths mentioned
        """
        file_patterns = [
            r'\b\w+\.\w{2,4}\b',   # filename.ext
            r'[\./][\w/.-]+',       # path/to/file or ./file
            r'\w+/\w+',             # dir/file
            r'~[\w/.-]+',           # ~/path/file
        ]
        return any(re.search(pattern, request) for pattern in file_patterns)

    def count_objectives(self, request: str) -> int:
        """
        Count number of distinct objectives in request.

        Multi-objective requests like "do X and then Y and Z" need coordination.

        Args:
            request: User's request string

        Returns:
            Number of objectives (1 = single, 2+ = multi)
        """
        request_lower = request.lower()
        count = 1  # Start with 1 (base objective)

        for marker in MULTI_OBJECTIVE_MARKERS:
            count += request_lower.count(marker)

        return count

    def classify(self, request: str) -> ComplexityAnalysis:
        """
        Classify request complexity using fast heuristics.

        Classification logic:
        1. Check for SIMPLE indicators (mechanical + explicit path)
        2. Check for COMPLEX indicators (judgment, ambiguity, multi-step)
        3. Default to MODERATE if unclear

        Args:
            request: User's request string

        Returns:
            ComplexityAnalysis with level, confidence, and indicators
        """
        request_lower = request.lower()
        indicators = []

        # Check SIMPLE patterns (using merged patterns)
        simple_matches = []
        for pattern, indicator_name in self.simple_indicators:
            if re.search(pattern, request_lower):
                simple_matches.append(indicator_name)
                indicators.append(f"simple:{indicator_name}")

        # Check COMPLEX patterns (using merged patterns)
        complex_matches = []
        for pattern, indicator_name in self.complex_indicators:
            if re.search(pattern, request_lower):
                complex_matches.append(indicator_name)
                indicators.append(f"complex:{indicator_name}")

        # Check for explicit file path
        has_explicit_path = self.has_explicit_file_path(request)
        if has_explicit_path:
            indicators.append("has_explicit_path")

        # Check for multiple objectives
        objective_count = self.count_objectives(request)
        if objective_count >= 3:
            indicators.append(f"multi_objective:{objective_count}")
            complex_matches.append("multi_objective")

        # DECISION LOGIC

        # SIMPLE: Has simple patterns, has explicit path, NO complex patterns
        if simple_matches and has_explicit_path and not complex_matches:
            return ComplexityAnalysis(
                level=ComplexityLevel.SIMPLE,
                confidence=min(0.95, self.config.simple_confidence_threshold + len(simple_matches) * self.config.simple_pattern_weight),
                indicators=indicators,
                recommendation=OrchestrationMode.SINGLE_STAGE
            )

        # COMPLEX: Has complex patterns OR multiple objectives
        if complex_matches or objective_count >= 3:
            return ComplexityAnalysis(
                level=ComplexityLevel.COMPLEX,
                confidence=min(0.95, self.config.complex_confidence_threshold + len(complex_matches) * self.config.complex_pattern_weight),
                indicators=indicators,
                recommendation=OrchestrationMode.MULTI_STAGE
            )

        # MODERATE: Default (some simple patterns but no explicit path, or unclear)
        return ComplexityAnalysis(
            level=ComplexityLevel.MODERATE,
            confidence=0.6,
            indicators=indicators or ["no_strong_indicators"],
            recommendation=OrchestrationMode.SINGLE_STAGE_WITH_MONITORING
        )
