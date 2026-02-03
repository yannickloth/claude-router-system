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
import os
import subprocess
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


def get_model_tier_from_agent_file(agent_name: str, agents_dir: Optional[str] = None) -> str:
    """
    Extract model tier from agent definition file's YAML frontmatter.

    Args:
        agent_name: Name of the agent (e.g., "router-escalation")
        agents_dir: Directory containing agent .md files (defaults to ../agents relative to this file)

    Returns:
        Model tier string ("haiku", "sonnet", or "opus"), defaults to "sonnet"
    """
    import yaml
    from pathlib import Path

    if agents_dir is None:
        # Default to ../agents relative to this file
        agents_dir = Path(__file__).parent.parent / "agents"
    else:
        agents_dir = Path(agents_dir)

    agent_file = agents_dir / f"{agent_name}.md"

    if not agent_file.exists():
        # Fallback to substring matching for unknown agents
        agent_lower = agent_name.lower()
        if "haiku" in agent_lower:
            return "haiku"
        elif "opus" in agent_lower:
            return "opus"
        return "sonnet"

    try:
        content = agent_file.read_text()
        # Extract YAML frontmatter between --- markers
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                if frontmatter and "model" in frontmatter:
                    return frontmatter["model"]
    except Exception:
        pass

    return "sonnet"  # Default


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


def match_request_to_agents_llm(
    request: str,
    agent_descriptions: Optional[Dict[str, str]] = None
) -> Tuple[Optional[str], float]:
    """
    Match request to available agents using Claude Haiku for semantic understanding.

    Args:
        request: User's request string
        agent_descriptions: Optional dict mapping agent names to descriptions

    Returns:
        Tuple of (agent_name, confidence_score) or (None, 0.0) if no match
    """
    if agent_descriptions is None:
        agent_descriptions = {
            "haiku-general": "Simple mechanical tasks: fix typos, correct spelling, format code, lint files, rename variables. Tasks with explicit file paths that require no judgment.",
            "sonnet-general": "Tasks requiring reasoning: analyze code, design features, implement functionality, refactor, review, optimize. Default for tasks needing judgment.",
            "opus-general": "Complex reasoning: mathematical proofs, formal verification, architecture decisions, algorithm design. High-stakes decisions requiring deep analysis.",
        }

    # Build the prompt
    agents_list = "\n".join(f"- {name}: {desc}" for name, desc in agent_descriptions.items())
    prompt = f"""Given this user request, which agent should handle it?

Request: {request}

Available agents:
{agents_list}

Respond with ONLY a JSON object (no markdown, no explanation):
{{"agent": "<agent-name or null>", "confidence": <0.0-1.0>}}

If the request is ambiguous or requires judgment to route, return null with low confidence."""

    try:
        # Call claude CLI with haiku model
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "haiku", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "CLAUDE_NO_HOOKS": "1"}  # Prevent hook recursion
        )

        if result.returncode != 0:
            # Fallback to keyword matching on error
            return match_request_to_agents_keywords(request)

        # Parse the response - claude --output-format json returns {"result": "..."}
        response = json.loads(result.stdout)
        content = response.get("result", "")

        # Extract JSON from the response (handle possible markdown wrapping)
        if "```" in content:
            # Extract from code block
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

        parsed = json.loads(content)
        agent = parsed.get("agent")
        confidence = float(parsed.get("confidence", 0.0))

        # Validate agent name
        if agent and agent not in agent_descriptions:
            return None, 0.0

        return agent, confidence

    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, Exception) as e:
        # Fallback to keyword matching on any error
        print(f"LLM routing failed ({type(e).__name__}), falling back to keywords", file=sys.stderr)
        return match_request_to_agents_keywords(request)


