# Codex Reasoning Streaming Design

## Goal

Add Codex reasoning support that both persists in `LLMResponse.reasoning_content` and streams live
progress updates, while keeping Matrix typing indicators reliable for all models (including models
without reasoning output).

## Scope

- Extend Codex SSE parsing to aggregate reasoning text alongside normal output text.
- Return aggregated reasoning in `LLMResponse.reasoning_content`.
- Forward reasoning deltas through the existing progress path (`on_progress` and bus updates).
- Refine Matrix typing behavior with a phase-aware policy that still falls back to current
  keepalive behavior when reasoning is absent.

Out of scope:

- New Matrix protocol states (Matrix typing is still on/off only).
- Provider-wide config redesign for reasoning verbosity.
- UI redesign for CLI progress output.

## Current Baseline

- `OpenAIProvider` already maps `message.reasoning_content` into `LLMResponse.reasoning_content`.
- `OpenAICodexProvider` requests `reasoning.encrypted_content` but does not surface reasoning in
  `LLMResponse`.
- `AgentLoop` already has a progress callback pipeline used by CLI and bus channels.
- Matrix typing currently uses a keepalive loop and stop-on-send semantics.

## Chosen Approach (A: Delta-based)

Use incremental SSE event handling in Codex provider:

1. Collect reasoning deltas in a dedicated buffer.
2. Keep normal output text and tool-call parsing logic intact.
3. Emit reasoning deltas into the existing progress callback path.
4. Persist final aggregated reasoning into `LLMResponse.reasoning_content`.

This keeps changes narrow, preserves existing behavior for non-reasoning models, and avoids a
large parser rewrite.

## Data Flow

1. `OpenAICodexProvider.chat(...)` prepares the request and invokes `_request_codex(...)`.
2. `_consume_sse(...)` parses SSE events:
   - output text deltas -> `content` buffer
   - reasoning deltas -> `reasoning_buffer`
   - function call events -> tool-call structures
3. Reasoning delta callback (if provided) forwards text to agent progress channel in near real-time.
4. Final return includes `content`, `tool_calls`, `finish_reason`, and `reasoning_content`.
5. `AgentLoop` stores reasoning content in context exactly as it already does for other providers.

## Matrix Typing Policy

Typing indicators must work for all models, with or without reasoning:

- Base behavior stays unchanged: start keepalive when processing starts, stop when response is sent.
- Reasoning/activity events can refine timing but never gate typing on/off correctness.
- If no reasoning events exist (or reasoning disabled), fallback remains current keepalive-only flow.

This guarantees no regression for non-reasoning providers.

## Error Handling and Compatibility

- Unknown reasoning event shapes are ignored safely.
- Missing reasoning data results in `reasoning_content=None` without failing the request.
- Existing tool-call parsing and finish-reason mapping remain backward compatible.
- Progress callback failures should not abort model response handling.

## Verification Strategy

- Provider tests for reasoning aggregation and mixed output/tool streams.
- Agent loop tests for forwarding streamed reasoning progress.
- Matrix channel tests for typing fallback behavior when reasoning is absent.
- Regression pass for existing codex generation-parameter tests.

## Acceptance Criteria

- Codex responses populate `LLMResponse.reasoning_content` when reasoning is present.
- Live reasoning updates appear via existing progress plumbing.
- Matrix typing behavior remains correct for reasoning and non-reasoning models.
- All targeted tests pass without breaking existing behavior.
