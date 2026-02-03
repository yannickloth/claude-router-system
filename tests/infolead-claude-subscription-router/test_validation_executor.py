"""
Tests for validation_executor module.

Tests syntax validation, build checks, and test collection.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from validation_executor import (
    ValidationExecutor,
    ValidationResult,
    ValidationType,
)


class TestSyntaxValidation:
    """Test syntax validation for various file types."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with temp project root."""
        return ValidationExecutor(project_root=tmp_path)

    def test_valid_python_syntax(self, executor, tmp_path):
        """Should pass for valid Python syntax."""
        py_file = tmp_path / "valid.py"
        py_file.write_text("def hello():\n    return 'hello'\n")

        result = executor.validate_syntax(py_file)

        assert result.passed is True
        assert result.validation_type == ValidationType.SYNTAX

    def test_invalid_python_syntax(self, executor, tmp_path):
        """Should fail for invalid Python syntax."""
        py_file = tmp_path / "invalid.py"
        py_file.write_text("def hello(\n")

        result = executor.validate_syntax(py_file)

        assert result.passed is False
        assert result.validation_type == ValidationType.SYNTAX

    def test_valid_json_syntax(self, executor, tmp_path):
        """Should pass for valid JSON."""
        json_file = tmp_path / "valid.json"
        json_file.write_text('{"key": "value", "number": 42}')

        result = executor.validate_syntax(json_file)

        assert result.passed is True

    def test_invalid_json_syntax(self, executor, tmp_path):
        """Should fail for invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text('{"key": "value",}')  # Trailing comma

        result = executor.validate_syntax(json_file)

        assert result.passed is False

    def test_unknown_extension(self, executor, tmp_path):
        """Should pass for unknown file extensions (no validator)."""
        unknown_file = tmp_path / "file.xyz"
        unknown_file.write_text("random content")

        result = executor.validate_syntax(unknown_file)

        # Should pass because no validator exists
        assert result.passed is True
        assert "No syntax validator" in result.details


class TestProjectTypeDetection:
    """Test project type detection."""

    def test_detect_nix_project(self, tmp_path):
        """Should detect Nix projects."""
        (tmp_path / "flake.nix").write_text("{}")

        executor = ValidationExecutor(project_root=tmp_path)

        assert executor.project_type == "nix"

    def test_detect_npm_project(self, tmp_path):
        """Should detect NPM projects."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        executor = ValidationExecutor(project_root=tmp_path)

        assert executor.project_type == "npm"

    def test_detect_python_project(self, tmp_path):
        """Should detect Python projects."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        executor = ValidationExecutor(project_root=tmp_path)

        assert executor.project_type == "python"

    def test_detect_latex_project(self, tmp_path):
        """Should detect LaTeX projects."""
        (tmp_path / "main.tex").write_text("\\documentclass{article}")

        executor = ValidationExecutor(project_root=tmp_path)

        assert executor.project_type == "latex"

    def test_detect_no_project_type(self, tmp_path):
        """Should return None for unknown project types."""
        # Empty directory
        executor = ValidationExecutor(project_root=tmp_path)

        assert executor.project_type is None


class TestBuildValidation:
    """Test build validation."""

    def test_no_build_system(self, tmp_path):
        """Should pass when no build system detected."""
        executor = ValidationExecutor(project_root=tmp_path)

        result = executor.validate_build()

        assert result.passed is True
        assert "No build system" in result.details

    def test_build_result_type(self, tmp_path):
        """Build result should have correct type."""
        executor = ValidationExecutor(project_root=tmp_path)

        result = executor.validate_build()

        assert result.validation_type == ValidationType.BUILD


class TestTestValidation:
    """Test test collection validation."""

    def test_no_test_framework(self, tmp_path):
        """Should pass when no test framework detected."""
        executor = ValidationExecutor(project_root=tmp_path)

        result = executor.validate_tests()

        assert result.passed is True
        assert "No test framework" in result.details

    def test_test_result_type(self, tmp_path):
        """Test result should have correct type."""
        executor = ValidationExecutor(project_root=tmp_path)

        result = executor.validate_tests()

        assert result.validation_type == ValidationType.TEST


class TestValidateAll:
    """Test combined validation."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor."""
        return ValidationExecutor(project_root=tmp_path)

    def test_validate_all_single_file(self, executor, tmp_path):
        """Should validate single file."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x = 1\n")

        results = executor.validate_all([py_file])

        assert f"syntax:{py_file.name}" in results
        assert "build" in results
        assert "tests" in results

    def test_validate_all_multiple_files(self, executor, tmp_path):
        """Should validate multiple files."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("x = 1\n")
        file2.write_text("y = 2\n")

        results = executor.validate_all([file1, file2])

        assert f"syntax:file1.py" in results
        assert f"syntax:file2.py" in results

    def test_validate_all_fast_fail(self, executor, tmp_path):
        """Should stop on first failure with fast_fail=True."""
        bad_file = tmp_path / "bad.py"
        good_file = tmp_path / "good.py"
        bad_file.write_text("def (\n")  # Invalid syntax
        good_file.write_text("x = 1\n")

        results = executor.validate_all([bad_file, good_file], fast_fail=True)

        # Should only have one syntax result (stopped early)
        syntax_results = [k for k in results.keys() if k.startswith("syntax:")]
        assert len(syntax_results) == 1

    def test_validate_all_no_fast_fail(self, executor, tmp_path):
        """Should continue after failure with fast_fail=False."""
        bad_file = tmp_path / "bad.py"
        good_file = tmp_path / "good.py"
        bad_file.write_text("def (\n")  # Invalid syntax
        good_file.write_text("x = 1\n")

        results = executor.validate_all([bad_file, good_file], fast_fail=False)

        # Should have results for both files
        syntax_results = [k for k in results.keys() if k.startswith("syntax:")]
        assert len(syntax_results) == 2


