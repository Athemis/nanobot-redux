# OpenAI Default Prompt Caching Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make prompt caching default-on only for the OpenAI provider, while preserving explicit user overrides and default-off behavior for other OpenAI-compatible providers.

**Architecture:** Add provider-level default metadata in the registry, switch config to tri-state for prompt caching enablement, and resolve effective value in `_make_provider` with user override precedence. Keep `OpenAIProvider` behavior unchanged except for receiving a resolved boolean.

**Tech Stack:** Python 3.14, dataclasses, Pydantic, pytest, ruff

---

### Task 1: Add failing tests for default-on OpenAI and default-off others

**Files:**
- Modify: `tests/test_onboard_openrouter_defaults.py`
- Test: `tests/test_onboard_openrouter_defaults.py`

**Step 1: Write the failing tests**

```python
def test_make_provider_defaults_openai_prompt_caching_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("nanobot.providers.openai_provider.OpenAIProvider", DummyProvider)

    config = Config()
    config.agents.defaults.model = "openai/gpt-4o"
    config.providers.openai.api_key = "sk-test"

    _make_provider(config)

    assert captured["prompt_caching_enabled"] is True


def test_make_provider_defaults_openrouter_prompt_caching_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DummyProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("nanobot.providers.openai_provider.OpenAIProvider", DummyProvider)

    config = Config()
    config.agents.defaults.model = "openrouter/anthropic/claude-opus-4-5"
    config.providers.openrouter.api_key = "sk-or-test"

    _make_provider(config)

    assert captured["prompt_caching_enabled"] is False
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest --no-cov -q tests/test_onboard_openrouter_defaults.py -k "defaults_openai_prompt_caching or defaults_openrouter_prompt_caching"`

Expected: FAIL because current fallback defaults to `False` for all providers.

**Step 3: Commit placeholder**

Do not commit yet; continue after implementation and passing tests.

### Task 2: Add failing test for tri-state config default

**Files:**
- Modify: `tests/test_config_loader_conversion.py`
- Test: `tests/test_config_loader_conversion.py`

**Step 1: Write the failing test**

```python
def test_provider_prompt_caching_enabled_defaults_to_none() -> None:
    config = Config()
    assert config.providers.openai.prompt_caching_enabled is None
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest --no-cov -q tests/test_config_loader_conversion.py -k "prompt_caching_enabled_defaults_to_none"`

Expected: FAIL because current default is `False`.

### Task 3: Implement registry default + tri-state resolution

**Files:**
- Modify: `nanobot/providers/registry.py`
- Modify: `nanobot/config/schema.py`
- Modify: `nanobot/cli/commands.py`

**Step 1: Minimal registry change**

Add to `ProviderSpec`:

```python
default_prompt_caching_enabled: bool = False
```

Set in OpenAI spec:

```python
default_prompt_caching_enabled=True,
```

**Step 2: Minimal schema change**

Change field in `ProviderConfig`:

```python
prompt_caching_enabled: bool | None = None
```

**Step 3: Minimal wiring change**

In `_make_provider`, compute effective value:

```python
prompt_caching_enabled = getattr(p, "prompt_caching_enabled", None) if p else None
effective_prompt_caching_enabled = (
    prompt_caching_enabled
    if prompt_caching_enabled is not None
    else bool(spec.default_prompt_caching_enabled) if spec else False
)
```

Pass `effective_prompt_caching_enabled` to `OpenAIProvider`.

### Task 4: Verify tests pass and add override test

**Files:**
- Modify: `tests/test_onboard_openrouter_defaults.py`
- Test: `tests/test_onboard_openrouter_defaults.py`

**Step 1: Add explicit override test**

```python
def test_make_provider_explicit_openai_prompt_caching_false_overrides_default(...):
    ...
    config.providers.openai.prompt_caching_enabled = False
    _make_provider(config)
    assert captured["prompt_caching_enabled"] is False
```

**Step 2: Run focused test files**

Run: `source .venv/bin/activate && pytest --no-cov -q tests/test_onboard_openrouter_defaults.py tests/test_config_loader_conversion.py tests/test_generation_params.py`

Expected: PASS.

### Task 5: Update docs and run full verification

**Files:**
- Modify: `docs/redux-changes.md`

**Step 1: Update redux changes entry**

Mention OpenAI-specific default-on behavior via provider registry.

**Step 2: Run full verification**

Run:
- `source .venv/bin/activate && pytest -q`
- `source .venv/bin/activate && ruff check .`

Expected: both pass.

**Step 3: Commit with thematic grouping**

```bash
git add nanobot/providers/registry.py nanobot/config/schema.py nanobot/cli/commands.py tests/test_onboard_openrouter_defaults.py tests/test_config_loader_conversion.py tests/test_generation_params.py
git commit -S -m "feat(openai): default prompt caching to enabled for OpenAI provider"

git add docs/redux-changes.md docs/plans/2026-02-19-openai-default-prompt-caching-design.md docs/plans/2026-02-19-openai-default-prompt-caching-implementation.md
git commit -S -m "docs(redux): document OpenAI default prompt caching policy"
```
