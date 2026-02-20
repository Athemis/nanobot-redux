<!--
  Issue template: Enhancement
  Title (copy into the issue title field):
    perf(cli): lazy-import MatrixChannel behind config check
  Labels: performance, enhancement
-->

## Problem / motivation

`matrix-nio[e2e]` includes Olm cryptography C bindings that take 150–300 ms to import on
first load. This cost is paid on **every `nanobot` CLI invocation** — including `nanobot --help`
and `nanobot ask "..."` — even when no Matrix configuration is present and the Matrix channel
is never used.

For users who run `nanobot` frequently from the command line (e.g. in scripts or shell
aliases), this cold-start penalty is consistently noticeable.

## Proposed solution

Guard the `MatrixChannel` import behind a config check so it is only loaded when Matrix is
actually configured:

```python
# Before (unconditional import at module level or startup):
from nanobot.channels.matrix import MatrixChannel
channel_manager.register(MatrixChannel(config))

# After:
if config.matrix and config.matrix.enabled:
    from nanobot.channels.matrix import MatrixChannel   # deferred import
    channel_manager.register(MatrixChannel(config))
```

If `MatrixChannel` is used only as a type annotation, use a `TYPE_CHECKING` guard instead
(zero runtime import).

The exact import location must be confirmed by searching:
```
grep -rn "MatrixChannel\|nanobot.channels.matrix" nanobot/
```

Full implementation plan: [`docs/perf/S1-lazy-matrix-import.md`](../S1-lazy-matrix-import.md)

## Alternatives considered

- **Remove `matrix-nio` from the default install** — would require a separate
  `pip install nanobot[matrix]` extra; higher friction for existing Matrix users.
- **Accept the overhead** — only viable if CLI invocations are rare; contradicted by the
  project's stated goal of fast startup and low resource usage.

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../../redux-manifest.md).
