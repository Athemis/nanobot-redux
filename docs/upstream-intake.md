# Upstream Intake Process

This is how I evaluate and adopt changes from upstream (`HKUDS/nanobot`). It's intentionally manual and selective—I only pull in what I can test and maintain.

## Why This Exists

The upstream project moves fast and serves different goals. This process helps me:
- Stay compatible with useful upstream improvements
- Avoid adopting features I can't test or maintain
- Keep a clean audit trail of what came from where
- Make conscious decisions about what goes into redux

## What I Monitor

- **Pull Requests**: https://github.com/HKUDS/nanobot/pulls
- **Commits to main**: https://github.com/HKUDS/nanobot/commits/main
- **Releases**: https://github.com/HKUDS/nanobot/releases

I check these periodically (no fixed schedule) and flag anything that looks relevant.

## Adoption Workflow

### 1. Pick a Candidate

Look for PRs or commits that might be valuable. Good candidates:
- Fix bugs I've encountered
- Add features I'd actually use
- Improve security or stability
- Enhance existing channels/providers I rely on

Skip anything that:
- Adds channels/platforms I can't test (e.g., WeChat, obscure messaging apps)
- Introduces complex dependencies
- Conflicts with redux philosophy

### 2. Create an Intake Branch

```bash
# For PR #789 adding feature X
git checkout -b redux/intake/pr-789-feature-x

# Cherry-pick the relevant commits
git cherry-pick <commit-sha>

# Or apply selectively if conflicts arise
git diff <upstream-ref> -- path/to/relevant/files | git apply
```

### 3. Evaluate Against Criteria

Ask the questions from `docs/redux-manifest.md`:
- **Can I test it?** Do I have access to the necessary platforms/services?
- **Do I need it?** Does it solve a problem I actually have?
- **Is the risk acceptable?** Security, stability, maintenance burden?
- **Does it break compatibility?** CLI, modules, config paths must stay stable

### 4. Run Tests

```bash
# Linting
ruff check .

# Full test suite
pytest

# Targeted tests for affected areas
pytest tests/test_matrix_channel.py  # if Matrix-related
pytest tests/test_web_search_tool.py # if search-related

# Docker smoke test
bash tests/test_docker.sh

# Manual testing
nanobot agent -m "test the new feature"
nanobot gateway  # if channel-related
```

### 5. Make a Decision

**Adopt** → Merge into `redux/main`:
```bash
git checkout redux/main
git merge --no-ff redux/intake/pr-789-feature-x
git branch -d redux/intake/pr-789-feature-x
```

**Defer** → Note it for future consideration:
- Add to "Deferred" section in `docs/upstream-log.md`
- Include reason (e.g., "needs testing setup I don't have yet")
- Delete the intake branch

**Reject** → Not relevant for redux:
- Optionally note in `upstream-log.md` if it's significant
- Delete the intake branch

### 6. Document the Adoption

If adopted, add an entry to `docs/upstream-log.md`:

```markdown
| [#789](https://github.com/HKUDS/nanobot/pull/789) | Web search | Added Perplexity provider support | low | `pytest tests/test_web_search_tool.py` | adopted (2025-01-15) |
```

Include:
- PR/commit link
- What area it affects
- Why I adopted it
- Risk assessment
- How to verify it works
- Adoption date

## Example: Real Adoption

Here's how I'd handle adopting a hypothetical upstream PR:

**Scenario**: Upstream PR #890 adds improved error handling for Matrix sync failures.

```bash
# 1. Create intake branch
git checkout -b redux/intake/pr-890-matrix-error-handling

# 2. Cherry-pick the changes
git cherry-pick abc123def

# 3. Review the changes
git show abc123def
# Looks good - just adds try/catch and better logging

# 4. Test it
pytest tests/test_matrix_channel.py
# All pass

# Manual test: force a sync error and verify logging
nanobot gateway
# Check logs: better error messages confirmed

# 5. Adopt it
git checkout redux/main
git merge --no-ff redux/intake/pr-890-matrix-error-handling

# 6. Document in upstream-log.md
# Added row: PR #890 | Matrix channel | Better sync error handling | low | manual testing | adopted (2025-01-15)

# Clean up
git branch -d redux/intake/pr-890-matrix-error-handling
```

## Tracking Deferred Changes

When I defer something, I add it to a "Deferred" section in `upstream-log.md`:

| Upstream PR | Area | Why Deferred | Revisit When |
|---|---|---|---|
| #999 | Discord channel | Don't use Discord | If I start using Discord |
| #1000 | Advanced memory | Needs more testing | After 0.3.0 release |

This helps me remember to check back later without cluttering the main log.

## Tips

- **Start small**: Cherry-pick individual commits rather than merging entire branches
- **Test thoroughly**: Especially for security-related changes
- **Document reasoning**: Future you will thank you
- **When in doubt, defer**: Better to wait than break your setup
- **Keep branches clean**: Delete intake branches after adoption or rejection

## Related Docs

- [`docs/redux-manifest.md`](redux-manifest.md) - Adoption criteria and fork philosophy
- [`docs/upstream-log.md`](upstream-log.md) - History of adopted changes
- [`docs/release-template.md`](release-template.md) - How to release after adoption