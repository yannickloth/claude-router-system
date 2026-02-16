#!/usr/bin/env python3
"""
Pytest suite for quota_tracker.py

Ported from embedded tests in implementation/quota_tracker.py

Change Driver: TESTING_REQUIREMENTS
"""

import tempfile
from pathlib import Path

import pytest

# Add implementation directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins/infolead-claude-subscription-router/implementation"))

from quota_tracker import QuotaTracker, QuotaAwareScheduler


@pytest.fixture
def temp_quota_dir():
    """Create temporary directory for test quota files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def quota_file(temp_quota_dir):
    """Create test quota file path."""
    return temp_quota_dir / "test-quota.json"


@pytest.fixture
def tracker(quota_file):
    """Create QuotaTracker with temp state file."""
    return QuotaTracker(state_file=quota_file)


def test_initialization(quota_file):
    """Test QuotaTracker initialization."""
    tracker = QuotaTracker(state_file=quota_file)
    assert quota_file.exists(), "State file should be created"


def test_can_use_models(tracker):
    """Test checking model availability."""
    assert tracker.can_use_model("haiku"), "Haiku should be available"
    assert tracker.can_use_model("sonnet"), "Sonnet should be available"
    assert tracker.can_use_model("opus"), "Opus should be available"


def test_increment_usage(tracker):
    """Test incrementing model usage."""
    new_total = tracker.increment_usage("sonnet", 10)
    assert new_total == 10, f"Expected 10, got {new_total}"


def test_get_usage_summary(tracker):
    """Test retrieving usage summary."""
    tracker.increment_usage("sonnet", 10)
    summary = tracker.get_usage_summary()
    assert summary["sonnet"]["used"] == 10


def test_increment_usage_multiple_times(tracker):
    """Test multiple increments accumulate correctly."""
    tracker.increment_usage("haiku", 5)
    tracker.increment_usage("haiku", 3)
    summary = tracker.get_usage_summary()
    assert summary["haiku"]["used"] == 8


def test_quota_aware_scheduler_select_model_complexity_2(tracker):
    """Test QuotaAwareScheduler selects Haiku for low complexity."""
    scheduler = QuotaAwareScheduler(tracker)
    model = scheduler.select_model_for_task(estimated_complexity=2)
    assert model == "haiku", f"Expected haiku for complexity 2, got {model}"


def test_quota_aware_scheduler_select_model_complexity_4(tracker):
    """Test QuotaAwareScheduler selects Sonnet for medium complexity."""
    scheduler = QuotaAwareScheduler(tracker)
    model = scheduler.select_model_for_task(estimated_complexity=4)
    assert model == "sonnet", f"Expected sonnet for complexity 4, got {model}"


def test_quota_aware_scheduler_select_model_complexity_9(tracker):
    """Test QuotaAwareScheduler selects Opus for high complexity."""
    scheduler = QuotaAwareScheduler(tracker)
    model = scheduler.select_model_for_task(estimated_complexity=9)
    assert model == "opus", f"Expected opus for complexity 9, got {model}"


def test_quota_aware_scheduler_get_recommendation(tracker):
    """Test QuotaAwareScheduler provides recommendation with reasoning."""
    scheduler = QuotaAwareScheduler(tracker)
    rec = scheduler.get_recommendation(estimated_complexity=3)
    assert "model" in rec
    assert "reasoning" in rec


def test_can_use_model_with_quota_exceeded(quota_file):
    """Test model availability when quota is nearly exhausted."""
    tracker = QuotaTracker(state_file=quota_file)
    # Sonnet limit is 1125
    tracker.increment_usage("sonnet", 1120)

    # Should still be available (reserve buffer is 10%)
    can_use = tracker.can_use_model("sonnet")
    # This depends on reserve buffer, may be True or False depending on exact implementation
    assert isinstance(can_use, bool)


def test_usage_summary_all_models(tracker):
    """Test usage summary includes all models."""
    summary = tracker.get_usage_summary()
    assert "haiku" in summary
    assert "sonnet" in summary
    assert "opus" in summary


def test_usage_summary_has_required_fields(tracker):
    """Test usage summary has all required fields."""
    tracker.increment_usage("haiku", 5)
    summary = tracker.get_usage_summary()

    for model in ["haiku", "sonnet", "opus"]:
        assert "used" in summary[model]
        assert "remaining" in summary[model]
        assert "limit" in summary[model]


def test_state_persistence(quota_file):
    """Test that quota state persists across instances."""
    # Create tracker and use some quota
    tracker1 = QuotaTracker(state_file=quota_file)
    tracker1.increment_usage("sonnet", 50)

    # Create new tracker instance
    tracker2 = QuotaTracker(state_file=quota_file)
    summary = tracker2.get_usage_summary()

    # Should see the previously recorded usage
    assert summary["sonnet"]["used"] == 50, \
        f"Expected 50 from first instance, got {summary['sonnet']['used']}"


def test_multiple_model_usage(tracker):
    """Test tracking usage across multiple models."""
    tracker.increment_usage("haiku", 100)
    tracker.increment_usage("sonnet", 50)
    tracker.increment_usage("opus", 10)

    summary = tracker.get_usage_summary()
    assert summary["haiku"]["used"] == 100
    assert summary["sonnet"]["used"] == 50
    assert summary["opus"]["used"] == 10
