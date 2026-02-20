# B3 — Session JSONL True Append-Only Writes

**Priority:** P2 | **Effort:** Low | **Risk:** Medium
**Status:** open

---

## Problem

`SessionManager.save()` opens the file with `"w"` (truncate + rewrite) and serialises every
message on every save:

```python
# nanobot/session/manager.py:142–156
def save(self, session: Session) -> None:
    path = self._get_session_path(session.key)
    with open(path, "w") as f:               # TRUNCATES THE ENTIRE FILE
        metadata_line = { ... }
        f.write(json.dumps(metadata_line) + "\n")
        for msg in session.messages:          # iterates ALL messages every time
            f.write(json.dumps(msg) + "\n")
```

The `Session` docstring explicitly states: *"Messages are append-only for LLM cache efficiency."*
Despite this intent, `save()` rewrites 200 messages even when only 1 is new.

**Growth:** 200 messages × ~500 bytes = ~100 KB rewrite per exchange.

---

## Current File Format (JSONL)

```
{"_type": "metadata", "created_at": "...", "updated_at": "...", "last_consolidated": 42}
{"role": "user", "content": "Hello", "timestamp": "..."}
{"role": "assistant", "content": "Hi!", "timestamp": "...", "tools_used": []}
...
```

The loader (`_load()`) reads the first line as metadata, the rest as messages.

---

## Implementation Plan

### 1. Add `_saved_count` to the `Session` dataclass

```python
# nanobot/session/manager.py — Session dataclass
from dataclasses import dataclass, field

@dataclass
class Session:
    key: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_consolidated: int = 0
    _saved_count: int = field(default=0, repr=False)   # transient — not persisted to JSONL
```

### 2. Update `_load()` to initialise `_saved_count`

After loading messages from disk, set `session._saved_count = len(messages)` so the first save
after a load does not rewrite anything already on disk.

### 3. Update `Session.clear()`

```python
def clear(self) -> None:
    self.messages = []
    self.last_consolidated = 0
    self._saved_count = 0          # force full rewrite on next save
    self.updated_at = datetime.now()
```

### 4. New `save()` logic

```python
def save(self, session: Session) -> None:
    path = self._get_session_path(session.key)
    new_messages = session.messages[session._saved_count:]

    if session._saved_count == 0 or not path.exists():
        # Full rewrite: first save or after clear()
        with open(path, "w") as f:
            metadata_line = {
                "_type": "metadata",
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata,
                "last_consolidated": session.last_consolidated,
            }
            f.write(json.dumps(metadata_line) + "\n")
            for msg in session.messages:
                f.write(json.dumps(msg) + "\n")
    else:
        # Append only new messages
        with open(path, "a") as f:
            for msg in new_messages:
                f.write(json.dumps(msg) + "\n")
        # Metadata on line 1 is now stale (updated_at, last_consolidated).
        # Acceptable: it will be corrected on the next full rewrite (after clear())
        # or on next process start (which always does a full rewrite of the first load).

    session._saved_count = len(session.messages)
    self._cache[session.key] = session
```

### Metadata Staleness Trade-off

JSONL does not support in-place line replacement without rewriting the whole file.
Keeping metadata accurate on every save would negate the benefit of append-only.
Chosen approach: let `updated_at` and `last_consolidated` in the on-disk metadata be
slightly stale; they are corrected on the next full rewrite. The in-memory `Session`
object always has accurate values.

---

## Files and Line Numbers

| File | Lines | Content |
|------|-------|---------|
| `nanobot/session/manager.py` | 14–52 | `Session` dataclass — add `_saved_count` field |
| `nanobot/session/manager.py` | 48–52 | `Session.clear()` — reset `_saved_count = 0` |
| `nanobot/session/manager.py` | 99–140 | `_load()` — set `_saved_count = len(messages)` after load |
| `nanobot/session/manager.py` | 142–158 | `save()` — implement append logic |

---

## Tests to Add

```python
# tests/test_session_manager.py
def test_save_appends_only_new_messages(tmp_path: Path) -> None:
    """Second save writes only the new message, not the full history."""
    mgr = SessionManager(tmp_path)
    session = mgr.get_or_create("test:chat")
    session.add_message("user", "Hello")
    mgr.save(session)

    path = mgr._get_session_path("test:chat")
    first_line_count = len(path.read_text().splitlines())

    session.add_message("assistant", "Hi!")
    mgr.save(session)

    lines = path.read_text().splitlines()
    assert len(lines) == first_line_count + 1   # only one new line added

def test_loaded_session_continues_append(tmp_path: Path) -> None:
    """Session loaded from disk continues in append mode (no duplicate messages)."""
    mgr = SessionManager(tmp_path)
    session = mgr.get_or_create("test:chat")
    session.add_message("user", "Hello")
    mgr.save(session)

    # Reload from disk
    mgr2 = SessionManager(tmp_path)
    session2 = mgr2.get_or_create("test:chat")
    session2.add_message("assistant", "Hi!")
    mgr2.save(session2)

    # Reload and verify no duplicates
    mgr3 = SessionManager(tmp_path)
    final = mgr3.get_or_create("test:chat")
    assert len(final.messages) == 2

def test_clear_triggers_full_rewrite(tmp_path: Path) -> None:
    """After clear(), next save does a full rewrite."""
    mgr = SessionManager(tmp_path)
    session = mgr.get_or_create("test:chat")
    session.add_message("user", "Hello")
    mgr.save(session)
    session.clear()
    session.add_message("user", "Fresh start")
    mgr.save(session)

    loaded = mgr._load("test:chat")
    assert loaded is not None
    assert len(loaded.messages) == 1
    assert loaded.messages[0]["content"] == "Fresh start"
```

---

## Session Prompt

```
I want to fix the session storage in nanobot-redux so saves are truly append-only.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W

Problem: SessionManager.save() in nanobot/session/manager.py:142 opens the JSONL file with "w"
and rewrites ALL messages on every save, even though the Session docstring says "Messages are
append-only for LLM cache efficiency." For a 200-message session this is a 100 KB rewrite per
exchange.

Task:
1. Add _saved_count: int = field(default=0, repr=False) as a transient field to Session
   (not persisted to JSONL)
2. At the end of _load(), set session._saved_count = len(messages)
3. In Session.clear(), add self._saved_count = 0
4. Rewrite save() so that:
   - If _saved_count == 0 or the file does not exist: full rewrite (existing behaviour)
   - Otherwise: open with "a" and write only messages[_saved_count:]
   - Set session._saved_count = len(session.messages) at the end of save()
5. Accept that on-disk metadata (updated_at, last_consolidated) will be slightly stale
   in append mode — this is an acceptable trade-off
6. Add tests in tests/test_session_manager.py
7. ruff check . and pytest must be green
8. Commit with "perf(session): switch save() to append-only writes"
9. Push to branch claude/analyze-performance-options-URI5W

Please read nanobot/session/manager.py in full first, then implement.
```
