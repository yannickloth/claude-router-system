"""
Routing Compliance Analysis Tool

Analyzes whether main Claude follows routing directives by linking
routing_recommendation records to request_tracking records.

CLI Usage:
    # Generate compliance report
    python3 routing_compliance.py report

    # Show detailed ignored directives
    python3 routing_compliance.py ignored

    # Show compliance breakdown by agent
    python3 routing_compliance.py by-agent

    # Export data for analysis
    python3 routing_compliance.py export --format json

    # Run tests
    python3 routing_compliance.py --test

Change Driver: MONITORING_REQUIREMENTS
Changes when: Compliance tracking needs evolve
"""

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Metrics storage directory
METRICS_DIR = Path.home() / ".claude" / "infolead-claude-subscription-router" / "metrics"


@dataclass
class ComplianceRecord:
    """Individual compliance record linking recommendation to actual behavior."""
    timestamp: str
    request_hash: str
    routing_decision: str
    routing_agent: Optional[str]
    routing_confidence: float
    actual_handler: str  # "main" or "agent"
    agent_invoked: Optional[str]
    compliance_status: str  # "followed", "ignored", "no_directive", "unknown"
    project: str
    routing_reason: str


@dataclass
class ComplianceReport:
    """Aggregated compliance statistics."""
    total_recommendations: int
    followed: int
    ignored: int
    no_directive: int
    unknown: int
    compliance_rate: float
    ignored_examples: List[Dict]
    by_agent: Dict[str, Dict[str, int]]


