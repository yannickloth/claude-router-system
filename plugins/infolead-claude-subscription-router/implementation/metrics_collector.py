"""
Metrics Collector - Track performance across all 8 solutions

Collects, aggregates, and visualizes metrics for the router system.
Supports dual record types: raw agent_events from hooks and computed solution_metrics.

CLI Usage:
    # Record a solution metric
    python3 metrics_collector.py record haiku_routing escalation --value 1

    # Generate reports
    python3 metrics_collector.py report daily
    python3 metrics_collector.py report weekly

    # Compute solution metrics from agent events
    python3 metrics_collector.py compute

    # Show routing efficiency and cost savings
    python3 metrics_collector.py efficiency

    # Live dashboard
    python3 metrics_collector.py dashboard

    # Run tests
    python3 metrics_collector.py --test

Change Driver: MONITORING_REQUIREMENTS
Changes when: Metrics tracking needs evolve
"""

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Metrics storage directory
METRICS_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "metrics"

# State directories for module integration
STATE_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "state"
CACHE_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "cache"
MEMORY_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "memory"

# Metric retention (days)
RETENTION_DAYS = 90

# Cost ratios for efficiency calculation (relative units, not absolute $)
# Based on API pricing: Haiku is ~12x cheaper than Sonnet, Sonnet is ~5x cheaper than Opus
COST_RATIO = {
    'haiku': 1,
    'sonnet': 12,
    'opus': 60
}


@dataclass
class MetricRecord:
    """Individual solution metric record (computed/aggregated)."""
    solution: str
    metric_name: str
    value: float
    timestamp: str
    metadata: Dict[str, Any]


@dataclass
class AgentEvent:
    """Raw agent event from hooks."""
    record_type: str  # 'agent_event'
    event: str  # 'agent_stop'
    timestamp: str
    project: str
    agent_type: str
    agent_id: str
    model_tier: str  # 'haiku', 'sonnet', 'opus'
    exit_status: str
    description: str
    duration_ms: Optional[int]
    duration_sec: Optional[int]


@dataclass
class SolutionMetrics:
    """Aggregated metrics for a solution."""
    solution_name: str
    total_events: int
    metrics: Dict[str, float]
    status: str  # 'on_target', 'warning', 'critical', 'unknown'


@dataclass
class EfficiencyReport:
    """Cost efficiency analysis."""
    model_distribution: Dict[str, int]
    total_invocations: int
    actual_cost_units: int
    baseline_cost_units: int
    savings_units: int
    savings_percent: float
    baseline_model: str


