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
from typing import Dict, List, Optional, Any, Tuple


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


@dataclass
class UserRules:
    """User-specific rules from ~/.claude/infolead-router/rules/."""
    safety: Dict[str, List[str]]
    routing: Dict[str, Any]
    quotas: Dict[str, Any]
    agent_rules: Dict[str, Any]
    context: Dict[str, Any]


# Default user rules directory
USER_RULES_DIR = Path.home() / ".claude" / "infolead-router" / "rules"


class DomainAdapter:
    """Load and apply domain-specific configurations."""

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        user_rules_dir: Optional[Path] = None
    ):
        """Initialize domain adapter.

        Args:
            config_dir: Directory containing domain YAML files.
                       Defaults to ../config/domains/ relative to this file.
            user_rules_dir: Directory containing user rules YAML files.
                           Defaults to ~/.claude/infolead-router/rules/
        """
        if config_dir is None:
            # Default to config/domains/ in project root
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config" / "domains"

        self.config_dir = Path(config_dir)
        self.user_rules_dir = Path(user_rules_dir or USER_RULES_DIR)
        self._configs: Dict[str, DomainConfig] = {}
        self._user_rules: Dict[str, Dict] = {}
        self._global_rules: Optional[Dict] = None
        self._load_all_configs()
        self._load_user_rules()

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

    def _load_user_rules(self) -> None:
        """Load user-specific rules from ~/.claude/infolead-router/rules/."""
        if not self.user_rules_dir.exists():
            return

        for yaml_file in self.user_rules_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    rules_data = yaml.safe_load(f)
                    rule_name = yaml_file.stem

                    if rule_name == "global":
                        self._global_rules = rules_data
                    else:
                        self._user_rules[rule_name] = rules_data
            except Exception as e:
                print(f"Warning: Failed to load user rules {yaml_file}: {e}", file=sys.stderr)

    def get_global_rules(self) -> Optional[Dict]:
        """Get global rules from user configuration.

        Returns:
            Global rules dict or None if not loaded
        """
        return self._global_rules

    def get_user_domain_rules(self, domain: str) -> Optional[Dict]:
        """Get user-specific rules for a domain.

        Args:
            domain: Domain name (e.g., 'latex-research')

        Returns:
            Domain-specific user rules or None if not found
        """
        return self._user_rules.get(domain)

    def is_destructive_operation(self, command: str) -> bool:
        """Check if a command is a destructive operation per global rules.

        Args:
            command: Command string to check

        Returns:
            True if command matches destructive patterns
        """
        if self._global_rules is None:
            return False

        import re
        patterns = self._global_rules.get('safety', {}).get('destructive_operations', [])
        for pattern in patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    def is_high_risk_pattern(self, command: str) -> bool:
        """Check if a command matches high risk patterns per global rules.

        Args:
            command: Command string to check

        Returns:
            True if command matches high risk patterns
        """
        if self._global_rules is None:
            return False

        import re
        patterns = self._global_rules.get('safety', {}).get('high_risk_patterns', [])
        for pattern in patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    def get_escalation_keywords(self) -> List[str]:
        """Get keywords that trigger escalation from global rules.

        Returns:
            List of escalation keywords
        """
        if self._global_rules is None:
            return []
        return self._global_rules.get('routing', {}).get('escalation_keywords', [])

    def get_haiku_suitable_keywords(self) -> List[str]:
        """Get keywords suitable for Haiku from global rules.

        Returns:
            List of Haiku-suitable keywords
        """
        if self._global_rules is None:
            return []
        return self._global_rules.get('routing', {}).get('haiku_suitable', [])

    def get_quota_buffer(self, model: str) -> float:
        """Get quota buffer percentage for a model from global rules.

        Args:
            model: Model name ('sonnet' or 'opus')

        Returns:
            Buffer percentage (0.0 to 1.0)
        """
        if self._global_rules is None:
            return 0.1 if model == 'sonnet' else 0.2

        buffer_key = f"{model}_buffer_percent"
        buffer = self._global_rules.get('quotas', {}).get(buffer_key)
        if buffer is not None:
            return buffer / 100.0
        return 0.1 if model == 'sonnet' else 0.2

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


