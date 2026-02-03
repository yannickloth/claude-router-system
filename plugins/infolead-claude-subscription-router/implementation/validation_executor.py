"""
Validation Executor - Execute validation checks for probabilistic routing.

Implements Solution 6 (Validation System) from architecture spec.
Supports syntax, build, and test validation hooks for quality assurance.

Usage:
    executor = ValidationExecutor()
    results = executor.validate_all(modified_files)
    if executor.all_passed(results):
        print("All validations passed")

Change Driver: QUALITY_ASSURANCE
Changes when: Validation requirements or tooling changes
"""

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# Validation timeout (seconds)
DEFAULT_TIMEOUT = 30
BUILD_TIMEOUT = 120
TEST_TIMEOUT = 60


class ValidationType(Enum):
    """Types of validation checks."""

    SYNTAX = "syntax"
    BUILD = "build"
    TEST = "test"
    DIFF = "diff"


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    validation_type: ValidationType
    details: str
    exit_code: int
    output: str


class ValidationExecutor:
    """Execute validation checks based on file types and domain."""

    # Syntax validators by file extension
    SYNTAX_VALIDATORS = {
        ".py": ["python3", "-m", "py_compile"],
        ".js": ["npx", "eslint", "--no-fix", "--quiet"],
        ".ts": ["npx", "tsc", "--noEmit", "--skipLibCheck"],
        ".tsx": ["npx", "tsc", "--noEmit", "--skipLibCheck"],
        ".tex": ["chktex", "-q", "-n1", "-n3", "-n6", "-n8"],
        ".json": ["python3", "-c", "import json; json.load(open('{}'))"],
        ".yaml": ["python3", "-c", "import yaml; yaml.safe_load(open('{}'))"],
        ".yml": ["python3", "-c", "import yaml; yaml.safe_load(open('{}'))"],
    }

    # Build commands by project type
    BUILD_COMMANDS = {
        "nix": ["nix", "build", "--dry-run"],
        "npm": ["npm", "run", "build", "--if-present"],
        "python": ["python3", "-m", "build", "--check"],
        "latex": ["latexmk", "-pdf", "-halt-on-error", "-interaction=nonstopmode"],
    }

    # Test commands by project type (collection only, not full run)
    TEST_COMMANDS = {
        "pytest": ["pytest", "--collect-only", "-q"],
        "npm": ["npm", "test", "--if-present", "--", "--listTests"],
        "nix": ["nix", "flake", "check", "--dry-run"],
    }

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize validation executor.

        Args:
            project_root: Root directory of project (defaults to cwd)
        """
        self.project_root = project_root or Path.cwd()
        self.project_type = self._detect_project_type()

    def _detect_project_type(self) -> Optional[str]:
        """Detect project type from files."""
        if (self.project_root / "flake.nix").exists():
            return "nix"
        elif (self.project_root / "package.json").exists():
            return "npm"
        elif (self.project_root / "pyproject.toml").exists():
            return "python"
        elif list(self.project_root.glob("*.tex")) or (
            self.project_root / "main.tex"
        ).exists():
            return "latex"
        return None

    def _run_command(
        self,
        cmd: List[str],
        timeout: int = DEFAULT_TIMEOUT,
        cwd: Optional[Path] = None,
    ) -> tuple[int, str]:
        """
        Run a command and capture output.

        Returns:
            Tuple of (exit_code, combined_output)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or self.project_root,
            )
            output = result.stdout + result.stderr
            return result.returncode, output.strip()
        except subprocess.TimeoutExpired:
            return -1, f"Command timed out after {timeout}s"
        except FileNotFoundError as e:
            return -2, f"Command not found: {e}"
        except Exception as e:
            return -3, f"Command failed: {e}"

    def validate_syntax(self, file_path: Path) -> ValidationResult:
        """
        Run syntax validation on a file.

        Args:
            file_path: Path to file to validate

        Returns:
            ValidationResult with pass/fail status
        """
        ext = file_path.suffix.lower()

        if ext not in self.SYNTAX_VALIDATORS:
            return ValidationResult(
                passed=True,
                validation_type=ValidationType.SYNTAX,
                details=f"No syntax validator for {ext}",
                exit_code=0,
                output="",
            )

        cmd = self.SYNTAX_VALIDATORS[ext].copy()

        # Handle template commands with {} placeholder
        has_placeholder = any("{}" in part for part in cmd)
        if has_placeholder:
            cmd = [part.replace("{}", str(file_path)) for part in cmd]
        else:
            cmd.append(str(file_path))

        exit_code, output = self._run_command(cmd)

        return ValidationResult(
            passed=exit_code == 0,
            validation_type=ValidationType.SYNTAX,
            details=f"Syntax check: {file_path.name}",
            exit_code=exit_code,
            output=output,
        )

    def validate_build(self) -> ValidationResult:
        """
        Run build validation for project.

        Returns:
            ValidationResult with pass/fail status
        """
        if self.project_type is None:
            return ValidationResult(
                passed=True,
                validation_type=ValidationType.BUILD,
                details="No build system detected",
                exit_code=0,
                output="",
            )

        cmd = self.BUILD_COMMANDS.get(self.project_type)
        if cmd is None:
            return ValidationResult(
                passed=True,
                validation_type=ValidationType.BUILD,
                details=f"No build command for {self.project_type}",
                exit_code=0,
                output="",
            )

        exit_code, output = self._run_command(cmd, timeout=BUILD_TIMEOUT)

        return ValidationResult(
            passed=exit_code == 0,
            validation_type=ValidationType.BUILD,
            details=f"Build check ({self.project_type})",
            exit_code=exit_code,
            output=output,
        )

    def validate_tests(self) -> ValidationResult:
        """
        Run test collection (not full tests) to verify test integrity.

        Returns:
            ValidationResult with pass/fail status
        """
        test_type = None

        # Detect test framework
        if (self.project_root / "pytest.ini").exists() or (
            self.project_root / "pyproject.toml"
        ).exists():
            # Check if pytest is configured
            pyproject = self.project_root / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text()
                if "[tool.pytest" in content or "pytest" in content:
                    test_type = "pytest"

        if test_type is None and (self.project_root / "package.json").exists():
            test_type = "npm"

        if test_type is None and self.project_type == "nix":
            test_type = "nix"

        if test_type is None:
            return ValidationResult(
                passed=True,
                validation_type=ValidationType.TEST,
                details="No test framework detected",
                exit_code=0,
                output="",
            )

        cmd = self.TEST_COMMANDS.get(test_type)
        if cmd is None:
            return ValidationResult(
                passed=True,
                validation_type=ValidationType.TEST,
                details=f"No test command for {test_type}",
                exit_code=0,
                output="",
            )

        exit_code, output = self._run_command(cmd, timeout=TEST_TIMEOUT)

        return ValidationResult(
            passed=exit_code == 0,
            validation_type=ValidationType.TEST,
            details=f"Test check ({test_type})",
            exit_code=exit_code,
            output=output,
        )

    def validate_all(
        self, modified_files: List[Path], fast_fail: bool = True
    ) -> Dict[str, ValidationResult]:
        """
        Run all applicable validations.

        Args:
            modified_files: List of files that were modified
            fast_fail: Stop on first failure if True

        Returns:
            Dict mapping validation name to result
        """
        results = {}

        # Syntax check each modified file
        for file_path in modified_files:
            if not file_path.exists():
                continue

            result = self.validate_syntax(file_path)
            results[f"syntax:{file_path.name}"] = result

            if fast_fail and not result.passed:
                return results

        # Build check
        results["build"] = self.validate_build()
        if fast_fail and not results["build"].passed:
            return results

        # Test collection check
        results["tests"] = self.validate_tests()

        return results

    def all_passed(self, results: Dict[str, ValidationResult]) -> bool:
        """Check if all validations passed."""
        return all(r.passed for r in results.values())

    def display_results(self, results: Dict[str, ValidationResult]) -> None:
        """Display validation results to console."""
        print("Validation Results")
        print("=" * 50)

        passed_count = 0
        failed_count = 0

        for name, result in results.items():
            status = "PASS" if result.passed else "FAIL"
            icon = "OK" if result.passed else "FAIL"

            print(f"  [{icon}] {name}: {result.details}")

            if result.passed:
                passed_count += 1
            else:
                failed_count += 1
                if result.output:
                    # Show first 3 lines of error output
                    lines = result.output.split("\n")[:3]
                    for line in lines:
                        print(f"       {line}")

        print("=" * 50)
        print(f"Passed: {passed_count}, Failed: {failed_count}")

        if failed_count > 0:
            print("\nValidation FAILED")
        else:
            print("\nValidation PASSED")


