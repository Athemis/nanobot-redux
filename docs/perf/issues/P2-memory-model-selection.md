<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    feat(loop): add memory_model config option for cheaper consolidation
  Labels: performance, enhancement, cost-reduction
-->

## Problem / motivation

Memory consolidation (`nanobot/agent/loop.py:462`) uses the same model as the main agent:

```python
response = await self.provider.chat(
    messages=[...],
    model=self.model,   # same expensive model
)
```

The consolidation task — extract facts from a conversation, return structured JSON — is
well within the capabilities of a small model. Using the full agent model (e.g.
`claude-opus-4-6` at $15/1M output tokens) for this subtask costs 20–50× more than necessary.

**Cost example:**

| Model | Cost / 1M output tokens | 5 consolidations × 500 output tokens |
|-------|--------------------------|---------------------------------------|
| `claude-opus-4-6` | $15.00 | $0.0375 |
| `claude-haiku-4-5` | $1.25 | $0.0031 |
| `gpt-4o-mini` | $0.60 | $0.0015 |

## Proposed solution

Add a `memory_model: str | None = None` config field. When set, consolidation uses the
specified model; when `None`, it falls back to the main agent model (no behaviour change):

```python
# nanobot/config/schema.py
memory_model: str | None = None
```

```python
# nanobot/agent/loop.py — in _consolidate_memory()
model=self.memory_model or self.model,
```

Full implementation plan: [`docs/perf/P2-memory-model-selection.md`](../P2-memory-model-selection.md)

## Alternatives considered

- **Hardcode a cheaper model** — removes user choice and may conflict with provider
  configuration (e.g. users on a self-hosted endpoint that doesn't offer `gpt-4o-mini`).
- **Disable consolidation** — not acceptable; memory persistence is a core feature.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
