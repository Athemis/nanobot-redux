"""Memory system for persistent agent memory."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from nanobot.utils.helpers import ensure_dir

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider
    from nanobot.session.manager import Session


_SAVE_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save the memory consolidation result to persistent storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "history_entry": {
                        "type": "string",
                        "description": "A paragraph (2-5 sentences) summarizing key events/decisions/topics. Start with a timestamp like [YYYY-MM-DD HH:MM]. Include enough detail to be useful when found by grep search later.",
                    },
                    "memory_update": {
                        "type": "string",
                        "description": "The full updated long-term memory content as a markdown string. Include all existing facts plus any new facts: user location, preferences, personal info, habits, project context, technical decisions, tools/services used. If nothing new, return the existing content unchanged.",
                    },
                },
                "required": ["history_entry", "memory_update"],
            },
        },
    }
]


class MemoryStore:
    """Two-layer memory: MEMORY.md (long-term facts) + HISTORY.md (grep-searchable log)."""

    def __init__(self, workspace: Path):
        """Initialize memory file locations under `<workspace>/memory`."""
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"

    def read_long_term(self) -> str:
        """Read `MEMORY.md`; return an empty string when the file is missing."""
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        """Overwrite `MEMORY.md` with the provided long-term memory content."""
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:
        """Append one entry to `HISTORY.md`, normalized to a blank-line separator."""
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:
        """Return formatted long-term memory text suitable for prompt injection."""
        long_term = self.read_long_term()
        return f"## Long-term Memory\n{long_term}" if long_term else ""

    async def consolidate(
        self,
        session: "Session",
        provider: "LLMProvider",
        model: str,
        *,
        archive_all: bool = False,
        memory_window: int = 50,
        prompt_cache_key: str | None = None,
    ) -> bool:
        """Consolidate session history into MEMORY.md and HISTORY.md."""
        snapshot_len = len(session.messages)
        if archive_all:
            old_messages = session.messages
            keep_count = 0
            logger.info(
                "Memory consolidation (archive_all): {} total messages archived",
                len(session.messages),
            )
        else:
            keep_count = memory_window // 2
            if len(session.messages) <= keep_count:
                logger.debug(
                    "Session {}: No consolidation needed (messages={}, keep={})",
                    session.key,
                    len(session.messages),
                    keep_count,
                )
                return True

            messages_to_process = len(session.messages) - session.last_consolidated
            if messages_to_process <= 0:
                logger.debug(
                    "Session {}: No new messages to consolidate (last_consolidated={}, total={})",
                    session.key,
                    session.last_consolidated,
                    len(session.messages),
                )
                return True

            snapshot_len = len(session.messages)
            end_index = snapshot_len - keep_count
            old_messages = session.messages[session.last_consolidated : end_index]
            if not old_messages:
                return True
            logger.info(
                "Memory consolidation started: {} total, {} new to consolidate, {} keep",
                len(session.messages),
                len(old_messages),
                keep_count,
            )

        lines: list[str] = []
        for msg in old_messages:
            if not msg.get("content"):
                continue
            tools = f" [tools: {', '.join(msg['tools_used'])}]" if msg.get("tools_used") else ""
            lines.append(
                f"[{msg.get('timestamp', '?')[:16]}] {msg['role'].upper()}{tools}: {msg['content']}"
            )
        conversation = "\n".join(lines)
        current_memory = self.read_long_term()

        prompt = f"""Process this conversation and call the save_memory tool with your consolidation.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{conversation}"""

        try:
            response = await provider.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a memory consolidation agent. Call the save_memory tool with your consolidation of the conversation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                tools=_SAVE_MEMORY_TOOL,
                model=model,
                prompt_cache_key=prompt_cache_key,
            )
            if not response.has_tool_calls:
                logger.warning("Memory consolidation: LLM did not call save_memory tool, skipping")
                return False

            call = response.tool_calls[0]
            if call.name != "save_memory":
                logger.warning("Memory consolidation: unexpected tool '{}', skipping", call.name)
                return False

            result: dict[str, Any] = call.arguments
            if entry := result.get("history_entry"):
                if not isinstance(entry, str):
                    entry = json.dumps(entry, ensure_ascii=False)
                self.append_history(entry)
            if update := result.get("memory_update"):
                if not isinstance(update, str):
                    update = json.dumps(update, ensure_ascii=False)
                if update != current_memory:
                    self.write_long_term(update)

            if archive_all:
                session.last_consolidated = 0
            else:
                session.last_consolidated = snapshot_len - keep_count
            logger.info(
                "Memory consolidation done: {} messages, last_consolidated={}",
                len(session.messages),
                session.last_consolidated,
            )
            return True
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")
            return False
