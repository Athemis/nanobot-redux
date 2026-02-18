"""
Provider Registry — single source of truth for LLM provider metadata.

Adding a new provider:
  1. Add a ProviderSpec to PROVIDERS below.
  2. Add a field to ProvidersConfig in config/schema.py.
  Done. Config matching, status display all derive from here.

Order matters — it controls match priority and fallback. Gateways first.
Every entry writes out all fields so you can copy-paste as a template.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderSpec:
    """One LLM provider's metadata. See PROVIDERS below for real examples."""

    # identity
    name: str                       # config field name, e.g. "dashscope"
    keywords: tuple[str, ...]       # model-name keywords for matching (lowercase)
    env_key: str                    # primary env var name, e.g. "DASHSCOPE_API_KEY"
    display_name: str = ""          # shown in `nanobot status`

    # model name handling: prefix that may appear in user-specified model names
    # and should be stripped before forwarding to the OpenAI-compatible API.
    # e.g. "deepseek" means "deepseek/deepseek-chat" → "deepseek-chat"
    model_prefix: str = ""

    # gateway / local detection
    is_gateway: bool = False                 # routes any model (OpenRouter, AiHubMix)
    is_local: bool = False                   # local deployment (vLLM, Ollama)
    detect_by_key_prefix: str = ""           # match api_key prefix, e.g. "sk-or-"
    detect_by_base_keyword: str = ""         # match substring in api_base URL
    default_api_base: str = ""               # fallback base URL

    # gateway behavior
    strip_model_prefix: bool = False         # strip "provider/" before forwarding

    # per-model param overrides, e.g. (("kimi-k2.5", {"temperature": 1.0}),)
    model_overrides: tuple[tuple[str, dict[str, Any]], ...] = ()

    # OAuth-based providers (e.g., OpenAI Codex) don't use API keys
    is_oauth: bool = False                   # if True, uses OAuth flow instead of API key

    @property
    def label(self) -> str:
        return self.display_name or self.name.title()


# ---------------------------------------------------------------------------
# PROVIDERS — the registry. Order = priority. Copy any entry as template.
# ---------------------------------------------------------------------------

