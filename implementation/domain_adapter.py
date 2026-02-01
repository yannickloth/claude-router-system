"""
Domain Adapter - Load and apply domain-specific configurations

Implements adaptive work coordination based on domain workflows, quality gates,
and context strategies.

CLI Usage:
    # Detect domain from current directory
    python3 domain_adapter.py detect

    # Get workflow for a specific domain
    python3 domain_adapter.py workflow latex-research literature_integration

    # Get agent recommendation
    python3 domain_adapter.py agent latex-research formalization

Change Driver: DOMAIN_INTEGRATION
Changes when: Domain-specific requirements evolve
"""

import os
import sys
import yaml
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class ParallelismLevel(Enum):
    """Work-in-progress parallelism levels."""
    SEQUENTIAL = "sequential"  # 1 task at a time
    LOW = "low"                # 1-2 concurrent
    MEDIUM = "medium"          # 2-3 concurrent
    HIGH = "high"              # 3-4 concurrent


@dataclass
class Workflow:
    """Domain workflow definition."""
    name: str
    phases: List[str]
    quality_gates: List[str]
    parallelism: ParallelismLevel


@dataclass
class DomainConfig:
    """Domain-specific configuration."""
    domain: str
    workflows: Dict[str, Workflow]
    default_agents: Dict[str, str]
    context_strategy: Dict[str, str]
    thresholds: Dict[str, int]
    quality_requirements: Dict[str, bool]
    file_patterns: Dict[str, str]
    risk_patterns: Dict[str, List[str]]
    quota_allocation: Dict[str, int]
    specialized_agents: Optional[List[str]] = None


class DomainAdapter:
    """Load and apply domain-specific configurations."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize domain adapter.

        Args:
            config_dir: Directory containing domain YAML files.
                       Defaults to ../config/domains/ relative to this file.
        """
        if config_dir is None:
            # Default to config/domains/ in project root
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config" / "domains"

        self.config_dir = Path(config_dir)
        self._configs: Dict[str, DomainConfig] = {}
        self._load_all_configs()

    def _load_all_configs(self) -> None:
        """Load all domain configuration files."""
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Domain config directory not found: {self.config_dir}")

        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    domain_config = self._parse_config(config_data)
                    self._configs[domain_config.domain] = domain_config
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}", file=sys.stderr)

    def _parse_config(self, data: Dict[str, Any]) -> DomainConfig:
        """Parse YAML config data into DomainConfig object."""
        # Parse workflows
        workflows = {}
        for workflow_name, workflow_data in data.get('workflows', {}).items():
            parallelism = ParallelismLevel(workflow_data['parallelism'])
            workflows[workflow_name] = Workflow(
                name=workflow_name,
                phases=workflow_data['phases'],
                quality_gates=workflow_data['quality_gates'],
                parallelism=parallelism
            )

        return DomainConfig(
            domain=data['domain'],
            workflows=workflows,
            default_agents=data.get('default_agents', {}),
            context_strategy=data.get('context_strategy', {}),
            thresholds=data.get('thresholds', {}),
            quality_requirements=data.get('quality_requirements', {}),
            file_patterns=data.get('file_patterns', {}),
            risk_patterns=data.get('risk_patterns', {}),
            quota_allocation=data.get('quota_allocation', {}),
            specialized_agents=data.get('specialized_agents', [])
        )

    def detect_domain(self, path: Optional[Path] = None) -> Optional[str]:
        """Detect domain from file patterns and project structure.

        Args:
            path: Directory to analyze. Defaults to current directory.

        Returns:
            Domain name if detected, None otherwise.
        """
        if path is None:
            path = Path.cwd()

        # Check for domain indicators
        indicators = {
            'latex-research': [
                ('*.tex', 'main_document'),
                ('*.bib', 'bibliography'),
                ('.claude/agents/', 'specialized_agents')
            ],
            'software-dev': [
                ('*.py', 'source_code'),
                ('test_*.py', 'tests'),
                ('pytest.ini', 'test_framework'),
                ('setup.py', 'package')
            ],
            'knowledge-mgmt': [
                ('*.md', 'notes'),
                ('*index.md', 'indexes')
            ]
        }

        # Score each domain
        scores = {domain: 0 for domain in indicators.keys()}

        for domain, patterns in indicators.items():
            for pattern, _ in patterns:
                # Check if pattern exists in directory
                if pattern.endswith('/'):
                    # Directory check
                    if (path / pattern.rstrip('/')).exists():
                        scores[domain] += 1
                else:
                    # File pattern check
                    if list(path.glob(pattern)):
                        scores[domain] += 1

        # Return domain with highest score, if any
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)

        return None

    def get_domain_config(self, domain: str) -> Optional[DomainConfig]:
        """Get configuration for a specific domain.

        Args:
            domain: Domain name (e.g., 'latex-research')

        Returns:
            DomainConfig if found, None otherwise.
        """
        return self._configs.get(domain)

    def get_workflow(self, domain: str, workflow_name: str) -> Optional[Workflow]:
        """Get a specific workflow from a domain.

        Args:
            domain: Domain name
            workflow_name: Workflow identifier

        Returns:
            Workflow if found, None otherwise.
        """
        config = self.get_domain_config(domain)
        if config is None:
            return None
        return config.workflows.get(workflow_name)

    def get_wip_limit(self, domain: str, workflow_name: str) -> int:
        """Get recommended WIP limit for a workflow.

        Args:
            domain: Domain name
            workflow_name: Workflow identifier

        Returns:
            Maximum concurrent tasks (1-4)
        """
        workflow = self.get_workflow(domain, workflow_name)
        if workflow is None:
            return 2  # Default medium parallelism

        # Map parallelism level to WIP limit
        limits = {
            ParallelismLevel.SEQUENTIAL: 1,
            ParallelismLevel.LOW: 2,
            ParallelismLevel.MEDIUM: 3,
            ParallelismLevel.HIGH: 4
        }

        return limits.get(workflow.parallelism, 2)

    def get_agent_recommendation(self, domain: str, task_type: str) -> str:
        """Get recommended agent for a task type.

        Args:
            domain: Domain name
            task_type: Type of task (e.g., 'formalization', 'syntax')

        Returns:
            Agent name (e.g., 'opus-general', 'haiku-general')
        """
        config = self.get_domain_config(domain)
        if config is None:
            return "sonnet-general"  # Safe default

        return config.default_agents.get(task_type, "sonnet-general")

    def get_context_strategy(self, domain: str, content_type: str) -> str:
        """Get context loading strategy for content type.

        Args:
            domain: Domain name
            content_type: Type of content (e.g., 'large_files', 'citations')

        Returns:
            Strategy name (e.g., 'split_into_chapters', 'lazy_load_bibtex')
        """
        config = self.get_domain_config(domain)
        if config is None:
            return "load_all"  # Default strategy

        return config.context_strategy.get(content_type, "load_all")

    def should_enforce_quality_gate(self, domain: str, gate_name: str) -> bool:
        """Check if a quality gate should be enforced.

        Args:
            domain: Domain name
            gate_name: Quality gate identifier

        Returns:
            True if gate should be enforced
        """
        config = self.get_domain_config(domain)
        if config is None:
            return False

        return config.quality_requirements.get(gate_name, False)

    def assess_risk_level(self, domain: str, request: str) -> str:
        """Assess risk level of a request.

        Args:
            domain: Domain name
            request: User request text

        Returns:
            Risk level: 'high', 'medium', or 'low'
        """
        config = self.get_domain_config(domain)
        if config is None:
            return "medium"  # Conservative default

        import re

        # Check high risk patterns first
        for pattern in config.risk_patterns.get('high_risk', []):
            if re.search(pattern, request, re.IGNORECASE):
                return "high"

        # Check medium risk patterns
        for pattern in config.risk_patterns.get('medium_risk', []):
            if re.search(pattern, request, re.IGNORECASE):
                return "medium"

        # Default to low risk
        return "low"

    def get_specialized_agents(self, domain: str) -> List[str]:
        """Get list of specialized agents available for domain.

        Args:
            domain: Domain name

        Returns:
            List of specialized agent names
        """
        config = self.get_domain_config(domain)
        if config is None:
            return []

        return config.specialized_agents or []

    def list_domains(self) -> List[str]:
        """List all available domains.

        Returns:
            List of domain names
        """
        return list(self._configs.keys())


