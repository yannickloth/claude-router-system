"""
Pytest test suite for adaptive orchestration.

Tests complexity classification, orchestration mode selection,
configuration loading, and edge cases.

Run:
    pytest test_adaptive_orchestrator.py -v
    pytest test_adaptive_orchestrator.py -v --cov=adaptive_orchestrator
"""

import pytest
import sys
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

# Add implementation directory to path
IMPL_DIR = Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from adaptive_orchestrator import (
    AdaptiveOrchestrator,
    ComplexityClassifier,
    ComplexityLevel,
    OrchestrationMode,
    OrchestratorConfig,
    load_config,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def orchestrator():
    """Create orchestrator with default config."""
    return AdaptiveOrchestrator()


@pytest.fixture
def classifier():
    """Create classifier with default config."""
    return ComplexityClassifier()


@pytest.fixture
def temp_config_file():
    """Create temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yield Path(f.name)
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


# ============================================================================
# COMPLEXITY CLASSIFICATION TESTS (from built-in test suite)
# ============================================================================

class TestComplexityClassification:
    """Test complexity classification with built-in test cases."""

    # SIMPLE test cases
    @pytest.mark.parametrize("request", [
        "Fix typo in README.md",
        "Format code in src/main.py",
        "Rename variable foo to bar in utils.py",
        "Sort imports in app.py",
        "Show me the contents of config.json",
    ])
    def test_simple_requests(self, orchestrator, request):
        """Test SIMPLE request classification."""
        result = orchestrator.orchestrate(request)
        assert result.complexity == ComplexityLevel.SIMPLE
        assert result.mode == OrchestrationMode.SINGLE_STAGE

    # COMPLEX test cases
    @pytest.mark.parametrize("request", [
        "Design a caching architecture with fallback strategies",
        "Which is the best approach for implementing authentication?",
        "Refactor the entire authentication system",
        "Implement a new API endpoint and add tests and update documentation",
        "Analyze the trade-offs between Redis and Memcached for our use case",
    ])
    def test_complex_requests(self, orchestrator, request):
        """Test COMPLEX request classification."""
        result = orchestrator.orchestrate(request)
        assert result.complexity == ComplexityLevel.COMPLEX
        assert result.mode == OrchestrationMode.MULTI_STAGE

    # MODERATE test cases
    @pytest.mark.parametrize("request", [
        "Fix the bug in auth.py",
        "Add logging to the payment module",
        "Update the API documentation",
        "Run the test suite",
    ])
    def test_moderate_requests(self, orchestrator, request):
        """Test MODERATE request classification."""
        result = orchestrator.orchestrate(request)
        assert result.complexity == ComplexityLevel.MODERATE
        assert result.mode == OrchestrationMode.SINGLE_STAGE_WITH_MONITORING


# ============================================================================
# PATTERN MATCHING TESTS
# ============================================================================

class TestPatternMatching:
    """Test pattern matching for complexity indicators."""

    def test_simple_mechanical_fix(self, classifier):
        """Test mechanical fix patterns."""
        analysis = classifier.classify("Fix typo in README.md")
        assert ComplexityLevel.SIMPLE == analysis.level
        assert any("mechanical_fix" in ind for ind in analysis.indicators)

    def test_simple_format(self, classifier):
        """Test format patterns."""
        analysis = classifier.classify("Format code in main.py")
        assert ComplexityLevel.SIMPLE == analysis.level
        assert any("mechanical_format" in ind for ind in analysis.indicators)

    def test_simple_rename(self, classifier):
        """Test rename patterns."""
        analysis = classifier.classify("Rename variable foo to bar in utils.py")
        assert ComplexityLevel.SIMPLE == analysis.level
        assert any("mechanical_rename" in ind for ind in analysis.indicators)

    def test_simple_read_only(self, classifier):
        """Test read-only patterns."""
        for verb in ["show", "display", "list", "get", "read"]:
            analysis = classifier.classify(f"{verb} the config file")
            assert any(f"read_only_{verb}" in ind for ind in analysis.indicators)

    def test_complex_design(self, classifier):
        """Test design/architecture patterns."""
        analysis = classifier.classify("Design a new authentication system")
        assert ComplexityLevel.COMPLEX == analysis.level
        assert any("requires_design" in ind for ind in analysis.indicators)

    def test_complex_judgment(self, classifier):
        """Test judgment patterns."""
        for word in ["best", "better", "optimal", "which"]:
            request = f"What is the {word} approach for caching?"
            analysis = classifier.classify(request)
            assert any("requires_judgment" in ind for ind in analysis.indicators)

    def test_complex_tradeoff(self, classifier):
        """Test trade-off analysis patterns."""
        analysis = classifier.classify("Evaluate the tradeoffs between SQL and NoSQL")
        assert ComplexityLevel.COMPLEX == analysis.level
        assert any("requires_analysis" in ind for ind in analysis.indicators)

    def test_complex_multi_target(self, classifier):
        """Test multi-target patterns."""
        analysis = classifier.classify("Update all files in the module")
        assert ComplexityLevel.COMPLEX == analysis.level
        assert any("multi_target" in ind for ind in analysis.indicators)

    def test_explicit_file_path_detection(self, classifier):
        """Test explicit file path detection."""
        assert classifier.has_explicit_file_path("Fix README.md")
        assert classifier.has_explicit_file_path("Update src/main.py")
        assert classifier.has_explicit_file_path("Edit ./config.json")
        assert classifier.has_explicit_file_path("Check ~/Documents/file.txt")
        assert not classifier.has_explicit_file_path("Fix the bug")

    def test_multi_objective_counting(self, classifier):
        """Test multi-objective counting."""
        assert classifier.count_objectives("Do X") == 1
        assert classifier.count_objectives("Do X and then Y") >= 2
        assert classifier.count_objectives("Do X; then Y; then Z") >= 3


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestConfiguration:
    """Test configuration loading and application."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OrchestratorConfig()
        assert config.simple_confidence_threshold == 0.7
        assert config.complex_confidence_threshold == 0.6
        assert config.simple_pattern_weight == 0.1
        assert config.complex_pattern_weight == 0.15
        assert config.custom_simple_patterns == []
        assert config.custom_complex_patterns == []
        assert config.force_mode is None

    def test_load_config_missing_file(self, temp_config_file):
        """Test loading config from non-existent file returns defaults."""
        # Delete temp file
        temp_config_file.unlink(missing_ok=True)
        config = load_config(temp_config_file)
        assert config.simple_confidence_threshold == 0.7
        assert config.complex_confidence_threshold == 0.6

    def test_load_config_empty_file(self, temp_config_file):
        """Test loading empty config file returns defaults."""
        with open(temp_config_file, 'w') as f:
            f.write("")
        config = load_config(temp_config_file)
        assert config.simple_confidence_threshold == 0.7
        assert config.complex_confidence_threshold == 0.6

    def test_load_config_custom_thresholds(self, temp_config_file):
        """Test loading custom thresholds from config."""
        config_data = {
            'thresholds': {
                'simple_confidence': 0.8,
                'complex_confidence': 0.7,
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = load_config(temp_config_file)
        assert config.simple_confidence_threshold == 0.8
        assert config.complex_confidence_threshold == 0.7

    def test_load_config_custom_weights(self, temp_config_file):
        """Test loading custom pattern weights from config."""
        config_data = {
            'weights': {
                'simple_weight': 0.2,
                'complex_weight': 0.25,
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = load_config(temp_config_file)
        assert config.simple_pattern_weight == 0.2
        assert config.complex_pattern_weight == 0.25

    def test_load_config_custom_patterns(self, temp_config_file):
        """Test loading custom patterns from config."""
        config_data = {
            'patterns': {
                'custom_simple': [
                    {'pattern': r'\\btest\\b', 'name': 'test_pattern'},
                ],
                'custom_complex': [
                    {'pattern': r'\\bmigrate\\b', 'name': 'migration'},
                ],
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = load_config(temp_config_file)
        assert len(config.custom_simple_patterns) == 1
        assert config.custom_simple_patterns[0] == (r'\\btest\\b', 'test_pattern')
        assert len(config.custom_complex_patterns) == 1
        assert config.custom_complex_patterns[0] == (r'\\bmigrate\\b', 'migration')

    def test_load_config_force_mode(self, temp_config_file):
        """Test loading force_mode override from config."""
        config_data = {
            'overrides': {
                'force_mode': 'multi_stage',
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = load_config(temp_config_file)
        assert config.force_mode == 'multi_stage'

    def test_load_config_invalid_force_mode(self, temp_config_file):
        """Test invalid force_mode is rejected."""
        config_data = {
            'overrides': {
                'force_mode': 'invalid_mode',
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)

        config = load_config(temp_config_file)
        assert config.force_mode is None  # Should be rejected

    def test_load_config_malformed_yaml(self, temp_config_file):
        """Test malformed YAML falls back to defaults."""
        with open(temp_config_file, 'w') as f:
            f.write("invalid: yaml: syntax: {")

        config = load_config(temp_config_file)
        assert config.simple_confidence_threshold == 0.7  # Default

    def test_orchestrator_uses_config(self, temp_config_file):
        """Test orchestrator respects config settings."""
        config_data = {
            'overrides': {
                'force_mode': 'multi_stage',
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)

        orchestrator = AdaptiveOrchestrator(config_path=temp_config_file)

        # Even a SIMPLE request should use multi_stage due to force_mode
        result = orchestrator.orchestrate("Fix typo in README.md")
        assert result.mode == OrchestrationMode.MULTI_STAGE

    def test_custom_patterns_applied(self, temp_config_file):
        """Test custom patterns are applied during classification."""
        config_data = {
            'patterns': {
                'custom_complex': [
                    {'pattern': r'\\bmigrate\\b', 'name': 'migration_task'},
                ],
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)

        orchestrator = AdaptiveOrchestrator(config_path=temp_config_file)
        result = orchestrator.orchestrate("Migrate database schema")

        # Should be classified as COMPLEX due to custom pattern
        assert result.complexity == ComplexityLevel.COMPLEX
        assert any("migration_task" in ind for ind in result.metadata['complexity_indicators'])


# ============================================================================
# ORCHESTRATION MODE TESTS
# ============================================================================

class TestOrchestrationModes:
    """Test orchestration mode selection and execution."""

    def test_single_stage_mode(self, orchestrator):
        """Test single-stage orchestration mode."""
        result = orchestrator.orchestrate("Fix typo in README.md")
        assert result.mode == OrchestrationMode.SINGLE_STAGE
        assert result.metadata['strategy'] == 'single_stage'
        assert 'route' in result.metadata['stages']

    def test_single_stage_monitored_mode(self, orchestrator):
        """Test single-stage with monitoring mode."""
        result = orchestrator.orchestrate("Fix bug in auth.py")
        assert result.mode == OrchestrationMode.SINGLE_STAGE_WITH_MONITORING
        assert result.metadata['strategy'] == 'single_stage_monitored'
        assert result.metadata.get('monitoring_enabled') is True

    def test_multi_stage_mode(self, orchestrator):
        """Test multi-stage orchestration mode."""
        result = orchestrator.orchestrate("Design a new authentication system")
        assert result.mode == OrchestrationMode.MULTI_STAGE
        assert result.metadata['strategy'] == 'multi_stage'
        assert 'interpret' in result.metadata['stages']
        assert 'plan' in result.metadata['stages']
        assert 'execute' in result.metadata['stages']

    def test_multi_stage_interpretation(self, orchestrator):
        """Test multi-stage interpretation phase."""
        result = orchestrator.orchestrate("Design a caching system")
        assert 'interpretation' in result.metadata
        interpretation = result.metadata['interpretation']
        assert 'intent' in interpretation
        assert 'scope' in interpretation

    def test_multi_stage_planning(self, orchestrator):
        """Test multi-stage planning phase."""
        result = orchestrator.orchestrate("Refactor authentication system")
        assert 'plan' in result.metadata
        plan = result.metadata['plan']
        assert 'refined_request' in plan
        assert 'recommended_tier' in plan


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_request(self, orchestrator):
        """Test empty request handling."""
        result = orchestrator.orchestrate("")
        assert result.complexity == ComplexityLevel.MODERATE  # Default
        assert result.mode == OrchestrationMode.SINGLE_STAGE_WITH_MONITORING

    def test_very_long_request(self, orchestrator):
        """Test very long request handling."""
        long_request = "Fix typo " * 1000 + "in README.md"
        result = orchestrator.orchestrate(long_request)
        assert result.complexity is not None
        assert result.mode is not None

    def test_special_characters(self, orchestrator):
        """Test request with special characters."""
        result = orchestrator.orchestrate("Fix $VAR in @file.py #bug")
        assert result.complexity is not None
        assert result.mode is not None

    def test_unicode_characters(self, orchestrator):
        """Test request with Unicode characters."""
        result = orchestrator.orchestrate("Fix 中文 in file.py")
        assert result.complexity is not None
        assert result.mode is not None

    def test_case_insensitive_matching(self, classifier):
        """Test pattern matching is case-insensitive."""
        analysis1 = classifier.classify("FIX TYPO in README.md")
        analysis2 = classifier.classify("fix typo in README.md")
        assert analysis1.level == analysis2.level

    def test_metadata_completeness(self, orchestrator):
        """Test result metadata is complete."""
        result = orchestrator.orchestrate("Fix typo in README.md")
        assert 'complexity_confidence' in result.metadata
        assert 'complexity_indicators' in result.metadata
        assert 'strategy' in result.metadata
        assert 'stages' in result.metadata
        assert result.timestamp is not None


# ============================================================================
# METRICS RECORDING TESTS
# ============================================================================

class TestMetricsRecording:
    """Test metrics recording during orchestration."""

    @patch('adaptive_orchestrator.MetricsCollector')
    def test_metrics_recorded(self, mock_metrics_class):
        """Test metrics are recorded during orchestration."""
        mock_metrics = Mock()
        mock_metrics_class.return_value = mock_metrics

        orchestrator = AdaptiveOrchestrator()
        orchestrator.orchestrate("Fix typo in README.md")

        # Verify metrics were recorded
        assert mock_metrics.record_metric.called
        assert mock_metrics.record_metric.call_count >= 2  # At least complexity + mode


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_workflow_simple(self, orchestrator):
        """Test full workflow for SIMPLE request."""
        result = orchestrator.orchestrate("Format code in main.py")

        # Complexity classification
        assert result.complexity == ComplexityLevel.SIMPLE
        assert result.metadata['complexity_confidence'] > 0.7

        # Orchestration mode
        assert result.mode == OrchestrationMode.SINGLE_STAGE

        # Routing result
        assert result.routing_result is not None

    def test_full_workflow_complex(self, orchestrator):
        """Test full workflow for COMPLEX request."""
        result = orchestrator.orchestrate("Design authentication architecture")

        # Complexity classification
        assert result.complexity == ComplexityLevel.COMPLEX
        assert result.metadata['complexity_confidence'] > 0.6

        # Orchestration mode
        assert result.mode == OrchestrationMode.MULTI_STAGE

        # Multi-stage metadata
        assert 'interpretation' in result.metadata
        assert 'plan' in result.metadata

    def test_config_affects_classification(self, temp_config_file):
        """Test configuration affects classification behavior."""
        # Create config with higher thresholds
        config_data = {
            'thresholds': {
                'simple_confidence': 0.95,  # Very strict
                'complex_confidence': 0.95,  # Very strict
            }
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)

        orchestrator = AdaptiveOrchestrator(config_path=temp_config_file)
        result = orchestrator.orchestrate("Fix typo in README.md")

        # With very high thresholds, should fall to MODERATE
        # (unless enough patterns match to exceed threshold)
        assert result.complexity in [ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
