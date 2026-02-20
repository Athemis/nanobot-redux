<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    perf(context): add TTL cache for bootstrap files and skills summary
  Labels: performance, enhancement
-->

## Problem / motivation

`ContextBuilder.build_system_prompt()` (`nanobot/agent/context.py:29`) reads up to six files
from disk on every call: `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `IDENTITY.md`, and
`MEMORY.md`, plus the skills directory. A typical request with 3 agent loop iterations triggers
this I/O **3 times** even though the files have not changed.

Under normal usage these files are stable for the duration of a session; only memory
consolidation updates `MEMORY.md`.

## Proposed solution

Add a 30-second TTL cache on `_load_bootstrap_files()` and `build_skills_summary()`, with an
explicit `invalidate_cache()` method called after memory consolidation and `/new`:

```python
def _load_bootstrap_files(self) -> str:
    now = time.monotonic()
    if now - self._bootstrap_cache_time < self._BOOTSTRAP_TTL:
        return self._bootstrap_cache
    result = self._load_bootstrap_files_uncached()
    self._bootstrap_cache = result
    self._bootstrap_cache_time = now
    return result

def invalidate_cache(self) -> None:
    self._bootstrap_cache_time = 0.0
    self._skills_summary_cache_time = 0.0
```

`datetime.now()` in `_get_identity()` is **not** cached — the current time must stay fresh.

Full implementation plan: [`docs/perf/B2b-cache-system-prompt.md`](../B2b-cache-system-prompt.md)

## Alternatives considered

- **`functools.lru_cache`** — not suitable because the cache key would need to include file
  mtimes to be correct; simpler to use explicit TTL with manual invalidation.
- **LLM provider-side prompt caching** (Anthropic/OpenAI) — orthogonal and complementary;
  tracked separately as P1.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