def match_request_to_agents_keywords(
    request: str,
    agent_registry: Optional[Dict[str, List[str]]] = None
) -> Tuple[Optional[str], float]:
    """
    Fallback: Match request to agents using keyword matching.

    Uses a tiered approach:
    1. Check for HIGH-confidence haiku patterns (mechanical, explicit file)
    2. Check for sonnet patterns (reasoning required)
    3. Check for opus patterns (complex reasoning)

    Args:
        request: User's request string
        agent_registry: Optional agent keyword mappings

    Returns:
        Tuple of (agent_name, confidence_score) or (None, 0.0) if no match
    """
    request_lower = request.lower()

    # HIGH-CONFIDENCE HAIKU PATTERNS
    # These are mechanical tasks that Haiku excels at
    haiku_high_confidence_patterns = [
        (r"fix\s+(typo|spelling|syntax)", 0.95),
        (r"format\s+(code|file)", 0.95),
        (r"lint\s+", 0.95),
        (r"rename\s+\w+\s+\w*\s*to\s+\w+", 0.95),  # "rename foo to bar" or "rename variable foo to bar"
        (r"add\s+(semicolon|comma|bracket|import)", 0.90),
        (r"remove\s+(trailing\s+whitespace|unused)", 0.90),
        (r"correct\s+(spelling|typo)", 0.95),
        (r"sort\s+(imports|lines)", 0.90),
    ]

    for pattern, confidence in haiku_high_confidence_patterns:
        if re.search(pattern, request_lower):
            # Also require explicit file path for file operations
            if explicit_file_mentioned(request):
                return "haiku-general", confidence

    # HAIKU KEYWORDS (require explicit file path)
    haiku_keywords = ["fix", "typo", "syntax", "format", "lint", "rename", "correct", "spelling"]
    haiku_matches = sum(1 for kw in haiku_keywords if kw in request_lower)

    if haiku_matches > 0 and explicit_file_mentioned(request):
        # Has haiku keywords AND explicit file path
        confidence = min(0.9, 0.6 + (haiku_matches * 0.1))
        return "haiku-general", confidence

    # SONNET PATTERNS (reasoning required)
    sonnet_keywords = ["analyze", "implement", "refactor", "integrate", "review", "optimize", "debug", "investigate"]
    sonnet_matches = sum(1 for kw in sonnet_keywords if kw in request_lower)

    if sonnet_matches > 0:
        confidence = min(0.9, 0.5 + (sonnet_matches * 0.15))
        return "sonnet-general", confidence

    # OPUS PATTERNS (complex reasoning)
    opus_keywords = ["prove", "formalize", "verify correctness", "mathematical", "theorem", "algorithm design"]
    opus_matches = sum(1 for kw in opus_keywords if kw in request_lower)

    if opus_matches > 0:
        confidence = min(0.95, 0.7 + (opus_matches * 0.1))
        return "opus-general", confidence

    # Default: check if has explicit file for haiku, else sonnet
    if explicit_file_mentioned(request):
        # Simple operation with explicit file -> haiku
        return "haiku-general", 0.6
    else:
        # No clear match
        return None, 0.0


# Use environment variable to control which matching strategy to use
USE_LLM_ROUTING = os.environ.get("ROUTER_USE_LLM", "0") == "1"


def match_request_to_agents(
    request: str,
    agent_registry: Optional[Dict[str, List[str]]] = None
) -> Tuple[Optional[str], float]:
    """
    Match request to available agents.

    Uses LLM-based semantic matching if ROUTER_USE_LLM=1, otherwise falls back
    to keyword matching.

    Args:
        request: User's request string
        agent_registry: Optional agent keyword mappings (for keyword fallback)

    Returns:
        Tuple of (agent_name, confidence_score) or (None, 0.0) if no match
    """
    if USE_LLM_ROUTING:
        return match_request_to_agents_llm(request)
    else:
        return match_request_to_agents_keywords(request, agent_registry)


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

    # Pattern 7: Agent matching (LLM or keyword-based)
    matched_agent, confidence = match_request_to_agents(request)

    if matched_agent is None:
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=None,
            reason="No clear agent match - needs intelligent routing",
            confidence=1.0
        )

    # Trust LLM confidence when using LLM routing (threshold 0.7)
    # For keyword fallback, require higher confidence (0.8)
    confidence_threshold = 0.7 if USE_LLM_ROUTING else 0.8

    if confidence < confidence_threshold:
        return RoutingResult(
            decision=RouterDecision.ESCALATE_TO_SONNET,
            agent=matched_agent,
            reason=f"Low confidence match ({confidence:.2f}) - needs verification",
            confidence=confidence
        )

    # High confidence match - route directly
    return RoutingResult(
        decision=RouterDecision.DIRECT_TO_AGENT,
        agent=matched_agent,
        reason="High-confidence agent match",
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


def route_request(
    request: str,
    context: Optional[Dict] = None,
    agent_registry: Optional[Dict[str, List[str]]] = None
) -> RoutingResult:
    """
    Route a user request to the appropriate agent.

    This is the main entry point for the routing system. It analyzes the request
    and returns a routing decision with the selected agent.

    Args:
        request: User's request string
        context: Optional context dict with project state, files, etc.
        agent_registry: Optional custom agent keyword mappings

    Returns:
        RoutingResult with decision, agent, reason, and confidence
    """
    return should_escalate(request, context)


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
        ("Fix the bug in auth.py", True),  # "bug" implies debugging which needs reasoning
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
