"""
File Locking Protocol - Prevent race conditions in concurrent agent execution.

Implements FR-2.7 (File Locking Protocol) and FR-2.8 (Lock Timeout and Recovery)
from routing-system-requirements.md.

Usage:
    from file_locking import locked_state_file

    with locked_state_file(Path("state.json"), 'r+') as f:
        data = json.load(f)
        # modify data
        f.seek(0)
        f.truncate()
        json.dump(data, f)

Change Driver: STATE_PERSISTENCE
Changes when: Concurrency requirements evolve
"""

import fcntl
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Generator, Optional, TextIO

# Lock timeout (seconds)
LOCK_TIMEOUT = 30.0
# Polling interval for lock acquisition
LOCK_POLL_INTERVAL = 0.1


@dataclass
class LockInfo:
    """Information about lock holder for debugging."""

    pid: int
    acquired_at: str
    file_path: str


def _get_lock_file_path(state_file: Path) -> Path:
    """Get the path to the lock info file."""
    return Path(str(state_file) + ".lock")


def _write_lock_holder(lock_file: Path, state_file: Path) -> None:
    """Record lock holder PID for debugging."""
    lock_info = LockInfo(
        pid=os.getpid(),
        acquired_at=datetime.now(UTC).isoformat(),
        file_path=str(state_file),
    )
    try:
        with open(lock_file, "w") as f:
            json.dump(
                {
                    "pid": lock_info.pid,
                    "acquired_at": lock_info.acquired_at,
                    "file_path": lock_info.file_path,
                },
                f,
            )
    except IOError:
        pass  # Non-critical, just for debugging


def _remove_lock_holder(lock_file: Path) -> None:
    """Remove lock holder file."""
    try:
        lock_file.unlink()
    except FileNotFoundError:
        pass


def _check_stale_lock(lock_file: Path) -> bool:
    """
    Check if the lock holder process is dead (stale lock).

    Returns:
        True if lock is stale (holder is dead), False otherwise
    """
    if not lock_file.exists():
        return True

    try:
        with open(lock_file, "r") as f:
            data = json.load(f)
            pid = data.get("pid")

            if pid is None:
                return True

            # Check if process is alive by sending signal 0
            try:
                os.kill(pid, 0)
                return False  # Process is alive
            except OSError:
                return True  # Process is dead

    except (json.JSONDecodeError, IOError, KeyError):
        # Malformed lock file, treat as stale
        return True


def _handle_lock_timeout(lock_file: Path, state_file: Path) -> None:
    """
    Handle lock timeout - check if holder is still alive.

    Raises:
        RuntimeError: If lock is held by active process
        TimeoutError: If lock cannot be acquired
    """
    if _check_stale_lock(lock_file):
        # Stale lock, remove it
        _remove_lock_holder(lock_file)
        # Don't raise - caller will retry
        return

    # Lock is held by active process
    try:
        with open(lock_file, "r") as f:
            data = json.load(f)
            pid = data.get("pid", "unknown")
            acquired_at = data.get("acquired_at", "unknown")

        raise RuntimeError(
            f"State file {state_file} locked by active process {pid} "
            f"(since {acquired_at}). Lock file: {lock_file}"
        )
    except (json.JSONDecodeError, IOError):
        raise TimeoutError(f"Could not acquire lock on {state_file} within timeout")


