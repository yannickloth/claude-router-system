"""
Tests for metrics_collector module.

Tests metric recording, aggregation, and reporting.
"""

import json
import pytest
from datetime import datetime, timedelta, UTC
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from metrics_collector import (
    MetricsCollector,
    MetricRecord,
    SolutionMetrics,
    RETENTION_DAYS,
)


class TestMetricRecording:
    """Test recording individual metrics."""

    @pytest.fixture
    def collector(self, tmp_path):
        """Create collector with temp metrics dir."""
        return MetricsCollector(metrics_dir=tmp_path)

    def test_record_single_metric(self, collector, tmp_path):
        """Should record a single metric event."""
        collector.record_metric(
            solution="haiku_routing",
            metric_name="escalation",
            value=1.0,
            metadata={"agent": "test-agent"}
        )

        # Check file was created
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = tmp_path / f"{today}.jsonl"
        assert log_file.exists()

        # Check content
        with open(log_file) as f:
            record = json.loads(f.readline())
            assert record["solution"] == "haiku_routing"
            assert record["metric_name"] == "escalation"
            assert record["value"] == 1.0
            assert record["metadata"]["agent"] == "test-agent"

    def test_record_multiple_metrics(self, collector, tmp_path):
        """Should record multiple metrics to same file."""
        for i in range(5):
            collector.record_metric(
                solution="work_coordination",
                metric_name="completion",
                value=float(i)
            )

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = tmp_path / f"{today}.jsonl"

        with open(log_file) as f:
            lines = f.readlines()
            assert len(lines) == 5

    def test_record_metric_without_metadata(self, collector, tmp_path):
        """Should record metric without optional metadata."""
        collector.record_metric(
            solution="deduplication",
            metric_name="cache_hit",
            value=42.0
        )

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = tmp_path / f"{today}.jsonl"

        with open(log_file) as f:
            record = json.loads(f.readline())
            assert record["metadata"] == {}


class TestMetricRetrieval:
    """Test retrieving metrics."""

    @pytest.fixture
    def collector_with_data(self, tmp_path):
        """Create collector with pre-populated data."""
        collector = MetricsCollector(metrics_dir=tmp_path)

        # Add metrics for today
        for i in range(10):
            collector.record_metric(
                solution="haiku_routing",
                metric_name="escalation",
                value=float(i % 2)  # Alternating 0 and 1
            )

        for i in range(5):
            collector.record_metric(
                solution="work_coordination",
                metric_name="completion_rate",
                value=95.0 + i
            )

        return collector

    def test_get_all_metrics(self, collector_with_data):
        """Should retrieve all metrics."""
        records = collector_with_data.get_metrics()
        assert len(records) == 15

    def test_get_metrics_by_solution(self, collector_with_data):
        """Should filter metrics by solution."""
        records = collector_with_data.get_metrics(solution="haiku_routing")
        assert len(records) == 10
        assert all(r.solution == "haiku_routing" for r in records)

    def test_get_metrics_empty_result(self, collector_with_data):
        """Should return empty list for no matches."""
        records = collector_with_data.get_metrics(solution="nonexistent")
        assert len(records) == 0


class TestMetricAggregation:
    """Test metric aggregation."""

    @pytest.fixture
    def collector_with_data(self, tmp_path):
        """Create collector with varied data."""
        collector = MetricsCollector(metrics_dir=tmp_path)

        # Record escalation events (mix of 0s and 1s)
        for i in range(20):
            collector.record_metric(
                solution="haiku_routing",
                metric_name="escalation",
                value=1.0 if i < 7 else 0.0  # 35% escalation rate
            )

        return collector

    def test_aggregate_metrics(self, collector_with_data):
        """Should aggregate metrics correctly."""
        aggregated = collector_with_data.aggregate_metrics("haiku_routing")

        assert aggregated.solution_name == "haiku_routing"
        assert aggregated.total_events == 20
        assert "escalation_count" in aggregated.metrics
        assert aggregated.metrics["escalation_count"] == 20
        assert "escalation_avg" in aggregated.metrics
        assert abs(aggregated.metrics["escalation_avg"] - 0.35) < 0.01

    def test_aggregate_empty_solution(self, collector_with_data):
        """Should handle aggregation for empty solution."""
        aggregated = collector_with_data.aggregate_metrics("nonexistent")

        assert aggregated.total_events == 0
        assert aggregated.metrics == {}
        assert aggregated.status == "unknown"


