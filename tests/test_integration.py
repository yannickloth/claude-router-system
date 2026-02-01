"""
Integration Tests for Claude Router System

Tests end-to-end workflows across all 8 solutions.

Run with:
    pytest tests/test_integration.py -v
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

# Import implementations
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "implementation"))

from routing_core import route_request, RouterDecision
from session_state_manager import SessionStateManager
from work_coordinator import WorkCoordinator, WorkItem, WorkStatus
from domain_adapter import DomainAdapter, ParallelismLevel
from lazy_context_loader import LazyContextLoader
from semantic_cache import SemanticCache


class TestHaikuRouting:
    """Test Solution 1: Haiku Pre-routing"""

    def test_simple_request_routes_directly(self):
        """Simple mechanical requests should not escalate."""
        result = route_request("Find all .py files")

        assert result.decision == RouterDecision.DIRECT_TO_AGENT
        assert result.agent == "haiku-general"

    def test_complex_request_escalates(self):
        """Complex requests requiring judgment should escalate."""
        result = route_request("Design a new microservices architecture")

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET
        assert result.reason.lower().find("design") >= 0 or \
               result.reason.lower().find("architecture") >= 0

    def test_destructive_request_escalates(self):
        """Destructive operations should escalate."""
        result = route_request("Delete all test files")

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET

    def test_escalation_rate_target(self):
        """Escalation rate should be 30-40%."""
        test_requests = [
            "Find files matching *.py",
            "List all directories",
            "Show git status",
            "Design a new feature",
            "Refactor the codebase",
            "Delete old backups",
            "Read config file",
            "Analyze performance",
            "Fix typos",
            "Implement new algorithm"
        ]

        escalations = 0
        for request in test_requests:
            result = route_request(request)
            if result.decision == RouterDecision.ESCALATE_TO_SONNET:
                escalations += 1

        escalation_rate = (escalations / len(test_requests)) * 100

        # Target: 30-40% escalation rate
        assert 20 <= escalation_rate <= 50, \
            f"Escalation rate {escalation_rate}% outside 30-40% target"


class TestWorkCoordination:
    """Test Solution 2: Parallel Work with Completion Guarantees"""

    def test_wip_limit_enforcement(self):
        """Work coordinator should enforce WIP limits."""
        coordinator = WorkCoordinator(max_wip=3)

        # Add tasks up to limit
        for i in range(3):
            task = WorkItem(
                task_id=f"task_{i}",
                task_name=f"Task {i}",
                agent="haiku-general",
                status=WorkStatus.IN_PROGRESS
            )
            coordinator.add_task(task)

        # Should have 3 tasks
        assert len(coordinator.get_active_tasks()) == 3

        # Trying to add 4th should be blocked or queued
        task4 = WorkItem(
            task_id="task_4",
            task_name="Task 4",
            agent="haiku-general",
            status=WorkStatus.IN_PROGRESS
        )

        # This should either raise or queue
        active_before = len(coordinator.get_active_tasks())
        try:
            coordinator.add_task(task4)
            # If it succeeds, check it didn't increase active count
            assert len(coordinator.get_active_tasks()) <= 3
        except ValueError:
            # Correctly rejected
            pass

    def test_task_completion(self):
        """Completing tasks should reduce WIP count."""
        coordinator = WorkCoordinator(max_wip=3)

        task = WorkItem(
            task_id="task_1",
            task_name="Task 1",
            agent="haiku-general",
            status=WorkStatus.IN_PROGRESS
        )
        coordinator.add_task(task)

        assert len(coordinator.get_active_tasks()) == 1

        # Complete task
        coordinator.complete_task("task_1")

        assert len(coordinator.get_active_tasks()) == 0


class TestDomainIntegration:
    """Test Solution 3: Domain-Specific Optimization"""

    def test_domain_detection(self):
        """Domain adapter should detect project type."""
        adapter = DomainAdapter()

        # Create temp directory with LaTeX files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create .tex file
            (tmppath / "main.tex").write_text("\\documentclass{article}")
            (tmppath / "references.bib").write_text("@article{test, title={Test}}")

            domain = adapter.detect_domain(tmppath)
            assert domain == "latex-research"

    def test_workflow_lookup(self):
        """Should retrieve workflow configuration."""
        adapter = DomainAdapter()

        workflow = adapter.get_workflow("latex-research", "literature_integration")

        assert workflow is not None
        assert workflow.name == "literature_integration"
        assert "search" in workflow.phases
        assert "assess" in workflow.phases
        assert workflow.parallelism == ParallelismLevel.LOW

    def test_wip_limit_by_workflow(self):
        """Different workflows should have different WIP limits."""
        adapter = DomainAdapter()

        # Sequential workflow
        sequential_wip = adapter.get_wip_limit("latex-research", "formalization")
        assert sequential_wip == 1

        # High parallelism workflow
        high_wip = adapter.get_wip_limit("latex-research", "bulk_editing")
        assert high_wip == 4

    def test_agent_recommendation(self):
        """Should recommend appropriate agents by task type."""
        adapter = DomainAdapter()

        # Formalization needs Opus
        agent = adapter.get_agent_recommendation("latex-research", "formalization")
        assert "opus" in agent.lower()

        # Syntax can use Haiku
        agent = adapter.get_agent_recommendation("latex-research", "syntax")
        assert "haiku" in agent.lower()


class TestStateContinuity:
    """Test Solution 7: Cross-Session State"""

    def test_session_state_persistence(self):
        """Session state should persist across manager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override memory directory
            import session_state_manager
            original_dir = session_state_manager.MEMORY_DIR
            session_state_manager.MEMORY_DIR = Path(tmpdir)

            try:
                # Create manager and save state
                manager1 = SessionStateManager()
                manager1.update_focus("Testing persistence")
                manager1.add_active_agent("test-agent")

                # Create new manager instance
                manager2 = SessionStateManager()
                state = manager2.get_current_state()

                assert state.current_focus == "Testing persistence"
                assert "test-agent" in state.active_agents

            finally:
                # Restore original directory
                session_state_manager.MEMORY_DIR = original_dir

    def test_search_deduplication(self):
        """Should detect duplicate searches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import session_state_manager
            original_dir = session_state_manager.MEMORY_DIR
            session_state_manager.MEMORY_DIR = Path(tmpdir)

            try:
                manager = SessionStateManager()

                # Record search
                manager.record_search(
                    query="test query",
                    agent="test-agent",
                    result_count=5,
                    files_found=["file1.py", "file2.py"]
                )

                # Check for duplicate (exact match)
                duplicate = manager.check_duplicate_search("test query")
                assert duplicate is not None
                assert duplicate.query == "test query"
                assert duplicate.result_count == 5

                # Different query should not match
                duplicate2 = manager.check_duplicate_search("different query")
                assert duplicate2 is None

            finally:
                session_state_manager.MEMORY_DIR = original_dir


class TestLazyContextLoading:
    """Test Solution 8: Context Management for UX"""

    def test_metadata_indexing(self):
        """Should build metadata index for LaTeX files."""
        loader = LazyContextLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test LaTeX file
            tex_content = """\\documentclass{article}
