# Performance Analysis: nanobot-redux

**Date:** 2026-02-20
**Branch:** `claude/analyze-performance-options-URI5W`
**Scope:** Core agent loop, context building, session persistence, web tools, provider layer

---

## Executive Summary

The codebase is already well-structured for an async-first design. Most bottlenecks are in three
categories: (1) repeated disk reads on every LLM call, (2) sequential tool execution where
parallelism is safe, and (3) per-request HTTP client construction that discards connection pools.
No architectural rewrites are needed — the improvements are surgical and low-risk.

---

## Bottleneck Inventory

### B1 — Sequential Tool Execution (`agent/loop.py:232`)

```python
for tool_call in response.tool_calls:
    result = await self.tools.execute(tool_call.name, tool_call.arguments)
```

The agent loop executes all tool calls from a single LLM response one after another. When the LLM
returns multiple independent tool calls (e.g., `web_search` + `read_file`), total latency is the
**sum** of each tool's latency, not the maximum.

**Impact:** High. Multi-tool responses are common. Each tool call can take 1–30 seconds (web,
exec). With 3 parallel-safe calls, a 10 s total becomes 30 s.

**Mitigation options:**

| Option | Approach | Tradeoff |
|---|---|---|
| A — `asyncio.gather` all | Run all tool calls concurrently | Simple; may interleave tool side-effects (e.g., two writes to same file) |
| B — Sequential by default, `gather` opt-in | Mark tools as `parallel_safe`; gather only those | Safer; requires metadata per tool |
| C — Parallel with result ordering | Use `asyncio.gather`, collect results, apply to messages in call-order | Best UX; slightly more complex |

**Recommendation:** Option C. Tool results must be appended to messages in the same order as
`tool_calls` to satisfy OpenAI API semantics. Gather with index-preserving collect is safe.

---

### B2 — System Prompt Rebuilt from Disk Every Call (`agent/context.py:29`)

```python
def build_system_prompt(self, skill_names=None) -> str:
    parts.append(self._get_identity())          # platform calls
    bootstrap = self._load_bootstrap_files()    # disk I/O
    memory = self.memory.get_memory_context()   # disk I/O
    always_skills = self.skills.get_always_skills()  # disk I/O
    skills_summary = self.skills.build_skills_summary()  # disk I/O
```

Every call to `build_messages()` → `build_system_prompt()` reads up to 6 files from disk:
`AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `IDENTITY.md`, `MEMORY.md`. The platform identity
section also calls `platform.system()`, `platform.machine()`, `platform.python_version()` which
are constant for the lifetime of the process.

**Impact:** Medium. Each agent loop iteration that calls the LLM triggers one full file-system
scan. On SSDs this is ~1–5 ms per file, but under load or slow NFS mounts it is much higher.
More importantly, it inflates token counts with identical content on every iteration.

**Mitigation options:**

| Option | Approach | Tradeoff |
|---|---|---|
| A — Module-level constants for platform info | Cache `platform.*` results at import time | Zero cost; no invalidation needed |
| B — TTL cache on `build_system_prompt` | Cache for N seconds; invalidate on MEMORY.md mtime change | Simple; memory.md changes respected |
| C — Explicit invalidation | Call `context.invalidate()` after `/new` or memory consolidation | Precise; requires discipline at call sites |
| D — LLM prompt caching (provider-side) | Use Anthropic/OpenAI cache-control headers on system prompt | Reduces API latency and costs; provider-dependent |

**Recommendation:** A (immediate, free) + B with a 30-second TTL for bootstrap/skills, +
invalidation after memory consolidation. Option D is orthogonal and recommended for production
deployments using supported providers.

---

### B3 — Session JSONL Rewrite on Every Save (`session/manager.py:142`)

```python
def save(self, session: Session) -> None:
    with open(path, "w") as f:       # truncates and rewrites entire file
        f.write(json.dumps(metadata_line) + "\n")
        for msg in session.messages:
            f.write(json.dumps(msg) + "\n")
```

The `Session` docstring explicitly states: *"Messages are append-only for LLM cache efficiency."*
However, `save()` truncates and rewrites the complete file every time. For a session with 200
messages, every save serializes and writes all 200 records even though only 1 is new.

**Impact:** Medium. Grows linearly with session length. At 200 messages × ~500 bytes each =
100 KB rewrite per message exchange. Also holds the GIL during JSON serialization of the full list.

**Mitigation options:**

| Option | Approach | Tradeoff |
|---|---|---|
| A — True append-only writes | Track `_saved_count`; open with `"a"` and write only new messages | Aligns with stated design intent; metadata requires rewrite on close/new |
| B — Periodic full rewrite | Append normally; rewrite only on session close or `/new` | Good balance; metadata stays accurate |
| C — SQLite backend | Replace JSONL with SQLite for atomic appends and indexed queries | More robust; harder to grep manually |

**Recommendation:** Option A. The session key is already tracked (`last_consolidated`). Adding
`_saved_count: int = 0` to `Session` and switching `save()` to append mode for new messages
respects the existing design intent with minimal change. The metadata line must still be updated
on close; a `flush_metadata()` method suffices.

---

### B4 — Per-Request HTTP Client Construction (`agent/tools/web.py:125`)

```python
async with httpx.AsyncClient(transport=self._transport) as client:
    r = await client.get(...)