class TestStatusAssessment:
    """Test status assessment against targets."""

    @pytest.fixture
    def collector(self, tmp_path):
        """Create collector with targets."""
        return MetricsCollector(metrics_dir=tmp_path)

    def test_on_target_status(self, collector):
        """Should return on_target when within range."""
        # Record metrics within target range (30-40%)
        for i in range(10):
            collector.record_metric(
                solution="haiku_routing",
                metric_name="escalation_rate",
                value=35.0  # Within 30-40% target
            )

        aggregated = collector.aggregate_metrics("haiku_routing")
        # Status depends on target configuration
        assert aggregated.status in ["on_target", "warning", "unknown"]

    def test_unknown_solution_status(self, collector):
        """Should return unknown for unconfigured solutions."""
        collector.record_metric(
            solution="custom_solution",
            metric_name="custom_metric",
            value=50.0
        )

        aggregated = collector.aggregate_metrics("custom_solution")
        assert aggregated.status == "unknown"


class TestReportGeneration:
    """Test report generation."""

    @pytest.fixture
    def collector_with_data(self, tmp_path):
        """Create collector with data for reports."""
        collector = MetricsCollector(metrics_dir=tmp_path)

        solutions = [
            ("haiku_routing", "escalation", 35.0),
            ("work_coordination", "completion_rate", 95.0),
            ("deduplication", "cache_hit_rate", 45.0),
        ]

        for solution, metric, value in solutions:
            for _ in range(5):
                collector.record_metric(solution, metric, value)

        return collector

    def test_daily_report_format(self, collector_with_data):
        """Should generate formatted daily report."""
        report = collector_with_data.generate_daily_report()

        assert "Daily Report" in report
        assert "=" in report  # Separator

    def test_weekly_report_format(self, collector_with_data):
        """Should generate formatted weekly report."""
        report = collector_with_data.generate_weekly_report()

        assert "Weekly Report" in report


class TestMetricCleanup:
    """Test old metric cleanup."""

    @pytest.fixture
    def collector_with_old_data(self, tmp_path):
        """Create collector with old metric files."""
        collector = MetricsCollector(metrics_dir=tmp_path)

        # Create old metric files
        old_date = datetime.now(UTC) - timedelta(days=RETENTION_DAYS + 10)
        for i in range(5):
            date_str = (old_date + timedelta(days=i)).strftime("%Y-%m-%d")
            old_file = tmp_path / f"{date_str}.jsonl"
            old_file.write_text('{"test": "data"}\n')

        # Create recent file
        recent_date = datetime.now(UTC).strftime("%Y-%m-%d")
        recent_file = tmp_path / f"{recent_date}.jsonl"
        recent_file.write_text('{"test": "recent"}\n')

        return collector

    def test_cleanup_old_metrics(self, collector_with_old_data, tmp_path):
        """Should remove metrics older than retention period."""
        # Count files before cleanup
        before_count = len(list(tmp_path.glob("*.jsonl")))
        assert before_count == 6  # 5 old + 1 recent

        # Run cleanup
        deleted = collector_with_old_data.cleanup_old_metrics()

        # Should delete old files
        assert deleted == 5

        # Only recent file should remain
        after_count = len(list(tmp_path.glob("*.jsonl")))
        assert after_count == 1


class TestTargetConfiguration:
    """Test target metric configuration."""

    def test_default_targets_exist(self):
        """Should have default targets for all solutions."""
        collector = MetricsCollector()

        expected_solutions = [
            "haiku_routing",
            "work_coordination",
            "domain_optimization",
            "temporal_optimization",
            "deduplication",
            "probabilistic_routing",
            "state_continuity",
            "context_ux",
        ]

        for solution in expected_solutions:
            assert solution in collector.targets, f"Missing targets for {solution}"

    def test_target_range_format(self):
        """Targets should be (min, max) tuples."""
        collector = MetricsCollector()

        for solution, metrics in collector.targets.items():
            for metric_name, target_range in metrics.items():
                assert len(target_range) == 2, (
                    f"{solution}.{metric_name} should have (min, max) tuple"
                )
                min_val, max_val = target_range
                assert min_val <= max_val, (
                    f"{solution}.{metric_name}: min ({min_val}) > max ({max_val})"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
