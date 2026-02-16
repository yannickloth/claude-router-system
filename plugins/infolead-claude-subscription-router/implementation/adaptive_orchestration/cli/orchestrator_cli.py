"""
CLI interface for adaptive orchestration.

Provides command-line interface for orchestration with:
- Direct request processing
- JSON output mode
- Human-readable formatting

Change Driver: CLI_INTERFACE
Changes when: CLI arguments, output formats, or user interaction change
"""

import json
import sys
from pathlib import Path

IMPL_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(IMPL_DIR))

from ..orchestration.adaptive_orchestrator import AdaptiveOrchestrator
from ..orchestration.types import OrchestrationResult
from routing_core import RouterDecision


def format_orchestration_output(result: OrchestrationResult) -> str:
    """
    Format orchestration result for human-readable output.

    Args:
        result: OrchestrationResult from orchestrate()

    Returns:
        Formatted string for display
    """
    output = []
    output.append("🎯 Adaptive Orchestration")
    output.append("═" * 60)

    # Complexity analysis
    output.append(f"Complexity: {result.complexity.value.upper()}")
    output.append(f"Confidence: {result.metadata.get('complexity_confidence', 0.0):.1%}")
    indicators = result.metadata.get("complexity_indicators", [])
    if indicators:
        output.append(f"Indicators: {', '.join(indicators)}")
    output.append("")

    # Orchestration mode
    output.append(f"Mode: {result.mode.value}")
    output.append(f"Stages: {' → '.join(result.metadata.get('stages', []))}")
    output.append("")

    # Routing result
    if result.routing_result:
        routing = result.routing_result
        if routing.decision == RouterDecision.ESCALATE_TO_SONNET:
            output.append(f"⚠️  ESCALATE to Sonnet Router")
            output.append(f"Reason: {routing.reason}")
        else:
            output.append(f"✅ ROUTE to Agent: {routing.agent}")
            output.append(f"Reason: {routing.reason}")
        output.append(f"Confidence: {routing.confidence:.1%}")
    output.append("")

    return "\n".join(output)


def run_cli() -> None:
    """CLI entry point for adaptive orchestration."""
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
        print("Usage: echo 'request' | orchestrator_cli.py [--json]", file=sys.stderr)
        sys.exit(1)

    # Perform orchestration
    orchestrator = AdaptiveOrchestrator()
    result = orchestrator.orchestrate(user_request)

    # Output result
    if output_json:
        output = {
            "mode": result.mode.value,
            "complexity": result.complexity.value,
            "routing": result.routing_result.to_dict() if result.routing_result else None,
            "metadata": result.metadata,
            "timestamp": result.timestamp,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_orchestration_output(result))


if __name__ == "__main__":
    run_cli()
