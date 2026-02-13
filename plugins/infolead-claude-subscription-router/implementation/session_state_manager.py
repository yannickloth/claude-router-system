"""
Session State Manager

Persists session state across Claude Code restarts for continuity.
Implements Solution 7 (Basic) from the router architecture.

State Files:
- session-state.json: Current session focus and active agents
- search-history.json: Cross-session search deduplication
- decisions.json: Decision log with rationale

Change Driver: STATE_PERSISTENCE
Changes when: Memory requirements evolve
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Optional, List

from file_locking import locked_state_file

# State directory
MEMORY_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "memory"

# State files
SESSION_STATE_FILE = MEMORY_DIR / "session-state.json"
SEARCH_HISTORY_FILE = MEMORY_DIR / "search-history.json"
DECISIONS_FILE = MEMORY_DIR / "decisions.json"
ACTIVE_CONTEXT_FILE = MEMORY_DIR / "active-context.json"

# TTL for cleanup (30 days)
DEFAULT_TTL_DAYS = 30


@dataclass
class SessionState:
    """Current session state"""

    current_focus: str
    active_agents: list[str]
    last_updated: str
    context_summary: str


@dataclass
class SearchRecord:
    """Search history record"""

    query: str
    timestamp: str
    agent: str
    result_count: int
    files_found: list[str]


@dataclass
class DecisionRecord:
    """Decision log record"""

    decision: str
    rationale: str
    alternatives: list[str]
    timestamp: str


def _ensure_directory() -> None:
    """Ensure memory directory exists with secure permissions"""
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(MEMORY_DIR, 0o700)  # User-only access
    except Exception as e:
        raise RuntimeError(f"Failed to create memory directory: {e}") from e


def _atomic_write(file_path: Path, data: dict) -> None:
    """Write data to file atomically with exclusive lock."""
    try:
        # Ensure directory exists
        _ensure_directory()

        # Write with exclusive lock
        with locked_state_file(file_path, "r+", create_if_missing=True) as f:
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

    except Exception as e:
        raise RuntimeError(f"Failed to write {file_path}: {e}") from e


def _read_json(file_path: Path) -> Optional[dict]:
    """Read JSON file with shared lock, return None if doesn't exist or invalid."""
    try:
        if not file_path.exists():
            return None

        with locked_state_file(file_path, "r") as f:
            return json.load(f)

    except (json.JSONDecodeError, IOError, TimeoutError) as e:
        print(f"Warning: Failed to read {file_path}: {e}")
        return None


def save_session_state(
    focus: str, active_agents: list[str], context: str
) -> None:
    """
    Save current session state

    Args:
        focus: Description of current task focus
        active_agents: List of currently active agent names
        context: Brief context summary
    """
    state = SessionState(
        current_focus=focus,
        active_agents=active_agents,
        last_updated=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        context_summary=context,
    )

    _atomic_write(SESSION_STATE_FILE, asdict(state))


def load_session_state() -> Optional[dict]:
    """
    Load session state from previous session

    Returns:
        Session state dict or None if no state exists
    """
    return _read_json(SESSION_STATE_FILE)


def record_search(
    query: str, results: list[str], agent: str, result_count: int = None
) -> None:
    """
    Record search operation for cross-session deduplication

    Args:
        query: Search query string
        results: List of files/results found
        agent: Agent that performed the search
        result_count: Number of results (defaults to len(results))
    """
    # Load existing history
    history = _read_json(SEARCH_HISTORY_FILE)
    if history is None:
        history = {"searches": []}

    # Create new search record
    record = SearchRecord(
        query=query,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        agent=agent,
        result_count=result_count if result_count is not None else len(results),
        files_found=results,
    )

    # Append to history
    history["searches"].append(asdict(record))

    # Clean up old entries (older than TTL)
    history["searches"] = _cleanup_old_entries(
        history["searches"], DEFAULT_TTL_DAYS
    )

    # Save updated history
    _atomic_write(SEARCH_HISTORY_FILE, history)


