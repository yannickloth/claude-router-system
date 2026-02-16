#!/usr/bin/env python3
"""
Pytest suite for routing_compliance.py

Ported from embedded tests in implementation/routing_compliance.py

Change Driver: TESTING_REQUIREMENTS
"""

import json
import tempfile
from datetime import datetime, UTC
from pathlib import Path

import pytest

# Add implementation directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins/infolead-claude-subscription-router/implementation"))

from routing_compliance import RoutingCompliance


@pytest.fixture
def temp_metrics_dir():
    """Create temporary directory for test metrics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def analyzer(temp_metrics_dir):
    """Create RoutingCompliance analyzer with temp directory."""
    return RoutingCompliance(metrics_dir=temp_metrics_dir)


@pytest.fixture
def test_log_file(temp_metrics_dir):
    """Create test log file path."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return temp_metrics_dir / f"{today}.jsonl"


@pytest.fixture
def populated_log_file(test_log_file):
    """Create log file with test data (1 followed, 1 ignored)."""
    # Recommendation 1 (will be followed)
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

    # Tracking 1 (followed)
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

    # Recommendation 2 (will be ignored)
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

    # Tracking 2 (ignored - different agent invoked)
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

    # Write all records
    with open(test_log_file, 'a') as f:
        for record in [rec1, track1, rec2, track2]:
            json.dump(record, f)
            f.write('\n')

    return test_log_file


def test_write_routing_recommendation(test_log_file):
    """Test writing routing recommendation to log file."""
    rec = {
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

    with open(test_log_file, 'a') as f:
        json.dump(rec, f)
        f.write('\n')

    # Verify file was created and contains data
    assert test_log_file.exists()
    content = test_log_file.read_text()
    assert 'routing_recommendation' in content
    assert 'test123' in content


def test_write_tracking_record(test_log_file):
    """Test writing tracking record to log file."""
    track = {
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

    with open(test_log_file, 'a') as f:
        json.dump(track, f)
        f.write('\n')

    # Verify file contains tracking data
    assert test_log_file.exists()
    content = test_log_file.read_text()
    assert 'request_tracking' in content
    assert 'followed' in content


def test_write_ignored_directive(test_log_file):
    """Test writing recommendation and tracking for ignored directive."""
    rec = {
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

    track = {
        'record_type': 'request_tracking',
        'timestamp': datetime.now(UTC).isoformat(),
        'request_hash': 'test456',
        'routing_decision': 'escalate',
        'routing_agent': 'haiku-general',
        'routing_confidence': 0.90,
        'actual_handler': 'agent',
        'agent_invoked': 'sonnet-general',  # Different agent - ignored!
        'compliance_status': 'ignored',
        'project': 'test-project'
    }

    with open(test_log_file, 'a') as f:
        json.dump(rec, f)
        f.write('\n')
        json.dump(track, f)
        f.write('\n')

    # Verify both records written
    content = test_log_file.read_text()
    assert content.count('test456') == 2
    assert 'ignored' in content


def test_analyze_compliance(analyzer, populated_log_file):
    """Test compliance analysis with mixed followed/ignored directives."""
    report = analyzer.analyze_compliance()

    assert report.total_recommendations == 2, f"Expected 2 recommendations, got {report.total_recommendations}"
    assert report.followed == 1, f"Expected 1 followed, got {report.followed}"
    assert report.ignored == 1, f"Expected 1 ignored, got {report.ignored}"
    assert 40 < report.compliance_rate < 60, f"Expected ~50% compliance rate, got {report.compliance_rate}"


def test_get_ignored_directives(analyzer, populated_log_file):
    """Test retrieving list of ignored directives."""
    ignored = analyzer.get_ignored_directives()

    assert len(ignored) == 1, f"Expected 1 ignored directive, got {len(ignored)}"
    assert ignored[0]['request_hash'] == 'test456'
    assert ignored[0]['agent_invoked'] == 'sonnet-general'


def test_compliance_by_agent(analyzer, populated_log_file):
    """Test compliance breakdown by agent."""
    by_agent = analyzer.compliance_by_agent()

    assert 'haiku-general' in by_agent
    assert by_agent['haiku-general']['followed'] == 1
    assert by_agent['haiku-general']['ignored'] == 1


def test_export_data_json(analyzer, populated_log_file):
    """Test exporting compliance data as JSON."""
    json_export = analyzer.export_data(format='json')

    assert 'test123' in json_export
    assert 'test456' in json_export


def test_export_data_csv(analyzer, populated_log_file):
    """Test exporting compliance data as CSV."""
    csv_export = analyzer.export_data(format='csv')

    assert 'timestamp,request_hash' in csv_export or 'timestamp' in csv_export
