"""
Temporal Scheduler - Optimize quota usage across time boundaries.

Implements Solution 4 from claude-code-architecture.md:
- Work timing classification (sync vs async)
- Overnight work scheduling
- Quota utilization forecasting

State file: ~/.claude/infolead-claude-subscription-router/state/temporal-work-queue.json

Usage:
    scheduler = TemporalScheduler()
    scheduler.add_work(TimedWorkItem(...))
    overnight_work = scheduler.schedule_overnight_work()

Change Driver: TEMPORAL_OPTIMIZATION
Changes when: Scheduling strategy or timing rules change
"""

import asyncio
import heapq
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, time, timedelta, UTC
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple

from file_locking import locked_state_file
from quota_tracker import QuotaTracker, QUOTA_LIMITS


# State directory
STATE_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "state"
QUEUE_FILE = STATE_DIR / "temporal-work-queue.json"
RESULTS_DIR = STATE_DIR / "overnight-results"


class WorkTiming(Enum):
    """Classification of work timing requirements."""
    SYNCHRONOUS = "sync"      # User must be present
    ASYNCHRONOUS = "async"    # Can run unattended
    EITHER = "either"         # Flexible timing


@dataclass
class TimedWorkItem:
    """Work item with timing and scheduling metadata."""
    id: str
    description: str
    timing: WorkTiming
    estimated_quota: int
    estimated_duration_minutes: int
    dependencies: List[str] = field(default_factory=list)
    deadline: Optional[str] = None  # ISO format datetime
    priority: int = 5  # 1-10 scale (10 = highest)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    scheduled_for: Optional[str] = None
    status: str = "queued"  # queued, scheduled, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    project_path: Optional[str] = None  # Project directory for execution context
    project_name: Optional[str] = None  # Human-readable project name

    def __lt__(self, other: "TimedWorkItem") -> bool:
        """Compare by priority for heap operations."""
        return self.priority > other.priority  # Higher priority first

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "timing": self.timing.value,
            "estimated_quota": self.estimated_quota,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "dependencies": self.dependencies,
            "deadline": self.deadline,
            "priority": self.priority,
            "created_at": self.created_at,
            "scheduled_for": self.scheduled_for,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "project_path": self.project_path,
            "project_name": self.project_name,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TimedWorkItem":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            description=data["description"],
            timing=WorkTiming(data["timing"]),
            estimated_quota=data["estimated_quota"],
            estimated_duration_minutes=data["estimated_duration_minutes"],
            dependencies=data.get("dependencies", []),
            deadline=data.get("deadline"),
            priority=data.get("priority", 5),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            scheduled_for=data.get("scheduled_for"),
            status=data.get("status", "queued"),
            result=data.get("result"),
            error=data.get("error"),
            project_path=data.get("project_path"),
            project_name=data.get("project_name"),
        )


def classify_work_timing(request: str, context: Optional[Dict] = None) -> WorkTiming:
    """
    Determine if work requires user presence or can run asynchronously.

    Synchronous signals:
    - Interactive editing, design decisions, judgment calls
    - "Help me choose", "which approach", "review and decide"
    - File modifications requiring user approval

    Asynchronous signals:
    - "Search for", "analyze", "generate report", "find papers"
    - Batch processing, data collection, background builds
    - Read-only analysis, metric collection

    Args:
        request: User's work request
        context: Optional context dict with additional signals

    Returns:
        WorkTiming classification
    """
    # Synchronous patterns (user must be present)
    sync_keywords = [
        "help me", "which", "should I", "decide", "choose",
        "review", "edit", "modify", "design", "architecture",
        "explain", "teach", "show me", "walk through",
        "interactive", "discuss", "opinion", "preference",
    ]

    # Asynchronous patterns (can run unattended)
    async_keywords = [
        "search for", "find papers", "analyze", "generate report",
        "batch", "scan", "index", "collect data", "background",
        "overnight", "when I'm away", "prepare", "compile",
        "build", "test suite", "lint", "format all",
    ]

    request_lower = request.lower()

    # Check synchronous signals
    if any(kw in request_lower for kw in sync_keywords):
        return WorkTiming.SYNCHRONOUS

    # Check asynchronous signals
    if any(kw in request_lower for kw in async_keywords):
        return WorkTiming.ASYNCHRONOUS

    # Check for destructive operations (default sync for safety)
    if any(op in request_lower for op in ["delete", "remove", "overwrite", "destroy"]):
        return WorkTiming.SYNCHRONOUS

    # Check for read-only operations (safe for async)
    if any(op in request_lower for op in ["read", "search", "find", "list", "show", "count"]):
        return WorkTiming.ASYNCHRONOUS

    # Check context for additional signals
    if context:
        if context.get("requires_approval"):
            return WorkTiming.SYNCHRONOUS
        if context.get("batch_mode"):
            return WorkTiming.ASYNCHRONOUS

    # Default to flexible (can optimize based on quota availability)
    return WorkTiming.EITHER


