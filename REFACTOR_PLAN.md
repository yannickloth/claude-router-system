# Refactor Plan: Multi-Plugin Marketplace Architecture

**Repository rename:** `claude-router-system` → `infolead-claudecode-marketplace`

**Goal:** Create a marketplace repo hosting multiple plugins: one core router plugin plus domain-specific extension plugins that register their agents via project CLAUDE.md.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Project CLAUDE.md                        │
│  - Declares which extension plugins are active              │
│  - Lists available agents from each extension               │
│  - Router reads this to know what agents exist              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     infolead-claude-subscription-router                         │
│  - Core routing logic (router, router-escalation)           │
│  - General agents (haiku/sonnet/opus-general)               │
│  - Cost optimization (strategy-advisor)                     │
│  - Work coordination (planner, work-coordinator)            │
│  - Routes to extension agents declared in CLAUDE.md         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌───────────┐   ┌───────────┐   ┌───────────┐
       │ git-tools │   │latex-tools│   │med-tools  │
       │(extension)│   │(extension)│   │(extension)│
       └───────────┘   └───────────┘   └───────────┘
```

**Key principle:** Router is self-contained. Extensions add domain agents. Project CLAUDE.md tells router which extensions are active and what agents they provide.

---

## Current State

Single plugin (`claude-router-system`) containing:
- 11 routing/core agents
- 13 Python implementation modules
- 3 domain configurations
- 2 hooks
- Documentation and tests

**Problems with current approach:**
1. Domain agents (latex, medical, git) mixed with core routing
2. No clear separation between "router infrastructure" and "domain tools"
3. Can't share domain agents across projects without copying

---

## Target State

```
infolead-claudecode-marketplace/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── infolead-claude-subscription-router/   ← Core plugin (required)
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── agents/
│   │   ├── implementation/
│   │   └── README.md
│   ├── infolead-dev-tools/                    ← Extension plugin
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── agents/
│   │   └── README.md
│   ├── infolead-git-tools/                    ← Extension plugin
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── agents/
│   │   └── README.md
│   ├── infolead-latex-tools/                  ← Extension plugin
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── agents/
│   │   ├── workflows/
│   │   └── README.md
│   └── infolead-medical-tools/                ← Extension plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── agents/
│       └── README.md
├── docs/
└── README.md
```

---

## Plugin Specifications

### Core Plugin: `infolead-claude-subscription-router`

**Purpose:** Cost-optimized routing infrastructure. Required for all projects using this system.

**Agents:**
- `router.md` — Entry point for all requests
- `router-escalation.md` — Handles uncertain routing (Opus)
- `strategy-advisor.md` — Cost/benefit analysis for execution patterns
- `haiku-general.md` — Mechanical tasks, no judgment
- `sonnet-general.md` — Default reasoning and analysis
- `opus-general.md` — Complex reasoning, proofs
- `planner.md` — Work planning
- `work-coordinator.md` — Kanban-style queue management
- `temporal-scheduler.md` — Time-aware scheduling
- `haiku-pre-router.md` — Pre-routing filter

**Implementation modules:**
- `routing_core.py`
- `work_coordinator.py`
- `semantic_cache.py`
- `session_state_manager.py`
- `metrics_collector.py`
- `file_locking.py`
- (all current implementation modules)

**Hooks:**
- `SubagentStart` / `SubagentStop` logging

**Version:** 2.0.0

```text
plugins/infolead-claude-subscription-router/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── router.md
│   ├── router-escalation.md
│   ├── strategy-advisor.md
│   ├── haiku-general.md
│   ├── sonnet-general.md
│   ├── opus-general.md
│   ├── planner.md
│   ├── work-coordinator.md
│   ├── temporal-scheduler.md
│   └── haiku-pre-router.md
├── implementation/
│   └── (all Python modules)
├── hooks/
│   ├── hooks.json
│   ├── log-subagent-start.sh
│   └── log-subagent-stop.sh
└── README.md
```

---

### Extension Plugin: `infolead-dev-tools`

**Purpose:** General development utilities for any codebase. Language-agnostic tools that improve development workflow.

**Agents:**

| Agent | Model | Purpose | Why Agent > Inline |
|-------|-------|---------|-------------------|
| `config-auditor` | Sonnet | Audit Claude Code config for conflicts, undefined refs, circular routing | Systematic multi-file analysis; human would miss cross-file issues |
| `config-optimizer` | Sonnet | Optimize CLAUDE.md/agents for context efficiency | Applies consistent patterns across files; tracks token savings |
| `code-reviewer` | Sonnet | Review code changes for logic errors, style issues, security | Fresh perspective on diff; catches what author overlooks |
| `test-analyzer` | Sonnet | Analyze test failures, suggest fixes, identify flaky tests | Pattern recognition across test runs; correlates failures |
| `refactor-advisor` | Sonnet | Identify refactoring opportunities, suggest improvements | Sees structural issues human eye misses; applies design principles |
| `dependency-auditor` | Haiku | Check for outdated/vulnerable dependencies | Mechanical version comparison; security database lookup |
| `docs-generator` | Sonnet | Generate documentation from code structure | Consistent format; extracts patterns human would skip |

**Why these are better as agents:**

1. **Systematic coverage** — Agents follow checklists exhaustively; humans skip steps
2. **Pattern recognition** — Agents see across files simultaneously; humans have limited working memory
3. **Consistency** — Same analysis quality every time; humans have good and bad days
4. **Objectivity** — No ego attachment to code; will flag issues author wouldn't see
5. **Speed** — Parallel analysis of multiple files; humans are sequential
6. **Documentation** — Agents produce structured reports; humans often skip writeup

**Requires:** `infolead-claude-subscription-router`

**Version:** 1.0.0

```text
plugins/infolead-dev-tools/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── config-auditor.md
│   ├── config-optimizer.md
│   ├── code-reviewer.md
│   ├── test-analyzer.md
│   ├── refactor-advisor.md
│   ├── dependency-auditor.md
│   └── docs-generator.md
└── README.md
```

---

### Extension Plugin: `infolead-git-tools`

**Purpose:** Git operations and version control workflows.

**Agents:**

| Agent | Model | Purpose | Why Agent > Inline |
|-------|-------|---------|-------------------|
| `commit-writer` | Sonnet | Generate commit messages from staged changes | Consistent format; includes all changes; follows conventions |
| `changelog-generator` | Sonnet | Generate release notes from commit history | Synthesizes multiple commits; groups by category |
| `git-historian` | Sonnet | Query history, blame, track changes over time | Correlates changes across files; finds patterns |
| `release-manager` | Sonnet | Manage releases, tags, versioning, PRs | Follows semantic versioning; automates checklist |

**Why these are better as agents:**

1. **Convention enforcement** — Commit messages follow project standards automatically
2. **Completeness** — Changelog includes all changes, not just memorable ones
3. **Cross-file correlation** — History analysis sees connections human misses
4. **Automation** — Release checklist executed consistently every time

**Requires:** `infolead-claude-subscription-router`

**Version:** 1.0.0

```text
plugins/infolead-git-tools/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── commit-writer.md
│   ├── changelog-generator.md
│   ├── git-historian.md
│   └── release-manager.md
└── README.md
```

---

### Extension Plugin: `infolead-latex-tools`

**Purpose:** LaTeX document authoring and research paper management.

**Agents:**
- `syntax-fixer.md` — LaTeX compilation errors
- `formatting-fixer.md` — Markdown to LaTeX conversion
- `style-naturalizer.md` — AI-to-human prose
- `template-advisor.md` — Environment selection
- `tikz-illustrator.md` — TikZ diagram creation
- `tikz-validator.md` — TikZ validation
- `dictionary-manager.md` — Spelling exceptions
- `test-runner.md` — Build validation
- `link-checker.md` — Reference validation
- `file-splitter.md` — Chapter splitting
- `literature-integrator.md` — Paper discovery and integration
- `chapter-integrator.md` — Citation integration
- `scientific-insight-generator.md` — Novel connections
- `content-reviewer.md` — Consistency checking
- `math-verifier.md` — Proof verification
- `logic-auditor.md` — Circular reasoning detection
- `scientific-rigor-auditor.md` — Citation compliance

**Workflows:**
- `literature-integration.md`
- `formalization-pipeline.md`
- `tikz-illustration-pipeline.md`
- `environment-selection.md`
- `pre-commit.md`
- `section-review.md`
- `full-document-review.md`

**Requires:** `infolead-claude-subscription-router`

**Version:** 1.0.0

```text
plugins/infolead-latex-tools/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   └── (17 agents)
├── workflows/
│   └── (7 workflows)
└── README.md
```

---

### Extension Plugin: `infolead-medical-tools`

**Purpose:** Personal health tracking and ME/CFS case documentation.

**Agents:**
- `case-documenter.md` — Symptom and treatment logging
- `medical-advisor.md` — Evidence-based recommendations
- `treatment-analyst.md` — Intervention effectiveness
- `crisis-manager.md` — Emergency protocols
- `pacing-coach.md` — Activity budgeting
- `data-validator.md` — Data quality checks
- `hypothesis-generator.md` — Mechanism hypotheses
- `research-monitor.md` — New research alerts
- `benefit-navigator.md` — Disability documentation
- `caregiver-coordinator.md` — Care team instructions

**Requires:** `infolead-claude-subscription-router`

**Version:** 1.0.0

```text
plugins/infolead-medical-tools/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   └── (10 agents)
└── README.md
```

---

## Extension Registration via CLAUDE.md

Extensions don't auto-register. Projects declare which extensions are active in their CLAUDE.md:

```markdown
## Installed Extensions

