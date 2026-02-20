# B5 — Cache Tool Definitions

**Priority:** P3 | **Effort:** Trivial | **Risk:** Minimal
**Status:** open

---

## Problem

`ToolRegistry.get_definitions()` is called on every LLM call inside the agent loop:

```python
# nanobot/agent/loop.py:199
response = await self.provider.chat(
    messages=messages,
    tools=self.tools.get_definitions(),   # called every iteration
    model=self.model,
    ...
)
```

`get_definitions()` iterates all registered tools and calls `tool.to_schema()` on each:

```python
# nanobot/agent/tools/registry.py:35–37
def get_definitions(self) -> list[dict[str, Any]]:
    """Get all tool definitions in OpenAI format."""
    return [tool.to_schema() for tool in self._tools.values()]
```

Tools are registered once at startup and never change during a session. The schema serialisation
is pure Python and typically < 1 ms, but it is genuinely wasted work on every iteration.

---

## Implementation Plan

Cache the result on first call and invalidate on `register()` / `unregister()`:

```python
# nanobot/agent/tools/registry.py

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._definitions_cache: list[dict[str, Any]] | None = None

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        self._definitions_cache = None   # invalidate

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)
        self._definitions_cache = None   # invalidate

    def get_definitions(self) -> list[dict[str, Any]]:
        if self._definitions_cache is None:
            self._definitions_cache = [tool.to_schema() for tool in self._tools.values()]
        return self._definitions_cache
```

---

## Files and Line Numbers

| File | Lines | Content |
|------|-------|---------|
| `nanobot/agent/tools/registry.py` | 15–37 | Add `_definitions_cache`; update `register`, `unregister`, `get_definitions` |

---

## Tests to Add

```python
# tests/test_tool_registry.py
def test_get_definitions_cached() -> None:
    """get_definitions() returns the same list object on repeated calls."""
    registry = ToolRegistry()
    registry.register(some_tool)
    first = registry.get_definitions()
    second = registry.get_definitions()
    assert first is second   # same object, not recomputed

def test_register_invalidates_cache() -> None:
    """Registering a new tool clears the cache."""
    registry = ToolRegistry()
    registry.register(tool_a)
    first = registry.get_definitions()
    registry.register(tool_b)
    second = registry.get_definitions()
    assert first is not second
    assert len(second) == 2
```

---

## Session Prompt

```
Read `docs/perf/B5-cache-tool-definitions.md` first — it contains the full implementation
plan and tests to add.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W
Commit message: "perf(registry): cache tool definitions between LLM calls"

Implement the changes described in the plan, then run `ruff check .` and `pytest`, and push.
```