def record_decision(
    decision: str, rationale: str, alternatives: list[str]
) -> None:
    """
    Record decision with rationale and alternatives

    Args:
        decision: The decision made
        rationale: Reasoning behind the decision
        alternatives: Other options that were considered
    """
    # Load existing decisions
    decisions = _read_json(DECISIONS_FILE)
    if decisions is None:
        decisions = {"decisions": []}

    # Create new decision record
    record = DecisionRecord(
        decision=decision,
        rationale=rationale,
        alternatives=alternatives,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )

    # Append to history
    decisions["decisions"].append(asdict(record))

    # Clean up old entries
    decisions["decisions"] = _cleanup_old_entries(
        decisions["decisions"], DEFAULT_TTL_DAYS
    )

    # Save updated decisions
    _atomic_write(DECISIONS_FILE, decisions)


def get_recent_searches(hours: int = 24) -> list[dict]:
    """
    Get search history from recent hours

    Args:
        hours: Number of hours to look back

    Returns:
        List of search records
    """
    history = _read_json(SEARCH_HISTORY_FILE)
    if history is None or "searches" not in history:
        return []

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    recent = []
    for search in history["searches"]:
        timestamp_str = search["timestamp"].rstrip("Z")
        # Parse as UTC timezone-aware datetime
        timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=UTC)
        if timestamp >= cutoff:
            recent.append(search)

    return recent


def get_recent_decisions(hours: int = 24) -> list[dict]:
    """
    Get decisions from recent hours

    Args:
        hours: Number of hours to look back

    Returns:
        List of decision records
    """
    decisions = _read_json(DECISIONS_FILE)
    if decisions is None or "decisions" not in decisions:
        return []

    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    recent = []
    for decision in decisions["decisions"]:
        timestamp_str = decision["timestamp"].rstrip("Z")
        # Parse as UTC timezone-aware datetime
        timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=UTC)
        if timestamp >= cutoff:
            recent.append(decision)

    return recent


def _cleanup_old_entries(entries: list[dict], ttl_days: int) -> list[dict]:
    """
    Remove entries older than TTL

    Args:
        entries: List of entries with 'timestamp' field
        ttl_days: Number of days to keep

    Returns:
        Filtered list of entries
    """
    cutoff = datetime.now(UTC) - timedelta(days=ttl_days)

    cleaned = []
    for entry in entries:
        try:
            timestamp_str = entry["timestamp"].rstrip("Z")
            # Parse as UTC timezone-aware datetime
            timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=UTC)
            if timestamp >= cutoff:
                cleaned.append(entry)
        except (ValueError, KeyError):
            # Skip malformed entries
            continue

    return cleaned


def clear_session_state() -> None:
    """Clear session state (useful for testing)"""
    if SESSION_STATE_FILE.exists():
        SESSION_STATE_FILE.unlink()


def clear_all_state() -> None:
    """Clear all state files (useful for testing)"""
    for file_path in [SESSION_STATE_FILE, SEARCH_HISTORY_FILE, DECISIONS_FILE, ACTIVE_CONTEXT_FILE]:
        if file_path.exists():
            file_path.unlink()


# =============================================================================
# Active Context Management (Solution 7 Enhancement)
# =============================================================================


@dataclass
class ActiveContext:
    """Active context for cross-session continuity."""

    project_path: str
    current_files: List[str]
    recent_decisions: List[str]
    last_agent: str
    continuation_summary: str
    timestamp: str


def save_active_context(
    project_path: str,
    current_files: List[str],
    recent_decisions: List[str],
    last_agent: str,
    continuation_summary: str,
) -> None:
    """
    Save active context for session continuation.

    Call this at the end of a session or when context needs to be preserved
    for a potential fresh start.

    Args:
        project_path: Path to the current project
        current_files: List of files currently being worked on
        recent_decisions: List of recent decisions made
        last_agent: Name of the last agent used
        continuation_summary: Brief summary of where work left off
    """
    context = ActiveContext(
        project_path=project_path,
        current_files=current_files[:10],  # Limit to 10 files
        recent_decisions=recent_decisions[:5],  # Limit to 5 decisions
        last_agent=last_agent,
        continuation_summary=continuation_summary[:500],  # Limit summary length
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )

    _atomic_write(ACTIVE_CONTEXT_FILE, asdict(context))