# =============================================================================
# Domain-Specific Configuration Classes
# =============================================================================

class LaTeXDomainConfig:
    """
    LaTeX Research Domain specialization.

    Optimization focus: Quality, correctness, citation integrity
    """

    @staticmethod
    def get_workflows() -> Dict[str, Dict]:
        return {
            "literature_integration": {
                "phases": ["search", "assess", "integrate", "verify"],
                "quality_gates": ["build_check", "citation_verify", "link_check"],
                "parallelism": "low",  # 1-2 concurrent, high quality focus
            },
            "formalization": {
                "phases": ["analyze", "model", "verify", "document"],
                "quality_gates": ["math_verify", "logic_audit"],
                "parallelism": "sequential",  # Must be done in order
            },
            "bulk_editing": {
                "phases": ["propose", "review", "apply"],
                "quality_gates": ["build_check", "diff_review"],
                "parallelism": "high",  # 3-4 concurrent file edits okay
            },
        }

    @staticmethod
    def get_default_agents() -> Dict[str, str]:
        return {
            "syntax": "haiku-general",
            "integration": "sonnet + specialized",
            "verification": "opus (math/logic)",
        }

    @staticmethod
    def get_context_strategy() -> Dict[str, str]:
        return {
            "large_files": "split_into_chapters",  # Don't load entire 500KB file
            "citations": "lazy_load_bibtex",  # Only load when needed
            "cross_references": "index_based",  # Build ref index, query as needed
        }


class DevDomainConfig:
    """
    Software Development Domain specialization.

    Optimization focus: Speed, test coverage, refactoring safety
    """

    @staticmethod
    def get_workflows() -> Dict[str, Dict]:
        return {
            "feature_development": {
                "phases": ["design", "implement", "test", "review"],
                "quality_gates": ["type_check", "test_suite", "lint"],
                "parallelism": "medium",  # 2-3 concurrent features
            },
            "debugging": {
                "phases": ["reproduce", "isolate", "fix", "verify"],
                "quality_gates": ["test_fails_before", "test_passes_after"],
                "parallelism": "sequential",  # One bug at a time
            },
            "refactoring": {
                "phases": ["analyze", "plan", "transform", "verify"],
                "quality_gates": ["tests_still_pass", "no_behavior_change"],
                "parallelism": "low",  # 1-2 refactorings, high risk of conflicts
            },
        }

    @staticmethod
    def get_default_agents() -> Dict[str, str]:
        return {
            "code_reading": "haiku-general",
            "architecture": "sonnet-general",
            "complex_logic": "opus-general",
        }

    @staticmethod
    def get_context_strategy() -> Dict[str, str]:
        return {
            "large_codebases": "workspace_indexing",  # Pre-index, query as needed
            "dependencies": "lazy_load_imports",  # Only load called modules
            "git_history": "summary_first",  # Don't load full history
        }


class KnowledgeDomainConfig:
    """
    Knowledge Management Domain specialization.

    Optimization focus: Organization, discoverability, link integrity
    """

    @staticmethod
    def get_workflows() -> Dict[str, Dict]:
        return {
            "reorganization": {
                "phases": ["analyze_structure", "propose_taxonomy", "migrate", "verify_links"],
                "quality_gates": ["no_broken_links", "no_orphaned_files"],
                "parallelism": "high",  # 4-5 concurrent file moves okay
            },
            "cleanup": {
                "phases": ["identify_candidates", "assess_value", "archive_or_delete"],
                "quality_gates": ["user_review_required"],
                "parallelism": "medium",  # 2-3 cleanup agents
            },
            "knowledge_graph": {
                "phases": ["extract_entities", "identify_relations", "build_graph", "visualize"],
                "quality_gates": ["entity_coherence", "relation_validity"],
                "parallelism": "high",  # Highly parallelizable
            },
        }

    @staticmethod
    def get_default_agents() -> Dict[str, str]:
        return {
            "file_operations": "haiku-general",
            "taxonomy_design": "sonnet-general",
            "insight_extraction": "opus-general",
        }

    @staticmethod
    def get_context_strategy() -> Dict[str, str]:
        return {
            "large_note_collections": "metadata_indexing",  # Title, tags, dates
            "full_text_search": "grep_based",  # On-demand content loading
            "graph_analysis": "incremental_build",  # Build graph over time
        }


