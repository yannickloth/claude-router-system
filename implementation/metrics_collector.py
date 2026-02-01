"""
Metrics Collector - Track performance across all 8 solutions

Collects, aggregates, and visualizes metrics for the router system.

CLI Usage:
    # Record a metric
    python3 metrics_collector.py record haiku_routing escalation --value 1

    # Generate daily report
    python3 metrics_collector.py report daily

    # Generate weekly report
    python3 metrics_collector.py report weekly

    # Show specific solution metrics
    python3 metrics_collector.py show haiku_routing

Change Driver: MONITORING_REQUIREMENTS
Changes when: Metrics tracking needs evolve
"""

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Dict, List, Optional, Any


# Metrics storage directory
METRICS_DIR = Path.home() / ".claude" / "infolead-router" / "metrics"

# Metric retention (days)
RETENTION_DAYS = 90


@dataclass
class MetricRecord:
    """Individual metric record."""
    solution: str
    metric_name: str
    value: float
    timestamp: str
    metadata: Dict[str, Any]


@dataclass
class SolutionMetrics:
    """Aggregated metrics for a solution."""
    solution_name: str
    total_events: int
    metrics: Dict[str, float]
    status: str  # 'on_target', 'warning', 'critical'


class MetricsCollector:
    """Collect and analyze router system metrics."""

    def __init__(self, metrics_dir: Optional[Path] = None):
        """Initialize metrics collector.

        Args:
            metrics_dir: Directory for metric storage. Defaults to ~/.claude/infolead-router/metrics
        """
        self.metrics_dir = metrics_dir or METRICS_DIR
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # Metric targets by solution
        self.targets = {
            'haiku_routing': {
                'escalation_rate': (30, 40),  # Min, max percentage
                'false_negatives': (0, 2),    # Max count per week
            },
            'work_coordination': {
                'completion_rate': (90, 100),  # Min, max percentage
                'stall_rate': (0, 10),         # Min, max percentage
            },
            'domain_optimization': {
                'detection_accuracy': (95, 100),  # Min, max percentage
                'rule_enforcement': (100, 100),   # Must be 100%
            },
            'temporal_optimization': {
                'quota_utilization': (80, 90),    # Min, max percentage
            },
            'deduplication': {
                'cache_hit_rate': (40, 50),       # Min, max percentage
            },
            'probabilistic_routing': {
                'optimistic_success': (85, 100),  # Min, max percentage
            },
            'state_continuity': {
                'save_success': (98, 100),        # Min, max percentage
            },
            'context_ux': {
                'avg_response_time': (0, 5),      # Max seconds
                'signal_to_noise': (80, 100),     # Min, max percentage
            }
        }

    def record_metric(
        self,
        solution: str,
        metric_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a metric event.

        Args:
            solution: Solution identifier (e.g., 'haiku_routing')
            metric_name: Metric name (e.g., 'escalation')
            value: Metric value
            metadata: Optional additional context
        """
        record = MetricRecord(
            solution=solution,
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(UTC).isoformat(),
            metadata=metadata or {}
        )

        # Append to daily log file
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = self.metrics_dir / f"{today}.jsonl"

        with open(log_file, 'a') as f:
            json.dump(asdict(record), f)
            f.write('\n')

    def get_metrics(
        self,
        solution: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[MetricRecord]:
        """Retrieve metrics for a time period.

        Args:
            solution: Filter by solution (optional)
            start_date: Start of time range (optional)
            end_date: End of time range (optional)

        Returns:
            List of metric records
        """
        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=7)

        if end_date is None:
            end_date = datetime.now(UTC)

        records = []

        # Read all log files in date range
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            log_file = self.metrics_dir / f"{date_str}.jsonl"

            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            record = MetricRecord(**data)

                            # Filter by solution if specified
                            if solution is None or record.solution == solution:
                                records.append(record)

                        except (json.JSONDecodeError, TypeError):
                            continue

            current_date += timedelta(days=1)

        return records

    def aggregate_metrics(
        self,
        solution: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> SolutionMetrics:
        """Aggregate metrics for a solution.

        Args:
            solution: Solution identifier
            start_date: Start of time range (optional)
            end_date: End of time range (optional)

        Returns:
            Aggregated solution metrics
        """
        records = self.get_metrics(solution, start_date, end_date)

        if not records:
            return SolutionMetrics(
                solution_name=solution,
                total_events=0,
                metrics={},
                status='unknown'
            )

        # Aggregate by metric name
        aggregated = defaultdict(list)
        for record in records:
            aggregated[record.metric_name].append(record.value)

        # Calculate statistics
        metrics = {}
        for metric_name, values in aggregated.items():
            if len(values) > 0:
                metrics[f"{metric_name}_count"] = len(values)
                metrics[f"{metric_name}_avg"] = sum(values) / len(values)
                metrics[f"{metric_name}_total"] = sum(values)

        # Determine status
        status = self._assess_status(solution, metrics)

        return SolutionMetrics(
            solution_name=solution,
            total_events=len(records),
            metrics=metrics,
            status=status
        )

    def _assess_status(self, solution: str, metrics: Dict[str, float]) -> str:
        """Assess if metrics are on target.

        Args:
            solution: Solution identifier
            metrics: Aggregated metrics

        Returns:
            Status: 'on_target', 'warning', or 'critical'
        """
        if solution not in self.targets:
            return 'unknown'

        targets = self.targets[solution]
        statuses = []

        for target_name, (min_val, max_val) in targets.items():
            # Look for matching metric
            metric_key = f"{target_name}_avg"
            if metric_key in metrics:
                value = metrics[metric_key]

                if min_val <= value <= max_val:
                    statuses.append('on_target')
                elif abs(value - ((min_val + max_val) / 2)) < (max_val - min_val):
                    statuses.append('warning')
                else:
                    statuses.append('critical')

        if not statuses:
            return 'unknown'

        # Overall status is worst individual status
        if 'critical' in statuses:
            return 'critical'
        elif 'warning' in statuses:
            return 'warning'
        else:
            return 'on_target'

    def generate_daily_report(self) -> str:
        """Generate daily metrics report.

        Returns:
            Formatted report string
        """
        today = datetime.now(UTC)
        start = today - timedelta(days=1)

        report_lines = [
            "",
            "=" * 70,
            f"📊 Claude Router System - Daily Report ({today.strftime('%Y-%m-%d')})",
            "=" * 70,
            ""
        ]

        # Get metrics for each solution
        solutions = [
            ('haiku_routing', 'Solution 1: Haiku Routing'),
            ('work_coordination', 'Solution 2: Work Coordination'),
            ('domain_optimization', 'Solution 3: Domain Optimization'),
            ('temporal_optimization', 'Solution 4: Temporal Optimization'),
            ('deduplication', 'Solution 5: Deduplication'),
            ('probabilistic_routing', 'Solution 6: Probabilistic Routing'),
            ('state_continuity', 'Solution 7: State Continuity'),
            ('context_ux', 'Solution 8: Context UX'),
        ]

        for solution_id, solution_name in solutions:
            metrics = self.aggregate_metrics(solution_id, start, today)

            if metrics.total_events == 0:
                continue

            # Status indicator
            status_icon = {
                'on_target': '✓',
                'warning': '⚠️',
                'critical': '🔴',
                'unknown': '?'
            }.get(metrics.status, '?')

            report_lines.append(f"{solution_name}")
            report_lines.append(f"  Status: {status_icon} {metrics.status}")
            report_lines.append(f"  Events: {metrics.total_events}")

            # Show key metrics
            for key, value in sorted(metrics.metrics.items()):
                if key.endswith('_avg'):
                    metric_name = key.replace('_avg', '')
                    report_lines.append(f"  {metric_name}: {value:.1f}")

            report_lines.append("")

        report_lines.extend([
            "=" * 70,
            ""
        ])

        return "\n".join(report_lines)

    def generate_weekly_report(self) -> str:
        """Generate weekly metrics report with trends.

        Returns:
            Formatted report string
        """
        today = datetime.now(UTC)
        week_start = today - timedelta(days=7)

        report_lines = [
            "",
            "=" * 70,
            f"📊 Claude Router System - Weekly Report",
            f"   Week of {week_start.strftime('%Y-%m-%d')}",
            "=" * 70,
            ""
        ]

        # Solution 1: Haiku Routing
        haiku_metrics = self.aggregate_metrics('haiku_routing', week_start, today)
        if haiku_metrics.total_events > 0:
            report_lines.append("Solution 1: Haiku Routing")

            escalation_rate = haiku_metrics.metrics.get('escalation_avg', 0)
            target_min, target_max = self.targets['haiku_routing']['escalation_rate']
            status = '✓' if target_min <= escalation_rate <= target_max else '⚠️'

            report_lines.append(f"  Escalation rate: {escalation_rate:.1f}% {status}")
            report_lines.append(f"  Target: {target_min}-{target_max}%")

            if 'quota_saved_total' in haiku_metrics.metrics:
                saved = int(haiku_metrics.metrics['quota_saved_total'])
                report_lines.append(f"  Quota saved: {saved} messages")

            report_lines.append("")

        # Solution 2: Work Coordination
        work_metrics = self.aggregate_metrics('work_coordination', week_start, today)
        if work_metrics.total_events > 0:
            report_lines.append("Solution 2: Work Coordination")

            completion_rate = work_metrics.metrics.get('completion_rate_avg', 0)
            target_min, target_max = self.targets['work_coordination']['completion_rate']
            status = '✓' if completion_rate >= target_min else '⚠️'

            report_lines.append(f"  Completion rate: {completion_rate:.1f}% {status}")
            report_lines.append(f"  Target: >{target_min}%")

            if 'avg_wip_avg' in work_metrics.metrics:
                avg_wip = work_metrics.metrics['avg_wip_avg']
                report_lines.append(f"  Average WIP: {avg_wip:.1f} tasks")

            report_lines.append("")

        # Solution 5: Deduplication
        dedup_metrics = self.aggregate_metrics('deduplication', week_start, today)
        if dedup_metrics.total_events > 0:
            report_lines.append("Solution 5: Deduplication")

            hit_rate = dedup_metrics.metrics.get('cache_hit_rate_avg', 0)
            target_min, target_max = self.targets['deduplication']['cache_hit_rate']
            status = '✓' if target_min <= hit_rate <= target_max else '⚠️'

            report_lines.append(f"  Cache hit rate: {hit_rate:.1f}% {status}")
            report_lines.append(f"  Target: {target_min}-{target_max}%")

            if 'quota_saved_total' in dedup_metrics.metrics:
                saved = int(dedup_metrics.metrics['quota_saved_total'])
                report_lines.append(f"  Quota saved: {saved} messages")

            report_lines.append("")

        # Cumulative Impact
        report_lines.extend([
            "Cumulative Impact:",
            "  (Metrics tracked across all solutions)",
            ""
        ])

        # Calculate total quota savings
        total_saved = 0
        for solution_id, _ in [
            ('haiku_routing', ''),
            ('deduplication', ''),
            ('probabilistic_routing', '')
        ]:
            metrics = self.aggregate_metrics(solution_id, week_start, today)
            if 'quota_saved_total' in metrics.metrics:
                total_saved += int(metrics.metrics['quota_saved_total'])

        if total_saved > 0:
            report_lines.append(f"  Total quota saved: {total_saved:,} messages")

        report_lines.extend([
            "",
            "=" * 70,
            ""
        ])

        return "\n".join(report_lines)

    def cleanup_old_metrics(self) -> int:
        """Remove metrics older than retention period.

        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
        deleted = 0

        for log_file in self.metrics_dir.glob("*.jsonl"):
            try:
                # Parse date from filename
                date_str = log_file.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)

                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted += 1

            except (ValueError, OSError):
                continue

        return deleted


