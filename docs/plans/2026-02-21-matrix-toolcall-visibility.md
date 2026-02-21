# Matrix Tool-Call Visibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Matrix tool-call progress hints explicitly configurable via schema-backed channel settings.

**Architecture:** Agent loop tags bus-published progress messages with a structured kind (`reasoning` vs `tool_hint`). Matrix channel decides visibility using config + progress metadata instead of content regex parsing. This keeps the filtering concern in `matrix.py` while preserving progress behavior for other channels.

**Tech Stack:** Python 3.14, Pydantic config schema, pytest, ruff.

---

## Task 1: Add failing tests for structured progress kinds and Matrix filtering

**Files:**
- Modify: `tests/test_on_progress.py`
- Modify: `tests/test_matrix_channel.py`

**Step 1: Write the failing tests**

```python
def test_bus_progress_sets_progress_kind(...):
    assert metadata["_progress_kind"] == "tool_hint"

def test_send_keeps_reasoning_progress_when_filter_enabled(...):
    assert len(client.room_send_calls) == 1
```

**Step 2: Run tests to verify RED**

Run: `python -m pytest --no-cov -q tests/test_on_progress.py::test_bus_progress_sets_progress_metadata tests/test_matrix_channel.py::test_send_filters_progress_tool_hint_when_enabled tests/test_matrix_channel.py::test_send_keeps_reasoning_progress_when_filter_enabled`
Expected: FAIL because `_progress_kind` is not produced/used yet.

## Task 2: Implement metadata-based progress typing and Matrix config behavior

**Files:**
- Modify: `nanobot/agent/loop.py`
- Modify: `nanobot/channels/matrix.py`
- Modify: `nanobot/config/schema.py`

**Step 1: Add minimal implementation**

```python
# loop.py
meta["_progress_kind"] = kind

# matrix.py
if config_flag and metadata["_progress"] and metadata.get("_progress_kind") == "tool_hint":
    return
```

**Step 2: Keep schema-backed option in Matrix config**

```python
show_progress_tool_calls: bool = True
```

Map behavior so hidden tool-call hints are only Matrix-specific.

## Task 3: Verify, document, commit, and open PR

**Files:**
- Modify: `README.md`
- Modify: `docs/redux-changes.md`

**Step 1: Run verification**

Run: `python -m ruff check nanobot/agent/loop.py nanobot/channels/matrix.py nanobot/config/schema.py tests/test_on_progress.py tests/test_matrix_channel.py`
Expected: PASS

Run: `python -m pytest --no-cov -q tests/test_on_progress.py tests/test_matrix_channel.py`
Expected: PASS

**Step 2: Commit**

```bash
git add docs/plans/2026-02-21-matrix-toolcall-visibility.md \
  nanobot/agent/loop.py nanobot/channels/matrix.py nanobot/config/schema.py \
  tests/test_on_progress.py tests/test_matrix_channel.py README.md docs/redux-changes.md
git commit -m "feat(matrix): make tool-call progress visibility configurable"
```
