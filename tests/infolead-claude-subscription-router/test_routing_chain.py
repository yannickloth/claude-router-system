"""
Tests for the complete routing chain.

Verifies end-to-end routing decisions:
- User request → routing decision → agent selection → model tier

This tests the full chain that would execute when a user makes a request.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from routing_core import route_request, should_escalate, RouterDecision, get_model_tier_from_agent_file


class TestRoutingChainSimpleTasks:
    """Test that simple mechanical tasks route to haiku-general.

    These tests require ROUTER_USE_LLM=1 to pass - keyword matching alone
    cannot semantically understand requests like "correct spelling".
    Without LLM routing, these tests document expected failures.
    """

    @pytest.mark.parametrize("user_request,expected_agent", [
        # Typo fixes - mechanical, haiku
        ("Fix typo in README.md", "haiku-general"),
        ("Correct spelling in main.py", "haiku-general"),
        ("Fix syntax error in config.json", "haiku-general"),

        # Formatting - mechanical, haiku
        ("Format code in src/utils.py", "haiku-general"),
        ("Lint the file test.py", "haiku-general"),

        # Simple renames with explicit paths - mechanical, haiku
        ("Rename foo to bar in helpers.py", "haiku-general"),
    ])
    def test_simple_tasks_route_to_haiku(self, user_request, expected_agent):
        """Simple mechanical tasks with explicit files should route to haiku.

        NOTE: This test requires LLM routing (ROUTER_USE_LLM=1) to pass.
        With keyword-only routing, it will fail due to low confidence scores.
        """
        import os
        if os.environ.get("ROUTER_USE_LLM", "0") != "1":
            pytest.skip("Requires ROUTER_USE_LLM=1 for semantic matching")

        result = route_request(user_request)

        assert result.decision == RouterDecision.DIRECT_TO_AGENT, \
            f"Expected direct routing for '{user_request}', got escalation: {result.reason}"
        assert result.agent == expected_agent, \
            f"Expected {expected_agent} for '{user_request}', got {result.agent}"


class TestRoutingChainComplexTasks:
    """Test that complex tasks escalate to sonnet router."""

    @pytest.mark.parametrize("user_request", [
        # Design/architecture - requires judgment
        "Design a new authentication system",
        "Architect the database schema",
        "Plan the microservices structure",

        # Trade-off decisions - requires judgment
        "Which approach is better for caching?",
        "Should we use REST or GraphQL?",
        "What's the trade-off between X and Y?",

        # Recommendations - requires judgment
        "Recommend a testing strategy",
        "Suggest improvements to the API",

        # Complex analysis
        "Analyze the performance bottlenecks",
        "Review the security implications",
    ])
    def test_complex_tasks_escalate(self, user_request):
        """Complex tasks requiring judgment should escalate."""
        result = route_request(user_request)

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET, \
            f"Expected escalation for '{user_request}', got direct to {result.agent}: {result.reason}"


class TestRoutingChainDestructiveOperations:
    """Test that destructive operations are handled safely."""

    @pytest.mark.parametrize("user_request", [
        # Bulk delete - always escalate
        "Delete all temporary files",
        "Remove all .pyc files",
        "Delete everything in build/",

        # Multi-file operations without explicit paths
        "Delete the old backups",
        "Remove unused imports",
    ])
    def test_bulk_destructive_escalates(self, user_request):
        """Bulk destructive operations should always escalate."""
        result = route_request(user_request)

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET, \
            f"Expected escalation for destructive '{user_request}', got {result.decision.value}"

    @pytest.mark.parametrize("user_request", [
        # Single file delete with explicit path - still needs judgment
        "Delete the file old_config.json",  # Might escalate due to ambiguity
    ])
    def test_single_file_delete_may_escalate(self, user_request):
        """Single file deletes might escalate for safety."""
        result = route_request(user_request)
        # Either outcome is acceptable for single file - test that it doesn't crash
        assert result.decision in [RouterDecision.DIRECT_TO_AGENT, RouterDecision.ESCALATE_TO_SONNET]


class TestRoutingChainMultiObjective:
    """Test that multi-objective requests escalate."""

    @pytest.mark.parametrize("user_request", [
        # Multiple objectives need coordination
        "Fix the bug and add tests",
        "Update the API and document it",
        "Refactor the code, then run the build",
        "Create the file and add the content and commit",

        # Sequential operations
        "First fix the error, then deploy",
        "Update dependencies and run tests",
    ])
    def test_multi_objective_escalates(self, user_request):
        """Requests with multiple objectives should escalate for coordination."""
        result = route_request(user_request)

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET, \
            f"Expected escalation for multi-objective '{user_request}', got {result.decision.value}"


class TestRoutingChainAgentDefinitions:
    """Test that agent definition changes are protected."""

    @pytest.mark.parametrize("user_request", [
        "Edit .claude/agents/router.md",
        "Modify the haiku-general agent",
        "Update .claude/agents/sonnet-general.md",
        "Change the agent definitions",
    ])
    def test_agent_changes_escalate(self, user_request):
        """Changes to agent definitions should escalate."""
        result = route_request(user_request)

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET, \
            f"Expected escalation for agent change '{user_request}', got {result.decision.value}"


class TestRoutingChainCreationTasks:
    """Test that creation tasks are handled appropriately."""

    @pytest.mark.parametrize("user_request", [
        # New features require design decisions
        "Create a new API endpoint",
        "Build a caching layer",
        "Implement user authentication",

        # New files without clear content
        "Create a new module for parsing",
        "Add a new test suite",
    ])
    def test_creation_tasks_escalate(self, user_request):
        """Creation tasks requiring design should escalate."""
        result = route_request(user_request)

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET, \
            f"Expected escalation for creation '{user_request}', got {result.decision.value}"


class TestRoutingChainAmbiguousTargets:
    """Test that ambiguous file operations escalate."""

    @pytest.mark.parametrize("user_request", [
        # No explicit file path
        "Fix the bug",
        "Update the configuration",
        "Change the settings",

        # Vague targets
        "Modify the relevant files",
        "Update the affected code",
    ])
    def test_ambiguous_targets_escalate(self, user_request):
        """Operations without explicit targets should escalate."""
        result = route_request(user_request)

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET, \
            f"Expected escalation for ambiguous '{user_request}', got {result.decision.value}"


class TestRoutingChainConfidenceScores:
    """Test that confidence scores are reasonable."""

    def test_high_confidence_for_clear_matches(self):
        """Clear mechanical tasks should have high confidence."""
        result = route_request("Fix typo in README.md")

        if result.decision == RouterDecision.DIRECT_TO_AGENT:
            assert result.confidence >= 0.8, \
                f"Expected high confidence for clear match, got {result.confidence}"

    def test_escalation_includes_reason(self):
        """Escalations should always include a reason."""
        result = route_request("Design a complex system")

        assert result.reason is not None
        assert len(result.reason) > 0

    def test_confidence_in_valid_range(self):
        """Confidence should always be between 0 and 1."""
        test_requests = [
            "Fix typo",
            "Design architecture",
            "Delete all files",
            "xyz qwerty asdf",  # Nonsense
        ]

        for request in test_requests:
            result = route_request(request)
            assert 0.0 <= result.confidence <= 1.0, \
                f"Confidence {result.confidence} out of range for '{request}'"


class TestRoutingChainModelTierMapping:
    """Test that agent names correctly map to model tiers."""

    # This verifies the hook's model tier detection logic
    AGENT_TO_TIER = {
        "haiku-general": "haiku",
        "sonnet-general": "sonnet",
        "opus-general": "opus",
        "router": "sonnet",
        "router-escalation": "opus",
    }

    def _get_model_tier(self, agent_type: str) -> str:
        """Get model tier from agent file or fallback to substring matching."""
        return get_model_tier_from_agent_file(agent_type)

    @pytest.mark.parametrize("agent,expected_tier", [
        ("haiku-general", "haiku"),
        ("sonnet-general", "sonnet"),
        ("opus-general", "opus"),
        ("router", "sonnet"),
        ("router-escalation", "opus"),
        ("custom-haiku-agent", "haiku"),
        ("my-opus-analyzer", "opus"),
        ("unknown-agent", "sonnet"),  # Default
    ])
    def test_model_tier_mapping(self, agent, expected_tier):
        """Agent names should map to correct model tiers."""
        tier = self._get_model_tier(agent)
        assert tier == expected_tier, \
            f"Expected {expected_tier} for {agent}, got {tier}"


class TestRoutingChainEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_request(self):
        """Empty request should raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            route_request("")

    def test_very_long_request(self):
        """Very long requests should still work."""
        request = "Fix " * 1000 + "typo in README.md"
        result = route_request(request)
        # Should not crash
        assert result.decision in [RouterDecision.DIRECT_TO_AGENT, RouterDecision.ESCALATE_TO_SONNET]

    def test_special_characters(self):
        """Special characters should not break routing."""
        requests = [
            "Fix bug in file$#%.txt",
            "Update config with special@chars!",
            "Edit path/to/file (copy).py",
        ]
        for request in requests:
            result = route_request(request)
            # Should not crash
            assert result is not None

    def test_unicode_request(self):
        """Unicode characters should be handled."""
        result = route_request("Fix typo: résumé → resume in docs.md")
        assert result is not None

    def test_case_insensitivity(self):
        """Keywords should match case-insensitively."""
        requests = [
            ("FIX TYPO in README.md", "Fix typo in README.md"),
            ("DESIGN architecture", "Design architecture"),
        ]
        for upper, lower in requests:
            upper_result = route_request(upper)
            lower_result = route_request(lower)
            assert upper_result.decision == lower_result.decision, \
                f"Case sensitivity issue: '{upper}' vs '{lower}'"


