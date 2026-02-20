# Performance Work — Continuation Index

**Analysis completed:** 2026-02-20
**Branch:** `claude/analyze-performance-options-URI5W`
**Analysis document:** [`docs/performance-analysis.md`](../performance-analysis.md)

Each bottleneck has its own work file with full context, exact change locations, test requirements,
and a copy-paste prompt that lets a fresh session pick up the work immediately.

---

## Bottleneck Overview

| ID | File | Priority | Effort | Status |
|----|------|----------|--------|--------|
| [B1](./B1-parallel-tool-execution.md) | Parallel tool execution | P1 — High | Medium | open |
| [B2a](./B2a-cache-platform-identity.md) | Cache platform identity | P1 — Trivial | Trivial | open |
| [B2b](./B2b-cache-system-prompt.md) | System-prompt TTL cache | P1 — Medium | Low | open |
| [B3](./B3-session-append-only.md) | Session JSONL append-only | P2 — Medium | Low | open |
| [B4](./B4-http-client-pooling.md) | HTTP client pooling | P2 — Medium | Low | open |
| [B5](./B5-cache-tool-definitions.md) | Cache tool definitions | P3 — Low | Trivial | open |
| [B6](./B6-reuse-memory-store.md) | Reuse MemoryStore instance | P3 — Low | Trivial | open |
| [P1](./P1-llm-prompt-caching.md) | LLM prompt caching | P2 — High (cost) | Low | open |
| [P2](./P2-memory-model-selection.md) | Smaller model for memory | P2 — Medium (cost) | Trivial | open |
| [S1](./S1-lazy-matrix-import.md) | Lazy Matrix import | P3 — Low | Low | open |

---

## Recommended Order

1. **B2a** (5 min, zero risk) — Module-level constants for platform info
2. **B6** (5 min, zero risk) — Reuse the existing MemoryStore instance
3. **B5** (10 min, zero risk) — Cache tool definitions
4. **P2** (15 min, low risk) — Smaller model for memory consolidation
5. **B2b** (30 min, low risk) — TTL cache for system prompt
6. **S1** (20 min, low risk) — Lazy Matrix import in CLI
7. **B3** (45 min, medium risk) — True append-only JSONL writes
8. **B4** (45 min, medium risk) — HTTP client connection pooling
9. **B1** (2–4 h, medium risk) — Parallel tool execution
10. **P1** (1–2 h, provider-dependent) — LLM prompt caching

---

## Shared Session Context

When starting a fresh session, this context is relevant:

- **Repo:** `/home/user/nanobot-redux`
- **Branch:** `claude/analyze-performance-options-URI5W`
- **Core files:** `nanobot/agent/loop.py`, `nanobot/agent/context.py`,
  `nanobot/session/manager.py`, `nanobot/agent/tools/web.py`,
  `nanobot/agent/tools/registry.py`
- **Run tests:** `source .venv/bin/activate && pytest`
- **Lint:** `ruff check .`
- **Style:** Python 3.14, type annotations everywhere, 100-char line limit, `snake_case`
- **Commits:** GPG-signed (`git commit -S`), Conventional Commits (`feat:`, `fix:`, `refactor:`)
- **Push to:** `git push -u origin claude/analyze-performance-options-URI5W`
