"""
Probabilistic Router CLI - Command-line interface for probabilistic routing.

Provides CLI commands for routing, validation, and statistics.

Commands:
    route REQUEST    - Route a request and show decision
    stats           - Show routing statistics
    validate FILE   - Validate a file's syntax

Usage:
    python3 probabilistic_router_cli.py route "Fix syntax error in main.py"
    python3 probabilistic_router_cli.py stats
    python3 probabilistic_router_cli.py validate test.py

Change Driver: CLI_INTERFACE
Changes when: CLI commands or output format changes
"""

import argparse
import sys
from pathlib import Path

# Add implementation directory to path for imports
IMPL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(IMPL_DIR))

from routing import ProbabilisticRouter, ResultValidator


def run_cli():
    """CLI interface for probabilistic router."""
    parser = argparse.ArgumentParser(description="Probabilistic Router CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # route command
    route_parser = subparsers.add_parser("route", help="Route a request")
    route_parser.add_argument("request", help="Request to route")

    # stats command
    subparsers.add_parser("stats", help="Show routing statistics")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a file")
    validate_parser.add_argument("file", help="File to validate")

    args = parser.parse_args()

    router = ProbabilisticRouter()

    if args.command == "route":
        decision = router.route_with_confidence(args.request)
        print(f"Model: {decision.recommended_model}")
        print(f"Confidence: {decision.confidence.value}")
        print(f"Fallback chain: {' → '.join(decision.fallback_chain) or 'None'}")
        print(f"Validation: {', '.join(decision.validation_criteria) or 'None'}")
        print(f"Reasoning: {decision.reasoning}")

    elif args.command == "stats":
        stats = router.get_statistics()
        print("Routing Statistics")
        print("=" * 40)
        for model, task_types in stats.items():
            print(f"\n{model.capitalize()}:")
            if not task_types:
                print("  No history")
            for task_type, data in task_types.items():
                print(f"  {task_type}: {data['successes']}/{data['attempts']} "
                      f"({data['success_rate']:.0%})")

    elif args.command == "validate":
        validator = ResultValidator()
        criteria = ["syntax_valid"]
        is_valid, reason = validator.validate_result(
            args.file,
            criteria,
            {}
        )
        if is_valid:
            print(f"Valid: {args.file}")
        else:
            print(f"Invalid: {reason}")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    run_cli()
