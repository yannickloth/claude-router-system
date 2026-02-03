"""
Tests for file_locking module.

Tests file locking, stale lock detection, and concurrent access.
"""

import json
import os
import pytest
import threading
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from file_locking import (
    locked_state_file,
    locked_state_file_shared,
    _check_stale_lock,
    _get_lock_file_path,
    _write_lock_holder,
    _remove_lock_holder,
    LOCK_TIMEOUT,
)


class TestBasicLocking:
    """Test basic lock acquisition and release."""

    def test_exclusive_lock_acquisition(self, tmp_path):
        """Should acquire and release exclusive lock."""
        test_file = tmp_path / "test-state.json"
        test_file.write_text('{"count": 0}')

        with locked_state_file(test_file, "r+") as f:
            data = json.load(f)
            assert data["count"] == 0

        # Lock should be released
        lock_file = _get_lock_file_path(test_file)
        assert not lock_file.exists()

    def test_shared_lock_acquisition(self, tmp_path):
        """Should acquire and release shared lock."""
        test_file = tmp_path / "test-state.json"
        test_file.write_text('{"count": 42}')

        with locked_state_file_shared(test_file) as f:
            data = json.load(f)
            assert data["count"] == 42

    def test_lock_file_created_during_lock(self, tmp_path):
        """Lock info file should exist while lock is held."""
        test_file = tmp_path / "test-state.json"
        test_file.write_text('{}')

        lock_file = _get_lock_file_path(test_file)

        with locked_state_file(test_file, "r+") as f:
            # Lock file should exist during lock
            assert lock_file.exists()

        # Lock file should be removed after
        assert not lock_file.exists()


class TestReadModifyWrite:
    """Test read-modify-write operations."""

    def test_modify_file_content(self, tmp_path):
        """Should safely modify file content."""
        test_file = tmp_path / "test-state.json"
        test_file.write_text('{"count": 0}')

        with locked_state_file(test_file, "r+") as f:
            data = json.load(f)
            data["count"] = 10
            f.seek(0)
            f.truncate()
            json.dump(data, f)

        # Verify modification
        with open(test_file) as f:
            data = json.load(f)
            assert data["count"] == 10

    def test_multiple_modifications(self, tmp_path):
        """Should handle multiple sequential modifications."""
        test_file = tmp_path / "test-state.json"
        test_file.write_text('{"count": 0}')

        for i in range(5):
            with locked_state_file(test_file, "r+") as f:
                data = json.load(f)
                data["count"] = i + 1
                f.seek(0)
                f.truncate()
                json.dump(data, f)

        with open(test_file) as f:
            data = json.load(f)
            assert data["count"] == 5


class TestCreateIfMissing:
    """Test file creation functionality."""

    def test_create_missing_file(self, tmp_path):
        """Should create file if missing when flag is set."""
        new_file = tmp_path / "new-state.json"
        assert not new_file.exists()

        with locked_state_file(new_file, "r+", create_if_missing=True) as f:
            data = json.load(f)
            assert data == {}

        assert new_file.exists()

    def test_create_missing_with_parent_dirs(self, tmp_path):
        """Should create parent directories if needed."""
        deep_file = tmp_path / "deep" / "nested" / "state.json"
        assert not deep_file.parent.exists()

        with locked_state_file(deep_file, "r+", create_if_missing=True) as f:
            data = json.load(f)

        assert deep_file.exists()

    def test_no_create_raises_error(self, tmp_path):
        """Should raise error for missing file without flag."""
        missing_file = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            with locked_state_file(missing_file, "r+") as f:
                pass


