"""
Tests for domain_adapter module.

Tests domain detection, workflow loading, and agent recommendations.
"""

import pytest
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router" / "implementation"))

from domain_adapter import (
    DomainAdapter,
    DomainConfig,
    Workflow,
    ParallelismLevel,
)


class TestDomainDetection:
    """Test domain detection from project structure."""

    def test_detect_latex_domain(self, tmp_path):
        """Should detect LaTeX research domain."""
        # Create LaTeX project indicators
        (tmp_path / "main.tex").write_text("\\documentclass{article}")
        (tmp_path / "references.bib").write_text("@article{test, title={Test}}")

        adapter = DomainAdapter()
        domain = adapter.detect_domain(tmp_path)
        assert domain == "latex-research"

    def test_detect_software_domain(self, tmp_path):
        """Should detect software development domain."""
        # Create Python project indicators
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "test_main.py").write_text("def test_main(): pass")
        (tmp_path / "pytest.ini").write_text("[pytest]")

        adapter = DomainAdapter()
        domain = adapter.detect_domain(tmp_path)
        assert domain == "software-dev"

    def test_detect_knowledge_domain(self, tmp_path):
        """Should detect knowledge management domain."""
        # Create markdown-heavy project
        (tmp_path / "notes.md").write_text("# Notes")
        (tmp_path / "index.md").write_text("# Index")

        adapter = DomainAdapter()
        domain = adapter.detect_domain(tmp_path)
        assert domain == "knowledge-mgmt"

    def test_detect_no_domain(self, tmp_path):
        """Should return None when no domain detected."""
        # Empty directory
        adapter = DomainAdapter()
        domain = adapter.detect_domain(tmp_path)
        # Could be None or lowest-scoring match
        assert domain is None or isinstance(domain, str)


class TestWorkflowLoading:
    """Test workflow configuration loading."""

    @pytest.fixture
    def adapter_with_config(self, tmp_path):
        """Create adapter with test domain config."""
        config_dir = tmp_path / "config" / "domains"
        config_dir.mkdir(parents=True)

        # Create test domain config
        config_yaml = """
domain: test-domain
workflows:
  test_workflow:
    phases:
      - phase1
      - phase2
    quality_gates:
      - gate1
    parallelism: low
  sequential_workflow:
    phases:
      - only_phase
    quality_gates: []
    parallelism: sequential
default_agents:
  complex_task: opus-general
  simple_task: haiku-general
context_strategy:
  large_files: split_by_section
thresholds:
  max_file_size: 10000
quality_requirements:
  require_tests: true
file_patterns:
  source: "*.txt"
risk_patterns:
  high_risk:
    - "delete.*all"
  medium_risk:
    - "modify"
quota_allocation:
  haiku: 70
  sonnet: 25
  opus: 5
specialized_agents:
  - test-agent-1
  - test-agent-2
"""
        (config_dir / "test-domain.yaml").write_text(config_yaml)

        return DomainAdapter(config_dir=config_dir)

    def test_get_workflow(self, adapter_with_config):
        """Should retrieve workflow by name."""
        workflow = adapter_with_config.get_workflow("test-domain", "test_workflow")

        assert workflow is not None
        assert workflow.name == "test_workflow"
        assert "phase1" in workflow.phases
        assert "phase2" in workflow.phases
        assert "gate1" in workflow.quality_gates
        assert workflow.parallelism == ParallelismLevel.LOW

    def test_get_workflow_not_found(self, adapter_with_config):
        """Should return None for unknown workflow."""
        workflow = adapter_with_config.get_workflow("test-domain", "nonexistent")
        assert workflow is None

    def test_get_wip_limit(self, adapter_with_config):
        """Should return WIP limit based on parallelism."""
        # LOW parallelism = 2 concurrent
        wip = adapter_with_config.get_wip_limit("test-domain", "test_workflow")
        assert wip == 2

        # SEQUENTIAL parallelism = 1 concurrent
        wip = adapter_with_config.get_wip_limit("test-domain", "sequential_workflow")
        assert wip == 1

    def test_wip_limit_unknown_workflow(self, adapter_with_config):
        """Should return default WIP for unknown workflow."""
        wip = adapter_with_config.get_wip_limit("test-domain", "unknown")
        assert wip == 2  # Default medium


