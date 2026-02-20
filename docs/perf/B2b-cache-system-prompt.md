# B2b — System Prompt TTL Cache

**Priority:** P1 | **Effort:** Low | **Risk:** Low
**Status:** open

---

## Problem

`ContextBuilder.build_system_prompt()` is called on every iteration of the agent loop and reads
the same files from disk each time:

```python
# nanobot/agent/context.py:29–72
def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
    parts.append(self._get_identity())           # platform calls + datetime.now()
    bootstrap = self._load_bootstrap_files()     # reads AGENTS.md, SOUL.md, USER.md, TOOLS.md, IDENTITY.md
    memory = self.memory.get_memory_context()    # reads MEMORY.md
    always_skills = self.skills.get_always_skills()     # reads skills/
    skills_summary = self.skills.build_skills_summary() # reads skills/
```

A typical request with 3 agent loop iterations reads the bootstrap files **3 times** even though
they have not changed.

**What must stay fresh:** `datetime.now()` in `_get_identity()` (current time) and `MEMORY.md`
(updated after consolidation). Everything else is stable within a session.

---

## Implementation Plan

### TTL cache with explicit invalidation

Add cache attributes to `ContextBuilder.__init__`:

```python
import time

class ContextBuilder:
    _BOOTSTRAP_TTL: float = 30.0   # seconds

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)
        self._bootstrap_cache: str = ""
        self._bootstrap_cache_time: float = 0.0
        self._skills_summary_cache: str = ""
        self._skills_summary_cache_time: float = 0.0
```

Wrap `_load_bootstrap_files()`:

```python
def _load_bootstrap_files(self) -> str:
    now = time.monotonic()
    if now - self._bootstrap_cache_time < self._BOOTSTRAP_TTL:
        return self._bootstrap_cache
    result = self._load_bootstrap_files_uncached()
    self._bootstrap_cache = result
    self._bootstrap_cache_time = now
    return result
```

Add an invalidation method:

```python
def invalidate_cache(self) -> None:
    """Force fresh disk reads on next build_system_prompt() call."""
    self._bootstrap_cache_time = 0.0
    self._skills_summary_cache_time = 0.0
```

### Invalidation Call Sites

| When | Where |
|------|-------|
| After `/new` command | `loop._handle_slash_command()` |
| After memory consolidation | end of `loop._consolidate_memory()` |

### What NOT to Cache

`datetime.now()` in `_get_identity()` must remain fresh — do **not** cache the identity section.
`MEMORY.md` updates right after consolidation, so `memory.get_memory_context()` should either
use a short TTL (5 s) or be invalidated explicitly via `invalidate_cache()`.

---

## Files and Line Numbers

| File | Lines | Content |
|------|-------|---------|
| `nanobot/agent/context.py` | 23–27 | `__init__` — add cache attributes |
| `nanobot/agent/context.py` | 117–127 | `_load_bootstrap_files()` — add TTL logic |
| `nanobot/agent/context.py` | 56–70 | `build_skills_summary()` call — add TTL logic |
| `nanobot/agent/context.py` | — | add `invalidate_cache()` method |
| `nanobot/agent/loop.py` | ~409 | `_consolidate_memory()` — call `self.context.invalidate_cache()` at end |

---

## Tests to Add

```python
# tests/test_context.py
def test_bootstrap_cache_avoids_repeated_disk_reads(tmp_path: Path) -> None:
    """Second call within TTL returns cached result without reading disk again."""
    ctx = ContextBuilder(tmp_path)
    (tmp_path / "AGENTS.md").write_text("hello")
    first = ctx.build_system_prompt()
    (tmp_path / "AGENTS.md").write_text("changed")   # change file on disk
    second = ctx.build_system_prompt()               # should still return cached
    assert "hello" in second
    assert "changed" not in second

def test_invalidate_cache_forces_fresh_read(tmp_path: Path) -> None:
    """invalidate_cache() causes next call to read from disk."""
    ctx = ContextBuilder(tmp_path)
    (tmp_path / "AGENTS.md").write_text("hello")
    ctx.build_system_prompt()
    (tmp_path / "AGENTS.md").write_text("changed")
    ctx.invalidate_cache()
    result = ctx.build_system_prompt()
    assert "changed" in result
```

---

## Session Prompt

```
I want to add a TTL cache for the system prompt in nanobot-redux's ContextBuilder.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W

Problem: build_system_prompt() in nanobot/agent/context.py reads bootstrap files (AGENTS.md,
SOUL.md, USER.md, TOOLS.md, IDENTITY.md) and skills from disk on every agent loop iteration.
A typical 3-iteration request reads these files 3 times unnecessarily.

Task:
1. Add _bootstrap_cache, _bootstrap_cache_time, _skills_summary_cache,
   _skills_summary_cache_time instance attributes to ContextBuilder.__init__
2. Wrap _load_bootstrap_files() with a 30-second TTL (use time.monotonic())
3. Wrap the skills summary computation with the same TTL
4. Add an invalidate_cache() method that resets both timestamps to 0.0
5. Call self.context.invalidate_cache() at the end of _consolidate_memory() in loop.py
6. Do NOT cache datetime.now() — the current time must stay fresh
7. Add tests in tests/test_context.py
8. ruff check . and pytest must be green
9. Commit with "perf(context): add TTL cache for bootstrap files and skills summary"
10. Push to branch claude/analyze-performance-options-URI5W

Please read nanobot/agent/context.py in full first, then loop.py from line 409.
```