class RoutingCompliance:
    """Analyze routing compliance from metrics data."""

    def __init__(self, metrics_dir: Optional[Path] = None):
        """Initialize compliance analyzer.

        Args:
            metrics_dir: Directory for metric storage. Defaults to standard location.
        """
        self.metrics_dir = metrics_dir or METRICS_DIR
        if not self.metrics_dir.exists():
            self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def get_recommendations(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get all routing recommendations for a date range.

        Args:
            start_date: Start of time range (default: 7 days ago)
            end_date: End of time range (default: now)

        Returns:
            List of routing recommendation records
        """
        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now(UTC)

        recommendations = []
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            log_file = self.metrics_dir / f"{date_str}.jsonl"

            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            if data.get('record_type') == 'routing_recommendation':
                                recommendations.append(data)
                        except json.JSONDecodeError:
                            continue

            current_date += timedelta(days=1)

        return recommendations

    def get_tracking_records(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """Get all request tracking records for a date range.

        Args:
            start_date: Start of time range (default: 7 days ago)
            end_date: End of time range (default: now)

        Returns:
            List of request tracking records
        """
        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now(UTC)

        tracking = []
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            log_file = self.metrics_dir / f"{date_str}.jsonl"

            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            if data.get('record_type') == 'request_tracking':
                                tracking.append(data)
                        except json.JSONDecodeError:
                            continue

            current_date += timedelta(days=1)

        return tracking

    def analyze_compliance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ComplianceReport:
        """Analyze routing compliance for a date range.

        Args:
            start_date: Start of time range
            end_date: End of time range

        Returns:
            ComplianceReport with statistics and examples
        """
        recommendations = self.get_recommendations(start_date, end_date)
        tracking = self.get_tracking_records(start_date, end_date)

        # Build index of tracking records by request_hash for fast lookup
        tracking_by_hash = {}
        for t in tracking:
            request_hash = t.get('request_hash')
            if request_hash:
                # If multiple tracking records for same hash, keep most recent
                if request_hash not in tracking_by_hash:
                    tracking_by_hash[request_hash] = t
                else:
                    # Compare timestamps
                    existing_ts = tracking_by_hash[request_hash].get('timestamp', '')
                    new_ts = t.get('timestamp', '')
                    if new_ts > existing_ts:
                        tracking_by_hash[request_hash] = t

        # Analyze each recommendation
        followed = 0
        ignored = 0
        no_directive = 0
        unknown = 0
        ignored_examples = []
        by_agent = defaultdict(lambda: {'followed': 0, 'ignored': 0, 'no_directive': 0, 'unknown': 0})

        for rec in recommendations:
            request_hash = rec.get('request_hash')
            routing_agent = rec.get('recommendation', {}).get('agent', 'null')

            # Look up tracking record
            track = tracking_by_hash.get(request_hash)

            if track:
                # We have tracking data
                status = track.get('compliance_status', 'unknown')
                agent_invoked = track.get('agent_invoked', 'none')

                if status == 'followed':
                    followed += 1
                    by_agent[routing_agent]['followed'] += 1
                elif status == 'ignored':
                    ignored += 1
                    by_agent[routing_agent]['ignored'] += 1
                    ignored_examples.append(track)
                elif status == 'no_directive':
                    no_directive += 1
                    by_agent[routing_agent]['no_directive'] += 1
                else:
                    unknown += 1
                    by_agent[routing_agent]['unknown'] += 1
            else:
                # No tracking record - likely means main Claude handled directly
                # This counts as "unknown" since we can't definitively say it was ignored
                # (could be a "direct" recommendation where no agent is expected)
                decision = rec.get('full_analysis', {}).get('decision', 'unknown')
                if decision == 'direct':
                    # Expected to handle directly
                    no_directive += 1
                    by_agent[routing_agent]['no_directive'] += 1
                else:
                    # Escalate directive but no agent invoked - likely ignored
                    unknown += 1
                    by_agent[routing_agent]['unknown'] += 1

        total = len(recommendations)
        compliance_rate = (followed / total * 100) if total > 0 else 0

        return ComplianceReport(
            total_recommendations=total,
            followed=followed,
            ignored=ignored,
            no_directive=no_directive,
            unknown=unknown,
            compliance_rate=compliance_rate,
            ignored_examples=ignored_examples[:20],  # Limit examples
            by_agent=dict(by_agent)
        )

    def get_ignored_directives(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get detailed list of ignored routing directives.

        Args:
            start_date: Start of time range
            end_date: End of time range
            limit: Maximum number of records to return

        Returns:
            List of tracking records where directives were ignored
        """
        tracking = self.get_tracking_records(start_date, end_date)
        ignored = [t for t in tracking if t.get('compliance_status') == 'ignored']
        return ignored[:limit]

    def compliance_by_agent(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Dict[str, int]]:
        """Get compliance breakdown by recommended agent.

        Args:
            start_date: Start of time range
            end_date: End of time range

        Returns:
            Dictionary mapping agent name to compliance stats
        """
        report = self.analyze_compliance(start_date, end_date)
        return report.by_agent

    def export_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = 'json'
    ) -> str:
        """Export compliance data for external analysis.

        Args:
            start_date: Start of time range
            end_date: End of time range
            format: Output format ('json' or 'csv')

        Returns:
            Formatted data string
        """
        recommendations = self.get_recommendations(start_date, end_date)
        tracking = self.get_tracking_records(start_date, end_date)

        # Build tracking index
        tracking_by_hash = {t.get('request_hash'): t for t in tracking}

        # Join recommendations with tracking
        joined = []
        for rec in recommendations:
            request_hash = rec.get('request_hash')
            track = tracking_by_hash.get(request_hash, {})

            joined.append({
                'timestamp': rec.get('timestamp'),
                'request_hash': request_hash,
                'routing_decision': rec.get('full_analysis', {}).get('decision'),
                'routing_agent': rec.get('recommendation', {}).get('agent'),
                'routing_confidence': rec.get('recommendation', {}).get('confidence'),
                'routing_reason': rec.get('recommendation', {}).get('reason'),
                'agent_invoked': track.get('agent_invoked'),
                'compliance_status': track.get('compliance_status', 'unknown'),
                'project': track.get('project', 'unknown')
            })

        if format == 'json':
            return json.dumps(joined, indent=2)
        elif format == 'csv':
            # Simple CSV format
            lines = ['timestamp,request_hash,routing_decision,routing_agent,agent_invoked,compliance_status']
            for j in joined:
                lines.append(f"{j['timestamp']},{j['request_hash']},{j['routing_decision']},"
                           f"{j['routing_agent']},{j['agent_invoked']},{j['compliance_status']}")
            return '\n'.join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")


# =============================================================================
# Display Functions
# =============================================================================