def main():
    """CLI interface for validation executor."""
    import argparse

    parser = argparse.ArgumentParser(description="Validation Executor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # validate command
    val_parser = subparsers.add_parser("validate", help="Run validations")
    val_parser.add_argument(
        "files", nargs="*", type=Path, help="Files to validate"
    )
    val_parser.add_argument(
        "--no-fast-fail", action="store_true", help="Run all validations even on failure"
    )
    val_parser.add_argument(
        "--project", type=Path, help="Project root directory"
    )

    # syntax command
    syn_parser = subparsers.add_parser("syntax", help="Run syntax check only")
    syn_parser.add_argument("file", type=Path, help="File to check")

    # build command
    build_parser = subparsers.add_parser("build", help="Run build check only")
    build_parser.add_argument(
        "--project", type=Path, help="Project root directory"
    )

    # detect command
    det_parser = subparsers.add_parser("detect", help="Detect project type")
    det_parser.add_argument(
        "--project", type=Path, help="Project root directory"
    )

    args = parser.parse_args()

    project_root = getattr(args, "project", None)
    executor = ValidationExecutor(project_root=project_root)

    if args.command == "validate" or args.command is None:
        files = getattr(args, "files", []) or []
        if not files:
            # Find modified files via git
            try:
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=executor.project_root,
                )
                if result.returncode == 0:
                    files = [
                        Path(f) for f in result.stdout.strip().split("\n") if f
                    ]
            except Exception:
                pass

        if not files:
            print("No files to validate. Specify files or have git changes.")
            sys.exit(0)

        fast_fail = not getattr(args, "no_fast_fail", False)
        results = executor.validate_all(files, fast_fail=fast_fail)
        executor.display_results(results)
        sys.exit(0 if executor.all_passed(results) else 1)

    elif args.command == "syntax":
        result = executor.validate_syntax(args.file)
        print(f"{'PASS' if result.passed else 'FAIL'}: {result.details}")
        if result.output:
            print(result.output)
        sys.exit(0 if result.passed else 1)

    elif args.command == "build":
        result = executor.validate_build()
        print(f"{'PASS' if result.passed else 'FAIL'}: {result.details}")
        if result.output:
            print(result.output)
        sys.exit(0 if result.passed else 1)

    elif args.command == "detect":
        print(f"Project type: {executor.project_type or 'unknown'}")
        print(f"Project root: {executor.project_root}")


