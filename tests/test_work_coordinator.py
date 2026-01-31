"""
Unit tests for work_coordinator module.

Tests Kanban-style work coordination with WIP limits.
"""

import unittest
import sys
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "implementation"))

from work_coordinator import (
    WorkCoordinator,
    WorkItem,
    WorkStatus,
)


class TestWorkItem(unittest.TestCase):
    """Test WorkItem serialization."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        item = WorkItem(
            id="test1",
            description="Test task",
            priority=5,
            estimated_complexity=3
        )
        data = item.to_dict()

        self.assertEqual(data["id"], "test1")
        self.assertEqual(data["priority"], 5)
        self.assertEqual(data["status"], "queued")

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "test1",
            "description": "Test task",
            "priority": 5,
            "estimated_complexity": 3,
            "dependencies": [],
            "status": "queued",
        }
        item = WorkItem.from_dict(data)

        self.assertEqual(item.id, "test1")
        self.assertEqual(item.priority, 5)
        self.assertEqual(item.status, WorkStatus.QUEUED)

    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = WorkItem(
            id="test1",
            description="Test task",
            priority=5,
            estimated_complexity=3,
            dependencies=["dep1"]
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = WorkItem.from_dict(data)

        self.assertEqual(original.id, restored.id)
        self.assertEqual(original.dependencies, restored.dependencies)


class TestWorkCoordinator(unittest.TestCase):
    """Test WorkCoordinator functionality."""

    def setUp(self):
        """Create temporary directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_file = self.temp_dir / "work-queue.json"
        self.coord = WorkCoordinator(wip_limit=2, state_file=self.state_file)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_add_work(self):
        """Test adding work items."""
        item = WorkItem(
            id="w1",
            description="Test task",
            priority=5,
            estimated_complexity=3
        )
        self.coord.add_work(item)

        self.assertEqual(len(self.coord.work_items), 1)
        self.assertEqual(self.coord.work_items[0].id, "w1")

    def test_wip_limit_respected(self):
        """Test that WIP limit is respected."""
        # Add 3 tasks
        for i in range(3):
            self.coord.add_work(WorkItem(
                id=f"w{i}",
                description=f"Task {i}",
                priority=5,
                estimated_complexity=2
            ))

        # Schedule work
        started = self.coord.schedule_work()

        # Should only start 2 (WIP limit)
        self.assertEqual(len(started), 2)
        self.assertEqual(self.coord.get_active_count(), 2)

    def test_priority_ordering(self):
        """Test that higher priority work is scheduled first."""
        # Add tasks with different priorities
        self.coord.add_work(WorkItem(
            id="low",
            description="Low priority",
            priority=3,
            estimated_complexity=2
        ))
        self.coord.add_work(WorkItem(
            id="high",
            description="High priority",
            priority=8,
            estimated_complexity=2
        ))

        # Schedule work
        started = self.coord.schedule_work()

        # High priority should be started first
        started_ids = [w.id for w in started]
        self.assertIn("high", started_ids)

    def test_dependency_blocking(self):
        """Test that dependencies block work."""
        # Add task with dependency
        self.coord.add_work(WorkItem(
            id="w1",
            description="Independent task",
            priority=5,
            estimated_complexity=2
        ))
        self.coord.add_work(WorkItem(
            id="w2",
            description="Dependent task",
            priority=8,  # Higher priority
            estimated_complexity=2,
            dependencies=["w1"]  # Depends on w1
        ))

        # Schedule work
        started = self.coord.schedule_work()

        # w1 should start, w2 should not (blocked by dependency)
        started_ids = [w.id for w in started]
        self.assertIn("w1", started_ids)
        self.assertNotIn("w2", started_ids)

    def test_dependency_unblocking(self):
        """Test that completing work unblocks dependents."""
        # Add tasks with dependency
        self.coord.add_work(WorkItem(
            id="w1",
            description="First task",
            priority=5,
            estimated_complexity=2
        ))
        self.coord.add_work(WorkItem(
            id="w2",
            description="Dependent task",
            priority=8,
            estimated_complexity=2,
            dependencies=["w1"]
        ))

        # Start work
        self.coord.schedule_work()

        # Complete w1
        self.coord.complete_work("w1")

        # Now w2 should be active
        w2 = next(w for w in self.coord.work_items if w.id == "w2")
        self.assertEqual(w2.status, WorkStatus.ACTIVE)

    def test_unblocking_priority(self):
        """Test that work that unblocks others is prioritized."""
        # Add blocker and multiple dependent tasks
        self.coord.add_work(WorkItem(
            id="blocker",
            description="Blocker task",
            priority=3,  # Low priority
            estimated_complexity=2
        ))
        self.coord.add_work(WorkItem(
            id="dep1",
            description="Dependent 1",
            priority=5,
            estimated_complexity=2,
            dependencies=["blocker"]
        ))
        self.coord.add_work(WorkItem(
            id="dep2",
            description="Dependent 2",
            priority=5,
            estimated_complexity=2,
            dependencies=["blocker"]
        ))
        self.coord.add_work(WorkItem(
            id="independent",
            description="Independent high priority",
            priority=8,  # Higher priority
            estimated_complexity=2
        ))

        # Schedule - blocker should start despite low priority
        # because it unblocks 2 other tasks
        started = self.coord.schedule_work()
        started_ids = [w.id for w in started]

        # Both blocker and independent should start
        self.assertIn("blocker", started_ids)
        self.assertIn("independent", started_ids)

    def test_state_persistence(self):
        """Test that state is saved and loaded correctly."""
        # Add work item
        self.coord.add_work(WorkItem(
            id="w1",
            description="Test task",
            priority=5,
            estimated_complexity=2
        ))

        # Create new coordinator with same state file
        coord2 = WorkCoordinator(wip_limit=2, state_file=self.state_file)

        # Should load previous state
        self.assertEqual(len(coord2.work_items), 1)
        self.assertEqual(coord2.work_items[0].id, "w1")

    def test_complete_work(self):
        """Test work completion."""
        # Add and start work
        self.coord.add_work(WorkItem(
            id="w1",
            description="Test task",
            priority=5,
            estimated_complexity=2
        ))
        self.coord.schedule_work()

        # Complete work
        self.coord.complete_work("w1")

        # Check status
        w1 = self.coord.work_items[0]
        self.assertEqual(w1.status, WorkStatus.COMPLETED)
        self.assertIsNotNone(w1.completed_at)

    def test_fail_work(self):
        """Test work failure."""
        # Add and start work
        self.coord.add_work(WorkItem(
            id="w1",
            description="Test task",
            priority=5,
            estimated_complexity=2
        ))
        self.coord.schedule_work()

        # Fail work
        self.coord.fail_work("w1", "Test error")

        # Check status
        w1 = self.coord.work_items[0]
        self.assertEqual(w1.status, WorkStatus.FAILED)
        self.assertEqual(w1.error_message, "Test error")

    def test_status_summary(self):
        """Test status summary generation."""
        # Add variety of work
        self.coord.add_work(WorkItem(id="w1", description="Task 1", priority=5, estimated_complexity=2))
        self.coord.add_work(WorkItem(id="w2", description="Task 2", priority=5, estimated_complexity=2))
        self.coord.add_work(WorkItem(id="w3", description="Task 3", priority=5, estimated_complexity=2))

        # Start some work
        self.coord.schedule_work()

        # Complete one
        self.coord.complete_work("w1")

        # Get summary
        summary = self.coord.get_status_summary()

        self.assertEqual(summary["total_count"], 3)
        self.assertEqual(summary["completed_count"], 1)
        self.assertGreater(summary["active_count"], 0)


