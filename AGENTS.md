# Repository Guidelines

## MCP Tools

Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask.

## Nanobot Redux Principles

- Ultra-lightweight core (~4,000 lines) over framework bloat.
- Research-ready, readable code over hidden complexity.
- Fast startup and low resource usage to maximize iteration speed.
- Easy onboarding and deployment with minimal setup friction.
- Quintessence: radical simplicity to maximize learning speed, development velocity, and practical impact.

## Fork Context

- This repository is `nanobot redux`, an opinionated fork of `HKUDS/nanobot`.
- Fork baseline is `HKUDS/nanobot v0.1.3.post7`.
- Keep fork decisions aligned with `docs/redux-manifest.md`.
- Preserve fork stability guarantees unless explicitly changed: CLI stays `nanobot`.
- Preserve fork stability guarantees unless explicitly changed: Python package namespace stays `nanobot.*`.
- Preserve fork stability guarantees unless explicitly changed: config path stays `~/.nanobot/*`.
- Runtime and CI baseline is Python `3.14`.

Context7 Library IDs for this project (use to skip library-matching):

| Library              | Context7 ID                             |
| -------------------- | --------------------------------------- |
| LiteLLM              | `/berriai/litellm`                      |
| Pydantic             | `/pydantic/pydantic`                    |
| Typer                | `/fastapi/typer`                        |
| Rich                 | `/textualize/rich`                      |
| Loguru               | `/delgan/loguru`                        |
| DDGS                 | `/deedy5/ddgs`                          |
| HTTPX                | `/encode/httpx`                         |
| MCP Python SDK       | `/modelcontextprotocol/python-sdk`      |
| Prompt Toolkit       | `/prompt-toolkit/python-prompt-toolkit` |
| Pytest               | `/pytest-dev/pytest`                    |
| Ruff                 | `/astral-sh/ruff`                       |
| Matrix Nio           | `/matrix-nio/matrix-nio`                |
| Matrix Specification | `/websites/spec_matrix`                 |

## Project Structure & Module Organization

- `nanobot/` contains the Python app code (agent loop, tools, channels, providers, CLI, config, cron, heartbeat, session, skills).
- `nanobot/agent/` — agent loop, context builder, memory, subagent, skills loader, and all tool implementations.
- `nanobot/channels/` — `BaseChannel` ABC plus concrete implementations (`email.py`, `matrix.py`) and `manager.py`.
- `nanobot/providers/` — `LLMProvider` ABC plus concrete implementations and transcription support.
- `nanobot/config/` — Pydantic schema (`schema.py`) and config loader (`loader.py`).
- `nanobot/bus/` — internal event bus (`queue.py`, `events.py`).
- `tests/` contains `pytest` suites plus `test_docker.sh` for container smoke testing.
- `docs/` stores feature/configuration docs plus fork governance docs (`docs/redux-manifest.md`, `docs/upstream-intake.md`, `docs/upstream-log.md`, `docs/redux-changes.md`, `docs/release-template.md`).
- `workspace/` is runtime workspace content (agent notes/memory) and is not core library code.
- Root files include packaging/config (`pyproject.toml`), container setup (`Dockerfile`), and project docs (`README.md`, `SECURITY.md`).

## Build, Test, and Development Commands

```bash
# Install
pip install -e .                         # editable install
pip install -e ".[dev]"                  # with test/lint dependencies

# Lint
ruff check .                             # lint (must pass before PR)
ruff check --fix .                       # auto-fix safe issues

# Tests — run from the activated venv
source .venv/bin/activate && pytest      # full suite with coverage
pytest tests/test_agent_context.py       # single file
pytest tests/test_tool_validation.py::test_validate_params_missing_required  # single test
pytest -k "keyword"                      # filter by keyword
pytest -x                                # stop on first failure
pytest --no-cov                          # skip coverage (faster iteration)

# Verification
bash core_agent_lines.sh                 # verify core line count target
bash tests/test_docker.sh               # build image + Docker smoke checks

# Runtime
nanobot onboard                          # initialize local config and workspace
nanobot status                           # show config, workspace, model, provider
nanobot agent                            # interactive chat
nanobot agent -m "Hello"                 # one-shot message
nanobot gateway                          # run channel gateway integrations
nanobot channels status                  # channel enablement overview
nanobot cron list                        # inspect scheduled tasks
nanobot provider login openai-codex      # OAuth login for Codex provider
```

pytest config is in `pyproject.toml`: `asyncio_mode = "auto"`, coverage threshold 80%, test path `tests/`.

## Coding Style & Naming Conventions

- Target Python 3.14; all new code must be fully type-annotated.
- 4-space indentation; `snake_case` for modules/functions/variables; `PascalCase` for classes.
- Line length 100 (Ruff enforced); `E501` is ignored so long lines are allowed but keep them readable.
- Ruff rule set: `E, F, I, N, W` — see `pyproject.toml` `[tool.ruff.lint]`.

### Import Order (Ruff `I` enforced)

