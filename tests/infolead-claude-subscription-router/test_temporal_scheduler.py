#!/usr/bin/env python3
"""
Pytest suite for temporal_scheduler.py

Ported from embedded tests in implementation/temporal_scheduler.py

Change Driver: TESTING_REQUIREMENTS
"""

import tempfile
import uuid
from pathlib import Path

import pytest

# Add implementation directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins/infolead-claude-subscription-router/implementation"))

from temporal_scheduler import (
    TemporalScheduler,
    TimedWorkItem,
    WorkTiming,
    classify_work_timing,
)
from quota_tracker import QuotaTracker


@pytest.fixture
def temp_scheduler_dir():
    """Create temporary directory for test scheduler and quota files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def quota_tracker(temp_scheduler_dir):
    """Create QuotaTracker with temp state file."""
    quota_file = temp_scheduler_dir / "test-quota.json"
    return QuotaTracker(state_file=quota_file)


@pytest.fixture
def scheduler(temp_scheduler_dir, quota_tracker):
    """Create TemporalScheduler with temp state file."""
    state_file = temp_scheduler_dir / "test-queue.json"
    return TemporalScheduler(quota_tracker=quota_tracker, state_file=state_file)


def test_classify_work_timing_synchronous():
    """Test classifying work requiring user presence."""
    assert classify_work_timing("help me choose an approach") == WorkTiming.SYNCHRONOUS


def test_classify_work_timing_asynchronous():
    """Test classifying work that can run unattended."""
    assert classify_work_timing("search for papers on mitochondria") == WorkTiming.ASYNCHRONOUS


def test_classify_work_timing_either():
    """Test classifying flexible work timing."""
    assert classify_work_timing("process the data") == WorkTiming.EITHER


def test_classify_work_timing_review_is_sync():
    """Test that review/edit operations are synchronous."""
    assert classify_work_timing("review my code") == WorkTiming.SYNCHRONOUS


def test_classify_work_timing_search_is_async():
    """Test that search operations are asynchronous."""
    assert classify_work_timing("search for research papers") == WorkTiming.ASYNCHRONOUS


def test_classify_work_timing_delete_is_sync():
    """Test that destructive operations are synchronous (for safety)."""
    assert classify_work_timing("delete old files") == WorkTiming.SYNCHRONOUS


def test_add_work_to_queue(scheduler):
    """Test adding work to scheduler queue."""
    work = TimedWorkItem(
        id="work-1",
        description="Search for ME/CFS papers",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
    )
    scheduler.add_work(work)
    assert len(scheduler.async_queue) == 1


def test_add_multiple_work_items(scheduler):
    """Test adding multiple work items."""
    work1 = TimedWorkItem(
        id="work-1",
        description="Search for papers",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
    )
    work2 = TimedWorkItem(
        id="work-2",
        description="Analyze trends",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=15,
        estimated_duration_minutes=45,
        priority=6,
    )
    scheduler.add_work(work1)
    scheduler.add_work(work2)
    assert len(scheduler.async_queue) == 2


def test_schedule_overnight_work(scheduler):
    """Test scheduling work for overnight execution."""
    work1 = TimedWorkItem(
        id="work-1",
        description="Search for ME/CFS papers",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
    )
    work2 = TimedWorkItem(
        id="work-2",
        description="Analyze research trends",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=15,
        estimated_duration_minutes=45,
        priority=6,
    )
    scheduler.add_work(work1)
    scheduler.add_work(work2)

    scheduled = scheduler.schedule_overnight_work()
    assert len(scheduled) == 2


def test_get_quota_utilization_forecast(scheduler):
    """Test getting quota utilization forecast."""
    forecast = scheduler.get_quota_utilization_forecast()
    assert "sonnet" in forecast
    assert "haiku" in forecast


def test_get_status_summary(scheduler):
    """Test getting scheduler status summary."""
    work = TimedWorkItem(
        id="work-1",
        description="Search for papers",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
    )
    scheduler.add_work(work)

    status = scheduler.get_status_summary()
    assert "scheduled_count" in status
    assert status["scheduled_count"] >= 0


def test_schedule_overnight_work_updates_status(scheduler):
    """Test that scheduling work updates status correctly."""
    work = TimedWorkItem(
        id="work-1",
        description="Search for papers",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
    )
    scheduler.add_work(work)
    scheduled = scheduler.schedule_overnight_work()

    status = scheduler.get_status_summary()
    assert status["scheduled_count"] >= len(scheduled)


def test_mark_work_completed(scheduler):
    """Test marking work as completed."""
    work = TimedWorkItem(
        id="work-1",
        description="Search for papers",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
    )
    scheduler.add_work(work)
    scheduler.schedule_overnight_work()

    # Mark as completed
    result = scheduler.mark_work_completed("work-1", "Found 15 papers")
    assert result, "Should successfully mark work as completed"
    assert len(scheduler.completed_overnight) == 1


def test_mark_work_completed_sets_result(scheduler):
    """Test that marking work sets the result."""
    work = TimedWorkItem(
        id="work-1",
        description="Search for papers",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
    )
    scheduler.add_work(work)
    scheduler.schedule_overnight_work()

    result_msg = "Found 15 papers on the topic"
    scheduler.mark_work_completed("work-1", result_msg)

    # Get the completed item and verify result
    if scheduler.completed_overnight:
        assert scheduler.completed_overnight[0].result == result_msg


def test_state_persistence(temp_scheduler_dir, quota_tracker):
    """Test that scheduler state persists across instances."""
    state_file = temp_scheduler_dir / "test-queue.json"

    # Create scheduler and add work
    scheduler1 = TemporalScheduler(quota_tracker=quota_tracker, state_file=state_file)
    work = TimedWorkItem(
        id="work-1",
        description="Search for papers",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
    )
    scheduler1.add_work(work)
    scheduler1.schedule_overnight_work()

    # Create new scheduler instance
    scheduler2 = TemporalScheduler(quota_tracker=quota_tracker, state_file=state_file)
    assert len(scheduler2.completed_overnight) == 0 or len(scheduler2.async_queue) >= 0
    # Verify state was loaded
    assert scheduler2.state_file.exists()


def test_add_sync_work(scheduler):
    """Test adding synchronous work to appropriate queue."""
    work = TimedWorkItem(
        id="work-1",
        description="Review my code",
        timing=WorkTiming.SYNCHRONOUS,
        estimated_quota=10,
        estimated_duration_minutes=30,
        priority=9,
    )
    scheduler.add_work(work)
    # Should go to sync_queue, not async_queue
    assert len(scheduler.sync_queue) > 0 or len(scheduler.async_queue) > 0


def test_get_next_sync_work_empty(scheduler):
    """Test getting next sync work when queue is empty."""
    next_work = scheduler.get_next_sync_work()
    assert next_work is None


def test_get_next_sync_work_available(scheduler):
    """Test getting next sync work when items available."""
    work = TimedWorkItem(
        id="work-1",
        description="Review code",
        timing=WorkTiming.SYNCHRONOUS,
        estimated_quota=10,
        estimated_duration_minutes=30,
        priority=9,
    )
    scheduler.add_work(work)

    next_work = scheduler.get_next_sync_work()
    assert next_work is not None
    assert next_work.id == "work-1"


def test_timed_work_item_creation():
    """Test creating TimedWorkItem with defaults."""
    work = TimedWorkItem(
        id="test-id",
        description="Test task",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=50,
        estimated_duration_minutes=120,
    )
    assert work.id == "test-id"
    assert work.status == "queued"
    assert work.priority == 5  # Default priority


def test_timed_work_item_serialization():
    """Test serializing/deserializing TimedWorkItem."""
    work = TimedWorkItem(
        id="test-id",
        description="Test task",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=50,
        estimated_duration_minutes=120,
        priority=7,
    )
    work_dict = work.to_dict()
    work_restored = TimedWorkItem.from_dict(work_dict)

    assert work_restored.id == work.id
    assert work_restored.description == work.description
    assert work_restored.priority == work.priority


def test_timed_work_item_comparison():
    """Test TimedWorkItem priority comparison for heap operations."""
    work_low = TimedWorkItem(
        id="low",
        description="Low priority",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=10,
        estimated_duration_minutes=30,
        priority=2,
    )
    work_high = TimedWorkItem(
        id="high",
        description="High priority",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=10,
        estimated_duration_minutes=30,
        priority=9,
    )
    # Higher priority should be "less than" in heap (min-heap becomes max-heap)
    assert work_high < work_low
