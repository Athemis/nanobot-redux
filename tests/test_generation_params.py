from types import SimpleNamespace

import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.agent.subagent import SubagentManager
from nanobot.bus.queue import MessageBus
from nanobot.config.schema import AgentDefaults
from nanobot.providers import openai_codex_provider as codex_provider
from nanobot.providers.base import LLMProvider, LLMResponse
from nanobot.providers.openai_codex_provider import OpenAICodexProvider
from nanobot.providers.openai_provider import OpenAIProvider, _hash_prompt_cache_key
from nanobot.session.manager import Session


class _RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__(api_key=None, api_base=None)
        self.calls: list[dict[str, object]] = []

    async def chat(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt_cache_key: str | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "prompt_cache_key": prompt_cache_key,
            }
        )
        return LLMResponse(content="ok")

    def get_default_model(self) -> str:
        return "test-model"


class _InMemorySessions:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, key: str) -> Session:
        if key not in self._sessions:
            self._sessions[key] = Session(key=key)
        return self._sessions[key]

    def save(self, session: Session) -> None:
        self._sessions[session.key] = session


@pytest.mark.asyncio
async def test_agent_loop_forwards_generation_parameters(tmp_path) -> None:
    provider = _RecordingProvider()
    loop = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=tmp_path,
        model="test-model",
        max_tokens=1234,
        temperature=0.25,
        session_manager=_InMemorySessions(),
    )

    response = await loop.process_direct("hello")

    assert response == "ok"
    assert provider.calls
    call = provider.calls[0]
    assert call["max_tokens"] == 1234
    assert call["temperature"] == 0.25
    assert call["prompt_cache_key"] == "cli:direct"


@pytest.mark.asyncio
async def test_subagent_forwards_generation_parameters(tmp_path) -> None:
    provider = _RecordingProvider()
    manager = SubagentManager(
        provider=provider,
        workspace=tmp_path,
        bus=MessageBus(),
        model="test-model",
        max_tokens=2222,
        temperature=0.15,
    )

    await manager._run_subagent(
        task_id="task1234",
        task="say hello",
        label="hello",
        origin={"channel": "cli", "chat_id": "direct"},
    )

    assert provider.calls
    call = provider.calls[0]
    assert call["max_tokens"] == 2222
    assert call["temperature"] == 0.15
    assert call["prompt_cache_key"] == "subagent:task1234"


@pytest.mark.asyncio
async def test_openai_provider_chat_uses_passed_generation_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_create(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        msg = SimpleNamespace(content="ok", tool_calls=None, reasoning_content=None)
        choice = SimpleNamespace(message=msg, finish_reason="stop")
        return SimpleNamespace(choices=[choice], usage=None)

    monkeypatch.setattr(
        "nanobot.providers.openai_provider.AsyncOpenAI",
        lambda **_: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
        ),
    )

    provider = OpenAIProvider(default_model="gpt-4o")
    result = await provider.chat(
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=987,
        temperature=0.42,
    )

    assert result.content == "ok"
    assert captured["max_tokens"] == 987
    assert captured["temperature"] == 0.42


@pytest.mark.asyncio
async def test_openai_provider_adds_prompt_cache_key_when_stable_key_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_create(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        msg = SimpleNamespace(content="ok", tool_calls=None, reasoning_content=None)
        choice = SimpleNamespace(message=msg, finish_reason="stop")
        return SimpleNamespace(choices=[choice], usage=None)

    monkeypatch.setattr(
        "nanobot.providers.openai_provider.AsyncOpenAI",
        lambda **_: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
        ),
    )

    provider = OpenAIProvider(
        default_model="gpt-4o",
        prompt_caching_enabled=True,
    )
    await provider.chat(
        messages=[{"role": "user", "content": "hello"}],
        prompt_cache_key="session-123",
    )

    assert captured["prompt_cache_key"] == _hash_prompt_cache_key("session-123", None)


@pytest.mark.asyncio
async def test_openai_provider_omits_prompt_cache_fields_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_create(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        msg = SimpleNamespace(content="ok", tool_calls=None, reasoning_content=None)
        choice = SimpleNamespace(message=msg, finish_reason="stop")
        return SimpleNamespace(choices=[choice], usage=None)

    monkeypatch.setattr(
        "nanobot.providers.openai_provider.AsyncOpenAI",
        lambda **_: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
        ),
    )

    provider = OpenAIProvider(default_model="gpt-4o", prompt_caching_enabled=False)
    await provider.chat(messages=[{"role": "user", "content": "hello"}])

    assert "prompt_cache_key" not in captured
    assert "prompt_cache_retention" not in captured


@pytest.mark.asyncio
async def test_openai_provider_omits_prompt_cache_key_when_enabled_without_stable_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_create(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        msg = SimpleNamespace(content="ok", tool_calls=None, reasoning_content=None)
        choice = SimpleNamespace(message=msg, finish_reason="stop")
        return SimpleNamespace(choices=[choice], usage=None)

    monkeypatch.setattr(
        "nanobot.providers.openai_provider.AsyncOpenAI",
        lambda **_: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
        ),
    )

    provider = OpenAIProvider(default_model="gpt-4o", prompt_caching_enabled=True)
    await provider.chat(messages=[{"role": "user", "content": "hello"}])

    assert "prompt_cache_key" not in captured
    assert "prompt_cache_retention" not in captured


