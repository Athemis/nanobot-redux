# Repository Guidelines

## Nanobot Redux Principles

- Ultra-lightweight core (~4,000 lines) over framework bloat.
- Research-ready, readable code over hidden complexity.
- Fast startup and low resource usage to maximize iteration speed.
- Quintessence: radical simplicity to maximize learning speed, development velocity, and practical impact.
- This is an opinionated fork of `HKUDS/nanobot` (baseline v0.1.3.post7). Decisions align with `docs/redux-manifest.md`.
- Stability guarantees: CLI stays `nanobot`, package namespace stays `nanobot.*`, config path stays `~/.nanobot/*`.

## Project Structure

- `nanobot/` - Python app code: `agent/` (loop, tools, context, memory, subagent, skills), `channels/` (email, matrix), `providers/` (openai, codex, transcription), `cli/`, `config/`, `cron/`, `heartbeat/`, `session/`, `bus/`, `utils/`, `skills/`.
- `tests/` - pytest suites plus `test_docker.sh` for container smoke tests.
- `docs/` - Feature docs and fork governance (`redux-manifest.md`, `upstream-intake.md`, `upstream-log.md`, `redux-changes.md`).
- `workspace/` - Runtime agent workspace (not library code, do not commit personal data).

## Build, Test, and Lint Commands

```bash
# Install
pip install -e .              # editable install
pip install -e ".[dev]"       # with test/lint deps (pytest, pytest-asyncio, pytest-cov, ruff)

# Run all tests (from project venv)
source .venv/bin/activate && pytest

# Run a single test file
pytest tests/test_tool_validation.py

# Run a single test function
pytest tests/test_shell_guard.py::test_guard_blocks_destructive_commands_in_prefixed_and_nested_contexts

# Run tests matching a keyword
pytest -k "test_execute_timeout"

# Run with verbose output
pytest -v tests/test_shell_guard.py

# Lint
ruff check .

# Lint with auto-fix
ruff check --fix .

# Docker smoke tests
bash tests/test_docker.sh

# Core line count check
bash core_agent_lines.sh
```

Pytest is configured in `pyproject.toml` with `asyncio_mode = "auto"`, `testpaths = ["tests"]`, and coverage defaults (`--cov=nanobot --cov-report=term-missing --cov-fail-under=80`). CI runs on Python 3.14 only.

## Code Style

### Formatting and Line Length

- **Python 3.14** target. All new code must be type-annotated.
- **4-space indentation**, no tabs.
- **100-character line length** (Ruff setting). `E501` (line-too-long) is ignored in Ruff but aim for 100.
- Ruff lint rules: `E, F, I, N, W`. Config in `pyproject.toml` under `[tool.ruff]`.

### Naming Conventions

- `snake_case` for modules, functions, variables, method names.
- `PascalCase` for classes (e.g., `AgentLoop`, `ExecTool`, `BaseChannel`).
- `UPPER_SNAKE_CASE` for module-level constants (e.g., `USER_AGENT`, `MAX_REDIRECTS`, `BLOCKED_COMMANDS`).
- Private helpers prefixed with `_` (e.g., `_strip_tags`, `_validate_url`, `_make_proc`).

### Import Ordering

Imports are sorted by Ruff `I` (isort) rules in three groups separated by blank lines:
1. Standard library (`asyncio`, `json`, `re`, `os`, `pathlib`, `typing`, `collections.abc`, etc.)
2. Third-party (`httpx`, `loguru`, `pydantic`, `ddgs`, `pytest`, etc.)
3. Local (`nanobot.agent.tools.base`, `nanobot.config.schema`, etc.)

Use `from typing import TYPE_CHECKING` and guard import-only dependencies behind `if TYPE_CHECKING:` blocks to avoid circular imports and reduce runtime overhead.

### Type Annotations

- Use modern Python generics: `dict[str, Any]`, `list[str]`, `str | None` (not `Optional[str]`).
- Use `collections.abc` for abstract types: `Callable`, `Awaitable`, `Sequence`.
- Annotate all function signatures including return types. Test functions return `-> None`.
- Use `@dataclass` for simple data holders (e.g., `ToolCallRequest`, `LLMResponse`).
- Use Pydantic `BaseModel` for config schemas with validation.

### Error Handling

- Tool `execute()` methods return error strings (e.g., `"Error: ..."`) rather than raising exceptions. The agent loop consumes string results.
- Wrap external calls (subprocess, network) in try/except and return descriptive error strings.
- Use `loguru.logger` for warnings and diagnostics (`logger.warning(...)`, `logger.error(...)`).
- Validate inputs early and return error messages rather than letting exceptions propagate silently.
- Pattern: `_guard_command()` returns `None` on success or an error string on block.

