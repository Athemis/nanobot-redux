<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    perf(loop): run tool calls concurrently with asyncio.gather
  Labels: performance, enhancement
-->

## Problem / motivation

The agent loop executes all tool calls returned by a single LLM response sequentially
(`nanobot/agent/loop.py:232`):

```python
for tool_call in response.tool_calls:
    result = await self.tools.execute(tool_call.name, tool_call.arguments)
```

When the model returns multiple independent calls — e.g. `web_search` + `read_file` + another
`web_search` — total latency is the **sum** of each call, not the maximum. Three 10-second web
fetches take 30 s instead of ~10 s.

## Proposed solution

Replace the sequential `for` loop with `asyncio.gather`, preserving result order to satisfy
OpenAI API semantics (each `tool` message must reference its `tool_call_id` in the original
order):

```python
async def _run_one(tc):
    tools_used.append(tc.name)
    logger.info(f"Tool call: {tc.name}(...)")
    return tc, await self.tools.execute(tc.name, tc.arguments)

pairs = await asyncio.gather(*[_run_one(tc) for tc in response.tool_calls])
for tc, result in pairs:
    messages = self.context.add_tool_result(messages, tc.id, tc.name, result)
```

Error behaviour is unchanged: `execute()` returns `"Error: ..."` strings and never raises.

Full implementation plan: [`docs/perf/B1-parallel-tool-execution.md`](../B1-parallel-tool-execution.md)

## Alternatives considered

- **Sequential with `parallel_safe` metadata per tool** — safer for tools with shared side
  effects (e.g. two writes to the same file), but adds per-tool annotation overhead and the
  common case is already safe.
- **No change** — acceptable only if the model rarely returns more than one tool call per
  response; in practice multi-call responses are common with web-heavy workflows.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
