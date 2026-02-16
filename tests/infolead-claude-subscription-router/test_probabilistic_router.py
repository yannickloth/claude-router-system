#!/usr/bin/env python3
"""
Pytest suite for probabilistic_router.py

Ported from embedded tests in implementation/probabilistic_router.py

Change Driver: TESTING_REQUIREMENTS
"""

import asyncio
import tempfile
from pathlib import Path
from typing import List

import pytest

# Add implementation directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins/infolead-claude-subscription-router/implementation"))

from probabilistic_router import (
    ProbabilisticRouter,
    RoutingConfidence,
    ResultValidator,
    OptimisticExecutor,
)


@pytest.fixture
def temp_history_dir():
    """Create temporary directory for test history files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def router(temp_history_dir):
    """Create ProbabilisticRouter with temp history file."""
    history_file = temp_history_dir / "test-history.json"
    return ProbabilisticRouter(history_file=history_file)


@pytest.fixture
def validator():
    """Create ResultValidator instance."""
    return ResultValidator()


@pytest.fixture
def executor(router, validator):
    """Create OptimisticExecutor instance."""
    return OptimisticExecutor(router, validator)


def test_pattern_matching_mechanical_task(router):
    """Test pattern matching for mechanical tasks (HIGH confidence for Haiku)."""
    decision = router.route_with_confidence("fix syntax error in main.py")
    assert decision.recommended_model == "haiku"
    assert decision.confidence == RoutingConfidence.HIGH


def test_pattern_matching_readonly_task(router):
    """Test pattern matching for read-only tasks (HIGH confidence for Haiku)."""
    decision = router.route_with_confidence("find all Python files")
    assert decision.recommended_model == "haiku"
    assert decision.confidence == RoutingConfidence.HIGH


def test_pattern_matching_judgment_task(router):
    """Test pattern matching for judgment tasks (HIGH confidence for Sonnet)."""
    decision = router.route_with_confidence("design the new authentication system")
    assert decision.recommended_model == "sonnet"
    assert decision.confidence == RoutingConfidence.HIGH


def test_pattern_matching_complex_task(router):
    """Test pattern matching for complex reasoning tasks (HIGH confidence for Opus)."""
    decision = router.route_with_confidence("prove this theorem is correct")
    assert decision.recommended_model == "opus"
    assert decision.confidence == RoutingConfidence.HIGH


def test_record_outcomes_success_rate(router):
    """Test recording outcomes and calculating success rates."""
    router.record_outcome("haiku", True, "mechanical")
    router.record_outcome("haiku", True, "mechanical")
    router.record_outcome("haiku", False, "mechanical")

    rate = router._get_success_rate("haiku", "mechanical")
    assert abs(rate - 0.667) < 0.01, f"Expected ~0.667, got {rate}"


def test_result_validator_python_syntax_valid(temp_history_dir):
    """Test Python syntax validation for valid code."""
    validator = ResultValidator()

    test_py = temp_history_dir / "test.py"
    test_py.write_text("def foo():\n    return 1\n")

    is_valid, _ = validator._validate_python_syntax(str(test_py))
    assert is_valid


def test_result_validator_python_syntax_invalid(temp_history_dir):
    """Test Python syntax validation for invalid code."""
    validator = ResultValidator()

    invalid_py = temp_history_dir / "invalid.py"
    invalid_py.write_text("def foo(\n")

    is_valid, reason = validator._validate_python_syntax(str(invalid_py))
    assert not is_valid
    assert reason is not None


def test_result_validator_results_found_with_results(validator):
    """Test results_found validation when results exist."""
    is_valid, _ = validator._validate_results_found(["result1", "result2"], {})
    assert is_valid


def test_result_validator_results_found_empty(validator):
    """Test results_found validation with empty results."""
    is_valid, _ = validator._validate_results_found([], {})
    assert not is_valid


def test_result_validator_results_found_dict_empty(validator):
    """Test results_found validation with empty dict results."""
    is_valid, _ = validator._validate_results_found({"results": []}, {})
    assert not is_valid


def test_fallback_chain_mechanical(router):
    """Test fallback chain for mechanical tasks."""
    decision = router.route_with_confidence("fix syntax error in main.py")
    assert decision.fallback_chain == ["sonnet", "opus"], \
        f"Mechanical task should have [sonnet, opus] chain, got {decision.fallback_chain}"


def test_fallback_chain_readonly(router):
    """Test fallback chain for read-only tasks."""
    decision = router.route_with_confidence("find all Python files")
    assert decision.fallback_chain == ["sonnet"], \
        f"Read-only task should have [sonnet] chain, got {decision.fallback_chain}"


def test_fallback_chain_complex(router):
    """Test fallback chain for complex tasks (Opus has no fallback)."""
    decision = router.route_with_confidence("prove this theorem is correct")
    assert decision.fallback_chain == [], \
        f"Opus task should have empty chain, got {decision.fallback_chain}"


def test_fallback_chain_judgment(router):
    """Test fallback chain for judgment tasks."""
    decision = router.route_with_confidence("design the new authentication system")
    assert decision.fallback_chain == ["opus"], \
        f"Judgment task should have [opus] chain, got {decision.fallback_chain}"


@pytest.mark.asyncio
async def test_optimistic_executor_simple_success(executor):
    """Test OptimisticExecutor with successful execution."""
    async def mock_executor(request, model, context):
        return {"status": "success", "model": model}

    result = await executor.execute(
        "find all Python files",
        agent_executor=mock_executor
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_optimistic_executor_escalation(router, validator, temp_history_dir):
    """Test escalation from haiku to sonnet."""
    call_log: List[str] = []

    async def failing_haiku_executor(request, model, context):
        call_log.append(model)
        if model == "haiku":
            return []  # Empty list — fails results_found validation
        return ["found_result"]

    executor2 = OptimisticExecutor(
        ProbabilisticRouter(history_file=temp_history_dir / "test2.json"),
        validator
    )

    result = await executor2.execute(
        "find all Python files",
        agent_executor=failing_haiku_executor
    )

    assert result == ["found_result"], f"Should get sonnet's result, got {result}"
    assert call_log == ["haiku", "sonnet"], \
        f"Should try haiku then sonnet, got {call_log}"


@pytest.mark.asyncio
async def test_optimistic_executor_skip_tier(router, temp_history_dir):
    """Test skip-tier escalation when reasoning failure detected."""
    call_log: List[str] = []

    class SkipTierValidator(ResultValidator):
        def validate_result(self, result, validation_criteria, context):
            if isinstance(result, dict) and result.get("status") == "success":
                return True, None
            return False, "Tests failed. Assertion error: incorrect logic in algorithm"

    skip_validator = SkipTierValidator()

    async def reasoning_failure_executor(request, model, context):
        call_log.append(model)
        if model == "opus":
            return {"status": "success", "model": model}
        return {"status": "failed", "model": model}

    executor3 = OptimisticExecutor(
        ProbabilisticRouter(history_file=temp_history_dir / "test3.json"),
        skip_validator
    )

    result = await executor3.execute(
        "fix syntax error in main.py",
        agent_executor=reasoning_failure_executor
    )

    assert result["model"] == "opus", f"Should reach opus, got {result}"
    # Haiku should be tried, sonnet should be skipped, opus should succeed
    assert "haiku" in call_log, f"Should try haiku first, got {call_log}"
    assert "sonnet" not in call_log, \
        f"Should skip sonnet due to reasoning failure, got {call_log}"
    assert "opus" in call_log, f"Should escalate to opus, got {call_log}"


@pytest.mark.asyncio
async def test_optimistic_executor_chain_exhaustion(router, validator, temp_history_dir):
    """Test behavior when all fallback tiers fail."""
    call_log: List[str] = []

    async def always_fail_executor(request, model, context):
        call_log.append(model)
        return []  # Empty — always fails results_found

    executor4 = OptimisticExecutor(
        ProbabilisticRouter(history_file=temp_history_dir / "test4.json"),
        validator
    )

    result = await executor4.execute(
        "find all Python files",
        agent_executor=always_fail_executor
    )

    assert result == [], "Should return last failed result"
    assert call_log == ["haiku", "sonnet"], \
        f"Should try haiku then sonnet (chain is [sonnet] for read-only), got {call_log}"


def test_should_skip_tier_mechanical_never_skip(validator):
    """Test that mechanical failures never trigger tier skipping."""
    assert not validator.should_skip_tier("Python syntax error at line 5: invalid syntax", "sonnet")
    assert not validator.should_skip_tier("No results found", "sonnet")
    assert not validator.should_skip_tier("Brace mismatch: 5 open, 3 close", "sonnet")


def test_should_skip_tier_reasoning_skip_sonnet(validator):
    """Test that reasoning failures skip to higher tiers."""
    assert validator.should_skip_tier("Tests failed. Assertion error: incorrect logic", "sonnet")
    assert validator.should_skip_tier("Unexpected behavior in output", "sonnet")
    assert validator.should_skip_tier("Design flaw detected in architecture", "sonnet")


def test_should_skip_tier_opus_never_skipped(validator):
    """Test that Opus is never skipped regardless of failure."""
    assert not validator.should_skip_tier("Fundamental design flaw detected", "opus")
    assert not validator.should_skip_tier("Any failure reason", "opus")


def test_get_statistics(router):
    """Test retrieving router statistics."""
    router.record_outcome("haiku", True, "mechanical")
    router.record_outcome("haiku", False, "mechanical")

    stats = router.get_statistics()
    assert "haiku" in stats
    assert "mechanical" in stats["haiku"]
    assert stats["haiku"]["mechanical"]["attempts"] == 2
    assert stats["haiku"]["mechanical"]["successes"] == 1


def test_executor_escalation_rate(executor):
    """Test executor escalation rate calculation."""
    executor.total_executions = 10
    executor.escalation_count = 3

    rate = executor.get_escalation_rate()
    assert abs(rate - 0.3) < 0.01


def test_executor_statistics(executor):
    """Test executor statistics collection."""
    executor.total_executions = 5
    executor.escalation_count = 1

    stats = executor.get_statistics()
    assert stats["total_executions"] == 5
    assert stats["escalation_count"] == 1
    assert "escalation_rate" in stats
    assert "router_stats" in stats