class TestStaleLockDetection:
    """Test stale lock detection and recovery."""

    def test_detect_stale_lock_dead_process(self, tmp_path):
        """Should detect lock from dead process."""
        test_file = tmp_path / "test-state.json"
        test_file.write_text('{}')

        lock_file = _get_lock_file_path(test_file)

        # Create fake stale lock with non-existent PID
        with open(lock_file, "w") as f:
            json.dump({
                "pid": 999999999,  # Very unlikely to exist
                "acquired_at": "2024-01-01T00:00:00",
                "file_path": str(test_file)
            }, f)

        assert _check_stale_lock(lock_file) is True

    def test_detect_active_lock(self, tmp_path):
        """Should detect lock from active process."""
        test_file = tmp_path / "test-state.json"
        test_file.write_text('{}')

        lock_file = _get_lock_file_path(test_file)

        # Create lock with current process PID
        with open(lock_file, "w") as f:
            json.dump({
                "pid": os.getpid(),  # Current process
                "acquired_at": "2024-01-01T00:00:00",
                "file_path": str(test_file)
            }, f)

        assert _check_stale_lock(lock_file) is False

        # Cleanup
        lock_file.unlink()

    def test_missing_lock_file_is_stale(self, tmp_path):
        """Should treat missing lock file as stale."""
        missing_lock = tmp_path / "missing.json.lock"
        assert _check_stale_lock(missing_lock) is True


class TestLockInfoFile:
    """Test lock info file operations."""

    def test_write_lock_holder(self, tmp_path):
        """Should write lock holder info."""
        test_file = tmp_path / "test.json"
        lock_file = _get_lock_file_path(test_file)

        _write_lock_holder(lock_file, test_file)

        assert lock_file.exists()

        with open(lock_file) as f:
            data = json.load(f)
            assert data["pid"] == os.getpid()
            assert "acquired_at" in data
            assert data["file_path"] == str(test_file)

        # Cleanup
        lock_file.unlink()

    def test_remove_lock_holder(self, tmp_path):
        """Should remove lock holder info."""
        lock_file = tmp_path / "test.json.lock"
        lock_file.write_text('{"test": "data"}')

        _remove_lock_holder(lock_file)

        assert not lock_file.exists()

    def test_remove_nonexistent_lock(self, tmp_path):
        """Should handle removing nonexistent lock file."""
        lock_file = tmp_path / "nonexistent.lock"

        # Should not raise
        _remove_lock_holder(lock_file)


class TestLockFilePath:
    """Test lock file path generation."""

    def test_lock_file_path_format(self, tmp_path):
        """Lock file should have .lock extension."""
        state_file = tmp_path / "state.json"
        lock_file = _get_lock_file_path(state_file)

        assert str(lock_file).endswith(".lock")
        assert str(lock_file) == str(state_file) + ".lock"


class TestConcurrentAccess:
    """Test concurrent access handling."""

    def test_sequential_access(self, tmp_path):
        """Multiple sequential accesses should work."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"count": 0}')

        results = []

        def increment():
            with locked_state_file(test_file, "r+") as f:
                data = json.load(f)
                count = data["count"]
                results.append(count)
                data["count"] = count + 1
                f.seek(0)
                f.truncate()
                json.dump(data, f)

        # Run 5 sequential increments
        for _ in range(5):
            increment()

        with open(test_file) as f:
            final = json.load(f)
            assert final["count"] == 5


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_malformed_lock_file(self, tmp_path):
        """Should handle malformed lock file."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{}')

        lock_file = _get_lock_file_path(test_file)
        lock_file.write_text("not valid json")

        # Should treat malformed as stale
        assert _check_stale_lock(lock_file) is True

    def test_empty_lock_file(self, tmp_path):
        """Should handle empty lock file."""
        lock_file = tmp_path / "test.json.lock"
        lock_file.write_text("")

        assert _check_stale_lock(lock_file) is True

    def test_lock_with_missing_pid(self, tmp_path):
        """Should handle lock file without PID."""
        lock_file = tmp_path / "test.json.lock"
        lock_file.write_text('{"acquired_at": "test"}')

        assert _check_stale_lock(lock_file) is True


class TestConstants:
    """Test module constants."""

    def test_lock_timeout_reasonable(self):
        """Lock timeout should be reasonable value."""
        assert LOCK_TIMEOUT >= 1
        assert LOCK_TIMEOUT <= 120  # Max 2 minutes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
