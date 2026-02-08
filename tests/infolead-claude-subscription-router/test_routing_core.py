"""
Unit tests for routing_core module.

Tests the Haiku pre-routing, escalation logic, agent matching,
input validation, and real-world routing scenarios.

Merged from tests/ and plugins/.../tests/ to consolidate all
routing_core coverage in one place.
"""

import unittest
import sys
from pathlib import Path

# Add implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from routing_core import (
    should_escalate,
    route_request,
    RouterDecision,
    RoutingResult,
    explicit_file_mentioned,
    match_request_to_agents,
    match_request_to_agents_keywords,
    get_model_tier_from_agent_file,
)


class TestFileDetection(unittest.TestCase):
    """Test explicit file path detection."""

    def test_simple_filename(self):
        """Detect simple filename.ext patterns."""
        self.assertTrue(explicit_file_mentioned("Fix bug in auth.py"))
        self.assertTrue(explicit_file_mentioned("Update README.md"))
        self.assertTrue(explicit_file_mentioned("Read config.json"))
        self.assertTrue(explicit_file_mentioned("Update styles.css"))
        self.assertTrue(explicit_file_mentioned("Fix bug.java"))

    def test_path(self):
        """Detect file paths with directories."""
        self.assertTrue(explicit_file_mentioned("Edit src/main.py"))
        self.assertTrue(explicit_file_mentioned("Check ./config.json"))
        self.assertTrue(explicit_file_mentioned("Update /home/user/config.json"))
        self.assertTrue(explicit_file_mentioned("Modify ~/Documents/notes.txt"))
        self.assertTrue(explicit_file_mentioned("Read ../config/settings.yaml"))
        self.assertTrue(explicit_file_mentioned("Update ./scripts/deploy.sh"))

    def test_no_file(self):
        """Requests without explicit files should not match."""
        self.assertFalse(explicit_file_mentioned("Fix the authentication bug"))
        self.assertFalse(explicit_file_mentioned("Refactor the codebase"))
        self.assertFalse(explicit_file_mentioned(""))
        self.assertFalse(explicit_file_mentioned("no files here"))
        self.assertFalse(explicit_file_mentioned("just talking"))
        self.assertFalse(explicit_file_mentioned("import export data"))


class TestAgentMatchingKeywords(unittest.TestCase):
    """Test keyword-based agent matching."""

    def test_haiku_high_confidence_with_file(self):
        """High-confidence haiku patterns with explicit files."""
        agent, conf = match_request_to_agents_keywords("Fix typo in README.md")
        self.assertEqual(agent, "haiku-general")
        self.assertGreaterEqual(conf, 0.90)

        agent, conf = match_request_to_agents_keywords("Format code in main.py")
        self.assertEqual(agent, "haiku-general")
        self.assertGreaterEqual(conf, 0.90)

    def test_haiku_rename_pattern(self):
        """Rename pattern with file should match haiku."""
        agent, conf = match_request_to_agents_keywords("Rename variable foo to bar in utils.py")
        self.assertEqual(agent, "haiku-general")
        self.assertGreaterEqual(conf, 0.90)

    def test_haiku_needs_explicit_file(self):
        """Haiku keywords without file should not route at high confidence."""
        agent, conf = match_request_to_agents_keywords("Fix typo")
        if agent == "haiku-general":
            self.assertLess(conf, 0.8)

    def test_sonnet_keywords(self):
        """Sonnet reasoning keywords."""
        agent, conf = match_request_to_agents_keywords("Analyze the codebase")
        self.assertEqual(agent, "sonnet-general")
        self.assertGreater(conf, 0.5)

        agent, conf = match_request_to_agents_keywords("Refactor this module")
        self.assertEqual(agent, "sonnet-general")

    def test_opus_keywords(self):
        """Opus complex reasoning keywords."""
        agent, conf = match_request_to_agents_keywords("Prove correctness of algorithm")
        self.assertEqual(agent, "opus-general")
        self.assertGreater(conf, 0.7)

        agent, conf = match_request_to_agents_keywords("Mathematical verification needed")
        self.assertEqual(agent, "opus-general")

    def test_no_clear_match(self):
        """Ambiguous requests should not match."""
        agent, conf = match_request_to_agents_keywords("Do something")
        self.assertTrue(agent is None or conf < 0.7)

    def test_explicit_file_alone_routes_haiku(self):
        """Request with explicit file but no strong keywords."""
        agent, conf = match_request_to_agents_keywords("Update config.json")
        self.assertEqual(agent, "haiku-general")
        self.assertGreaterEqual(conf, 0.6)


