"""
Orchestration strategy implementations.

Implements three execution strategies:
1. Single-stage: Fast path for simple mechanical requests
2. Single-stage with monitoring: Normal path with basic tracking
3. Multi-stage: Deliberate path with interpretation and planning

Change Driver: ORCHESTRATION_STRATEGY
Changes when: Strategy implementations or stage logic change
"""

from typing import Dict, Optional, Any

import sys
from pathlib import Path
IMPL_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(IMPL_DIR))
from routing_core import route_request


def execute_single_stage(request: str, context: Optional[Dict]) -> Dict[str, Any]:
    """
    Single-stage orchestration: route → execute (fast path).

    For SIMPLE requests: mechanical operations with explicit targets.
    No interpretation or planning overhead.

    Args:
        request: User's request
        context: Optional context

    Returns:
        Dict with routing and execution results
    """
    # Handle empty requests
    if not request or not request.strip():
        return {
            "routing": None,
            "execution": None,
            "metadata": {
                "strategy": "single_stage",
                "stages": ["route"],
                "error": "empty_request"
            }
        }

    # Route request
    routing = route_request(request, context)

    # For single-stage, we return routing decision for immediate execution
    # (Actual agent execution would happen in calling context)
    return {
        "routing": routing,
        "execution": None,  # Execution handled by caller
        "metadata": {
            "strategy": "single_stage",
            "stages": ["route"],
        }
    }


def execute_single_stage_with_monitoring(request: str, context: Optional[Dict]) -> Dict[str, Any]:
    """
    Single-stage with monitoring: route → execute + monitor (normal path).

    For MODERATE requests: typical operations that may benefit from basic tracking.

    Args:
        request: User's request
        context: Optional context

    Returns:
        Dict with routing and execution results
    """
    # Handle empty requests
    if not request or not request.strip():
        return {
            "routing": None,
            "execution": None,
            "metadata": {
                "strategy": "single_stage_monitored",
                "stages": ["route", "execute_with_monitoring"],
                "monitoring_enabled": True,
                "error": "empty_request"
            }
        }

    # Route request
    routing = route_request(request, context)

    # Add monitoring metadata for caller to track execution
    return {
        "routing": routing,
        "execution": None,  # Execution handled by caller
        "metadata": {
            "strategy": "single_stage_monitored",
            "stages": ["route", "execute_with_monitoring"],
            "monitoring_enabled": True,
        }
    }


def execute_multi_stage(request: str, context: Optional[Dict]) -> Dict[str, Any]:
    """
    Multi-stage orchestration: interpret → plan → execute (deliberate path).

    For COMPLEX requests: ambiguous scope, multi-step work, requires judgment.

    This implements a three-stage pipeline:
    1. INTERPRET: Clarify intent, resolve ambiguities, understand scope
    2. PLAN: Break into steps, identify dependencies, allocate resources
    3. EXECUTE: Carry out plan with coordination

    Args:
        request: User's request
        context: Optional context

    Returns:
        Dict with multi-stage results
    """
    stages_completed = []

    # STAGE 1: INTERPRET
    # Analyze request to understand intent and resolve ambiguities
    interpretation = _interpret_request(request, context)
    stages_completed.append("interpret")

    # STAGE 2: PLAN
    # Create execution plan based on interpretation
    plan = _plan_execution(interpretation, context)
    stages_completed.append("plan")

    # STAGE 3: EXECUTE (routing decision for execution)
    # Route based on plan
    routing = route_request(plan.get("refined_request", request), context)
    stages_completed.append("execute")

    return {
        "routing": routing,
        "execution": None,  # Execution handled by caller
        "metadata": {
            "strategy": "multi_stage",
            "stages": stages_completed,
            "interpretation": interpretation,
            "plan": plan,
        }
    }


def _interpret_request(request: str, context: Optional[Dict]) -> Dict[str, Any]:
    """
    Interpret request to clarify intent and scope.

    This stage identifies:
    - Key intent: What is the user trying to accomplish?
    - Ambiguities: What needs clarification?
    - Scope: How broad/narrow is the request?
    - Constraints: What limitations apply?

    NOTE: In production, this could call an LLM for semantic interpretation.
    For now, using heuristic analysis.

    Args:
        request: User's request
        context: Optional context

    Returns:
        Dict with interpretation results
    """
    request_lower = request.lower()

    # Identify intent keywords
    intent_keywords = {
        "design": "architectural_design",
        "implement": "implementation",
        "refactor": "code_restructuring",
        "debug": "problem_solving",
        "analyze": "analysis",
        "optimize": "optimization",
        "test": "testing",
        "document": "documentation",
    }

    detected_intent = None
    for keyword, intent_type in intent_keywords.items():
        if keyword in request_lower:
            detected_intent = intent_type
            break

    # Identify ambiguities
    ambiguity_signals = ["best", "better", "should", "which", "how to"]
    has_ambiguity = any(signal in request_lower for signal in ambiguity_signals)

    # Estimate scope
    scope_markers = {
        "large": ["all", "every", "entire", "whole", "system-wide"],
        "medium": ["multiple", "several", "some"],
        "small": ["this", "that", "the", "one"],
    }

    scope = "medium"  # default
    for scope_level, markers in scope_markers.items():
        if any(marker in request_lower for marker in markers):
            scope = scope_level
            break

    return {
        "intent": detected_intent or "general_task",
        "has_ambiguity": has_ambiguity,
        "scope": scope,
        "original_request": request,
        "interpretation_confidence": 0.7,
    }


def _plan_execution(interpretation: Dict[str, Any], context: Optional[Dict]) -> Dict[str, Any]:
    """
    Create execution plan based on interpretation.

    This stage produces:
    - Refined request (clarified and scoped)
    - Execution steps (if multi-step)
    - Resource requirements (agent tier, estimated time)
    - Risk assessment

    Args:
        interpretation: Result from _interpret_request
        context: Optional context

    Returns:
        Dict with execution plan
    """
    intent = interpretation["intent"]
    scope = interpretation["scope"]
    original_request = interpretation["original_request"]

    # Determine if multi-step
    is_multi_step = scope in ["large", "medium"] or interpretation["has_ambiguity"]

    # Estimate agent tier needed
    complex_intents = ["architectural_design", "optimization", "problem_solving"]
    needs_opus = intent in complex_intents and scope == "large"
    needs_sonnet = intent in complex_intents or scope in ["medium", "large"]

    recommended_tier = "opus" if needs_opus else "sonnet" if needs_sonnet else "haiku"

    # Create refined request (more specific than original)
    refined_request = original_request
    if interpretation["has_ambiguity"]:
        # In production, this would ask for clarification or make reasonable assumptions
        # For now, we pass through with metadata
        refined_request = f"{original_request} [REQUIRES CLARIFICATION]"

    return {
        "refined_request": refined_request,
        "is_multi_step": is_multi_step,
        "recommended_tier": recommended_tier,
        "estimated_complexity": scope,
        "steps": ["clarify", "execute", "verify"] if is_multi_step else ["execute"],
    }