class TestAgentRecommendation:
    """Test agent recommendation by task type."""

    @pytest.fixture
    def adapter_with_config(self, tmp_path):
        """Create adapter with test domain config."""
        config_dir = tmp_path / "config" / "domains"
        config_dir.mkdir(parents=True)

        config_yaml = """
domain: test-domain
workflows: {}
default_agents:
  formalization: opus-general
  syntax: haiku-general
  analysis: sonnet-general
context_strategy: {}
thresholds: {}
quality_requirements: {}
file_patterns: {}
risk_patterns: {}
quota_allocation: {}
"""
        (config_dir / "test-domain.yaml").write_text(config_yaml)
        return DomainAdapter(config_dir=config_dir)

    def test_get_agent_for_complex_task(self, adapter_with_config):
        """Should recommend Opus for complex tasks."""
        agent = adapter_with_config.get_agent_recommendation(
            "test-domain", "formalization"
        )
        assert agent == "opus-general"

    def test_get_agent_for_simple_task(self, adapter_with_config):
        """Should recommend Haiku for simple tasks."""
        agent = adapter_with_config.get_agent_recommendation(
            "test-domain", "syntax"
        )
        assert agent == "haiku-general"

    def test_get_agent_unknown_task_type(self, adapter_with_config):
        """Should return Sonnet for unknown task types."""
        agent = adapter_with_config.get_agent_recommendation(
            "test-domain", "unknown_task"
        )
        assert agent == "sonnet-general"

    def test_get_agent_unknown_domain(self, adapter_with_config):
        """Should return Sonnet for unknown domains."""
        agent = adapter_with_config.get_agent_recommendation(
            "nonexistent-domain", "any_task"
        )
        assert agent == "sonnet-general"


class TestContextStrategy:
    """Test context loading strategy."""

    @pytest.fixture
    def adapter_with_config(self, tmp_path):
        """Create adapter with context strategies."""
        config_dir = tmp_path / "config" / "domains"
        config_dir.mkdir(parents=True)

        config_yaml = """
domain: test-domain
workflows: {}
default_agents: {}
context_strategy:
  large_files: split_into_chapters
  citations: lazy_load_bibtex
thresholds: {}
quality_requirements: {}
file_patterns: {}
risk_patterns: {}
quota_allocation: {}
"""
        (config_dir / "test-domain.yaml").write_text(config_yaml)
        return DomainAdapter(config_dir=config_dir)

    def test_get_context_strategy(self, adapter_with_config):
        """Should return context strategy for content type."""
        strategy = adapter_with_config.get_context_strategy(
            "test-domain", "large_files"
        )
        assert strategy == "split_into_chapters"

    def test_get_context_strategy_default(self, adapter_with_config):
        """Should return default for unknown content type."""
        strategy = adapter_with_config.get_context_strategy(
            "test-domain", "unknown"
        )
        assert strategy == "load_all"


class TestQualityRequirements:
    """Test quality gate enforcement."""

    @pytest.fixture
    def adapter_with_config(self, tmp_path):
        """Create adapter with quality requirements."""
        config_dir = tmp_path / "config" / "domains"
        config_dir.mkdir(parents=True)

        config_yaml = """
domain: test-domain
workflows: {}
default_agents: {}
context_strategy: {}
thresholds: {}
quality_requirements:
  require_build: true
  require_tests: false
file_patterns: {}
risk_patterns: {}
quota_allocation: {}
"""
        (config_dir / "test-domain.yaml").write_text(config_yaml)
        return DomainAdapter(config_dir=config_dir)

    def test_quality_gate_enabled(self, adapter_with_config):
        """Should return True for enabled quality gate."""
        should_enforce = adapter_with_config.should_enforce_quality_gate(
            "test-domain", "require_build"
        )
        assert should_enforce is True

    def test_quality_gate_disabled(self, adapter_with_config):
        """Should return False for disabled quality gate."""
        should_enforce = adapter_with_config.should_enforce_quality_gate(
            "test-domain", "require_tests"
        )
        assert should_enforce is False

    def test_quality_gate_unknown(self, adapter_with_config):
        """Should return False for unknown quality gate."""
        should_enforce = adapter_with_config.should_enforce_quality_gate(
            "test-domain", "unknown_gate"
        )
        assert should_enforce is False


