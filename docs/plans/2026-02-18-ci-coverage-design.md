# CI Code Coverage Design

**Date:** 2026-02-18
**Status:** Approved

## Goal

Integrate code coverage measurement into the test suite so that CI fails when coverage drops below the current baseline.

## Decisions

- **No external service.** Coverage is reported locally in CI logs only (no Codecov, Coveralls, etc.).
- **Fail on regression.** CI fails if total coverage drops below the threshold.
- **Threshold: 63%.** Matches current measured coverage, freezing the status quo without requiring immediate test additions.

## Changes

### `pyproject.toml`

Add `pytest-cov` to `[project.optional-dependencies] dev`.

Add `addopts` to `[tool.pytest.ini_options]`:

```toml
addopts = "--cov=nanobot --cov-report=term-missing --cov-fail-under=63"
```

This ensures coverage runs automatically on every `pytest` invocation — locally and in CI — without touching `.github/workflows/tests.yml`.

## Non-Changes

- `tests.yml` remains unchanged; `addopts` handles everything.
- No coverage badge, no upload step, no HTML report artifact.
