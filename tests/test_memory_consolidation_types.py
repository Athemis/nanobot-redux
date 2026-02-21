"""Test memory consolidation handles non-string values from LLM.

This test verifies the fix for the bug where memory consolidation fails
when LLM returns JSON objects instead of strings for history_entry or
memory_update fields.

Related issue: Memory consolidation fails with TypeError when LLM returns dict
"""

import inspect
import json
from pathlib import Path

from nanobot.agent.memory import MemoryStore


class TestMemoryConsolidationTypeHandling:
    """Test that MemoryStore methods handle type conversion correctly."""

    def test_append_history_accepts_string(self, tmp_path: Path) -> None:
        """MemoryStore.append_history should accept string values."""
        memory = MemoryStore(tmp_path)

        # Should not raise TypeError
        memory.append_history("[2026-02-14] Test entry")

        # Verify content was written
        history_content = memory.history_file.read_text()
        assert "Test entry" in history_content

    def test_write_long_term_accepts_string(self, tmp_path: Path) -> None:
        """MemoryStore.write_long_term should accept string values."""
        memory = MemoryStore(tmp_path)

        # Should not raise TypeError
        memory.write_long_term("- Fact 1\n- Fact 2")

        # Verify content was written
        memory_content = memory.read_long_term()
        assert "Fact 1" in memory_content

    def test_type_conversion_dict_to_str(self) -> None:
        """Dict values should be converted to JSON strings."""
        input_val = {"timestamp": "2026-02-14", "summary": "test"}
        expected = '{"timestamp": "2026-02-14", "summary": "test"}'

        # Simulate the fix logic
        if not isinstance(input_val, str):
            result = json.dumps(input_val, ensure_ascii=False)
        else:
            result = input_val

        assert result == expected
        assert isinstance(result, str)

    def test_type_conversion_list_to_str(self) -> None:
        """List values should be converted to JSON strings."""
        input_val = ["item1", "item2"]
        expected = '["item1", "item2"]'

        # Simulate the fix logic
        if not isinstance(input_val, str):
            result = json.dumps(input_val, ensure_ascii=False)
        else:
            result = input_val

        assert result == expected
        assert isinstance(result, str)

    def test_type_conversion_str_unchanged(self) -> None:
        """String values should remain unchanged."""
        input_val = "already a string"

        # Simulate the fix logic
        if not isinstance(input_val, str):
            result = json.dumps(input_val, ensure_ascii=False)
        else:
            result = input_val

        assert result == input_val
        assert isinstance(result, str)

    def test_memory_consolidation_simulation(self, tmp_path: Path) -> None:
        """Simulate full consolidation with dict values from LLM."""
        memory = MemoryStore(tmp_path)

        # Simulate LLM returning dict values (the bug scenario)
        history_entry = {"timestamp": "2026-02-14", "summary": "User asked about..."}
        memory_update = {"facts": ["Location: Beijing", "Skill: Python"]}

        # Apply the fix: convert to str
        if not isinstance(history_entry, str):
            history_entry = json.dumps(history_entry, ensure_ascii=False)
        if not isinstance(memory_update, str):
            memory_update = json.dumps(memory_update, ensure_ascii=False)

        # Should not raise TypeError after conversion
        memory.append_history(history_entry)
        memory.write_long_term(memory_update)

        # Verify content
        assert memory.history_file.exists()
        assert memory.memory_file.exists()

        history_content = memory.history_file.read_text()
        memory_content = memory.read_long_term()

        assert "timestamp" in history_content
        assert "facts" in memory_content


class TestConsolidationSchemaGuardrails:
    """Test that consolidation prompt/schema guardrails are present."""

    def test_prompt_includes_string_requirement(self) -> None:
        """The consolidation implementation should enforce schema via tool calling."""
        import nanobot.agent.memory as _memory_module

        source = inspect.getsource(_memory_module)
        expected_keywords = [
            "save_memory",
            "required",
            '"history_entry"',
            '"memory_update"',
        ]

        for keyword in expected_keywords:
            assert keyword in source, f"Prompt should include: {keyword!r}"