This project uses the following infolead-claudecode-marketplace extensions:

### infolead-git-tools
Agents: commit-writer, changelog-generator, git-historian, release-manager

### infolead-latex-tools
Agents: syntax-fixer, formatting-fixer, style-naturalizer, template-advisor,
tikz-illustrator, tikz-validator, dictionary-manager, test-runner, link-checker,
file-splitter, literature-integrator, chapter-integrator, scientific-insight-generator,
content-reviewer, math-verifier, logic-auditor, scientific-rigor-auditor

Workflows: literature-integration, formalization-pipeline, tikz-illustration-pipeline,
environment-selection, pre-commit, section-review, full-document-review
```

**Router reads this section** to know what extension agents are available for routing.

Each extension plugin provides a **CLAUDE.md snippet** that users copy into their project:

```text
plugins/infolead-latex-tools/
├── ...
└── INSTALL_SNIPPET.md   ← Copy this into your project CLAUDE.md
```

---

## Router Discovery Logic

The router agent needs updated instructions to discover extension agents:

```markdown
## Extension Agent Discovery

1. Read project CLAUDE.md for "Installed Extensions" section
2. Parse listed agents from each extension
3. Include these agents in routing decisions
4. Route to extension agents using: `marketplace:plugin:agent` syntax
   Example: `infolead-claudecode-marketplace:latex-tools:syntax-fixer`
