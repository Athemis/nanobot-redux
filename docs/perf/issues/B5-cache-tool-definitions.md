<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    perf(registry): cache tool definitions between LLM calls
  Labels: performance, enhancement
-->

## Problem / motivation

`ToolRegistry.get_definitions()` (`nanobot/agent/tools/registry.py:35`) is called on every LLM
API call inside the agent loop:

```python
response = await self.provider.chat(
    ...
    tools=self.tools.get_definitions(),   # every iteration
)
```

It re-serialises all tool schemas on each call via `tool.to_schema()`. Tools are registered
once at startup and never change during a session, so this is repeated pure-Python work with
no benefit.

## Proposed solution

Cache the result on first call; invalidate on `register()` and `unregister()`:

```python
class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._definitions_cache: list[dict[str, Any]] | None = None

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        self._definitions_cache = None

    def get_definitions(self) -> list[dict[str, Any]]:
        if self._definitions_cache is None:
            self._definitions_cache = [t.to_schema() for t in self._tools.values()]
        return self._definitions_cache
```

Full implementation plan: [`docs/perf/B5-cache-tool-definitions.md`](../B5-cache-tool-definitions.md)

## Alternatives considered

None — this is a straightforward cache-on-first-use pattern with automatic invalidation.
The only risk (mutating a cached list externally) does not apply since callers only pass it to
the provider API.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
