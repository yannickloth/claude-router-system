"""
Context UX Manager - Optimize context for user experience.

Implements Solution 8 from architecture spec.
Monitors context health and recommends fresh starts when beneficial.

Usage:
    manager = ContextUXManager()
    analysis = manager.analyze_context(tokens_used=80000, turns=15, files=5)
    if analysis.health == ContextHealth.RECOMMEND_RESTART:
        print(analysis.recommendation)

Change Driver: UX_REQUIREMENTS
Changes when: User experience priorities or context thresholds change
"""

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ContextHealth(Enum):
    """Context health status levels."""

    HEALTHY = "healthy"  # < 70% capacity
    ATTENTION = "attention"  # 70-85% capacity
    RECOMMEND_RESTART = "recommend_restart"  # > 85% capacity


@dataclass
class ContextAnalysis:
    """Analysis of current context state."""

    health: ContextHealth
    tokens_used: int
    tokens_limit: int
    percent_used: float
    signal_to_noise: float  # Estimated useful content ratio (0-100)
    recommendation: str
    cost_analysis: Optional[Dict] = None


class ContextUXManager:
    """Monitor and optimize context for UX."""

    # Thresholds from architecture (adjusted for Claude Code's 100k compaction)
    # Claude Code compacts at ~100k tokens, so thresholds are relative to that
    ATTENTION_THRESHOLD = 0.70  # 70% of effective limit
    RECOMMEND_THRESHOLD = 0.85  # 85% of effective limit
    COMPACTION_LIMIT = 100000  # Claude Code compacts around here

    # Token display limit (what user sees)
    DISPLAY_LIMIT = 200000

    def __init__(self, token_limit: int = 200000):
        """
        Initialize context UX manager.

        Args:
            token_limit: Maximum token limit for display (default 200k)
        """
        self.token_limit = token_limit
        # Effective limit is where compaction happens
        self.effective_limit = min(self.COMPACTION_LIMIT, token_limit)

    def analyze_context(
        self,
        tokens_used: int,
        conversation_turns: int = 0,
        unique_files_referenced: int = 0,
    ) -> ContextAnalysis:
        """
        Analyze context health and provide recommendations.

        Args:
            tokens_used: Current token usage
            conversation_turns: Number of conversation turns (optional)
            unique_files_referenced: Number of unique files in context (optional)

        Returns:
            ContextAnalysis with health status and recommendations
        """
        # Calculate percentage relative to EFFECTIVE limit (compaction threshold)
        effective_percent = tokens_used / self.effective_limit
        display_percent = tokens_used / self.token_limit

        # Estimate signal-to-noise ratio
        # Higher file:turn ratio = more useful content
        if conversation_turns > 0 and unique_files_referenced > 0:
            # Files contribute signal, turns contribute noise
            file_signal = unique_files_referenced * 0.15
            turn_noise = conversation_turns * 0.05
            signal_to_noise = min(100.0, (file_signal / max(0.01, turn_noise)) * 100)
        else:
            signal_to_noise = 50.0  # Unknown, assume moderate

        # Determine health based on effective percentage
        if effective_percent < self.ATTENTION_THRESHOLD:
            health = ContextHealth.HEALTHY
            recommendation = "Context is healthy. Continue working."
        elif effective_percent < self.RECOMMEND_THRESHOLD:
            health = ContextHealth.ATTENTION
            recommendation = (
                f"Context at {display_percent*100:.0f}% (effective: {effective_percent*100:.0f}%). "
                "Consider summarizing completed work or using /clear with continuation prompt."
            )
        else:
            health = ContextHealth.RECOMMEND_RESTART
            recommendation = (
                f"Context at {display_percent*100:.0f}% (effective: {effective_percent*100:.0f}%). "
                "Fresh start recommended for better performance. "
                "Generate continuation prompt with generate_continuation_prompt(), "
                "then use /clear and paste the prompt."
            )

        # Calculate cost analysis
        cost_analysis = self.estimate_continuation_cost(tokens_used)

        return ContextAnalysis(
            health=health,
            tokens_used=tokens_used,
            tokens_limit=self.token_limit,
            percent_used=display_percent * 100,
            signal_to_noise=signal_to_noise,
            recommendation=recommendation,
            cost_analysis=cost_analysis,
        )

    def should_recommend_fresh_start(
        self,
        tokens_used: int,
        conversation_turns: int = 0,
    ) -> bool:
        """
        Quick check if fresh start should be recommended.

        Args:
            tokens_used: Current token usage
            conversation_turns: Number of conversation turns

        Returns:
            True if fresh start is recommended
        """
        effective_percent = tokens_used / self.effective_limit
        return effective_percent >= self.RECOMMEND_THRESHOLD

    def estimate_continuation_cost(
        self,
        current_tokens: int,
        continuation_prompt_tokens: int = 5000,
    ) -> Dict:
        """
        Estimate cost comparison: continue vs fresh start.

        Args:
            current_tokens: Current token count
            continuation_prompt_tokens: Estimated tokens for continuation prompt

        Returns:
            Dict with cost analysis and recommendation
        """
        # Estimate compaction cost (processing current tokens + summary generation)
        # This happens when continuing past the compaction threshold
        compaction_input_cost = current_tokens * 0.000015  # ~$15/1M tokens
        compaction_output_cost = 5000 * 0.000075  # Summary ~5k tokens at $75/1M
        compaction_total = compaction_input_cost + compaction_output_cost

        # Fresh start cost (cached system prompt + new continuation)
        # System prompt is cached at lower rate
        system_prompt_tokens = 10000  # Typical system prompt size
        cached_cost = system_prompt_tokens * 0.0000015  # Cached at 10% rate
        continuation_cost = continuation_prompt_tokens * 0.000015
        fresh_start_total = cached_cost + continuation_cost

        # Decision logic
        effective_percent = current_tokens / self.effective_limit

        if effective_percent > 0.70:
            # Above 70% effective, fresh start usually cheaper
            recommendation = "fresh_start"
            reason = "Fresh start more cost-effective at high context usage"
        elif effective_percent > 0.50:
            # 50-70%, compare costs
            if fresh_start_total < compaction_total * 0.7:
                recommendation = "fresh_start"
                reason = "Fresh start is significantly cheaper"
            else:
                recommendation = "continue"
                reason = "Continuing is more cost-effective"
        else:
            # Below 50%, continuing is usually better
            recommendation = "continue"
            reason = "Context is within efficient range"

        return {
            "continue_cost": round(compaction_total, 4),
            "fresh_start_cost": round(fresh_start_total, 4),
            "recommendation": recommendation,
            "reason": reason,
            "effective_percent": round(effective_percent * 100, 1),
        }

    def get_context_status_line(self, tokens_used: int) -> str:
        """
        Generate a status line for display at start of responses.

        Args:
            tokens_used: Current token usage

        Returns:
            Formatted status line string
        """
        percent = (tokens_used / self.token_limit) * 100
        effective_percent = (tokens_used / self.effective_limit) * 100

        if effective_percent < 50:
            status = "OK"
        elif effective_percent < 70:
            status = "ATTENTION"
        elif effective_percent < 85:
            status = "HIGH"
        else:
            status = "CRITICAL"

        return f"Context: {percent:.1f}% ({tokens_used:,} / {self.token_limit:,} tokens) [{status}]"

    def display_analysis(self, analysis: ContextAnalysis) -> None:
        """Display context analysis to console."""
        print("Context Health Analysis")
        print("=" * 50)
        print(f"Status: {analysis.health.value.upper()}")
        print(f"Tokens: {analysis.tokens_used:,} / {analysis.tokens_limit:,}")
        print(f"Usage: {analysis.percent_used:.1f}%")
        print(f"Signal-to-noise: {analysis.signal_to_noise:.0f}%")
        print()
        print(f"Recommendation: {analysis.recommendation}")

        if analysis.cost_analysis:
            print()
            print("Cost Analysis:")
            ca = analysis.cost_analysis
            print(f"  Continue cost: ${ca['continue_cost']:.4f}")
            print(f"  Fresh start cost: ${ca['fresh_start_cost']:.4f}")
            print(f"  Recommendation: {ca['recommendation']}")
            print(f"  Reason: {ca['reason']}")

        print("=" * 50)


