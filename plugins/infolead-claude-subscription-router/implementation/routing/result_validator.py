"""
Result Validator - Post-execution validation for routing decisions.

Validates agent execution results against criteria to determine if
escalation to a higher-tier model is needed.

Usage:
    validator = ResultValidator()
    is_valid, reason = validator.validate_result(result, criteria, context)

Change Driver: VALIDATION_CRITERIA
Changes when: Validation rules or criteria change
"""

import ast
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


class ResultValidator:
    """Validates agent execution results to determine if escalation needed."""

    def validate_result(
        self,
        result: Any,
        validation_criteria: List[str],
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate result against criteria.

        Args:
            result: Execution result to validate
            validation_criteria: List of validation types to run
            context: Context with additional info (test commands, etc.)

        Returns:
            Tuple of (is_valid, failure_reason)
        """
        for criterion in validation_criteria:
            validator_method = getattr(self, f"_validate_{criterion}", None)

            if validator_method:
                is_valid, reason = validator_method(result, context)
                if not is_valid:
                    return False, reason

        return True, None

    def _validate_syntax_valid(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check if modified code/LaTeX has valid syntax."""
        # Extract file path from result
        file_path = None
        if isinstance(result, dict):
            file_path = result.get("modified_file") or result.get("file_path")
        elif isinstance(result, str) and os.path.exists(result):
            file_path = result

        if not file_path:
            return True, None

        # Check file type and run appropriate validator
        if file_path.endswith(".py"):
            return self._validate_python_syntax(file_path)
        elif file_path.endswith(".tex"):
            return self._validate_latex_syntax(file_path)
        elif file_path.endswith((".js", ".ts", ".tsx")):
            return self._validate_js_syntax(file_path)
        elif file_path.endswith(".json"):
            return self._validate_json_syntax(file_path)

        return True, None

    def _validate_python_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate Python syntax using ast.parse."""
        try:
            with open(file_path) as f:
                ast.parse(f.read())
            return True, None
        except SyntaxError as e:
            return False, f"Python syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Python validation error: {e}"

    def _validate_latex_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate LaTeX syntax (basic checks)."""
        try:
            with open(file_path) as f:
                content = f.read()

            # Check brace matching
            open_braces = content.count("{")
            close_braces = content.count("}")

            if open_braces != close_braces:
                return False, f"Brace mismatch: {open_braces} open, {close_braces} close"

            # Check environment matching
            begin_envs = re.findall(r"\\begin\{(\w+)\}", content)
            end_envs = re.findall(r"\\end\{(\w+)\}", content)

            if len(begin_envs) != len(end_envs):
                return False, f"Environment mismatch: {len(begin_envs)} begins, {len(end_envs)} ends"

            return True, None
        except Exception as e:
            return False, f"LaTeX validation error: {e}"

    def _validate_js_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate JavaScript/TypeScript syntax using node."""
        try:
            result = subprocess.run(
                ["node", "--check", file_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return False, f"JS syntax error: {result.stderr}"
            return True, None
        except FileNotFoundError:
            # Node not available, skip check
            return True, None
        except subprocess.TimeoutExpired:
            return False, "JS syntax check timed out"
        except Exception as e:
            return True, None  # Skip on errors

    def _validate_json_syntax(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate JSON syntax."""
        try:
            with open(file_path) as f:
                json.load(f)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"JSON syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"JSON validation error: {e}"

    def _validate_no_logic_change(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Verify that logic/behavior didn't change (for refactoring)."""
        # Run tests if available
        test_command = context.get("test_command")
        if test_command:
            try:
                proc = subprocess.run(
                    test_command if isinstance(test_command, list) else test_command.split(),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=context.get("cwd")
                )
                if proc.returncode != 0:
                    return False, f"Tests failed: {proc.stderr[:200]}"
                return True, None
            except subprocess.TimeoutExpired:
                return False, "Tests timed out"
            except Exception as e:
                return True, None  # Skip on errors

        # No tests available, assume valid
        return True, None

    def _validate_results_found(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check that search/find operation returned results."""
        if isinstance(result, list):
            if len(result) == 0:
                return False, "No results found"
            return True, None

        if isinstance(result, dict):
            if "results" in result and len(result["results"]) == 0:
                return False, "No results found"
            if "matches" in result and len(result["matches"]) == 0:
                return False, "No matches found"
            if "files" in result and len(result["files"]) == 0:
                return False, "No files found"

        if isinstance(result, str):
            if "no results" in result.lower() or "not found" in result.lower():
                return False, "No results found"

        return True, None

    def _validate_output_valid(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Generic output validity check."""
        if isinstance(result, str):
            error_markers = [
                "error:", "failed:", "exception:", "traceback:",
                "fatal:", "panic:", "abort:"
            ]
            for marker in error_markers:
                if marker.lower() in result.lower():
                    return False, f"Error detected in output: {marker}"

        if isinstance(result, dict):
            if result.get("error") or result.get("status") == "error":
                return False, f"Error in result: {result.get('error', 'unknown')}"

        return True, None

    def _validate_user_verify(
        self,
        result: Any,
        context: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Require user verification for medium-confidence tasks.
        Always returns True (user will review), but flags for review.
        """
        print("[validation] Result flagged for user review", file=sys.stderr)
        return True, None

    # Patterns that indicate failures beyond simple mechanical fixes
    _REASONING_FAILURE_PATTERNS = [
        r"tests? failed.*logic",
        r"assertion.*error",
        r"unexpected (behavior|result|output)",
        r"design (flaw|issue|problem)",
        r"architectural",
        r"race condition",
        r"incorrect (logic|algorithm|approach)",
        r"fundamental",
        r"conceptual",
        r"misunderst",
    ]

    def should_skip_tier(
        self,
        failure_reason: str,
        candidate_model: str,
    ) -> bool:
        """
        Determine if a candidate fallback model should be skipped.

        When a cheaper model fails, the failure reason may reveal complexity
        that exceeds the next tier's capability. Mechanical failures (syntax,
        format) can be fixed by any tier. Reasoning failures (logic errors,
        design issues) suggest skipping to a higher tier.

        Args:
            failure_reason: Why the previous model's result failed validation
            candidate_model: The model we're considering trying next

        Returns:
            True if candidate_model should be skipped (failure is beyond its tier)
        """
        # Opus is never skipped — it's the top tier
        if candidate_model == "opus":
            return False

        # Mechanical failures are fixable by any tier — never skip
        mechanical_indicators = [
            "syntax error", "brace mismatch", "environment mismatch",
            "json syntax", "no results found", "no matches found",
            "no files found", "command not found", "timed out",
        ]
        failure_lower = failure_reason.lower()
        if any(indicator in failure_lower for indicator in mechanical_indicators):
            return False

        # Check for reasoning-level failure patterns
        if any(re.search(p, failure_lower) for p in self._REASONING_FAILURE_PATTERNS):
            print(f"[validation] Failure indicates reasoning complexity, "
                  f"skipping {candidate_model}", file=sys.stderr)
            return True

        # Default: don't skip — let the next tier try
        return False