@pytest.mark.asyncio
async def test_openai_provider_passes_prompt_cache_retention_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_create(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        msg = SimpleNamespace(content="ok", tool_calls=None, reasoning_content=None)
        choice = SimpleNamespace(message=msg, finish_reason="stop")
        return SimpleNamespace(choices=[choice], usage=None)

    monkeypatch.setattr(
        "nanobot.providers.openai_provider.AsyncOpenAI",
        lambda **_: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=_fake_create))
        ),
    )

    provider = OpenAIProvider(
        default_model="gpt-4o",
        prompt_caching_enabled=True,
        prompt_cache_retention="24h",
    )
    await provider.chat(
        messages=[{"role": "user", "content": "hello"}],
        prompt_cache_key="session-123",
    )

    assert captured["prompt_cache_key"] == _hash_prompt_cache_key("session-123", None)
    assert captured["prompt_cache_retention"] == "24h"


def test_agent_defaults_max_tokens_default_is_4096() -> None:
    defaults = AgentDefaults()
    assert defaults.max_tokens == 4096


@pytest.mark.asyncio
async def test_codex_chat_omits_token_limit_fields_and_ignores_temperature(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_request_codex(
        url: str, headers: dict[str, str], body: dict[str, object], verify: bool
    ):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        captured["verify"] = verify
        return "ok", [], "stop", None

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider._request_codex",
        _fake_request_codex,
    )

    provider = OpenAICodexProvider(default_model="openai-codex/gpt-5.1-codex")
    response = await provider.chat(
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=777,
        temperature=0.19,
    )

    assert response.content == "ok"
    assert captured["verify"] is True
    body = captured["body"]
    assert isinstance(body, dict)
    assert "max_tokens" not in body
    assert "max_output_tokens" not in body
    assert "temperature" not in body


@pytest.mark.asyncio
async def test_codex_chat_disables_ssl_verify_only_when_provider_configured(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_request_codex(
        url: str, headers: dict[str, str], body: dict[str, object], verify: bool
    ):
        captured["verify"] = verify
        return "ok", [], "stop", None

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider._request_codex",
        _fake_request_codex,
    )

    provider = OpenAICodexProvider(default_model="openai-codex/gpt-5.1-codex", ssl_verify=False)
    response = await provider.chat(messages=[{"role": "user", "content": "hello"}])

    assert response.content == "ok"
    assert captured["verify"] is False


@pytest.mark.asyncio
async def test_codex_chat_no_longer_auto_retries_without_ssl_verify(monkeypatch) -> None:
    calls: list[bool] = []

    async def _fake_request_codex(
        url: str, headers: dict[str, str], body: dict[str, object], verify: bool
    ):
        calls.append(verify)
        raise RuntimeError("CERTIFICATE_VERIFY_FAILED")

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider._request_codex",
        _fake_request_codex,
    )

    provider = OpenAICodexProvider(default_model="openai-codex/gpt-5.1-codex")
    response = await provider.chat(messages=[{"role": "user", "content": "hello"}])

    assert response.finish_reason == "error"
    assert calls == [True]


@pytest.mark.asyncio
async def test_codex_consume_sse_error_event_includes_message(monkeypatch) -> None:
    async def _fake_iter_sse(_response):
        yield {"type": "error", "message": "token expired"}

    monkeypatch.setattr("nanobot.providers.openai_codex_provider._iter_sse", _fake_iter_sse)

    with pytest.raises(RuntimeError, match="Codex response failed: token expired"):
        await codex_provider._consume_sse(object())


@pytest.mark.asyncio
async def test_codex_consume_sse_response_failed_uses_nested_error(monkeypatch) -> None:
    async def _fake_iter_sse(_response):
        yield {
            "type": "response.failed",
            "response": {"error": {"message": "quota exceeded"}},
        }

    monkeypatch.setattr("nanobot.providers.openai_codex_provider._iter_sse", _fake_iter_sse)

    with pytest.raises(RuntimeError, match="Codex response failed: quota exceeded"):
        await codex_provider._consume_sse(object())


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


@pytest.mark.asyncio
async def test_codex_chat_sets_reasoning_content(monkeypatch) -> None:
    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider.get_codex_token",
        lambda: SimpleNamespace(account_id="acc", access="tok"),
    )

    async def _fake_request_codex(
        url: str, headers: dict[str, str], body: dict[str, object], verify: bool
    ):
        return "ok", [], "stop", "reasoning summary"

    monkeypatch.setattr(
        "nanobot.providers.openai_codex_provider._request_codex", _fake_request_codex
    )

    provider = OpenAICodexProvider(default_model="openai-codex/gpt-5.1-codex")
    result = await provider.chat(messages=[{"role": "user", "content": "hello"}])
    assert result.content == "ok"
    assert result.finish_reason == "stop"
    assert result.reasoning_content == "reasoning summary"