class TestRoutingChainConsistency:
    """Test that routing is deterministic and consistent."""

    def test_same_request_same_result(self):
        """Same request should always produce same result."""
        request = "Fix typo in README.md"

        results = [route_request(request) for _ in range(10)]

        decisions = [r.decision for r in results]
        agents = [r.agent for r in results]

        assert len(set(decisions)) == 1, "Decision should be consistent"
        assert len(set(agents)) == 1, "Agent should be consistent"

    def test_similar_requests_similar_routing(self):
        """Semantically similar requests should route similarly."""
        similar_pairs = [
            ("Fix typo in README.md", "Correct typo in README.md"),
            ("Design architecture", "Architect the system"),
        ]

        for req1, req2 in similar_pairs:
            result1 = route_request(req1)
            result2 = route_request(req2)

            # At minimum, both should escalate or both should route directly
            # (actual agent might differ based on keywords)
            assert result1.decision == result2.decision, \
                f"Similar requests routed differently: '{req1}' -> {result1.decision.value}, '{req2}' -> {result2.decision.value}"


class TestRoutingChainFullPipeline:
    """Test the complete pipeline from request to execution context."""

    def test_haiku_pipeline(self):
        """Test complete pipeline for haiku-routable request.

        NOTE: Requires ROUTER_USE_LLM=1 for semantic matching.
        """
        import os
        if os.environ.get("ROUTER_USE_LLM", "0") != "1":
            pytest.skip("Requires ROUTER_USE_LLM=1 for semantic matching")

        request = "Fix typo in README.md"
        result = route_request(request)

        # Verify complete result structure
        assert result.decision == RouterDecision.DIRECT_TO_AGENT
        assert result.agent == "haiku-general"
        assert result.confidence > 0
        assert result.reason is not None

        # Verify model tier would be correct
        assert "haiku" in result.agent.lower()

    def test_escalation_pipeline(self):
        """Test complete pipeline for escalated request."""
        request = "Design a new microservices architecture"
        result = route_request(request)

        # Verify complete result structure
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET
        assert result.reason is not None
        assert len(result.reason) > 10  # Should have meaningful reason

    def test_result_serialization(self):
        """Test that results can be serialized (for logging/metrics)."""
        result = route_request("Fix typo in README.md")

        # to_dict should work
        result_dict = result.to_dict()

        assert "decision" in result_dict
        assert "agent" in result_dict
        assert "reason" in result_dict
        assert "confidence" in result_dict

        # Values should be JSON-serializable types
        assert isinstance(result_dict["decision"], str)
        assert result_dict["agent"] is None or isinstance(result_dict["agent"], str)
        assert isinstance(result_dict["reason"], str)
        assert isinstance(result_dict["confidence"], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
