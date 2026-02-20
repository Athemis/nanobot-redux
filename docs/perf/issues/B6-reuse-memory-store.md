<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    refactor(loop): reuse context.memory in _consolidate_memory
  Labels: performance, enhancement
-->

## Problem / motivation

`_consolidate_memory()` in `nanobot/agent/loop.py:416` constructs a new `MemoryStore` instance
on every call:

```python
async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
    memory = MemoryStore(self.workspace)   # new instance every call
```

`MemoryStore.__init__` calls `ensure_dir()` → `Path.mkdir(parents=True, exist_ok=True)`, a
syscall, each time. `AgentLoop` already holds an equivalent `MemoryStore` at
`self.context.memory` pointing to the same workspace — there is no reason to create a second
instance.

Maintaining two `MemoryStore` instances for the same path is also a latent correctness risk if
either ever gains internal state (e.g. a read cache).

## Proposed solution

Replace the one-liner:

```python
# Before
memory = MemoryStore(self.workspace)

# After
memory = self.context.memory
```

Then check whether the `MemoryStore` import at the top of `loop.py` is still needed elsewhere;
remove it if not.

Full implementation plan: [`docs/perf/B6-reuse-memory-store.md`](../B6-reuse-memory-store.md)

## Alternatives considered

None — this is an unambiguous simplification with no trade-offs.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
