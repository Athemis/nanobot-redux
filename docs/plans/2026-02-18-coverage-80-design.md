# Design: Test Coverage 63% → 80%

**Date:** 2026-02-18
**Status:** Approved
**Goal:** Increase pytest coverage from 63.3% to 80% by adding ~633 covered statements.

## Context

Current state (228 tests, 2.56s):

```text
Total statements : 3792
Currently covered: 2401  (63.3%)
Target covered   : 3034  (80.0%)
Gap              : +633 statements
```

## Strategy

**Quick-wins first, then ROI-first.**

Phase 1 targets modules already close to 80% — low effort, immediate visible progress.
Phase 2 targets modules with the highest absolute missing-line count — maximum coverage gain per test written.

`# pragma: no cover` is applied only to genuine entry-points:
- `nanobot/__main__.py` (3 stmts)
- `nanobot/heartbeat/__init__.py` (2 stmts)

## Phase 1 — Quick-wins (modules 70–79%)

Modules that need a small push to cross 80%. Ordered by effort (easiest first).

| Module | Current | Missing for 80% | Action |
|---|---|---|---|
| `providers/openai_provider.py` | 79% | ~1 stmt | Extend `test_onboard_openrouter_defaults.py` |
| `agent/memory.py` | 79% | ~1 stmt | New `test_agent_memory.py` |
| `channels/matrix.py` | 77% | ~18 stmts | Extend `test_matrix_channel.py` |
| `agent/subagent.py` | 77% | ~3 stmts | New `test_agent_subagent.py` |
| `channels/email.py` | 75% | ~14 stmts | Extend `test_email_channel.py` |
| `channels/base.py` | 71% | ~4 stmts | New `test_channels_base.py` |

Estimated gain: **~41 statements** → coverage ~64.4%

## Phase 2 — ROI-first (highest missing-line count)

Ordered by absolute missing lines descending.

| # | Module | Current | Missing | Action |
|---|---|---|---|---|
| 1 | `cli/commands.py` | 37% | 277 | Extend `test_commands.py`, `test_cron_commands.py`, `test_cli_input.py` |
| 2 | `agent/loop.py` | 55% | 114 | Extend `test_generation_params.py`, `test_on_progress.py` |
| 3 | `providers/openai_codex_provider.py` | 47% | 110 | Extend `test_generation_params.py` |
| 4 | `heartbeat/service.py` | 0% | 75 | New `test_heartbeat.py` |
| 5 | `cron/service.py` | 66% | 72 | Extend `test_cron_service.py` |
| 6 | `channels/manager.py` | 22% | 63 | New `test_channels_manager.py` |
| 7 | `agent/tools/mcp.py` | 0% | 53 | New `test_mcp_tool.py` |
| 8 | `agent/tools/cron.py` | 24% | 54 | Extend `test_cron_commands.py` |
| 9 | `agent/tools/shell.py` | 44% | 41 | Extend `test_shell_guard.py` |
| 10 | `agent/tools/web.py` | 70% | 50 | Extend `test_web_search_tool.py` |
| 11 | `agent/tools/filesystem.py` | 68% | 50 | Extend `test_filesystem_delete_tool.py` |
| 12 | `providers/transcription.py` | 0% | 28 | New `test_transcription_provider.py` |
| 13 | `config/loader.py` | 53% | 18 | Extend `test_config_loader_conversion.py` |
| 14 | `bus/queue.py` | 51% | 21 | New `test_bus_queue.py` |
| 15 | `utils/helpers.py` | 52% | 16 | New `test_utils_helpers.py` |

Not every module needs to reach 100% — we stop when the 80% overall target is met.

## New Test Files

| File | Covers |
|---|---|
| `tests/test_agent_memory.py` | `nanobot/agent/memory.py` |
| `tests/test_agent_subagent.py` | `nanobot/agent/subagent.py` |
| `tests/test_channels_base.py` | `nanobot/channels/base.py` |
| `tests/test_channels_manager.py` | `nanobot/channels/manager.py` |
| `tests/test_heartbeat.py` | `nanobot/heartbeat/service.py` |
| `tests/test_mcp_tool.py` | `nanobot/agent/tools/mcp.py` |
| `tests/test_bus_queue.py` | `nanobot/bus/queue.py` |
| `tests/test_utils_helpers.py` | `nanobot/utils/helpers.py` |
| `tests/test_transcription_provider.py` | `nanobot/providers/transcription.py` |

## Existing Test Files to Extend

| File | Module targeted |
|---|---|
| `tests/test_onboard_openrouter_defaults.py` | `providers/openai_provider.py` |
| `tests/test_matrix_channel.py` | `channels/matrix.py` |
| `tests/test_email_channel.py` | `channels/email.py` |
| `tests/test_commands.py`, `test_cli_input.py`, `test_cron_commands.py` | `cli/commands.py` |
| `tests/test_generation_params.py`, `test_on_progress.py` | `agent/loop.py` |
| `tests/test_generation_params.py` | `providers/openai_codex_provider.py` |
| `tests/test_cron_service.py` | `cron/service.py` |
| `tests/test_shell_guard.py` | `agent/tools/shell.py` |
| `tests/test_web_search_tool.py` | `agent/tools/web.py` |
| `tests/test_filesystem_delete_tool.py` | `agent/tools/filesystem.py` |
| `tests/test_config_loader_conversion.py` | `config/loader.py` |

## Pragma Exclusions

Add `# pragma: no cover` to:

- `nanobot/__main__.py` — CLI entry-point, not importable in tests
- `nanobot/heartbeat/__init__.py` — re-export init, no logic

## Test Approach per Module

**`cli/commands.py`** — Use Typer's `CliRunner` + monkeypatch for config paths. Test `status`, `agent`, `gateway`, `provider login` command paths.

**`agent/loop.py`** — Mock `litellm.acompletion`. Test tool-call iterations, max-turns cutoff, error handling, context trimming.

**`providers/openai_codex_provider.py`** — Mock `httpx.AsyncClient`. Test SSE streaming, error events, reconnect logic, OAuth refresh.

**`heartbeat/service.py`** — Use `asyncio` with short intervals. Test start/stop lifecycle, tick callbacks, error resilience.

**`cron/service.py`** — Extend existing tests for missed execution paths: delete, list, next-run calculation, concurrent execution guard.

**`channels/manager.py`** — Mock channel classes. Test start/stop lifecycle, channel registration, message routing.

**`agent/tools/mcp.py`** — Mock MCP client transport. Test tool listing, execution, error handling.

**`agent/tools/shell.py`** — Extend shell guard tests with actual subprocess mock. Cover timeout, working directory, stdout/stderr capture.

**`bus/queue.py`** — Test async put/get, drain, size limit, cancellation.

**`utils/helpers.py`** — Unit test pure helper functions directly.

**`providers/transcription.py`** — Mock audio file I/O and provider API. Test transcription request/response path.

## Acceptance Criteria

- `pytest --cov=nanobot` reports ≥ 80.0% total coverage
- `ruff check .` passes with no new errors
- All 228 existing tests continue to pass
- No coverage inflation via excessive pragmas
