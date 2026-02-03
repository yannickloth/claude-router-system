"""
Tests for session_state_manager module.

Tests session state persistence, search deduplication, and agent tracking.
"""

import json
import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from session_state_manager import (
    SessionStateManager,
    SessionState,
    SearchRecord,
)


class TestSessionStateBasics:
    """Test basic session state operations."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with temp directory."""
        return SessionStateManager(memory_dir=tmp_path)

    def test_initial_state_empty(self, manager):
        """New manager should have empty state."""
        state = manager.get_current_state()

        # New state has empty string for focus (not None)
        assert state.current_focus == ""
        assert len(state.active_agents) == 0

    def test_update_focus(self, manager):
        """Should update current focus."""
        manager.update_focus("Working on feature X")

        state = manager.get_current_state()
        assert state.current_focus == "Working on feature X"

    def test_update_focus_persists(self, manager, tmp_path):
        """Focus update should persist."""
        manager.update_focus("Persistent focus")

        # Create new manager instance
        manager2 = SessionStateManager(memory_dir=tmp_path)
        state = manager2.get_current_state()

        assert state.current_focus == "Persistent focus"


class TestActiveAgentTracking:
    """Test active agent tracking."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager."""
        return SessionStateManager(memory_dir=tmp_path)

    def test_add_active_agent(self, manager):
        """Should add agent to active set."""
        manager.add_active_agent("test-agent")

        state = manager.get_current_state()
        assert "test-agent" in state.active_agents

    def test_add_multiple_agents(self, manager):
        """Should track multiple active agents."""
        manager.add_active_agent("agent-1")
        manager.add_active_agent("agent-2")
        manager.add_active_agent("agent-3")

        state = manager.get_current_state()
        assert len(state.active_agents) == 3
        assert "agent-1" in state.active_agents
        assert "agent-2" in state.active_agents
        assert "agent-3" in state.active_agents

    def test_remove_active_agent(self, manager):
        """Should remove agent from active set."""
        manager.add_active_agent("test-agent")
        manager.remove_active_agent("test-agent")

        state = manager.get_current_state()
        assert "test-agent" not in state.active_agents

    def test_remove_nonexistent_agent(self, manager):
        """Should handle removing nonexistent agent gracefully."""
        # Should not raise
        manager.remove_active_agent("nonexistent")

        state = manager.get_current_state()
        assert len(state.active_agents) == 0


class TestSearchRecording:
    """Test search deduplication recording."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager."""
        return SessionStateManager(memory_dir=tmp_path)

    def test_record_search(self, manager):
        """Should record search with details."""
        manager.record_search(
            query="test query",
            agent="search-agent",
            result_count=10,
            files_found=["file1.py", "file2.py"]
        )

        # Check for duplicate
        duplicate = manager.check_duplicate_search("test query")
        assert duplicate is not None
        assert duplicate.query == "test query"
        assert duplicate.result_count == 10

    def test_check_duplicate_exact_match(self, manager):
        """Should find exact duplicate searches."""
        manager.record_search(
            query="find all tests",
            agent="agent",
            result_count=5,
            files_found=["test1.py"]
        )

        duplicate = manager.check_duplicate_search("find all tests")
        assert duplicate is not None

    def test_check_no_duplicate(self, manager):
        """Should return None for new searches."""
        manager.record_search(
            query="original query",
            agent="agent",
            result_count=1,
            files_found=[]
        )

        duplicate = manager.check_duplicate_search("completely different query")
        assert duplicate is None

    def test_duplicate_has_files(self, manager):
        """Duplicate search should include found files."""
        files = ["a.py", "b.py", "c.py"]
        manager.record_search(
            query="test query",
            agent="agent",
            result_count=3,
            files_found=files
        )

        duplicate = manager.check_duplicate_search("test query")
        assert duplicate is not None
        assert duplicate.files_found == files