PROVIDERS: tuple[ProviderSpec, ...] = (

    # === Gateways (detected by api_key / api_base, not model name) =========
    # Gateways can route any model, so they win in fallback.

    # OpenRouter: global gateway, keys start with "sk-or-"
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        model_prefix="openrouter",           # strip "openrouter/" prefix if present
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="sk-or-",
        detect_by_base_keyword="openrouter",
        default_api_base="https://openrouter.ai/api/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # AiHubMix: global gateway, OpenAI-compatible interface.
    # model_prefix="" is intentionally empty — AiHubMix doesn't use a routing prefix.
    # strip_model_prefix=True removes any slash-prefixed namespace from the incoming
    # model string via model.split("/")[-1] in OpenAIProvider._resolve_model(), so
    # "anthropic/claude-3" becomes "claude-3". The two fields are independent:
    # model_prefix drives prefix-strip-by-name; strip_model_prefix drives take-last-segment.
    ProviderSpec(
        name="aihubmix",
        keywords=("aihubmix",),
        env_key="OPENAI_API_KEY",           # OpenAI-compatible
        display_name="AiHubMix",
        model_prefix="",                    # intentionally empty; strip_model_prefix handles namespace removal
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="aihubmix",
        default_api_base="https://aihubmix.com/v1",
        strip_model_prefix=True,            # "anthropic/claude-3" → "claude-3" (last segment)
        model_overrides=(),
    ),

    # === Standard providers (matched by model-name keywords) ===============

    # OpenAI: gpt-* models via api.openai.com
    ProviderSpec(
        name="openai",
        keywords=("openai", "gpt"),
        env_key="OPENAI_API_KEY",
        display_name="OpenAI",
        model_prefix="",
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.openai.com/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # OpenAI Codex: uses OAuth, not API key. Has its own provider class.
    ProviderSpec(
        name="openai_codex",
        keywords=("openai-codex", "codex"),
        env_key="",                         # OAuth-based, no API key
        display_name="OpenAI Codex",
        model_prefix="",
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="codex",
        default_api_base="https://chatgpt.com/backend-api",
        strip_model_prefix=False,
        model_overrides=(),
        is_oauth=True,
    ),

    # DeepSeek: OpenAI-compatible API.
    ProviderSpec(
        name="deepseek",
        keywords=("deepseek",),
        env_key="DEEPSEEK_API_KEY",
        display_name="DeepSeek",
        model_prefix="deepseek",            # strip "deepseek/" if present
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.deepseek.com/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # Zhipu: GLM models, OpenAI-compatible API.
    ProviderSpec(
        name="zhipu",
        keywords=("zhipu", "glm", "zai"),
        env_key="ZAI_API_KEY",
        display_name="Zhipu AI",
        model_prefix="zai",                 # strip "zai/" if present
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://open.bigmodel.cn/api/paas/v4/",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # DashScope: Qwen models, OpenAI-compatible API.
    ProviderSpec(
        name="dashscope",
        keywords=("qwen", "dashscope"),
        env_key="DASHSCOPE_API_KEY",
        display_name="DashScope",
        model_prefix="dashscope",           # strip "dashscope/" if present
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # Moonshot: Kimi models, OpenAI-compatible API.
    # Kimi K2.5 API enforces temperature >= 1.0.
    ProviderSpec(
        name="moonshot",
        keywords=("moonshot", "kimi"),
        env_key="MOONSHOT_API_KEY",
        display_name="Moonshot",
        model_prefix="moonshot",            # strip "moonshot/" if present
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.moonshot.ai/v1",   # intl; use api.moonshot.cn for China
        strip_model_prefix=False,
        model_overrides=(
            ("kimi-k2.5", {"temperature": 1.0}),
        ),
    ),

    # MiniMax: OpenAI-compatible API at api.minimax.io/v1.
    ProviderSpec(
        name="minimax",
        keywords=("minimax",),
        env_key="MINIMAX_API_KEY",
        display_name="MiniMax",
        model_prefix="minimax",             # strip "minimax/" if present
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.minimax.io/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # === Local deployment (matched by config key, NOT by api_base) =========

    # vLLM / any OpenAI-compatible local server.
    ProviderSpec(
        name="vllm",
        keywords=("vllm",),
        env_key="HOSTED_VLLM_API_KEY",
        display_name="vLLM/Local",
        model_prefix="hosted_vllm",         # strip "hosted_vllm/" if present
        is_gateway=False,
        is_local=True,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",                # user must provide in config
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # === Auxiliary (not a primary LLM provider) ============================

    # Groq: mainly used for Whisper voice transcription, also usable for LLM.
    ProviderSpec(
        name="groq",
        keywords=("groq",),
        env_key="GROQ_API_KEY",
        display_name="Groq",
        model_prefix="groq",                # strip "groq/" if present
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.groq.com/openai/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),
)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def find_by_model(model: str) -> ProviderSpec | None:
    """Match a standard provider by model-name keyword (case-insensitive).
    Skips gateways/local — those are matched by api_key/api_base instead."""
    model_lower = model.lower()
    for spec in PROVIDERS:
        if spec.is_gateway or spec.is_local:
            continue
        if any(kw in model_lower for kw in spec.keywords):
            return spec
    return None


def find_gateway(
    provider_name: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
) -> ProviderSpec | None:
    """Detect gateway/local provider.

    Priority:
      1. provider_name — if it maps to a gateway/local spec, use it directly.
      2. api_key prefix — e.g. "sk-or-" → OpenRouter.
      3. api_base keyword — e.g. "aihubmix" in URL → AiHubMix.
    """
    # 1. Direct match by config key
    if provider_name:
        spec = find_by_name(provider_name)
        if spec and (spec.is_gateway or spec.is_local):
            return spec

    # 2. Auto-detect by api_key prefix / api_base keyword
    for spec in PROVIDERS:
        if spec.detect_by_key_prefix and api_key and api_key.startswith(spec.detect_by_key_prefix):
            return spec
        if spec.detect_by_base_keyword and api_base and spec.detect_by_base_keyword in api_base:
            return spec

    return None


def find_by_name(name: str) -> ProviderSpec | None:
    """Find a provider spec by config field name, e.g. "dashscope"."""
    for spec in PROVIDERS:
        if spec.name == name:
            return spec
    return None