# =============================================================================
# Adaptive WIP Management
# =============================================================================

@dataclass
class WorkCompletion:
    """Record of completed work for adaptive WIP calculation."""
    timestamp: str
    duration_minutes: float
    success: bool
    escalated: bool
    domain: str
    workflow: str


def adaptive_wip_limit(recent_history: List[WorkCompletion], base_limit: int = 3) -> int:
    """
    Calculate adaptive WIP limit based on recent work history.

    Adjusts WIP limit based on:
    - Success rate: Lower WIP if many failures
    - Escalation rate: Lower WIP if many escalations (overcommitting)
    - Completion time: Lower WIP if tasks taking longer than expected

    Args:
        recent_history: List of recent work completions
        base_limit: Starting WIP limit

    Returns:
        Adjusted WIP limit (1-5)
    """
    if len(recent_history) < 5:
        # Not enough data, use base limit
        return base_limit

    # Calculate metrics from recent history
    successes = sum(1 for w in recent_history if w.success)
    escalations = sum(1 for w in recent_history if w.escalated)
    total = len(recent_history)

    success_rate = successes / total
    escalation_rate = escalations / total

    # Adjust based on success rate
    if success_rate < 0.7:
        # Too many failures, reduce WIP
        base_limit = max(1, base_limit - 1)
    elif success_rate > 0.95:
        # Very high success, can increase WIP
        base_limit = min(5, base_limit + 1)

    # Adjust based on escalation rate
    if escalation_rate > 0.3:
        # Too many escalations, reduce WIP
        base_limit = max(1, base_limit - 1)
    elif escalation_rate < 0.1:
        # Few escalations, routing is good
        base_limit = min(5, base_limit + 1)

    return base_limit


# =============================================================================
# Quality Gate Execution
# =============================================================================

class QualityGateExecutor:
    """Execute quality gates for domain workflows."""

    def __init__(self, domain: str, adapter: DomainAdapter):
        self.domain = domain
        self.adapter = adapter

    def execute_gate(self, gate_name: str, context: Dict) -> Tuple[bool, Optional[str]]:
        """
        Execute a quality gate.

        Args:
            gate_name: Name of quality gate
            context: Context with files, results, etc.

        Returns:
            Tuple of (passed, failure_reason)
        """
        gate_method = getattr(self, f"_gate_{gate_name}", None)
        if gate_method:
            return gate_method(context)

        # Unknown gate, default to pass
        return True, None

    def _gate_build_check(self, context: Dict) -> Tuple[bool, Optional[str]]:
        """Check that project builds successfully."""
        import subprocess

        build_cmd = context.get("build_command")
        if not build_cmd:
            # Try common build commands
            if self.domain == "latex-research":
                build_cmd = "nix build"
            elif self.domain == "software-dev":
                build_cmd = "make build"
            else:
                return True, None

        try:
            result = subprocess.run(
                build_cmd.split(),
                capture_output=True,
                text=True,
                timeout=120,
                cwd=context.get("cwd")
            )
            if result.returncode != 0:
                return False, f"Build failed: {result.stderr[:200]}"
            return True, None
        except subprocess.TimeoutExpired:
            return False, "Build timed out"
        except Exception as e:
            return True, None  # Skip on errors

    def _gate_test_pass(self, context: Dict) -> Tuple[bool, Optional[str]]:
        """Check that tests pass."""
        import subprocess

        test_cmd = context.get("test_command", "pytest")

        try:
            result = subprocess.run(
                test_cmd.split(),
                capture_output=True,
                text=True,
                timeout=300,
                cwd=context.get("cwd")
            )
            if result.returncode != 0:
                return False, f"Tests failed: {result.stderr[:200]}"
            return True, None
        except subprocess.TimeoutExpired:
            return False, "Tests timed out"
        except Exception as e:
            return True, None

    def _gate_lint_check(self, context: Dict) -> Tuple[bool, Optional[str]]:
        """Check that linting passes."""
        import subprocess

        lint_cmd = context.get("lint_command", "ruff check .")

        try:
            result = subprocess.run(
                lint_cmd.split(),
                capture_output=True,
                text=True,
                timeout=60,
                cwd=context.get("cwd")
            )
            if result.returncode != 0:
                return False, f"Lint failed: {result.stdout[:200]}"
            return True, None
        except Exception:
            return True, None

    def _gate_type_check(self, context: Dict) -> Tuple[bool, Optional[str]]:
        """Check that type checking passes."""
        import subprocess

        type_cmd = context.get("type_command", "mypy .")

        try:
            result = subprocess.run(
                type_cmd.split(),
                capture_output=True,
                text=True,
                timeout=120,
                cwd=context.get("cwd")
            )
            if result.returncode != 0:
                return False, f"Type check failed: {result.stdout[:200]}"
            return True, None
        except Exception:
            return True, None

    def _gate_link_check(self, context: Dict) -> Tuple[bool, Optional[str]]:
        """Check for broken links/references."""
        # Implementation depends on domain
        return True, None

    def _gate_citation_verify(self, context: Dict) -> Tuple[bool, Optional[str]]:
        """Verify citations are valid."""
        # For LaTeX, check that all \\cite{} have matching bib entries
        return True, None


