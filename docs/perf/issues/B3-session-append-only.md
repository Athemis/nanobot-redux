<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    perf(session): switch SessionManager.save() to append-only writes
  Labels: performance, enhancement
-->

## Problem / motivation

`SessionManager.save()` (`nanobot/session/manager.py:142`) opens the JSONL file with `"w"`
(truncate + full rewrite) on every save:

```python
with open(path, "w") as f:
    f.write(json.dumps(metadata_line) + "\n")
    for msg in session.messages:       # ALL messages, every time
        f.write(json.dumps(msg) + "\n")
```

The `Session` docstring explicitly states *"Messages are append-only for LLM cache efficiency"*
— but `save()` contradicts this intent. For a 200-message session, every exchange rewrites
~100 KB even though only one message is new.

## Proposed solution

Track how many messages have already been written with a transient `_saved_count` field.
On subsequent saves, open with `"a"` and write only the new messages:

```python
@dataclass
class Session:
    ...
    _saved_count: int = field(default=0, repr=False)   # not persisted
```

```python
def save(self, session: Session) -> None:
    if session._saved_count == 0 or not path.exists():
        self._write_full(path, session)           # first write or after clear()
    else:
        with open(path, "a") as f:
            for msg in session.messages[session._saved_count:]:
                f.write(json.dumps(msg) + "\n")
    session._saved_count = len(session.messages)
```

On-disk metadata (`updated_at`, `last_consolidated`) will be slightly stale in append mode and
corrected on the next full rewrite — an acceptable trade-off for the write reduction.

Full implementation plan: [`docs/perf/B3-session-append-only.md`](../B3-session-append-only.md)

## Alternatives considered

- **SQLite backend** — more robust for concurrent access and atomic appends, but breaks the
  "grep-searchable JSONL" design principle from the redux manifest.
- **Periodic full rewrite** — simpler but still rewrites frequently; append-only aligns better
  with the stated design intent.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
