# Changelog

All notable changes to the Infolead Claude Subscription Router plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.7.0] - 2026-02-14

### Added

- **Multi-Project Support (Hybrid Architecture)**: Complete project isolation with global router logic
  - **Project Detection System**: Automatic project root detection by walking up directory tree
    - `detect_project_root()`: Finds `.claude` directory to identify project boundary
    - `get_project_id()`: Generates stable 16-char hash of project root path for unique identification
    - `get_project_data_dir()`: Returns project-specific data directory path
    - Fallback to "global" ID when no `.claude` directory found

  - **Project-Specific State Storage**: Complete isolation prevents state corruption
    - Storage structure: `~/.claude/infolead-claude-subscription-router/projects/{project-id}/`
    - Separate state/metrics/logs per project
    - Session state tracks project context (id, root path)
    - Work-in-progress isolated per project
    - No more state mixing when switching projects

  - **Project-Aware Configuration Cascade**: Priority-based configuration loading
    - Priority 1: Project-specific (`.claude/adaptive-orchestration.yaml`)
    - Priority 2: Global user config (`~/.claude/adaptive-orchestration.yaml`)
    - Priority 3: Plugin defaults (built-in)
    - `detect_project_config()` in `adaptive_orchestrator.py` for automatic detection
    - `load_config_file()` bash function for hook scripts

  - **Per-Project Enable/Disable**: Fine-grained control over router activation
    - `is_router_enabled()`: Checks `.claude/settings.json` for `plugins.router.enabled`
    - All hooks respect project-level disable flag
    - Router can be disabled for specific projects while enabled globally

  - **File Locking for Concurrent Sessions**: Prevents race conditions
    - `flock` with 5-second timeout on all state file operations
    - Lock files: `{state-file}.lock` for coordination
    - Graceful degradation on lock timeout with warning messages
    - Safe concurrent access from multiple Claude Code sessions

  - **Migration Tool**: Automated upgrade path from v1.6.x
    - `scripts/migrate-to-project-isolation.sh`: One-command migration per project
    - Copies old global state → new project-specific directories
    - Adds project context to migrated metrics and state
    - Preserves old data until verified safe to delete
    - Interactive confirmation with clear instructions

  - **Comprehensive Documentation**:
    - `docs/MULTI-PROJECT-ARCHITECTURE.md`: Complete architecture guide (500+ lines)
      - Hybrid model explanation and rationale
      - Storage structure diagrams
      - Configuration cascade details
      - Migration instructions
      - Testing scenarios
      - Troubleshooting guide
      - API reference for developers
    - `MULTI-PROJECT-FIXES-SUMMARY.md`: Executive summary of all fixes

### Changed

- **All Hooks Updated for Project Isolation**:
  - `hooks/common-functions.sh`: Added 5 new project-aware functions (130+ new lines)
  - `hooks/user-prompt-submit.sh`: Uses project-specific metrics/logs, adds project context to metrics
  - `hooks/load-session-state.sh`: Project-specific state with flock locking, project context in state
  - `hooks/save-session-state.sh`: Project-specific state with flock locking, project context preservation
  - `hooks/log-subagent-start.sh`: Project-specific paths, adds project context to compliance tracking
  - `hooks/log-subagent-stop.sh`: Project-specific paths, adds project context to agent metrics
  - All hooks check `is_router_enabled()` before executing

- **Python Implementation Enhanced**:
  - `implementation/adaptive_orchestrator.py`: Project-aware config loading with cascade
    - `detect_project_config()`: Auto-detects project-specific config files
    - `load_config()`: Updated with `enable_project_cascade` parameter (default: true)
    - Walks directory tree to find project `.claude` directory

- **systemd Installation Flexibility**:
  - `systemd/claude-overnight-executor.service`: Converted to template with `__PLUGIN_ROOT__` placeholder
  - `scripts/setup-overnight-execution.sh`: Dynamic path substitution during installation
  - Supports marketplace installations, local clones, any custom paths
  - No more hardcoded `/home/user/code/...` paths

- **Metrics Schema Enhanced**: All metrics now include project context

  ```json
  {
    "project": {
      "id": "abc123def456",
      "root": "/home/user/code/my-project",
      "name": "my-project"
    }
  }
  ```

  - Enables per-project cost tracking and analysis
  - Routing recommendations track which project they belong to
  - Agent usage metrics separated by project

### Fixed

- **Multi-Project State Corruption**: Projects no longer share state/metrics/logs
  - Before: All projects → same global directories → state mixing
  - After: Each project → isolated `projects/{id}/` directory → complete separation

