# Contributing to nanobot redux

Thanks for your interest in contributing! This document explains how this fork works and what to expect when contributing.

## About This Fork

**nanobot redux** is an opinionated fork maintained for personal needs and workflows. I adopt upstream changes selectively and focus on features I can actually use and test.

## What Gets Accepted

I'll integrate contributions that:

- **I can test myself**: I need to be able to verify the feature works. For example, I won't merge support for chat platforms I don't have access to.
- **Solve real problems**: Features that address practical, daily workflows are prioritized over theoretical use cases.
- **Fit the philosophy**: Keep things stable, debuggable, self-hostable, and secure.
- **I'm willing to maintain**: If I can't support it long-term, I probably won't merge it.

If you need something I can't test, consider maintaining your own fork—that's totally fine and encouraged!

## Development Setup

### Prerequisites

- Python 3.11+
- A virtual environment tool (venv, virtualenv, etc.)

### Getting Started

```bash
# Clone the repository
git clone https://github.com/Athemis/nanobot-redux.git
cd nanobot-redux

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Initialize local config and workspace
nanobot onboard

# Run tests
pytest
ruff check .
```

## Coding Style

### General Guidelines

- **Python version**: Target Python 3.11+
- **Type hints**: Use type annotations for new code
- **Indentation**: 4 spaces (no tabs)
- **Naming conventions**:
  - `snake_case` for modules, functions, variables
  - `PascalCase` for classes
- **Line length**: 100 characters max
- **Linting**: Follow Ruff settings in `pyproject.toml` (rules: E, F, I, N, W)

### Code Organization

- Keep features in the matching package:
  - Channel logic → `nanobot/channels/`
  - Provider logic → `nanobot/providers/`
  - Tools → `nanobot/tools/`
- Prefer explicit, readable code over framework-style indirection
- No hidden magic or overly clever abstractions

## Testing

### Running Tests

```bash
# Activate your virtual environment first
source .venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_something.py

# Run with coverage
pytest --cov=nanobot

# Lint checks
ruff check .
```

### Writing Tests

- Use `pytest` with `pytest-asyncio` for async code
- Test files: `tests/test_*.py`
- Test functions: `test_*`
- Prefer deterministic unit tests with mocks over live network calls
- Add tests for behavior changes, especially:
  - Tool validation
  - Channel handling
  - Provider routing

### Docker Testing

```bash
bash tests/test_docker.sh
```

## Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <description>

[optional body]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no behavior change)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(matrix): add support for encrypted rooms
fix(email): handle IMAP connection timeout
docs: update web search provider setup
refactor(tools): simplify file validation logic
feat: add SearXNG web search provider
```

### Guidelines

- Use imperative mood ("add feature" not "added feature")
- Keep title concise (< 72 chars)
- Include scope when relevant (e.g., `email`, `matrix`, `tools`)
- Add body for complex changes

## Pull Requests

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass: `pytest`
- [ ] Linting passes: `ruff check .`
- [ ] Relevant tests added or updated
- [ ] Documentation updated if needed

### PR Description Should Include

1. **Summary**: What does this change?
2. **Motivation**: Why is this needed?
3. **Testing**: How did you verify it works?
   - Test commands run
   - Manual testing performed
   - Edge cases considered
4. **Related Issues**: Link any relevant issues

### Example PR Template

```markdown
## Summary
Adds support for SearXNG as a web search provider.

## Motivation
Allows using self-hosted search instances for privacy and control.

## Testing
- Added unit tests for SearXNG provider
- Ran `pytest` - all pass
- Ran `ruff check .` - no issues
- Tested with local SearXNG instance at http://localhost:8080
- Verified fallback to DuckDuckGo when SearXNG unavailable

## Related Issues
Closes #123
```

## Configuration & Documentation

- Update `docs/` when changing CLI behavior or adding features
- Update config examples when adding new settings
- Keep `docs/web-search.md` style for new feature docs
- Don't commit secrets or personal runtime data

## Questions?

- Check existing docs: `docs/redux-manifest.md`, `docs/upstream-intake.md`
- Open a discussion issue before starting large changes
- Remember: contributions are welcome, but I can only merge what I can test and maintain

Thanks for contributing! 🎉
