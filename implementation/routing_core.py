"""
Routing Core - Production-ready implementation of Haiku pre-routing and escalation logic.

This module implements the two-tier routing architecture with mechanical escalation
triggers that Haiku can reliably execute.

CLI Usage:
    # From stdin
    echo "Find files matching *.py" | python3 routing_core.py

    # From arguments
    python3 routing_core.py "Design a new architecture"

    # JSON output mode
    echo "Test request" | python3 routing_core.py --json
"""

from typing import Dict, Optional, Tuple, List
import re
import sys
import json
from dataclasses import dataclass, asdict
from enum import Enum


class RouterDecision(Enum):
    """Routing decision outcomes."""
    DIRECT_TO_AGENT = "direct"
    ESCALATE_TO_SONNET = "escalate"


@dataclass
class RoutingResult:
    """Result of a routing decision."""
    decision: RouterDecision
    agent: Optional[str]
    reason: str
    confidence: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "decision": self.decision.value,
            "agent": self.agent,
            "reason": self.reason,
            "confidence": self.confidence,
        }


def explicit_file_mentioned(request: str) -> bool:
    """
    Check if request contains explicit file paths or filenames.

    Args:
        request: User's request string

    Returns:
        True if explicit files/paths mentioned, False otherwise
    """
    # Look for patterns like: file.ext, path/to/file, ./file, etc.
    file_patterns = [
        r'\b\w+\.\w{2,4}\b',   # filename.ext (2-4 char extension)
        r'[\./][\w/.-]+',       # path/to/file or ./file
        r'\w+/\w+',             # dir/file
        r'~[\w/.-]+',           # ~/path/file
    ]
    return any(re.search(pattern, request) for pattern in file_patterns)


def match_request_to_agents(
    request: str,
    agent_registry: Optional[Dict[str, List[str]]] = None
) -> Tuple[Optional[str], float]:
    """
    Match request to available agents using keyword matching.

    In production, this would:
    1. Load agent registry from .claude/agents/
    2. Use semantic similarity (embeddings) for better matching
    3. Consider agent capabilities and current availability

    Args:
        request: User's request string
        agent_registry: Optional agent keyword mappings (for testing)

    Returns:
        Tuple of (agent_name, confidence_score) or (None, 0.0) if no match
    """
    # Default agent keywords (production would load from registry)
    if agent_registry is None:
        agent_registry = {
            "haiku-general": [
                "fix", "typo", "syntax", "simple", "quick",
                "rename", "format", "lint"
            ],
            "sonnet-general": [
                "analyze", "design", "implement", "refactor",
                "integrate", "review", "optimize"
            ],
            "opus-general": [
                "complex", "formalize", "prove", "verify",
                "architecture", "algorithm", "mathematical"
            ],
        }

    request_lower = request.lower()
    best_match = None
    best_confidence = 0.0

    for agent, keywords in agent_registry.items():
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in request_lower)
        confidence = matches / len(keywords) if keywords else 0.0

        if confidence > best_confidence:
            best_match = agent
            best_confidence = confidence

    return best_match, best_confidence