def main():
    """CLI interface for context UX manager."""
    import argparse

    parser = argparse.ArgumentParser(description="Context UX Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze context health")
    analyze_parser.add_argument(
        "--tokens", type=int, required=True, help="Current token usage"
    )
    analyze_parser.add_argument(
        "--turns", type=int, default=0, help="Conversation turns"
    )
    analyze_parser.add_argument(
        "--files", type=int, default=0, help="Unique files referenced"
    )

    # status command
    status_parser = subparsers.add_parser("status", help="Get status line")
    status_parser.add_argument(
        "--tokens", type=int, required=True, help="Current token usage"
    )

    # cost command
    cost_parser = subparsers.add_parser("cost", help="Estimate costs")
    cost_parser.add_argument(
        "--tokens", type=int, required=True, help="Current token usage"
    )

    args = parser.parse_args()

    manager = ContextUXManager()

    if args.command == "analyze":
        analysis = manager.analyze_context(
            tokens_used=args.tokens,
            conversation_turns=args.turns,
            unique_files_referenced=args.files,
        )
        manager.display_analysis(analysis)
        # Exit with 1 if restart recommended
        sys.exit(0 if analysis.health != ContextHealth.RECOMMEND_RESTART else 1)

    elif args.command == "status":
        status = manager.get_context_status_line(args.tokens)
        print(status)

    elif args.command == "cost":
        cost = manager.estimate_continuation_cost(args.tokens)
        print(f"Continue cost: ${cost['continue_cost']:.4f}")
        print(f"Fresh start cost: ${cost['fresh_start_cost']:.4f}")
        print(f"Recommendation: {cost['recommendation']}")
        print(f"Reason: {cost['reason']}")

    else:
        parser.print_help()


