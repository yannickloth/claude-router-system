"""
Routing Package - Probabilistic routing with confidence-based model selection.

This package implements probabilistic routing that classifies requests by confidence
and uses optimistic execution with validation-based fallback.

Public API:
- ProbabilisticRouter: Main router for confidence-based routing
- ResultValidator: Post-execution validation logic
- OptimisticExecutor: Optimistic execution with fallback chain
- RoutingDecision, RoutingOutcome: Data types
- RoutingConfidence: Confidence enum

Usage:
    from routing import ProbabilisticRouter, ResultValidator, OptimisticExecutor

    router = ProbabilisticRouter()
    decision = router.route_with_confidence(request, context)

    executor = OptimisticExecutor(router, ResultValidator())
    result = await executor.execute(request, context)

Change Driver: PROBABILISTIC_ROUTING
Changes when: Routing logic, validation criteria, or execution strategy changes
"""

# Core router
from .probabilistic_router import ProbabilisticRouter

# Validation
from .result_validator import ResultValidator

# Execution
from .optimistic_executor import OptimisticExecutor

# Types
from .types import (
    RoutingConfidence,
    RoutingDecision,
    RoutingOutcome,
    STATE_DIR,
    HISTORY_FILE,
)

# Version
__version__ = "1.0.0"

# Public API
__all__ = [
    # Main classes
    "ProbabilisticRouter",
    "ResultValidator",
    "OptimisticExecutor",

    # Types
    "RoutingConfidence",
    "RoutingDecision",
    "RoutingOutcome",

    # Constants
    "STATE_DIR",
    "HISTORY_FILE",
]
