# OpenAI Default Prompt Caching Design

## Goal

Enable prompt caching by default only for the real OpenAI provider, while keeping all other
OpenAI-compatible providers default-off unless explicitly configured.

## Approved Decisions

- Add a provider-level default flag in the provider registry.
- Keep user configuration as override authority.
- Use tri-state config for `promptCachingEnabled` so "unset" can inherit provider defaults.

## Architecture

1. Add `default_prompt_caching_enabled: bool = False` to `ProviderSpec`.
2. Set `default_prompt_caching_enabled=True` for `openai` in `PROVIDERS`.
3. Change `ProviderConfig.prompt_caching_enabled` from `bool` to `bool | None` with default `None`.
4. In `_make_provider`, compute effective prompt-caching enablement:
   - if config is explicitly `True` or `False`, use it
   - if config is `None`, inherit from `ProviderSpec.default_prompt_caching_enabled`

## Data Flow

- `Config` resolves provider and model as before.
- `_make_provider` resolves provider spec and computes effective prompt-caching enablement.
- `OpenAIProvider` receives final boolean and emits prompt-caching fields only when enabled.

## Error Handling and Safety

- No behavior change for Codex provider.
- No behavior change for non-OpenAI providers unless user explicitly enables prompt caching.
- Explicit user config (`true` or `false`) always wins over registry defaults.

## Testing Plan

- Config parsing: verify `promptCachingEnabled` can be `true/false` and defaults to `None` when omitted.
- Provider wiring: verify OpenAI defaults to `True` when omitted and non-OpenAI defaults remain `False`.
- Override behavior: verify explicit `False` disables OpenAI default and explicit `True` enables for others.

## Rollout

- Keep current branch and PR.
- Add one focused feature commit for registry default + tri-state resolution + tests.
- Update `docs/redux-changes.md` entry to mention registry-backed default-open for OpenAI.
