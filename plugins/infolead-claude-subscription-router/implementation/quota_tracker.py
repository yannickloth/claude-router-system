"""
Quota Tracker - Track and enforce API quota usage across sessions.

Implements FR-6.1 (Quota Tracking) and FR-6.2 (Quota Limit Enforcement)
from routing-system-requirements.md.

State file: ~/.claude/infolead-claude-subscription-router/state/quota-tracking.json

Usage:
    tracker = QuotaTracker()
    if tracker.can_use_model("sonnet"):
        tracker.increment_usage("sonnet")
        # ... use model ...

    scheduler = QuotaAwareScheduler()
    model = scheduler.select_model_for_task(complexity=3)

Change Driver: QUOTA_MANAGEMENT
Changes when: Subscription tiers or pricing change
"""

import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, date, UTC
from pathlib import Path
from typing import Dict, Optional

from file_locking import locked_state_file

# State directory
STATE_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "state"
QUOTA_FILE = STATE_DIR / "quota-tracking.json"

# Subscription tier limits (Max 5x tier - adjustable)
QUOTA_LIMITS = {
    "haiku": float("inf"),
    "sonnet": 1125,
    "opus": 250,
}

# Buffer reserves (don't exceed these to leave room for urgent work)
RESERVE_BUFFER = {
    "haiku": 0.0,
    "sonnet": 0.1,  # 10% reserve
    "opus": 0.2,  # 20% reserve
}


@dataclass
class QuotaState:
    """Daily quota state."""

    date: str  # YYYY-MM-DD
    used: Dict[str, int]  # model -> messages used
    last_updated: str


class QuotaTracker:
    """Track and enforce API quota limits."""

    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize quota tracker.

        Args:
            state_file: Path to state file (default: ~/.claude/infolead-claude-subscription-router/state/quota-tracking.json)
        """
        self.state_file = state_file or QUOTA_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._ensure_state_file()

    def _ensure_state_file(self) -> None:
        """Create state file if it doesn't exist."""
        if not self.state_file.exists():
            initial_state = QuotaState(
                date=date.today().isoformat(),
                used={"haiku": 0, "sonnet": 0, "opus": 0},
                last_updated=datetime.now(UTC).isoformat(),
            )
            with open(self.state_file, "w") as f:
                json.dump(asdict(initial_state), f, indent=2)
            os.chmod(self.state_file, 0o600)

    def _load_state(self) -> QuotaState:
        """Load quota state, reset if new day."""
        with locked_state_file(self.state_file, "r") as f:
            data = json.load(f)

        state = QuotaState(**data)

        # Reset if new day
        today = date.today().isoformat()
        if state.date != today:
            state = QuotaState(
                date=today,
                used={"haiku": 0, "sonnet": 0, "opus": 0},
                last_updated=datetime.now(UTC).isoformat(),
            )
            self._save_state(state)

        return state

    def _save_state(self, state: QuotaState) -> None:
        """Save quota state atomically with lock."""
        with locked_state_file(self.state_file, "r+", create_if_missing=True) as f:
            f.seek(0)
            f.truncate()
            json.dump(asdict(state), f, indent=2)

    def can_use_model(self, model: str) -> bool:
        """
        Check if quota is available for model.

        Args:
            model: Model name ("haiku", "sonnet", "opus")

        Returns:
            True if quota available (respecting reserve buffer)
        """
        if model not in QUOTA_LIMITS:
            return False

        if QUOTA_LIMITS[model] == float("inf"):
            return True

        state = self._load_state()
        used = state.used.get(model, 0)
        limit = QUOTA_LIMITS[model]
        buffer = RESERVE_BUFFER.get(model, 0)

        # Available quota = limit * (1 - buffer)
        available = limit * (1 - buffer)
        return used < available

    def increment_usage(self, model: str, count: int = 1) -> int:
        """
        Increment quota usage atomically.

        Args:
            model: Model name
            count: Number of messages to add

        Returns:
            New total usage for the model
        """
        with locked_state_file(self.state_file, "r+") as f:
            data = json.load(f)
            state = QuotaState(**data)

            # Reset if new day
            today = date.today().isoformat()
            if state.date != today:
                state = QuotaState(
                    date=today,
                    used={"haiku": 0, "sonnet": 0, "opus": 0},
                    last_updated=datetime.now(UTC).isoformat(),
                )

            # Increment
            state.used[model] = state.used.get(model, 0) + count
            state.last_updated = datetime.now(UTC).isoformat()

            # Write back
            f.seek(0)
            f.truncate()
            json.dump(asdict(state), f, indent=2)

            return state.used[model]

    def get_usage_summary(self) -> Dict:
        """
        Get current quota usage summary.

        Returns:
            Dict with usage stats for each model
        """
        state = self._load_state()

        summary = {}
        for model in ["haiku", "sonnet", "opus"]:
            used = state.used.get(model, 0)
            limit = QUOTA_LIMITS[model]

            if limit == float("inf"):
                summary[model] = {
                    "used": used,
                    "limit": "unlimited",
                    "remaining": "unlimited",
                    "percent": 0,
                }
            else:
                remaining = max(0, limit - used)
                percent = (used / limit) * 100 if limit > 0 else 0
                buffer_limit = int(limit * (1 - RESERVE_BUFFER.get(model, 0)))
                summary[model] = {
                    "used": used,
                    "limit": int(limit),
                    "effective_limit": buffer_limit,
                    "remaining": remaining,
                    "percent": round(percent, 1),
                }

        summary["date"] = state.date
        summary["last_updated"] = state.last_updated
        return summary

    def display_status(self) -> None:
        """Display quota status to console."""
        summary = self.get_usage_summary()

        print("Quota Status")
        print("=" * 50)
        print(f"Date: {summary['date']}")
        print()

        for model in ["haiku", "sonnet", "opus"]:
            data = summary[model]
            if data["limit"] == "unlimited":
                print(f"  {model.capitalize()}: {data['used']} used (unlimited)")
            else:
                status = (
                    "OK"
                    if data["percent"] < 80
                    else ("WARNING" if data["percent"] < 95 else "CRITICAL")
                )
                effective = data.get("effective_limit", data["limit"])
                print(
                    f"  {model.capitalize()}: {data['used']}/{data['limit']} "
                    f"({data['percent']}%) [{status}]"
                )
                print(f"    Effective limit (with buffer): {effective}")

        print("=" * 50)


