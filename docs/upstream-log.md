# Upstream Log

This file tracks what I've adopted from upstream (`HKUDS/nanobot`), what I've deferred, and occasionally what I've explicitly rejected. It's a historical record and helps me remember why I made each decision.

## How to Use This Log

- **Adopted**: Changes integrated into `redux/main`
- **Deferred**: Interesting but not ready yet - revisit later
- **Rejected**: Explicitly decided not to adopt (recorded for transparency)

See [`docs/upstream-intake.md`](upstream-intake.md) for the adoption process.

## Baseline Features

These upstream features were integrated before I started tracking adoptions systematically. They form the foundation of the fork:

| Upstream PR                                       | Area                 | Why Adopted                                | Adopted  | Verification                                  |
| ------------------------------------------------- | -------------------- | ------------------------------------------ | -------- | --------------------------------------------- |
| [#420](https://github.com/HKUDS/nanobot/pull/420) | Matrix channel       | Core communication channel I actually use  | baseline | `pytest tests/test_matrix_channel.py`         |
| [#151](https://github.com/HKUDS/nanobot/pull/151) | OpenAI Codex OAuth   | Access to ChatGPT Plus models via OAuth    | baseline | Provider generation tests                     |
| [#398](https://github.com/HKUDS/nanobot/pull/398) | Web search + SearXNG | Self-hosted search infrastructure          | baseline | `pytest tests/test_web_search_tool.py`        |
| [#564](https://github.com/HKUDS/nanobot/pull/564) | `delete_file` tool   | Safe file deletion with symlink protection | baseline | `pytest tests/test_filesystem_delete_tool.py` |
| [#555](https://github.com/HKUDS/nanobot/pull/555) | Shell security regex | Hardening against destructive commands     | baseline | `pytest tests/test_shell_guard.py`            |

**Note**: "baseline" means these were part of the upstream release (v0.1.3.post7) that the fork is based on.

## Adopted Changes

Changes integrated after the initial fork:

| Upstream PR/Commit                                                                                                                              | Area            | Why Adopted                                                                                                                                                                        | Risk | Adopted    | Verification                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---------- | --------------------------------------------------------------------------------------------------------------- |
| HKUDS/nanobot@a219a91bc5e41a311d7e48b752aa489039ccd281                                                                                          | Skills loader   | Adds compatibility with `openclaw`/ClawHub skill metadata frontmatter                                                                                                              | low  | 2026-02-16 | `pytest tests/test_skills_loader.py`                                                                            |
| HKUDS/nanobot@1ce586e9f515ca537353331f726307844e1b4e2f                                                                                          | Codex Provider  | Upstream fixes for PR HKUDS/nanobot#151                                                                                                                                            | low  | 2026-02-16 | -                                                                                                               |
| [#744](https://github.com/HKUDS/nanobot/pull/744) + [6bae6a6](https://github.com/HKUDS/nanobot/commit/6bae6a617f7130e0a1021811b8cd8b379c2c0820) | Cron scheduling | Preserves timezone-aware cron semantics end-to-end (`--tz` propagation + deterministic next-run computation), fixes timezone display edge cases, and adds timezone validation/docs | low  | 2026-02-17 | `ruff check nanobot/agent/tools/cron.py nanobot/cli/commands.py nanobot/cron/service.py`                        |
| [#747](https://github.com/HKUDS/nanobot/pull/747) (partial)                                                                                     | Message tool    | Keep upstream attachment count feedback in `message` tool responses while preserving redux media-path sanitization; Telegram channel changes intentionally excluded                | low  | 2026-02-17 | `ruff check nanobot/agent/tools/message.py tests/test_message_tool.py` + `pytest -q tests/test_message_tool.py` |
| [#748](https://github.com/HKUDS/nanobot/pull/748)                                                                                               | Agent context   | Avoids sending empty assistant `content` entries that some providers reject when assistant messages only contain tool calls/reasoning                                             | low  | 2026-02-17 | `ruff check nanobot/agent/context.py tests/test_agent_context.py` + `pytest -q tests/test_agent_context.py`      |

## Redux-Specific Changes

Changes made in this fork that are not directly adopted from upstream:

| Change                                                  | Area           | Why                                                                                                                                                                                 | Risk   | Added      | Verification                                                                                                                                                                                                                                                                                                                                                       |
| ------------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| OpenClaw skill metadata regression tests                | Skills loader  | Lock in fork behavior for `openclaw` metadata support and `nanobot` precedence when both keys exist                                                                                 | low    | 2026-02-16 | `pytest tests/test_skills_loader.py`                                                                                                                                                                                                                                                                                                                               |
| Codex TLS verification hardening                        | Codex Provider | Avoid silent TLS downgrade; require explicit `providers.openaiCodex.sslVerify=false` opt-in                                                                                         | low    | 2026-02-16 | `pytest -q tests/test_config_loader_conversion.py tests/test_generation_params.py tests/test_onboard_openrouter_defaults.py` + `ruff check nanobot/config/schema.py nanobot/cli/commands.py nanobot/providers/openai_codex_provider.py tests/test_config_loader_conversion.py tests/test_generation_params.py tests/test_onboard_openrouter_defaults.py README.md` |
| Codex SSE error diagnostics                             | Codex Provider | Surface provider error details from `error`/`response.failed` payloads instead of generic failure text                                                                              | low    | 2026-02-16 | `pytest -q tests/test_generation_params.py` + `ruff check nanobot/providers/openai_codex_provider.py tests/test_generation_params.py`                                                                                                                                                                                                                              |
| Email TLS verification hardening + plaintext SMTP block | Email channel  | Enforce explicit TLS verification by default with explicit opt-out warning (`channels.email.tlsVerify`), and refuse SMTP sends when both `smtpUseTls` and `smtpUseSsl` are disabled | medium | 2026-02-16 | `pytest -q tests/test_email_channel.py` + `ruff check nanobot/channels/email.py tests/test_email_channel.py nanobot/config/schema.py README.md SECURITY.md`                                                                                                                                                                                                        |

### Template for New Adoptions

When adopting something new, add a row like this:

```markdown
| [#789](https://github.com/HKUDS/nanobot/pull/789) | Web search | Added provider X that I want to use | low | 2025-01-15 | `pytest tests/test_web_search_tool.py` |
```

**Columns:**

- **Upstream PR/Commit**: Link to the upstream change
- **Area**: What part of the codebase (Matrix, tools, providers, etc.)
- **Why Adopted**: Brief explanation of why it's valuable for redux
- **Risk**: `low`, `medium`, or `high` - maintenance/security assessment
- **Adopted**: Date when merged into `redux/main` (YYYY-MM-DD)
- **Verification**: How to verify it works (test commands, manual steps)

## Deferred Changes

Changes that look interesting but aren't ready to adopt yet:

| Upstream PR/Commit              | Area | Why Deferred | Revisit When |
| ------------------------------- | ---- | ------------ | ------------ |
| _No deferred changes currently_ | -    | -            | -            |

### Example Deferred Entry

```markdown
| [#999](https://github.com/HKUDS/nanobot/pull/999) | Discord channel | Don't use Discord yet | When I start using Discord for comms |
```

## Rejected Changes

Changes I've explicitly decided not to adopt (for transparency and to avoid reconsidering the same thing repeatedly):

| Upstream PR/Commit                  | Area | Why Rejected | Rejected |
| ----------------------------------- | ---- | ------------ | -------- |
| _No explicit rejections logged yet_ | -    | -            | -        |

### Example Rejected Entry

```markdown
| [#1234](https://github.com/HKUDS/nanobot/pull/1234) | WeChat channel | Can't test, don't use WeChat | 2025-01-10 |
```

## Notes

- **Not everything is logged**: I only track significant changes. Minor docs updates or typo fixes don't get entries.
- **Dates are adoption dates**: Not when the upstream PR was merged, but when I integrated it into redux.
- **Risk is subjective**: Based on my assessment of maintenance burden and security impact.
- **Deferred ≠ Rejected**: Deferred means "maybe later", rejected means "probably never".

## Related Documentation

- [`docs/redux-manifest.md`](redux-manifest.md) - Fork philosophy and adoption criteria
- [`docs/upstream-intake.md`](upstream-intake.md) - How I evaluate and adopt changes
- [`docs/release-template.md`](release-template.md) - Release process
