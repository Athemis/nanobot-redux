# B2a — Cache Platform Identity as Module Constants

**Priority:** P1 | **Effort:** Trivial | **Risk:** Minimal
**Status:** open

---

## Problem

`ContextBuilder._get_identity()` calls runtime functions on every invocation whose return values
never change:

```python
# nanobot/agent/context.py:81–82
system = platform.system()
runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"
```

`platform.system()`, `platform.machine()`, and `platform.python_version()` are constant for the
lifetime of the process. They are recomputed on every LLM call (every iteration of the agent loop).

**Impact:** Nanosecond-level individually, but semantically wrong — computing a constant on every
call is pure waste. Best example of a zero-risk, zero-tradeoff fix.

---

## Implementation Plan

Define module-level constants at the top of `context.py`, after the imports:

```python
# nanobot/agent/context.py — after imports, before class definition
import platform as _platform

_PLATFORM_SYSTEM = _platform.system()
_PLATFORM_MACHINE = _platform.machine()
_PYTHON_VERSION = _platform.python_version()
_RUNTIME_STRING = (
    f"{'macOS' if _PLATFORM_SYSTEM == 'Darwin' else _PLATFORM_SYSTEM} "
    f"{_PLATFORM_MACHINE}, Python {_PYTHON_VERSION}"
)
```

Then in `_get_identity()`, replace the two lines with:

```python
# Before:
system = platform.system()
runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"

# After:
runtime = _RUNTIME_STRING
```

The `import platform` at the top of the file can be removed (replaced by `import platform as
_platform` used only for computing the constants).

---

## Files and Line Numbers

| File | Lines | Content |
|------|-------|---------|
| `nanobot/agent/context.py` | 5 | `import platform` — update or replace |
| `nanobot/agent/context.py` | 74–82 | `_get_identity()` — replace `system` + `runtime` computation |

---

## Tests

No new tests needed. Run `pytest` to confirm nothing regressed.

---

## Session Prompt

```
Read `docs/perf/B2a-cache-platform-identity.md` first — it contains the full implementation
plan and the exact lines to change.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W
Commit message: "refactor(context): cache platform identity as module constants"

Implement the changes described in the plan, then run `ruff check .` and `pytest`, and push.
```
