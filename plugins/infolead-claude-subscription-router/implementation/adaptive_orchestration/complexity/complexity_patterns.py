"""
Complexity detection patterns.

Defines regex patterns and markers for classifying request complexity.
Separated from classifier logic to make patterns independently maintainable.

Change Driver: COMPLEXITY_PATTERNS
Changes when: Pattern definitions change (new patterns, pattern tuning)
"""

from typing import List, Tuple


# SIMPLE patterns: mechanical, explicit, single-target
SIMPLE_INDICATORS: List[Tuple[str, str]] = [
    (r"fix\s+(typo|spelling|syntax)", "mechanical_fix"),
    (r"format\s+(code|file)", "mechanical_format"),
    (r"lint\s+", "mechanical_lint"),
    (r"rename\s+\w+.*\s+to\s+\w+", "mechanical_rename"),  # More flexible: "rename variable foo to bar"
    (r"add\s+(semicolon|comma|bracket|import)", "mechanical_add"),
    (r"remove\s+(trailing\s+whitespace|unused)", "mechanical_remove"),
    (r"correct\s+(spelling|typo)", "mechanical_correct"),
    (r"sort\s+(imports|lines)", "mechanical_sort"),
    (r"show\s+", "read_only_show"),
    (r"display\s+", "read_only_display"),
    (r"list\s+", "read_only_list"),
    (r"get\s+", "read_only_get"),
    (r"read\s+", "read_only_read"),
]

# COMPLEX patterns: ambiguous, multi-step, requires judgment
COMPLEX_INDICATORS: List[Tuple[str, str]] = [
    (r"\b(design|architecture|implement)\b", "requires_design"),
    (r"\b(best|better|optimal|should I|which)\b", "requires_judgment"),
    (r"\b(trade-off|tradeoff|pros and cons|evaluate)\b", "requires_analysis"),  # Added "tradeoff" variant
    (r"\b(complex|nuanced|subtle|careful)\b", "explicit_complexity"),
    (r"\b(integrate|refactor|restructure)\b", "structural_change"),
    (r"\b(multiple|several|all|every)\b.*\b(file|module|component)\b", "multi_target"),
    (r"\b(plan|strategy|approach)\b", "requires_planning"),
    (r"\banalyze\b", "requires_analysis"),  # "Analyze" is inherently complex
]

# Multi-objective indicators (suggests coordination needed)
MULTI_OBJECTIVE_MARKERS: List[str] = [" and then ", ", then ", " after ", " before ", ";", "\n"]