def test_context_ux_manager() -> None:
    """Test context UX manager functionality."""
    print("Testing context UX manager...")

    manager = ContextUXManager()

    # Test 1: Healthy context
    print("Test 1: Healthy context (30k tokens)")
    analysis = manager.analyze_context(tokens_used=30000, conversation_turns=5, unique_files_referenced=3)
    assert analysis.health == ContextHealth.HEALTHY, f"Expected HEALTHY, got {analysis.health}"
    print("  OK")

    # Test 2: Attention context (75k tokens - 75% of 100k effective)
    print("Test 2: Attention context (75k tokens)")
    analysis = manager.analyze_context(tokens_used=75000, conversation_turns=20, unique_files_referenced=5)
    assert analysis.health == ContextHealth.ATTENTION, f"Expected ATTENTION, got {analysis.health}"
    print("  OK")

    # Test 3: Recommend restart (90k tokens - 90% of 100k effective)
    print("Test 3: Recommend restart (90k tokens)")
    analysis = manager.analyze_context(tokens_used=90000, conversation_turns=30, unique_files_referenced=8)
    assert analysis.health == ContextHealth.RECOMMEND_RESTART, f"Expected RECOMMEND_RESTART, got {analysis.health}"
    print("  OK")

    # Test 4: Cost estimation
    print("Test 4: Cost estimation")
    cost = manager.estimate_continuation_cost(80000)
    assert "recommendation" in cost
    assert "continue_cost" in cost
    assert "fresh_start_cost" in cost
    print("  OK")

    # Test 5: Status line
    print("Test 5: Status line generation")
    status = manager.get_context_status_line(50000)
    assert "Context:" in status
    assert "%" in status
    print("  OK")

    # Test 6: Should recommend fresh start
    print("Test 6: Should recommend fresh start")
    assert not manager.should_recommend_fresh_start(50000), "50k should not trigger"
    assert manager.should_recommend_fresh_start(90000), "90k should trigger"
    print("  OK")

    print("\nAll context UX manager tests passed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_context_ux_manager()
    else:
        main()
