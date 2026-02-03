# Infolead Claude Code Marketplace

A collection of plugins and tools for extending Claude Code with intelligent agent routing, cost optimization, and workflow automation.

## Overview

This marketplace provides production-ready plugins that enhance Claude Code's capabilities through:

- **Intelligent agent routing** - Automatically select the right model tier (Haiku/Sonnet/Opus) based on task complexity
- **Cost optimization** - Minimize API costs while maintaining quality through smart delegation
- **Workflow automation** - Coordinate multi-step processes with specialized agents
- **State management** - Persistent cross-session memory and work queue coordination

## Available Plugins

### Infolead Claude Subscription Router

**Status:** Production-ready
**Location:** `plugins/infolead-claude-subscription-router/`

An intelligent routing system that analyzes user requests and delegates to the appropriate model tier. Features include:

- **Automatic escalation** - Complex tasks route to more capable models
- **Risk assessment** - Destructive operations get extra scrutiny
- **WIP limits** - Prevent overwhelming parallel execution
- **Semantic caching** - Avoid redundant expensive operations
- **Cross-session state** - Persistent memory between Claude Code sessions

**Quick start:**
```bash
# Install the plugin
ln -s $(pwd)/plugins/infolead-claude-subscription-router/.claude-plugin \
      ~/.claude/plugins/infolead-claude-subscription-router

# Copy the configuration template to your project
cp plugins/infolead-claude-subscription-router/EXAMPLE.claude.md \
   your-project/.claude/CLAUDE.md

# Verify installation
claude /plugins
```

See [plugin documentation](plugins/infolead-claude-subscription-router/README.md) for full details.

## Roadmap

See [REFACTOR_PLAN.md](REFACTOR_PLAN.md) for the marketplace evolution plan, including:

- Additional plugins (code review, testing, documentation)
- Plugin discovery and versioning system
- Community contribution guidelines
- Quality standards and certification

## Repository Structure

```
claude-router-system/
├── plugins/
│   └── infolead-claude-subscription-router/  # Router plugin
│       ├── .claude-plugin/                    # Plugin definition
│       ├── docs/                              # Documentation
│       └── README.md                          # Plugin-specific docs
├── tests/
│   └── infolead-claude-subscription-router/   # Plugin tests
├── README.md                                  # This file
└── REFACTOR_PLAN.md                          # Roadmap
```

## Installation

### Prerequisites

- Claude Code CLI installed
- Nix package manager (for running tests)
- Python 3.12+ (for development)

### Installing Plugins

**Option 1: Symlink (recommended for development)**
```bash
ln -s $(pwd)/plugins/PLUGIN_NAME/.claude-plugin \
      ~/.claude/plugins/PLUGIN_NAME
```

**Option 2: Copy (for stable usage)**
```bash
cp -r plugins/PLUGIN_NAME/.claude-plugin \
      ~/.claude/plugins/PLUGIN_NAME
```

### Verifying Installation

```bash
# Start Claude Code and check plugins loaded
claude /plugins

# Verify agents available
claude /agents
```

## Testing

Each plugin includes comprehensive tests:

```bash
# Run all tests for a plugin
./tests/PLUGIN_NAME/run_all_tests.sh

# Run specific test suites
./tests/PLUGIN_NAME/test_hooks.sh
nix-shell -p python312Packages.pytest python312Packages.pyyaml \
  --run "pytest tests/PLUGIN_NAME/ -v"
```

See individual plugin documentation for detailed testing guides.

## Development

### Adding a New Plugin

1. Create plugin directory: `plugins/your-plugin-name/`
2. Add `.claude-plugin/` structure (see existing plugins as templates)
3. Write comprehensive tests in `tests/your-plugin-name/`
4. Document in `plugins/your-plugin-name/README.md`
5. Update this README's plugin list

### Plugin Structure Requirements

Each plugin must include:

- `.claude-plugin/plugin.json` - Plugin metadata
- `.claude-plugin/agents/*.md` - Agent definitions
- `.claude-plugin/hooks/` - Event hooks (optional)
- `README.md` - Plugin documentation
- `tests/` - Comprehensive test suite

## Contributing

Contributions are welcome! Please:

1. Follow the plugin structure requirements
2. Include comprehensive tests (aim for >90% coverage)
3. Document all features and configuration options
4. Ensure tests pass: `./tests/PLUGIN_NAME/run_all_tests.sh`

## License

MIT License - see individual plugin directories for specific licensing details.

## Support

- **Documentation:** See `plugins/*/docs/` for detailed guides
- **Issues:** GitHub Issues for bug reports and feature requests
- **Discussions:** GitHub Discussions for questions and community support

## Credits

Created and maintained by Infolead.

Built on [Claude Code](https://claude.ai/code) by Anthropic.