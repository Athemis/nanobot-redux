# P1 — LLM Prompt Caching (Provider-Side)

**Priority:** P2 | **Effort:** Low | **Risk:** Low (additive only)
**Status:** open

---

## Problem

For providers that support prompt caching (Anthropic, OpenAI), the system prompt and long
conversation history are sent as input tokens on every LLM call, even when they have not changed.
At 50+ messages in a session, this is thousands of tokens repeated unnecessarily.

**Cost example (Anthropic Claude):**
- Normal input: $3 / 1M tokens
- Cache write: $3.75 / 1M tokens (25% premium on first write)
- Cache read: $0.30 / 1M tokens (90% discount on hits)

A 2,000-token system prompt repeated 20 times across a session costs $0.12 without caching,
$0.006 with caching — a 20× reduction.

**Latency:** Cached prefixes skip reprocessing, reducing TTFT (time to first token) by up to
85% on cache hits.

---

## How It Works

### Anthropic

Add `"cache_control": {"type": "ephemeral"}` to the last block of the system message:

```python
{
    "role": "system",
    "content": [
        {"type": "text", "text": full_system_prompt, "cache_control": {"type": "ephemeral"}}
    ]
}
```

Mark the last `N` turns of conversation history similarly to cache the prefix up to that point.

### OpenAI

OpenAI caches automatically for prompts > 1,024 tokens sharing a common prefix; no explicit
headers needed. The `cached_tokens` field in the usage response shows how many tokens were served
from cache.

---

## Implementation Plan

### Config addition

```python
# nanobot/config/schema.py — in AgentConfig or ProviderConfig
use_prompt_cache: bool = False
```

### Provider-level change (Anthropic)

In `nanobot/providers/openai_provider.py` (or a new `anthropic_provider.py` if one is added):

```python
def _apply_cache_control(self, messages: list[dict]) -> list[dict]:
    """Add cache_control to system message and last few history turns."""
    if not self.config.use_prompt_cache:
        return messages
    result = []
    for i, msg in enumerate(messages):
        if msg["role"] == "system":
            # Wrap content in array format with cache_control
            msg = {**msg, "content": [
                {"type": "text", "text": msg["content"], "cache_control": {"type": "ephemeral"}}
            ]}
        result.append(msg)
    return result
```

### For OpenAI

No code change needed — just verify `cached_tokens` appears in usage when prefixes are long
enough (> 1,024 tokens). Optionally log it for observability.

---

## Files and Line Numbers

| File | Lines | Content |
|------|-------|---------|
| `nanobot/config/schema.py` | varies | Add `use_prompt_cache: bool = False` |
| `nanobot/providers/openai_provider.py` | `chat()` method | Apply cache_control when enabled |

---

## Dependencies and Constraints

- Anthropic cache_control requires the Anthropic API directly or an OpenAI-compatible proxy that
  passes it through. Most OpenRouter routes do not forward custom message fields.
- Cache TTL: Anthropic ephemeral cache = 5 minutes. Long idle sessions will miss cache.
- The system prompt must be deterministic (same content on every call) for caching to work.
  The `datetime.now()` in `_get_identity()` changes every minute — consider moving the time to
  the user message or accept cache misses every minute.

---

## Session Prompt

```
Read `docs/perf/P1-llm-prompt-caching.md` first — it contains the full implementation plan,
provider constraints, and the datetime.now() caveat.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W
Commit message: "feat(providers): add optional prompt caching for Anthropic"

Implement the changes described in the plan, then run `ruff check .` and `pytest`, and push.
```