@contextmanager
def locked_state_file(
    path: Path,
    mode: str = "r+",
    timeout: float = LOCK_TIMEOUT,
    create_if_missing: bool = False,
) -> Generator[TextIO, None, None]:
    """
    Acquire exclusive lock on state file for read-modify-write operations.

    Args:
        path: Path to state file
        mode: File open mode ('r', 'r+', 'w', etc.)
        timeout: Lock acquisition timeout in seconds
        create_if_missing: Create file with empty JSON object if it doesn't exist

    Yields:
        File handle with exclusive lock held

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
        RuntimeError: If lock held by active process
        FileNotFoundError: If file doesn't exist and create_if_missing is False
    """
    lock_file = _get_lock_file_path(path)

    # Handle file creation if requested
    if create_if_missing and not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with open(path, "w") as f:
            json.dump({}, f)
        os.chmod(path, 0o600)

    # Open file
    f: Optional[TextIO] = None
    try:
        f = open(path, mode)

        # Attempt to acquire lock with timeout
        start = time.monotonic()
        lock_acquired = False

        while not lock_acquired:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_acquired = True
            except BlockingIOError:
                elapsed = time.monotonic() - start
                if elapsed > timeout:
                    _handle_lock_timeout(lock_file, path)
                    # If we get here, stale lock was removed, retry once
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        lock_acquired = True
                    except BlockingIOError:
                        raise TimeoutError(
                            f"Could not acquire lock on {path} within {timeout}s"
                        )
                else:
                    time.sleep(LOCK_POLL_INTERVAL)

        # Lock acquired, write holder info
        _write_lock_holder(lock_file, path)

        try:
            yield f
        finally:
            # Release lock
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            _remove_lock_holder(lock_file)

    finally:
        if f is not None:
            f.close()


@contextmanager
def locked_state_file_shared(
    path: Path,
    timeout: float = LOCK_TIMEOUT,
) -> Generator[TextIO, None, None]:
    """
    Acquire shared (read) lock on state file.

    Multiple readers can hold shared locks simultaneously,
    but writers must wait for all readers to finish.

    Args:
        path: Path to state file
        timeout: Lock acquisition timeout in seconds

    Yields:
        File handle with shared lock held
    """
    f: Optional[TextIO] = None
    try:
        f = open(path, "r")

        start = time.monotonic()
        lock_acquired = False

        while not lock_acquired:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                lock_acquired = True
            except BlockingIOError:
                if time.monotonic() - start > timeout:
                    raise TimeoutError(
                        f"Could not acquire shared lock on {path} within {timeout}s"
                    )
                time.sleep(LOCK_POLL_INTERVAL)

        try:
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    finally:
        if f is not None:
            f.close()


def test_file_locking() -> None:
    """Test file locking functionality."""
    import tempfile

    print("Testing file locking...")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test-state.json"

        # Test 1: Create and lock file
        print("Test 1: Basic lock acquisition")
        with open(test_file, "w") as f:
            json.dump({"count": 0}, f)

        with locked_state_file(test_file, "r+") as f:
            data = json.load(f)
            assert data["count"] == 0
            data["count"] = 1
            f.seek(0)
            f.truncate()
            json.dump(data, f)

        # Verify write
        with open(test_file, "r") as f:
            data = json.load(f)
            assert data["count"] == 1
        print("  OK")

        # Test 2: Lock info file created and removed
        print("Test 2: Lock info file lifecycle")
        lock_file = _get_lock_file_path(test_file)
        assert not lock_file.exists(), "Lock file should not exist outside context"
        print("  OK")

        # Test 3: Shared lock
        print("Test 3: Shared lock")
        with locked_state_file_shared(test_file) as f:
            data = json.load(f)
            assert data["count"] == 1
        print("  OK")

        # Test 4: Create if missing
        print("Test 4: Create if missing")
        new_file = Path(tmpdir) / "new-state.json"
        with locked_state_file(new_file, "r+", create_if_missing=True) as f:
            data = json.load(f)
            assert data == {}
            f.seek(0)
            f.truncate()
            json.dump({"created": True}, f)
        print("  OK")

        # Test 5: Stale lock detection
        print("Test 5: Stale lock detection")
        # Create a fake stale lock with non-existent PID
        with open(lock_file, "w") as f:
            json.dump({"pid": 999999999, "acquired_at": "test", "file_path": str(test_file)}, f)

        assert _check_stale_lock(lock_file) is True, "Should detect stale lock"
        print("  OK")

    print("\nAll file locking tests passed!")


if __name__ == "__main__":
    test_file_locking()