class TestWorkCoordinatorEdgeCases(unittest.TestCase):
    """Test edge cases in work coordination."""

    def setUp(self):
        """Create temporary directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_file = self.temp_dir / "work-queue.json"
        self.coord = WorkCoordinator(wip_limit=2, state_file=self.state_file)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_empty_queue(self):
        """Test scheduling from empty queue."""
        started = self.coord.schedule_work()
        self.assertEqual(len(started), 0)

    def test_circular_dependencies(self):
        """Test handling of circular dependencies."""
        # Create circular dependency (w1 -> w2 -> w1)
        self.coord.add_work(WorkItem(
            id="w1",
            description="Task 1",
            priority=5,
            estimated_complexity=2,
            dependencies=["w2"]
        ))
        self.coord.add_work(WorkItem(
            id="w2",
            description="Task 2",
            priority=5,
            estimated_complexity=2,
            dependencies=["w1"]
        ))

        # Try to schedule - should not deadlock
        started = self.coord.schedule_work()

        # Nothing should start (circular dependency)
        self.assertEqual(len(started), 0)

    def test_missing_dependency(self):
        """Test work with missing dependency."""
        # Add task with non-existent dependency
        self.coord.add_work(WorkItem(
            id="w1",
            description="Task 1",
            priority=5,
            estimated_complexity=2,
            dependencies=["nonexistent"]
        ))

        # Try to schedule
        started = self.coord.schedule_work()

        # Should not start (dependency not satisfied)
        self.assertEqual(len(started), 0)


if __name__ == "__main__":
    unittest.main()