```

This keeps router self-contained — it doesn't need to know about extensions at build time, only at runtime via CLAUDE.md.

---

## Marketplace Configuration

**File:** `.claude-plugin/marketplace.json`

```json
{
  "name": "infolead-claudecode-marketplace",
  "description": "Infolead's Claude Code plugins: cost-optimized routing and domain-specific extensions",
  "owner": {
    "name": "Infolead",
    "url": "https://github.com/infolead"
  },
  "metadata": {
    "pluginRoot": "./plugins"
  },
  "plugins": [
    {
      "name": "infolead-claude-subscription-router",
      "source": "infolead-claude-subscription-router",
      "description": "Cost-optimized routing infrastructure with general agents",
      "tags": ["routing", "core", "required"]
    },
    {
      "name": "infolead-dev-tools",
      "source": "infolead-dev-tools",
      "description": "General development utilities: config audit, code review, testing, refactoring",
      "tags": ["dev", "review", "testing", "extension"]
    },
    {
      "name": "infolead-git-tools",
      "source": "infolead-git-tools",
      "description": "Git operations, commits, changelogs, and release management",
      "tags": ["git", "scm", "extension"]
    },
    {
      "name": "infolead-latex-tools",
      "source": "infolead-latex-tools",
      "description": "LaTeX authoring, literature integration, and academic workflows",
      "tags": ["latex", "research", "extension"]
    },
    {
      "name": "infolead-medical-tools",
      "source": "infolead-medical-tools",
      "description": "Personal health tracking and ME/CFS case documentation",
      "tags": ["medical", "health", "extension"]
    }
  ]
}
```

---

## Migration Steps

### Phase 1: Create Directory Structure

```bash
mkdir -p plugins/infolead-claude-subscription-router/{.claude-plugin,agents,implementation,hooks}
mkdir -p plugins/infolead-dev-tools/{.claude-plugin,agents}
mkdir -p plugins/infolead-git-tools/{.claude-plugin,agents}
mkdir -p plugins/infolead-latex-tools/{.claude-plugin,agents,workflows}
mkdir -p plugins/infolead-medical-tools/{.claude-plugin,agents}
```

### Phase 2: Move Router Plugin Content

Move all core routing content:

```bash
# Agents
mv agents/router.md plugins/infolead-claude-subscription-router/agents/
mv agents/router-escalation.md plugins/infolead-claude-subscription-router/agents/
mv agents/strategy-advisor.md plugins/infolead-claude-subscription-router/agents/
mv agents/haiku-general.md plugins/infolead-claude-subscription-router/agents/
mv agents/sonnet-general.md plugins/infolead-claude-subscription-router/agents/
mv agents/opus-general.md plugins/infolead-claude-subscription-router/agents/
mv agents/planner.md plugins/infolead-claude-subscription-router/agents/
mv agents/work-coordinator.md plugins/infolead-claude-subscription-router/agents/
mv agents/temporal-scheduler.md plugins/infolead-claude-subscription-router/agents/
mv agents/haiku-pre-router.md plugins/infolead-claude-subscription-router/agents/