class MetricsCollector:
    """Collect and analyze router system metrics."""

    def __init__(self, metrics_dir: Optional[Path] = None):
        """Initialize metrics collector.

        Args:
            metrics_dir: Directory for metric storage. Defaults to ~/.claude/infolead-claude-subscription-router/metrics
        """
        self.metrics_dir = metrics_dir or METRICS_DIR
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        # Metric targets by solution (min, max) - values outside range trigger warnings
        self.targets = {
            'haiku_routing': {
                'escalation_rate': (30, 40),  # % of requests escalated beyond haiku
            },
            'work_coordination': {
                'completion_rate': (90, 100),  # % of started tasks completed
            },
            'domain_optimization': {
                'detection_accuracy': (95, 100),  # % correct domain matches
            },
            'temporal_optimization': {
                'quota_utilization': (80, 90),  # % of available quota used
            },
            'deduplication': {
                'cache_hit_rate': (40, 50),  # % of requests served from cache
            },
            'probabilistic_routing': {
                'optimistic_success': (85, 100),  # % of haiku attempts that succeed
            },
            'state_continuity': {
                'save_success': (98, 100),  # % of state saves that succeed
            },
            'context_ux': {
                'avg_response_time': (0, 5),  # seconds (lower is better)
            }
        }

    # =========================================================================
    # Agent Event Methods (reading raw events from hooks)
    # =========================================================================

    def get_agent_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        project: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Read raw agent events from JSONL files.

        Args:
            start_date: Start of time range (default: 7 days ago)
            end_date: End of time range (default: now)
            project: Filter by project name (optional)

        Returns:
            List of agent event dictionaries
        """
        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now(UTC)

        events = []
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            log_file = self.metrics_dir / f"{date_str}.jsonl"

            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            # Check if this is an agent event (has 'event' field or record_type)
                            record_type = data.get('record_type', self._infer_record_type(data))
                            if record_type == 'agent_event':
                                # Filter by project if specified
                                if project is None or data.get('project') == project:
                                    events.append(data)
                        except json.JSONDecodeError:
                            continue

            current_date += timedelta(days=1)

        return events

    def _infer_record_type(self, data: Dict[str, Any]) -> str:
        """Infer record type for legacy data without record_type field.

        Args:
            data: Record data

        Returns:
            'agent_event', 'solution_metric', or 'unknown'
        """
        if 'event' in data and data.get('event') in ('agent_start', 'agent_stop'):
            return 'agent_event'
        elif 'solution' in data and 'metric_name' in data:
            return 'solution_metric'
        return 'unknown'

    # =========================================================================
    # Solution Metric Methods (recording and retrieving computed metrics)
    # =========================================================================

    def record_metric(
        self,
        solution: str,
        metric_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a solution metric.

        Args:
            solution: Solution identifier (e.g., 'haiku_routing')
            metric_name: Metric name (e.g., 'escalation_rate')
            value: Metric value
            metadata: Optional additional context
        """
        record = {
            'record_type': 'solution_metric',
            'solution': solution,
            'metric_name': metric_name,
            'value': value,
            'timestamp': datetime.now(UTC).isoformat(),
            'metadata': metadata or {}
        }

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = self.metrics_dir / f"{today}.jsonl"

        with open(log_file, 'a') as f:
            json.dump(record, f)
            f.write('\n')

    def get_metrics(
        self,
        solution: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[MetricRecord]:
        """Retrieve solution metrics for a time period.

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
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            log_file = self.metrics_dir / f"{date_str}.jsonl"

            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            record_type = data.get('record_type', self._infer_record_type(data))

                            if record_type == 'solution_metric':
                                record = MetricRecord(
                                    solution=data['solution'],
                                    metric_name=data['metric_name'],
                                    value=data['value'],
                                    timestamp=data['timestamp'],
                                    metadata=data.get('metadata', {})
                                )
                                if solution is None or record.solution == solution:
                                    records.append(record)

                        except (json.JSONDecodeError, KeyError, TypeError):
                            continue

            current_date += timedelta(days=1)

        return records

    # =========================================================================
    # Compute Methods (aggregate agent events into solution metrics)
    # =========================================================================

    def compute_all_solution_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, SolutionMetrics]:
        """Compute metrics for all 8 solutions from agent events and module state.

        Args:
            start_date: Start of time range
            end_date: End of time range

        Returns:
            Dictionary mapping solution ID to SolutionMetrics
        """
        events = self.get_agent_events(start_date, end_date)

        return {
            'haiku_routing': self._compute_haiku_routing(events),
            'work_coordination': self._compute_work_coordination(),
            'domain_optimization': self._compute_domain_optimization(events),
            'temporal_optimization': self._compute_temporal_optimization(),
            'deduplication': self._compute_deduplication(),
            'probabilistic_routing': self._compute_probabilistic_routing(),
            'state_continuity': self._compute_state_continuity(),
            'context_ux': self._compute_context_ux(events),
        }

    def _compute_haiku_routing(self, events: List[Dict]) -> SolutionMetrics:
        """Compute haiku routing metrics from agent events.

        Escalation rate = (sonnet + opus events) / total events * 100
        This represents what % of work was NOT handled by haiku.
        Target: 30-40% escalation (meaning 60-70% handled by haiku)
        """
        if not events:
            return SolutionMetrics(
                solution_name='haiku_routing',
                total_events=0,
                metrics={},
                status='unknown'
            )

        model_counts = Counter(e.get('model_tier', 'unknown') for e in events)
        total = sum(model_counts.values())

        haiku_count = model_counts.get('haiku', 0)
        sonnet_count = model_counts.get('sonnet', 0)
        opus_count = model_counts.get('opus', 0)

        # Escalation rate = % not handled by haiku
        escalation_rate = ((sonnet_count + opus_count) / total * 100) if total > 0 else 0

        # Calculate cost savings vs all-sonnet baseline
        actual_cost = sum(COST_RATIO.get(tier, 12) * count for tier, count in model_counts.items())
        baseline_cost = total * COST_RATIO['sonnet']
        savings = baseline_cost - actual_cost

        metrics = {
            'escalation_rate_avg': escalation_rate,
            'haiku_count': haiku_count,
            'sonnet_count': sonnet_count,
            'opus_count': opus_count,
            'quota_saved_total': savings,
        }

        status = self._assess_status('haiku_routing', metrics)

        return SolutionMetrics(
            solution_name='haiku_routing',
            total_events=total,
            metrics=metrics,
            status=status
        )

    def _compute_work_coordination(self) -> SolutionMetrics:
        """Compute work coordination metrics from work queue state."""
        state_file = STATE_DIR / "work-queue.json"

        if not state_file.exists():
            return SolutionMetrics(
                solution_name='work_coordination',
                total_events=0,
                metrics={},
                status='unknown'
            )

        try:
            with open(state_file) as f:
                data = json.load(f)

            # Count by status
            work_items = data.get('work_items', [])
            completed = sum(1 for w in work_items if w.get('status') == 'completed')
            failed = sum(1 for w in work_items if w.get('status') == 'failed')
            active = sum(1 for w in work_items if w.get('status') == 'active')
            queued = sum(1 for w in work_items if w.get('status') == 'queued')

            total_finished = completed + failed
            completion_rate = (completed / total_finished * 100) if total_finished > 0 else 100

            metrics = {
                'completion_rate_avg': completion_rate,
                'completed_count': completed,
                'failed_count': failed,
                'active_count': active,
                'queued_count': queued,
            }

            status = self._assess_status('work_coordination', metrics)

            return SolutionMetrics(
                solution_name='work_coordination',
                total_events=len(work_items),
                metrics=metrics,
                status=status
            )

        except (json.JSONDecodeError, IOError):
            return SolutionMetrics(
                solution_name='work_coordination',
                total_events=0,
                metrics={},
                status='unknown'
            )

    def _compute_domain_optimization(self, events: List[Dict]) -> SolutionMetrics:
        """Compute domain optimization metrics.

        Detection accuracy is estimated from agent type distribution per project.
        """
        if not events:
            return SolutionMetrics(
                solution_name='domain_optimization',
                total_events=0,
                metrics={},
                status='unknown'
            )

        # Group by project
        projects = defaultdict(list)
        for e in events:
            project = e.get('project', 'unknown')
            projects[project].append(e)

        # For now, assume 100% detection accuracy (domain rules are enforced by config)
        # This would need actual tracking of rule matches vs misses
        metrics = {
            'detection_accuracy_avg': 100.0,
            'projects_tracked': len(projects),
        }

        status = self._assess_status('domain_optimization', metrics)

        return SolutionMetrics(
            solution_name='domain_optimization',
            total_events=len(events),
            metrics=metrics,
            status=status
        )

    def _compute_temporal_optimization(self) -> SolutionMetrics:
        """Compute temporal optimization metrics from quota tracker state."""
        state_file = STATE_DIR / "quota-tracking.json"

        if not state_file.exists():
            return SolutionMetrics(
                solution_name='temporal_optimization',
                total_events=0,
                metrics={},
                status='unknown'
            )

        try:
            with open(state_file) as f:
                data = json.load(f)

            # Calculate utilization from today's quota
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            today_usage = data.get('daily_usage', {}).get(today, {})

            sonnet_used = today_usage.get('sonnet', 0)
            opus_used = today_usage.get('opus', 0)

            # Default quotas (from subscription model)
            sonnet_quota = 1125
            opus_quota = 250

            sonnet_util = (sonnet_used / sonnet_quota * 100) if sonnet_quota > 0 else 0
            opus_util = (opus_used / opus_quota * 100) if opus_quota > 0 else 0

            # Combined utilization (weighted by relative value)
            quota_utilization = (sonnet_util + opus_util) / 2

            metrics = {
                'quota_utilization_avg': quota_utilization,
                'sonnet_used': sonnet_used,
                'opus_used': opus_used,
            }

            status = self._assess_status('temporal_optimization', metrics)

            return SolutionMetrics(
                solution_name='temporal_optimization',
                total_events=sonnet_used + opus_used,
                metrics=metrics,
                status=status
            )

        except (json.JSONDecodeError, IOError):
            return SolutionMetrics(
                solution_name='temporal_optimization',
                total_events=0,
                metrics={},
                status='unknown'
            )

    def _compute_deduplication(self) -> SolutionMetrics:
        """Compute deduplication metrics from semantic cache."""
        cache_file = CACHE_DIR / "semantic-cache.json"

        if not cache_file.exists():
            return SolutionMetrics(
                solution_name='deduplication',
                total_events=0,
                metrics={},
                status='unknown'
            )

        try:
            with open(cache_file) as f:
                data = json.load(f)

            entries = data.get('entries', [])
            total_hits = sum(e.get('hit_count', 0) for e in entries)
            total_entries = len(entries)

            # Hit rate = hits / (hits + entries) - each entry was a miss initially
            total_requests = total_hits + total_entries
            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

            # Quota saved = hits * avg_quota_cost
            avg_cost = sum(e.get('quota_cost', 1) for e in entries) / total_entries if total_entries > 0 else 1
            quota_saved = int(total_hits * avg_cost)

            metrics = {
                'cache_hit_rate_avg': hit_rate,
                'total_hits': total_hits,
                'total_entries': total_entries,
                'quota_saved_total': quota_saved,
            }

            status = self._assess_status('deduplication', metrics)

            return SolutionMetrics(
                solution_name='deduplication',
                total_events=total_requests,
                metrics=metrics,
                status=status
            )

        except (json.JSONDecodeError, IOError):
            return SolutionMetrics(
                solution_name='deduplication',
                total_events=0,
                metrics={},
                status='unknown'
            )

    def _compute_probabilistic_routing(self) -> SolutionMetrics:
        """Compute probabilistic routing metrics from routing history."""
        state_file = STATE_DIR / "routing-history.json"

        if not state_file.exists():
            return SolutionMetrics(
                solution_name='probabilistic_routing',
                total_events=0,
                metrics={},
                status='unknown'
            )

        try:
            with open(state_file) as f:
                data = json.load(f)

            # Get haiku success stats
            success_history = data.get('success_history', {})
            haiku_stats = success_history.get('haiku', {})

            total_attempts = 0
            total_successes = 0

            for task_type, counts in haiku_stats.items():
                total_attempts += counts.get('attempts', 0)
                total_successes += counts.get('successes', 0)

            success_rate = (total_successes / total_attempts * 100) if total_attempts > 0 else 0

            metrics = {
                'optimistic_success_avg': success_rate,
                'haiku_attempts': total_attempts,
                'haiku_successes': total_successes,
            }

            status = self._assess_status('probabilistic_routing', metrics)

            return SolutionMetrics(
                solution_name='probabilistic_routing',
                total_events=total_attempts,
                metrics=metrics,
                status=status
            )

        except (json.JSONDecodeError, IOError):
            return SolutionMetrics(
                solution_name='probabilistic_routing',
                total_events=0,
                metrics={},
                status='unknown'
            )

    def _compute_state_continuity(self) -> SolutionMetrics:
        """Compute state continuity metrics from memory files."""
        # Check if key state files exist and are valid
        state_files = [
            MEMORY_DIR / "session-state.json",
            MEMORY_DIR / "search-history.json",
            MEMORY_DIR / "decisions.json",
        ]

        valid_files = 0
        total_files = len(state_files)

        for f in state_files:
            if f.exists():
                try:
                    with open(f) as fp:
                        json.load(fp)
                    valid_files += 1
                except (json.JSONDecodeError, IOError):
                    pass

        save_success = (valid_files / total_files * 100) if total_files > 0 else 0

        metrics = {
            'save_success_avg': save_success,
            'valid_files': valid_files,
            'total_files': total_files,
        }

        status = self._assess_status('state_continuity', metrics)

        return SolutionMetrics(
            solution_name='state_continuity',
            total_events=total_files,
            metrics=metrics,
            status=status
        )

    def _compute_context_ux(self, events: List[Dict]) -> SolutionMetrics:
        """Compute context UX metrics from agent event durations."""
        if not events:
            return SolutionMetrics(
                solution_name='context_ux',
                total_events=0,
                metrics={},
                status='unknown'
            )

        # Get durations
        durations = [e.get('duration_sec') for e in events if e.get('duration_sec') is not None]

        if not durations:
            return SolutionMetrics(
                solution_name='context_ux',
                total_events=len(events),
                metrics={},
                status='unknown'
            )

        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        metrics = {
            'avg_response_time_avg': avg_duration,
            'max_response_time': max_duration,
            'min_response_time': min_duration,
            'samples': len(durations),
        }

        status = self._assess_status('context_ux', metrics)

        return SolutionMetrics(
            solution_name='context_ux',
            total_events=len(events),
            metrics=metrics,
            status=status
        )

    # =========================================================================
    # Efficiency Calculation
    # =========================================================================

    def calculate_routing_efficiency(
        self,
        events: Optional[List[Dict]] = None,
        baseline: str = 'sonnet'
    ) -> EfficiencyReport:
        """Calculate cost savings vs baseline (no routing).

        Args:
            events: Agent events (default: last 7 days)
            baseline: Model to compare against (default: sonnet)

        Returns:
            EfficiencyReport with cost analysis
        """
        if events is None:
            events = self.get_agent_events()

        if not events:
            return EfficiencyReport(
                model_distribution={},
                total_invocations=0,
                actual_cost_units=0,
                baseline_cost_units=0,
                savings_units=0,
                savings_percent=0.0,
                baseline_model=baseline
            )

        model_counts = Counter(e.get('model_tier', 'unknown') for e in events)
        total = sum(model_counts.values())

        actual_cost = sum(COST_RATIO.get(tier, COST_RATIO['sonnet']) * count
                         for tier, count in model_counts.items())
        baseline_cost = total * COST_RATIO.get(baseline, COST_RATIO['sonnet'])

        savings = baseline_cost - actual_cost
        savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

        return EfficiencyReport(
            model_distribution=dict(model_counts),
            total_invocations=total,
            actual_cost_units=actual_cost,
            baseline_cost_units=baseline_cost,
            savings_units=savings,
            savings_percent=savings_percent,
            baseline_model=baseline
        )

    # =========================================================================
    # Status Assessment
    # =========================================================================

    def _assess_status(self, solution: str, metrics: Dict[str, float]) -> str:
        """Assess if metrics are on target.

        Args:
            solution: Solution identifier
            metrics: Computed metrics

        Returns:
            Status: 'on_target', 'warning', or 'critical'
        """
        if solution not in self.targets:
            return 'unknown'

        targets = self.targets[solution]
        statuses = []

        for target_name, (min_val, max_val) in targets.items():
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

        if 'critical' in statuses:
            return 'critical'
        elif 'warning' in statuses:
            return 'warning'
        else:
            return 'on_target'

    def aggregate_metrics(
        self,
        solution: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> SolutionMetrics:
        """Aggregate recorded solution metrics.

        Args:
            solution: Solution identifier
            start_date: Start of time range
            end_date: End of time range

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

        aggregated = defaultdict(list)
        for record in records:
            aggregated[record.metric_name].append(record.value)

        metrics = {}
        for metric_name, values in aggregated.items():
            if len(values) > 0:
                metrics[f"{metric_name}_count"] = len(values)
                metrics[f"{metric_name}_avg"] = sum(values) / len(values)
                metrics[f"{metric_name}_total"] = sum(values)

        status = self._assess_status(solution, metrics)

        return SolutionMetrics(
            solution_name=solution,
            total_events=len(records),
            metrics=metrics,
            status=status
        )

    # =========================================================================
    # Report Generation
    # =========================================================================

    def generate_daily_report(self) -> str:
        """Generate daily metrics report with computed solution metrics."""
        today = datetime.now(UTC)
        start = today - timedelta(days=1)

        # Compute metrics from events
        computed = self.compute_all_solution_metrics(start, today)

        report_lines = [
            "",
            "=" * 70,
            f"  Claude Router System - Daily Report ({today.strftime('%Y-%m-%d')})",
            "=" * 70,
            ""
        ]

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
            metrics = computed.get(solution_id)
            if not metrics or metrics.total_events == 0:
                continue

            status_icon = {
                'on_target': '[OK]',
                'warning': '[WARN]',
                'critical': '[CRIT]',
                'unknown': '[--]'
            }.get(metrics.status, '[--]')

            report_lines.append(f"{solution_name} {status_icon}")
            report_lines.append(f"  Events: {metrics.total_events}")

            # Show key metrics
            for key, value in sorted(metrics.metrics.items()):
                if key.endswith('_avg') or key.endswith('_total'):
                    display_name = key.replace('_avg', '').replace('_total', ' (total)')
                    if isinstance(value, float):
                        report_lines.append(f"  {display_name}: {value:.1f}")
                    else:
                        report_lines.append(f"  {display_name}: {value}")

            report_lines.append("")

        # Add efficiency summary
        efficiency = self.calculate_routing_efficiency(
            self.get_agent_events(start, today)
        )

        if efficiency.total_invocations > 0:
            report_lines.extend([
                "Efficiency Summary:",
                f"  Total invocations: {efficiency.total_invocations}",
                f"  Model distribution: {efficiency.model_distribution}",
                f"  Cost savings: {efficiency.savings_percent:.1f}% vs all-{efficiency.baseline_model}",
                ""
            ])

        report_lines.extend(["=" * 70, ""])

        return "\n".join(report_lines)

    def generate_weekly_report(self) -> str:
        """Generate weekly metrics report with trends."""
        today = datetime.now(UTC)
        week_start = today - timedelta(days=7)

        # Compute metrics from events
        computed = self.compute_all_solution_metrics(week_start, today)

        report_lines = [
            "",
            "=" * 70,
            f"  Claude Router System - Weekly Report",
            f"  Week of {week_start.strftime('%Y-%m-%d')}",
            "=" * 70,
            ""
        ]

        # Solution 1: Haiku Routing
        haiku = computed.get('haiku_routing')
        if haiku and haiku.total_events > 0:
            escalation_rate = haiku.metrics.get('escalation_rate_avg', 0)
            target_min, target_max = self.targets['haiku_routing']['escalation_rate']
            status = '[OK]' if target_min <= escalation_rate <= target_max else '[WARN]'

            report_lines.append(f"Solution 1: Haiku Routing {status}")
            report_lines.append(f"  Escalation rate: {escalation_rate:.1f}% (target: {target_min}-{target_max}%)")
            report_lines.append(f"  Haiku: {haiku.metrics.get('haiku_count', 0)}, "
                              f"Sonnet: {haiku.metrics.get('sonnet_count', 0)}, "
                              f"Opus: {haiku.metrics.get('opus_count', 0)}")
            if 'quota_saved_total' in haiku.metrics:
                report_lines.append(f"  Cost units saved: {int(haiku.metrics['quota_saved_total'])}")
            report_lines.append("")

        # Solution 2: Work Coordination
        work = computed.get('work_coordination')
        if work and work.total_events > 0:
            completion_rate = work.metrics.get('completion_rate_avg', 0)
            target_min, _ = self.targets['work_coordination']['completion_rate']
            status = '[OK]' if completion_rate >= target_min else '[WARN]'

            report_lines.append(f"Solution 2: Work Coordination {status}")
            report_lines.append(f"  Completion rate: {completion_rate:.1f}% (target: >{target_min}%)")
            report_lines.append(f"  Completed: {int(work.metrics.get('completed_count', 0))}, "
                              f"Failed: {int(work.metrics.get('failed_count', 0))}")
            report_lines.append("")

        # Solution 5: Deduplication
        dedup = computed.get('deduplication')
        if dedup and dedup.total_events > 0:
            hit_rate = dedup.metrics.get('cache_hit_rate_avg', 0)
            target_min, target_max = self.targets['deduplication']['cache_hit_rate']
            status = '[OK]' if target_min <= hit_rate <= target_max else '[WARN]'

            report_lines.append(f"Solution 5: Deduplication {status}")
            report_lines.append(f"  Cache hit rate: {hit_rate:.1f}% (target: {target_min}-{target_max}%)")
            if 'quota_saved_total' in dedup.metrics:
                report_lines.append(f"  Quota saved: {int(dedup.metrics['quota_saved_total'])} messages")
            report_lines.append("")

        # Solution 8: Context UX
        ux = computed.get('context_ux')
        if ux and ux.total_events > 0:
            avg_time = ux.metrics.get('avg_response_time_avg', 0)
            _, target_max = self.targets['context_ux']['avg_response_time']
            status = '[OK]' if avg_time <= target_max else '[WARN]'

            report_lines.append(f"Solution 8: Context UX {status}")
            report_lines.append(f"  Avg response time: {avg_time:.1f}s (target: <{target_max}s)")
            report_lines.append("")

        # Cumulative efficiency
        efficiency = self.calculate_routing_efficiency(
            self.get_agent_events(week_start, today)
        )

        report_lines.extend([
            "Cumulative Impact:",
            f"  Total agent invocations: {efficiency.total_invocations}",
            f"  Model distribution: {efficiency.model_distribution}",
            f"  Cost savings: {efficiency.savings_percent:.1f}% vs all-{efficiency.baseline_model}",
            f"  Savings in cost units: {efficiency.savings_units}",
            "",
            "=" * 70,
            ""
        ])

        return "\n".join(report_lines)

    def cleanup_old_metrics(self) -> int:
        """Remove metrics older than retention period."""
        cutoff_date = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
        deleted = 0

        for log_file in self.metrics_dir.glob("*.jsonl"):
            try:
                date_str = log_file.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)

                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted += 1

            except (ValueError, OSError):
                continue

        return deleted


