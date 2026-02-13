# Testing Guide for Infolead Claude Subscription Router

## Quick Start

```bash
# Run ALL automated tests (recommended)
./tests/infolead-claude-subscription-router/run_all_tests.sh

# Or run individually:

# Unit tests (224 tests)
nix-shell -p python312Packages.pytest python312Packages.pyyaml --run "pytest tests/infolead-claude-subscription-router/ -v"

# Hook tests (10 tests)
./tests/infolead-claude-subscription-router/test_hooks.sh

# E2E plugin integration (12 tests)
./tests/infolead-claude-subscription-router/test_e2e_plugin.sh

# Run specific test file
nix-shell -p python312Packages.pytest python312Packages.pyyaml --run "pytest tests/infolead-claude-subscription-router/test_routing_core.py -v"
```

## Test Layers

### Layer 1: Unit Tests (Automated)

**Location:** `tests/infolead-claude-subscription-router/test_*.py`

**What they test:**
- `test_routing_core.py` - Escalation logic, pattern matching, confidence scoring
- `test_semantic_cache.py` - Cache storage, similarity matching, TTL expiration
- `test_session_state.py` - State persistence, search deduplication
- `test_work_coordinator.py` - WIP limits, task scheduling, dependencies
- `test_domain_adapter.py` - Domain detection, workflow configuration
- `test_validation_executor.py` - Syntax validation, build detection
- `test_file_locking.py` - Concurrent file access, lock acquisition
- `test_lazy_context_loader.py` - Section indexing, LRU cache
- `test_plugin_structure.py` - Plugin JSON validity, agent frontmatter
- `test_metrics_collector.py` - Metric recording, aggregation
- `test_hooks.py` - Hook script execution (pytest wrapper)

**Run:**
```bash
nix-shell -p python312Packages.pytest python312Packages.pyyaml --run "pytest tests/infolead-claude-subscription-router/ -v --tb=short"
```

**Expected:** 224 tests pass

---

### Layer 2: Hook Script Tests (Automated)

**Location:** `tests/infolead-claude-subscription-router/test_hooks.sh`

**What they test:**
- Basic start/stop hook functionality
- Duration calculation accuracy
- Concurrent execution (10 parallel agents)
- Special characters in agent IDs
- Model tier detection for cost estimation
- Metrics JSONL format validity
- Missing field handling
- Lock file cleanup
- stderr output format

**Run:**
```bash
./tests/infolead-claude-subscription-router/test_hooks.sh
```

**Expected:** 10 tests pass

---

### Layer 3: Integration Tests (Automated)

**Location:** `tests/infolead-claude-subscription-router/test_integration.py`

**What they test:**
- Routing decisions flow correctly
- Domain detection works
- Work coordination enforces WIP limits
- Session state persists across manager instances
- Semantic cache stores and retrieves
- End-to-end workflow simulation

**Run:**
```bash
nix-shell -p python312Packages.pytest python312Packages.pyyaml --run "pytest tests/infolead-claude-subscription-router/test_integration.py -v"
```

---

### Layer 4: Plugin Loading Test (Manual)

**Purpose:** Verify Claude Code recognizes the plugin

**Steps:**
1. Install plugin:
   ```bash
   # Option A: Symlink (for development)
   ln -s /home/nicky/code/claude-router-system/plugins/infolead-claude-subscription-router/.claude-plugin ~/.claude/plugins/infolead-claude-subscription-router

   # Option B: Copy (for testing isolation)
   cp -r /home/nicky/code/claude-router-system/plugins/infolead-claude-subscription-router/.claude-plugin ~/.claude/plugins/infolead-claude-subscription-router
   ```

2. Start Claude Code and check plugin loaded:
   ```
   /plugins
   ```

   Expected output should list `infolead-claude-subscription-router`

3. Verify agents available:
   ```
   /agents
   ```

   Should show: `infolead-claude-subscription-router:haiku-general`, `infolead-claude-subscription-router:sonnet-general`, `infolead-claude-subscription-router:opus-general`, `infolead-claude-subscription-router:router`, etc.

---

### Layer 5: Live Routing Test (Manual)

**Purpose:** Verify routing decisions work in real Claude Code session

**Test Cases:**

| Input | Expected Route | Verify |
|-------|----------------|--------|
| "Fix typo in README.md" | infolead-claude-subscription-router:haiku-general | Check stderr shows `→ haiku-general` |
| "Design a new API architecture" | escalate to sonnet | Check stderr shows escalation |
| "Delete all temp files" | escalate to sonnet | Bulk destructive should escalate |

