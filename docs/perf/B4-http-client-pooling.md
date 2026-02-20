# B4 — HTTP Client Connection Pooling

**Priority:** P2 | **Effort:** Low | **Risk:** Low
**Status:** open

---

## Problem

Both `WebSearchTool` and `WebFetchTool` create a new `httpx.AsyncClient` on every call:

```python
# nanobot/agent/tools/web.py:125
async with httpx.AsyncClient(transport=self._transport) as client:
    r = await client.get(...)
```

```python
# nanobot/agent/tools/web.py:149
async with httpx.AsyncClient(transport=self._transport) as client:
    r = await client.post(...)
```

`httpx.AsyncClient` maintains a connection pool internally. Creating one per request discards the
pool entirely, forcing a fresh TCP handshake (and TLS negotiation) on every web search or fetch.

**Impact:** Each TLS handshake adds 50–300 ms. For web-heavy workflows (multiple searches per
agent turn) this is measurable and cumulative.

---

## Current Locations

Both patterns appear in these methods:

| Method | File | Line |
|--------|------|------|
| `_search_brave()` | `nanobot/agent/tools/web.py` | ~125 |
| `_search_tavily()` | `nanobot/agent/tools/web.py` | ~149 |
| `WebFetchTool.execute()` | `nanobot/agent/tools/web.py` | varies |

SearXNG and other providers likely follow the same pattern. Check when implementing.

---

## Implementation Plan

### Option A (recommended): Shared client as instance attribute

```python
# In WebSearchTool.__init__
class WebSearchTool(Tool):
    def __init__(self, config: ...) -> None:
        ...
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            transport=self._transport,
            timeout=10.0,
        )
```

Replace all `async with httpx.AsyncClient(...) as client:` blocks with direct `self._client`
usage:

```python
# Before
async with httpx.AsyncClient(transport=self._transport) as client:
    r = await client.get(url, ...)

# After
r = await self._client.get(url, ...)
```

Add a `close()` method so the agent loop can clean up:

```python
async def close(self) -> None:
    await self._client.aclose()
```

### Lifecycle Management

The `AgentLoop` already uses an `AsyncExitStack` for MCP server lifecycle
(`nanobot/agent/loop.py`, `_connect_mcp()`). Register the tool client there:

```python
# nanobot/agent/loop.py — in _connect_mcp() or a new _setup_tools() method
if hasattr(self.tools.get("web_search"), "close"):
    self._exit_stack.push_async_callback(self.tools.get("web_search").close)
```

Alternatively, implement `__aenter__`/`__aexit__` on the tool and register it with the stack.

---

## Files and Line Numbers

| File | Lines | Content |
|------|-------|---------|
| `nanobot/agent/tools/web.py` | ~30–60 | `WebSearchTool.__init__` — add `self._client` |
| `nanobot/agent/tools/web.py` | ~125, ~149 | Replace `async with AsyncClient(...)` |
| `nanobot/agent/tools/web.py` | — | Add `close()` / `__aexit__` method |
| `nanobot/agent/loop.py` | ~250 (`_connect_mcp`) | Register tool close in exit stack |

---

## Tests to Add

```python
# tests/test_web_tools.py
async def test_web_search_reuses_client() -> None:
    """Two calls to the same WebSearchTool instance use the same AsyncClient."""
    tool = WebSearchTool(config=...)
    first_client_id = id(tool._client)
    await tool.execute(query="python asyncio")
    assert id(tool._client) == first_client_id   # same object, not recreated

async def test_web_search_client_closed_on_close() -> None:
    """close() calls aclose() on the underlying client."""
    tool = WebSearchTool(config=...)
    await tool.close()
    assert tool._client.is_closed
```

---

## Session Prompt

```
Read `docs/perf/B4-http-client-pooling.md` first — it contains the full implementation plan,
lifecycle management details, and tests to add.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W
Commit message: "perf(web): reuse httpx.AsyncClient across tool calls"

Implement the changes described in the plan, then run `ruff check .` and `pytest`, and push.
```
