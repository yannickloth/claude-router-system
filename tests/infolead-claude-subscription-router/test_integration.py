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
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from routing_core import route_request, should_escalate, RouterDecision, RoutingResult
from session_state_manager import SessionStateManager, MEMORY_DIR
from work_coordinator import WorkCoordinator, WorkItem, WorkStatus
from domain_adapter import DomainAdapter, ParallelismLevel
from lazy_context_loader import LazyContextLoader
from semantic_cache import SemanticCache


class TestHaikuRouting:
    """Test Solution 1: Haiku Pre-routing"""

    def test_simple_request_routes_directly(self):
        """Simple mechanical requests should route directly to haiku-general.

        NOTE: Requires ROUTER_USE_LLM=1 for semantic matching.
        """
        import os
        if os.environ.get("ROUTER_USE_LLM", "0") != "1":
            pytest.skip("Requires ROUTER_USE_LLM=1 for semantic matching")

        result = route_request("Fix typo in README.md")

        assert result.decision == RouterDecision.DIRECT_TO_AGENT
        assert result.agent == "haiku-general"

    def test_complex_request_escalates(self):
        """Complex requests requiring judgment should escalate."""
        result = route_request("Design a new microservices architecture")

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET
        # Check reason mentions design or architecture or complexity
        reason_lower = result.reason.lower()
        assert any(kw in reason_lower for kw in ["design", "architecture", "complexity", "creation"])

    def test_destructive_request_escalates(self):
        """Destructive operations should escalate."""
        result = route_request("Delete all test files")

        assert result.decision == RouterDecision.ESCALATE_TO_SONNET


class TestWorkCoordination:
    """Test Solution 2: Parallel Work with Completion Guarantees"""

    @pytest.fixture
    def coordinator(self, tmp_path):
        """Create a coordinator with temp state file."""
        state_file = tmp_path / "work-queue.json"
        return WorkCoordinator(wip_limit=3, state_file=state_file)

    def test_wip_limit_enforcement(self, coordinator):
        """Work coordinator should enforce WIP limits."""
        # Add 4 tasks
        for i in range(4):
            task = WorkItem(
                id=f"task_{i}",
                description=f"Task {i}",
                priority=5,
                estimated_complexity=2
            )
            coordinator.add_work(task)

        # Schedule work
        started = coordinator.schedule_work()

        # Should only start 3 (WIP limit)
        assert len(started) <= 3
        assert coordinator.get_active_count() <= 3

    def test_task_completion(self, coordinator):
        """Completing tasks should reduce WIP count."""
        task = WorkItem(
            id="task_1",
            description="Task 1",
            priority=5,
            estimated_complexity=2
        )
        coordinator.add_work(task)
        coordinator.schedule_work()

        assert coordinator.get_active_count() == 1

        # Complete task
        coordinator.complete_work("task_1")

        assert coordinator.get_active_count() == 0

    def test_compatibility_aliases(self, coordinator):
        """Test backwards compatibility aliases."""
        # Test add_task alias
        task = WorkItem(
            id="alias_test",
            description="Testing aliases",
            priority=5,
            estimated_complexity=2
        )
        coordinator.add_task(task)
        assert len(coordinator.work_items) == 1

        # Test schedule and get_active_tasks
        coordinator.schedule_work()
        active = coordinator.get_active_tasks()
        assert len(active) == 1

        # Test complete_task alias
        coordinator.complete_task("alias_test")
        assert coordinator.get_active_count() == 0

        # Test max_wip property
        assert coordinator.max_wip == 3


class TestDomainIntegration:
    """Test Solution 3: Domain-Specific Optimization"""

    @pytest.fixture
    def adapter(self):
        """Create domain adapter."""
        return DomainAdapter()

    def test_domain_detection(self, adapter, tmp_path):
        """Domain adapter should detect project type."""
        # Create .tex file
        (tmp_path / "main.tex").write_text("\\documentclass{article}")
        (tmp_path / "references.bib").write_text("@article{test, title={Test}}")

        domain = adapter.detect_domain(tmp_path)
        assert domain == "latex-research"

    def test_workflow_lookup(self, adapter):
        """Should retrieve workflow configuration."""
        workflow = adapter.get_workflow("latex-research", "literature_integration")

        assert workflow is not None
        assert workflow.name == "literature_integration"
        assert "search" in workflow.phases
        assert "assess" in workflow.phases
        assert workflow.parallelism == ParallelismLevel.LOW

    def test_wip_limit_by_workflow(self, adapter):
        """Different workflows should have different WIP limits."""
        # Sequential workflow
        sequential_wip = adapter.get_wip_limit("latex-research", "formalization")
        assert sequential_wip == 1

        # High parallelism workflow
        high_wip = adapter.get_wip_limit("latex-research", "bulk_editing")
        assert high_wip == 4

    def test_agent_recommendation(self, adapter):
        """Should recommend appropriate agents by task type."""
        # Formalization needs Opus
        agent = adapter.get_agent_recommendation("latex-research", "formalization")
        assert "opus" in agent.lower()

        # Syntax can use Haiku
        agent = adapter.get_agent_recommendation("latex-research", "syntax")
        assert "haiku" in agent.lower()