class TemporalScheduler:
    """
    Schedule work across time boundaries to maximize quota utilization.

    Manages sync/async queues and overnight work scheduling.
    """

    def __init__(
        self,
        quota_tracker: Optional[QuotaTracker] = None,
        state_file: Optional[Path] = None,
    ):
        """
        Initialize temporal scheduler.

        Args:
            quota_tracker: QuotaTracker instance for quota-aware scheduling
            state_file: Path to state file (default: ~/.claude/infolead-claude-subscription-router/state/temporal-work-queue.json)
        """
        self.tracker = quota_tracker or QuotaTracker()
        self.state_file = state_file or QUEUE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Time boundaries
        self.active_hours_start = time(9, 0)   # 9 AM
        self.active_hours_end = time(22, 0)    # 10 PM

        # Load state
        self._load_state()

    def _load_state(self) -> None:
        """Load scheduler state from file."""
        if not self.state_file.exists():
            self.sync_queue: List[TimedWorkItem] = []
            self.async_queue: List[TimedWorkItem] = []
            self.scheduled_async: List[TimedWorkItem] = []
            self.completed_overnight: List[TimedWorkItem] = []
            self.failed_work: List[TimedWorkItem] = []
            self._save_state()
            return

        try:
            with locked_state_file(self.state_file, "r") as f:
                data = json.load(f)

            self.sync_queue = [TimedWorkItem.from_dict(w) for w in data.get("sync_queue", [])]
            self.async_queue = [TimedWorkItem.from_dict(w) for w in data.get("async_queue", [])]
            self.scheduled_async = [TimedWorkItem.from_dict(w) for w in data.get("scheduled_async", [])]
            self.completed_overnight = [TimedWorkItem.from_dict(w) for w in data.get("completed_overnight", [])]
            self.failed_work = [TimedWorkItem.from_dict(w) for w in data.get("failed_work", [])]

            # Rebuild heaps
            heapq.heapify(self.sync_queue)
            heapq.heapify(self.async_queue)

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[temporal] Warning: Failed to load state: {e}", file=sys.stderr)
            self.sync_queue = []
            self.async_queue = []
            self.scheduled_async = []
            self.completed_overnight = []
            self.failed_work = []

    def _save_state(self) -> None:
        """Save scheduler state to file."""
        data = {
            "sync_queue": [w.to_dict() for w in self.sync_queue],
            "async_queue": [w.to_dict() for w in self.async_queue],
            "scheduled_async": [w.to_dict() for w in self.scheduled_async],
            "completed_overnight": [w.to_dict() for w in self.completed_overnight],
            "failed_work": [w.to_dict() for w in self.failed_work],
            "last_updated": datetime.now(UTC).isoformat(),
        }

        with locked_state_file(self.state_file, "r+", create_if_missing=True) as f:
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)

    def is_active_hours(self) -> bool:
        """Check if currently in user's active hours."""
        now = datetime.now().time()
        return self.active_hours_start <= now <= self.active_hours_end

    def quota_remaining(self, model: str) -> int:
        """Calculate remaining quota for model."""
        summary = self.tracker.get_usage_summary()
        if model not in summary:
            return 0
        model_data = summary[model]
        if model_data.get("remaining") == "unlimited":
            return 999999
        return model_data.get("remaining", 0)

    def time_until_midnight(self) -> timedelta:
        """Calculate time remaining until quota reset."""
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return midnight - now

    def time_until_active_hours_end(self) -> timedelta:
        """Calculate time until active hours end."""
        now = datetime.now()
        end_today = now.replace(
            hour=self.active_hours_end.hour,
            minute=self.active_hours_end.minute,
            second=0, microsecond=0
        )
        if now.time() > self.active_hours_end:
            # Already past end time
            return timedelta(0)
        return end_today - now

    def add_work(self, work: TimedWorkItem) -> None:
        """
        Route work to appropriate queue based on timing requirements.

        Args:
            work: Work item to add
        """
        if work.timing == WorkTiming.SYNCHRONOUS:
            heapq.heappush(self.sync_queue, work)
        elif work.timing == WorkTiming.ASYNCHRONOUS:
            heapq.heappush(self.async_queue, work)
        else:  # EITHER - decide based on current context
            if self.is_active_hours():
                # During active hours, default to sync for responsiveness
                heapq.heappush(self.sync_queue, work)
            else:
                # During inactive hours, queue as async
                heapq.heappush(self.async_queue, work)

        self._save_state()

    def get_next_sync_work(self) -> Optional[TimedWorkItem]:
        """Get highest-priority synchronous work."""
        if not self.sync_queue:
            return None
        return heapq.heappop(self.sync_queue)

    def schedule_overnight_work(self) -> List[TimedWorkItem]:
        """
        Plan overnight work to utilize remaining quota.
        Called at end of active hours (e.g., 10 PM).

        Strategy:
        1. Calculate quota remaining
        2. Estimate how much async work can complete overnight
        3. Select highest-priority async work fitting quota budget
        4. Schedule for execution during inactive hours

        Returns:
            List of work items scheduled for overnight execution
        """
        hours_until_reset = self.time_until_midnight().total_seconds() / 3600
        quota_available = {
            "haiku": self.quota_remaining("haiku"),
            "sonnet": self.quota_remaining("sonnet"),
            "opus": self.quota_remaining("opus"),
        }

        # Select async work that fits quota budget
        selected_work = []
        quota_budget = quota_available.copy()
        time_budget = hours_until_reset

        # Extract all items from heap for sorting
        async_work = []
        while self.async_queue:
            work = heapq.heappop(self.async_queue)
            async_work.append(work)

        # Sort by priority (already sorted by heap, but make explicit)
        async_work.sort(key=lambda w: -w.priority)

        for work in async_work:
            # Check dependencies
            if work.dependencies:
                deps_satisfied = all(
                    any(c.id == dep and c.status == "completed"
                        for c in self.completed_overnight)
                    for dep in work.dependencies
                )
                if not deps_satisfied:
                    # Put back, might be satisfied later
                    heapq.heappush(self.async_queue, work)
                    continue

            # Determine model needed for this work
            required_model = self._estimate_model_for_work(work)

            # Check if quota available
            if quota_budget[required_model] >= work.estimated_quota:
                # Check if time available
                work_hours = work.estimated_duration_minutes / 60
                if work_hours <= time_budget:
                    work.status = "scheduled"
                    work.scheduled_for = datetime.now(UTC).isoformat()
                    selected_work.append(work)
                    quota_budget[required_model] -= work.estimated_quota
                    time_budget -= work_hours
                else:
                    # Not enough time, put back in queue
                    heapq.heappush(self.async_queue, work)
            else:
                # Not enough quota, put back in queue
                heapq.heappush(self.async_queue, work)

        self.scheduled_async = selected_work
        self._save_state()
        return selected_work

    def _estimate_model_for_work(self, work: TimedWorkItem) -> str:
        """
        Estimate which model tier work requires.

        Args:
            work: Work item to estimate

        Returns:
            Model name: "haiku", "sonnet", or "opus"
        """
        desc_lower = work.description.lower()

        # Opus indicators
        if any(kw in desc_lower for kw in [
            "formalize", "proof", "complex reasoning", "mathematical",
            "verify", "theorem", "derive", "philosophical"
        ]):
            return "opus"

        # Sonnet indicators
        if any(kw in desc_lower for kw in [
            "analyze", "design", "integrate", "architect", "review",
            "refactor", "plan", "strategy", "research"
        ]):
            return "sonnet"

        # Default to haiku for mechanical work
        return "haiku"

    def get_quota_utilization_forecast(self) -> Dict[str, float]:
        """
        Forecast quota utilization with current scheduling.

        Returns:
            Dict mapping model to percentage of quota that will be used
        """
        # Calculate quota that will be used by scheduled async work
        async_quota_usage: Dict[str, int] = {"haiku": 0, "sonnet": 0, "opus": 0}
        for work in self.scheduled_async:
            model = self._estimate_model_for_work(work)
            async_quota_usage[model] += work.estimated_quota

        # Calculate total utilization
        utilization = {}
        summary = self.tracker.get_usage_summary()

        for model in ["haiku", "sonnet", "opus"]:
            model_data = summary.get(model, {})
            limit = model_data.get("limit", 0)
            if limit == "unlimited" or limit == 0:
                utilization[model] = 0.0
                continue

            used = model_data.get("used", 0)
            total_projected = used + async_quota_usage.get(model, 0)
            utilization[model] = (total_projected / limit) * 100

        return utilization

    def mark_work_completed(self, work_id: str, result: Optional[str] = None) -> bool:
        """
        Mark scheduled work as completed.

        Args:
            work_id: ID of work item
            result: Optional result summary

        Returns:
            True if found and marked
        """
        for work in self.scheduled_async:
            if work.id == work_id:
                work.status = "completed"
                work.result = result
                self.scheduled_async.remove(work)
                self.completed_overnight.append(work)
                self._save_state()
                return True
        return False

    def mark_work_failed(self, work_id: str, error: str) -> bool:
        """
        Mark scheduled work as failed.

        Args:
            work_id: ID of work item
            error: Error message

        Returns:
            True if found and marked
        """
        for work in self.scheduled_async:
            if work.id == work_id:
                work.status = "failed"
                work.error = error
                self.scheduled_async.remove(work)
                self.failed_work.append(work)
                self._save_state()
                return True
        return False

    def get_status_summary(self) -> Dict:
        """Get summary of scheduler status."""
        return {
            "sync_queue_count": len(self.sync_queue),
            "async_queue_count": len(self.async_queue),
            "scheduled_count": len(self.scheduled_async),
            "completed_overnight_count": len(self.completed_overnight),
            "failed_count": len(self.failed_work),
            "is_active_hours": self.is_active_hours(),
            "hours_until_reset": round(self.time_until_midnight().total_seconds() / 3600, 1),
            "quota_forecast": self.get_quota_utilization_forecast(),
        }

    def display_evening_queue(self) -> None:
        """Display evening planning dashboard."""
        status = self.get_status_summary()
        forecast = status["quota_forecast"]

        print("\nOvernight Work Schedule")
        print("=" * 60)
        print(f"Time until quota reset: {status['hours_until_reset']:.1f} hours")
        print()

        print("Quota Utilization Forecast:")
        for model in ["haiku", "sonnet", "opus"]:
            pct = forecast.get(model, 0)
            bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
            print(f"  {model.capitalize():8} [{bar}] {pct:.1f}%")
        print()

        if self.scheduled_async:
            print(f"Scheduled for Tonight ({len(self.scheduled_async)} items):")
            total_duration = 0
            total_quota = 0
            for work in self.scheduled_async:
                model = self._estimate_model_for_work(work)
                print(f"  [{work.priority}] {work.description[:50]}")
                print(f"      Est: {work.estimated_duration_minutes}m, ~{work.estimated_quota} msgs ({model})")
                total_duration += work.estimated_duration_minutes
                total_quota += work.estimated_quota
            print()
            print(f"  Total: {total_duration}m, ~{total_quota} messages")
        else:
            print("No work scheduled for tonight.")

        if self.async_queue:
            print(f"\nPending Async Work ({len(self.async_queue)} items):")
            for work in list(self.async_queue)[:5]:
                print(f"  [{work.priority}] {work.description[:50]}")
            if len(self.async_queue) > 5:
                print(f"  ... and {len(self.async_queue) - 5} more")

        print("=" * 60)


