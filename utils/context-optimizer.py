#!/usr/bin/env python3
"""
Context UX Manager - Monitor and optimize context usage for response speed.

Implements UX-driven context optimization:
- Monitor context size and composition
- Calculate health status (OPTIMAL/ACCEPTABLE/DEGRADED/CRITICAL)
- Estimate response latency based on context size
- Recommend fresh start when UX degrades
- Generate continuation prompts for session transfer
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import sys
from pathlib import Path


class ContextHealth(Enum):
    """Context health status from UX perspective."""
    OPTIMAL = "optimal"          # <30k tokens, <3s response
    ACCEPTABLE = "acceptable"    # 30-60k tokens, 3-7s response
    DEGRADED = "degraded"        # 60-80k tokens, 7-15s response
    CRITICAL = "critical"        # >80k tokens, >15s response


@dataclass
class ContextMetrics:
    """Metrics describing context health and composition."""
    total_tokens: int
    signal_tokens: int          # Relevant, recent context
    noise_tokens: int           # Old, irrelevant context
    response_latency_ms: int    # Estimated response time
    health_status: ContextHealth
    noise_ratio: float          # noise / total
    recommendation: str


class ContextOptimizer:
    """
    Analyze context composition and recommend UX optimizations.

    Focus: Response speed and user experience, not cost.
    Goal: Keep responses <5s throughout session.
    """

    # Context health thresholds (tokens)
    OPTIMAL_MAX = 30000       # <3s response time
    ACCEPTABLE_MAX = 60000    # <7s response time
    DEGRADED_MAX = 80000      # <15s response time
    CRITICAL = 80000          # >15s response, recommend restart

    # Latency estimates (milliseconds per 1000 tokens)
    # Based on Claude Code empirical measurements
    LATENCY_PER_1K = {
        "haiku": 50,    # ~50ms per 1k tokens
        "sonnet": 80,   # ~80ms per 1k tokens
        "opus": 120     # ~120ms per 1k tokens
    }

    # Baseline latency (network + processing)
    BASELINE_LATENCY_MS = {
        "haiku": 500,
        "sonnet": 800,
        "opus": 1200
    }

    def __init__(self, model: str = "sonnet"):
        """
        Initialize context optimizer.

        Args:
            model: Model being used (haiku, sonnet, opus)
        """
        self.model = model

    def estimate_response_latency(self, context_tokens: int) -> int:
        """
        Estimate response latency based on context size.

        Args:
            context_tokens: Current context size in tokens

        Returns:
            Estimated response time in milliseconds
        """
        baseline = self.BASELINE_LATENCY_MS[self.model]
        context_latency = (context_tokens / 1000) * self.LATENCY_PER_1K[self.model]
        return int(baseline + context_latency)

    def classify_health(self, context_tokens: int) -> ContextHealth:
        """
        Classify context health based on token count.

        Args:
            context_tokens: Current context size in tokens

        Returns:
            Health status (OPTIMAL/ACCEPTABLE/DEGRADED/CRITICAL)
        """
        if context_tokens <= self.OPTIMAL_MAX:
            return ContextHealth.OPTIMAL
        elif context_tokens <= self.ACCEPTABLE_MAX:
            return ContextHealth.ACCEPTABLE
        elif context_tokens <= self.DEGRADED_MAX:
            return ContextHealth.DEGRADED
        else:
            return ContextHealth.CRITICAL

    def estimate_signal_noise(
        self,
        total_tokens: int,
        conversation_turns: int,
        recent_turns: int = 5
    ) -> Tuple[int, int]:
        """
        Estimate signal (relevant) vs noise (irrelevant) tokens.

        Simple heuristic:
        - Signal: Recent conversation (last N turns) + system prompts
        - Noise: Old conversation history

        Args:
            total_tokens: Total context size
            conversation_turns: Total conversation turns
            recent_turns: How many recent turns to consider signal

        Returns:
            (signal_tokens, noise_tokens)
        """
        if conversation_turns == 0:
            return (total_tokens, 0)

        # Estimate system prompt size (CLAUDE.md, agent definitions)
        system_prompt_tokens = min(10000, total_tokens * 0.3)

        # Estimate tokens per turn
        avg_tokens_per_turn = (total_tokens - system_prompt_tokens) / conversation_turns

        # Recent turns are signal
        recent_conversation_tokens = min(
            avg_tokens_per_turn * recent_turns,
            total_tokens - system_prompt_tokens
        )

        signal_tokens = int(system_prompt_tokens + recent_conversation_tokens)
        noise_tokens = total_tokens - signal_tokens

        return (signal_tokens, noise_tokens)

    def analyze_context_health(
        self,
        current_tokens: int,
        conversation_turns: int = 0
    ) -> ContextMetrics:
        """
        Analyze context from UX perspective.

        Args:
            current_tokens: Current context size in tokens
            conversation_turns: Number of conversation turns (optional)

        Returns:
            ContextMetrics with health status and recommendations
        """
        # Calculate metrics
        health_status = self.classify_health(current_tokens)
        latency_ms = self.estimate_response_latency(current_tokens)

        signal_tokens, noise_tokens = self.estimate_signal_noise(
            current_tokens,
            conversation_turns
        )

        noise_ratio = noise_tokens / current_tokens if current_tokens > 0 else 0

        # Generate recommendation
        recommendation = self._generate_recommendation(
            health_status,
            noise_ratio,
            latency_ms
        )

        return ContextMetrics(
            total_tokens=current_tokens,
            signal_tokens=signal_tokens,
            noise_tokens=noise_tokens,
            response_latency_ms=latency_ms,
            health_status=health_status,
            noise_ratio=noise_ratio,
            recommendation=recommendation
        )

    def _generate_recommendation(
        self,
        health: ContextHealth,
        noise_ratio: float,
        latency_ms: int
    ) -> str:
        """Generate UX optimization recommendation."""

        if health == ContextHealth.OPTIMAL:
            return "Context optimal. No action needed."

        elif health == ContextHealth.ACCEPTABLE:
            if noise_ratio > 0.5:
                return (
                    "Context acceptable but growing. "
                    "Consider fresh start soon for best UX."
                )
            return "Context acceptable. Continue working."

        elif health == ContextHealth.DEGRADED:
            return (
                f"Context degraded (~{latency_ms/1000:.1f}s responses). "
                "Recommend starting fresh session for better UX."
            )

        else:  # CRITICAL
            return (
                f"Context critical (>{latency_ms/1000:.0f}s responses). "
                "Strongly recommend fresh start immediately."
            )

    def should_recommend_fresh_start(
        self,
        metrics: ContextMetrics,
        max_latency_ms: int = 10000
    ) -> bool:
        """
        Determine if fresh start should be recommended.

        Triggers:
        1. Context in CRITICAL state (>80k tokens)
        2. Noise ratio >60% (context bloat)
        3. Estimated latency >threshold (default 10s)

        Args:
            metrics: Context metrics from analyze_context_health()
            max_latency_ms: Maximum acceptable latency (default 10s)

        Returns:
            True if fresh start recommended
        """
        return (
            metrics.health_status == ContextHealth.CRITICAL
            or metrics.noise_ratio > 0.6
            or metrics.response_latency_ms > max_latency_ms
        )

    def generate_continuation_prompt(
        self,
        task_summary: str,
        active_files: List[str],
        decisions_made: List[str],
        next_steps: List[str],
        critical_context: Optional[str] = None
    ) -> str:
        """
        Generate continuation prompt for fresh session.

        Goal: <5% of current context size, preserve only essential info.

        Args:
            task_summary: 1-2 sentence description of current task
            active_files: Key files being worked on
            decisions_made: Critical decisions/choices made
            next_steps: Specific next steps
            critical_context: Any essential context to preserve

        Returns:
            Continuation prompt string
        """
        prompt_parts = []

        # Task summary (1-2 sentences)
        prompt_parts.append(f"Continue {task_summary}")

        # Active files (concise list)
        if active_files:
            files_list = ", ".join(active_files[:5])  # Max 5 files
            if len(active_files) > 5:
                files_list += f" (+{len(active_files) - 5} more)"
            prompt_parts.append(f"Files: {files_list}")

        # Decisions (bullet points)
        if decisions_made:
            decisions_text = "; ".join(decisions_made[:3])  # Max 3 decisions
            prompt_parts.append(f"Decisions: {decisions_text}")

        # Next steps (bullet points)
        if next_steps:
            steps_text = "; ".join(next_steps[:3])  # Max 3 steps
            prompt_parts.append(f"Next: {steps_text}")

        # Critical context (optional, brief)
        if critical_context:
            # Truncate to max 200 chars
            context_brief = critical_context[:200]
            if len(critical_context) > 200:
                context_brief += "..."
            prompt_parts.append(f"Context: {context_brief}")

        return ". ".join(prompt_parts) + "."

    def format_health_report(
        self,
        metrics: ContextMetrics,
        include_continuation: bool = True,
        continuation_prompt: Optional[str] = None
    ) -> str:
        """
        Format health metrics for user display.

        Args:
            metrics: Context metrics
            include_continuation: Whether to include continuation prompt
            continuation_prompt: Optional pre-generated continuation prompt

        Returns:
            Formatted health report string
        """
        # Status icon
        status_icons = {
            ContextHealth.OPTIMAL: "✓",
            ContextHealth.ACCEPTABLE: "⚠",
            ContextHealth.DEGRADED: "⚠️",
            ContextHealth.CRITICAL: "🚨"
        }

        icon = status_icons[metrics.health_status]
        status_name = metrics.health_status.value.upper()

        # Format latency
        latency_seconds = metrics.response_latency_ms / 1000

        # Build report
        lines = []
        lines.append(f"{icon} Context health: {status_name}")
        lines.append(f"   Tokens: {metrics.total_tokens:,} "
                    f"(signal: {metrics.signal_tokens:,}, noise: {metrics.noise_tokens:,})")
        lines.append(f"   Noise ratio: {metrics.noise_ratio * 100:.0f}%")
        lines.append(f"   Estimated latency: {latency_seconds:.1f}s")
        lines.append("")
        lines.append(f"   {metrics.recommendation}")

        # Add continuation prompt if recommended
        if include_continuation and self.should_recommend_fresh_start(metrics):
            lines.append("")
            lines.append("   💡 To start fresh session:")
            lines.append("      1. Copy continuation prompt below")
            lines.append("      2. Run: /clear")
            lines.append("      3. Paste prompt in new session")
            lines.append("")

            if continuation_prompt:
                lines.append("   Continuation prompt:")
                lines.append(f"   {continuation_prompt}")

        return "\n".join(lines)


# CLI interface
def main():
    """CLI interface for context optimization."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Context UX Manager - Analyze and optimize context usage"
    )
    parser.add_argument(
        "tokens",
        type=int,
        help="Current context size in tokens"
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=0,
        help="Number of conversation turns"
    )
    parser.add_argument(
        "--model",
        choices=["haiku", "sonnet", "opus"],
        default="sonnet",
        help="Model being used"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format"
    )
    parser.add_argument(
        "--continuation",
        action="store_true",
        help="Generate example continuation prompt"
    )

    args = parser.parse_args()

    # Create optimizer
    optimizer = ContextOptimizer(model=args.model)

    # Analyze context
    metrics = optimizer.analyze_context_health(
        current_tokens=args.tokens,
        conversation_turns=args.turns
    )

    # Generate continuation prompt if requested
    continuation_prompt = None
    if args.continuation and optimizer.should_recommend_fresh_start(metrics):
        continuation_prompt = optimizer.generate_continuation_prompt(
            task_summary="current work session",
            active_files=["example.py", "test.py"],
            decisions_made=["Used approach A instead of B"],
            next_steps=["Complete implementation", "Run tests"]
        )

    # Output format
    if args.json:
        # JSON output
        output = {
            "total_tokens": metrics.total_tokens,
            "signal_tokens": metrics.signal_tokens,
            "noise_tokens": metrics.noise_tokens,
            "noise_ratio": metrics.noise_ratio,
            "response_latency_ms": metrics.response_latency_ms,
            "health_status": metrics.health_status.value,
            "recommendation": metrics.recommendation,
            "should_restart": optimizer.should_recommend_fresh_start(metrics)
        }
        if continuation_prompt:
            output["continuation_prompt"] = continuation_prompt

        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print(optimizer.format_health_report(
            metrics,
            include_continuation=args.continuation,
            continuation_prompt=continuation_prompt
        ))


if __name__ == "__main__":
    main()