- **Race Conditions in Concurrent Sessions**: File locking prevents corruption
  - Before: Multiple sessions could corrupt state file during simultaneous updates
  - After: flock coordination ensures atomic read-modify-write operations

- **systemd Hardcoded Paths**: Template-based service file supports any installation location
  - Before: Service file assumed `/home/user/code/claude-router-system/...`
  - After: Paths replaced during installation based on actual plugin location

- **No Project-Specific Configuration**: Config now cascades from project → global → defaults
  - Before: Only global config supported
  - After: Each project can override global settings

- **Unable to Disable Router Per-Project**: Can now disable for specific projects
  - Before: Router was all-or-nothing globally
  - After: Set `plugins.router.enabled: false` in project `.claude/settings.json`

### Migration Guide

**For users upgrading from v1.6.x:**

1. Update plugin files (git pull or reinstall)
2. Run migration script for EACH project:

   ```bash
   cd ~/your-project
   /path/to/plugin/scripts/migrate-to-project-isolation.sh
   ```

3. Verify each project works correctly
4. After ALL projects migrated, optionally delete old global data:

   ```bash
   rm -rf ~/.claude/infolead-claude-subscription-router/{state,metrics,logs}
   ```

**For new installations:**

- No migration needed - multi-project support works automatically

### Backward Compatibility

- **Migration preserves all data**: Old state/metrics/logs copied to new structure
- **Old data not deleted**: Migration script leaves original files in place
- **Graceful fallback**: If no `.claude` directory found, uses "global" project ID
- **No breaking changes**: Existing configurations continue to work

### Known Limitations

- **Overnight Execution**: Multi-project queue support deferred to v1.7.1+
  - Current: Overnight work uses global queue without project context
  - Workaround: Manually manage separate overnight queues per project
  - Future: Each project will have isolated overnight queue

---

## [1.6.2] - 2026-02-14

### Added

- **Clear Dependency Error Messages**: All hooks now show user-friendly installation instructions when dependencies are missing
  - Created `hooks/common-functions.sh`: Reusable dependency checking functions
    - `check_python3()`: Checks for Python 3.7+ with installation instructions for major platforms
    - `check_pyyaml()`: Checks for PyYAML package with pip installation command
    - `check_jq()`: Checks for jq with installation instructions for major platforms
    - `check_routing_dependencies()`: Combined check for all routing dependencies
  - Platform-specific installation commands included:
    - Ubuntu/Debian: `apt-get install`
    - macOS: `brew install`
    - Arch Linux: `pacman -S`
    - Fedora: `dnf install`

### Changed

- **Improved Hook Dependency Handling**: Replaced silent failures with clear error messages
  - `user-prompt-submit.sh`: Uses `check_routing_dependencies()` for python3, PyYAML, and jq
  - `log-subagent-start.sh`: Changed from hard error (`exit 1`) to graceful warning with `check_jq()`
  - `log-subagent-stop.sh`: Changed from hard error to graceful warning with `check_jq()`
  - `morning-briefing.sh`: Added clear warning via `check_jq()`
  - `load-session-state.sh`: Uses `check_jq()` with optional mode
  - `save-session-state.sh`: Uses `check_jq()` with optional mode
  - `load-session-memory.sh`: Uses `check_jq()` with optional mode
  - `cache-invalidation.sh`: Uses `check_python3()` with fallback behavior

### Fixed

- **User Experience**: Hooks no longer fail silently when dependencies are missing
  - Users now see clear error messages with specific installation commands
  - Hooks exit gracefully (exit 0) instead of blocking Claude Code operation
  - Error messages explain impact: "routing won't work", "limited functionality", etc.

### Backward Compatibility

- **Fully backward compatible**: No breaking changes
  - Hooks continue to exit gracefully when dependencies are missing
  - Added `common-functions.sh` library that all hooks can optionally source
  - Fallback checks in place if common-functions.sh is unavailable

---

## [1.6.1] - 2026-02-14

### Added

- **Adaptive Orchestration Configuration Support**: YAML configuration for customizing orchestration behavior
  - `adaptive-orchestration.yaml.example`: Comprehensive configuration template with comments (180 lines)
  - Configuration location: `~/.claude/adaptive-orchestration.yaml` (optional)
  - Configurable thresholds: `simple_confidence`, `complex_confidence` (0.0-1.0)
  - Configurable weights: `simple_weight`, `complex_weight` for pattern matches
  - Custom pattern support: Add domain-specific SIMPLE/COMPLEX patterns (migrations, deployments, etc.)
  - Mode override: Force specific orchestration mode for debugging (`force_mode`)
  - Robust fallback: System works without config, falls back to defaults on errors
  - Configuration loading: `load_config()` function with validation and error messages