def load_active_context() -> Optional[dict]:
    """
    Load active context from previous session.

    Returns:
        Active context dict or None if no context exists
    """
    return _read_json(ACTIVE_CONTEXT_FILE)


def clear_active_context() -> None:
    """Clear active context file."""
    if ACTIVE_CONTEXT_FILE.exists():
        ACTIVE_CONTEXT_FILE.unlink()


def generate_continuation_prompt() -> str:
    """
    Generate a continuation prompt for starting a new session.

    This creates a concise prompt that can be pasted into a new Claude session
    to continue where the previous session left off.

    Returns:
        Formatted continuation prompt string, or empty string if no context
    """
    context = load_active_context()
    if context is None:
        return ""

    state = load_session_state()

    prompt_parts = []

    # Header
    prompt_parts.append("Continue working on the following project:")
    prompt_parts.append("")

    # Project info
    project = context.get("project_path", "unknown project")
    prompt_parts.append(f"Project: {project}")

    # Current focus from session state
    if state and state.get("current_focus"):
        prompt_parts.append(f"Focus: {state['current_focus']}")

    prompt_parts.append("")

    # Files being worked on
    files = context.get("current_files", [])
    if files:
        prompt_parts.append("Current files:")
        for f in files[:5]:  # Show max 5
            prompt_parts.append(f"  - {f}")
        prompt_parts.append("")

    # Recent decisions
    decisions = context.get("recent_decisions", [])
    if decisions:
        prompt_parts.append("Recent decisions:")
        for d in decisions[:3]:  # Show max 3
            prompt_parts.append(f"  - {d}")
        prompt_parts.append("")

    # Continuation summary
    summary = context.get("continuation_summary", "")
    if summary:
        prompt_parts.append(f"Where we left off: {summary}")
        prompt_parts.append("")

    # Last agent (for context on task type)
    last_agent = context.get("last_agent", "")
    if last_agent:
        prompt_parts.append(f"Last task type: {last_agent}")

    return "\n".join(prompt_parts)


def should_save_context_on_exit() -> bool:
    """
    Check if active context should be saved on session exit.

    Returns True if there's meaningful session state to preserve.

    Returns:
        True if context should be saved
    """
    state = load_session_state()
    if state is None:
        return False

    # Save if there's an active focus or active agents
    has_focus = bool(state.get("current_focus"))
    has_agents = bool(state.get("active_agents"))

    return has_focus or has_agents


# =============================================================================
# SessionStateManager Class (OOP wrapper for module functions)
# =============================================================================