class QuotaAwareScheduler:
    """
    Select model based on task complexity and available quota.

    Implements quota-aware model selection for optimal cost/capability balance.
    """

    def __init__(self, quota_tracker: Optional[QuotaTracker] = None):
        """
        Initialize scheduler.

        Args:
            quota_tracker: QuotaTracker instance (creates new one if not provided)
        """
        self.tracker = quota_tracker or QuotaTracker()

    def select_model_for_task(self, estimated_complexity: int) -> str:
        """
        Select most cost-effective model with available quota.

        Complexity scale:
        - 1-2: Trivial/mechanical tasks (Haiku capable)
        - 3: Moderate reasoning (Sonnet minimum)
        - 4: Complex reasoning (Sonnet preferred, Opus for quality)
        - 5: Deep analysis/proofs (Opus preferred)

        Args:
            estimated_complexity: 1-5 scale

        Returns:
            Model name: "haiku", "sonnet", "opus", or "queue_for_tomorrow"
        """
        # Clamp complexity to valid range
        complexity = max(1, min(5, estimated_complexity))

        # Determine minimum required capability
        if complexity <= 2:
            # Haiku capable
            if self.tracker.can_use_model("haiku"):
                return "haiku"
            # Shouldn't happen (unlimited), but fall through

        if complexity <= 4:
            # Sonnet is sufficient
            if self.tracker.can_use_model("sonnet"):
                return "sonnet"
            # Try Haiku as fallback for 3
            if complexity == 3 and self.tracker.can_use_model("haiku"):
                return "haiku"

        # Complexity 5 or fallback from 4
        if self.tracker.can_use_model("opus"):
            return "opus"

        # Opus exhausted, try Sonnet
        if self.tracker.can_use_model("sonnet"):
            return "sonnet"

        # All non-haiku quota exhausted
        if self.tracker.can_use_model("haiku"):
            return "haiku"

        # All quotas exhausted
        return "queue_for_tomorrow"

    def get_recommendation(self, estimated_complexity: int) -> Dict:
        """
        Get model recommendation with reasoning.

        Args:
            estimated_complexity: 1-5 scale

        Returns:
            Dict with model selection and reasoning
        """
        model = self.select_model_for_task(estimated_complexity)
        summary = self.tracker.get_usage_summary()

        reasoning = []
        if model == "haiku":
            if estimated_complexity <= 2:
                reasoning.append("Task is mechanical, Haiku sufficient")
            else:
                reasoning.append("Higher-tier quotas exhausted, using Haiku")

        elif model == "sonnet":
            if estimated_complexity <= 4:
                reasoning.append("Task requires reasoning, Sonnet appropriate")
            else:
                reasoning.append("Opus quota exhausted, using Sonnet")

        elif model == "opus":
            reasoning.append("Task requires deep analysis, using Opus")

        elif model == "queue_for_tomorrow":
            reasoning.append("All quotas exhausted for today")
            reasoning.append("Queue task for overnight execution or tomorrow")

        return {
            "model": model,
            "complexity": estimated_complexity,
            "reasoning": reasoning,
            "quota_status": {
                "sonnet_remaining": summary["sonnet"]["remaining"],
                "opus_remaining": summary["opus"]["remaining"],
            },
        }