### Docstrings

- Keep docstrings short (1-2 sentences), high-signal, focused on side effects and invariants.
- Do not add docstrings for trivial property accessors (`name`, `description`, `parameters`) or obvious magic methods.
- Use `"""One-liner."""` for simple docstrings; multi-line with Args/Returns only for public APIs with non-obvious behavior.

### Classes and Abstractions

- Abstract base classes use `ABC` with `@abstractmethod` (e.g., `Tool`, `LLMProvider`, `BaseChannel`).
- Tools subclass `Tool` and implement `name`, `description`, `parameters` (properties) and `execute(**kwargs) -> str` (async).
- Channels subclass `BaseChannel` and implement `start()`, `stop()`, `send()`.
- Providers subclass `LLMProvider` and implement `chat()`, `get_default_model()`, `get_available_models()`.
- Prefer explicit control flow over framework magic or hidden indirection.

## Testing Conventions

- Files: `tests/test_*.py`. Functions: `test_*`. All return `-> None`.
- Async tests use `@pytest.mark.asyncio` decorator (or rely on `asyncio_mode = "auto"`).
- Use `pytest.mark.parametrize` for data-driven tests (see `test_shell_guard.py`).
- Use `unittest.mock.patch`, `AsyncMock`, `MagicMock`, `monkeypatch` for isolation. No live network calls.
- Use `tmp_path` fixture for filesystem tests.
- Helper factories prefixed with `_make_*` or `_Fake*` classes for test doubles.
- Assert on specific substrings in error messages (e.g., `assert "blocked by safety guard" in result`).

## Commit and PR Guidelines

- Sign commits with GPG (`git commit -S`).
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Scoped forms: `feat(matrix):`.
- Imperative mood, concise titles (< 72 chars).
- Before merging: `ruff check .` and `pytest` must pass.
- Update `docs/redux-changes.md` for fork-specific changes and `docs/upstream-log.md` for upstream adopted, deferred, and rejected intake decisions.

## Fork Documentation — Keeping the Logs Current

These three files must be kept up to date whenever code changes land. Update them **in the same PR** as the code change, not as a follow-up.

### `docs/redux-changes.md`

Add a row to the **Changes** table for every fork-specific change (features, bugfixes, refactors, CI changes) that originates in this repository and is not a direct upstream adoption. Columns: Change, PR/Commit, Area, Why, Risk, Added (YYYY-MM-DD), Verification.

Do **not** add entries for: minor doc edits, workspace content, style-only formatting, or changes that are pure upstream cherry-picks (those go in `upstream-log.md`).

### `docs/upstream-log.md`

Add a row to the **Adopted Changes** table for every upstream commit or PR cherry-picked into this fork. Record: upstream PR/commit link, area, why adopted, risk, date, and verification command. When a change is partially adopted, note which parts were excluded and why. When upstream changes are evaluated but not adopted, record them in the **Deferred** or **Rejected** table with a brief reason.

### `README.md`

Keep the **"What This Fork Adds"** section current:

- Add a bullet for every new user-visible feature or behaviour change merged to `main`.
- Update or remove bullets when features are removed or substantially changed.
- The **"Real-time line count"** line (`📏 Real-time line count: X lines`) must be updated whenever the core agent line count changes materially. Run `bash core_agent_lines.sh` to get the current count.
- Do **not** add bullets for: internal refactors with no user-visible effect, CI-only changes, or doc-only changes.

## Upstream Intake and Fork Documentation

- For upstream adoption work, follow `docs/upstream-intake.md`.
- Evaluate candidates against `docs/redux-manifest.md` criteria: testability, practical need, risk, compatibility.
- Prefer selective cherry-picks over broad merges.
- Use `git cherry-pick` so the source commit stays traceable in git history.
- When upstream diffs conflict or need adaptation, use `git cherry-pick -n <sha>`, resolve, then commit.
- For each adopted upstream change, record link, area, rationale, risk, date, and verification in `docs/upstream-log.md`.
- For deferred/rejected upstream changes, record concise reasons in `docs/upstream-log.md`.
- When preparing a release, use `docs/release-template.md`.

## Security

- Never commit API keys or secrets. Keep them in `~/.nanobot/config.json`.
- Do not commit personal runtime data from `workspace/`.
- For production, enable `tools.restrictToWorkspace` in config.

## MCP Tools

Always use Context7 MCP for library/API documentation without being asked.

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
| Matrix Nio           | `/matrix-nio/matrix-nio`               |
| Matrix Specification | `/websites/spec_matrix`                 |
