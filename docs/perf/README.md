# Performance Work — Issue Tracker

**Analysis completed:** 2026-02-20
**Branch:** `claude/analyze-performance-options-URI5W`
**Analysis document:** [`docs/performance-analysis.md`](../performance-analysis.md)
**Tracking issue:** [#60](https://github.com/Athemis/nanobot-redux/issues/60)

All implementation plans live in GitHub issues. Each issue is independently actionable and
contains a self-contained plan with code, tests, and a session prompt.

---

## Bottleneck Overview

| ID | Issue | Priority | Effort |
|----|-------|----------|--------|
| B1 | [#50 — Parallel tool execution](https://github.com/Athemis/nanobot-redux/issues/50) | P1 | Medium |
| B2a | [#51 — Cache platform identity](https://github.com/Athemis/nanobot-redux/issues/51) | P1 | Trivial |
| B2b | [#52 — System-prompt TTL cache](https://github.com/Athemis/nanobot-redux/issues/52) | P1 | Low |
| B3 | [#53 — Session JSONL append-only](https://github.com/Athemis/nanobot-redux/issues/53) | P2 | Low |
| B4 | [#54 — HTTP client pooling](https://github.com/Athemis/nanobot-redux/issues/54) | P2 | Low |
| B5 | [#55 — Cache tool definitions](https://github.com/Athemis/nanobot-redux/issues/55) | P3 | Trivial |
| B6 | [#56 — Reuse MemoryStore instance](https://github.com/Athemis/nanobot-redux/issues/56) | P3 | Trivial |
| P1 | [#57 — LLM prompt caching](https://github.com/Athemis/nanobot-redux/issues/57) | P2 | Low |
| P2 | [#58 — Smaller model for memory](https://github.com/Athemis/nanobot-redux/issues/58) | P2 | Trivial |
| S1 | [#59 — Lazy Matrix import](https://github.com/Athemis/nanobot-redux/issues/59) | P3 | Low |
