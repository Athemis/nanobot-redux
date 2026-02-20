# P2 — Smaller Model for Memory Consolidation

**Priority:** P2 | **Effort:** Trivial | **Risk:** Low
**Status:** open

---

## Problem

Memory consolidation uses the same model as the main agent:

```python
# nanobot/agent/loop.py:462–468
response = await self.provider.chat(
    messages=[
        {"role": "system", "content": "You are a memory consolidation agent. Respond only with valid JSON."},
        {"role": "user", "content": prompt},
    ],
    model=self.model,   # same expensive model as the main agent
)
```

The consolidation task — extract facts from a conversation, return structured JSON — is simple
enough for a small model like `gpt-4o-mini` or `claude-haiku-4-5-20251001`. Using the full agent
model (e.g. `claude-opus-4-6`) costs 20–50× more for this subtask.

**Cost example:** A session that triggers consolidation 5 times over 50 messages, with a 3,000-token
consolidation prompt and `gpt-4o` as the agent model:
- Without this fix: 5 × 3,000 tokens × $5/1M = $0.075 per session
- With `gpt-4o-mini`: 5 × 3,000 tokens × $0.15/1M = $0.002 per session

---

## Implementation Plan

### Config addition

```python
# nanobot/config/schema.py — in AgentConfig
memory_model: str | None = None
# If None, falls back to the main agent model
```

### Loop change

```python
# nanobot/agent/loop.py:462
response = await self.provider.chat(
    messages=[...],
    model=self.memory_model or self.model,   # use smaller model if configured
)
```

### AgentLoop.__init__

```python
# nanobot/agent/loop.py — __init__
self.memory_model: str | None = config.agent.memory_model
```

---

## Files and Line Numbers

| File | Lines | Content |
|------|-------|---------|
| `nanobot/config/schema.py` | varies | Add `memory_model: str \| None = None` |
| `nanobot/agent/loop.py` | `__init__` | Read `config.agent.memory_model` |
| `nanobot/agent/loop.py` | 462 | Replace `model=self.model` with `model=self.memory_model or self.model` |

---

## Tests to Add

```python
# tests/test_agent_loop.py
async def test_consolidation_uses_memory_model_when_configured() -> None:
    """_consolidate_memory() passes memory_model to provider.chat() when set."""
    ...

async def test_consolidation_falls_back_to_main_model() -> None:
    """When memory_model is None, consolidation uses the main agent model."""
    ...
```

---

## Session Prompt

```
Read `docs/perf/P2-memory-model-selection.md` first — it contains the full implementation
plan, cost example, and tests to add.

Repository: /home/user/nanobot-redux
Branch: claude/analyze-performance-options-URI5W
Commit message: "feat(loop): add memory_model config option for cheaper consolidation"

Implement the changes described in the plan, then run `ruff check .` and `pytest`, and push.
```