class OvernightWorkExecutor:
    """
    Execute scheduled overnight work with dependency resolution.
    """

    def __init__(self, scheduler: TemporalScheduler):
        """
        Initialize executor.

        Args:
            scheduler: TemporalScheduler instance
        """
        self.scheduler = scheduler
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.results_dir = RESULTS_DIR
        self.results_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    async def execute_overnight_queue(
        self,
        work_items: List[TimedWorkItem],
        agent_executor: Callable[[TimedWorkItem, str], Any],
    ) -> Dict[str, Any]:
        """
        Execute scheduled overnight work.

        Strategy:
        1. Respect dependencies (DAG execution)
        2. Run non-dependent work in parallel (limited concurrency)
        3. Monitor for errors, continue on failure
        4. Save results for morning review

        Args:
            work_items: Work items to execute
            agent_executor: Callable(work_item, model) -> result

        Returns:
            Dict mapping work_id to result/error
        """
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(work_items)

        # Track completion
        completed_ids: set = set()
        results: Dict[str, Any] = {}

        # Max concurrent tasks
        max_concurrent = 3
        semaphore = asyncio.Semaphore(max_concurrent)

        while len(completed_ids) < len(work_items):
            # Find work ready to execute (dependencies satisfied)
            ready_work = [
                work for work in work_items
                if work.id not in completed_ids and
                all(dep in completed_ids for dep in work.dependencies)
            ]

            if not ready_work:
                # Check if we're stuck
                remaining = [w for w in work_items if w.id not in completed_ids]
                if remaining:
                    print(f"[overnight] Stalled: {len(remaining)} items blocked by dependencies")
                    for work in remaining:
                        unmet = [d for d in work.dependencies if d not in completed_ids]
                        results[work.id] = {"error": f"Blocked by: {unmet}"}
                        self.scheduler.mark_work_failed(work.id, f"Blocked by dependencies: {unmet}")
                        completed_ids.add(work.id)
                break

            # Execute ready work with concurrency limit
            tasks = []
            for work in ready_work:
                task = asyncio.create_task(
                    self._execute_with_semaphore(
                        semaphore, work, agent_executor
                    )
                )
                tasks.append((work.id, task))

            # Wait for batch to complete
            for work_id, task in tasks:
                try:
                    result = await task
                    results[work_id] = {"result": result}
                    self.scheduler.mark_work_completed(work_id, str(result)[:500])
                except Exception as e:
                    results[work_id] = {"error": str(e)}
                    self.scheduler.mark_work_failed(work_id, str(e))

                completed_ids.add(work_id)

        # Save results
        self._save_overnight_results(results)
        return results

    async def _execute_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        work: TimedWorkItem,
        agent_executor: Callable,
    ) -> Any:
        """Execute work item with semaphore for concurrency control."""
        async with semaphore:
            work.status = "running"
            model = self.scheduler._estimate_model_for_work(work)

            print(f"[overnight] Starting: {work.description[:50]} ({model})")

            try:
                # Execute the work
                import inspect
                if inspect.iscoroutinefunction(agent_executor):
                    result = await agent_executor(work, model)
                else:
                    result = agent_executor(work, model)

                print(f"[overnight] Completed: {work.id}")
                return result

            except Exception as e:
                print(f"[overnight] Failed: {work.id} - {e}")
                raise

    def _build_dependency_graph(
        self,
        work_items: List[TimedWorkItem]
    ) -> Dict[str, List[str]]:
        """Build dependency graph from work items."""
        return {work.id: work.dependencies for work in work_items}

    def _save_overnight_results(self, results: Dict[str, Any]) -> None:
        """Save overnight execution results."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        result_file = self.results_dir / f"results-{timestamp}.json"

        with open(result_file, "w") as f:
            json.dump({
                "timestamp": datetime.now(UTC).isoformat(),
                "results": results,
            }, f, indent=2, default=str)

        os.chmod(result_file, 0o600)
        print(f"[overnight] Results saved: {result_file}")


def main():
    """CLI interface for temporal scheduler."""
    import argparse
    import uuid

    parser = argparse.ArgumentParser(description="Temporal Scheduler CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status command
    subparsers.add_parser("status", help="Show scheduler status")

    # add command
    add_parser = subparsers.add_parser("add", help="Add work to queue")
    add_parser.add_argument("description", help="Work description")
    add_parser.add_argument("--timing", choices=["sync", "async", "either"], default="either")
    add_parser.add_argument("--quota", type=int, default=10, help="Estimated quota usage")
    add_parser.add_argument("--duration", type=int, default=30, help="Estimated duration (minutes)")
    add_parser.add_argument("--priority", type=int, default=5, help="Priority (1-10)")
    add_parser.add_argument("--project-path", help="Project directory path")
    add_parser.add_argument("--project-name", help="Project name")

    # schedule command
    subparsers.add_parser("schedule", help="Schedule overnight work")

    # evening command
    subparsers.add_parser("evening", help="Display evening planning dashboard")

    # classify command
    classify_parser = subparsers.add_parser("classify", help="Classify work timing")
    classify_parser.add_argument("request", help="Work request to classify")

    args = parser.parse_args()

    scheduler = TemporalScheduler()

    if args.command == "status" or args.command is None:
        status = scheduler.get_status_summary()
        print("Temporal Scheduler Status")
        print("=" * 40)
        print(f"Active hours: {'Yes' if status['is_active_hours'] else 'No'}")
        print(f"Hours until reset: {status['hours_until_reset']:.1f}")
        print(f"Sync queue: {status['sync_queue_count']} items")
        print(f"Async queue: {status['async_queue_count']} items")
        print(f"Scheduled overnight: {status['scheduled_count']} items")
        print(f"Completed overnight: {status['completed_overnight_count']} items")
        print(f"Failed: {status['failed_count']} items")

    elif args.command == "add":
        timing = WorkTiming(args.timing)
        work = TimedWorkItem(
            id=str(uuid.uuid4())[:8],
            description=args.description,
            timing=timing,
            estimated_quota=args.quota,
            estimated_duration_minutes=args.duration,
            priority=args.priority,
            project_path=args.project_path,
            project_name=args.project_name,
        )
        scheduler.add_work(work)
        print(f"Added work: {work.id} ({timing.value})")
        if args.project_path:
            print(f"  Project: {args.project_name or args.project_path}")

    elif args.command == "schedule":
        scheduled = scheduler.schedule_overnight_work()
        print(f"Scheduled {len(scheduled)} items for overnight execution")
        for work in scheduled:
            print(f"  [{work.priority}] {work.description[:50]}")

    elif args.command == "evening":
        scheduler.display_evening_queue()

    elif args.command == "classify":
        timing = classify_work_timing(args.request)
        print(f"Classification: {timing.value}")
        print(f"  SYNCHRONOUS = requires user presence")
        print(f"  ASYNCHRONOUS = can run unattended")
        print(f"  EITHER = flexible timing")


def test_temporal_scheduler() -> None:
    """Test temporal scheduler functionality."""
    import tempfile
    import uuid

    print("Testing temporal scheduler...")

    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "test-queue.json"
        quota_file = Path(tmpdir) / "test-quota.json"

        # Create quota tracker for testing
        tracker = QuotaTracker(state_file=quota_file)
        scheduler = TemporalScheduler(quota_tracker=tracker, state_file=state_file)

        # Test 1: Work timing classification
        print("Test 1: Work timing classification")
        assert classify_work_timing("help me choose an approach") == WorkTiming.SYNCHRONOUS
        assert classify_work_timing("search for papers on mitochondria") == WorkTiming.ASYNCHRONOUS
        assert classify_work_timing("process the data") == WorkTiming.EITHER
        print("  OK")

        # Test 2: Add work
        print("Test 2: Add work to queue")
        work1 = TimedWorkItem(
            id="work-1",
            description="Search for ME/CFS papers",
            timing=WorkTiming.ASYNCHRONOUS,
            estimated_quota=20,
            estimated_duration_minutes=60,
            priority=8,
        )
        scheduler.add_work(work1)
        assert len(scheduler.async_queue) == 1
        print("  OK")

        # Test 3: Schedule overnight work
        print("Test 3: Schedule overnight work")
        work2 = TimedWorkItem(
            id="work-2",
            description="Analyze research trends",
            timing=WorkTiming.ASYNCHRONOUS,
            estimated_quota=15,
            estimated_duration_minutes=45,
            priority=6,
        )
        scheduler.add_work(work2)
        scheduled = scheduler.schedule_overnight_work()
        assert len(scheduled) == 2
        print("  OK")

        # Test 4: Quota forecast
        print("Test 4: Quota utilization forecast")
        forecast = scheduler.get_quota_utilization_forecast()
        assert "sonnet" in forecast
        assert "haiku" in forecast
        print("  OK")

        # Test 5: Status summary
        print("Test 5: Status summary")
        status = scheduler.get_status_summary()
        assert "scheduled_count" in status
        assert status["scheduled_count"] == 2
        print("  OK")

        # Test 6: Mark completed
        print("Test 6: Mark work completed")
        assert scheduler.mark_work_completed("work-1", "Found 15 papers")
        assert len(scheduler.completed_overnight) == 1
        print("  OK")

        # Test 7: State persistence
        print("Test 7: State persistence")
        scheduler2 = TemporalScheduler(quota_tracker=tracker, state_file=state_file)
        assert len(scheduler2.completed_overnight) == 1
        print("  OK")

    print("\nAll temporal scheduler tests passed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_temporal_scheduler()
    else:
        main()