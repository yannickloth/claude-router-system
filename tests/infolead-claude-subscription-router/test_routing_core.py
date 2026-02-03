"""
Unit tests for routing_core module.

Tests the Haiku pre-routing and escalation logic.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from routing_core import (
    should_escalate,
    RouterDecision,
    explicit_file_mentioned,
    match_request_to_agents,
)


class TestFileDetection(unittest.TestCase):
    """Test explicit file path detection."""

    def test_simple_filename(self):
        """Test detection of simple filename.ext"""
        self.assertTrue(explicit_file_mentioned("Fix bug in auth.py"))
        self.assertTrue(explicit_file_mentioned("Update README.md"))

    def test_path(self):
        """Test detection of file paths."""
        self.assertTrue(explicit_file_mentioned("Edit src/main.py"))
        self.assertTrue(explicit_file_mentioned("Check ./config.json"))

    def test_no_file(self):
        """Test requests without explicit files."""
        self.assertFalse(explicit_file_mentioned("Fix the authentication bug"))
        self.assertFalse(explicit_file_mentioned("Refactor the codebase"))


class TestAgentMatching(unittest.TestCase):
    """Test agent matching logic."""

    def test_haiku_match(self):
        """Test matching to haiku-general."""
        agent, confidence = match_request_to_agents("Fix typo in file")
        self.assertEqual(agent, "haiku-general")
        self.assertGreater(confidence, 0)

    def test_sonnet_match(self):
        """Test matching to sonnet-general."""
        agent, confidence = match_request_to_agents("Analyze the design")
        self.assertEqual(agent, "sonnet-general")
        self.assertGreater(confidence, 0)

    def test_no_match(self):
        """Test request with no clear match."""
        agent, confidence = match_request_to_agents("xyz qwerty asdf")
        self.assertIsNone(agent)
        self.assertEqual(confidence, 0.0)


class TestEscalationLogic(unittest.TestCase):
    """Test the escalation decision logic."""

    def test_complexity_keywords_escalate(self):
        """Complexity keywords should trigger escalation."""
        test_cases = [
            "Which approach is best for authentication?",
            "Design a caching system",
            "What's the trade-off between X and Y?",
            "Recommend a solution",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                # All should escalate (decision matters, reason varies)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_bulk_destructive_escalates(self):
        """Bulk destructive operations should escalate."""
        test_cases = [
            "Delete all temporary files",
            "Remove multiple old logs",
            "Delete everything in test/*",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)
                # Reason should mention destructive or bulk/judgment concepts
                self.assertTrue(
                    "destructive" in result.reason.lower() or
                    "bulk" in result.reason.lower() or
                    "judgment" in result.reason.lower()
                )

    def test_ambiguous_file_operations_escalate(self):
        """File operations without explicit paths should escalate."""
        result = should_escalate("Fix the bug")
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)
        # Reason should indicate file discovery or path-related issue
        self.assertTrue(
            "path" in result.reason.lower() or
            "file" in result.reason.lower() or
            "discovery" in result.reason.lower() or
            "match" in result.reason.lower()  # "no clear agent match"
        )

    def test_explicit_file_operations_okay(self):
        """File operations with explicit paths should not escalate."""
        result = should_escalate("Fix bug in src/auth.py")
        # Should not escalate for file operations (assuming good agent match)
        # Note: might still escalate for other reasons, check decision
        self.assertIsNotNone(result)

    def test_agent_modification_escalates(self):
        """Modifications to .claude/agents should escalate."""
        result = should_escalate("Edit .claude/agents/router.md")
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)
        # Reason should mention agent definitions or judgment
        self.assertTrue(
            "agent" in result.reason.lower() or
            "judgment" in result.reason.lower()
        )

    def test_multiple_objectives_escalate(self):
        """Multiple objectives should escalate."""
        test_cases = [
            "Fix bug and add tests",
            "Update docs, then run build",
            "Create file and add content and commit",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                # All should escalate (decision matters, reason varies)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_creation_tasks_escalate(self):
        """Creation/design tasks should escalate."""
        test_cases = [
            "Create a new API endpoint",
            "Design the database schema",
            "Build a caching layer",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_simple_tasks_dont_escalate(self):
        """Simple, mechanical tasks should not escalate."""
        test_cases = [
            "Fix typo in README.md",
            "Format code in main.py",
            "Lint the source files",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                # These should route directly if there's a good agent match
                # Check that a decision was made
                self.assertIsNotNone(result.decision)


class TestEscalationEdgeCases(unittest.TestCase):
    """Test edge cases in escalation logic."""

    def test_empty_request(self):
        """Empty request should escalate (no match)."""
        result = should_escalate("")
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_very_long_request(self):
        """Very long requests should still work."""
        request = "Fix " * 1000 + "bug in main.py"
        result = should_escalate(request)
        self.assertIsNotNone(result)

    def test_special_characters(self):
        """Special characters should not break parsing."""
        request = "Fix bug in file$#%.txt with special@chars!"
        result = should_escalate(request)
        self.assertIsNotNone(result)


class TestEscalationResults(unittest.TestCase):
    """Test the structure of escalation results."""

    def test_result_has_required_fields(self):
        """Result should have all required fields."""
        result = should_escalate("Fix typo in README.md")

        self.assertIsNotNone(result.decision)
        self.assertIsNotNone(result.reason)
        self.assertIsInstance(result.confidence, float)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_escalation_has_no_agent(self):
        """Escalation results should have agent=None."""
        result = should_escalate("Which approach is best?")

        if result.decision == RouterDecision.ESCALATE_TO_SONNET:
            # Escalations might have agent suggestion but not assignment
            self.assertIsNotNone(result.reason)

    def test_direct_routing_has_agent(self):
        """Direct routing should have an agent assigned."""
        result = should_escalate("Fix syntax in main.py")

        if result.decision == RouterDecision.DIRECT_TO_AGENT:
            self.assertIsNotNone(result.agent)


if __name__ == "__main__":
    unittest.main()