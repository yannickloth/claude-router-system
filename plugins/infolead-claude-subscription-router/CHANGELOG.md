# Changelog

All notable changes to the Infolead Claude Subscription Router plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