def should_escalate(request: str, context: Optional[Dict] = None) -> RoutingResult:
    """
    Mechanical escalation checklist that Haiku can reliably execute.

    This implements a rule-based system for determining when to escalate
    from Haiku pre-routing to Sonnet routing. All checks are mechanical
    (pattern matching, keyword detection) - no judgment required.

    Args:
        request: User's request string
        context: Optional context dict with project state, files, etc.

    Returns:
        RoutingResult with decision, agent, reason, and confidence
    """
    context = context or {}
    request_lower = request.lower()

    # Check for explicit file paths (used by multiple patterns)
    has_explicit_path = "/" in request or explicit_file_mentioned(request)

    # Pattern 1: Explicit complexity signals
    complexity_keywords = [
        "complex", "subtle", "nuanced", "judgment",
        "trade-off", "best approach", "design", "architecture",
        "should I", "which is better", "recommend", "decide"
    ]
    if any(kw in request_lower for kw in complexity_keywords):
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=None,
            reason="Request contains complexity signal keywords",
            confidence=1.0
        )

    # Pattern 2: Multi-file destructive operations
    is_destructive = any(op in request_lower for op in ["delete", "remove", "drop"])
    is_bulk = any(q in request_lower for q in ["all", "multiple", "*", "every"])
    if is_destructive and is_bulk:
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=None,
            reason="Bulk destructive operation requires judgment",
            confidence=1.0
        )

    # Pattern 3: Ambiguous targets (file operations without explicit paths)
    file_operations = ["edit", "modify", "change", "update", "delete", "remove"]
    has_file_operation = any(op in request_lower for op in file_operations)

    if has_file_operation and not has_explicit_path:
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=None,
            reason="File operation without explicit path - needs file discovery",
            confidence=0.9
        )

    # Pattern 4: Agent definition modifications (system integrity)
    if ".claude/agents" in request and any(op in request_lower for op in ["edit", "modify", "update"]):
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=None,
            reason="Agent definition changes require careful judgment",
            confidence=1.0
        )

    # Pattern 5: Multiple objectives (coordination needed)
    objective_indicators = [" and ", ", then ", " after ", " before ", ";"]
    objective_count = sum(request_lower.count(ind) for ind in objective_indicators)

    if objective_count >= 2:
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=None,
            reason=f"Multiple objectives ({objective_count}) require coordination",
            confidence=0.9
        )

    # Pattern 6: New/unfamiliar project areas (creation requires design)
    creation_keywords = ["new", "create", "design", "build", "implement"]
    if any(kw in request_lower for kw in creation_keywords):
        # Exception: simple file creation with explicit name is okay
        if "new file" in request_lower and explicit_file_mentioned(request):
            pass  # Continue to next checks
        else:
            return RoutingResult(
                decision=RouterDecision.ESCALATE_TO_SONNET,
                agent=None,
                reason="Creation/design tasks require planning and judgment",
                confidence=0.85
            )

    # Pattern 7: Unknown or low-confidence agent match
    matched_agent, confidence = match_request_to_agents(request)

    if matched_agent is None:
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=None,
            reason="No clear agent match - needs intelligent routing",
            confidence=1.0
        )

    # For simple file operations with explicit paths, use lower confidence threshold
    # These are mechanical operations that don't require judgment
    simple_operations = ["fix", "typo", "format", "rename", "correct", "update"]
    is_simple_file_op = (
        has_explicit_path and
        any(op in request_lower for op in simple_operations)
    )

    if is_simple_file_op:
        # Simple file operations can go directly to haiku-general regardless of confidence
        return RoutingResult(
            decision=RouterDecision.DIRECT_TO_AGENT,
            agent="haiku-general",
            reason="Simple file operation with explicit path - mechanical task",
            confidence=0.95  # High confidence for mechanical operations
        )

    # For other requests, require high confidence (80%)
    if confidence < 0.8:
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=matched_agent,
            reason=f"Low confidence match ({confidence:.2f}) - needs verification",
            confidence=confidence
        )

    # All checks passed - safe for Haiku to route directly
    return RoutingResult(
        decision=RouterDecision.DIRECT_TO_AGENT,
        agent=matched_agent,
        reason="Clear, mechanical request with high-confidence agent match",
        confidence=confidence
    )


def format_routing_output(result: RoutingResult, user_request: str) -> str:
    """
    Format routing result for human-readable output

    Args:
        result: RoutingResult from should_escalate()
        user_request: Original user request

    Returns:
        Formatted string for display
    """
    output = []
    output.append("🎯 Routing Analysis")
    output.append("═" * 50)
    output.append(f"Request: {user_request}")
    output.append("")

    if result.decision == RouterDecision.ESCALATE_TO_SONNET:
        output.append("⚠️  ESCALATE to Sonnet Router")
        output.append(f"Reason: {result.reason}")
        if result.agent:
            output.append(f"Suggested agent: {result.agent}")
    else:
        output.append(f"✅ DIRECT to Agent: {result.agent}")
        output.append(f"Reason: {result.reason}")

    output.append(f"Confidence: {result.confidence:.1%}")
    output.append("")

    return "\n".join(output)


def run_cli() -> None:
    """CLI entry point for routing analysis"""
    # Parse arguments
    args = sys.argv[1:]
    output_json = "--json" in args

    # Remove flags from args
    args = [arg for arg in args if not arg.startswith("--")]

    # Get user request from stdin or args
    if args:
        user_request = " ".join(args)
    else:
        user_request = sys.stdin.read().strip()

    if not user_request:
        print("Error: No request provided", file=sys.stderr)
        print("Usage: echo 'request' | routing_core.py [--json]", file=sys.stderr)
        sys.exit(1)

    # Perform routing analysis
    result = should_escalate(user_request)

    # Output result
    if output_json:
        output = {
            "request": user_request,
            "routing": result.to_dict(),
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_routing_output(result, user_request))


def run_tests() -> None:
    """Run test cases for routing logic"""
    test_cases = [
        # Should escalate
        ("Which approach is best for implementing authentication?", True),
        ("Delete all temporary files", True),
        ("Fix the bug in auth.py", False),  # Has explicit file
        ("Modify the agent definitions", True),
        ("Create a new API endpoint and add tests", True),  # Multiple objectives
        ("Design a caching system", True),
        # Should not escalate
        ("Fix typo in README.md", False),
        ("Format code in src/main.py", False),
        ("Rename variable foo to bar in utils.py", False),
    ]

    print("Running routing tests...\n")
    passed = 0
    failed = 0

    for request, should_escalate_expected in test_cases:
        result = should_escalate(request)
        escalated = result.decision == RouterDecision.ESCALATE_TO_SONNET
        status = "✅" if escalated == should_escalate_expected else "❌"

        if escalated == should_escalate_expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} {request}")
        print(f"   Decision: {result.decision.value}")
        print(f"   Reason: {result.reason}")
        print(f"   Agent: {result.agent}")
        print(f"   Confidence: {result.confidence:.2f}")
        print()

    print(f"\n{'='*50}")
    print(f"Tests: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    # Check if running tests or CLI mode
    if "--test" in sys.argv:
        run_tests()
    else:
        run_cli()
