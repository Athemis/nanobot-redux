# Release Template (nanobot redux)

Use this checklist when preparing a new release. Copy and fill it out in release notes or commit messages.

## Release Meta

- Version: `0.x.y`
- Date: `YYYY-MM-DD`
- Tag: `v0.x.y`

## Summary

Brief description of what changed and why this release matters.

Example: "Adds SearXNG support for self-hosted search, improves Matrix E2EE stability, and fixes workspace path validation bug."

## Upstream Changes Adopted (if any)

List upstream PRs/commits adopted in this release:

- [HKUDS#123](https://github.com/HKUDS/nanobot/pull/123) - Brief rationale for adopting
- [HKUDS#456](https://github.com/HKUDS/nanobot/pull/456) - Why this was needed

If no upstream changes: "None - fork-native release only"

## Fork-Native Changes

New features, fixes, or improvements specific to redux:

- Feature/fix description
- Feature/fix description
- Refactoring or cleanup work

## Breaking Changes (if any)

Changes that break existing setups or require user action:

- **Config change**: Description of what changed and why
- **CLI change**: Command syntax or behavior change
- **API change**: Module/function signature change

If no breaking changes: "None"

## Migration Notes (if needed)

Step-by-step instructions for users to update their setup:

```bash
# Example migration steps
cd squidbot
git pull
pip install -e ".[dev]"
# Update config: add new field X to ~/.nanobot/config.json
```

If no migration needed: "None - drop-in replacement"

## Verification

Tests and checks performed before release:

- [x] `ruff check .` - no issues
- [x] `pytest` - all pass
- [x] `bash tests/test_docker.sh` - container builds and runs
- [x] Targeted tests: `<specific test commands for affected areas>`
- [x] Manual testing: `<what you tested manually>`

## Compatibility Guarantees

These remain stable across versions:

- CLI: `nanobot` unchanged
- Python package: `nanobot.*` unchanged
- Config path: `~/.nanobot/*` unchanged

(Note any exceptions if compatibility was intentionally broken)

## Notes

- Releases happen when things feel stable - no fixed schedule
- See `docs/upstream-log.md` for detailed adoption history
- See `docs/redux-manifest.md` for fork philosophy and priorities

## Example Release Notes Format

For GitHub releases or CHANGELOG:

```markdown
## [0.2.1] - 2026-02-16

### Added
- SearXNG web search provider support
- Matrix E2EE session persistence improvements

### Changed
- Updated shell security regex patterns
- Improved workspace path validation

### Fixed
- Matrix sync token loss on restart
- Email IMAP timeout handling

### Upstream
- Adopted HKUDS#789 for improved memory handling
```
