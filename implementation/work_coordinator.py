"""
Work Coordinator - Production-ready Kanban-style work queue with WIP limits.

Implements the work coordination algorithm with completion guarantees through
bounded parallelism and priority-based scheduling.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from enum import Enum
from datetime import datetime, timedelta
import json
import os
import tempfile
from pathlib import Path


class WorkStatus(Enum):
    """Work item states in the workflow."""
    QUEUED = "queued"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkItem:
    """A unit of work in the queue."""
    id: str
    description: str
    priority: int  # 1-10, higher = more important
    estimated_complexity: int  # 1-5 scale
    dependencies: List[str] = field(default_factory=list)  # IDs of required tasks
    status: WorkStatus = WorkStatus.QUEUED
    agent_assigned: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "estimated_complexity": self.estimated_complexity,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "agent_assigned": self.agent_assigned,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }

    @staticmethod
    def from_dict(data: Dict) -> "WorkItem":
        """Deserialize from dictionary."""
        return WorkItem(
            id=data["id"],
            description=data["description"],
            priority=data["priority"],
            estimated_complexity=data["estimated_complexity"],
            dependencies=data.get("dependencies", []),
            status=WorkStatus(data["status"]),
            agent_assigned=data.get("agent_assigned"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message"),
        )


class WorkCoordinator:
    """
    Manages parallel work distribution with WIP limits and completion prioritization.

    Implements Kanban-style work coordination:
    - Bounded parallelism (WIP limit)
    - Priority-based scheduling
    - Dependency management
    - Completion tracking
    """

    def __init__(
        self,
        wip_limit: int = 3,
        state_file: Optional[Path] = None
    ):
        """
        Initialize work coordinator.

        Args:
            wip_limit: Maximum concurrent active tasks (default 3)
            state_file: Path to persist state (default: ~/.claude/infolead-router/state/work-queue.json)
        """
        self.wip_limit = wip_limit
        self.work_items: List[WorkItem] = []

        # State file for persistence
        if state_file is None:
            state_file = Path.home() / ".claude" / "infolead-router" / "state" / "work-queue.json"
        self.state_file = state_file

        # Ensure state directory exists with secure permissions
        self.state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Load existing state
        self._load_state()

    def _load_state(self):
        """Load work queue state from disk."""
        if not self.state_file.exists():
            return

        try:
            with open(self.state_file) as f:
                data = json.load(f)
                self.wip_limit = data.get("wip_limit", 3)
                self.work_items = [
                    WorkItem.from_dict(item)
                    for item in data.get("work_items", [])
                ]
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"Warning: Could not load work queue state: {e}")
            self.work_items = []

    def _save_state(self):
        """Save work queue state to disk using atomic writes."""
        data = {
            "wip_limit": self.wip_limit,
            "work_items": [item.to_dict() for item in self.work_items],
            "last_updated": datetime.now().isoformat(),
        }

        try:
            # Atomic write pattern
            fd, temp_path = tempfile.mkstemp(
                dir=self.state_file.parent,
                prefix=".work-queue-",
                suffix=".json.tmp"
            )

            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)

            # Secure permissions
            os.chmod(temp_path, 0o600)

            # Atomic rename
            os.rename(temp_path, self.state_file)
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise RuntimeError(f"Failed to save work queue state: {e}") from e

    def add_work(self, item: WorkItem):
        """Add work item to queue."""
        self.work_items.append(item)
        self._save_state()

    def get_active_count(self) -> int:
        """Count currently active work items."""
        return len([w for w in self.work_items if w.status == WorkStatus.ACTIVE])

    def get_completed_ids(self) -> Set[str]:
        """Get set of completed work item IDs."""
        return {w.id for w in self.work_items if w.status == WorkStatus.COMPLETED}

    def dependencies_satisfied(self, item: WorkItem) -> bool:
        """Check if all dependencies for a work item are satisfied."""
        completed_ids = self.get_completed_ids()
        return all(dep_id in completed_ids for dep_id in item.dependencies)

    def count_dependent_work(self, work_id: str) -> int:
        """Count how many other work items depend on this one."""
        count = 0
        for item in self.work_items:
            if work_id in item.dependencies:
                count += 1
        return count

    def get_next_work(self) -> Optional[WorkItem]:
        """
        Select next work item using priority rules:

        1. Unblock other work (highest priority if dependencies satisfied)
        2. Highest priority eligible work
        3. Respect WIP limit

        Returns:
            Next work item to start, or None if at capacity or no eligible work
        """
        # Check WIP limit
        if self.get_active_count() >= self.wip_limit:
            return None

        # Get eligible work (queued, dependencies satisfied)
        eligible = [
            w for w in self.work_items
            if w.status == WorkStatus.QUEUED and self.dependencies_satisfied(w)
        ]

        if not eligible:
            return None

        # Priority 1: Work that unblocks most other work
        unblocking_scores = {
            w.id: self.count_dependent_work(w.id) for w in eligible
        }
        max_unblocking = max(unblocking_scores.values())

        if max_unblocking > 0:
            # Among unblocking work, choose highest priority
            unblocking_work = [
                w for w in eligible
                if unblocking_scores[w.id] == max_unblocking
            ]
            return max(unblocking_work, key=lambda w: w.priority)

        # Priority 2: Highest priority eligible work
        return max(eligible, key=lambda w: w.priority)

    def schedule_work(self) -> List[WorkItem]:
        """
        Main scheduling loop: Fill WIP slots with highest-value work.

        Returns:
            List of newly-started work items
        """
        newly_started = []

        while self.get_active_count() < self.wip_limit:
            next_work = self.get_next_work()
            if not next_work:
                break  # No eligible work available

            next_work.status = WorkStatus.ACTIVE
            next_work.started_at = datetime.now()
            newly_started.append(next_work)

        if newly_started:
            self._save_state()

        return newly_started

    def complete_work(self, work_id: str, agent: Optional[str] = None):
        """
        Mark work complete and trigger re-scheduling.

        Args:
            work_id: ID of completed work
            agent: Optional agent name that completed the work
        """
        for item in self.work_items:
            if item.id == work_id:
                item.status = WorkStatus.COMPLETED
                item.completed_at = datetime.now()
                if agent:
                    item.agent_assigned = agent
                break

        self._save_state()

        # Attempt to fill the freed WIP slot
        self.schedule_work()

    def fail_work(self, work_id: str, error: str):
        """
        Mark work failed.

        Args:
            work_id: ID of failed work
            error: Error message
        """
        for item in self.work_items:
            if item.id == work_id:
                item.status = WorkStatus.FAILED
                item.error_message = error
                item.completed_at = datetime.now()
                break

        self._save_state()

        # Attempt to fill the freed WIP slot
        self.schedule_work()

    def get_status_summary(self) -> Dict:
        """Get summary of work queue status."""
        return {
            "wip_limit": self.wip_limit,
            "active_count": self.get_active_count(),
            "queued_count": len([w for w in self.work_items if w.status == WorkStatus.QUEUED]),
            "completed_count": len([w for w in self.work_items if w.status == WorkStatus.COMPLETED]),
            "failed_count": len([w for w in self.work_items if w.status == WorkStatus.FAILED]),
            "total_count": len(self.work_items),
        }

    def display_dashboard(self):
        """Display work status dashboard for user."""
        summary = self.get_status_summary()

        print("📊 Work Status")
        print("═" * 60)
        print()

        # Active work
        active_work = [w for w in self.work_items if w.status == WorkStatus.ACTIVE]
        print(f"Active ({len(active_work)}/{self.wip_limit}):")

        if active_work:
            for w in active_work:
                elapsed = datetime.now() - w.started_at if w.started_at else timedelta(0)
                elapsed_min = int(elapsed.total_seconds() / 60)
                print(f"  ⏳ [{w.id}] {w.description}")
                print(f"     Agent: {w.agent_assigned or 'unassigned'} | Elapsed: {elapsed_min}m")
        else:
            print("  (none)")
        print()

        # Queued work
        queued_work = [w for w in self.work_items if w.status == WorkStatus.QUEUED]
        print(f"Queued ({len(queued_work)}):")

        if queued_work:
            for w in sorted(queued_work, key=lambda x: x.priority, reverse=True)[:5]:
                blocked = not self.dependencies_satisfied(w)
                status_icon = "🚫" if blocked else "📋"
                print(f"  {status_icon} [{w.id}] Priority {w.priority} - {w.description}")
                if blocked:
                    print(f"     Blocked by: {', '.join(w.dependencies)}")
        else:
            print("  (none)")
        print()

        # Completed work (recent)
        completed_work = [w for w in self.work_items if w.status == WorkStatus.COMPLETED]
        recent_completed = sorted(
            completed_work,
            key=lambda x: x.completed_at or datetime.min,
            reverse=True
        )[:3]

        print(f"Recently Completed ({len(completed_work)} total):")
        if recent_completed:
            for w in recent_completed:
                print(f"  ✅ [{w.id}] {w.description}")
        else:
            print("  (none)")
        print()


# Test/example usage
if __name__ == "__main__":
    # Create coordinator
    coord = WorkCoordinator(wip_limit=2)

    # Add some work items
    coord.add_work(WorkItem(
        id="w1",
        description="Fix syntax errors in main.py",
        priority=8,
        estimated_complexity=2
    ))

    coord.add_work(WorkItem(
        id="w2",
        description="Add tests for authentication",
        priority=6,
        estimated_complexity=4,
        dependencies=["w1"]  # Blocked until w1 completes
    ))

    coord.add_work(WorkItem(
        id="w3",
        description="Update documentation",
        priority=5,
        estimated_complexity=2
    ))

    # Schedule work
    print("Initial scheduling...")
    started = coord.schedule_work()
    print(f"Started {len(started)} tasks")
    print()

    # Display dashboard
    coord.display_dashboard()

    # Simulate completion
    print("\n--- Completing w1 ---\n")
    coord.complete_work("w1")

    # Display updated dashboard
    coord.display_dashboard()