def display_compliance_report(analyzer: RoutingCompliance) -> None:
    """Display formatted compliance report."""
    report = analyzer.analyze_compliance()

    print()
    print("=" * 70)
    print("  ROUTING COMPLIANCE REPORT")
    print("=" * 70)
    print()
    print(f"Total routing recommendations: {report.total_recommendations}")
    print()
    print(f"  Followed:     {report.followed:>4} ({report.compliance_rate:>5.1f}%)")
    print(f"  Ignored:      {report.ignored:>4}")
    print(f"  No directive: {report.no_directive:>4}")
    print(f"  Unknown:      {report.unknown:>4}")
    print()

    if report.ignored > 0:
        print("Recent ignored directives (sample):")
        print("-" * 70)
        for ex in report.ignored_examples[:10]:
            timestamp = ex.get('timestamp', 'unknown')[:19]  # Truncate to datetime
            routing_agent = ex.get('routing_agent', 'unknown')
            agent_invoked = ex.get('agent_invoked', 'unknown')
            reason = ex.get('metadata', {}).get('routing_reason', 'no reason')[:40]
            print(f"  {timestamp} | recommended: {routing_agent:<15} | actual: {agent_invoked:<15}")
            print(f"    reason: {reason}")
        print()

    if report.by_agent:
        print("Compliance by recommended agent:")
        print("-" * 70)
        print(f"{'Agent':<20} {'Followed':>10} {'Ignored':>10} {'Unknown':>10}")
        print("-" * 70)
        for agent, stats in sorted(report.by_agent.items()):
            followed = stats['followed']
            ignored = stats['ignored']
            unknown = stats['unknown']
            total = followed + ignored + unknown
            if total > 0:
                rate = followed / total * 100
                print(f"{agent:<20} {followed:>10} {ignored:>10} {unknown:>10} ({rate:.0f}%)")
        print()

    print("=" * 70)


def display_ignored_directives(analyzer: RoutingCompliance) -> None:
    """Display detailed list of ignored directives."""
    ignored = analyzer.get_ignored_directives(limit=50)

    print()
    print("=" * 70)
    print("  IGNORED ROUTING DIRECTIVES")
    print("=" * 70)
    print()

    if not ignored:
        print("No ignored directives found in the analyzed period.")
        print()
        return

    print(f"Found {len(ignored)} ignored directives:")
    print()

    for i, record in enumerate(ignored, 1):
        timestamp = record.get('timestamp', 'unknown')
        request_hash = record.get('request_hash', 'unknown')[:16]
        routing_agent = record.get('routing_agent', 'unknown')
        agent_invoked = record.get('agent_invoked', 'unknown')
        confidence = record.get('routing_confidence', 0)
        reason = record.get('metadata', {}).get('routing_reason', 'no reason')

        print(f"{i}. {timestamp}")
        print(f"   Request: {request_hash}")
        print(f"   Recommended: {routing_agent} (confidence: {confidence:.2f})")
        print(f"   Actually invoked: {agent_invoked}")
        print(f"   Reason: {reason}")
        print()

    print("=" * 70)


def display_by_agent(analyzer: RoutingCompliance) -> None:
    """Display compliance breakdown by agent."""
    by_agent = analyzer.compliance_by_agent()

    print()
    print("=" * 70)
    print("  COMPLIANCE BY RECOMMENDED AGENT")
    print("=" * 70)
    print()

    if not by_agent:
        print("No agent recommendations found in the analyzed period.")
        print()
        return

    print(f"{'Agent':<25} {'Followed':>10} {'Ignored':>10} {'Unknown':>10} {'Rate':>10}")
    print("-" * 70)

    for agent in sorted(by_agent.keys()):
        stats = by_agent[agent]
        followed = stats['followed']
        ignored = stats['ignored']
        unknown = stats['unknown']
        no_directive = stats['no_directive']

        total = followed + ignored + unknown
        if total > 0:
            rate = followed / total * 100
            print(f"{agent:<25} {followed:>10} {ignored:>10} {unknown:>10} {rate:>9.1f}%")

    print("=" * 70)


# =============================================================================
# Tests
# =============================================================================

