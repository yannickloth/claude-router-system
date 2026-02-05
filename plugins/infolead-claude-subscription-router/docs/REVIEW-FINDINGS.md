# Router Plugin Implementation Review

**Date:** 2026-02-05
**Reviewer:** Claude Sonnet 4.5
**Status:** ⚠️ Issues Found - Recommendations Provided

---

## Executive Summary

The router plugin implementation is **functionally sound** with good architecture and working tests. However, several issues were identified that could impact reliability, maintainability, and robustness:

### Critical Issues: 0
### High Priority Issues: 3
### Medium Priority Issues: 4
### Low Priority Issues: 2

---

## Issues Found

### HIGH PRIORITY

#### 1. Missing Dependency Management ⚠️

**Location:** Root plugin directory
**Issue:** No `requirements.txt` or dependency specification file

**Details:**
- Code imports `yaml` (PyYAML) at [routing_core.py:63](implementation/routing_core.py#L63)
- Other implementation files also use yaml
- Installation/setup will fail without explicit dependency tracking

**Impact:** Plugin installation will fail or have runtime errors on systems without PyYAML

**Recommendation:**
```bash
# Create requirements.txt
echo "PyYAML>=6.0" > requirements.txt
```

**Test Case Needed:**
- Test installation on clean system
- Verify all imports succeed

---

#### 2. Uncaught Import Error in `get_model_tier_from_agent_file()` ⚠️

**Location:** [routing_core.py:63](implementation/routing_core.py#L63)
**Issue:** `import yaml` inside function without dependency check

**Details:**
```python
def get_model_tier_from_agent_file(agent_name: str, agents_dir: Optional[str] = None) -> str:
    import yaml  # <-- Will fail if PyYAML not installed
    from pathlib import Path
```

The function has a bare `except Exception` that swallows import errors, but this:
1. Hides the real problem from users
2. Always falls back to "sonnet" default even when file exists
3. Makes debugging harder

**Current Behavior:**
- If PyYAML missing: returns default "sonnet" silently
- If file malformed: returns default "sonnet" silently
- No way to distinguish between "file not found" and "import failed"

**Impact:**
- Silent failures
- Agent model tier misconfiguration
- Hard-to-debug issues

**Recommendation:**
```python
def get_model_tier_from_agent_file(agent_name: str, agents_dir: Optional[str] = None) -> str:
    """
    Extract model tier from agent definition file's YAML frontmatter.

    Args:
        agent_name: Name of the agent (e.g., "router-escalation")
        agents_dir: Directory containing agent .md files (defaults to ../agents relative to this file)

    Returns:
        Model tier string ("haiku", "sonnet", or "opus"), defaults to "sonnet"

    Raises:
        ImportError: If yaml module is not available (install PyYAML)
    """
    try:
        import yaml
    except ImportError as e:
        print(f"Warning: PyYAML not installed. Install with: pip install PyYAML", file=sys.stderr)
        raise ImportError("PyYAML required for agent model tier detection") from e

    from pathlib import Path

    if agents_dir is None:
        agents_dir = Path(__file__).parent.parent / "agents"
    else:
        agents_dir = Path(agents_dir)

    agent_file = agents_dir / f"{agent_name}.md"

    if not agent_file.exists():
        # Fallback to substring matching for unknown agents
        agent_lower = agent_name.lower()
        if "haiku" in agent_lower:
            return "haiku"
        elif "opus" in agent_lower:
            return "opus"
        return "sonnet"

    try:
        content = agent_file.read_text()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                if frontmatter and "model" in frontmatter:
                    return frontmatter["model"]
    except yaml.YAMLError as e:
        print(f"Warning: Failed to parse YAML frontmatter in {agent_file}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Unexpected error reading {agent_file}: {e}", file=sys.stderr)

    return "sonnet"  # Default
```

**Test Cases Needed:**
- Test with PyYAML missing
- Test with malformed YAML frontmatter
- Test with missing agent file
- Test with valid agent file

---

#### 3. LLM Routing Subprocess Has No Error Visibility ⚠️

**Location:** [routing_core.py:154-192](implementation/routing_core.py#L154-L192)
**Issue:** `match_request_to_agents_llm()` silently swallows all subprocess errors

**Details:**
```python
try:
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", "haiku", "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "CLAUDE_NO_HOOKS": "1"}
    )

    if result.returncode != 0:
        # Fallback to keyword matching on error
        return match_request_to_agents_keywords(request)  # <-- Silent fallback
```

**Problems:**
1. No logging of subprocess stderr
2. No visibility when `claude` CLI is missing/misconfigured
3. Users don't know LLM routing is disabled
4. Makes debugging impossible

**Impact:**
- Users may think LLM routing is working when it's not
- Silent performance degradation to keyword matching
- Hard to diagnose routing quality issues

**Recommendation:**
```python
def match_request_to_agents_llm(
    request: str,
    agent_descriptions: Optional[Dict[str, str]] = None
) -> Tuple[Optional[str], float]:
    """
    Match request to available agents using Claude Haiku for semantic understanding.

    Falls back to keyword matching if LLM routing fails.

    Args:
        request: User's request string
        agent_descriptions: Optional dict mapping agent names to descriptions

    Returns:
        Tuple of (agent_name, confidence_score) or (None, 0.0) if no match
    """
    if agent_descriptions is None:
        agent_descriptions = {
            "haiku-general": "Simple mechanical tasks: fix typos, correct spelling, format code, lint files, rename variables. Tasks with explicit file paths that require no judgment.",
            "sonnet-general": "Tasks requiring reasoning: analyze code, design features, implement functionality, refactor, review, optimize. Default for tasks needing judgment.",
            "opus-general": "Complex reasoning: mathematical proofs, formal verification, architecture decisions, algorithm design. High-stakes decisions requiring deep analysis.",
        }

    # Build the prompt
    agents_list = "\n".join(f"- {name}: {desc}" for name, desc in agent_descriptions.items())
    prompt = f"""Given this user request, which agent should handle it?

Request: {request}

Available agents:
{agents_list}

Respond with ONLY a JSON object (no markdown, no explanation):
{{"agent": "<agent-name or null>", "confidence": <0.0-1.0>}}

If the request is ambiguous or requires judgment to route, return null with low confidence."""

    try:
        # Call claude CLI with haiku model
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", "haiku", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "CLAUDE_NO_HOOKS": "1"}  # Prevent hook recursion
        )

        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "no error output"
            print(f"LLM routing failed (exit {result.returncode}): {stderr}", file=sys.stderr)
            print(f"Falling back to keyword matching", file=sys.stderr)
            return match_request_to_agents_keywords(request)

        # Parse the response
        response = json.loads(result.stdout)
        content = response.get("result", "")

        # Extract JSON from the response (handle possible markdown wrapping)
        if "```" in content:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

        parsed = json.loads(content)
        agent = parsed.get("agent")
        confidence = float(parsed.get("confidence", 0.0))

        # Validate agent name
        if agent and agent not in agent_descriptions:
            print(f"LLM suggested unknown agent: {agent}", file=sys.stderr)
            return None, 0.0

        return agent, confidence

    except subprocess.TimeoutExpired:
        print(f"LLM routing timeout after 10s, falling back to keywords", file=sys.stderr)
        return match_request_to_agents_keywords(request)
    except json.JSONDecodeError as e:
        print(f"LLM routing failed (invalid JSON): {e}", file=sys.stderr)
        print(f"Falling back to keyword matching", file=sys.stderr)
        return match_request_to_agents_keywords(request)
    except FileNotFoundError:
        print(f"claude CLI not found in PATH, falling back to keywords", file=sys.stderr)
        return match_request_to_agents_keywords(request)
    except Exception as e:
        print(f"LLM routing failed ({type(e).__name__}: {e}), falling back to keywords", file=sys.stderr)
        return match_request_to_agents_keywords(request)
```

**Test Cases Needed:**
- Test with `claude` CLI not in PATH
- Test with `claude` CLI failing (exit code != 0)
- Test with timeout
- Test with malformed JSON response
- Test with unknown agent suggestion

---

### MEDIUM PRIORITY

#### 4. Shell Hook Has No Python3 Availability Check 🔶

**Location:** [hooks/user-prompt-submit.sh:43](hooks/user-prompt-submit.sh#L43)
**Issue:** Assumes `python3` is in PATH

**Details:**
```bash
ROUTING_OUTPUT=$(python3 "$ROUTING_SCRIPT" --json <<< "$USER_REQUEST" 2>/dev/null || echo '{"error": "routing_failed"}')
```

**Impact:**
- Hook fails silently on systems without python3
- No indication to user that routing is disabled
- Works on most Linux/Mac but may fail on minimal containers

**Recommendation:**
```bash
# Check for python3 availability
if ! command -v python3 &> /dev/null; then
    # Python3 not available - pass through silently
    exit 0
fi

# Run routing analysis with JSON output
ROUTING_OUTPUT=$(python3 "$ROUTING_SCRIPT" --json <<< "$USER_REQUEST" 2>/dev/null || echo '{"error": "routing_failed"}')
```

**Test Case Needed:**
- Test hook execution with `python3` removed from PATH

---

#### 5. `explicit_file_mentioned()` Has False Positives 🔶

**Location:** [routing_core.py:98-116](implementation/routing_core.py#L98-L116)
**Issue:** Regex patterns too broad, catch non-file patterns

**Details:**
```python
file_patterns = [
    r'\b\w+\.\w{2,4}\b',   # filename.ext (2-4 char extension)
    r'[\./][\w/.-]+',       # path/to/file or ./file
    r'\w+/\w+',             # dir/file
    r'~[\w/.-]+',           # ~/path/file
]
```

**False Positives:**
- `"version 3.14"` matches `r'\b\w+\.\w{2,4}\b'`
- `"ratio 0.95"` matches `r'\b\w+\.\w{2,4}\b'`
- `"import/export"` matches `r'\w+/\w+'`
- `"input/output"` matches `r'\w+/\w+'`
- URLs like `"example.com"` match

**Impact:**
- Haiku routing triggered for non-file operations
- Lower routing accuracy
- Potential misrouting of tasks

**Recommendation:**
```python
def explicit_file_mentioned(request: str) -> bool:
    """
    Check if request contains explicit file paths or filenames.

    Uses conservative patterns to minimize false positives.

    Args:
        request: User's request string

    Returns:
        True if explicit files/paths mentioned, False otherwise
    """
    # Look for explicit file indicators
    file_indicators = [
        # Explicit path separators
        r'[\./][\w/.-]+\.[\w]{2,10}',  # ./file.ext or path/to/file.ext
        r'~[\w/.-]+',                    # ~/path/file
        r'/[\w/.-]+',                    # /absolute/path

        # Common file extensions (more specific)
        r'\b\w+\.(py|js|ts|jsx|tsx|md|txt|json|yaml|yml|toml|sh|bash|zsh)\b',
        r'\b\w+\.(java|cpp|c|h|hpp|rs|go|rb|php|swift|kt)\b',
        r'\b\w+\.(html|css|scss|sass|less|xml|svg)\b',
        r'\b\w+\.(sql|db|sqlite|csv|log)\b',

        # Quoted paths
        r'["\'][\w/.-]+\.[\w]+["\']',

        # Common file keywords followed by path-like pattern
        r'\bfile\s+[\w/.-]+',
        r'\bpath\s+[\w/.-]+',
    ]

    return any(re.search(pattern, request, re.IGNORECASE) for pattern in file_indicators)
```

**Test Cases Needed:**
```python
# Should match (true positives)
assert explicit_file_mentioned("Fix typo in README.md")
assert explicit_file_mentioned("Edit ./src/main.py")
assert explicit_file_mentioned("Update /home/user/config.json")
assert explicit_file_mentioned("Modify the file test.py")

# Should NOT match (avoid false positives)
assert not explicit_file_mentioned("version 3.14")
assert not explicit_file_mentioned("ratio is 0.95")
assert not explicit_file_mentioned("import/export data")
assert not explicit_file_mentioned("input/output streams")
assert not explicit_file_mentioned("example.com")
assert not explicit_file_mentioned("v2.5 release")
```

---

#### 6. Insufficient Test Coverage 🔶

**Location:** [implementation/routing_core.py:506-547](implementation/routing_core.py#L506-L547)
**Issue:** Built-in tests only cover 9 happy-path cases

**Current Coverage:**
- ✅ Basic escalation patterns (6 tests)
- ✅ Basic direct routing (3 tests)
- ❌ Edge cases (0 tests)
- ❌ Error handling (0 tests)
- ❌ LLM routing mode (0 tests)
- ❌ File path detection edge cases (0 tests)

**Missing Test Cases:**
1. Empty request
2. Very long request (>10k chars)
3. Special characters: regex, unicode, shell metacharacters
4. File path false positives (version numbers, ratios, etc.)
5. LLM routing with ROUTER_USE_LLM=1
6. LLM routing failures (timeout, bad JSON)
7. Missing agent file
8. Malformed agent YAML frontmatter
9. Concurrent routing requests (thread safety)
10. All escalation patterns individually
11. Confidence threshold boundary cases (0.69, 0.70, 0.71, 0.79, 0.80, 0.81)
12. Agent matching with custom registry

**Recommendation:** See "Comprehensive Unit Test Suite" section below

---

#### 7. No Input Validation in `route_request()` 🔶

**Location:** [routing_core.py:452-472](implementation/routing_core.py#L452-L472)
**Issue:** No validation of inputs, can pass invalid data types

**Details:**
```python
def route_request(
    request: str,
    context: Optional[Dict] = None,
    agent_registry: Optional[Dict[str, List[str]]] = None
) -> RoutingResult:
    """Route a user request to the appropriate agent."""
    return should_escalate(request, context)  # <-- No validation
```

**Potential Issues:**
- `request` could be None, int, empty string
- `context` could be malformed dict
- No length limits (could be 1GB string)

**Impact:**
- Crashes with confusing errors
- Potential DoS vector
- Poor error messages for API users

**Recommendation:**
```python
def route_request(
    request: str,
    context: Optional[Dict] = None,
    agent_registry: Optional[Dict[str, List[str]]] = None
) -> RoutingResult:
    """
    Route a user request to the appropriate agent.

    This is the main entry point for the routing system. It analyzes the request
    and returns a routing decision with the selected agent.

    Args:
        request: User's request string (1-10000 characters)
        context: Optional context dict with project state, files, etc.
        agent_registry: Optional custom agent keyword mappings

    Returns:
        RoutingResult with decision, agent, reason, and confidence

    Raises:
        ValueError: If request is invalid (None, empty, too long)
        TypeError: If request is not a string
    """
    # Validate request
    if not isinstance(request, str):
        raise TypeError(f"request must be str, got {type(request).__name__}")

    if not request or not request.strip():
        raise ValueError("request cannot be empty")

    if len(request) > 10000:
        raise ValueError(f"request too long: {len(request)} chars (max 10000)")

    # Validate context if provided
    if context is not None and not isinstance(context, dict):
        raise TypeError(f"context must be dict or None, got {type(context).__name__}")

    return should_escalate(request, context)
```

**Test Cases Needed:**
- Test with None request
- Test with int/list request
- Test with empty string
- Test with whitespace-only string
- Test with very long request (>10k chars)
- Test with invalid context type

---

#### 8. Hook Metrics File Locking Timeout Not Configurable 🔶

**Location:** [hooks/user-prompt-submit.sh:82-86](hooks/user-prompt-submit.sh#L82-L86)
**Issue:** `flock` has no timeout, can block indefinitely

**Details:**
```bash
(
    flock -x 200
    echo "$METRICS_ENTRY" >> "$METRICS_DIR/${TODAY}.jsonl"
) 200>"$METRICS_DIR/${TODAY}.jsonl.lock"
```

**Impact:**
- If lock file corrupted/stuck, all routing hangs
- Hook timeout (10s) will kill the hook, causing failed requests
- No recovery mechanism

**Recommendation:**
```bash
# Atomic append to metrics file with timeout
(
    # Try to acquire lock with 5 second timeout
    if flock -x -w 5 200; then
        echo "$METRICS_ENTRY" >> "$METRICS_DIR/${TODAY}.jsonl"
    else
        # Lock timeout - log to stderr but don't fail the hook
        echo "[ROUTER] Warning: Failed to acquire metrics lock, skipping logging" >&2
    fi
) 200>"$METRICS_DIR/${TODAY}.jsonl.lock"
```

**Test Cases Needed:**
- Test with stuck lock file
- Test with concurrent writes
- Test with corrupted lock file

---

### LOW PRIORITY

#### 9. Magic Numbers Not Documented 📘

**Location:** Multiple locations
**Issue:** Confidence thresholds, timeouts hardcoded without explanation

**Examples:**
- `confidence_threshold = 0.7 if USE_LLM_ROUTING else 0.8` ([routing_core.py:401](implementation/routing_core.py#L401))
  - Why 0.7 vs 0.8? No explanation
- `timeout=10` ([routing_core.py:159](implementation/routing_core.py#L159))
  - Why 10 seconds? No justification
- `timeout: 10` ([plugin.json:28](plugin.json#L28))
  - Hook timeouts scattered across config

**Recommendation:**
```python
# Configuration constants
CONFIDENCE_THRESHOLD_LLM = 0.7      # LLM routing is more accurate, lower threshold
CONFIDENCE_THRESHOLD_KEYWORD = 0.8  # Keyword matching needs higher confidence
LLM_ROUTING_TIMEOUT_SECONDS = 10    # Balance accuracy vs latency
HOOK_TIMEOUT_SECONDS = 10           # Must complete before user sees delay

# Use named constants
confidence_threshold = CONFIDENCE_THRESHOLD_LLM if USE_LLM_ROUTING else CONFIDENCE_THRESHOLD_KEYWORD
```

---

#### 10. No Version Compatibility Checking 📘

**Location:** Throughout codebase
**Issue:** No checks for minimum Python version, dependency versions

**Details:**
- Uses f-strings (requires Python 3.6+)
- Uses type hints (requires Python 3.5+)
- Uses `subprocess.run` with `capture_output` (Python 3.7+)
- Uses `|` for Optional types in comments (Python 3.10+ syntax but not runtime)

**Recommendation:**
Add version check in `routing_core.py`:
```python
import sys

if sys.version_info < (3, 7):
    print("Error: Python 3.7 or higher required", file=sys.stderr)
    sys.exit(1)
```

Add to `requirements.txt`:
```
python_requires>=3.7
PyYAML>=6.0
```

---

## Test Coverage Analysis

### Current Tests

**Unit Tests:** `routing_core.py --test`
- 9 test cases, all passing
- Tests core routing logic
- **Coverage: ~40%** (happy paths only)

**Integration Tests:** `tests/test-routing-visibility.sh`
- 15 test cases
- Tests hook integration, metrics, concurrency
- Good coverage of integration layer
- **Coverage: ~70%** of integration layer

### Missing Coverage

1. **Error Handling**: 0% coverage
2. **Edge Cases**: 0% coverage
3. **LLM Routing Mode**: 0% coverage
4. **Input Validation**: 0% coverage
5. **Fallback Mechanisms**: 0% coverage

---

## Recommended Unit Test Suite

Create `tests/test_routing_core.py`:

```python
"""
Comprehensive unit tests for routing_core.py

Run with: python3 -m pytest tests/test_routing_core.py -v
"""

import pytest
import sys
import os
from pathlib import Path

# Add implementation to path
sys.path.insert(0, str(Path(__file__).parent.parent / "implementation"))

from routing_core import (
    RouterDecision,
    RoutingResult,
    explicit_file_mentioned,
    match_request_to_agents_keywords,
    match_request_to_agents_llm,
    should_escalate,
    route_request,
    get_model_tier_from_agent_file,
)


class TestExplicitFileMentioned:
    """Test file path detection"""

    def test_explicit_paths(self):
        """Should detect explicit file paths"""
        assert explicit_file_mentioned("Fix typo in README.md")
        assert explicit_file_mentioned("Edit ./src/main.py")
        assert explicit_file_mentioned("Update /home/user/config.json")
        assert explicit_file_mentioned("Modify ~/Documents/notes.txt")

    def test_relative_paths(self):
        """Should detect relative paths"""
        assert explicit_file_mentioned("Read ../config/settings.yaml")
        assert explicit_file_mentioned("Update ./scripts/deploy.sh")

    def test_quoted_paths(self):
        """Should detect quoted paths"""
        assert explicit_file_mentioned('Edit "my file.txt"')
        assert explicit_file_mentioned("Read 'config.json'")

    def test_file_keywords(self):
        """Should detect file/path keywords"""
        assert explicit_file_mentioned("the file main.py")
        assert explicit_file_mentioned("path src/utils.js")

    def test_false_positives_version_numbers(self):
        """Should NOT match version numbers"""
        assert not explicit_file_mentioned("version 3.14")
        assert not explicit_file_mentioned("Python 2.7")
        assert not explicit_file_mentioned("v1.5.2 release")

    def test_false_positives_ratios(self):
        """Should NOT match ratios/decimals"""
        assert not explicit_file_mentioned("ratio is 0.95")
        assert not explicit_file_mentioned("score of 8.5")

    def test_false_positives_urls(self):
        """Should NOT match domain names (debatable)"""
        # Note: This might be desired behavior - review needed
        assert not explicit_file_mentioned("visit example.com")

    def test_false_positives_word_pairs(self):
        """Should NOT match word pairs with slash"""
        assert not explicit_file_mentioned("import/export data")
        assert not explicit_file_mentioned("input/output streams")
        assert not explicit_file_mentioned("read/write operations")

    def test_edge_cases(self):
        """Edge cases"""
        assert not explicit_file_mentioned("")
        assert not explicit_file_mentioned("no files here")


class TestMatchRequestToAgentsKeywords:
    """Test keyword-based agent matching"""

    def test_haiku_high_confidence(self):
        """High-confidence haiku patterns with explicit files"""
        agent, conf = match_request_to_agents_keywords("Fix typo in README.md")
        assert agent == "haiku-general"
        assert conf >= 0.90

        agent, conf = match_request_to_agents_keywords("Format code in main.py")
        assert agent == "haiku-general"
        assert conf >= 0.90

    def test_haiku_needs_explicit_file(self):
        """Haiku keywords without file should not match haiku"""
        agent, conf = match_request_to_agents_keywords("Fix typo")
        # Without explicit file, should either not match or match sonnet
        assert agent != "haiku-general" or conf < 0.9

    def test_sonnet_keywords(self):
        """Sonnet reasoning keywords"""
        agent, conf = match_request_to_agents_keywords("Analyze the codebase")
        assert agent == "sonnet-general"

        agent, conf = match_request_to_agents_keywords("Refactor this module")
        assert agent == "sonnet-general"

    def test_opus_keywords(self):
        """Opus complex reasoning keywords"""
        agent, conf = match_request_to_agents_keywords("Prove correctness of algorithm")
        assert agent == "opus-general"

        agent, conf = match_request_to_agents_keywords("Formal verification needed")
        assert agent == "opus-general"

    def test_no_match(self):
        """Ambiguous requests should not match"""
        agent, conf = match_request_to_agents_keywords("Do something")
        # Either no match or very low confidence
        assert agent is None or conf < 0.5


class TestShouldEscalate:
    """Test escalation decision logic"""

    def test_complexity_signals(self):
        """Requests with complexity keywords should escalate"""
        result = should_escalate("Which approach is best?")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET
        assert "complexity" in result.reason.lower()

        result = should_escalate("This is a complex trade-off")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET

    def test_bulk_destructive(self):
        """Bulk destructive operations should escalate"""
        result = should_escalate("Delete all temporary files")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET
        assert "destructive" in result.reason.lower()

        result = should_escalate("Remove every backup")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET

    def test_ambiguous_file_operations(self):
        """File operations without explicit paths should escalate"""
        result = should_escalate("Edit the main file")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET
        assert "file operation without explicit path" in result.reason.lower()

    def test_agent_definition_changes(self):
        """Changes to .claude/agents should escalate"""
        result = should_escalate("Modify .claude/agents/router.md")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET
        assert "agent definition" in result.reason.lower()

    def test_multiple_objectives(self):
        """Multiple objectives should escalate"""
        result = should_escalate("Create API endpoint, add tests, and update docs")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET
        # Has multiple " and " separators

    def test_creation_tasks(self):
        """Creation/design tasks should escalate"""
        result = should_escalate("Design a new auth system")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET

        result = should_escalate("Implement user login")
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET

    def test_simple_mechanical_direct(self):
        """Simple mechanical tasks should route direct"""
        result = should_escalate("Fix typo in README.md")
        assert result.decision == RouterDecision.DIRECT_TO_AGENT
        assert result.agent == "haiku-general"
        assert result.confidence >= 0.8

    def test_confidence_threshold(self):
        """Low confidence should escalate"""
        # This depends on internal matching - might need adjustment
        result = should_escalate("Fix the bug")  # Ambiguous
        # Likely to escalate due to low confidence or ambiguity
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET


class TestRouteRequest:
    """Test main routing entry point"""

    def test_basic_routing(self):
        """Basic routing works"""
        result = route_request("Fix typo in README.md")
        assert isinstance(result, RoutingResult)
        assert result.decision in [RouterDecision.DIRECT_TO_AGENT, RouterDecision.ESCALATE_TO_SONNET]

    def test_with_context(self):
        """Routing with context dict"""
        result = route_request("Fix bug", context={"project": "test"})
        assert isinstance(result, RoutingResult)

    def test_invalid_request_none(self):
        """Should raise on None request"""
        with pytest.raises((TypeError, AttributeError)):
            route_request(None)

    def test_invalid_request_empty(self):
        """Should handle empty request"""
        # Current implementation doesn't validate - might escalate
        result = route_request("")
        # Should either error or escalate
        assert isinstance(result, RoutingResult)

    def test_invalid_request_type(self):
        """Should raise on non-string request"""
        with pytest.raises((TypeError, AttributeError)):
            route_request(123)

        with pytest.raises((TypeError, AttributeError)):
            route_request(['list'])

    def test_very_long_request(self):
        """Should handle very long requests"""
        long_request = "Fix typo " * 10000  # Very long
        result = route_request(long_request)
        assert isinstance(result, RoutingResult)


class TestGetModelTierFromAgentFile:
    """Test agent model tier detection"""

    def test_haiku_in_name(self):
        """Agent name with 'haiku' should return haiku"""
        tier = get_model_tier_from_agent_file("test-haiku-agent", agents_dir="/nonexistent")
        assert tier == "haiku"

    def test_opus_in_name(self):
        """Agent name with 'opus' should return opus"""
        tier = get_model_tier_from_agent_file("test-opus-agent", agents_dir="/nonexistent")
        assert tier == "opus"

    def test_default_sonnet(self):
        """Unknown agents should default to sonnet"""
        tier = get_model_tier_from_agent_file("unknown-agent", agents_dir="/nonexistent")
        assert tier == "sonnet"

    def test_real_agent_file(self):
        """Should read model from real agent file"""
        # Test with actual haiku-general.md if it exists
        agents_dir = Path(__file__).parent.parent / "agents"
        if (agents_dir / "haiku-general.md").exists():
            tier = get_model_tier_from_agent_file("haiku-general", agents_dir=str(agents_dir))
            assert tier == "haiku"


class TestEdgeCases:
    """Test edge cases and special inputs"""

    def test_special_characters_regex(self):
        """Requests with regex patterns"""
        result = route_request("Fix regex: /\\w+@\\w+\\.\\w+/")
        assert isinstance(result, RoutingResult)

    def test_special_characters_unicode(self):
        """Requests with unicode"""
        result = route_request("Fix typo in café.txt 中文")
        assert isinstance(result, RoutingResult)

    def test_special_characters_shell(self):
        """Requests with shell metacharacters"""
        result = route_request("Fix file with spaces & special chars; $(pwd)")
        assert isinstance(result, RoutingResult)

    def test_newlines_in_request(self):
        """Multi-line requests"""
        result = route_request("Fix typo\nin README.md\nline 42")
        assert isinstance(result, RoutingResult)

    def test_only_whitespace(self):
        """Whitespace-only requests"""
        result = route_request("   \t\n   ")
        # Should either error or escalate
        assert isinstance(result, RoutingResult)


class TestLLMRouting:
    """Test LLM-based routing (requires claude CLI)"""

    @pytest.mark.skipif(os.environ.get("ROUTER_USE_LLM") != "1",
                        reason="LLM routing not enabled")
    def test_llm_routing_enabled(self):
        """Test with LLM routing enabled"""
        result = route_request("Fix typo in README.md")
        assert isinstance(result, RoutingResult)

    def test_llm_routing_fallback(self):
        """Test fallback when LLM routing fails"""
        # This is hard to test without mocking
        # Could mock subprocess.run to raise exception
        pass


# Fixtures for integration testing
@pytest.fixture
def temp_agent_dir(tmp_path):
    """Create temporary agent directory with test agents"""
    agents = tmp_path / "agents"
    agents.mkdir()

    # Create haiku agent
    (agents / "test-haiku.md").write_text("""---
name: test-haiku
model: haiku
---
Test haiku agent
""")

    # Create sonnet agent
    (agents / "test-sonnet.md").write_text("""---
name: test-sonnet
model: sonnet
---
Test sonnet agent
""")

    return str(agents)


class TestIntegration:
    """Integration tests"""

    def test_end_to_end_haiku(self):
        """End-to-end routing to haiku"""
        result = route_request("Fix typo in README.md")
        assert result.decision in [RouterDecision.DIRECT_TO_AGENT, RouterDecision.ESCALATE_TO_SONNET]
        if result.decision == RouterDecision.DIRECT_TO_AGENT:
            assert result.agent is not None
            assert result.confidence > 0

    def test_end_to_end_escalate(self):
        """End-to-end routing with escalation"""
        result = route_request("Design a new system")
        # Should escalate due to design keyword
        assert result.decision == RouterDecision.ESCALATE_TO_SONNET


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Installation Test

Create `tests/test_installation.sh`:

```bash
#!/bin/bash
# Test plugin installation from scratch

set -euo pipefail

echo "=== Plugin Installation Test ==="

# Test 1: Check Python3
echo "Checking Python3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi
echo "✅ Python3 found: $(python3 --version)"

# Test 2: Check dependencies
echo "Checking dependencies..."
if ! python3 -c "import yaml" 2>/dev/null; then
    echo "❌ PyYAML not installed"
    echo "Install with: pip install PyYAML"
    exit 1
fi
echo "✅ PyYAML installed"

# Test 3: Check routing_core.py
echo "Checking routing_core.py..."
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$(readlink -f "$0")")")}"
if [ ! -f "$PLUGIN_DIR/implementation/routing_core.py" ]; then
    echo "❌ routing_core.py not found"
    exit 1
fi
echo "✅ routing_core.py found"

# Test 4: Test basic routing
echo "Testing basic routing..."
if ! echo "test" | python3 "$PLUGIN_DIR/implementation/routing_core.py" --json >/dev/null 2>&1; then
    echo "❌ Routing test failed"
    exit 1
fi
echo "✅ Routing works"

echo ""
echo "=== All installation tests passed ==="
```

---

## Priority Recommendations

### Immediate (Do First)
1. **Add `requirements.txt`** (5 minutes)
   - Critical for installation

2. **Fix PyYAML import error handling** (15 minutes)
   - Prevents silent failures

3. **Add stderr logging to LLM routing** (15 minutes)
   - Essential for debugging

### Short Term (This Week)
4. **Add input validation to `route_request()`** (30 minutes)
5. **Add python3 check to shell hook** (10 minutes)
6. **Add flock timeout to metrics logging** (10 minutes)

### Medium Term (This Month)
7. **Improve `explicit_file_mentioned()` accuracy** (2 hours)
   - Requires testing and refinement
8. **Add comprehensive unit tests** (4-6 hours)
   - Use provided test suite as starting point
9. **Document magic numbers** (1 hour)

### Long Term (Nice to Have)
10. **Add version compatibility checks** (1 hour)

---

## Summary Checklist

### Critical Path to Production
- [ ] Add requirements.txt
- [ ] Fix PyYAML import handling
- [ ] Add LLM routing error visibility
- [ ] Add installation test
- [ ] Add python3 availability check in hook
- [ ] Add comprehensive unit tests
- [ ] Add input validation

### Quality Improvements
- [ ] Improve file path detection
- [ ] Add flock timeout
- [ ] Document configuration constants
- [ ] Add version checks

---

## Positive Notes

The plugin has many **excellent design decisions**:

✅ **Clean separation of concerns** - Router logic independent from execution
✅ **Good fallback strategy** - LLM → keyword matching
✅ **Comprehensive integration tests** - Hook testing is thorough
✅ **Atomic metrics logging** - Uses flock correctly
✅ **Graceful degradation** - Silently disables when components missing
✅ **Good documentation** - Functions well documented
✅ **IVP-compliant architecture** - Clear change driver separation

The issues found are **typical for early-stage production code** and easily fixable.

---

## Conclusion

The router plugin is **functionally solid** but needs **hardening for production use**. The main gaps are:

1. **Dependency management** - No requirements file
2. **Error visibility** - Silent failures make debugging hard
3. **Input validation** - Missing edge case handling
4. **Test coverage** - Only happy paths tested

**Estimated effort to production-ready:** 8-12 hours

**Risk level if deployed as-is:** 🟡 MEDIUM
- Won't corrupt data or cause security issues
- May fail silently or have confusing errors
- Users may not know when routing is degraded

**Recommended approach:**
1. Fix critical issues (1-2 hours)
2. Add comprehensive tests (4-6 hours)
3. Deploy to staging/personal use
4. Monitor for issues
5. Add remaining improvements iteratively
