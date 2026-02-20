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
I want to fix a minor inefficiency in nanobot-redux's agent loop.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W

Problem: _consolidate_memory() in nanobot/agent/loop.py line 416 creates a new MemoryStore
instance on every call ("memory = MemoryStore(self.workspace)"), which triggers a mkdir syscall
each time. AgentLoop already has self.context.memory pointing to the same workspace — there is
no reason to create a second instance.

Task:
1. Replace "memory = MemoryStore(self.workspace)" with "memory = self.context.memory" at line 416
2. Verify the MemoryStore import at the top of loop.py is still needed elsewhere; remove if not
3. ruff check . and pytest must be green
4. Commit with "refactor(loop): reuse context.memory in _consolidate_memory"
5. Push to branch claude/analyze-performance-options-URI5W

Please read nanobot/agent/loop.py lines 409-493 to understand the consolidation method first.
```
