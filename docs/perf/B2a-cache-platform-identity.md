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
I want to make a trivial performance fix in nanobot/agent/context.py in nanobot-redux.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W

Problem: _get_identity() in ContextBuilder calls platform.system(), platform.machine(), and
platform.python_version() on every invocation, even though these values are constant for the
entire process lifetime.

Task:
1. Define module-level constants _RUNTIME_STRING (and any sub-constants needed) after the imports
2. Replace the computation in _get_identity() with the constant
3. Update or remove the import platform statement accordingly
4. ruff check . and pytest must be green
5. Commit with "refactor(context): cache platform identity as module constants"
6. Push to branch claude/analyze-performance-options-URI5W

Please read nanobot/agent/context.py in full first, then make the change.
```