def main():
    """CLI interface for metrics collector."""
    if len(sys.argv) < 2:
        print("Usage: python3 metrics_collector.py <command> [args]")
        print("\nCommands:")
        print("  record <solution> <metric> --value <value>  - Record a metric")
        print("  report daily                                - Daily report")
        print("  report weekly                               - Weekly report")
        print("  show <solution>                             - Show solution metrics")
        print("  cleanup                                     - Remove old metrics")
        sys.exit(1)

    collector = MetricsCollector()
    command = sys.argv[1]

    if command == "record":
        if len(sys.argv) < 5:
            print("Usage: metrics_collector.py record <solution> <metric> --value <value>")
            sys.exit(1)

        solution = sys.argv[2]
        metric_name = sys.argv[3]

        # Parse --value flag
        value = None
        for i, arg in enumerate(sys.argv):
            if arg == "--value" and i + 1 < len(sys.argv):
                value = float(sys.argv[i + 1])
                break

        if value is None:
            print("Error: --value flag required")
            sys.exit(1)

        collector.record_metric(solution, metric_name, value)
        print(f"Recorded: {solution}.{metric_name} = {value}")

    elif command == "report":
        if len(sys.argv) < 3:
            print("Usage: metrics_collector.py report <daily|weekly>")
            sys.exit(1)

        report_type = sys.argv[2]

        if report_type == "daily":
            print(collector.generate_daily_report())
        elif report_type == "weekly":
            print(collector.generate_weekly_report())
        else:
            print(f"Unknown report type: {report_type}")
            sys.exit(1)

    elif command == "show":
        if len(sys.argv) < 3:
            print("Usage: metrics_collector.py show <solution>")
            sys.exit(1)

        solution = sys.argv[2]
        metrics = collector.aggregate_metrics(solution)

        print(f"\nMetrics for {solution}:")
        print(f"  Total events: {metrics.total_events}")
        print(f"  Status: {metrics.status}")
        print("\n  Metrics:")
        for key, value in sorted(metrics.metrics.items()):
            print(f"    {key}: {value:.2f}")

    elif command == "cleanup":
        deleted = collector.cleanup_old_metrics()
        print(f"Deleted {deleted} old metric files")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