class TestAgentMatching(unittest.TestCase):
    """Test the main match_request_to_agents dispatcher."""

    def test_haiku_match(self):
        """Haiku-general match for mechanical task."""
        agent, confidence = match_request_to_agents("Fix typo in README.md")
        self.assertEqual(agent, "haiku-general")
        self.assertGreater(confidence, 0)

    def test_sonnet_match(self):
        """Sonnet-general match for reasoning task."""
        agent, confidence = match_request_to_agents("Analyze the design")
        self.assertEqual(agent, "sonnet-general")
        self.assertGreater(confidence, 0)

    def test_no_match(self):
        """No clear match for gibberish."""
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
            "This is a complex trade-off",
            "I need to decide between two options",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_bulk_destructive_escalates(self):
        """Bulk destructive operations should escalate."""
        test_cases = [
            "Delete all temporary files",
            "Remove multiple old logs",
            "Delete everything in test/*",
            "Remove every backup",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)
                self.assertTrue(
                    "destructive" in result.reason.lower() or
                    "bulk" in result.reason.lower() or
                    "judgment" in result.reason.lower()
                )

    def test_ambiguous_file_operations_escalate(self):
        """File operations without explicit paths should escalate."""
        for request in ["Fix the bug", "Edit the main file", "Delete the config"]:
            with self.subTest(request=request):
                result = should_escalate(request)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_explicit_file_operations_okay(self):
        """File operations with explicit paths should not escalate."""
        result = should_escalate("Fix bug in src/auth.py")
        self.assertIsNotNone(result)

    def test_agent_modification_escalates(self):
        """Modifications to .claude/agents should escalate."""
        result = should_escalate("Edit .claude/agents/router.md")
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)
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
            "Create API endpoint and add tests and update docs",
            "First do this, then do that, after that do this",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_creation_tasks_escalate(self):
        """Creation/design tasks should escalate."""
        test_cases = [
            "Create a new API endpoint",
            "Design the database schema",
            "Build a caching layer",
            "Implement user login",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_simple_tasks_dont_escalate(self):
        """Simple, mechanical tasks should route directly."""
        test_cases = [
            "Fix typo in README.md",
            "Format code in main.py",
            "Lint the source files",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = should_escalate(request)
                self.assertIsNotNone(result.decision)

    def test_simple_mechanical_direct(self):
        """Simple mechanical tasks should route direct with high confidence."""
        result = should_escalate("Fix typo in README.md")
        self.assertEqual(result.decision, RouterDecision.DIRECT_TO_AGENT)
        self.assertEqual(result.agent, "haiku-general")
        self.assertGreaterEqual(result.confidence, 0.8)

        result = should_escalate("Format code in main.py")
        self.assertEqual(result.decision, RouterDecision.DIRECT_TO_AGENT)
        self.assertEqual(result.agent, "haiku-general")

    def test_low_confidence_escalates(self):
        """Low confidence matches should escalate."""
        result = should_escalate("Fix the bug")  # Ambiguous, no file
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)


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
        self.assertIsNotNone(should_escalate("Fix bug in file$#%.txt with special@chars!"))

    def test_special_characters_regex(self):
        """Regex patterns in requests should not break routing."""
        result = route_request("Fix regex: /\\w+@\\w+\\.\\w+/ in validator.py")
        self.assertIsInstance(result, RoutingResult)

    def test_special_characters_unicode(self):
        """Unicode in requests should not break routing."""
        result = route_request("Fix typo in café.txt 中文测试")
        self.assertIsInstance(result, RoutingResult)

    def test_special_characters_shell_metacharacters(self):
        """Shell metacharacters should not break routing."""
        result = route_request("Fix file with spaces & special chars; $(pwd)")
        self.assertIsInstance(result, RoutingResult)

    def test_newlines_in_request(self):
        """Multi-line requests should work."""
        result = route_request("Fix typo\nin README.md\nline 42")
        self.assertIsInstance(result, RoutingResult)

    def test_tabs_in_request(self):
        """Requests with tabs should work."""
        result = route_request("Fix\ttypo\tin\tREADME.md")
        self.assertIsInstance(result, RoutingResult)

    def test_quotes_in_request(self):
        """Requests with various quote types should work."""
        result = route_request('Fix "typo" in \'file.txt\'')
        self.assertIsInstance(result, RoutingResult)


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
        """Escalation results may have agent suggestion but always have reason."""
        result = should_escalate("Which approach is best?")
        if result.decision == RouterDecision.ESCALATE_TO_SONNET:
            self.assertIsNotNone(result.reason)

    def test_direct_routing_has_agent(self):
        """Direct routing should have an agent assigned."""
        result = should_escalate("Fix syntax in main.py")
        if result.decision == RouterDecision.DIRECT_TO_AGENT:
            self.assertIsNotNone(result.agent)


class TestRouteRequest(unittest.TestCase):
    """Test main routing entry point with input validation."""

    def test_basic_routing_direct(self):
        """Basic direct routing."""
        result = route_request("Fix typo in README.md")
        self.assertIsInstance(result, RoutingResult)
        self.assertEqual(result.decision, RouterDecision.DIRECT_TO_AGENT)
        self.assertIsNotNone(result.agent)

    def test_basic_routing_escalate(self):
        """Basic escalation routing."""
        result = route_request("Design a new system")
        self.assertIsInstance(result, RoutingResult)
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_with_context(self):
        """Routing with context dict."""
        result = route_request("Fix bug", context={"project": "test"})
        self.assertIsInstance(result, RoutingResult)

    def test_none_request_raises_type_error(self):
        """None request should raise TypeError."""
        with self.assertRaises(TypeError):
            route_request(None)

    def test_empty_string_raises_value_error(self):
        """Empty string should raise ValueError."""
        with self.assertRaises(ValueError):
            route_request("")

    def test_whitespace_only_raises_value_error(self):
        """Whitespace-only should raise ValueError."""
        with self.assertRaises(ValueError):
            route_request("   \t\n   ")

    def test_very_long_request_raises_value_error(self):
        """Requests over 10k chars should raise ValueError."""
        long_request = "Fix typo in README.md" + " and also update the documentation" * 500
        with self.assertRaises(ValueError) as ctx:
            route_request(long_request)
        self.assertIn("too long", str(ctx.exception))

    def test_reasonable_long_request_works(self):
        """Requests under 10k chars should work."""
        long_request = "Fix typo in README.md" + " and also update the documentation" * 100
        result = route_request(long_request)
        self.assertIsInstance(result, RoutingResult)

    def test_invalid_request_type_int(self):
        """Integer request should raise TypeError."""
        with self.assertRaises(TypeError):
            route_request(123)

    def test_invalid_request_type_list(self):
        """List request should raise TypeError."""
        with self.assertRaises(TypeError):
            route_request(['test'])

    def test_invalid_context_type(self):
        """Invalid context type should raise TypeError."""
        with self.assertRaises(TypeError):
            route_request("test request", context="not a dict")


class TestGetModelTierFromAgentFile(unittest.TestCase):
    """Test agent model tier detection from agent files."""

    def test_haiku_in_name_fallback(self):
        """Agent name with 'haiku' should return haiku."""
        tier = get_model_tier_from_agent_file("test-haiku-agent", agents_dir="/nonexistent")
        self.assertEqual(tier, "haiku")

    def test_opus_in_name_fallback(self):
        """Agent name with 'opus' should return opus."""
        tier = get_model_tier_from_agent_file("test-opus-agent", agents_dir="/nonexistent")
        self.assertEqual(tier, "opus")

    def test_default_sonnet(self):
        """Unknown agents should default to sonnet."""
        tier = get_model_tier_from_agent_file("unknown-agent", agents_dir="/nonexistent")
        self.assertEqual(tier, "sonnet")

    def test_real_agent_file_haiku(self):
        """Should read model from real haiku-general.md if available."""
        agents_dir = Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "agents"
        if (agents_dir / "haiku-general.md").exists():
            tier = get_model_tier_from_agent_file("haiku-general", agents_dir=str(agents_dir))
            self.assertEqual(tier, "haiku")

    def test_real_agent_file_sonnet(self):
        """Should read model from real sonnet-general.md if available."""
        agents_dir = Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "agents"
        if (agents_dir / "sonnet-general.md").exists():
            tier = get_model_tier_from_agent_file("sonnet-general", agents_dir=str(agents_dir))
            self.assertEqual(tier, "sonnet")


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios."""

    def test_git_commit_message(self):
        """Simple typo fix should route direct."""
        result = route_request("Fix typo in README.md: change 'teh' to 'the'")
        self.assertEqual(result.decision, RouterDecision.DIRECT_TO_AGENT)

    def test_code_review_request(self):
        """Code review requires reasoning."""
        result = route_request("Review the authentication implementation")
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_debugging_task(self):
        """Debugging requires analysis."""
        result = route_request("Debug why the tests are failing")
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_architecture_decision(self):
        """Architecture decisions need reasoning."""
        result = route_request("Should I use Redis or Memcached for caching?")
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_api_implementation(self):
        """API implementation requires design."""
        result = route_request("Add a new REST API endpoint for user registration")
        self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)


class TestConfidenceScoring(unittest.TestCase):
    """Test confidence score behavior."""

    def test_high_confidence_haiku(self):
        """High confidence for obvious haiku tasks."""
        result = route_request("Fix typo in README.md")
        if result.decision == RouterDecision.DIRECT_TO_AGENT:
            self.assertGreaterEqual(result.confidence, 0.9)

    def test_confidence_range(self):
        """Confidence should always be 0.0-1.0."""
        test_cases = [
            "Fix typo in README.md",
            "Analyze the codebase",
            "Design new system",
            "Format code",
        ]
        for request in test_cases:
            with self.subTest(request=request):
                result = route_request(request)
                self.assertGreaterEqual(result.confidence, 0.0)
                self.assertLessEqual(result.confidence, 1.0)


class TestEscalationPatterns(unittest.TestCase):
    """Test specific escalation pattern triggers."""

    def test_pattern_complexity_keywords(self):
        """Each complexity keyword should trigger escalation."""
        keywords = [
            "complex", "subtle", "nuanced", "judgment", "trade-off",
            "best approach", "design", "architecture", "should I",
            "which is better", "recommend", "decide",
        ]
        for keyword in keywords:
            with self.subTest(keyword=keyword):
                result = should_escalate(f"This involves {keyword} decisions")
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET,
                                 f"Failed to escalate for keyword: {keyword}")

    def test_pattern_bulk_operations(self):
        """Bulk + destructive combinations should escalate."""
        bulk_words = ["all", "multiple", "*", "every"]
        destructive_words = ["delete", "remove", "drop"]

        for bulk in bulk_words:
            for dest in destructive_words:
                with self.subTest(combo=f"{dest} {bulk}"):
                    result = should_escalate(f"{dest} {bulk} files")
                    self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)

    def test_pattern_creation_keywords(self):
        """Creation keywords should trigger escalation."""
        keywords = ["new", "create", "design", "build", "implement"]
        for keyword in keywords:
            with self.subTest(keyword=keyword):
                result = should_escalate(f"{keyword} a feature")
                self.assertEqual(result.decision, RouterDecision.ESCALATE_TO_SONNET)


if __name__ == "__main__":
    unittest.main()