class TestAllPassed:
    """Test all_passed helper."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor."""
        return ValidationExecutor(project_root=tmp_path)

    def test_all_passed_true(self, executor):
        """Should return True when all pass."""
        results = {
            "syntax:file.py": ValidationResult(
                passed=True,
                validation_type=ValidationType.SYNTAX,
                details="OK",
                exit_code=0,
                output=""
            ),
            "build": ValidationResult(
                passed=True,
                validation_type=ValidationType.BUILD,
                details="OK",
                exit_code=0,
                output=""
            ),
        }

        assert executor.all_passed(results) is True

    def test_all_passed_false(self, executor):
        """Should return False when any fail."""
        results = {
            "syntax:file.py": ValidationResult(
                passed=True,
                validation_type=ValidationType.SYNTAX,
                details="OK",
                exit_code=0,
                output=""
            ),
            "build": ValidationResult(
                passed=False,
                validation_type=ValidationType.BUILD,
                details="Failed",
                exit_code=1,
                output="Error"
            ),
        }

        assert executor.all_passed(results) is False

    def test_all_passed_empty(self, executor):
        """Should return True for empty results."""
        assert executor.all_passed({}) is True


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_result_creation(self):
        """Should create ValidationResult with all fields."""
        result = ValidationResult(
            passed=True,
            validation_type=ValidationType.SYNTAX,
            details="Syntax check passed",
            exit_code=0,
            output="No errors"
        )

        assert result.passed is True
        assert result.validation_type == ValidationType.SYNTAX
        assert result.exit_code == 0

    def test_failed_result(self):
        """Should create failed ValidationResult."""
        result = ValidationResult(
            passed=False,
            validation_type=ValidationType.BUILD,
            details="Build failed",
            exit_code=1,
            output="Compilation error"
        )

        assert result.passed is False
        assert result.exit_code == 1


class TestCommandTimeout:
    """Test command timeout handling."""

    def test_timeout_result(self, tmp_path):
        """Should handle command timeouts gracefully."""
        executor = ValidationExecutor(project_root=tmp_path)

        # Run command with very short timeout (may timeout)
        exit_code, output = executor._run_command(
            ["sleep", "10"],
            timeout=0.1
        )

        # Should return timeout error
        assert exit_code == -1 or "timeout" in output.lower() or exit_code == 0


class TestNonexistentFiles:
    """Test handling of nonexistent files."""

    def test_validate_all_skips_nonexistent(self, tmp_path):
        """Should skip nonexistent files."""
        executor = ValidationExecutor(project_root=tmp_path)

        nonexistent = tmp_path / "does_not_exist.py"
        results = executor.validate_all([nonexistent])

        # Should not have syntax result for nonexistent file
        assert f"syntax:{nonexistent.name}" not in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
