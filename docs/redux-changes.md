# Redux Changes

This file tracks changes that originate in this fork — not adopted from upstream, but developed here. It's a record of why decisions were made and how to verify them.

See [`docs/upstream-log.md`](upstream-log.md) for upstream adoptions.

## Changes

| Change | PR/Commit | Area | Why | Risk | Added | Verification |
| ------ | --------- | ---- | --- | ---- | ----- | ------------ |
| OpenClaw skill metadata regression tests | [9290f23](https://github.com/Athemis/nanobot-redux/commit/9290f23879df58cec39671b2cf984be23e1915fb) | Skills loader | Lock in fork behavior for `openclaw` metadata support and `nanobot` precedence when both keys exist | low | 2026-02-16 | `pytest tests/test_skills_loader.py` |
| Codex TLS verification hardening | [3d0d1eb](https://github.com/Athemis/nanobot-redux/commit/3d0d1ebdf2e711dce527b4b3ed2ddee2612734ca) | Codex Provider | Avoid silent TLS downgrade; require explicit `providers.openaiCodex.sslVerify=false` opt-in | low | 2026-02-16 | `pytest -q tests/test_config_loader_conversion.py tests/test_generation_params.py tests/test_onboard_openrouter_defaults.py` + `ruff check nanobot/config/schema.py nanobot/cli/commands.py nanobot/providers/openai_codex_provider.py` |
| Codex SSE error diagnostics | [2a77f20](https://github.com/Athemis/nanobot-redux/commit/2a77f20c2b91136ab9dabc11df063b4502dedc8d) | Codex Provider | Surface provider error details from `error`/`response.failed` payloads instead of generic failure text | low | 2026-02-16 | `pytest -q tests/test_generation_params.py` + `ruff check nanobot/providers/openai_codex_provider.py` |
| Codex OAuth token-limit compatibility | [#16](https://github.com/Athemis/nanobot-redux/pull/16), [#17](https://github.com/Athemis/nanobot-redux/issues/17) | Codex Provider | `chatgpt.com/backend-api/codex/responses` rejects unsupported token-limit parameters; align payload with OpenAI Codex OAuth request shape that omits `max_output_tokens`/`max_tokens` | low | 2026-02-17 | `pytest -q tests/test_generation_params.py -k codex` + `ruff check nanobot/providers/openai_codex_provider.py` |
| Email TLS verification hardening + plaintext SMTP block | [#6](https://github.com/Athemis/nanobot-redux/pull/6) | Email channel | Enforce explicit TLS verification by default with explicit opt-out warning (`channels.email.tlsVerify`), and refuse SMTP sends when both `smtpUseTls` and `smtpUseSsl` are disabled | medium | 2026-02-16 | `pytest -q tests/test_email_channel.py` + `ruff check nanobot/channels/email.py tests/test_email_channel.py nanobot/config/schema.py` |
| Subagent skill access in workspace-restricted mode | [#18](https://github.com/Athemis/nanobot-redux/pull/18) | Agent / Skills | Subagents couldn't read builtin skills when `restrictToWorkspace` was enabled; `ReadFileTool` gains `extra_allowed_dirs` allowlist so `BUILTIN_SKILLS_DIR` is always readable; subagent prompt updated to surface available skills | low | 2026-02-17 | `pytest -q tests/test_read_file_tool.py` + `ruff check nanobot/agent/subagent.py nanobot/agent/tools/filesystem.py` |
| Agentic prompt hardening | [#18](https://github.com/Athemis/nanobot-redux/pull/18) | Agent prompts | Skill-trigger wording, loop-continuation nudge, heartbeat prompt, spawn tool description, and workspace docs rewritten to push the agent toward direct action over passive confirmation-seeking | low | 2026-02-17 | `ruff check nanobot/agent/loop.py nanobot/agent/context.py nanobot/agent/tools/spawn.py nanobot/heartbeat/service.py` |
| CI lint enforcement | [e3128af](https://github.com/Athemis/nanobot-redux/commit/e3128af28bb7bccd455be70900152efc18379b44) | CI | `ruff check` failures now cause the test workflow to fail; previously lint errors were reported but did not block merges | low | 2026-02-16 | `.github/workflows/tests.yml` |
| Cron mtime hot-reload | [#22](https://github.com/Athemis/nanobot-redux/pull/22) | Cron service | `nanobot cron add` (CLI) writes only to disk; the running gateway never reloaded its in-memory store, so externally added jobs were silently skipped. Adds `_store_mtime` tracking, `_check_disk_changes()`, and a `_POLL_INTERVAL_S=300` cap on `_arm_timer` — fixes both the empty-store case (no timer at all) and the far-future-job case (timer would fire too late). No new dependencies. See rejected [HKUDS/nanobot#788](https://github.com/HKUDS/nanobot/pull/788) for the watchdog alternative. | low | 2026-02-18 | `pytest tests/test_cron_service.py` |
| Cron `_save_store` OSError resilience | [#22](https://github.com/Athemis/nanobot-redux/pull/22) | Cron service | `write_text()` or `stat()` in `_save_store` could raise `OSError` (disk full, permission error), propagating through `_on_timer` and killing the `tick()` asyncio task before `_arm_timer()` is called — permanently stopping the cron loop. Wraps both calls in `try/except OSError` with error logging; `_store_mtime` is only updated on success. | low | 2026-02-18 | `pytest tests/test_cron_service.py` |
| LiteLLM removal — OpenAIProvider replaces LiteLLMProvider | [#33](https://github.com/Athemis/nanobot-redux/pull/33) | Providers | Removes `litellm` dependency entirely; `OpenAIProvider` uses `openai.AsyncOpenAI` directly with `base_url` routing. All OpenAI-compatible providers (OpenRouter, DeepSeek, Zhipu, Moonshot, MiniMax, Groq, vLLM, AiHubMix, OpenAI) work without LiteLLM. Anthropic-native and Gemini-native support dropped — both are accessible via OpenRouter. `CustomProvider` absorbed into `OpenAIProvider` (same `_parse()` logic, adds registry-based routing). `ProviderSpec` fields `env_extras`, `skip_prefixes`, `is_direct` removed; `litellm_prefix` renamed to `model_prefix`. Breaking: `bedrock/` models no longer supported; `providers.anthropic`, `providers.gemini`, `providers.custom` config keys warn and are removed during migration. | low | 2026-02-18 | `grep -rE "import litellm\|LiteLLMProvider\|CustomProvider" nanobot/` (no output) + `pytest -q` + `ruff check nanobot/ tests/` |
| CI code coverage enforcement | [#42](https://github.com/Athemis/nanobot-redux/pull/42) | CI | `pytest` runs produce a `term-missing` coverage report and fail if total coverage of `nanobot/` drops below 63%; prevents silent test-gap regressions on every push and in CI without requiring changes to the workflow file | low | 2026-02-18 | `pytest -q` (last line: `Required test coverage of 63% reached`) |

### Template for New Entries

```markdown
| Description | [#N](https://github.com/Athemis/nanobot-redux/pull/N) or [abc1234](https://github.com/Athemis/nanobot-redux/commit/abc1234) | Area | Why | low | YYYY-MM-DD | `pytest tests/...` |
```

**Columns:**

- **Change**: Short description of what changed
- **PR/Commit**: Link to the PR or the key implementation commit in this fork
- **Area**: What part of the codebase (Codex Provider, Email channel, CI, etc.)
- **Why**: Rationale — what problem it solves or what invariant it enforces
- **Risk**: `low`, `medium`, or `high` — maintenance/security assessment
- **Added**: Date merged into `main` (YYYY-MM-DD)
- **Verification**: How to verify it works

## Notes

- **Not everything is logged**: Minor docs tweaks, workspace content edits, and style-only changes don't get entries.
- **Dates are merge dates**: When the change landed in `main`, not when it was authored.
- **Risk is subjective**: Assessed for maintenance burden and security impact.

## Related Documentation

- [`docs/upstream-log.md`](upstream-log.md) - Upstream adoptions, deferrals, and rejections
- [`docs/redux-manifest.md`](redux-manifest.md) - Fork philosophy and priorities
- [`docs/upstream-intake.md`](upstream-intake.md) - How upstream changes are evaluated
- [`docs/release-template.md`](release-template.md) - Release checklist
