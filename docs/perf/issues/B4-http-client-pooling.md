<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    perf(web): reuse httpx.AsyncClient across tool calls
  Labels: performance, enhancement
-->

## Problem / motivation

`WebSearchTool` and `WebFetchTool` in `nanobot/agent/tools/web.py` create a new
`httpx.AsyncClient` on every call:

```python
async with httpx.AsyncClient(transport=self._transport) as client:
    r = await client.get(...)
```

`httpx.AsyncClient` maintains a connection pool internally. Creating a new instance per call
discards the pool, forcing a fresh TCP handshake and TLS negotiation (50–300 ms) on every
web search or fetch.

For web-heavy agent turns (multiple searches + fetches), this overhead is cumulative and
measurable.

## Proposed solution

Create the client once in `__init__` and reuse it across calls:

```python
class WebSearchTool(Tool):
    def __init__(self, config: ...) -> None:
        ...
        self._client = httpx.AsyncClient(transport=self._transport, timeout=10.0)

    async def close(self) -> None:
        await self._client.aclose()
```

Register `close()` with the `AgentLoop`'s `AsyncExitStack` (already used for MCP) for clean
shutdown.

Full implementation plan: [`docs/perf/B4-http-client-pooling.md`](../B4-http-client-pooling.md)

## Alternatives considered

- **Module-level shared client** — slightly simpler lifecycle but harder to test and couples
  all web tool instances to a single global object.
- **Keep per-request clients, tune keep-alive** — does not help since the client is closed
  immediately after each request; the pool is never reused.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
