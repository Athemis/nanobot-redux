# Upstream Log

This file tracks what I've adopted from upstream (`HKUDS/nanobot`), what I've deferred, and occasionally what I've explicitly rejected. It's a historical record and helps me remember why I made each decision.

See [`docs/upstream-intake.md`](upstream-intake.md) for the adoption process.
See [`docs/redux-changes.md`](redux-changes.md) for changes that originate in this fork.

## How to Use This Log

- **Adopted**: Changes integrated into `redux/main`
- **Deferred**: Interesting but not ready yet - revisit later
- **Rejected**: Explicitly decided not to adopt (recorded for transparency)

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
| [a219a91](https://github.com/HKUDS/nanobot/commit/a219a91bc5e41a311d7e48b752aa489039ccd281)                                                   | Skills loader   | Adds compatibility with `openclaw`/ClawHub skill metadata frontmatter                                                                                                              | low  | 2026-02-16 | `pytest tests/test_skills_loader.py`                                                                            |
| [1ce586e](https://github.com/HKUDS/nanobot/commit/1ce586e9f515ca537353331f726307844e1b4e2f)                                                   | Codex Provider  | Upstream fixes for [HKUDS/nanobot#151](https://github.com/HKUDS/nanobot/pull/151)                                                                                                 | low  | 2026-02-16 | -                                                                                                               |
| [#744](https://github.com/HKUDS/nanobot/pull/744) + [6bae6a6](https://github.com/HKUDS/nanobot/commit/6bae6a617f7130e0a1021811b8cd8b379c2c0820) | Cron scheduling | Preserves timezone-aware cron semantics end-to-end (`--tz` propagation + deterministic next-run computation), fixes timezone display edge cases, and adds timezone validation/docs | low  | 2026-02-17 | `ruff check nanobot/agent/tools/cron.py nanobot/cli/commands.py nanobot/cron/service.py`                        |
| [#747](https://github.com/HKUDS/nanobot/pull/747) (partial)                                                                                     | Message tool    | Keep upstream attachment count feedback in `message` tool responses while preserving redux media-path sanitization; Telegram channel changes intentionally excluded                | low  | 2026-02-17 | `ruff check nanobot/agent/tools/message.py tests/test_message_tool.py` + `pytest -q tests/test_message_tool.py` |
| [#748](https://github.com/HKUDS/nanobot/pull/748)                                                                                               | Agent context   | Avoids sending empty assistant `content` entries that some providers reject when assistant messages only contain tool calls/reasoning                                             | low  | 2026-02-17 | `ruff check nanobot/agent/context.py tests/test_agent_context.py` + `pytest -q tests/test_agent_context.py`      |
| [#759](https://github.com/HKUDS/nanobot/pull/759) *(superseded by [#766](https://github.com/HKUDS/nanobot/pull/766))*                           | Config loader   | Fixes `HKUDS/nanobot#703` by preserving MCP `env` map entry names (`OPENAI_API_KEY`, etc.) during snake/camel conversion without broad config refactors                           | low  | 2026-02-17 | superseded |
| [#766](https://github.com/HKUDS/nanobot/pull/766)                                                                                               | Config loader   | Replaces manual camel/snake conversion in `loader.py` with Pydantic `alias_generator=to_camel` on all schema models; removes ~80 lines of path-tracking conversion code; `env` and `extra_headers` dict keys are preserved automatically since Pydantic alias_generator only applies to model field names, not dict keys | low  | 2026-02-17 | `ruff check nanobot/config/loader.py nanobot/config/schema.py tests/test_config_loader_conversion.py` + `pytest -q tests/test_config_loader_conversion.py tests/test_tool_validation.py` |
| [#713](https://github.com/HKUDS/nanobot/pull/713) (partial, session-scoping only) | Session | Scopes session storage to `<workspace>/sessions/` instead of global `~/.nanobot/sessions/`; legacy sessions still readable as fallback. `get_history()` tool-metadata part deferred — see Deferred section. | low  | 2026-02-18 | `ruff check nanobot/session/manager.py` |
| [#765](https://github.com/HKUDS/nanobot/pull/765) | Docker | Adds `docker-compose.yml` with persistent gateway service (restart policy, 1 CPU / 1 GB resource limits) and on-demand CLI service (`--profile cli`); README gains "Using Docker Compose" section. Cherry-pick `c03f2b6` applied cleanly. | low  | 2026-02-18 | `docker compose build && docker compose run --rm nanobot-cli status` + `bash tests/test_docker.sh` |
| [#746](https://github.com/HKUDS/nanobot/pull/746) | CLI / Cron | Wires `CronService` into `nanobot agent` CLI command; previously only the gateway had cron tool access. Cherry-pick `778a933` with conflict resolved (import order, `brave_api_key` → `web_search_config`). | low  | 2026-02-18 | `ruff check nanobot/cli/commands.py` + `pytest -q` |
| [#786](https://github.com/HKUDS/nanobot/pull/786) | Custom provider | New `CustomProvider` bypasses LiteLLM for the `custom` endpoint via `openai.AsyncOpenAI` directly — fixes model-prefix mangling for local/self-hosted servers. Cherry-pick `e2a0d63` with conflict resolved (import order in `_make_provider`); upstream's improved `is_oauth` guard in API key check adopted. **Phase 2 note:** `CustomProvider` was subsequently absorbed into `OpenAIProvider` (see redux-changes.md LiteLLM removal); `custom_provider.py` deleted, `is_direct` mechanism obsolete. | low  | 2026-02-18 | `ruff check nanobot/providers/registry.py nanobot/cli/commands.py` + `pytest -q` |
| [#590](https://github.com/HKUDS/nanobot/pull/590) | Session memory | Consolidation offset tracking: `last_consolidated` pointer prevents re-summarising messages already written to HISTORY.md; messages are append-only (consolidation never mutates history); background consolidation via `asyncio.create_task()`. Fork implements equivalent behavior independently — verified by `tests/test_consolidate_offset.py`. | low | 2026-02-18 | `pytest -q tests/test_consolidate_offset.py` |
| [#802](https://github.com/HKUDS/nanobot/pull/802) | Agent / CLI | Pre-tool progress streaming: `on_progress` callback fires before each tool call with the agent's reasoning text; CLI shows live `↳ {text}` instead of generic spinner; system prompt nudge added. Independent re-implementation against fork's `OpenAIProvider` architecture (upstream written against LiteLLM). **Note:** initial re-implementation omitted `_bus_progress` default — gateway users (Matrix, Email) received no intermediate updates; fixed in [b41409e](https://github.com/Athemis/nanobot-redux/commit/b41409e) + [67ab8d3](https://github.com/Athemis/nanobot-redux/commit/67ab8d3) (see `redux-changes.md`). | low | 2026-02-18 | `pytest -q tests/test_on_progress.py` |
| [#803](https://github.com/HKUDS/nanobot/pull/803) | Providers | Mistral AI provider: `mistral: ProviderConfig` in `ProvidersConfig`, `ProviderSpec` in registry. Cherry-pick `d04d5f6` with conflict resolved: replaced LiteLLM-specific fields (`litellm_prefix`, `skip_prefixes`, `env_extras`) with fork's `model_prefix="mistral"` and `default_api_base="https://api.mistral.ai/v1"`; dropped upstream-only `siliconflow`/`github_copilot` schema fields. | low | 2026-02-18 | `pytest -q tests/test_mistral_provider.py` |
| [#851](https://github.com/HKUDS/nanobot/pull/851) | Shell tool | Prevents subprocess FD/pipe leaks on timeout by awaiting bounded `process.wait()` after `process.kill()`; adopted via cherry-pick `c86dbc9`. | low | 2026-02-19 | `ruff check nanobot/agent/tools/shell.py tests/test_shell_guard.py` + `pytest -q tests/test_shell_guard.py --no-cov` |
| [#823](https://github.com/HKUDS/nanobot/pull/823) (`107a380e`) | Session memory | Adds `_consolidating: set[str]` guard so only one background consolidation task runs per session key; `finally` block always clears the flag. Fork also fixes #56 (replace `MemoryStore(self.workspace)` with `self.context.memory`) and extends the guard to the `/new` command path + stores task refs in `_consolidation_tasks` to prevent GC. | low | 2026-02-20 | `pytest -q tests/test_consolidate_offset.py` |
| [#825](https://github.com/HKUDS/nanobot/pull/825) (`464352c`) | Agent loop | Allow one retry when a model sends interim text before tool calls (e.g. "Let me investigate…" from MiniMax, Gemini Flash, GPT-4.1). Forwards interim text via `on_progress`; single retry prevents infinite loops. Conflict resolved: `response.content or ""` guards fork's `str`-typed `_strip_think`. | low | 2026-02-20 | `pytest -q tests/test_agent_loop.py` |
| [#455](https://github.com/HKUDS/nanobot/pull/455) (`c7b5dd9` + `a2379a0`) | UTF-8 encoding | Ensure `encoding="utf-8"` and `ensure_ascii=False` throughout file operations and JSON serialisation (loop, cron store, config loader, web tool, session, subagent). Conflict resolved: cron `_save_store` keeps fork's OSError guard + `_check_disk_changes`; `dingtalk.py` dropped (channel removed in fork). | low | 2026-02-20 | `pytest -q tests/test_cron_service.py tests/test_config_loader_conversion.py tests/test_web_search_tool.py` |
| [#653](https://github.com/HKUDS/nanobot/pull/653) (`fbbbdc7` + `e17342d`) | File tools / subagent | Resolve relative paths against `workspace` in `_resolve_path`; pass `workspace=` to all file tool constructors in both the main loop and subagent. Conflict resolved: `_resolve_path` signature extended to keep fork's `extra_allowed_dirs` (builtin-skills allowlist); `DeleteFileTool` unchanged (custom symlink guard); subagent retains `skill_dirs` passthrough for `ReadFileTool`. | low | 2026-02-20 | `pytest -q tests/test_filesystem_tools.py tests/test_subagent.py` |
| [#644](https://github.com/HKUDS/nanobot/pull/644) (`b523b27`) | Agent / memory | Guard `history_entry` and `memory_update` with `isinstance(…, str)` check in `_consolidate_memory`; non-string values (dict, list) are JSON-serialised. Fixes `TypeError` when LLM returns structured data instead of a plain string. Applied cleanly. | low | 2026-02-20 | `pytest -q tests/test_memory_consolidation_types.py tests/test_consolidate_offset.py` |
| [#705](https://github.com/HKUDS/nanobot/pull/705) (`1b49bf9`) | Agent loop | Follow-up to #825 retry: remove duplicate `on_progress` call on retry path; reset `final_content = None` before retry so stale text is never returned if the retry also fails. Applied cleanly. | low | 2026-02-20 | `pytest -q tests/test_agent_loop.py` |
| [#864](https://github.com/HKUDS/nanobot/pull/864) (`37252a4`) | Logging | Replace f-string logger calls with loguru native `logger.info("msg {}", var)` syntax throughout fork-relevant files; prevents `KeyError` when log messages contain literal `{` or `}`. Removed-channel files (dingtalk, discord, feishu, qq, slack, telegram, whatsapp) excluded. Also includes session path migration (`shutil.move`) for legacy session files. | low | 2026-02-20 | `ruff check . && pytest --no-cov -q` |
| [#870](https://github.com/HKUDS/nanobot/pull/870) (`0001f28`) | Message bus | Remove dead pub/sub methods (`subscribe_outbound`, `dispatch_outbound`, `stop`) from `MessageBus`; zero callers — `ChannelManager._dispatch_outbound` handles all outbound routing via `consume_outbound()`. Conflict resolved: HEAD had unused `Callable`/`Awaitable` imports and `_outbound_subscribers`/`_running` state. | low | 2026-02-20 | `ruff check nanobot/bus/queue.py && pytest --no-cov -q` |
| [#807](https://github.com/HKUDS/nanobot/pull/807) (`c5b4331` + `f5fe74f`) | MCP / Config | Add `headers: dict[str, str]` to `MCPServerConfig`; when present, creates an `httpx.AsyncClient` with those headers for the streamable HTTP MCP connection (e.g. `Authorization: Bearer ...`). Moves `httpx` import to top-level. Conflict resolved: upstream f-string warning already resolved by #864. | low | 2026-02-20 | `ruff check nanobot/agent/tools/mcp.py nanobot/config/schema.py` |
| [#821](https://github.com/HKUDS/nanobot/pull/821) (`b97b1a5`) | CLI / Cron | Fix `nanobot cron run` to pass the full agent config: `temperature`, `max_tokens`, `web_search_config`, `mcp_servers`. Previously the manual run command ignored most config, so the agent ran with wrong defaults. Conflict resolved: `brave_api_key` → `web_search_config` (fork API); import sort fixed. | low | 2026-02-20 | `ruff check nanobot/cli/commands.py` |
| [#833](https://github.com/HKUDS/nanobot/pull/833) (`523b298`) | Agent loop | Always fire `on_progress` with the tool hint when `response.has_tool_calls`, even when the model also sends preceding text. Previously `clean or tool_hint` caused the hint to be dropped if `clean` was truthy. Conflict resolved: HEAD lacked the `on_progress` block; took upstream version, applied style fix from `8db91f5`. | low | 2026-02-20 | `ruff check nanobot/agent/loop.py && pytest --no-cov -q tests/test_on_progress.py` |
| [#892](https://github.com/HKUDS/nanobot/pull/892) (`44f44b3` + `37222f9`) | MCP / loop | MCP retry on failed connection + concurrent-connect guard | low | 2026-02-20 | `pytest tests/test_mcp_tool.py --no-cov` |

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

| Upstream PR/Commit                                        | Area          | Why Deferred                                                                 | Revisit When                                                                                |
| --------------------------------------------------------- | ------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| [#713](https://github.com/HKUDS/nanobot/pull/713) (`get_history()` part only) | Session | `get_history()` is extended to preserve `tool_calls`/`tool_call_id`/`name` — but both upstream and redux `loop.py` only persist user + final assistant messages; tool messages are never written to the session. The fix is a no-op in the current architecture. | When `loop.py` is extended to persist individual tool call/result messages to the session |

## Rejected Changes

Changes I've explicitly decided not to adopt (for transparency and to avoid reconsidering the same thing repeatedly):

| Upstream PR/Commit                  | Area | Why Rejected | Rejected |
| ----------------------------------- | ---- | ------------ | -------- |
| [#788](https://github.com/HKUDS/nanobot/pull/788) | Cron hot-reload | Adds `watchdog` dependency + async public API refactor for filesystem-event-driven store reload. Replaced in redux by lightweight mtime polling ([#22](https://github.com/Athemis/nanobot-redux/pull/22)) — no new dependency, 5-minute polling latency is sufficient for minute-granularity cron jobs. If upstream adopts #788, redux will likely follow and drop polling. | 2026-02-18 |
| [#820](https://github.com/HKUDS/nanobot/pull/820) | Shell guard | Already covered in redux by the hardened exec safety regex (`nanobot/agent/tools/shell.py`) and existing guard allow-case for `?format=3` (`tests/test_shell_guard.py`); upstream's added networked curl tests are not aligned with redux's no-live-network test policy. | 2026-02-19 |

## Notes

- **Not everything is logged**: I only track significant changes. Minor docs updates or typo fixes don't get entries.
- **Dates are adoption dates**: Not when the upstream PR was merged, but when I integrated it into redux.
- **Risk is subjective**: Based on my assessment of maintenance burden and security impact.
- **Deferred ≠ Rejected**: Deferred means "maybe later", rejected means "probably never".

## Related Documentation

- [`docs/redux-manifest.md`](redux-manifest.md) - Fork philosophy and adoption criteria
- [`docs/upstream-intake.md`](upstream-intake.md) - How I evaluate and adopt changes
- [`docs/redux-changes.md`](redux-changes.md) - Changes originating in this fork
- [`docs/release-template.md`](release-template.md) - Release process