def main():
    """CLI interface for domain adapter."""
    if len(sys.argv) < 2:
        print("Usage: python3 domain_adapter.py <command> [args]")
        print("\nCommands:")
        print("  detect              - Detect domain from current directory")
        print("  workflow <domain> <workflow>  - Get workflow info")
        print("  agent <domain> <task_type>    - Get agent recommendation")
        print("  list                - List all available domains")
        sys.exit(1)

    adapter = DomainAdapter()
    command = sys.argv[1]

    if command == "detect":
        domain = adapter.detect_domain()
        if domain:
            print(f"Detected domain: {domain}")
        else:
            print("No domain detected")

    elif command == "workflow":
        if len(sys.argv) < 4:
            print("Usage: domain_adapter.py workflow <domain> <workflow_name>")
            sys.exit(1)

        domain = sys.argv[2]
        workflow_name = sys.argv[3]
        workflow = adapter.get_workflow(domain, workflow_name)

        if workflow:
            print(f"Workflow: {workflow.name}")
            print(f"Phases: {', '.join(workflow.phases)}")
            print(f"Quality gates: {', '.join(workflow.quality_gates)}")
            print(f"Parallelism: {workflow.parallelism.value}")
            print(f"WIP limit: {adapter.get_wip_limit(domain, workflow_name)}")
        else:
            print(f"Workflow '{workflow_name}' not found in domain '{domain}'")

    elif command == "agent":
        if len(sys.argv) < 4:
            print("Usage: domain_adapter.py agent <domain> <task_type>")
            sys.exit(1)

        domain = sys.argv[2]
        task_type = sys.argv[3]
        agent = adapter.get_agent_recommendation(domain, task_type)
        print(f"Recommended agent: {agent}")

    elif command == "list":
        domains = adapter.list_domains()
        print("Available domains:")
        for domain in domains:
            print(f"  - {domain}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
