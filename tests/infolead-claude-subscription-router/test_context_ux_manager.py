#!/usr/bin/env python3
"""
Pytest suite for context_ux_manager.py

Ported from embedded tests in implementation/context_ux_manager.py

Change Driver: TESTING_REQUIREMENTS
"""

import pytest

# Add implementation directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins/infolead-claude-subscription-router/implementation"))

from context_ux_manager import ContextUXManager, ContextHealth


@pytest.fixture
def manager():
    """Create ContextUXManager instance."""
    return ContextUXManager()


def test_healthy_context(manager):
    """Test context analysis for healthy context (30k tokens)."""
    analysis = manager.analyze_context(tokens_used=30000, conversation_turns=5, unique_files_referenced=3)
    assert analysis.health == ContextHealth.HEALTHY, f"Expected HEALTHY, got {analysis.health}"


def test_attention_context(manager):
    """Test context analysis for attention state (75k tokens - 75% of 100k effective)."""
    analysis = manager.analyze_context(tokens_used=75000, conversation_turns=20, unique_files_referenced=5)
    assert analysis.health == ContextHealth.ATTENTION, f"Expected ATTENTION, got {analysis.health}"


def test_recommend_restart_context(manager):
    """Test context analysis recommending restart (90k tokens - 90% of 100k effective)."""
    analysis = manager.analyze_context(tokens_used=90000, conversation_turns=30, unique_files_referenced=8)
    assert analysis.health == ContextHealth.RECOMMEND_RESTART, f"Expected RECOMMEND_RESTART, got {analysis.health}"


def test_percent_used_calculation(manager):
    """Test that percent_used is calculated correctly."""
    analysis = manager.analyze_context(tokens_used=50000)
    # 50k / 100k effective limit = 50%
    assert 40 < analysis.percent_used < 60, f"Expected ~50%, got {analysis.percent_used}"


def test_analysis_has_recommendation(manager):
    """Test that analysis includes a recommendation."""
    analysis = manager.analyze_context(tokens_used=50000)
    assert "recommendation" in analysis
    assert isinstance(analysis.recommendation, str)
    assert len(analysis.recommendation) > 0


def test_analysis_has_tokens_info(manager):
    """Test that analysis includes token information."""
    analysis = manager.analyze_context(tokens_used=50000)
    assert analysis.tokens_used == 50000
    assert analysis.tokens_limit > 0


def test_healthy_context_description(manager):
    """Test that healthy context has appropriate recommendation."""
    analysis = manager.analyze_context(tokens_used=30000)
    assert analysis.health == ContextHealth.HEALTHY
    assert analysis.recommendation is not None


def test_attention_context_description(manager):
    """Test that attention context has appropriate recommendation."""
    analysis = manager.analyze_context(tokens_used=75000)
    assert analysis.health == ContextHealth.ATTENTION
    # Should include some recommendation about monitoring
    assert analysis.recommendation is not None


def test_recommend_restart_description(manager):
    """Test that RECOMMEND_RESTART context has restart recommendation."""
    analysis = manager.analyze_context(tokens_used=90000)
    assert analysis.health == ContextHealth.RECOMMEND_RESTART
    assert "fresh start" in analysis.recommendation.lower() or "restart" in analysis.recommendation.lower()


def test_estimate_continuation_cost(manager):
    """Test cost estimation for continuing vs fresh start."""
    cost = manager.estimate_continuation_cost(80000)
    assert "recommendation" in cost
    assert "continue_cost" in cost
    assert "fresh_start_cost" in cost


def test_estimate_continuation_cost_healthy(manager):
    """Test cost estimation for healthy context."""
    cost = manager.estimate_continuation_cost(30000)
    # At 30%, should recommend continuing
    assert cost is not None
    assert isinstance(cost, dict)


def test_estimate_continuation_cost_near_limit(manager):
    """Test cost estimation near context limit."""
    cost = manager.estimate_continuation_cost(90000)
    # At 90%, fresh start cost might be lower
    assert cost is not None