def test_validation_executor() -> None:
    """Test validation executor functionality."""
    import tempfile

    print("Testing validation executor...")

    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)

        # Test 1: Create valid Python file
        print("Test 1: Valid Python syntax")
        py_file = project / "test.py"
        py_file.write_text("def hello():\n    return 'hello'\n")

        executor = ValidationExecutor(project_root=project)
        result = executor.validate_syntax(py_file)
        assert result.passed, f"Valid Python should pass: {result.output}"
        print("  OK")

        # Test 2: Invalid Python syntax
        print("Test 2: Invalid Python syntax")
        bad_py = project / "bad.py"
        bad_py.write_text("def hello(\n")

        result = executor.validate_syntax(bad_py)
        assert not result.passed, "Invalid Python should fail"
        print("  OK")

        # Test 3: Valid JSON
        print("Test 3: Valid JSON syntax")
        json_file = project / "test.json"
        json_file.write_text('{"key": "value"}')

        result = executor.validate_syntax(json_file)
        assert result.passed, f"Valid JSON should pass: {result.output}"
        print("  OK")

        # Test 4: Unknown extension
        print("Test 4: Unknown extension")
        unknown = project / "test.xyz"
        unknown.write_text("random content")

        result = executor.validate_syntax(unknown)
        assert result.passed, "Unknown extension should pass (no validator)"
        print("  OK")

        # Test 5: validate_all
        print("Test 5: validate_all")
        results = executor.validate_all([py_file, json_file])
        assert executor.all_passed(results), "All valid files should pass"
        print("  OK")

        # Test 6: validate_all with failure
        print("Test 6: validate_all with failure (fast_fail)")
        results = executor.validate_all([bad_py, py_file], fast_fail=True)
        assert not executor.all_passed(results), "Should fail on bad file"
        assert len(results) == 1, "Fast fail should stop after first failure"
        print("  OK")

    print("\nAll validation executor tests passed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_validation_executor()
    else:
        main()
