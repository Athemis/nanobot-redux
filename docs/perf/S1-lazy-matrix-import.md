# S1 — Lazy Matrix Import in CLI

**Priority:** P3 | **Effort:** Low | **Risk:** Low
**Status:** open

---

## Problem

The `matrix-nio[e2e]` dependency includes Olm cryptography bindings (C extension) that take
150–300 ms to import on first load. The Matrix channel is already not imported in the package
`__init__.py`, but somewhere in the CLI startup path `MatrixChannel` is imported unconditionally
— even when no Matrix config is present.

**Impact:** 150–300 ms added to every `nanobot` CLI invocation, including simple operations like
`nanobot --help` or `nanobot ask "..."`, even for users who never use Matrix.

---

## Investigation Required

Before implementing, locate the exact import path:

```bash
grep -r "MatrixChannel\|from nanobot.channels.matrix" nanobot/cli/ nanobot/__init__.py
```

Likely candidates:
- `nanobot/cli/commands.py` or equivalent
- The channel manager that registers all channels at startup

---

## Implementation Plan

Guard the import behind a config check:

```python
# Wherever MatrixChannel is currently imported unconditionally:

# Before:
from nanobot.channels.matrix import MatrixChannel
channel_manager.register(MatrixChannel(config))

# After:
if config.matrix and config.matrix.enabled:
    from nanobot.channels.matrix import MatrixChannel   # import only when needed
    channel_manager.register(MatrixChannel(config))
```

If the import is at module level (top of file), move it inside the function/method that
constructs channels.

### Alternative: TYPE_CHECKING guard

If `MatrixChannel` is only used as a type annotation, use:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nanobot.channels.matrix import MatrixChannel
```

This removes the runtime import entirely for non-Matrix users.

---

## Files and Line Numbers

Determine exact locations by running:

```
grep -rn "MatrixChannel\|nanobot.channels.matrix" nanobot/
```

Expected locations:
- `nanobot/cli/commands.py` or `nanobot/cli/app.py`
- `nanobot/channels/__init__.py` (if it re-exports)

---

## Tests to Add

```python
# tests/test_startup.py
def test_matrix_not_imported_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """matrix_nio is not imported when Matrix is not configured."""
    import sys
    # Remove matrix_nio from sys.modules to detect fresh import
    for key in list(sys.modules):
        if "matrix_nio" in key or "olm" in key:
            del sys.modules[key]

    # Create config without Matrix
    # Import CLI entry point
    # Assert "matrix_nio" not in sys.modules
    ...
```

---

## Session Prompt

```
Read `docs/perf/S1-lazy-matrix-import.md` first — it contains the investigation step,
implementation plan, and test to add.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W
Commit message: "perf(cli): lazy-import MatrixChannel behind config check"

Implement the changes described in the plan, then run `ruff check .` and `pytest`, and push.
```
