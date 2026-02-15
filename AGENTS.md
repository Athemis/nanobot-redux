# Repository Guidelines

## MCP Tools

Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask.

## Squidbot Core Principles

- Ultra-lightweight core (~4,000 lines) over framework bloat.
- Research-ready, readable code over hidden complexity.
- Fast startup and low resource usage to maximize iteration speed.
- Easy onboarding and deployment with minimal setup friction.
- Quintessence: radical simplicity to maximize learning speed, development velocity, and practical impact.

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

- `squidbot/` contains the Python app code (agent loop, tools, channels, providers, CLI, config, cron, heartbeat, session, skills).
- `tests/` contains `pytest` suites plus `test_docker.sh` for container smoke testing.
- `docs/` stores focused feature/configuration docs (for example web search setup).
- `workspace/` is runtime workspace content (agent notes/memory) and is not core library code.
- Root files include packaging/config (`pyproject.toml`), container setup (`Dockerfile`), and project docs (`README.md`, `SECURITY.md`).

## Build, Test, and Development Commands

- `pip install -e .`: install Squidbot in editable mode.
- `pip install -e ".[dev]"`: install with test/lint dependencies.
- `squidbot onboard`: initialize local config and workspace.
- `squidbot agent` or `squidbot agent -m "Hello"`: run interactive or one-shot chat.
- `squidbot gateway`: run channel gateway integrations.
- `squidbot status`: show config, workspace, model, and provider readiness.
- `squidbot channels status`: show channel enablement/config overview.
- `squidbot cron list`: inspect scheduled tasks.
- `squidbot provider login openai-codex`: run OAuth login for Codex provider.
- `source .venv/bin/activate && pytest`: run Python tests in the project virtual environment.
- `ruff check .`: run lint checks.
- `bash tests/test_docker.sh`: build image and run Docker smoke checks.

## Coding Style & Naming Conventions

- Target Python 3.11+ and keep new code type-annotated.
- Use 4-space indentation; `snake_case` for modules/functions/variables; `PascalCase` for classes.
- Follow Ruff settings in `pyproject.toml` (line length 100, rules `E,F,I,N,W`).
- Keep features in the matching package (for example, channel logic in `squidbot/channels/`, provider logic in `squidbot/providers/`).
- Prefer explicit, readable control flow over framework-style indirection or hidden magic.

## Testing Guidelines

- Use `pytest` with `pytest-asyncio` for async paths.
- Run tests from the activated project virtual environment (`source .venv/bin/activate`).
- Test files and test functions should follow `test_*.py` and `test_*` naming.
- Add/update tests in `tests/` for behavior changes, especially tool validation, channel handling, and provider routing.
- Prefer deterministic unit tests (mocks/monkeypatch) over live network dependencies.
- Before opening a PR, run at least `ruff check .` and `pytest`.

## Commit & Pull Request Guidelines

- Follow the Conventional Commits specification for all commit messages.
- Mirror existing commit style: `feat:`, `fix:`, `docs:`, `refactor:`, and scoped forms like `feat(email): ...`.
- Keep commit titles imperative and concise.
- PRs should include: summary, rationale, test evidence (`pytest`, `ruff`, relevant docker commands), and linked issues.
- Update docs/config examples when changing CLI behavior, provider setup, or channel integration flows.

## Security & Configuration Tips

- Do not commit API keys or local secrets; keep them in `~/.squidbot/config.json`.
- Do not commit personal runtime data from `workspace/` unless intentionally needed.
- For safer production operation, enable `tools.restrictToWorkspace` in config.
