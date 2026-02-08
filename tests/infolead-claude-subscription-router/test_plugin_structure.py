"""
Tests for Claude Code plugin structure validation.

Verifies:
- plugin.json is valid
- hooks.json references exist
- Agent files have valid frontmatter
- All paths resolve correctly
"""

import json
import re
import pytest
from pathlib import Path

# Plugin root (now inside plugins directory)
PLUGIN_ROOT = Path(__file__).parent.parent.parent / "plugins" / "infolead-claude-subscription-router"
PLUGIN_DIR = PLUGIN_ROOT  # plugin.json is now in the plugin root
HOOKS_DIR = PLUGIN_ROOT / "hooks"
AGENTS_DIR = PLUGIN_ROOT / "agents"


class TestPluginJson:
    """Test plugin.json validity."""

    @pytest.fixture
    def plugin_json(self):
        """Load plugin.json."""
        plugin_file = PLUGIN_DIR / "plugin.json"
        assert plugin_file.exists(), "plugin.json must exist"
        with open(plugin_file) as f:
            return json.load(f)

    def test_plugin_json_exists(self):
        """Plugin.json must exist in .claude-plugin/."""
        plugin_file = PLUGIN_DIR / "plugin.json"
        assert plugin_file.exists(), "plugin.json must exist in .claude-plugin/"

    def test_required_fields(self, plugin_json):
        """Plugin must have required fields."""
        required = ["name", "version", "description"]
        for field in required:
            assert field in plugin_json, f"plugin.json must have '{field}' field"

    def test_version_format(self, plugin_json):
        """Version must be semver format."""
        version = plugin_json.get("version", "")
        assert re.match(r"^\d+\.\d+\.\d+$", version), f"Version '{version}' must be semver"

    def test_hooks_path_valid(self, plugin_json):
        """Hooks must be either inline dict or a valid file path."""
        hooks = plugin_json.get("hooks")
        if hooks is None:
            return
        if isinstance(hooks, dict):
            # Inline hooks in plugin.json - valid format
            assert len(hooks) > 0, "Hooks dict must not be empty"
            return
        # String path - resolve relative to plugin.json location
        resolved = (PLUGIN_DIR / hooks).resolve()
        assert resolved.exists(), f"Hooks file not found: {resolved}"

    def test_pretooluse_hook_exists(self, plugin_json):
        """Plugin must have PreToolUse hook for write permission approval."""
        hooks = plugin_json.get("hooks", {})
        assert "PreToolUse" in hooks, "plugin.json must define PreToolUse hook"
        pre_hooks = hooks["PreToolUse"]
        assert len(pre_hooks) > 0, "PreToolUse must have at least one config"
        matchers = [c.get("matcher", "") for c in pre_hooks]
        assert any("Write" in m for m in matchers), (
            "PreToolUse must match Write tool"
        )

    def test_pretooluse_hook_script_exists(self, plugin_json):
        """PreToolUse hook command script must exist."""
        hooks = plugin_json.get("hooks", {})
        for config in hooks.get("PreToolUse", []):
            for hook in config.get("hooks", []):
                if hook.get("type") == "command":
                    command = hook.get("command", "")
                    script_path = command.replace(
                        "${CLAUDE_PLUGIN_ROOT}",
                        str(PLUGIN_ROOT)
                    )
                    assert Path(script_path).exists(), (
                        f"PreToolUse hook script not found: {script_path}"
                    )


class TestHooksJson:
    """Test hooks.json validity."""

    @pytest.fixture
    def hooks_json(self):
        """Load hooks.json."""
        hooks_file = HOOKS_DIR / "hooks.json"
        if not hooks_file.exists():
            pytest.skip("No hooks.json file")
        with open(hooks_file) as f:
            return json.load(f)

    def test_hooks_json_structure(self, hooks_json):
        """Hooks must have valid structure."""
        assert "hooks" in hooks_json, "hooks.json must have 'hooks' key"

    def test_hook_commands_exist(self, hooks_json):
        """Hook command scripts must exist."""
        for event_type, hook_configs in hooks_json.get("hooks", {}).items():
            for config in hook_configs:
                for hook in config.get("hooks", []):
                    if hook.get("type") == "command":
                        command = hook.get("command", "")
                        # Replace plugin root variable
                        script_path = command.replace(
                            "${CLAUDE_PLUGIN_ROOT}",
                            str(PLUGIN_ROOT)
                        )
                        # Check if script exists
                        script_file = Path(script_path)
                        assert script_file.exists(), (
                            f"Hook script not found: {script_path}"
                        )

    def test_hook_timeouts_reasonable(self, hooks_json):
        """Hook timeouts must be reasonable (1-60 seconds)."""
        for event_type, hook_configs in hooks_json.get("hooks", {}).items():
            for config in hook_configs:
                for hook in config.get("hooks", []):
                    timeout = hook.get("timeout", 5)
                    assert 1 <= timeout <= 60, (
                        f"Hook timeout {timeout} must be between 1-60s"
                    )


