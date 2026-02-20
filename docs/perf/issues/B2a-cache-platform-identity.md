<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    refactor(context): cache platform identity as module constants
  Labels: performance, enhancement
-->

## Problem / motivation

`ContextBuilder._get_identity()` in `nanobot/agent/context.py:81` calls
`platform.system()`, `platform.machine()`, and `platform.python_version()` on every invocation.
These values are constant for the entire lifetime of the process but are recomputed on every
LLM call (every iteration of the agent loop).

This is semantically incorrect — computing a constant on every call — and a zero-effort fix.

## Proposed solution

Define module-level constants once at import time and replace the per-call computation:

```python
# after imports, before class definition
import platform as _platform

_RUNTIME_STRING = (
    f"{'macOS' if _platform.system() == 'Darwin' else _platform.system()} "
    f"{_platform.machine()}, Python {_platform.python_version()}"
)
```

Then in `_get_identity()`:

```python
runtime = _RUNTIME_STRING   # replaces the 2-line computation
```

Full implementation plan: [`docs/perf/B2a-cache-platform-identity.md`](../B2a-cache-platform-identity.md)

## Alternatives considered

None — this is a pure refactor with no trade-offs.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
