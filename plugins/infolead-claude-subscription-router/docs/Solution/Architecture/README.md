# System Architecture

This directory contains the complete system architecture design and routing guidelines for Claude Code integration.

## Files

- **[architecture.md](architecture.md)** - Complete system architecture design (3900+ lines)
  - Overall architecture and component breakdown
  - IVP (Independent Variation Principle) compliance
  - Design decisions and rationale

- **[CLAUDE-ROUTING-ADVISORY.md](CLAUDE-ROUTING-ADVISORY.md)** - Mandatory routing system guide
  - How the routing system works
  - Your responsibilities as Claude
  - Execution rules for routing directives
  - Example scenarios and best practices

## Key Concepts

### Mandatory Routing System

The router provides **binding directives** via the UserPromptSubmit hook:

- **When decision == "escalate"**: Invoke the router agent with the user's request
- **When decision == "direct"**: Invoke the specified agent (haiku-general, sonnet-general, or opus-general)

**No interpretation, hesitation, or override allowed** - routing decisions are mechanical and deterministic.

### Architecture Design

The system is designed with **Independent Variation Principle (IVP)**:
- Each component changes only when its specific change driver changes
- Clear separation of concerns
- Measurable and auditable routing decisions

## Reading Guide

1. **Start here**: [CLAUDE-ROUTING-ADVISORY.md](CLAUDE-ROUTING-ADVISORY.md) - Understand how to handle routing directives
2. **Deep dive**: [architecture.md](architecture.md) - Understand the complete system design

## See Also

- [Implementation details](../Implementation/) - Workarounds and features
- [Solution overview](../) - Review findings and fixes
- [Requirements](../../Requirements/) - System constraints