class SessionStateManager:
    """
    Object-oriented wrapper for session state management.

    This class provides a convenient interface for managing session state,
    wrapping the module-level functions for easier use in tests and applications.
    """

    def __init__(self, memory_dir: Optional[Path] = None):
        """
        Initialize session state manager.

        Args:
            memory_dir: Optional custom memory directory (for testing)
        """
        global MEMORY_DIR, SESSION_STATE_FILE, SEARCH_HISTORY_FILE, DECISIONS_FILE, ACTIVE_CONTEXT_FILE

        if memory_dir is not None:
            MEMORY_DIR = Path(memory_dir)
            SESSION_STATE_FILE = MEMORY_DIR / "session-state.json"
            SEARCH_HISTORY_FILE = MEMORY_DIR / "search-history.json"
            DECISIONS_FILE = MEMORY_DIR / "decisions.json"
            ACTIVE_CONTEXT_FILE = MEMORY_DIR / "active-context.json"

        _ensure_directory()
        self._state = self._load_or_create_state()

    def _load_or_create_state(self) -> dict:
        """Load existing state or create new."""
        state = load_session_state()
        if state is None:
            state = {
                "current_focus": "",
                "active_agents": [],
                "last_updated": "",
                "context_summary": ""
            }
        return state

    def update_focus(self, focus: str) -> None:
        """Update the current task focus."""
        self._state["current_focus"] = focus
        self._save()

    def add_active_agent(self, agent: str) -> None:
        """Add an agent to the active agents list."""
        if agent not in self._state.get("active_agents", []):
            if "active_agents" not in self._state:
                self._state["active_agents"] = []
            self._state["active_agents"].append(agent)
            self._save()

    def remove_active_agent(self, agent: str) -> None:
        """Remove an agent from the active agents list."""
        if "active_agents" in self._state and agent in self._state["active_agents"]:
            self._state["active_agents"].remove(agent)
            self._save()

    def get_current_state(self) -> SessionState:
        """Get the current session state as a dataclass."""
        return SessionState(
            current_focus=self._state.get("current_focus", ""),
            active_agents=self._state.get("active_agents", []),
            last_updated=self._state.get("last_updated", ""),
            context_summary=self._state.get("context_summary", "")
        )

    def _save(self) -> None:
        """Save current state to disk."""
        self._state["last_updated"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        save_session_state(
            focus=self._state.get("current_focus", ""),
            active_agents=self._state.get("active_agents", []),
            context=self._state.get("context_summary", "")
        )

    def record_search(
        self,
        query: str,
        agent: str,
        result_count: int,
        files_found: Optional[List[str]] = None
    ) -> None:
        """Record a search operation."""
        record_search(
            query=query,
            results=files_found or [],
            agent=agent,
            result_count=result_count
        )

    def check_duplicate_search(self, query: str, hours: int = 24) -> Optional[SearchRecord]:
        """
        Check if a similar search was performed recently.

        Args:
            query: Search query to check
            hours: How far back to look

        Returns:
            SearchRecord if duplicate found, None otherwise
        """
        recent = get_recent_searches(hours=hours)
        for search in recent:
            if search["query"] == query:
                return SearchRecord(
                    query=search["query"],
                    timestamp=search["timestamp"],
                    agent=search["agent"],
                    result_count=search["result_count"],
                    files_found=search["files_found"]
                )
        return None

    def clear_state(self) -> None:
        """Clear all session state (useful for testing)."""
        clear_all_state()
        self._state = self._load_or_create_state()


# Test function
def test_session_state() -> None:
    """Test session state manager functionality"""
    print("Testing session state manager...")

    # Clean start
    clear_all_state()

    # Test 1: Save and load session state
    print("Test 1: Session state persistence")
    save_session_state(
        focus="Testing session state",
        active_agents=["test-agent-1", "test-agent-2"],
        context="Running unit tests",
    )

    loaded = load_session_state()
    assert loaded is not None, "Failed to load session state"
    assert loaded["current_focus"] == "Testing session state"
    assert loaded["active_agents"] == ["test-agent-1", "test-agent-2"]
    print("✓ Session state persistence works")

    # Test 2: Record searches
    print("\nTest 2: Search history")
    record_search(
        query="test query",
        results=["file1.py", "file2.py"],
        agent="test-agent",
    )

    recent = get_recent_searches(hours=24)
    assert len(recent) == 1, "Failed to record search"
    assert recent[0]["query"] == "test query"
    assert recent[0]["result_count"] == 2
    print("✓ Search history works")

    # Test 3: Record decisions
    print("\nTest 3: Decision logging")
    record_decision(
        decision="Use Haiku for routing",
        rationale="Cost-effective for simple requests",
        alternatives=["Always Sonnet", "No routing"],
    )

    recent_decisions = get_recent_decisions(hours=24)
    assert len(recent_decisions) == 1, "Failed to record decision"
    assert recent_decisions[0]["decision"] == "Use Haiku for routing"
    print("✓ Decision logging works")

    # Test 4: Atomic writes (verify file permissions)
    print("\nTest 4: File permissions")
    assert (
        oct(SESSION_STATE_FILE.stat().st_mode)[-3:] == "600"
    ), "Incorrect file permissions"
    print("✓ Secure file permissions")

    # Cleanup
    clear_all_state()
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    # Run tests when executed directly
    test_session_state()