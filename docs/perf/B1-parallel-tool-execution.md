# B1 — Parallel Tool Execution

**Priority:** P1 | **Effort:** Medium | **Risk:** Medium
**Status:** open

---

## Problem

The agent loop executes all tool calls from a single LLM response sequentially:

```python
# nanobot/agent/loop.py:232–239
for tool_call in response.tool_calls:
    tools_used.append(tool_call.name)
    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
    logger.info(f"Tool call: {tool_call.name}({args_str[:200]})")
    result = await self.tools.execute(tool_call.name, tool_call.arguments)
    messages = self.context.add_tool_result(messages, tool_call.id, tool_call.name, result)
```

When the LLM returns `web_search` + `read_file` + `web_search`, total latency is the **sum** of
each tool's latency, not the maximum. Three 10-second web calls → 30 s instead of 10 s.

**Why it is this way:** Historical growth; sequential is simpler to debug and avoids side-effect
races.

---

## Desired Behaviour

Tool calls that are independent of each other (reading different resources, multiple searches)
should run concurrently. Results must be appended to `messages` in the **original order** of the
`tool_calls` list (required by OpenAI API semantics: each `tool` message must reference a
`tool_call_id` that was emitted in sequence).

---

## Implementation Plan

### Option C (recommended): `asyncio.gather` with order preservation

Replace the `for` loop at `loop.py:232` with:

```python
async def _run_one(tc):
    tools_used.append(tc.name)
    args_str = json.dumps(tc.arguments, ensure_ascii=False)
    logger.info(f"Tool call: {tc.name}({args_str[:200]})")
    return tc, await self.tools.execute(tc.name, tc.arguments)

pairs = await asyncio.gather(*[_run_one(tc) for tc in response.tool_calls])
for tc, result in pairs:
    messages = self.context.add_tool_result(messages, tc.id, tc.name, result)
```

`asyncio.gather` preserves order: `pairs[i]` corresponds to `response.tool_calls[i]`.

**Note on `tools_used.append`:** safe with `asyncio.gather` because asyncio is single-threaded;
coroutines interleave only at `await` points, and `append` is not an `await`.

### Edge Cases

| Case | Behaviour |
|------|-----------|
| One tool fails | `execute()` returns `"Error: ..."` — no exception propagation, loop continues |
| Two writes to the same file | Race condition possible — rare in practice; document the known limitation |
| Long tool + short tool | Both start at once; short tool result is collected first but inserted at its original index |

---

## Files and Line Numbers

| File | Lines | Content |
|------|-------|---------|
| `nanobot/agent/loop.py` | 232–239 | Sequential `for` loop → replace with `asyncio.gather` |
| `tests/test_agent_loop.py` | — | Add tests for parallel execution and result ordering |

---

## Tests to Add

```python
# tests/test_agent_loop.py
import asyncio
import time

async def test_tool_calls_run_in_parallel() -> None:
    """Independent tool calls execute concurrently, not sequentially."""
    start_times: list[float] = []

    async def slow_tool(**kwargs: Any) -> str:
        start_times.append(time.monotonic())
        await asyncio.sleep(0.05)
        return "ok"

    # Mock two independent tool calls; assert total elapsed ~ 0.05 s, not ~ 0.10 s
    ...

async def test_tool_results_preserve_order() -> None:
    """Results are appended to messages in tool_call order, not completion order."""
    completion_order: list[str] = []

    async def fast_tool(**kwargs: Any) -> str:
        return "fast"

    async def slow_tool(**kwargs: Any) -> str:
        await asyncio.sleep(0.02)
        return "slow"

    # slow_tool is listed first in tool_calls; its result must appear first in messages
    ...
```

---

## Session Prompt

```
Read `docs/perf/B1-parallel-tool-execution.md` first — it contains the full implementation
plan, edge cases, and test requirements.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W
Commit message: "perf(loop): run tool calls concurrently with asyncio.gather"

Implement the changes described in the plan, then run `ruff check .` and `pytest`, and push.
```