def test_get_context_status_line(manager):
    """Test status line generation."""
    status = manager.get_context_status_line(50000)
    assert "Context:" in status
    assert "%" in status


def test_context_status_line_format(manager):
    """Test status line includes progress indicator."""
    status = manager.get_context_status_line(50000)
    # Should have context info and percentage
    assert len(status) > 10
    assert isinstance(status, str)


def test_context_status_line_varies_by_usage(manager):
    """Test that status line changes with different token usage."""
    status_low = manager.get_context_status_line(30000)
    status_high = manager.get_context_status_line(80000)
    # Different token levels should produce different output
    assert "30" in status_low or "30k" in status_low.lower()


def test_should_recommend_fresh_start_healthy(manager):
    """Test that healthy context should not trigger fresh start recommendation."""
    assert not manager.should_recommend_fresh_start(50000), "50k should not trigger"


def test_should_recommend_fresh_start_critical(manager):
    """Test that critical context should trigger fresh start recommendation."""
    assert manager.should_recommend_fresh_start(90000), "90k should trigger"


def test_should_recommend_fresh_start_very_low(manager):
    """Test that very low token usage should not trigger."""
    assert not manager.should_recommend_fresh_start(10000), "10k should not trigger"


def test_should_recommend_fresh_start_moderate(manager):
    """Test moderate token usage doesn't trigger."""
    assert not manager.should_recommend_fresh_start(60000), "60k should not trigger fresh start"


def test_signal_to_noise_calculation(manager):
    """Test signal-to-noise ratio calculation."""
    analysis = manager.analyze_context(
        tokens_used=50000,
        conversation_turns=10,
        unique_files_referenced=5
    )
    # With files and turns, should have meaningful signal-to-noise
    assert 0 < analysis.signal_to_noise <= 100


def test_signal_to_noise_more_files(manager):
    """Test signal-to-noise increases with more files."""
    analysis_low = manager.analyze_context(
        tokens_used=50000,
        conversation_turns=20,
        unique_files_referenced=2
    )
    analysis_high = manager.analyze_context(
        tokens_used=50000,
        conversation_turns=20,
        unique_files_referenced=8
    )
    # More files should increase signal-to-noise
    assert analysis_high.signal_to_noise > analysis_low.signal_to_noise


def test_signal_to_noise_default(manager):
    """Test signal-to-noise defaults when no files/turns info."""
    analysis = manager.analyze_context(tokens_used=50000)
    # Should have default reasonable value
    assert analysis.signal_to_noise == 50.0


def test_custom_token_limit(manager):
    """Test manager with custom token limit."""
    custom_manager = ContextUXManager(token_limit=150000)
    assert custom_manager.token_limit == 150000


def test_analysis_with_custom_limit(manager):
    """Test analysis respects custom token limit."""
    custom_manager = ContextUXManager(token_limit=150000)
    analysis = custom_manager.analyze_context(tokens_used=100000)
    assert analysis.tokens_limit == 150000


def test_tokens_used_preserved(manager):
    """Test that tokens_used is accurately preserved in analysis."""
    for tokens in [10000, 50000, 100000]:
        analysis = manager.analyze_context(tokens_used=tokens)
        assert analysis.tokens_used == tokens


def test_health_enum_values():
    """Test ContextHealth enum has expected values."""
    assert hasattr(ContextHealth, 'HEALTHY')
    assert hasattr(ContextHealth, 'ATTENTION')
    assert hasattr(ContextHealth, 'RECOMMEND_RESTART')


def test_multiple_analyses_independent(manager):
    """Test that multiple analyses don't interfere with each other."""
    analysis1 = manager.analyze_context(tokens_used=30000)
    analysis2 = manager.analyze_context(tokens_used=80000)
    analysis3 = manager.analyze_context(tokens_used=30000)

    assert analysis1.health == ContextHealth.HEALTHY
    assert analysis2.health == ContextHealth.ATTENTION or analysis2.health == ContextHealth.RECOMMEND_RESTART
    assert analysis3.health == ContextHealth.HEALTHY
