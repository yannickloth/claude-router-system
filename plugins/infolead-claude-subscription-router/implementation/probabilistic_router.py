"""
Probabilistic Router - Confidence-based routing with optimistic execution.

Implements Solution 6 from claude-code-architecture.md:
- Confidence classification for routing decisions
- Post-execution validation
- Optimistic execution with escalation

State file: ~/.claude/infolead-claude-subscription-router/state/routing-history.json

Usage:
    router = ProbabilisticRouter()
    decision = router.route_with_confidence(request, context)

    executor = OptimisticExecutor(router, ResultValidator())
    result = await executor.execute(request, context)

Change Driver: PROBABILISTIC_ROUTING
Changes when: Routing heuristics or validation criteria change

NOTE: This file is now a backward compatibility wrapper.
The refactored implementation is in routing/ package.
All imports and CLI functionality are preserved for backward compatibility.
"""

import sys
from pathlib import Path

# Re-export all public APIs from the refactored package
from routing import (
    # Main classes
    ProbabilisticRouter,
    ResultValidator,
    OptimisticExecutor,

    # Types
    RoutingConfidence,
    RoutingDecision,
    RoutingOutcome,

    # Constants
    STATE_DIR,
    HISTORY_FILE,
)

# Re-export CLI function
from cli.probabilistic_router_cli import run_cli


# Test runner - preserved for backward compatibility
def test_probabilistic_router() -> None:
    """Test probabilistic router functionality."""
    import tempfile
    import asyncio
    from typing import List

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

        # Test 5: Fallback chain populated correctly
        print("Test 5: Fallback chains")
        decision = router.route_with_confidence("fix syntax error in main.py")
        assert decision.fallback_chain == ["sonnet", "opus"], \
            f"Mechanical task should have [sonnet, opus] chain, got {decision.fallback_chain}"

        decision = router.route_with_confidence("find all Python files")
        assert decision.fallback_chain == ["sonnet"], \
            f"Read-only task should have [sonnet] chain, got {decision.fallback_chain}"

        decision = router.route_with_confidence("prove this theorem is correct")
        assert decision.fallback_chain == [], \
            f"Opus task should have empty chain, got {decision.fallback_chain}"

        decision = router.route_with_confidence("design the new authentication system")
        assert decision.fallback_chain == ["opus"], \
            f"Judgment task should have [opus] chain, got {decision.fallback_chain}"
        print("  OK")

        # Test 6: OptimisticExecutor — simple success
        print("Test 6: OptimisticExecutor simple success")

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

        # Test 7: Multi-step escalation (haiku fails → sonnet succeeds)
        print("Test 7: Multi-step escalation")

        call_log: List[str] = []

        async def failing_haiku_executor(request, model, context):
            call_log.append(model)
            if model == "haiku":
                return []  # Empty list — fails results_found validation
            return ["found_result"]

        executor2 = OptimisticExecutor(
            ProbabilisticRouter(history_file=Path(tmpdir) / "test2.json"),
            validator
        )

        async def run_escalation_test():
            return await executor2.execute(
                "find all Python files",
                agent_executor=failing_haiku_executor
            )

        call_log.clear()
        result = asyncio.run(run_escalation_test())
        assert result == ["found_result"], f"Should get sonnet's result, got {result}"
        assert call_log == ["haiku", "sonnet"], \
            f"Should try haiku then sonnet, got {call_log}"
        print("  OK")

        # Test 8: Skip-tier escalation (reasoning failure skips sonnet → opus)
        print("Test 8: Skip-tier escalation")

        # Use a custom validator that produces reasoning-level failure reasons
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
            ProbabilisticRouter(history_file=Path(tmpdir) / "test3.json"),
            skip_validator
        )

        async def run_skip_test():
            return await executor3.execute(
                "fix syntax error in main.py",
                agent_executor=reasoning_failure_executor
            )

        call_log.clear()
        result = asyncio.run(run_skip_test())
        assert result["model"] == "opus", f"Should reach opus, got {result}"
        # Haiku should be tried, sonnet should be skipped, opus should succeed
        assert "haiku" in call_log, f"Should try haiku first, got {call_log}"
        assert "sonnet" not in call_log, \
            f"Should skip sonnet due to reasoning failure, got {call_log}"
        assert "opus" in call_log, f"Should escalate to opus, got {call_log}"
        print("  OK")

        # Test 9: Full chain exhaustion (all tiers fail)
        print("Test 9: Full chain exhaustion")

        async def always_fail_executor(request, model, context):
            call_log.append(model)
            return []  # Empty — always fails results_found

        executor4 = OptimisticExecutor(
            ProbabilisticRouter(history_file=Path(tmpdir) / "test4.json"),
            validator
        )

        async def run_exhaust_test():
            return await executor4.execute(
                "find all Python files",
                agent_executor=always_fail_executor
            )

        call_log.clear()
        result = asyncio.run(run_exhaust_test())
        assert result == [], "Should return last failed result"
        assert call_log == ["haiku", "sonnet"], \
            f"Should try haiku then sonnet (chain is [sonnet] for read-only), got {call_log}"
        print("  OK")

        # Test 10: should_skip_tier
        print("Test 10: should_skip_tier")
        # Mechanical failure → never skip
        assert not validator.should_skip_tier("Python syntax error at line 5: invalid syntax", "sonnet")
        assert not validator.should_skip_tier("No results found", "sonnet")
        # Reasoning failure → skip sonnet
        assert validator.should_skip_tier("Tests failed. Assertion error: incorrect logic", "sonnet")
        assert validator.should_skip_tier("Unexpected behavior in output", "sonnet")
        # Opus is never skipped
        assert not validator.should_skip_tier("Fundamental design flaw detected", "opus")
        print("  OK")

        # Test 11: Statistics
        print("Test 11: Statistics")
        stats = router.get_statistics()
        assert "haiku" in stats
        print("  OK")

    print("\nAll probabilistic router tests passed!")


def main():
    """Main entry point - delegates to CLI."""
    run_cli()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_probabilistic_router()
    else:
        main()