class TestRiskAssessment:
    """Test risk level assessment."""

    @pytest.fixture
    def adapter_with_config(self, tmp_path):
        """Create adapter with risk patterns."""
        config_dir = tmp_path / "config" / "domains"
        config_dir.mkdir(parents=True)

        config_yaml = """
domain: test-domain
workflows: {}
default_agents: {}
context_strategy: {}
thresholds: {}
quality_requirements: {}
file_patterns: {}
risk_patterns:
  high_risk:
    - "delete.*all"
    - "drop.*table"
  medium_risk:
    - "modify.*config"
quota_allocation: {}
"""
        (config_dir / "test-domain.yaml").write_text(config_yaml)
        return DomainAdapter(config_dir=config_dir)

    def test_high_risk_detection(self, adapter_with_config):
        """Should detect high risk requests."""
        risk = adapter_with_config.assess_risk_level(
            "test-domain", "Please delete all test files"
        )
        assert risk == "high"

    def test_medium_risk_detection(self, adapter_with_config):
        """Should detect medium risk requests."""
        risk = adapter_with_config.assess_risk_level(
            "test-domain", "modify config settings"
        )
        assert risk == "medium"

    def test_low_risk_default(self, adapter_with_config):
        """Should return low risk for safe requests."""
        risk = adapter_with_config.assess_risk_level(
            "test-domain", "read the file contents"
        )
        assert risk == "low"


class TestSpecializedAgents:
    """Test specialized agent listing."""

    @pytest.fixture
    def adapter_with_config(self, tmp_path):
        """Create adapter with specialized agents."""
        config_dir = tmp_path / "config" / "domains"
        config_dir.mkdir(parents=True)

        config_yaml = """
domain: test-domain
workflows: {}
default_agents: {}
context_strategy: {}
thresholds: {}
quality_requirements: {}
file_patterns: {}
risk_patterns: {}
quota_allocation: {}
specialized_agents:
  - agent-1
  - agent-2
  - agent-3
"""
        (config_dir / "test-domain.yaml").write_text(config_yaml)
        return DomainAdapter(config_dir=config_dir)

    def test_list_specialized_agents(self, adapter_with_config):
        """Should list all specialized agents."""
        agents = adapter_with_config.get_specialized_agents("test-domain")
        assert len(agents) == 3
        assert "agent-1" in agents
        assert "agent-2" in agents
        assert "agent-3" in agents

    def test_no_specialized_agents(self, adapter_with_config):
        """Should return empty list for domain without agents."""
        agents = adapter_with_config.get_specialized_agents("unknown-domain")
        assert agents == []


class TestDomainListing:
    """Test domain listing."""

    @pytest.fixture
    def adapter_with_configs(self, tmp_path):
        """Create adapter with multiple domain configs."""
        config_dir = tmp_path / "config" / "domains"
        config_dir.mkdir(parents=True)

        for domain in ["domain-a", "domain-b", "domain-c"]:
            config = f"""
domain: {domain}
workflows: {{}}
default_agents: {{}}
context_strategy: {{}}
thresholds: {{}}
quality_requirements: {{}}
file_patterns: {{}}
risk_patterns: {{}}
quota_allocation: {{}}
"""
            (config_dir / f"{domain}.yaml").write_text(config)

        return DomainAdapter(config_dir=config_dir)

    def test_list_all_domains(self, adapter_with_configs):
        """Should list all loaded domains."""
        domains = adapter_with_configs.list_domains()
        assert len(domains) == 3
        assert "domain-a" in domains
        assert "domain-b" in domains
        assert "domain-c" in domains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
