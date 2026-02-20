<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    feat(providers): add optional prompt caching for Anthropic
  Labels: performance, enhancement, cost-reduction
-->

## Problem / motivation

For providers that support prompt caching (Anthropic, OpenAI), the system prompt and
conversation history are re-sent as input tokens on every LLM call, even when they are
identical to the previous call.

**Cost example (Anthropic Claude):**

| Scenario | Rate | Cost for 2,000-token system prompt × 20 calls |
|----------|------|-----------------------------------------------|
| No caching | $3.00 / 1M tokens | $0.120 |
| Cache write | $3.75 / 1M (first write only) | $0.0075 |
| Cache read | $0.30 / 1M | $0.006 × 19 = $0.114 → **total ~$0.121 first session, $0.006 thereafter** |

In long-running sessions the saving is up to **20×** on prompt tokens.

**Latency:** Cached prefixes skip GPU reprocessing; TTFT (time to first token) drops by up to
85% on cache hits.

## Proposed solution

Add an opt-in `use_prompt_cache: bool = False` config field. When enabled, wrap the system
message content in Anthropic's array format with `cache_control`:

```python
# nanobot/providers/openai_provider.py
def _apply_cache_control(self, messages):
    if not self.config.use_prompt_cache:
        return messages
    result = []
    for msg in messages:
        if msg["role"] == "system":
            msg = {**msg, "content": [
                {"type": "text", "text": msg["content"],
                 "cache_control": {"type": "ephemeral"}}
            ]}
        result.append(msg)
    return result
```

OpenAI caches automatically for prompts > 1,024 tokens — no code change needed there.

**Constraint:** `datetime.now()` in the system prompt changes every minute and breaks cache
coherency. Consider moving the current time to the user message, or accept ~1-minute cache
TTL misses.

Full implementation plan: [`docs/perf/P1-llm-prompt-caching.md`](../P1-llm-prompt-caching.md)

## Alternatives considered

- **Always-on caching** — opt-in is safer; providers without cache support may reject unknown
  message fields or behave unexpectedly.
- **Cache entire message history** — too aggressive; history changes on every turn. Only the
  stable system prompt prefix benefits consistently.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
