"""
Probabilistic Router - Confidence-based routing with pattern matching.

Routes requests based on confidence classification using pattern matching
and historical success rates to determine optimal model selection.

Usage:
    router = ProbabilisticRouter()
    decision = router.route_with_confidence(request, context)

Change Driver: PROBABILISTIC_ROUTING
Changes when: Routing heuristics or pattern matching logic changes
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from file_locking import locked_state_file
from .types import (
    RoutingConfidence,
    RoutingDecision,
    HISTORY_FILE,
)


class ProbabilisticRouter:
    """
    Route requests based on confidence classification.

    Uses pattern matching and historical success rates to determine
    optimal model selection with validation fallback.
    """

    def __init__(self, history_file: Optional[Path] = None):
        """
        Initialize probabilistic router.

        Args:
            history_file: Path to history file for learning
        """
        self.history_file = history_file or HISTORY_FILE
        self.history_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Task type success tracking
        self.success_history: Dict[str, Dict[str, Dict[str, int]]] = {
            "haiku": {},
            "sonnet": {},
            "opus": {},
        }

        self._load_history()

    def _load_history(self) -> None:
        """Load routing history from file."""
        if not self.history_file.exists():
            return

        try:
            with locked_state_file(self.history_file, "r") as f:
                data = json.load(f)
                self.success_history = data.get("success_history", self.success_history)
        except (json.JSONDecodeError, KeyError):
            pass

    def _save_history(self) -> None:
        """Save routing history to file."""
        from datetime import datetime, UTC

        data = {
            "success_history": self.success_history,
            "last_updated": datetime.now(UTC).isoformat(),
        }

        with locked_state_file(self.history_file, "r+", create_if_missing=True) as f:
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

    def route_with_confidence(
        self,
        request: str,
        context: Optional[Dict] = None
    ) -> RoutingDecision:
        """
        Classify request and return routing decision with confidence.

        Args:
            request: User's request
            context: Optional context dict

        Returns:
            RoutingDecision with model, confidence, and validation criteria
        """
        context = context or {}

        # Pattern 1: Mechanical, rule-based tasks → HIGH confidence for Haiku
        mechanical_patterns = [
            r"fix syntax error",
            r"remove trailing whitespace",
            r"add missing import",
            r"rename variable \w+ to \w+",
            r"delete lines? \d+",
            r"format (code|file)",
            r"sort (imports|lines)",
            r"fix (typo|spelling)",
            r"add (semicolon|comma|bracket)",
            r"remove (unused|dead) (code|import)",
        ]

        if self._matches_patterns(request, mechanical_patterns):
            return RoutingDecision(
                recommended_model="haiku",
                confidence=RoutingConfidence.HIGH,
                fallback_chain=["sonnet", "opus"],
                validation_criteria=["syntax_valid", "no_logic_change"],
                reasoning="Mechanical task with clear rules",
            )

        # Pattern 2: Simple read-only operations → HIGH confidence for Haiku
        readonly_patterns = [
            r"find (all|files|occurrences)",
            r"list \w+",
            r"show (me )?",
            r"count \w+",
            r"search for",
            r"grep",
            r"what (files|functions|classes)",
            r"where is",
        ]

        if self._matches_patterns(request, readonly_patterns):
            return RoutingDecision(
                recommended_model="haiku",
                confidence=RoutingConfidence.HIGH,
                fallback_chain=["sonnet"],
                validation_criteria=["results_found"],
                reasoning="Read-only operation",
            )

        # Pattern 3: Simple transformations → MEDIUM confidence for Haiku
        transform_patterns = [
            r"convert \w+ to \w+",
            r"replace \w+ with \w+",
            r"extract \w+ from",
            r"merge (files|data)",
            r"split \w+ into",
            r"move \w+ to",
            r"copy \w+ to",
        ]

        if self._matches_patterns(request, transform_patterns):
            # Check historical success rate
            haiku_success_rate = self._get_success_rate("haiku", "transform")

            if haiku_success_rate > 0.8:
                return RoutingDecision(
                    recommended_model="haiku",
                    confidence=RoutingConfidence.MEDIUM,
                    fallback_chain=["sonnet", "opus"],
                    validation_criteria=["output_valid", "user_verify"],
                    reasoning=f"Transform task (success rate: {haiku_success_rate:.0%})",
                )
            else:
                return RoutingDecision(
                    recommended_model="sonnet",
                    confidence=RoutingConfidence.HIGH,
                    fallback_chain=["opus"],
                    validation_criteria=[],
                    reasoning=f"Transform task, Haiku success rate too low ({haiku_success_rate:.0%})",
                )

        # Pattern 4: Judgment, design, analysis → LOW confidence for Haiku, use Sonnet
        judgment_patterns = [
            r"(design|architect|plan)",
            r"(which|what) (is|should|would)",
            r"recommend",
            r"best (approach|way|practice)",
            r"analyze (and|for)",
            r"review (and|for)",
            r"evaluate",
            r"compare",
            r"trade-?offs?",
            r"pros? (and|&) cons?",
        ]

        if self._matches_patterns(request, judgment_patterns):
            return RoutingDecision(
                recommended_model="sonnet",
                confidence=RoutingConfidence.HIGH,
                fallback_chain=["opus"],
                validation_criteria=[],
                reasoning="Requires judgment or analysis",
            )

        # Pattern 5: Complex reasoning, proofs → Opus
        complex_patterns = [
            r"(prove|proof|theorem)",
            r"formal(ize|ly)",
            r"mathematical",
            r"verify correctness",
            r"logical (deduction|inference)",
            r"deep analysis",
        ]

        if self._matches_patterns(request, complex_patterns):
            return RoutingDecision(
                recommended_model="opus",
                confidence=RoutingConfidence.HIGH,
                fallback_chain=[],
                validation_criteria=[],
                reasoning="Requires complex reasoning",
            )

        # Pattern 6: Destructive operations → Sonnet with caution
        destructive_patterns = [
            r"delete",
            r"remove",
            r"drop",
            r"destroy",
            r"overwrite",
            r"reset",
        ]

        if self._matches_patterns(request, destructive_patterns):
            return RoutingDecision(
                recommended_model="sonnet",
                confidence=RoutingConfidence.MEDIUM,
                fallback_chain=["opus"],
                validation_criteria=["user_verify"],
                reasoning="Destructive operation requires caution",
            )

        # Default: Medium confidence for Sonnet
        return RoutingDecision(
            recommended_model="sonnet",
            confidence=RoutingConfidence.MEDIUM,
            fallback_chain=["opus"],
            validation_criteria=[],
            reasoning="Default routing",
        )

    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any regex pattern."""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in patterns)

    def _get_success_rate(self, model: str, task_type: str) -> float:
        """
        Get historical success rate for model on task type.

        Args:
            model: Model name
            task_type: Task type category

        Returns:
            Success rate (0.0-1.0), defaults to 0.5 if no history
        """
        model_history = self.success_history.get(model, {})
        task_history = model_history.get(task_type, {"attempts": 0, "successes": 0})

        if task_history["attempts"] == 0:
            return 0.5  # Default to 50% if no history

        return task_history["successes"] / task_history["attempts"]

    def record_outcome(
        self,
        model: str,
        success: bool,
        task_type: str = "general"
    ) -> None:
        """
        Record routing outcome for learning.

        Args:
            model: Model that was used
            success: Whether execution succeeded
            task_type: Category of task
        """
        if model not in self.success_history:
            self.success_history[model] = {}

        if task_type not in self.success_history[model]:
            self.success_history[model][task_type] = {"attempts": 0, "successes": 0}

        self.success_history[model][task_type]["attempts"] += 1
        if success:
            self.success_history[model][task_type]["successes"] += 1

        self._save_history()

    def get_statistics(self) -> Dict:
        """Get routing statistics."""
        stats = {}
        for model, task_types in self.success_history.items():
            model_stats = {}
            for task_type, counts in task_types.items():
                attempts = counts["attempts"]
                successes = counts["successes"]
                rate = successes / attempts if attempts > 0 else 0
                model_stats[task_type] = {
                    "attempts": attempts,
                    "successes": successes,
                    "success_rate": round(rate, 3),
                }
            stats[model] = model_stats
        return stats
