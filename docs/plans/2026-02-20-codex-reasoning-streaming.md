# Codex Reasoning Streaming Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface Codex reasoning in `LLMResponse.reasoning_content` and stream reasoning progress through existing callbacks without breaking Matrix typing fallback behavior.

**Architecture:** Extend the Codex SSE consumer to aggregate reasoning deltas and optionally emit them via a callback, then thread that callback through `OpenAICodexProvider.chat(...)` from the agent loop. Preserve current Matrix typing keepalive as the baseline so non-reasoning models behave exactly as before, with reasoning acting only as an additional activity signal.

**Tech Stack:** Python 3.14, httpx SSE parsing, pytest, unittest.mock, nio-based Matrix channel.

---

## Task 1: Add failing Codex reasoning parser tests

**Files:**
- Modify: `tests/test_generation_params.py`
- Test: `tests/test_generation_params.py`

**Step 1: Write the failing test for reasoning aggregation**

```python
@pytest.mark.asyncio
async def test_codex_consume_sse_collects_reasoning_content(monkeypatch) -> None:
    async def _fake_iter_sse(_response):
        yield {"type": "response.reasoning_text.delta", "delta": "Thinking "}
        yield {"type": "response.reasoning_text.delta", "delta": "step-by-step"}
        yield {"type": "response.completed", "response": {"status": "completed"}}

    monkeypatch.setattr("nanobot.providers.openai_codex_provider._iter_sse", _fake_iter_sse)

    content, tool_calls, finish_reason, reasoning = await codex_provider._consume_sse(object())
    assert content == ""
    assert tool_calls == []
    assert finish_reason == "stop"
    assert reasoning == "Thinking step-by-step"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_generation_params.py::test_codex_consume_sse_collects_reasoning_content -v`
Expected: FAIL due to `_consume_sse` return shape / missing reasoning handling.

**Step 3: Add failing chat-level propagation test**

```python
@pytest.mark.asyncio
async def test_codex_chat_sets_reasoning_content(monkeypatch) -> None:
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )

    async def _fake_request_codex(url, headers, body, verify):
        return "ok", [], "stop", "reasoning summary"

    monkeypatch.setattr("nanobot.providers.openai_codex_provider._request_codex", _fake_request_codex)

    provider = OpenAICodexProvider(default_model="openai-codex/gpt-5.1-codex")
    result = await provider.chat(messages=[{"role": "user", "content": "hello"}])
    assert result.reasoning_content == "reasoning summary"
```

**Step 4: Run both tests to verify they fail first**

Run: `pytest tests/test_generation_params.py -k "codex_consume_sse_collects_reasoning_content or codex_chat_sets_reasoning_content" -v`
Expected: FAIL.

**Step 5: Commit**

```bash
git add tests/test_generation_params.py
git commit -m "test: add codex reasoning streaming expectations"
```

## Task 2: Implement Codex reasoning aggregation and response propagation

**Files:**
- Modify: `nanobot/providers/openai_codex_provider.py`
- Test: `tests/test_generation_params.py`

**Step 1: Implement minimal parser changes**

```python
reasoning_content = ""

elif event_type == "response.reasoning_text.delta":
    reasoning_content += event.get("delta") or ""

return content, tool_calls, finish_reason, (reasoning_content or None)
```

Also update `_request_codex(...)` and `chat(...)` tuple handling to include reasoning.

**Step 2: Run targeted tests**

Run: `pytest tests/test_generation_params.py -k "codex_consume_sse_collects_reasoning_content or codex_chat_sets_reasoning_content" -v`
Expected: PASS.

**Step 3: Run broader Codex regression tests**

Run: `pytest tests/test_generation_params.py -k "codex" -v`
Expected: PASS, no regressions in token/SSL/error handling tests.

**Step 4: Commit**

```bash
git add nanobot/providers/openai_codex_provider.py tests/test_generation_params.py
git commit -m "feat(codex): propagate reasoning content from SSE responses"
```

## Task 3: Stream reasoning through agent progress callback

**Files:**
- Modify: `nanobot/providers/base.py`
- Modify: `nanobot/providers/openai_provider.py`
- Modify: `nanobot/providers/openai_codex_provider.py`
- Modify: `nanobot/agent/loop.py`
- Modify: `tests/test_on_progress.py`

**Step 1: Add provider callback contract with failing test**

Add/extend tests in `tests/test_on_progress.py` to verify that when provider emits reasoning deltas,
`on_progress` receives them before tool completion.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_on_progress.py -k "reasoning" -v`
Expected: FAIL (no streaming path yet).

**Step 3: Implement minimal callback plumbing**

```python
# base.py
async def chat(..., on_reasoning_delta: Callable[[str], Awaitable[None]] | None = None) -> LLMResponse:
    ...

# loop.py
response = await self.provider.chat(..., on_reasoning_delta=on_progress)
```

In `OpenAIProvider`, accept the new optional arg but ignore it.
In `OpenAICodexProvider`, forward callback into `_request_codex`/`_consume_sse` and invoke on deltas.

**Step 4: Run tests**

Run: `pytest tests/test_on_progress.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add nanobot/providers/base.py nanobot/providers/openai_provider.py nanobot/providers/openai_codex_provider.py nanobot/agent/loop.py tests/test_on_progress.py
git commit -m "feat(agent): stream codex reasoning via progress callbacks"
```

## Task 4: Preserve and verify Matrix typing fallback behavior

**Files:**
- Modify: `tests/test_matrix_channel.py`
- Modify (if needed): `nanobot/channels/matrix.py`

**Step 1: Add failing fallback-focused tests**

Add tests that assert typing keepalive behavior remains correct when no reasoning/progress deltas are
available (start typing on processing, clear typing on final send).

**Step 2: Run test to verify behavior baseline**

Run: `pytest tests/test_matrix_channel.py -k "typing" -v`
Expected: Either PASS baseline or FAIL if code changes introduced regression.

**Step 3: Minimal fix only if needed**

If tests fail, adjust MatrixChannel lifecycle so fallback keepalive remains independent of reasoning.

**Step 4: Re-run Matrix and integration-adjacent tests**

Run: `pytest tests/test_matrix_channel.py tests/test_on_progress.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add nanobot/channels/matrix.py tests/test_matrix_channel.py
git commit -m "test(matrix): guarantee typing fallback without reasoning"
```

## Task 5: Final verification and fork docs updates

**Files:**
- Modify: `docs/redux-changes.md`
- Modify: `README.md`

**Step 1: Update fork docs for user-visible behavior**

- Add a `docs/redux-changes.md` entry for Codex reasoning streaming + typing fallback guarantee.
- Update README "What This Fork Adds" with user-visible progress/typing improvement bullet.

**Step 2: Run lint and focused tests**

Run: `ruff check nanobot/providers nanobot/agent nanobot/channels tests`
Expected: PASS.

Run: `pytest tests/test_generation_params.py tests/test_on_progress.py tests/test_matrix_channel.py -v`
Expected: PASS.

**Step 3: Run full test suite if practical**

Run: `pytest`
Expected: PASS.

**Step 4: Commit**

```bash
git add docs/redux-changes.md README.md
git commit -m "docs: record codex reasoning streaming and matrix typing fallback"
```
