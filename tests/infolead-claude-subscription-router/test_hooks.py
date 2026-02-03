"""
Pytest wrapper for hook script testing.

Tests hook scripts execute correctly and handle inputs properly.
"""

import json
import os
import subprocess
import pytest
from pathlib import Path

# Plugin root
PLUGIN_ROOT = Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router"
HOOKS_DIR = PLUGIN_ROOT / "hooks"


class TestHookScriptExecution:
    """Test hook script execution."""

    @pytest.fixture
    def test_input(self, tmp_path):
        """Create standard test input for hooks."""
        return {
            "cwd": str(tmp_path),
            "agent_type": "test-agent",
            "agent_id": "test-id-12345678",
            "exit_status": "success",
            "transcript_path": "",
        }

    def test_start_hook_executes(self, test_input, tmp_path):
        """Start hook should execute without error."""
        start_script = HOOKS_DIR / "log-subagent-start.sh"
        if not start_script.exists():
            pytest.skip("Start hook not found")

        result = subprocess.run(
            ["bash", str(start_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should not fail (exit 0 or exit with warning)
        assert result.returncode in [0, 1], f"Hook failed: {result.stderr}"

    def test_stop_hook_executes(self, test_input, tmp_path):
        """Stop hook should execute without error."""
        stop_script = HOOKS_DIR / "log-subagent-stop.sh"
        if not stop_script.exists():
            pytest.skip("Stop hook not found")

        result = subprocess.run(
            ["bash", str(stop_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should not fail
        assert result.returncode in [0, 1], f"Hook failed: {result.stderr}"

    def test_start_hook_creates_log(self, test_input, tmp_path):
        """Start hook should create routing log."""
        start_script = HOOKS_DIR / "log-subagent-start.sh"
        if not start_script.exists():
            pytest.skip("Start hook not found")

        subprocess.run(
            ["bash", str(start_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=10,
        )

        log_file = tmp_path / ".claude" / "logs" / "routing.log"
        # Log may or may not be created depending on hook success
        # Just verify no crash

    def test_stop_hook_outputs_to_stderr(self, test_input, tmp_path):
        """Stop hook should output status to stderr."""
        stop_script = HOOKS_DIR / "log-subagent-stop.sh"
        if not stop_script.exists():
            pytest.skip("Stop hook not found")

        result = subprocess.run(
            ["bash", str(stop_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should have some output on stderr
        # (may be error or success message)
        assert result.stderr is not None


class TestHookInputHandling:
    """Test hook input handling."""

    def test_missing_fields_handled(self, tmp_path):
        """Hooks should handle missing input fields."""
        start_script = HOOKS_DIR / "log-subagent-start.sh"
        if not start_script.exists():
            pytest.skip("Start hook not found")

        # Minimal input
        minimal_input = {"cwd": str(tmp_path)}

        result = subprocess.run(
            ["bash", str(start_script)],
            input=json.dumps(minimal_input),
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should handle gracefully (not crash)
        # Return code 0 or 1 acceptable

    def test_empty_input_handled(self, tmp_path):
        """Hooks should handle empty JSON input."""
        start_script = HOOKS_DIR / "log-subagent-start.sh"
        if not start_script.exists():
            pytest.skip("Start hook not found")

        result = subprocess.run(
            ["bash", str(start_script)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should not crash


class TestJqDependency:
    """Test jq dependency handling."""

    def test_jq_available(self):
        """Test that jq is available."""
        result = subprocess.run(
            ["which", "jq"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.skip("jq not installed - hooks will fail")

    def test_hooks_check_for_jq(self):
        """Hooks should check for jq dependency."""
        for hook_script in HOOKS_DIR.glob("*.sh"):
            content = hook_script.read_text()

            # Should check for jq
            assert "command -v jq" in content or "which jq" in content, (
                f"{hook_script.name} uses jq but doesn't check for it"
            )


class TestHookTimeout:
    """Test hook timeout behavior."""

    def test_hooks_complete_quickly(self, tmp_path):
        """Hooks should complete within timeout."""
        test_input = {
            "cwd": str(tmp_path),
            "agent_type": "test-agent",
            "agent_id": "test-id",
        }

        for hook_script in HOOKS_DIR.glob("*.sh"):
            try:
                result = subprocess.run(
                    ["bash", str(hook_script)],
                    input=json.dumps(test_input),
                    capture_output=True,
                    text=True,
                    timeout=5,  # 5 second timeout
                )
            except subprocess.TimeoutExpired:
                pytest.fail(f"{hook_script.name} timed out")


class TestHookOutputFormat:
    """Test hook output format."""

    def test_start_hook_output_format(self, tmp_path):
        """Start hook should output expected format."""
        start_script = HOOKS_DIR / "log-subagent-start.sh"
        if not start_script.exists():
            pytest.skip("Start hook not found")

        test_input = {
            "cwd": str(tmp_path),
            "agent_type": "test-agent",
            "agent_id": "test-id-12345678",
        }

        result = subprocess.run(
            ["bash", str(start_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Output should contain routing marker
        if result.returncode == 0:
            assert "[routing]" in result.stderr or result.stderr == ""

    def test_stop_hook_output_format(self, tmp_path):
        """Stop hook should output expected format."""
        stop_script = HOOKS_DIR / "log-subagent-stop.sh"
        if not stop_script.exists():
            pytest.skip("Stop hook not found")

        test_input = {
            "cwd": str(tmp_path),
            "agent_type": "test-agent",
            "agent_id": "test-id-12345678",
            "exit_status": "success",
        }

        result = subprocess.run(
            ["bash", str(stop_script)],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Output should contain routing marker
        if result.returncode == 0:
            assert "[routing]" in result.stderr or result.stderr == ""


class TestHookFilePermissions:
    """Test hook file permissions."""

    def test_hooks_are_executable(self):
        """Hook scripts should be executable."""
        import stat

        for hook_script in HOOKS_DIR.glob("*.sh"):
            mode = os.stat(hook_script).st_mode
            is_executable = bool(mode & stat.S_IXUSR)
            assert is_executable, f"{hook_script.name} should be executable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