class TestAgentFiles:
    """Test agent file validity."""

    @pytest.fixture
    def agent_files(self):
        """Get all agent markdown files."""
        return list(AGENTS_DIR.glob("*.md"))

    def test_agents_directory_exists(self):
        """Agents directory must exist."""
        assert AGENTS_DIR.exists(), "agents/ directory must exist"

    def test_agents_have_frontmatter(self, agent_files):
        """All agent files must have YAML frontmatter."""
        for agent_file in agent_files:
            content = agent_file.read_text()
            assert content.startswith("---"), (
                f"{agent_file.name} must start with YAML frontmatter (---)"
            )
            # Must have closing ---
            parts = content.split("---", 2)
            assert len(parts) >= 3, (
                f"{agent_file.name} must have closing --- for frontmatter"
            )

    def test_required_frontmatter_fields(self, agent_files):
        """Agent frontmatter must have required fields."""
        required = ["name", "description", "model", "tools"]

        for agent_file in agent_files:
            content = agent_file.read_text()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue

            frontmatter = parts[1]

            for field in required:
                assert f"{field}:" in frontmatter, (
                    f"{agent_file.name} frontmatter must have '{field}' field"
                )

    def test_model_values_valid(self, agent_files):
        """Agent model must be haiku, sonnet, or opus."""
        valid_models = {"haiku", "sonnet", "opus"}

        for agent_file in agent_files:
            content = agent_file.read_text()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue

            frontmatter = parts[1]
            for line in frontmatter.split("\n"):
                if line.startswith("model:"):
                    model = line.split(":", 1)[1].strip()
                    assert model in valid_models, (
                        f"{agent_file.name} has invalid model '{model}'"
                    )

    def test_agent_name_matches_filename(self, agent_files):
        """Agent name in frontmatter should match filename."""
        for agent_file in agent_files:
            expected_name = agent_file.stem  # filename without extension
            content = agent_file.read_text()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue

            frontmatter = parts[1]
            for line in frontmatter.split("\n"):
                if line.startswith("name:"):
                    actual_name = line.split(":", 1)[1].strip()
                    assert actual_name == expected_name, (
                        f"{agent_file.name}: name '{actual_name}' "
                        f"should match filename '{expected_name}'"
                    )


class TestAgentPermissionMode:
    """Test that agents with Write/Edit tools have permissionMode set."""

    WRITE_EDIT_AGENTS = {
        "haiku-general", "sonnet-general", "opus-general",
        "work-coordinator", "temporal-scheduler"
    }
    READ_ONLY_AGENTS = {
        "router", "router-escalation", "haiku-pre-router",
        "planner", "strategy-advisor", "probabilistic-router"
    }

    @pytest.fixture
    def agent_files(self):
        """Get all agent markdown files."""
        return list(AGENTS_DIR.glob("*.md"))

    def test_write_agents_have_permission_mode(self, agent_files):
        """Agents with Write/Edit tools must have permissionMode: acceptEdits."""
        for agent_file in agent_files:
            agent_name = agent_file.stem
            if agent_name not in self.WRITE_EDIT_AGENTS:
                continue
            content = agent_file.read_text()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            frontmatter = parts[1]
            assert "permissionMode:" in frontmatter, (
                f"{agent_name} has Write/Edit tools but missing permissionMode"
            )
            assert "acceptEdits" in frontmatter, (
                f"{agent_name} permissionMode should be 'acceptEdits'"
            )

    def test_readonly_agents_no_permission_mode(self, agent_files):
        """Read-only agents should NOT have permissionMode set."""
        for agent_file in agent_files:
            agent_name = agent_file.stem
            if agent_name not in self.READ_ONLY_AGENTS:
                continue
            content = agent_file.read_text()
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            frontmatter = parts[1]
            assert "permissionMode:" not in frontmatter, (
                f"{agent_name} is read-only and should NOT have permissionMode"
            )


class TestHookScripts:
    """Test hook script validity."""

    @pytest.fixture
    def hook_scripts(self):
        """Get all hook shell scripts."""
        return list(HOOKS_DIR.glob("*.sh"))

    def test_hook_scripts_executable(self, hook_scripts):
        """Hook scripts should be executable (for git)."""
        import os
        import stat

        for script in hook_scripts:
            mode = os.stat(script).st_mode
            is_executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
            assert is_executable, f"{script.name} should be executable"

    def test_hook_scripts_have_shebang(self, hook_scripts):
        """Hook scripts must have shebang."""
        for script in hook_scripts:
            content = script.read_text()
            assert content.startswith("#!/"), (
                f"{script.name} must have shebang (#!/bin/bash)"
            )

    def test_hook_scripts_check_jq(self, hook_scripts):
        """Hook scripts that use jq must check for it."""
        for script in hook_scripts:
            content = script.read_text()
            if "jq " in content or "jq -" in content:
                assert "command -v jq" in content or "which jq" in content, (
                    f"{script.name} uses jq but doesn't check for it"
                )


class TestImplementationFiles:
    """Test implementation Python files."""

    @pytest.fixture
    def impl_dir(self):
        """Get implementation directory."""
        return PLUGIN_ROOT / "implementation"

    @pytest.fixture
    def impl_files(self, impl_dir):
        """Get all implementation files."""
        return list(impl_dir.glob("*.py"))

    def test_implementation_directory_exists(self, impl_dir):
        """Implementation directory must exist."""
        assert impl_dir.exists(), "implementation/ directory must exist"

    def test_implementation_files_importable(self, impl_dir, impl_files):
        """Implementation files should be syntactically valid."""
        import sys
        import ast

        for py_file in impl_files:
            content = py_file.read_text()
            try:
                ast.parse(content)
            except SyntaxError as e:
                pytest.fail(f"{py_file.name} has syntax error: {e}")


class TestConfigDomains:
    """Test domain configuration files."""

    @pytest.fixture
    def config_dir(self):
        """Get config directory."""
        return PLUGIN_ROOT / "config" / "domains"

    def test_domain_configs_valid_yaml(self, config_dir):
        """Domain config files must be valid YAML."""
        if not config_dir.exists():
            pytest.skip("No config/domains directory")

        import yaml

        for yaml_file in config_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"{yaml_file.name} is invalid YAML: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