**Steps:**
1. Open Claude Code in a project with the plugin
2. Say: "Fix typo in README.md"
3. Watch stderr for routing decision:
   ```
   [routing] → infolead-claude-subscription-router:haiku-general (agent-abc123)
   ```
4. Verify the correct model was used (check response quality)

---

### Layer 6: Hook Event Test (Manual)

**Purpose:** Verify hooks fire during actual agent execution

**Steps:**
1. Clear existing logs:
   ```bash
   rm -f ~/.claude/logs/routing.log
   rm -f ~/.claude/infolead-claude-subscription-router/metrics/$(date +%Y-%m-%d).jsonl
   ```

2. Run a task that spawns an agent:
   ```
   [In Claude Code] "List files in current directory"
   ```

3. Verify log entries:
   ```bash
   cat ~/.claude/logs/routing.log
   ```

   Expected:
   ```
   2026-02-03T12:34:56Z | START | infolead-claude-subscription-router:haiku-general | agent-abc123 | /path/to/project
   2026-02-03T12:34:58Z | STOP  | infolead-claude-subscription-router:haiku-general | agent-abc123 | 2s | success
   ```

4. Verify metrics:
   ```bash
   cat ~/.claude/infolead-claude-subscription-router/metrics/$(date +%Y-%m-%d).jsonl | jq .
   ```

   Expected: JSON entries with `event`, `agent_type`, `model_tier`, `duration_seconds`

---

### Layer 7: Cross-Session State Test (Manual)

**Purpose:** Verify state persists across Claude Code restarts

**Steps:**
1. In Claude Code session 1:
   ```
   [Perform some searches and tasks]
   ```

2. Check state was saved:
   ```bash
   cat ~/.claude/infolead-claude-subscription-router/memory/session-state.json
   ```

3. Close Claude Code completely

4. Reopen Claude Code and verify:
   - Previous search doesn't re-execute (deduplication)
   - Session context is restored

---

## CI/CD Integration

For automated testing in CI:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: cachix/install-nix-action@v25

      - name: Run unit tests
        run: |
          nix-shell -p python312Packages.pytest python312Packages.pyyaml \
            --run "pytest tests/ -v --tb=short"

      - name: Run hook tests
        run: ./tests/test_hooks.sh
```

---

## Coverage Gaps (Known Limitations)

These aspects are NOT automatically tested:

1. **Actual Claude API calls** - We don't verify Haiku/Sonnet/Opus models respond correctly
2. **Real file system side effects** - Tests use temp directories, not real projects
3. **Claude Code internal behavior** - Plugin loading, agent spawning are Claude Code internals
4. **Network conditions** - Timeout, retry, rate limiting behavior
5. **Quota integration** - Actual message counting and quota tracking

These require manual testing or mocking the Claude Code environment.

---

## Adding New Tests

When adding functionality, add tests at appropriate layers:

1. **New routing pattern** → Add to `test_routing_core.py`
2. **New hook behavior** → Add to `test_hooks.sh`
3. **New implementation module** → Create `test_<module>.py`
4. **Cross-component interaction** → Add to `test_integration.py`

Template for new pytest tests:

```python
"""
Tests for new_module.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "implementation"))

from new_module import NewClass


class TestNewFeature:
    """Test new feature."""

    @pytest.fixture
    def instance(self, tmp_path):
        """Create instance with temp directory."""
        return NewClass(work_dir=tmp_path)

    def test_basic_operation(self, instance):
        """Should perform basic operation."""
        result = instance.do_thing()
        assert result is not None
```

---

## Debugging Test Failures

### Unit test failure
```bash
# Run with full traceback
pytest tests/infolead-claude-subscription-router/test_routing_core.py -v --tb=long

# Run single test
pytest tests/infolead-claude-subscription-router/test_routing_core.py::TestEscalationLogic::test_complexity_keywords_escalate -v
```

### Hook test failure
```bash
# Run with debug output
bash -x ./tests/infolead-claude-subscription-router/test_hooks.sh

# Test single hook manually
echo '{"cwd": "/tmp", "agent_type": "test", "agent_id": "123"}' | ./plugins/infolead-claude-subscription-router/.claude-plugin/hooks/log-subagent-start.sh
```

### Check implementation directly
```bash
# Test routing logic
cd implementation && python3 -c "
from routing_core import should_escalate
result = should_escalate('Fix typo in README.md')
print(f'Decision: {result.decision.value}')
print(f'Agent: {result.agent}')
print(f'Reason: {result.reason}')
"
```