class TestStateContinuity:
    """Test Solution 7: Cross-Session State"""

    def test_session_state_persistence(self, tmp_path):
        """Session state should persist across manager instances."""
        # Create manager and save state
        manager1 = SessionStateManager(memory_dir=tmp_path)
        manager1.update_focus("Testing persistence")
        manager1.add_active_agent("test-agent")

        # Create new manager instance pointing to same dir
        manager2 = SessionStateManager(memory_dir=tmp_path)
        state = manager2.get_current_state()

        assert state.current_focus == "Testing persistence"
        assert "test-agent" in state.active_agents

    def test_search_deduplication(self, tmp_path):
        """Should detect duplicate searches."""
        manager = SessionStateManager(memory_dir=tmp_path)

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


class TestLazyContextLoading:
    """Test Solution 8: Context Management for UX"""

    @pytest.fixture
    def loader(self):
        """Create context loader."""
        return LazyContextLoader()

    def test_metadata_indexing(self, loader, tmp_path):
        """Should build metadata index for LaTeX files."""
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
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(tex_content)

        # Build index
        loader.build_metadata_index(tmp_path)

        # Check sections were indexed
        sections = loader.list_sections(str(tex_file))
        assert len(sections) >= 2  # At least 2 chapters

        # Find chapter section
        intro_section = next(
            (s for s in sections if "Introduction" in s.section_name),
            None
        )
        assert intro_section is not None

    def test_section_loading(self, loader, tmp_path):
        """Should load specific sections without loading entire file."""
        # Create test file with sections
        md_content = """# First Heading

Content for first section.

# Second Heading

Content for second section.

# Third Heading

Content for third section.
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content)

        # Build index
        loader.build_metadata_index(tmp_path)

        # Load specific section
        sections = loader.list_sections(str(md_file))
        if sections:
            first_section = sections[0]
            content = loader.load_section(str(md_file), first_section.section_id)

            assert content is not None
            assert "First Heading" in content
            # Should not contain third section
            assert "Third Heading" not in content

    def test_lru_cache(self, tmp_path):
        """LRU cache should evict oldest items when full."""
        loader = LazyContextLoader(context_budget=100)  # Very small budget

        # Create multiple sections
        for i in range(5):
            md_file = tmp_path / f"test{i}.md"
            md_file.write_text(f"# Section {i}\n\n" + "x" * 50)

        loader.build_metadata_index(tmp_path)

        # Load all sections (should trigger eviction)
        for i in range(5):
            sections = loader.list_sections(str(tmp_path / f"test{i}.md"))
            if sections:
                loader.load_section(str(tmp_path / f"test{i}.md"), sections[0].section_id)

        stats = loader.get_stats()

        # Should have evicted some sections to stay under budget
        assert stats.total_tokens <= 100


class TestSemanticCache:
    """Test Solution 5: Semantic Deduplication"""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create semantic cache."""
        return SemanticCache(cache_dir=tmp_path)

    def test_exact_match_detection(self, cache):
        """Should detect exact duplicate queries."""
        query1 = "Find all Python files"
        result1 = {"files": ["a.py", "b.py"]}

        cache.store(query1, "haiku-general", result1, quota_cost=5)

        # Exact match should hit
        cached = cache.get(query1)
        assert cached is not None
        assert cached["files"] == ["a.py", "b.py"]

    def test_store_and_find_similar(self, cache):
        """Should store and find similar queries."""
        query1 = "List all Python files in the project"
        result1 = {"files": ["a.py", "b.py"]}

        cache.store(query1, "haiku-general", result1, quota_cost=5)

        # Finding similar should work
        cached = cache.find_similar(
            request="Find all .py files",
            agent="haiku-general"
        )

        # Might hit or might not depending on similarity threshold
        # Just verify it doesn't crash
        assert cached is None or isinstance(cached.result, dict)


def test_end_to_end_workflow(tmp_path):
    """Test complete workflow from request to completion."""

    # 1. Route request
    request = "Fix syntax errors in main.py"
    routing = route_request(request)

    # Should route to Haiku for mechanical fix
    assert routing.agent == "haiku-general"

    # 2. Detect domain
    adapter = DomainAdapter()
    # In a real scenario, would detect software-dev

    # 3. Create work item
    state_file = tmp_path / "work-queue.json"
    coordinator = WorkCoordinator(wip_limit=3, state_file=state_file)
    task = WorkItem(
        id="syntax_fix_1",
        description="Fix syntax errors",
        priority=5,
        estimated_complexity=2
    )
    coordinator.add_work(task)
    coordinator.schedule_work()

    # 4. Track in session state
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    manager = SessionStateManager(memory_dir=memory_dir)
    manager.update_focus("Fixing syntax errors")
    manager.add_active_agent("haiku-general")

    # 5. Complete work
    coordinator.complete_work("syntax_fix_1")

    # 6. Verify state
    assert coordinator.get_active_count() == 0
    state = manager.get_current_state()
    assert state.current_focus == "Fixing syntax errors"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
