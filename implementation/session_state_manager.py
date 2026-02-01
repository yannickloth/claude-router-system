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
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Optional

# State directory
MEMORY_DIR = Path.home() / ".claude" / "infolead-router" / "memory"

# State files
SESSION_STATE_FILE = MEMORY_DIR / "session-state.json"
SEARCH_HISTORY_FILE = MEMORY_DIR / "search-history.json"
DECISIONS_FILE = MEMORY_DIR / "decisions.json"

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
    """Write data to file atomically using temp file + rename"""
    try:
        # Ensure directory exists
        _ensure_directory()

        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", dir=MEMORY_DIR, delete=False, suffix=".tmp"
        ) as temp_file:
            json.dump(data, temp_file, indent=2)
            temp_name = temp_file.name

        # Set secure permissions
        os.chmod(temp_name, 0o600)  # User read/write only

        # Atomic rename
        os.rename(temp_name, file_path)

    except Exception as e:
        # Clean up temp file on error
        if "temp_name" in locals():
            try:
                os.unlink(temp_name)
            except:
                pass
        raise RuntimeError(f"Failed to write {file_path}: {e}") from e


def _read_json(file_path: Path) -> Optional[dict]:
    """Read JSON file, return None if doesn't exist or invalid"""
    try:
        if not file_path.exists():
            return None

        with open(file_path, "r") as f:
            return json.load(f)

    except (json.JSONDecodeError, IOError) as e:
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
    for file_path in [SESSION_STATE_FILE, SEARCH_HISTORY_FILE, DECISIONS_FILE]:
        if file_path.exists():
            file_path.unlink()


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