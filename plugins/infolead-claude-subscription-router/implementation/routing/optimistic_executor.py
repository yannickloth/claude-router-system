"""
Optimistic Executor - Execute with cheap model, validate, escalate if needed.

Implements optimistic execution strategy: try the recommended (cheap) model first,
validate the result, and walk the fallback chain if validation fails.

Usage:
    executor = OptimisticExecutor(router, validator)
    result = await executor.execute(request, context, agent_executor=my_executor)

Change Driver: EXECUTION_STRATEGY
Changes when: Execution or escalation strategy changes
"""

import inspect
import sys
from typing import Any, Callable, Dict, Optional

from .probabilistic_router import ProbabilisticRouter
from .result_validator import ResultValidator


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
        Try cheap model first, walk the fallback chain on validation failure.
        Tiers may be skipped when the failure reveals complexity beyond that tier.

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
        if decision.fallback_chain:
            print(f"[routing] Fallback chain: {' → '.join(decision.fallback_chain)}",
                  file=sys.stderr)

        self.total_executions += 1
        task_type = self._classify_task_type(request)
        escalation_path = [decision.recommended_model]

        # Execute with recommended model
        result = await self._execute_with_model(
            request, decision.recommended_model, context, executor
        )

        # If no validation criteria, assume success
        if not decision.validation_criteria:
            self.router.record_outcome(
                decision.recommended_model, success=True, task_type=task_type
            )
            return result

        # Validate
        is_valid, failure_reason = self.validator.validate_result(
            result, decision.validation_criteria, context
        )

        if is_valid:
            self.router.record_outcome(
                decision.recommended_model, success=True, task_type=task_type
            )
            return result

        # Validation failed — walk the fallback chain
        print(f"[validation] Failed: {failure_reason}", file=sys.stderr)
        self.router.record_outcome(
            decision.recommended_model, success=False, task_type=task_type
        )

        if not decision.fallback_chain:
            print("[routing] No fallback chain available", file=sys.stderr)
            return result

        self.escalation_count += 1
        last_failure_reason = failure_reason

        for fallback_model in decision.fallback_chain:
            # Check if this tier should be skipped based on the failure
            if self.validator.should_skip_tier(last_failure_reason, fallback_model):
                print(f"[routing] Skipping {fallback_model} — failure exceeds its tier",
                      file=sys.stderr)
                continue

            print(f"[routing] Escalating to {fallback_model}...", file=sys.stderr)
            escalation_path.append(fallback_model)

            result = await self._execute_with_model(
                request, fallback_model, context, executor
            )

            is_valid, failure_reason = self.validator.validate_result(
                result, decision.validation_criteria, context
            )

            if is_valid:
                self.router.record_outcome(
                    fallback_model, success=True, task_type=task_type
                )
                print(f"[routing] Escalation path: {' → '.join(escalation_path)}",
                      file=sys.stderr)
                return result

            # This tier also failed — record and continue
            print(f"[validation] {fallback_model} also failed: {failure_reason}",
                  file=sys.stderr)
            self.router.record_outcome(
                fallback_model, success=False, task_type=task_type
            )
            last_failure_reason = failure_reason

        # All tiers exhausted
        print(f"[routing] All tiers exhausted. Path: {' → '.join(escalation_path)}",
              file=sys.stderr)
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