def main():
    """CLI interface for quota tracker."""
    import argparse

    parser = argparse.ArgumentParser(description="Quota Tracker CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status command
    subparsers.add_parser("status", help="Show quota status")

    # increment command
    inc_parser = subparsers.add_parser("increment", help="Increment quota usage")
    inc_parser.add_argument("model", choices=["haiku", "sonnet", "opus"])
    inc_parser.add_argument("--count", type=int, default=1, help="Number of messages")

    # can-use command
    can_parser = subparsers.add_parser("can-use", help="Check if model can be used")
    can_parser.add_argument("model", choices=["haiku", "sonnet", "opus"])

    # recommend command
    rec_parser = subparsers.add_parser("recommend", help="Get model recommendation")
    rec_parser.add_argument("complexity", type=int, help="Task complexity (1-5)")

    args = parser.parse_args()

    tracker = QuotaTracker()

    if args.command == "status" or args.command is None:
        tracker.display_status()

    elif args.command == "increment":
        new_total = tracker.increment_usage(args.model, args.count)
        print(f"Incremented {args.model} by {args.count}. New total: {new_total}")

    elif args.command == "can-use":
        can_use = tracker.can_use_model(args.model)
        print(f"Can use {args.model}: {can_use}")
        sys.exit(0 if can_use else 1)

    elif args.command == "recommend":
        scheduler = QuotaAwareScheduler(tracker)
        rec = scheduler.get_recommendation(args.complexity)
        print(f"Recommended model: {rec['model']}")
        print(f"Complexity: {rec['complexity']}")
        print(f"Reasoning:")
        for r in rec["reasoning"]:
            print(f"  - {r}")
        print(f"Quota status:")
        print(f"  Sonnet remaining: {rec['quota_status']['sonnet_remaining']}")
        print(f"  Opus remaining: {rec['quota_status']['opus_remaining']}")


def test_quota_tracker() -> None:
    """Test quota tracker functionality."""
    import tempfile

    print("Testing quota tracker...")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test-quota.json"

        # Test 1: Initialization
        print("Test 1: Initialization")
        tracker = QuotaTracker(state_file=test_file)
        assert test_file.exists(), "State file should be created"
        print("  OK")

        # Test 2: Can use models
        print("Test 2: Model availability check")
        assert tracker.can_use_model("haiku"), "Haiku should be available"
        assert tracker.can_use_model("sonnet"), "Sonnet should be available"
        assert tracker.can_use_model("opus"), "Opus should be available"
        print("  OK")

        # Test 3: Increment usage
        print("Test 3: Usage increment")
        new_total = tracker.increment_usage("sonnet", 10)
        assert new_total == 10, f"Expected 10, got {new_total}"
        print("  OK")

        # Test 4: Usage summary
        print("Test 4: Usage summary")
        summary = tracker.get_usage_summary()
        assert summary["sonnet"]["used"] == 10
        print("  OK")

        # Test 5: QuotaAwareScheduler
        print("Test 5: QuotaAwareScheduler")
        scheduler = QuotaAwareScheduler(tracker)
        model = scheduler.select_model_for_task(estimated_complexity=2)
        assert model == "haiku", f"Expected haiku for complexity 2, got {model}"
        model = scheduler.select_model_for_task(estimated_complexity=4)
        assert model == "sonnet", f"Expected sonnet for complexity 4, got {model}"
        print("  OK")

        # Test 6: Recommendation
        print("Test 6: Recommendation")
        rec = scheduler.get_recommendation(estimated_complexity=3)
        assert "model" in rec
        assert "reasoning" in rec
        print("  OK")

    print("\nAll quota tracker tests passed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_quota_tracker()
    else:
        main()