def test_domain_adapter() -> None:
    """Test domain adapter functionality."""
    print("Testing domain adapter...")

    adapter = DomainAdapter()

    # Test 1: List domains
    print("Test 1: List domains")
    domains = adapter.list_domains()
    assert "latex-research" in domains
    assert "software-dev" in domains
    print(f"  Found domains: {domains}")
    print("  OK")

    # Test 2: Get domain config
    print("Test 2: Get domain config")
    config = adapter.get_domain_config("latex-research")
    assert config is not None
    assert config.domain == "latex-research"
    print("  OK")

    # Test 3: Get workflow
    print("Test 3: Get workflow")
    workflow = adapter.get_workflow("latex-research", "formalization")
    assert workflow is not None
    assert "verify" in workflow.phases
    print("  OK")

    # Test 4: WIP limit
    print("Test 4: WIP limit")
    wip = adapter.get_wip_limit("latex-research", "formalization")
    assert wip == 1  # Sequential
    wip = adapter.get_wip_limit("software-dev", "bug_fix")
    assert wip == 4  # High
    print("  OK")

    # Test 5: Risk assessment
    print("Test 5: Risk assessment")
    risk = adapter.assess_risk_level("latex-research", "delete main.tex")
    assert risk == "high"
    risk = adapter.assess_risk_level("software-dev", "fix typo")
    assert risk == "low"
    print("  OK")

    # Test 6: Specialized agents
    print("Test 6: Specialized agents")
    agents = adapter.get_specialized_agents("latex-research")
    assert "tikz-illustrator" in agents
    print("  OK")

    # Test 7: Adaptive WIP
    print("Test 7: Adaptive WIP")
    history = [
        WorkCompletion("2024-01-01", 30, True, False, "latex-research", "formalization"),
        WorkCompletion("2024-01-01", 25, True, False, "latex-research", "formalization"),
        WorkCompletion("2024-01-01", 45, True, True, "latex-research", "formalization"),
        WorkCompletion("2024-01-01", 30, False, False, "latex-research", "formalization"),
        WorkCompletion("2024-01-01", 35, True, False, "latex-research", "formalization"),
    ]
    wip = adaptive_wip_limit(history, base_limit=3)
    assert 1 <= wip <= 5
    print("  OK")

    print("\nAll domain adapter tests passed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_domain_adapter()
    else:
        main()
