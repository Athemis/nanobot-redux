"""Direct OpenAI-compatible provider — replaces LiteLLM for multi-provider support."""

from __future__ import annotations

from typing import Any

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
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self._provider_name = provider_name
        self._gateway = find_gateway(provider_name, api_key, api_base)

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
                model = model[len(prefix) + 1:]
            return model

        spec = find_by_model(model) or find_by_name(self._provider_name or "")
        if spec and spec.model_prefix:
            pfx = f"{spec.model_prefix}/"
            if model.startswith(pfx):
                model = model[len(pfx):]
        return model

    def _apply_model_overrides(self, model: str, kwargs: dict[str, Any]) -> None:
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
    ) -> LLMResponse:
        model = self._resolve_model(model or self.default_model)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max(1, max_tokens),
            "temperature": temperature,
        }
        self._apply_model_overrides(model, kwargs)
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")
        try:
            return self._parse(await self._client.chat.completions.create(**kwargs))
        except Exception as e:
            return LLMResponse(content=f"Error: {e}", finish_reason="error")

    def _parse(self, response: Any) -> LLMResponse:
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