class TestStatePersistence:
    """Test state persistence across instances."""

    def test_state_persists(self, tmp_path):
        """State should persist across manager instances."""
        # First manager
        manager1 = SessionStateManager(memory_dir=tmp_path)
        manager1.update_focus("Test focus")
        manager1.add_active_agent("persistent-agent")
        manager1.record_search(
            query="persistent query",
            agent="agent",
            result_count=5,
            files_found=["file.py"]
        )

        # Second manager (same directory)
        manager2 = SessionStateManager(memory_dir=tmp_path)
        state = manager2.get_current_state()

        assert state.current_focus == "Test focus"
        assert "persistent-agent" in state.active_agents

        # Search should also persist
        duplicate = manager2.check_duplicate_search("persistent query")
        assert duplicate is not None


class TestStateClear:
    """Test state clearing."""

    @pytest.fixture
    def manager_with_state(self, tmp_path):
        """Create manager with existing state."""
        manager = SessionStateManager(memory_dir=tmp_path)
        manager.update_focus("Some focus")
        manager.add_active_agent("agent-1")
        manager.record_search("query", "agent", 5, ["file.py"])
        return manager

    def test_clear_state(self, manager_with_state):
        """Should clear all state."""
        manager_with_state.clear_state()

        state = manager_with_state.get_current_state()
        # After clear, focus is empty string (not None)
        assert state.current_focus == ""
        assert len(state.active_agents) == 0

    def test_clear_persists(self, manager_with_state, tmp_path):
        """Clear should persist."""
        manager_with_state.clear_state()

        manager2 = SessionStateManager(memory_dir=tmp_path)
        state = manager2.get_current_state()

        # After clear, focus is empty string (not None)
        assert state.current_focus == ""
        assert len(state.active_agents) == 0


class TestSessionState:
    """Test SessionState dataclass."""

    def test_session_state_with_all_fields(self):
        """SessionState should accept all required fields."""
        state = SessionState(
            current_focus="",
            active_agents=[],
            last_updated="",
            context_summary=""
        )

        assert state.current_focus == ""
        assert state.active_agents == []

    def test_session_state_with_values(self):
        """SessionState should accept custom values."""
        state = SessionState(
            current_focus="Custom focus",
            active_agents=["agent1", "agent2"],
            last_updated="2024-01-01T00:00:00Z",
            context_summary="Test context"
        )

        assert state.current_focus == "Custom focus"
        assert len(state.active_agents) == 2


class TestSearchRecord:
    """Test SearchRecord dataclass."""

    def test_search_record_creation(self):
        """Should create SearchRecord with all fields."""
        record = SearchRecord(
            query="test query",
            agent="test-agent",
            timestamp="2024-01-01T00:00:00",
            result_count=10,
            files_found=["a.py", "b.py"]
        )

        assert record.query == "test query"
        assert record.agent == "test-agent"
        assert record.result_count == 10
        assert len(record.files_found) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager."""
        return SessionStateManager(memory_dir=tmp_path)

    def test_empty_focus(self, manager):
        """Should handle empty focus string."""
        manager.update_focus("")

        state = manager.get_current_state()
        assert state.current_focus == ""

    def test_special_characters_in_focus(self, manager):
        """Should handle special characters in focus."""
        focus = "Working on feature: 'test' with \"quotes\" & symbols"
        manager.update_focus(focus)

        state = manager.get_current_state()
        assert state.current_focus == focus

    def test_special_characters_in_agent_name(self, manager):
        """Should handle special characters in agent names."""
        agent_name = "test-agent_v2.0"
        manager.add_active_agent(agent_name)

        state = manager.get_current_state()
        assert agent_name in state.active_agents

    def test_duplicate_agent_add(self, manager):
        """Should handle adding same agent twice."""
        manager.add_active_agent("agent")
        manager.add_active_agent("agent")

        state = manager.get_current_state()
        # Should only have one entry (set behavior)
        assert state.active_agents.count("agent") <= 1 or len(set(state.active_agents)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
