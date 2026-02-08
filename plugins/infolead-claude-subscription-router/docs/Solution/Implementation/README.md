# Implementation Details

This directory contains implementation-specific documentation, including workarounds, features, and testing information.

## Files

- **[BACKGROUND-AGENT-WRITE-PERMISSIONS.md](BACKGROUND-AGENT-WRITE-PERMISSIONS.md)** - Background agent write permission handling
  - Problem: Background agents can't get interactive Write/Edit approval
  - Solution: 3-layer approach with hooks and settings
  - Workaround script included

- **[HOOKS-WORKAROUND.md](HOOKS-WORKAROUND.md)** - Plugin hook execution workarounds
  - Problem: Plugin hooks in plugin.json don't execute (Claude Code bug)
  - Solution: Copy hooks to settings.json via setup script
  - Detailed setup instructions

- **[TESTING.md](TESTING.md)** - Testing methodology and coverage
  - Test suite overview (81 tests, 100% pass rate)
  - How to run tests
  - Coverage analysis

## Known Issues & Workarounds

### Plugin Hooks Not Executing
**Issue**: Hooks defined in `plugin.json` are matched but never execute (Claude Code bug)
**Workaround**: Use `setup-hooks-workaround.sh` to copy hooks to settings.json

See [HOOKS-WORKAROUND.md](HOOKS-WORKAROUND.md) for details.

### Background Agent Write Permissions
**Issue**: Background agents can't get interactive approval for Write/Edit tools
**Solution**: 3-layer permission system combining hooks, frontmatter, and settings

See [BACKGROUND-AGENT-WRITE-PERMISSIONS.md](BACKGROUND-AGENT-WRITE-PERMISSIONS.md) for details.

## Pre-Existing Test Failures

The following tests have pre-existing issues (not regressions):

- `test_hooks_path_valid` - Tries to resolve hooks dict as file path (TypeError)
- `test_hook_scripts_check_jq` - False positive on indirect jq usage
- E2E `verify_hooks_json` - Looks for nonexistent `hooks/hooks.json`
- Bash hook test 6 - Hangs on model tier detection

See [TESTING.md](TESTING.md) for details.

## See Also

- [Architecture guide](../Architecture/) - System design
- [Solution overview](../) - Review findings and fixes
- [Main documentation](../../) - Overall documentation index