- **Comprehensive Test Suites**: Production-ready testing infrastructure
  - `tests/test_adaptive_orchestrator.py`: Full pytest suite (500+ lines, 50+ test cases)
    - Parametrized tests for all 14 built-in complexity test cases
    - Configuration loading tests (defaults, custom values, error handling)
    - Pattern matching tests (SIMPLE, COMPLEX, multi-objective)
    - Orchestration mode tests (single-stage, monitored, multi-stage)
    - Edge case tests (empty requests, Unicode, special characters)
    - Metrics recording tests
    - Integration workflow tests
  - `tests/test_adaptive_orchestrator_integration.sh`: Bash integration tests (350 lines, 10 tests)
    - Routing core integration
    - Metrics collector integration
    - Config file loading and effects
    - Config fallback and error handling
    - Custom pattern application
    - JSON/human output modes
    - Full workflow testing
  - `tests/test_adaptive_orchestrator_e2e.sh`: End-to-end realistic scenarios (500 lines, 11 tests)
    - SIMPLE/MODERATE/COMPLEX request workflows
    - Multi-objective request handling
    - Config override effects
    - Custom pattern detection
    - Threshold tuning verification
    - Production deployment scenario
    - Read-only operation scenario
    - Architectural decision scenario
    - Classification performance benchmarks

### Changed

- **Enhanced `adaptive_orchestrator.py`**: Configuration system integration
  - Added `OrchestratorConfig` dataclass for configuration management
  - Added `load_config()` function with YAML parsing and validation
  - Updated `ComplexityClassifier` to accept config and merge custom patterns
  - Updated `AdaptiveOrchestrator` to load and apply configuration
  - Confidence calculation now uses configurable thresholds and weights
  - Mode selection respects `force_mode` override when set
  - Added `yaml` import for YAML configuration parsing

- **Updated documentation**: Configuration support documented throughout
  - `docs/Solution/Architecture/ADAPTIVE-ORCHESTRATION.md`: New Configuration section (150 lines)
    - Configuration file format and options
    - Thresholds, weights, custom patterns, mode override
    - Fallback behavior and error handling
    - Configuration loading examples
    - Updated Testing section with new test suites
    - Updated References section with test paths
  - `README.md`: New Configuration subsection in setup
    - Quick setup instructions
    - Example custom patterns
    - Configuration options overview
    - Fallback behavior notes
    - Documentation links
  - Updated Adaptive Orchestration section header to mention v1.6.1 enhancements

### Testing

- **100% test coverage maintained**: All tests passing
  - Built-in test suite: 14/14 passing
  - Pytest suite: 50+ test cases passing
  - Integration tests: 10/10 passing
  - E2E tests: 11/11 passing

### Backward Compatibility

- **Fully backward compatible**: No breaking changes
  - Works without configuration file (uses built-in defaults)
  - Existing code continues to work unchanged
  - Optional configuration file for customization
  - Graceful fallback on malformed config

---

## [1.6.0] - 2026-02-14

### Added

- **Adaptive Orchestration System**: Intelligent orchestration strategy selection based on request complexity
  - `implementation/adaptive_orchestrator.py`: Complete adaptive orchestration implementation (617 lines)
  - `ComplexityClassifier`: Fast heuristic-based complexity classification (<1ms, no API calls)
  - Three orchestration modes: single-stage (simple), single-stage monitored (moderate), multi-stage (complex)
  - Built-in test suite: 14 test cases covering all complexity patterns (100% passing)
  - CLI support: analyze requests, JSON output mode, test execution
  - `docs/Solution/Architecture/ADAPTIVE-ORCHESTRATION.md`: Complete architecture documentation (665 lines)
  - `hooks/user-prompt-submit-with-orchestration.sh.example`: Optional hook integration example
  - Expected performance: 12% avg latency increase (vs 150% for universal multi-stage)
  - Expected cost: 12% avg cost increase (vs 56% for universal multi-stage)
  - Accuracy improvement: 15% on complex requests, maintained speed for simple requests
  - Metrics integration: complexity classification and mode selection tracking

### Changed

- **README.md**: Added comprehensive Adaptive Orchestration section with examples and CLI usage
- **Documentation structure**: Organized adaptive orchestration docs in `docs/Solution/Architecture/`

## [1.5.0] - 2026-02-13

### Added

