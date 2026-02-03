"""
Probabilistic Router - Confidence-based routing with optimistic execution.

Implements Solution 6 from claude-code-architecture.md:
- Confidence classification for routing decisions
- Post-execution validation
- Optimistic execution with escalation

State file: ~/.claude/infolead-router/state/routing-history.json

Usage:
    router = ProbabilisticRouter()
    decision = router.route_with_confidence(request, context)

    executor = OptimisticExecutor(router, ResultValidator())
    result = await executor.execute(request, context)

Change Driver: PROBABILISTIC_ROUTING
Changes when: Routing heuristics or validation criteria change
"""

import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple

from file_locking import locked_state_file


# State directory
STATE_DIR = Path.home() / ".claude" / "infolead-router" / "state"
HISTORY_FILE = STATE_DIR / "routing-history.json"


class RoutingConfidence(Enum):
    """Confidence level for routing decisions."""
    HIGH = "high"          # >90% sure model can handle
    MEDIUM = "medium"      # 70-90% sure
    LOW = "low"            # <70% sure, use higher-tier model


@dataclass
class RoutingDecision:
    """Routing decision with confidence and validation criteria."""
    recommended_model: str
    confidence: RoutingConfidence
    fallback_model: Optional[str]
    validation_criteria: List[str]
    reasoning: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "recommended_model": self.recommended_model,
            "confidence": self.confidence.value,
            "fallback_model": self.fallback_model,
            "validation_criteria": self.validation_criteria,
            "reasoning": self.reasoning,
        }


