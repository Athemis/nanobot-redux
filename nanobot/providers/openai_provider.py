"""Direct OpenAI-compatible provider — replaces LiteLLM for multi-provider support."""

from __future__ import annotations

import hashlib
import hmac
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

import json_repair
from openai import AsyncOpenAI

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from nanobot.providers.registry import find_by_model, find_by_name, find_gateway


class OpenAIProvider(LLMProvider):
    """LLM provider using openai.AsyncOpenAI for all OpenAI-compatible endpoints.

    Replaces LiteLLMProvider. Provider routing is done via base_url rather than
    model-name prefixes, so model names are stripped of routing prefixes before
    forwarding to the API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_model: str = "gpt-4o",
        extra_headers: dict[str, str] | None = None,
        provider_name: str | None = None,
        prompt_caching_enabled: bool = False,
        prompt_cache_retention: str | None = None,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self._provider_name = provider_name
        self._gateway = find_gateway(provider_name, api_key, api_base)
        self._prompt_caching_enabled = prompt_caching_enabled
        self._prompt_cache_retention = prompt_cache_retention

        spec = self._gateway or find_by_model(default_model) or find_by_name(provider_name or "")
        effective_base = api_base or (spec.default_api_base if spec else None)

        self._client = AsyncOpenAI(
            api_key=api_key or "no-key",
            base_url=effective_base or None,
            default_headers=extra_headers or {},
        )

    def _resolve_model(self, model: str) -> str:
        """Strip provider-specific routing prefixes — base_url handles routing."""
        if self._gateway:
            if self._gateway.strip_model_prefix:
                return model.split("/")[-1]
            prefix = self._gateway.model_prefix
            if prefix and model.startswith(f"{prefix}/"):
                model = model[len(prefix) + 1 :]
            return model

        spec = find_by_model(model) or find_by_name(self._provider_name or "")
        if spec and spec.model_prefix:
            pfx = f"{spec.model_prefix}/"
            if model.startswith(pfx):
                model = model[len(pfx) :]
        return model

    def _apply_model_overrides(self, model: str, kwargs: dict[str, Any]) -> None:
        """Apply per-model parameter overrides from the registry (e.g. temperature floor for kimi-k2.5)."""
        spec = find_by_model(model)
        if spec:
            model_lower = model.lower()
            for pattern, overrides in spec.model_overrides:
                if pattern in model_lower:
                    kwargs.update(overrides)
                    return

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        prompt_cache_key: str | None = None,
        on_reasoning_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request. max_tokens is clamped to ≥1. API errors are
        caught and returned as LLMResponse(finish_reason="error") rather than raised.
        on_reasoning_delta is accepted but ignored (OpenAI does not stream reasoning text)."""
        model = self._resolve_model(model or self.default_model)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max(1, max_tokens),
            "temperature": temperature,
        }
        self._apply_model_overrides(model, kwargs)
        if self._prompt_caching_enabled and prompt_cache_key:
            kwargs["prompt_cache_key"] = _hash_prompt_cache_key(prompt_cache_key, self.api_key)
            if self._prompt_cache_retention:
                kwargs["prompt_cache_retention"] = self._prompt_cache_retention
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")
        try:
            return self._parse(await self._client.chat.completions.create(**kwargs))
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    def _parse(self, response: Any) -> LLMResponse:
        """Parse a chat completion response. Raises ValueError on empty choices.
        Tool-call arguments are run through json_repair to tolerate malformed JSON."""
        if not response.choices:
            raise ValueError(f"OpenAI response contains no choices: {response}")
        choice = response.choices[0]
        msg = choice.message
        tool_calls = [
            ToolCallRequest(
                id=tc.id,
                name=tc.function.name,
                arguments=json_repair.loads(tc.function.arguments)
                if isinstance(tc.function.arguments, str)
                else tc.function.arguments,
            )
            for tc in (msg.tool_calls or [])
        ]
        u = response.usage
        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": u.prompt_tokens,
                "completion_tokens": u.completion_tokens,
                "total_tokens": u.total_tokens,
            }
            if u
            else {},
            reasoning_content=getattr(msg, "reasoning_content", None),
        )

    def get_default_model(self) -> str:
        return self.default_model


def _hash_prompt_cache_key(prompt_cache_key: str, secret: str | None) -> str:
    """Return deterministic HMAC-SHA256 key material for OpenAI prompt caching.

    The "v1:" prefix version-tags the hash input so we can safely change hashing
    strategy later (e.g., v2 with different normalization/secret handling) without
    colliding with previously derived cache keys.
    """
    key_material = (secret or "nanobot").encode("utf-8")
    message = f"v1:{prompt_cache_key}".encode("utf-8")
    return hmac.new(key_material, message, hashlib.sha256).hexdigest()