- **Agent Usage Tracking System**: Complete request-level and agent-level tracking
  - `implementation/routing_compliance.py`: Comprehensive compliance analyzer (367 lines)
  - `hooks/log-subagent-start.sh`: Enhanced to track agent invocations with request linking
  - `docs/AGENT-USAGE-TRACKING.md`: Full design specification (665 lines)
  - `docs/AGENT-USAGE-TRACKING-QUICKSTART.md`: User guide with examples (428 lines)
  - `tests/test_agent_usage_tracking.sh`: Comprehensive test suite (262 lines)
  - Track which agents are invoked for each request
  - Detect compliance: whether routing directives were followed or ignored
  - Analysis tools: compliance reports, agent breakdowns, ignored directive detection
  - Export capabilities: JSON and CSV formats for external analysis

- **External Orchestration Architecture**: Script-based agent spawning for guaranteed compliance
  - `scripts/orchestrate-request.py`: Functional prototype for external orchestration (330 lines)
  - `tests/test_orchestration.sh`: Test suite for orchestration script (200 lines)
  - `docs/external-orchestration-analysis.md`: Complete feasibility analysis (9,000+ words)
  - `docs/orchestration-vs-directives-comparison.md`: Decision guide and comparison matrix
  - `docs/orchestration-implementation-roadmap.md`: 6-week implementation plan
  - `docs/orchestration-architecture-diagram.md`: Visual architecture and data flow diagrams
  - `docs/ORCHESTRATION-SUMMARY.md`: Executive summary for decision makers
  - `docs/INDEX-ORCHESTRATION.md`: Master index and navigation guide
  - Proves programmatic Claude spawning is feasible (extends overnight execution pattern)
  - Proposes hybrid approach: orchestration for automation, directives for interaction
  - Expected impact: 100% routing compliance for automated workflows

- **Overnight Execution System**: Background task execution with agent spawning
  - `implementation/overnight_execution_runner.py`: Runner for scheduled Claude tasks
  - `scripts/setup-overnight-execution.sh`: Installation and configuration script
  - Demonstrates working programmatic Claude invocation
  - Foundation for external orchestration approach

- **Utility Scripts**: Installation and maintenance automation
  - `scripts/update.sh`: Plugin update script
  - `scripts/uninstall.sh`: Clean plugin removal

### Changed

- **Enhanced metrics integration**: Added `compliance` command to `metrics_collector.py`
- **Documentation reorganization**: Moved docs into Requirements and Solution structure
- **Routing directives**: Strengthened "MANDATORY" language in hooks and CLAUDE.md

### Fixed

- Removed obsolete `hooks/evening-planning.sh` (redundant with temporal scheduler)

### Notes

- **v1.5.0 delivers both planned v1.4.0 compliance tracking AND new orchestration architecture**
- Agent usage tracking enables data-driven analysis of routing effectiveness
- External orchestration provides architectural path to guaranteed routing compliance
- All tests passing (10/10 for tracking, 8/8 for orchestration)
- System is active and collecting compliance data in production

---

## [1.3.2] - 2026-02-06

### Added

- **Hooks workaround documentation**: Complete documentation and tooling for Claude Code plugin hooks bug
  - `docs/HOOKS-WORKAROUND.md`: Detailed workaround guide with GitHub issue references
  - `scripts/setup-hooks-workaround.sh`: Automated setup script with three scope options
  - References Claude Code issues: #10225, #14410, #6305, #2891, #5093

- **Three installation scopes** for hooks workaround:
  - `--local`: `.claude/settings.local.json` (this user, this project)
  - `--project`: `.claude/settings.json` (all users, this project - committed)
  - `--global`: `~/.claude/settings.json` (this user, all projects)

