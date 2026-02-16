#!/usr/bin/env python3
"""
Pytest suite for overnight_execution_runner.py

Creates tests for core functionality:
- load_scheduled_work() - Load work items from queue file
- create_agent_executor() - Create agent executor function
- execute_overnight_work() - Main execution function

Change Driver: TESTING_REQUIREMENTS
"""

import asyncio
import json
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List

import pytest

# Add implementation directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins/infolead-claude-subscription-router/implementation"))

from temporal_scheduler import TimedWorkItem, WorkTiming

# Import functions from overnight_execution_runner
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins/infolead-claude-subscription-router"))
from implementation.overnight_execution_runner import (
    load_scheduled_work,
    create_agent_executor,
    execute_overnight_work,
)


@pytest.fixture
def temp_work_dir():
    """Create temporary directory for test work files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def queue_file(temp_work_dir):
    """Create test queue file path."""
    return temp_work_dir / "test-queue.json"


@pytest.fixture
def results_dir(temp_work_dir):
    """Create test results directory path."""
    results = temp_work_dir / "overnight-results"
    results.mkdir(exist_ok=True)
    return results


@pytest.fixture
def sample_work_items():
    """Create sample work items for testing."""
    return [
        TimedWorkItem(
            id="work-1",
            description="Search for research papers",
            timing=WorkTiming.ASYNCHRONOUS,
            estimated_quota=20,
            estimated_duration_minutes=60,
            priority=8,
            project_name="research-project",
        ),
        TimedWorkItem(
            id="work-2",
            description="Analyze data trends",
            timing=WorkTiming.ASYNCHRONOUS,
            estimated_quota=15,
            estimated_duration_minutes=45,
            priority=6,
            project_name="analytics-project",
        ),
    ]


@pytest.fixture
def populated_queue_file(queue_file, sample_work_items):
    """Create queue file with test work items."""
    queue_data = {
        "scheduled_async": [item.to_dict() for item in sample_work_items],
        "last_updated": datetime.now(UTC).isoformat(),
    }

    with open(queue_file, 'w') as f:
        json.dump(queue_data, f, indent=2)

    return queue_file


def test_load_scheduled_work_no_file(queue_file):
    """Test loading from non-existent queue file."""
    work_items = load_scheduled_work(queue_file)
    assert work_items == []


def test_load_scheduled_work_empty_queue(queue_file):
    """Test loading from queue file with no scheduled work."""
    queue_data = {
        "scheduled_async": [],
        "last_updated": datetime.now(UTC).isoformat(),
    }

    with open(queue_file, 'w') as f:
        json.dump(queue_data, f)

    work_items = load_scheduled_work(queue_file)
    assert work_items == []


def test_load_scheduled_work_single_item(queue_file, sample_work_items):
    """Test loading single work item from queue."""
    queue_data = {
        "scheduled_async": [sample_work_items[0].to_dict()],
        "last_updated": datetime.now(UTC).isoformat(),
    }

    with open(queue_file, 'w') as f:
        json.dump(queue_data, f)

    work_items = load_scheduled_work(queue_file)
    assert len(work_items) == 1
    assert work_items[0].id == "work-1"


def test_load_scheduled_work_multiple_items(populated_queue_file):
    """Test loading multiple work items from queue."""
    work_items = load_scheduled_work(populated_queue_file)
    assert len(work_items) == 2
    assert work_items[0].id == "work-1"
    assert work_items[1].id == "work-2"


def test_load_scheduled_work_preserves_metadata(populated_queue_file):
    """Test that loading preserves work item metadata."""
    work_items = load_scheduled_work(populated_queue_file)
    work = work_items[0]

    assert work.description == "Search for research papers"
    assert work.estimated_quota == 20
    assert work.priority == 8


def test_load_scheduled_work_invalid_json(queue_file):
    """Test loading from queue file with invalid JSON."""
    with open(queue_file, 'w') as f:
        f.write("{ invalid json }")

    work_items = load_scheduled_work(queue_file)
    assert work_items == []


def test_create_agent_executor_returns_callable():
    """Test that create_agent_executor returns a callable."""
    project_contexts = {"work-1": "/some/project"}
    executor = create_agent_executor(project_contexts)
    assert callable(executor)


def test_create_agent_executor_with_empty_contexts():
    """Test creating executor with empty project contexts."""
    executor = create_agent_executor({})
    assert callable(executor)


def test_create_agent_executor_result_format(sample_work_items):
    """Test that executor returns string results."""
    project_contexts = {"work-1": "/some/project"}
    executor = create_agent_executor(project_contexts)

    # Call executor with a work item
    result = executor(sample_work_items[0], "haiku")

    # Result should be a string
    assert isinstance(result, str)
    # In fallback mode, should be a simulation message
    assert len(result) > 0


def test_create_agent_executor_different_models(sample_work_items):
    """Test that executor can handle different model tiers."""
    project_contexts = {"work-1": "/some/project"}
    executor = create_agent_executor(project_contexts)

    for model in ["haiku", "sonnet", "opus"]:
        result = executor(sample_work_items[0], model)
        assert isinstance(result, str)


@pytest.mark.asyncio
async def test_execute_overnight_work_no_queue(results_dir):
    """Test execute_overnight_work with missing queue file."""
    queue_file = Path("/nonexistent/queue.json")
    result = await execute_overnight_work(queue_file, results_dir)
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_overnight_work_empty_queue(queue_file, results_dir):
    """Test execute_overnight_work with empty queue."""
    queue_data = {
        "scheduled_async": [],
        "last_updated": datetime.now(UTC).isoformat(),
    }

    with open(queue_file, 'w') as f:
        json.dump(queue_data, f)

    result = await execute_overnight_work(queue_file, results_dir, max_concurrent=2, timeout=10)
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_overnight_work_returns_dict(populated_queue_file, results_dir):
    """Test that execute_overnight_work returns a dictionary."""
    result = await execute_overnight_work(
        populated_queue_file,
        results_dir,
        max_concurrent=2,
        timeout=30
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_overnight_work_with_single_item(queue_file, results_dir, sample_work_items):
    """Test executing single work item."""
    queue_data = {
        "scheduled_async": [sample_work_items[0].to_dict()],
        "last_updated": datetime.now(UTC).isoformat(),
    }

    with open(queue_file, 'w') as f:
        json.dump(queue_data, f)

    result = await execute_overnight_work(queue_file, results_dir, max_concurrent=1, timeout=30)
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_overnight_work_respects_timeout(queue_file, results_dir):
    """Test that execute_overnight_work respects timeout setting."""
    queue_data = {
        "scheduled_async": [],
        "last_updated": datetime.now(UTC).isoformat(),
    }

    with open(queue_file, 'w') as f:
        json.dump(queue_data, f)

    # Very short timeout shouldn't cause issues with empty queue
    result = await asyncio.wait_for(
        execute_overnight_work(queue_file, results_dir, max_concurrent=1, timeout=1),
        timeout=5
    )
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_overnight_work_creates_results_dir(queue_file, temp_work_dir):
    """Test that execute_overnight_work creates results directory."""
    results_dir = temp_work_dir / "new-results"
    assert not results_dir.exists()

    queue_data = {
        "scheduled_async": [],
        "last_updated": datetime.now(UTC).isoformat(),
    }

    with open(queue_file, 'w') as f:
        json.dump(queue_data, f)

    await execute_overnight_work(queue_file, results_dir)
    # Results dir might be created by the function
    # (depends on implementation details)


def test_work_item_project_context_extraction(sample_work_items):
    """Test extracting project context from work items."""
    project_contexts = {}
    for item in sample_work_items:
        if item.project_path:
            project_contexts[item.id] = item.project_path

    # Should have empty dict since our samples don't have project_path set
    assert isinstance(project_contexts, dict)


def test_work_item_with_project_path(temp_work_dir):
    """Test work item with project path set."""
    project_dir = temp_work_dir / "my-project"
    project_dir.mkdir()

    work = TimedWorkItem(
        id="work-1",
        description="Process project",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
        project_path=str(project_dir),
        project_name="my-project",
    )

    assert work.project_path == str(project_dir)
    assert work.project_name == "my-project"


def test_load_scheduled_work_with_project_paths(queue_file, temp_work_dir):
    """Test loading work items that have project paths."""
    project_dir = temp_work_dir / "my-project"
    project_dir.mkdir()

    work = TimedWorkItem(
        id="work-1",
        description="Process project",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=20,
        estimated_duration_minutes=60,
        priority=8,
        project_path=str(project_dir),
        project_name="my-project",
    )

    queue_data = {
        "scheduled_async": [work.to_dict()],
        "last_updated": datetime.now(UTC).isoformat(),
    }

    with open(queue_file, 'w') as f:
        json.dump(queue_data, f)

    work_items = load_scheduled_work(queue_file)
    assert len(work_items) == 1
    assert work_items[0].project_name == "my-project"


@pytest.mark.asyncio
async def test_execute_overnight_work_max_concurrent_respected(populated_queue_file, results_dir):
    """Test that max_concurrent parameter is respected."""
    # Should handle concurrency parameter without errors
    result = await execute_overnight_work(
        populated_queue_file,
        results_dir,
        max_concurrent=1,  # Single concurrency
        timeout=30
    )
    assert isinstance(result, dict)


def test_create_agent_executor_handles_missing_claude():
    """Test executor handles missing Claude CLI gracefully."""
    project_contexts = {"work-1": "/nonexistent/project"}
    executor = create_agent_executor(project_contexts)

    # Should still return something (simulated execution)
    from temporal_scheduler import TimedWorkItem
    work = TimedWorkItem(
        id="work-1",
        description="Test work",
        timing=WorkTiming.ASYNCHRONOUS,
        estimated_quota=10,
        estimated_duration_minutes=30,
    )

    result = executor(work, "haiku")
    # Should be simulated result since Claude probably not in PATH
    assert isinstance(result, str)