# Implementation
mv implementation/* plugins/infolead-claude-subscription-router/implementation/

# Hooks
mv hooks/* plugins/infolead-claude-subscription-router/hooks/
```

### Phase 3: Create Extension Plugins

Copy/create agents for extension plugins:

```bash
# Dev tools (2 existing + 5 new)
cp ../health-me-cfs/.claude/agents/config-auditor.md plugins/infolead-dev-tools/agents/
cp ../health-me-cfs/.claude/agents/config-optimizer.md plugins/infolead-dev-tools/agents/
# Create new: code-reviewer.md, test-analyzer.md, refactor-advisor.md,
#             dependency-auditor.md, docs-generator.md

# Git tools (4 existing)
cp ../health-me-cfs/.claude/agents/commit-writer.md plugins/infolead-git-tools/agents/
cp ../health-me-cfs/.claude/agents/changelog-generator.md plugins/infolead-git-tools/agents/
cp ../health-me-cfs/.claude/agents/git-historian.md plugins/infolead-git-tools/agents/
cp ../health-me-cfs/.claude/agents/release-manager.md plugins/infolead-git-tools/agents/

# LaTeX tools (17 agents + 7 workflows)
cp ../health-me-cfs/.claude/agents/syntax-fixer.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/formatting-fixer.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/style-naturalizer.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/template-advisor.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/tikz-illustrator.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/tikz-validator.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/dictionary-manager.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/test-runner.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/link-checker.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/file-splitter.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/literature-integrator.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/chapter-integrator.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/scientific-insight-generator.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/content-reviewer.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/math-verifier.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/logic-auditor.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/agents/scientific-rigor-auditor.md plugins/infolead-latex-tools/agents/
cp ../health-me-cfs/.claude/workflows/*.md plugins/infolead-latex-tools/workflows/

# Medical tools (10 agents)
cp ../health-me-cfs/.claude/agents/case-documenter.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/medical-advisor.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/treatment-analyst.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/crisis-manager.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/pacing-coach.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/data-validator.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/hypothesis-generator.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/research-monitor.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/benefit-navigator.md plugins/infolead-medical-tools/agents/
cp ../health-me-cfs/.claude/agents/caregiver-coordinator.md plugins/infolead-medical-tools/agents/
```

### Phase 4: Create Plugin Manifests

**Router plugin** (`plugins/infolead-claude-subscription-router/.claude-plugin/plugin.json`):

```json
{
  "name": "infolead-claude-subscription-router",
  "version": "2.0.0",
  "description": "Cost-optimized routing with general agents",
  "author": { "name": "Yannick Loth" },
  "license": "MIT",
  "hooks": "../hooks/hooks.json"
}
```

**Extension plugins** (example for git-tools):

```json
{
  "name": "infolead-git-tools",
  "version": "1.0.0",
  "description": "Git operations and version control workflows",
  "author": { "name": "Yannick Loth" },
  "license": "MIT",
  "requires": ["infolead-claude-subscription-router"]
}
```

### Phase 5: Create INSTALL_SNIPPET.md for Each Extension

Each extension provides a snippet users copy to their project CLAUDE.md:

**Example:** `plugins/infolead-git-tools/INSTALL_SNIPPET.md`

```markdown
### infolead-git-tools

**Agents:** commit-writer, changelog-generator, git-historian, release-manager

Use for: Creating commits, generating changelogs, exploring git history, managing releases.
```

### Phase 6: Update Marketplace Root

1. Replace `.claude-plugin/plugin.json` with `.claude-plugin/marketplace.json`
2. Update root README.md with:
   - Marketplace installation instructions
   - Plugin overview table
   - Extension registration guide

### Phase 7: Update health-me-cfs Project

Update `health-me-cfs/.claude/CLAUDE.md`:

1. Remove local copies of agents now in marketplace
2. Add "Installed Extensions" section declaring active extensions
3. Update agent references to use marketplace syntax

### Phase 8: Clean Up

```bash
# Remove old directories (now empty or moved)
rm -rf agents/
rm -rf implementation/
rm -rf hooks/

# Keep for reference, then remove
rm -rf config/domains/
```

---

## Dependency Graph

```text
┌─────────────────────────────────────────┐
│            infolead-claude-subscription-router              │
│  (router, escalation, general agents,   │
│   strategy, planner, work-coordinator)  │
└────────────────────┬────────────────────┘
                     │ required by
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌─────────────┐ ┌──────────┐ ┌─────────────┐
│  git-tools  │ │latex-tools│ │medical-tools│
│ (4 agents)  │ │(17 agents)│ │ (10 agents) │
└─────────────┘ └──────────┘ └─────────────┘
```

---

## Installation Examples

```bash
# Add marketplace (once)
/plugin marketplace add infolead/infolead-claudecode-marketplace

# Install core router (required)
/plugin install infolead-claude-subscription-router@infolead-claudecode-marketplace

# Install extensions as needed
/plugin install infolead-dev-tools@infolead-claudecode-marketplace
/plugin install infolead-git-tools@infolead-claudecode-marketplace
/plugin install infolead-latex-tools@infolead-claudecode-marketplace
/plugin install infolead-medical-tools@infolead-claudecode-marketplace
```

Then add extension declaration to project CLAUDE.md:

```markdown
## Installed Extensions

### infolead-git-tools

Agents: commit-writer, changelog-generator, git-historian, release-manager

### infolead-latex-tools

Agents: syntax-fixer, formatting-fixer, style-naturalizer, template-advisor,
tikz-illustrator, tikz-validator, dictionary-manager, test-runner, link-checker,
file-splitter, literature-integrator, chapter-integrator, scientific-insight-generator,
content-reviewer, math-verifier, logic-auditor, scientific-rigor-auditor

Workflows: literature-integration, formalization-pipeline, tikz-illustration-pipeline,
environment-selection, pre-commit, section-review, full-document-review
```

---

## Verification Checklist

- [ ] `plugins/infolead-claude-subscription-router/` contains all 10 core agents
- [ ] `plugins/infolead-claude-subscription-router/` contains all implementation modules
- [ ] `plugins/infolead-claude-subscription-router/` contains hooks
- [ ] `plugins/infolead-dev-tools/` contains 7 agents (2 existing + 5 new)
- [ ] `plugins/infolead-git-tools/` contains 4 agents
- [ ] `plugins/infolead-latex-tools/` contains 17 agents + 7 workflows
- [ ] `plugins/infolead-medical-tools/` contains 10 agents
- [ ] Each plugin has valid `plugin.json`
- [ ] Marketplace `marketplace.json` lists all 5 plugins
- [ ] Each plugin is self-contained (no `../` references outside plugin)
- [ ] Each extension has `INSTALL_SNIPPET.md`
- [ ] Root README updated with installation instructions
- [ ] health-me-cfs CLAUDE.md updated with extension declarations
- [ ] Router agent updated with extension discovery logic
- [ ] All tests pass
- [ ] Hooks work from new location

---

## Risk Mitigation

**Risk:** Breaking existing projects using `claude-router-system`

**Mitigation:**

1. Tag current state as `v1.2.0` before refactor
2. Keep old plugin structure in a `legacy/` branch
3. Document migration path in README

**Risk:** Router doesn't discover extension agents

**Mitigation:**

1. Update router.md with explicit extension discovery instructions
2. Test with health-me-cfs project before release
3. Provide example CLAUDE.md with correct extension format

---

## Notes

- **5 plugins total:** 1 core (router) + 4 extensions (dev, git, latex, medical)
- **Extension registration:** Via project CLAUDE.md, not auto-discovery
- **Shared code:** Python modules stay in router plugin only (extensions don't need them)
- **Versioning:** Each plugin versioned independently
- **Hooks:** Stay in router plugin (extensions don't need hooks)

---

## Agent Reusability Analysis

Agents from health-me-cfs analyzed for reuse:

### Already Reusable (move to marketplace)

| Agent | Current Location | Target Plugin | Notes |
|-------|-----------------|---------------|-------|
| config-auditor | health-me-cfs | dev-tools | Language-agnostic |
| config-optimizer | health-me-cfs | dev-tools | Language-agnostic |
| commit-writer | health-me-cfs | git-tools | Universal git |
| changelog-generator | health-me-cfs | git-tools | Universal git |
| git-historian | health-me-cfs | git-tools | Universal git |
| release-manager | health-me-cfs | git-tools | Universal git |

### Domain-Specific (keep in domain plugins)

| Agent | Target Plugin | Reason |
|-------|---------------|--------|
| syntax-fixer | latex-tools | LaTeX-specific |
| tikz-* | latex-tools | LaTeX/TikZ-specific |
| literature-integrator | latex-tools | Academic paper workflow |
| case-documenter | medical-tools | ME/CFS-specific data model |
| medical-advisor | medical-tools | Health domain |

### New Agents to Create

| Agent | Plugin | Priority | Complexity |
|-------|--------|----------|------------|
| code-reviewer | dev-tools | High | Medium |
| test-analyzer | dev-tools | High | Medium |
| refactor-advisor | dev-tools | Medium | High |
| dependency-auditor | dev-tools | Medium | Low |
| docs-generator | dev-tools | Low | Medium |

### Potentially Generalizable (future consideration)

| Agent | Current Domain | Could Generalize To |
|-------|----------------|---------------------|
| content-reviewer | latex-tools | Any document type |
| data-validator | medical-tools | Any data validation |
| style-naturalizer | latex-tools | Any AI-written prose |

These could be promoted to dev-tools later with configuration for domain-specific rules.
