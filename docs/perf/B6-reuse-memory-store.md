# B6 — Reuse MemoryStore Instance in Memory Consolidation

**Priority:** P3 | **Effort:** Trivial | **Risk:** Minimal
**Status:** open

---

## Problem

`_consolidate_memory()` creates a new `MemoryStore` instance on every call:

```python
# nanobot/agent/loop.py:416
async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
    memory = MemoryStore(self.workspace)   # new instance every call
```

`MemoryStore.__init__` calls `ensure_dir()` which calls `Path.mkdir(parents=True, exist_ok=True)` —
a syscall — on every invocation. Meanwhile, `AgentLoop` already holds a `MemoryStore` via
`self.context.memory`, which is the same logical store pointing to the same workspace.

Having two live `MemoryStore` instances for the same workspace is also a correctness risk: if one
instance caches any state, the other will not see it.

---

## Implementation Plan

Replace the local construction with the existing instance:

```python
# nanobot/agent/loop.py:416
# Before:
memory = MemoryStore(self.workspace)

# After:
memory = self.context.memory
```

That is the entire change. One line.

---

## Files and Line Numbers

| File | Line | Content |
|------|------|---------|
| `nanobot/agent/loop.py` | 416 | Replace `MemoryStore(self.workspace)` with `self.context.memory` |

---

## Tests

No new tests needed for this one-liner. Run `pytest` to confirm nothing regressed.
If `MemoryStore` ever gains internal state (e.g. a read cache), add a test then.

---

## Session Prompt

```
Read `docs/perf/B6-reuse-memory-store.md` first — it contains the exact line to change and
the rationale.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W
Commit message: "refactor(loop): reuse context.memory in _consolidate_memory"

Implement the one-line change described in the plan, then run `ruff check .` and `pytest`,
and push.
```