def test_routing_compliance() -> None:
    """Test routing compliance analyzer."""
    import tempfile

    print("Testing routing compliance analyzer...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        analyzer = RoutingCompliance(metrics_dir=tmpdir)

        # Create test data
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = tmpdir / f"{today}.jsonl"

        # Test 1: Write sample routing recommendation
        print("Test 1: Write routing recommendation")
        rec1 = {
            'record_type': 'routing_recommendation',
            'timestamp': datetime.now(UTC).isoformat(),
            'request_hash': 'test123',
            'recommendation': {
                'agent': 'haiku-general',
                'reason': 'Simple task',
                'confidence': 0.85
            },
            'full_analysis': {
                'decision': 'escalate',
                'agent': 'haiku-general'
            }
        }
        with open(log_file, 'a') as f:
            json.dump(rec1, f)
            f.write('\n')
        print("  OK")

        # Test 2: Write matching tracking record (followed)
        print("Test 2: Write tracking record (followed)")
        track1 = {
            'record_type': 'request_tracking',
            'timestamp': datetime.now(UTC).isoformat(),
            'request_hash': 'test123',
            'routing_decision': 'escalate',
            'routing_agent': 'haiku-general',
            'routing_confidence': 0.85,
            'actual_handler': 'agent',
            'agent_invoked': 'haiku-general',
            'compliance_status': 'followed',
            'project': 'test-project'
        }
        with open(log_file, 'a') as f:
            json.dump(track1, f)
            f.write('\n')
        print("  OK")

        # Test 3: Write recommendation + tracking for ignored directive
        print("Test 3: Write ignored directive")
        rec2 = {
            'record_type': 'routing_recommendation',
            'timestamp': datetime.now(UTC).isoformat(),
            'request_hash': 'test456',
            'recommendation': {
                'agent': 'haiku-general',
                'reason': 'Simple task',
                'confidence': 0.90
            },
            'full_analysis': {
                'decision': 'escalate',
                'agent': 'haiku-general'
            }
        }
        track2 = {
            'record_type': 'request_tracking',
            'timestamp': datetime.now(UTC).isoformat(),
            'request_hash': 'test456',
            'routing_decision': 'escalate',
            'routing_agent': 'haiku-general',
            'routing_confidence': 0.90,
            'actual_handler': 'agent',
            'agent_invoked': 'sonnet-general',  # Different agent!
            'compliance_status': 'ignored',
            'project': 'test-project'
        }
        with open(log_file, 'a') as f:
            json.dump(rec2, f)
            f.write('\n')
            json.dump(track2, f)
            f.write('\n')
        print("  OK")

        # Test 4: Analyze compliance
        print("Test 4: Analyze compliance")
        report = analyzer.analyze_compliance()
        assert report.total_recommendations == 2, f"Expected 2 recommendations, got {report.total_recommendations}"
        assert report.followed == 1, f"Expected 1 followed, got {report.followed}"
        assert report.ignored == 1, f"Expected 1 ignored, got {report.ignored}"
        assert 40 < report.compliance_rate < 60, f"Expected ~50% rate, got {report.compliance_rate}"
        print(f"  Compliance rate: {report.compliance_rate:.1f}%")
        print("  OK")

        # Test 5: Get ignored directives
        print("Test 5: Get ignored directives")
        ignored = analyzer.get_ignored_directives()
        assert len(ignored) == 1, f"Expected 1 ignored directive, got {len(ignored)}"
        assert ignored[0]['request_hash'] == 'test456'
        assert ignored[0]['agent_invoked'] == 'sonnet-general'
        print("  OK")

        # Test 6: Compliance by agent
        print("Test 6: Compliance by agent")
        by_agent = analyzer.compliance_by_agent()
        assert 'haiku-general' in by_agent
        assert by_agent['haiku-general']['followed'] == 1
        assert by_agent['haiku-general']['ignored'] == 1
        print("  OK")

        # Test 7: Export data
        print("Test 7: Export data")
        json_export = analyzer.export_data(format='json')
        assert 'test123' in json_export
        assert 'test456' in json_export
        csv_export = analyzer.export_data(format='csv')
        assert 'timestamp,request_hash' in csv_export
        print("  OK")

    print("\nAll routing compliance tests passed!")


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI interface for routing compliance analysis."""
    if len(sys.argv) < 2:
        print("Usage: python3 routing_compliance.py <command> [options]")
        print("\nCommands:")
        print("  report       - Generate compliance report")
        print("  ignored      - Show detailed ignored directives")
        print("  by-agent     - Show compliance breakdown by agent")
        print("  export       - Export data (--format json|csv)")
        print("  --test       - Run tests")
        sys.exit(1)

    command = sys.argv[1]

    if command == "--test":
        test_routing_compliance()
        sys.exit(0)

    analyzer = RoutingCompliance()

    if command == "report":
        display_compliance_report(analyzer)

    elif command == "ignored":
        display_ignored_directives(analyzer)

    elif command == "by-agent":
        display_by_agent(analyzer)

    elif command == "export":
        format = 'json'
        for i, arg in enumerate(sys.argv):
            if arg == "--format" and i + 1 < len(sys.argv):
                format = sys.argv[i + 1]
                break

        data = analyzer.export_data(format=format)
        print(data)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