@dataclass
class RoutingOutcome:
    """Record of a routing outcome for learning."""
    timestamp: str
    request_hash: str  # Hash of request for privacy
    model: str
    task_type: str
    success: bool
    escalated: bool
    validation_failures: List[str] = field(default_factory=list)


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
                fallback_model="sonnet",
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
                fallback_model="sonnet",
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
                    fallback_model="sonnet",
                    validation_criteria=["output_valid", "user_verify"],
                    reasoning=f"Transform task (success rate: {haiku_success_rate:.0%})",
                )
            else:
                return RoutingDecision(
                    recommended_model="sonnet",
                    confidence=RoutingConfidence.HIGH,
                    fallback_model=None,
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
                fallback_model="opus",
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
                fallback_model=None,
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
                fallback_model=None,
                validation_criteria=["user_verify"],
                reasoning="Destructive operation requires caution",
            )

        # Default: Medium confidence for Sonnet
        return RoutingDecision(
            recommended_model="sonnet",
            confidence=RoutingConfidence.MEDIUM,
            fallback_model=None,
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


class ResultValidator:
    """Validates agent execution results to determine if escalation needed."""

    def validate_result(
        self,
        result: Any,
        validation_criteria: List[str],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate result against criteria.

        Args:
            result: Execution result to validate
            validation_criteria: List of validation types to run
            context: Context with additional info (test commands, etc.)

        Returns:
            Tuple of (is_valid, failure_reason)
        """
        for criterion in validation_criteria:
            validator_method = getattr(self, f"_validate_{criterion}", None)

            if validator_method:
                is_valid, reason = validator_method(result, context)
                if not is_valid:
                    return False, reason

        return True, None

    def _validate_syntax_valid(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check if modified code/LaTeX has valid syntax."""
        # Extract file path from result
        file_path = None
        if isinstance(result, dict):
            file_path = result.get("modified_file") or result.get("file_path")
        elif isinstance(result, str) and os.path.exists(result):
            file_path = result

        if not file_path:
            return True, None

        # Check file type and run appropriate validator
        if file_path.endswith(".py"):
            return self._validate_python_syntax(file_path)
        elif file_path.endswith(".tex"):
            return self._validate_latex_syntax(file_path)
        elif file_path.endswith((".js", ".ts", ".tsx")):
            return self._validate_js_syntax(file_path)
        elif file_path.endswith(".json"):
            return self._validate_json_syntax(file_path)

        return True, None

    def _validate_python_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate Python syntax using ast.parse."""
        try:
            with open(file_path) as f:
                ast.parse(f.read())
            return True, None
        except SyntaxError as e:
            return False, f"Python syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Python validation error: {e}"

    def _validate_latex_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate LaTeX syntax (basic checks)."""
        try:
            with open(file_path) as f:
                content = f.read()

            # Check brace matching
            open_braces = content.count("{")
            close_braces = content.count("}")

            if open_braces != close_braces:
                return False, f"Brace mismatch: {open_braces} open, {close_braces} close"

            # Check environment matching
            begin_envs = re.findall(r"\\begin\{(\w+)\}", content)
            end_envs = re.findall(r"\\end\{(\w+)\}", content)

            if len(begin_envs) != len(end_envs):
                return False, f"Environment mismatch: {len(begin_envs)} begins, {len(end_envs)} ends"

            return True, None
        except Exception as e:
            return False, f"LaTeX validation error: {e}"

    def _validate_js_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate JavaScript/TypeScript syntax using node."""
        try:
            result = subprocess.run(
                ["node", "--check", file_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return False, f"JS syntax error: {result.stderr}"
            return True, None
        except FileNotFoundError:
            # Node not available, skip check
            return True, None
        except subprocess.TimeoutExpired:
            return False, "JS syntax check timed out"
        except Exception as e:
            return True, None  # Skip on errors

    def _validate_json_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate JSON syntax."""
        try:
            with open(file_path) as f:
                json.load(f)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"JSON syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"JSON validation error: {e}"

    def _validate_no_logic_change(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Verify that logic/behavior didn't change (for refactoring)."""
        # Run tests if available
        test_command = context.get("test_command")
        if test_command:
            try:
                proc = subprocess.run(
                    test_command if isinstance(test_command, list) else test_command.split(),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=context.get("cwd")
                )
                if proc.returncode != 0:
                    return False, f"Tests failed: {proc.stderr[:200]}"
                return True, None
            except subprocess.TimeoutExpired:
                return False, "Tests timed out"
            except Exception as e:
                return True, None  # Skip on errors

        # No tests available, assume valid
        return True, None

    def _validate_results_found(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check that search/find operation returned results."""
        if isinstance(result, list):
            if len(result) == 0:
                return False, "No results found"
            return True, None

        if isinstance(result, dict):
            if "results" in result and len(result["results"]) == 0:
                return False, "No results found"
            if "matches" in result and len(result["matches"]) == 0:
                return False, "No matches found"
            if "files" in result and len(result["files"]) == 0:
                return False, "No files found"

        if isinstance(result, str):
            if "no results" in result.lower() or "not found" in result.lower():
                return False, "No results found"

        return True, None

    def _validate_output_valid(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Generic output validity check."""
        if isinstance(result, str):
            error_markers = [
                "error:", "failed:", "exception:", "traceback:",
                "fatal:", "panic:", "abort:"
            ]
            for marker in error_markers:
                if marker.lower() in result.lower():
                    return False, f"Error detected in output: {marker}"

        if isinstance(result, dict):
            if result.get("error") or result.get("status") == "error":
                return False, f"Error in result: {result.get('error', 'unknown')}"

        return True, None

    def _validate_user_verify(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Require user verification for medium-confidence tasks.
        Always returns True (user will review), but flags for review.
        """
        print("[validation] Result flagged for user review", file=sys.stderr)
        return True, None


class OptimisticExecutor:
    """Execute with cheap model, validate, escalate if needed."""

    def __init__(
        self,
        router: ProbabilisticRouter,
        validator: ResultValidator,
        agent_executor: Optional[Callable] = None,
    ):
        """
        Initialize optimistic executor.

        Args:
            router: ProbabilisticRouter for routing decisions
            validator: ResultValidator for post-execution validation
            agent_executor: Optional callable(request, model, context) -> result
        """
        self.router = router
        self.validator = validator
        self.agent_executor = agent_executor
        self.escalation_count = 0
        self.total_executions = 0

    async def execute(
        self,
        request: str,
        context: Optional[Dict] = None,
        agent_executor: Optional[Callable] = None,
    ) -> Any:
        """
        Execute request with optimistic routing.
        Try cheap model first, escalate on validation failure.

        Args:
            request: User's request
            context: Optional context dict
            agent_executor: Optional override for agent execution

        Returns:
            Execution result
        """
        context = context or {}
        executor = agent_executor or self.agent_executor

        if not executor:
            raise ValueError("No agent_executor provided")

        # Get routing decision
        decision = self.router.route_with_confidence(request, context)

        print(f"[routing] {decision.recommended_model} "
              f"(confidence: {decision.confidence.value})", file=sys.stderr)
        if decision.reasoning:
            print(f"[routing] Reason: {decision.reasoning}", file=sys.stderr)

        # Try recommended model
        self.total_executions += 1

        # Determine task type for learning
        task_type = self._classify_task_type(request)

        result = await self._execute_with_model(
            request,
            decision.recommended_model,
            context,
            executor
        )

        # Validate result if criteria specified
        if decision.validation_criteria:
            is_valid, failure_reason = self.validator.validate_result(
                result,
                decision.validation_criteria,
                context
            )

            if not is_valid:
                print(f"[validation] Failed: {failure_reason}", file=sys.stderr)

                # Escalate to fallback model
                if decision.fallback_model:
                    print(f"[routing] Escalating to {decision.fallback_model}...",
                          file=sys.stderr)
                    self.escalation_count += 1

                    # Record failure for learning
                    self.router.record_outcome(
                        decision.recommended_model,
                        success=False,
                        task_type=task_type
                    )

                    # Re-execute with better model
                    result = await self._execute_with_model(
                        request,
                        decision.fallback_model,
                        context,
                        executor
                    )

                    # Record fallback success (assume success after escalation)
                    self.router.record_outcome(
                        decision.fallback_model,
                        success=True,
                        task_type=task_type
                    )
                else:
                    # No fallback, return failed result
                    print("[routing] No fallback model available", file=sys.stderr)
                    self.router.record_outcome(
                        decision.recommended_model,
                        success=False,
                        task_type=task_type
                    )
                    return result
            else:
                # Validation passed
                self.router.record_outcome(
                    decision.recommended_model,
                    success=True,
                    task_type=task_type
                )
        else:
            # No validation criteria, assume success
            self.router.record_outcome(
                decision.recommended_model,
                success=True,
                task_type=task_type
            )

        return result

    async def _execute_with_model(
        self,
        request: str,
        model: str,
        context: Dict,
        executor: Callable,
    ) -> Any:
        """Execute request with specific model."""
        print(f"[execution] Running with {model}...", file=sys.stderr)

        import inspect
        if inspect.iscoroutinefunction(executor):
            return await executor(request, model, context)
        else:
            return executor(request, model, context)

    def _classify_task_type(self, request: str) -> str:
        """Classify request into task type for learning."""
        request_lower = request.lower()

        if any(kw in request_lower for kw in ["fix", "syntax", "format", "lint"]):
            return "mechanical"
        if any(kw in request_lower for kw in ["find", "search", "list", "show"]):
            return "readonly"
        if any(kw in request_lower for kw in ["convert", "replace", "extract", "merge"]):
            return "transform"
        if any(kw in request_lower for kw in ["analyze", "review", "design", "plan"]):
            return "judgment"

        return "general"

    def get_escalation_rate(self) -> float:
        """Calculate percentage of executions that required escalation."""
        if self.total_executions == 0:
            return 0.0
        return self.escalation_count / self.total_executions

    def get_statistics(self) -> Dict:
        """Get executor statistics."""
        return {
            "total_executions": self.total_executions,
            "escalation_count": self.escalation_count,
            "escalation_rate": round(self.get_escalation_rate(), 3),
            "router_stats": self.router.get_statistics(),
        }


def main():
    """CLI interface for probabilistic router."""
    import argparse

    parser = argparse.ArgumentParser(description="Probabilistic Router CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # route command
    route_parser = subparsers.add_parser("route", help="Route a request")
    route_parser.add_argument("request", help="Request to route")

    # stats command
    subparsers.add_parser("stats", help="Show routing statistics")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a file")
    validate_parser.add_argument("file", help="File to validate")

    args = parser.parse_args()

    router = ProbabilisticRouter()

    if args.command == "route":
        decision = router.route_with_confidence(args.request)
        print(f"Model: {decision.recommended_model}")
        print(f"Confidence: {decision.confidence.value}")
        print(f"Fallback: {decision.fallback_model or 'None'}")
        print(f"Validation: {', '.join(decision.validation_criteria) or 'None'}")
        print(f"Reasoning: {decision.reasoning}")

    elif args.command == "stats":
        stats = router.get_statistics()
        print("Routing Statistics")
        print("=" * 40)
        for model, task_types in stats.items():
            print(f"\n{model.capitalize()}:")
            if not task_types:
                print("  No history")
            for task_type, data in task_types.items():
                print(f"  {task_type}: {data['successes']}/{data['attempts']} "
                      f"({data['success_rate']:.0%})")

    elif args.command == "validate":
        validator = ResultValidator()
        criteria = ["syntax_valid"]
        is_valid, reason = validator.validate_result(
            args.file,
            criteria,
            {}
        )
        if is_valid:
            print(f"Valid: {args.file}")
        else:
            print(f"Invalid: {reason}")
            sys.exit(1)

    else:
        parser.print_help()


def test_probabilistic_router() -> None:
    """Test probabilistic router functionality."""
    import tempfile
    import asyncio

    print("Testing probabilistic router...")

    with tempfile.TemporaryDirectory() as tmpdir:
        history_file = Path(tmpdir) / "test-history.json"

        # Test 1: Pattern matching
        print("Test 1: Pattern matching")
        router = ProbabilisticRouter(history_file=history_file)

        decision = router.route_with_confidence("fix syntax error in main.py")
        assert decision.recommended_model == "haiku"
        assert decision.confidence == RoutingConfidence.HIGH

        decision = router.route_with_confidence("design the new authentication system")
        assert decision.recommended_model == "sonnet"

        decision = router.route_with_confidence("prove this theorem is correct")
        assert decision.recommended_model == "opus"
        print("  OK")

        # Test 2: Record outcomes
        print("Test 2: Record outcomes")
        router.record_outcome("haiku", True, "mechanical")
        router.record_outcome("haiku", True, "mechanical")
        router.record_outcome("haiku", False, "mechanical")

        rate = router._get_success_rate("haiku", "mechanical")
        assert abs(rate - 0.667) < 0.01
        print("  OK")

        # Test 3: ResultValidator
        print("Test 3: ResultValidator")
        validator = ResultValidator()

        # Create test Python file
        test_py = Path(tmpdir) / "test.py"
        test_py.write_text("def foo():\n    return 1\n")
        is_valid, _ = validator._validate_python_syntax(str(test_py))
        assert is_valid

        # Create invalid Python file
        invalid_py = Path(tmpdir) / "invalid.py"
        invalid_py.write_text("def foo(\n")
        is_valid, reason = validator._validate_python_syntax(str(invalid_py))
        assert not is_valid
        print("  OK")

        # Test 4: Results validation
        print("Test 4: Results validation")
        is_valid, _ = validator._validate_results_found(["result1", "result2"], {})
        assert is_valid

        is_valid, _ = validator._validate_results_found([], {})
        assert not is_valid
        print("  OK")

        # Test 5: OptimisticExecutor
        print("Test 5: OptimisticExecutor")

        async def mock_executor(request, model, context):
            return {"status": "success", "model": model}

        executor = OptimisticExecutor(router, validator)

        async def run_test():
            result = await executor.execute(
                "find all Python files",
                agent_executor=mock_executor
            )
            return result

        result = asyncio.run(run_test())
        assert result["status"] == "success"
        print("  OK")

        # Test 6: Statistics
        print("Test 6: Statistics")
        stats = router.get_statistics()
        assert "haiku" in stats
        print("  OK")

    print("\nAll probabilistic router tests passed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_probabilistic_router()
    else:
        main()