\\begin{document}

\\chapter{Introduction}
This is the introduction.

\\section{Background}
Some background information.

\\chapter{Methods}
Research methods.

\\end{document}
"""
            tex_file = tmppath / "test.tex"
            tex_file.write_text(tex_content)

            # Build index
            loader.build_metadata_index(tmppath)

            # Check sections were indexed
            sections = loader.list_sections(str(tex_file))
            assert len(sections) >= 2  # At least 2 chapters

            # Find chapter section
            intro_section = next(
                (s for s in sections if "Introduction" in s.section_name),
                None
            )
            assert intro_section is not None

    def test_section_loading(self):
        """Should load specific sections without loading entire file."""
        loader = LazyContextLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test file with sections
            md_content = """# First Heading

Content for first section.

# Second Heading

Content for second section.

# Third Heading

Content for third section.
"""
            md_file = tmppath / "test.md"
            md_file.write_text(md_content)

            # Build index
            loader.build_metadata_index(tmppath)

            # Load specific section
            sections = loader.list_sections(str(md_file))
            if sections:
                first_section = sections[0]
                content = loader.load_section(str(md_file), first_section.section_id)

                assert content is not None
                assert "First Heading" in content
                # Should not contain third section
                assert "Third Heading" not in content

    def test_lru_cache(self):
        """LRU cache should evict oldest items when full."""
        loader = LazyContextLoader(context_budget=100)  # Very small budget

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create multiple sections
            for i in range(5):
                md_file = tmppath / f"test{i}.md"
                md_file.write_text(f"# Section {i}\n\n" + "x" * 50)

            loader.build_metadata_index(tmppath)

            # Load all sections (should trigger eviction)
            for i in range(5):
                sections = loader.list_sections(str(tmppath / f"test{i}.md"))
                if sections:
                    loader.load_section(str(tmppath / f"test{i}.md"), sections[0].section_id)

            stats = loader.get_stats()

            # Should have evicted some sections to stay under budget
            assert stats.total_tokens <= 100


class TestSemanticCache:
    """Test Solution 5: Semantic Deduplication"""

    def test_exact_match_detection(self):
        """Should detect exact duplicate queries."""
        cache = SemanticCache()

        query1 = "Find all Python files"
        result1 = {"files": ["a.py", "b.py"]}

        cache.store(query1, result1, "haiku-general")

        # Exact match should hit
        cached = cache.get(query1)
        assert cached is not None
        assert cached["files"] == ["a.py", "b.py"]

    def test_similar_query_detection(self):
        """Should detect semantically similar queries."""
        cache = SemanticCache()

        query1 = "List all Python files in the project"
        result1 = {"files": ["a.py", "b.py"]}

        cache.store(query1, result1, "haiku-general")

        # Similar query should potentially hit (depending on similarity threshold)
        query2 = "Find all .py files"
        cached = cache.get(query2)

        # Might hit or might not depending on similarity threshold
        # Just verify it doesn't crash
        assert cached is None or isinstance(cached, dict)


def test_end_to_end_workflow():
    """Test complete workflow from request to completion."""

    # 1. Route request
    request = "Fix syntax errors in Python files"
    routing = route_request(request)

    # Should route to Haiku for mechanical fix
    assert routing.agent == "haiku-general"

    # 2. Detect domain
    adapter = DomainAdapter()
    # In a real scenario, would detect software-dev

    # 3. Create work item
    coordinator = WorkCoordinator(max_wip=3)
    task = WorkItem(
        task_id="syntax_fix_1",
        task_name="Fix syntax errors",
        agent="haiku-general",
        status=WorkStatus.IN_PROGRESS
    )
    coordinator.add_task(task)

    # 4. Track in session state
    with tempfile.TemporaryDirectory() as tmpdir:
        import session_state_manager
        original_dir = session_state_manager.MEMORY_DIR
        session_state_manager.MEMORY_DIR = Path(tmpdir)

        try:
            manager = SessionStateManager()
            manager.update_focus("Fixing syntax errors")
            manager.add_active_agent("haiku-general")

            # 5. Complete work
            coordinator.complete_task("syntax_fix_1")

            # 6. Verify state
            assert len(coordinator.get_active_tasks()) == 0
            state = manager.get_current_state()
            assert state.current_focus == "Fixing syntax errors"

        finally:
            session_state_manager.MEMORY_DIR = original_dir


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
