# CI Code Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `pytest-cov` to the dev dependencies and configure pytest to measure coverage on every run, failing the build if total coverage drops below 63%.

**Architecture:** All configuration lives in `pyproject.toml` — `pytest-cov` as a dev dependency, `addopts` in `[tool.pytest.ini_options]` to inject coverage flags automatically. No changes to the CI workflow file are needed.

**Tech Stack:** pytest, pytest-cov

---

### Task 1: Add pytest-cov as dev dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Open the file and locate the dev extras block**

In `pyproject.toml` find:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
]
```

**Step 2: Add pytest-cov**

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
]
```

**Step 3: Add addopts to pytest config**

Locate `[tool.pytest.ini_options]` and add `addopts`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=nanobot --cov-report=term-missing --cov-fail-under=63"
```

**Step 4: Install updated dev dependencies**

Run: `pip install -e ".[dev]"`
Expected: `Successfully installed pytest-cov-...`

**Step 5: Run pytest to verify coverage report appears and passes**

Run: `pytest`
Expected: coverage table printed at end, `TOTAL ... 63%` or higher, exit code 0.

**Step 6: Commit**

```bash
git add pyproject.toml
git commit -S -m "feat(ci): add pytest-cov with 63% coverage threshold"
```