```python
# 1. stdlib
import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

# 2. third-party
from loguru import logger
from pydantic import BaseModel

# 3. first-party (nanobot.*)
from nanobot.agent.tools.base import Tool
from nanobot.bus.queue import MessageBus

# 4. TYPE_CHECKING-only imports (avoids circular imports at runtime)
if TYPE_CHECKING:
    from nanobot.config.schema import WebSearchConfig
```

### Type Annotations

- Use `X | Y` union syntax (Python 3.10+), not `Optional[X]` or `Union[X, Y]`.
- Use `list[T]`, `dict[K, V]` (lowercase), not `List`, `Dict` from `typing`.
- Use `from collections.abc import Callable, Awaitable` for callable types.
- Prefer `Path` over `str` for filesystem arguments.
- Return type `None` must be explicit on functions that only produce side effects.

### Error Handling

- Raise `PermissionError` for security/access violations (e.g., path outside allowed dir).
- Return `"Error: <description>"` strings from tool `execute()` methods — do not raise into the agent loop.
- Log exceptions with `logger.exception(...)` or `logger.error(...)` (Loguru); never use `print()` for diagnostics.
- Use specific exception types; avoid bare `except Exception` unless re-raising or logging at top level.

### Docstrings

- Module-level: one-line summary, required for every module file.
- Class-level: describe the role and key invariants; avoid restating the class name.
- Method-level: document only public APIs and non-obvious side effects/security behavior.
- Do not add docstrings for trivial `name`/`description`/`parameters` properties or obvious magic methods.
- Keep docstrings short (usually 1–2 sentences); avoid verbose Args/Returns blocks for simple methods.
- Avoid broad docstring-only churn; make docstring edits only when they improve clarity for maintained code paths.

### Architecture Patterns

- New tools: subclass `nanobot.agent.tools.base.Tool`, implement `name`, `description`, `parameters`, and `async execute(**kwargs)`.
- New channels: subclass `nanobot.channels.base.BaseChannel`, implement `start()`, `stop()`, and `send_message()`.
- New providers: subclass `nanobot.providers.base.LLMProvider`, implement `chat()` and `get_default_model()`.
- Config additions: add a Pydantic model to `nanobot/config/schema.py` extending `Base`; use `camelCase` aliases via `to_camel`.
- Prefer explicit, readable control flow over framework-style indirection or hidden magic.

## Testing Guidelines

- Use `pytest` with `pytest-asyncio` (`asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed).
- Run tests from the activated project virtual environment (`source .venv/bin/activate`).
- Test files: `tests/test_<module>.py`; test functions: `test_<behavior>`.
- Use `monkeypatch` or `unittest.mock` — prefer deterministic unit tests over live network calls.
- `tmp_path` fixture (pytest built-in) for workspace/file tests.
- Add/update tests for behavior changes, especially tool validation, channel handling, and provider routing.
- Coverage threshold is 80% (`--cov-fail-under=80`); run `pytest --no-cov` only for fast local iteration.
- Before opening a PR, run `ruff check .` and `pytest` (with coverage) and confirm both pass.

## Commit & Pull Request Guidelines

- Always sign commits with GPG (`git commit -S`).
- Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, and scoped forms like `feat(email): ...`.
- Keep commit titles imperative and concise (≤72 chars).
- PRs must include: summary, rationale, test evidence (`pytest`, `ruff`, relevant docker commands), and linked issues.
- Update docs/config examples when changing CLI behavior, provider setup, or channel integration flows.
- Keep `README.md` current: update feature descriptions, install instructions, and CLI examples when the corresponding behavior changes.
- Keep `docs/redux-changes.md` current: add an entry for every fork-specific code change merged into `main`.
- Keep `docs/upstream-log.md` current: add an entry for every upstream change adopted, deferred, or rejected.

## Upstream Intake & Fork Documentation

- For upstream adoption work, follow `docs/upstream-intake.md`.
- Evaluate candidates against `docs/redux-manifest.md` criteria: testability, practical need, risk, and compatibility.
- Prefer selective cherry-picks over broad merges. Use `git cherry-pick` so the source commit is referenced; resolve conflicts by keeping fork behavior where it intentionally differs.
- Use `git cherry-pick -n <sha>` (no-commit) when the upstream diff conflicts or needs structural adaptation; resolve manually then commit — the upstream SHA still appears in the commit message.
- For each adopted upstream change, add an entry in `docs/upstream-log.md` with upstream link, area, rationale, risk, adoption date, and verification command(s).
- For deferred or rejected upstream changes, record concise reasons in `docs/upstream-log.md`.
- For fork-specific changes (not adopted from upstream), add an entry in `docs/redux-changes.md` with PR/commit link, area, rationale, risk, date, and verification command(s).
- When preparing a release, use `docs/release-template.md`.

## Security & Configuration Tips

- Do not commit API keys or local secrets; keep them in `~/.nanobot/config.json`.
- Do not commit personal runtime data from `workspace/` unless intentionally needed.
- For safer production operation, enable `tools.restrictToWorkspace` in config.
- Path traversal is blocked by `_resolve_path()` in `nanobot/agent/tools/filesystem.py`; always route file operations through it when `allowed_dir` enforcement is required.