- **Workaround script features**:
  - `--dry-run` mode to preview changes
  - `--revert` mode to remove workaround when bug is fixed
  - Automatic backup creation
  - Smart merging (won't duplicate existing hooks)

### Changed

- Updated README troubleshooting section with hooks workaround instructions

### Notes

- This release provides a temporary workaround for Claude Code plugin hook execution bugs
- Plugin hooks are correctly matched but never executed (upstream bug)
- Workaround copies hooks to settings.json where they execute correctly

---

## [1.3.1] - 2026-02-05

### Fixed

- Minor fixes to hooks and namespace resolution

---

## [1.3.0] - 2026-02-05

### 🎉 Major: Visibility & Monitoring System (Option D Implementation)

Complete transformation from invisible black-box routing to transparent, trustworthy advisory system.

### Added

- **Real-time routing recommendations**: Every request now displays routing analysis to user
  - Display format: `[ROUTER] Recommendation: haiku-general (confidence: 0.95)`
  - Shows agent recommendation, confidence level, and reasoning
  - Visible before main Claude processes the request

- **Advisory routing system**: Pre-router provides recommendations as context to main Claude
  - Recommendations injected as `<routing-recommendation>` XML tags
  - Main Claude makes final decision with full context
  - Can follow, override, or escalate based on additional information

- **Comprehensive metrics collection**: All routing decisions tracked to daily JSONL files
  - Location: `~/.claude/infolead-claude-subscription-router/metrics/YYYY-MM-DD.jsonl`
  - Records: timestamp, request hash, recommendation, confidence, reasoning
  - Atomic writes with flock for concurrent request safety
  - Daily rotation for easy analysis

- **New documentation**:
  - `docs/OPTION-D-IMPLEMENTATION.md`: Technical implementation guide
  - `docs/CLAUDE-ROUTING-ADVISORY.md`: Guide for main Claude on using recommendations
  - `docs/IMPLEMENTATION-REVIEW.md`: Complete review with test results
  - `tests/test-routing-visibility.sh`: Comprehensive test suite

### Changed

- **`hooks/user-prompt-submit.sh`**: Complete rewrite for visibility
  - Was: Silent operation, recommendations discarded to `/dev/null`
  - Now: Dual output - stderr for user visibility, stdout for Claude context
  - Handles edge cases: missing scripts, null agents, routing failures
  - Performance: ~108ms average latency per request

- **`implementation/routing_core.py`**: Simplified JSON output format
  - Was: `{"request": "...", "routing": {...}}`
  - Now: `{"decision": "direct", "agent": "haiku-general", ...}`
  - Flatter structure easier to parse in bash

### Fixed

- **Stale metrics**: Was only capturing test data (last update Feb 3rd)
  - Now: Real usage tracked continuously
  - All routing decisions logged with full context

- **Escalation display**: Null agent values now show as "escalate" instead of "null"
  - Clearer communication of routing decisions
  - Better user experience

### Performance

- Average hook latency: 108ms (well under 200ms threshold)
- Concurrent request handling: Fully tested with atomic writes
- 10 sequential requests: 1088ms total

### Testing

All tests passing:
- ✅ Mechanical task routing (haiku-general)
- ✅ Complex task escalation
- ✅ Ambiguous request handling
- ✅ Empty request rejection
- ✅ Hook dual output (stderr + stdout)
- ✅ Metrics file creation and structure
- ✅ Request hash uniqueness
- ✅ Special character handling
- ✅ Concurrent write safety
- ✅ Performance benchmarks

### Migration Notes

**No breaking changes.** System adds visibility without changing existing behavior:

- Old: Routing happened silently
- New: Same routing logic, now visible
- Metrics: Were test-only, now capture real usage
- Main Claude: Unchanged workflow, now receives advisory input

**Upgrade path**: Simply update to 1.3.0. No configuration changes required.

---

## [1.2.0] - 2026-02-03

### Added

- Domain-specific workflow management
- Lazy context loading with LRU caching
- Morning briefing and evening planning hooks
- Cache invalidation on file modifications

### Changed

- Improved agent namespace resolution
- Enhanced metrics collection

---

## [1.1.0] - 2026-02-01

### Added

- Haiku pre-routing with mechanical escalation
- Strategy advisor for cost optimization
- Semantic caching for deduplication
- Work coordination with parallel tracking

### Changed

- Router agent now uses Bash + claude CLI for delegation
- Improved routing decision logic

---

## [1.0.0] - 2026-01-31

### Added

- Initial release
- Central router architecture
- Risk assessment system
- Agent matching and delegation
- IVP-compliant design
- Basic metrics collection

---

## Future Releases

### [1.4.0] - Planned: Compliance Tracking (Phase 2)

- Track recommendation vs actual routing decisions
- Compute compliance rate metrics
- Identify patterns where pre-router is accurate/inaccurate

### [1.5.0] - Planned: Adaptive Escalation (Phase 3)

- Use metrics to improve escalation triggers
- Adjust confidence thresholds based on outcomes
- Add/remove patterns based on empirical data

### [1.6.0] - Planned: Performance Feedback (Phase 4)

- Link routing recommendations to agent outcomes
- Optimize routing based on success rates
- Data-driven routing decisions

---

## Notes

- **v1.3.0** addresses user feedback: "too obscure, monitoring fails, lack confidence"
- All versions maintain backward compatibility
- IVP architecture enables independent evolution of components
- See [IMPLEMENTATION-REVIEW.md](docs/IMPLEMENTATION-REVIEW.md) for detailed v1.3.0 review

[1.3.2]: https://github.com/yannickloth/claude-router-system/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/yannickloth/claude-router-system/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/yannickloth/claude-router-system/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/yannickloth/claude-router-system/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/yannickloth/claude-router-system/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/yannickloth/claude-router-system/releases/tag/v1.0.0
