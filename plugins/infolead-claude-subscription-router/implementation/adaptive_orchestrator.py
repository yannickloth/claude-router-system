"""
Adaptive Orchestration - Intelligently select orchestration strategy based on request complexity.

This module implements adaptive orchestration that chooses between fast single-stage
routing and deliberate multi-stage planning based on request complexity classification.

MOTIVATION:
- Universal multi-stage orchestration (interpret → plan → execute) adds 56% cost and 40-60% latency
- Simple mechanical requests don't benefit from multi-stage planning
- Complex ambiguous requests need deliberate interpretation and planning
- Solution: Classify complexity first, then choose appropriate strategy

EXPECTED PERFORMANCE:
- 12% average latency increase (vs 150% for universal multi-stage)
- 12% average cost increase (vs 56% for universal multi-stage)
- 15% accuracy improvement on complex requests
- Maintained speed for simple requests

CLI Usage:
    # Orchestrate a request
    python3 adaptive_orchestrator.py "Fix typo in README.md"
    python3 adaptive_orchestrator.py "Design a caching architecture with fallback"

    # JSON output mode
    echo "Test request" | python3 adaptive_orchestrator.py --json

    # Run tests
    python3 adaptive_orchestrator.py --test

Change Driver: ORCHESTRATION_STRATEGY
Changes when: Orchestration strategies evolve, complexity classification improves

NOTE: This file is now a backward compatibility wrapper.
The refactored implementation is in adaptive_orchestration/ package.
All imports and CLI functionality are preserved for backward compatibility.
"""

import sys
from pathlib import Path

# Re-export all public APIs from the refactored package
from adaptive_orchestration import (
    # Main orchestrator
    AdaptiveOrchestrator,

    # Configuration
    OrchestratorConfig,
    load_config,

    # Complexity classification
    ComplexityClassifier,

    # Types
    ComplexityLevel,
    OrchestrationMode,
    ComplexityAnalysis,
    OrchestrationResult,
)

# Re-export configuration constants for backward compatibility
from adaptive_orchestration.config.config_detection import DEFAULT_CONFIG_PATH, detect_project_config

# Re-export CLI functions
from adaptive_orchestration.cli.orchestrator_cli import format_orchestration_output, run_cli

# Re-export MetricsCollector for test mocking compatibility
import sys
from pathlib import Path
IMPL_DIR = Path(__file__).parent
sys.path.insert(0, str(IMPL_DIR))
from metrics_collector import MetricsCollector


# Test runner - preserved for backward compatibility
def run_tests() -> None:
    """Run test cases for adaptive orchestration."""
    test_cases = [
        # SIMPLE requests
        ("Fix typo in README.md", ComplexityLevel.SIMPLE),
        ("Format code in src/main.py", ComplexityLevel.SIMPLE),
        ("Rename variable foo to bar in utils.py", ComplexityLevel.SIMPLE),
        ("Sort imports in app.py", ComplexityLevel.SIMPLE),
        ("Show me the contents of config.json", ComplexityLevel.SIMPLE),

        # COMPLEX requests
        ("Design a caching architecture with fallback strategies", ComplexityLevel.COMPLEX),
        ("Which is the best approach for implementing authentication?", ComplexityLevel.COMPLEX),
        ("Refactor the entire authentication system", ComplexityLevel.COMPLEX),
        ("Implement a new API endpoint and add tests and update documentation", ComplexityLevel.COMPLEX),
        ("Analyze the trade-offs between Redis and Memcached for our use case", ComplexityLevel.COMPLEX),

        # MODERATE requests
        ("Fix the bug in auth.py", ComplexityLevel.MODERATE),
        ("Add logging to the payment module", ComplexityLevel.MODERATE),
        ("Update the API documentation", ComplexityLevel.MODERATE),
        ("Run the test suite", ComplexityLevel.MODERATE),
    ]

    print("Running adaptive orchestration tests...\n")
    orchestrator = AdaptiveOrchestrator()

    passed = 0
    failed = 0

    for request, expected_complexity in test_cases:
        result = orchestrator.orchestrate(request)
        actual_complexity = result.complexity
        status = "✅" if actual_complexity == expected_complexity else "❌"

        if actual_complexity == expected_complexity:
            passed += 1
        else:
            failed += 1

        print(f"{status} {request}")
        print(f"   Expected: {expected_complexity.value}")
        print(f"   Actual: {actual_complexity.value}")
        print(f"   Mode: {result.mode.value}")
        print(f"   Confidence: {result.metadata.get('complexity_confidence', 0.0):.2f}")
        if result.metadata.get("complexity_indicators"):
            print(f"   Indicators: {', '.join(result.metadata['complexity_indicators'][:3])}")
        print()

    print(f"\n{'='*60}")
    print(f"Tests: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    # Check if running tests or CLI mode
    if "--test" in sys.argv:
        run_tests()
    else:
        run_cli()