# =============================================================================
# Display Functions
# =============================================================================

def display_live_dashboard(collector: MetricsCollector) -> None:
    """Display live metrics dashboard with computed solution metrics."""
    today = datetime.now(UTC)
    week_start = today - timedelta(days=7)

    # Compute all solution metrics
    computed = collector.compute_all_solution_metrics(week_start, today)

    print()
    print("=" * 70)
    print("  CLAUDE ROUTER SYSTEM - LIVE DASHBOARD")
    print(f"  {today.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)
    print()

    solutions = [
        ('haiku_routing', 'Haiku Routing', 'escalation_rate'),
        ('work_coordination', 'Work Coordination', 'completion_rate'),
        ('domain_optimization', 'Domain Optimization', 'detection_accuracy'),
        ('temporal_optimization', 'Temporal Optimization', 'quota_utilization'),
        ('deduplication', 'Deduplication', 'cache_hit_rate'),
        ('probabilistic_routing', 'Probabilistic Routing', 'optimistic_success'),
        ('state_continuity', 'State Continuity', 'save_success'),
        ('context_ux', 'Context UX', 'avg_response_time'),
    ]

    print(f"{'Solution':<25} {'Status':<10} {'Key Metric':<20} {'Events':<10}")
    print("-" * 70)

    total_events = 0

    for solution_id, solution_name, key_metric in solutions:
        metrics = computed.get(solution_id)
        if not metrics:
            continue

        status_display = {
            'on_target': '[OK]',
            'warning': '[WARN]',
            'critical': '[CRIT]',
            'unknown': '[--]'
        }.get(metrics.status, '[--]')

        metric_value = metrics.metrics.get(f"{key_metric}_avg", 0)
        if key_metric == 'avg_response_time':
            metric_display = f"{metric_value:.1f}s" if metric_value > 0 else "N/A"
        else:
            metric_display = f"{metric_value:.1f}%" if metric_value > 0 else "N/A"

        print(f"{solution_name:<25} {status_display:<10} {metric_display:<20} {metrics.total_events:<10}")
        total_events += metrics.total_events

    print("-" * 70)
    print(f"{'TOTAL':<25} {'':<10} {'':<20} {total_events:<10}")

    # Efficiency summary
    efficiency = collector.calculate_routing_efficiency(
        collector.get_agent_events(week_start, today)
    )

    if efficiency.total_invocations > 0:
        print()
        print(f"Cost Savings: {efficiency.savings_percent:.1f}% vs all-{efficiency.baseline_model}")
        print(f"Model Mix: H:{efficiency.model_distribution.get('haiku', 0)} "
              f"S:{efficiency.model_distribution.get('sonnet', 0)} "
              f"O:{efficiency.model_distribution.get('opus', 0)}")

    # Health check
    print()
    print("Health Check:")
    critical_count = sum(1 for m in computed.values() if m.status == 'critical')
    warning_count = sum(1 for m in computed.values() if m.status == 'warning')

    if critical_count > 0:
        print(f"  {critical_count} solution(s) in CRITICAL state")
    if warning_count > 0:
        print(f"  {warning_count} solution(s) in WARNING state")
    if critical_count == 0 and warning_count == 0:
        print("  All solutions operating normally or no data")

    print()
    print("=" * 70)


def display_efficiency(collector: MetricsCollector) -> None:
    """Display detailed efficiency analysis."""
    today = datetime.now(UTC)
    week_start = today - timedelta(days=7)

    events = collector.get_agent_events(week_start, today)
    efficiency = collector.calculate_routing_efficiency(events)

    print()
    print("=" * 70)
    print("  ROUTING EFFICIENCY ANALYSIS")
    print(f"  Last 7 days ({week_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')})")
    print("=" * 70)
    print()

    if efficiency.total_invocations == 0:
        print("No agent events recorded in this period.")
        print()
        return

    print("Model Distribution:")
    print("-" * 40)
    total = efficiency.total_invocations

    for model in ['haiku', 'sonnet', 'opus']:
        count = efficiency.model_distribution.get(model, 0)
        pct = (count / total * 100) if total > 0 else 0
        bar = '#' * int(pct / 2)
        print(f"  {model:>8}: {count:>5} ({pct:>5.1f}%) {bar}")

    unknown = efficiency.model_distribution.get('unknown', 0)
    if unknown > 0:
        pct = (unknown / total * 100)
        print(f"  {'unknown':>8}: {unknown:>5} ({pct:>5.1f}%)")

    print()
    print("Cost Analysis:")
    print("-" * 40)
    print(f"  Baseline ({efficiency.baseline_model}): {efficiency.baseline_cost_units} cost units")
    print(f"  Actual (with routing):  {efficiency.actual_cost_units} cost units")
    print(f"  Savings:                {efficiency.savings_units} cost units ({efficiency.savings_percent:.1f}%)")
    print()
    print(f"  Cost ratios used: haiku={COST_RATIO['haiku']}, sonnet={COST_RATIO['sonnet']}, opus={COST_RATIO['opus']}")
    print()

    # Interpretation
    print("Interpretation:")
    print("-" * 40)
    haiku_pct = efficiency.model_distribution.get('haiku', 0) / total * 100 if total > 0 else 0

    if haiku_pct >= 60:
        print(f"  [OK] Haiku handles {haiku_pct:.1f}% of work (target: 60-70%)")
    elif haiku_pct >= 50:
        print(f"  [WARN] Haiku handles {haiku_pct:.1f}% of work (below 60% target)")
    else:
        print(f"  [CRIT] Haiku handles only {haiku_pct:.1f}% of work (well below target)")

    if efficiency.savings_percent >= 50:
        print(f"  [OK] Cost savings of {efficiency.savings_percent:.1f}% (target: >50%)")
    elif efficiency.savings_percent >= 30:
        print(f"  [WARN] Cost savings of {efficiency.savings_percent:.1f}% (below 50% target)")
    else:
        print(f"  [CRIT] Cost savings of only {efficiency.savings_percent:.1f}% (needs improvement)")

    print()
    print("=" * 70)


def display_work_dashboard(work_file: Optional[Path] = None) -> None:
    """Display work coordination dashboard (Kanban-style)."""
    work_file = work_file or (STATE_DIR / "work-queue.json")

    print()
    print("=" * 70)
    print("  WORK COORDINATION DASHBOARD")
    print("=" * 70)
    print()

    if not work_file.exists():
        print("No active work queue.")
        print()
        return

    try:
        with open(work_file) as f:
            work_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        print("Could not read work queue.")
        print()
        return

    work_items = work_data.get('work_items', [])

    # Group by status
    queued = [w for w in work_items if w.get('status') == 'queued']
    active = [w for w in work_items if w.get('status') == 'active']
    completed = [w for w in work_items if w.get('status') == 'completed']
    failed = [w for w in work_items if w.get('status') == 'failed']

    print(f"QUEUED ({len(queued)})")
    print("-" * 30)
    for work in queued[:5]:
        priority = work.get('priority', 5)
        desc = work.get('description', 'Unknown')[:40]
        print(f"  [{priority}] {desc}")
    if len(queued) > 5:
        print(f"  ... and {len(queued) - 5} more")
    print()

    print(f"ACTIVE ({len(active)})")
    print("-" * 30)
    for work in active:
        agent = work.get('agent_assigned', 'unknown')
        desc = work.get('description', 'Unknown')[:40]
        print(f"  [{agent}] {desc}")
    print()

    print(f"COMPLETED ({len(completed)})")
    print("-" * 30)
    for work in completed[-5:]:
        desc = work.get('description', 'Unknown')[:40]
        print(f"  {desc}")
    print()

    if failed:
        print(f"FAILED ({len(failed)})")
        print("-" * 30)
        for work in failed[-3:]:
            desc = work.get('description', 'Unknown')[:40]
            err = work.get('error_message', '')[:30]
            print(f"  {desc} - {err}")
        print()

    print("=" * 70)


# =============================================================================
# Tests
# =============================================================================

def test_metrics_collector() -> None:
    """Comprehensive tests for metrics collector functionality."""
    import tempfile

    print("Testing metrics collector...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        collector = MetricsCollector(metrics_dir=tmpdir)

        # Test 1: Record solution metric
        print("Test 1: Record solution metric")
        collector.record_metric(
            solution="haiku_routing",
            metric_name="escalation_rate",
            value=35.0,
            metadata={"reason": "test"}
        )
        print("  OK")

        # Test 2: Retrieve solution metrics
        print("Test 2: Retrieve solution metrics")
        records = collector.get_metrics(solution="haiku_routing")
        assert len(records) >= 1, "Should have at least 1 record"
        assert records[0].solution == "haiku_routing"
        assert records[0].metric_name == "escalation_rate"
        assert records[0].value == 35.0
        print("  OK")

        # Test 3: Infer record type
        print("Test 3: Infer record type")
        agent_event = {'event': 'agent_stop', 'model_tier': 'haiku'}
        solution_metric = {'solution': 'haiku_routing', 'metric_name': 'test', 'value': 1}
        assert collector._infer_record_type(agent_event) == 'agent_event'
        assert collector._infer_record_type(solution_metric) == 'solution_metric'
        print("  OK")

        # Test 4: Write and read agent events
        print("Test 4: Agent event handling")
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = tmpdir / f"{today}.jsonl"

        # Write a test agent event
        test_event = {
            'record_type': 'agent_event',
            'event': 'agent_stop',
            'timestamp': datetime.now(UTC).isoformat(),
            'project': 'test-project',
            'agent_type': 'haiku-general',
            'agent_id': 'test123',
            'model_tier': 'haiku',
            'exit_status': 'success',
            'description': 'test task',
            'duration_ms': 1000,
            'duration_sec': 1
        }
        with open(log_file, 'a') as f:
            json.dump(test_event, f)
            f.write('\n')

        events = collector.get_agent_events()
        assert len(events) >= 1, "Should have at least 1 event"
        assert events[-1]['model_tier'] == 'haiku'
        print("  OK")

        # Test 5: Compute haiku routing metrics
        print("Test 5: Compute haiku routing metrics")
        # Add more events for better stats
        for model in ['haiku', 'haiku', 'haiku', 'sonnet', 'opus']:
            event = dict(test_event)
            event['model_tier'] = model
            event['agent_id'] = f'test-{model}'
            with open(log_file, 'a') as f:
                json.dump(event, f)
                f.write('\n')

        haiku_metrics = collector._compute_haiku_routing(collector.get_agent_events())
        assert haiku_metrics.total_events >= 5
        assert 'escalation_rate_avg' in haiku_metrics.metrics
        print(f"  Escalation rate: {haiku_metrics.metrics['escalation_rate_avg']:.1f}%")
        print("  OK")

        # Test 6: Calculate efficiency
        print("Test 6: Calculate routing efficiency")
        efficiency = collector.calculate_routing_efficiency()
        assert efficiency.total_invocations > 0
        assert 'haiku' in efficiency.model_distribution
        print(f"  Savings: {efficiency.savings_percent:.1f}%")
        print("  OK")

        # Test 7: Status assessment
        print("Test 7: Status assessment")
        metrics_on_target = {'escalation_rate_avg': 35.0}  # Within 30-40%
        metrics_warning = {'escalation_rate_avg': 25.0}    # Below 30%
        metrics_critical = {'escalation_rate_avg': 10.0}   # Way below

        assert collector._assess_status('haiku_routing', metrics_on_target) == 'on_target'
        assert collector._assess_status('haiku_routing', metrics_warning) in ['warning', 'critical']
        print("  OK")

        # Test 8: Daily report
        print("Test 8: Daily report generation")
        report = collector.generate_daily_report()
        assert "Claude Router System" in report
        assert "Daily Report" in report
        print("  OK")

        # Test 9: Weekly report
        print("Test 9: Weekly report generation")
        report = collector.generate_weekly_report()
        assert "Weekly Report" in report
        print("  OK")

        # Test 10: Compute all solutions
        print("Test 10: Compute all solution metrics")
        all_metrics = collector.compute_all_solution_metrics()
        assert 'haiku_routing' in all_metrics
        assert 'work_coordination' in all_metrics
        assert 'deduplication' in all_metrics
        assert 'context_ux' in all_metrics
        print(f"  Computed {len(all_metrics)} solutions")
        print("  OK")

        # Test 11: Cleanup
        print("Test 11: Cleanup old metrics")
        old_date = (datetime.now(UTC) - timedelta(days=RETENTION_DAYS + 10)).strftime("%Y-%m-%d")
        old_file = tmpdir / f"{old_date}.jsonl"
        old_file.write_text('{"record_type": "agent_event", "event": "agent_stop"}\n')

        deleted = collector.cleanup_old_metrics()
        assert deleted >= 1, "Should delete old file"
        assert not old_file.exists(), "Old file should be deleted"
        print("  OK")

    print("\nAll metrics collector tests passed!")


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI interface for metrics collector."""
    if len(sys.argv) < 2:
        print("Usage: python3 metrics_collector.py <command> [args]")
        print("\nCommands:")
        print("  record <solution> <metric> --value <value>  - Record a solution metric")
        print("  report daily                                - Daily report")
        print("  report weekly                               - Weekly report")
        print("  compute                                     - Compute all solution metrics")
        print("  efficiency                                  - Show routing efficiency")
        print("  compliance                                  - Show routing compliance")
        print("  show <solution>                             - Show solution metrics")
        print("  dashboard                                   - Live status dashboard")
        print("  work                                        - Work coordination view")
        print("  cleanup                                     - Remove old metrics")
        print("  --test                                      - Run tests")
        sys.exit(1)

    command = sys.argv[1]

    if command == "--test":
        test_metrics_collector()
        sys.exit(0)

    collector = MetricsCollector()

    if command == "record":
        if len(sys.argv) < 5:
            print("Usage: metrics_collector.py record <solution> <metric> --value <value>")
            sys.exit(1)

        solution = sys.argv[2]
        metric_name = sys.argv[3]

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

    elif command == "compute":
        computed = collector.compute_all_solution_metrics()
        print()
        print("Computed Solution Metrics:")
        print("-" * 50)
        for solution_id, metrics in computed.items():
            status = metrics.status.upper()
            print(f"\n{solution_id} [{status}]")
            print(f"  Events: {metrics.total_events}")
            for key, value in sorted(metrics.metrics.items()):
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")

    elif command == "efficiency":
        display_efficiency(collector)

    elif command == "compliance":
        # Import and use routing compliance analyzer
        try:
            from routing_compliance import RoutingCompliance, display_compliance_report
            compliance = RoutingCompliance()
            display_compliance_report(compliance)
        except ImportError:
            print("Error: routing_compliance module not found")
            print("Make sure routing_compliance.py is in the same directory")
            sys.exit(1)

    elif command == "show":
        if len(sys.argv) < 3:
            print("Usage: metrics_collector.py show <solution>")
            sys.exit(1)

        solution = sys.argv[2]

        # Show both computed and recorded metrics
        computed = collector.compute_all_solution_metrics()
        if solution in computed:
            metrics = computed[solution]
            print(f"\nComputed metrics for {solution}:")
            print(f"  Status: {metrics.status}")
            print(f"  Events: {metrics.total_events}")
            for key, value in sorted(metrics.metrics.items()):
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
        else:
            print(f"Unknown solution: {solution}")

    elif command == "dashboard":
        display_live_dashboard(collector)

    elif command == "work":
        display_work_dashboard()

    elif command == "cleanup":
        deleted = collector.cleanup_old_metrics()
        print(f"Deleted {deleted} old metric files")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