```

Both `WebFetchTool` and `WebSearchTool` create a new `httpx.AsyncClient` on every call. HTTPX
clients maintain a connection pool; creating one per request bypasses pooling entirely, causing a
fresh TCP handshake (and TLS negotiation) on every search or fetch.

**Impact:** Medium. Each TLS handshake adds 50–300 ms. For web-heavy workflows (multiple searches
per agent turn), this is measurable.

**Mitigation options:**

| Option | Approach | Tradeoff |
|---|---|---|
| A — Shared client as instance attribute | Create `AsyncClient` once in `__init__`; reuse across calls | Simple; connection pool works; requires explicit close |
| B — Module-level shared client | Single global client for all web tools | Simpler lifecycle; no per-tool state |
| C — `AsyncClient` with `limits` tuned | Keep per-request but increase keep-alive | Reduces benefit; still no reuse across calls |

**Recommendation:** Option A. Add `self._client: httpx.AsyncClient` to `__init__`, use it in
`execute()`, and close it in a `close()` / `__aexit__` method. The `AgentLoop` already has an
`AsyncExitStack` (for MCP) that can manage this lifecycle cleanly.

---

### B5 — Tool Definitions Recomputed on Every LLM Call (`agent/loop.py:199`)

```python
response = await self.provider.chat(
    ...
    tools=self.tools.get_definitions(),   # called every iteration
    ...
)
```

`ToolRegistry.get_definitions()` iterates all registered tools and serializes their parameter
schemas each time. If tools are registered once and never change (which is the common case), this
is wasted work on every iteration of the agent loop.

**Impact:** Low. Pure Python computation, typically < 1 ms. Worth a one-liner fix but not urgent.

**Mitigation:** Cache `get_definitions()` result on first call; invalidate on `register()`.

---

### B6 — Memory Consolidation Always Creates a New `MemoryStore` (`agent/loop.py:416`)

```python
async def _consolidate_memory(self, session, archive_all=False) -> None:
    memory = MemoryStore(self.workspace)   # new instance every call
```

`MemoryStore.__init__` calls `ensure_dir()` (which calls `Path.mkdir(parents=True, exist_ok=True)`)
on every invocation. The `AgentLoop` already has `self.context.memory` (a `MemoryStore`) that
could be reused.

**Impact:** Low. `mkdir` with `exist_ok=True` is a syscall, but fast. The real waste is the
redundant object allocation and potential for split state between two `MemoryStore` instances.

**Mitigation:** Replace `memory = MemoryStore(self.workspace)` with `memory = self.context.memory`.

---

## Provider-Level Opportunities

### P1 — Prompt Caching (Anthropic / OpenAI)

For providers that support cache-control (Anthropic's `cache_control: {"type": "ephemeral"}`),
marking the system prompt and long conversation history as cacheable can reduce input token costs
by up to 90% and latency by up to 85% on repeated calls with the same prefix.

**Applicability:** High for long-running sessions. Zero code risk — purely additive headers.
**Implementation:** Add optional `use_prompt_cache: bool` to provider config; set
`cache_control` on the system message and last few history turns.

### P2 — Model Selection for Memory Consolidation (`agent/loop.py:462`)

```python
response = await self.provider.chat(
    ...
    model=self.model,   # same model as main agent
)
```

Memory consolidation uses the same (potentially large/expensive) model as the main agent.
A smaller, cheaper model (e.g., `gpt-4o-mini` or `claude-haiku`) is more than sufficient for the
JSON summarization task and costs 10–20× less.

**Mitigation:** Add `memory_model: str | None` to `AgentLoop.__init__`; fall back to `self.model`
if not set.

---

## Startup Time

The `matrix-nio[e2e]` dependency includes Olm cryptography bindings that take ~150–300 ms to
import on first use. The channel is already lazy-imported (not in `__init__.py`), but
`from nanobot.channels.matrix import MatrixChannel` in the CLI triggers it at startup even when
no Matrix config is present.

**Mitigation:** Guard Matrix import behind a config check in the CLI; only import when
`config.matrix.enabled` is true.

---

## Summary Table

| ID | Area | Impact | Effort | Priority |
|----|------|--------|--------|----------|
| B1 | Parallel tool execution | High | Medium | P1 |
| B2a | Cache platform identity | Medium | Trivial | P1 |
| B2b | Cache system prompt (TTL) | Medium | Low | P1 |
| B3 | Append-only session writes | Medium | Low | P2 |
| B4 | Reuse HTTP client | Medium | Low | P2 |
| P1 | LLM prompt caching | High (cost) | Low | P2 |
| P2 | Smaller model for memory | Medium (cost) | Trivial | P2 |
| B5 | Cache tool definitions | Low | Trivial | P3 |
| B6 | Reuse MemoryStore instance | Low | Trivial | P3 |
| S1 | Lazy Matrix import | Low | Low | P3 |

---

## Not Recommended

- **LRU cache on LLM responses:** Identical LLM inputs are rare in practice; caching would add
  memory pressure with negligible hit rate.
- **SQLite session backend (B3-C):** Breaks the "grep-searchable JSONL" design principle from
  the redux manifest without sufficient benefit at the current scale.
- **Rewriting to use `uvloop`:** The event loop is already async-first; `uvloop` only helps under
  very high concurrency. Not worth the extra C dependency at this scale.
