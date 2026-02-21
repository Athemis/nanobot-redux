import pytest

from nanobot.agent.context import ContextBuilder


def test_add_assistant_message_omits_content_when_none_and_tool_calls_present(tmp_path) -> None:
    builder = ContextBuilder(tmp_path)
    messages: list[dict[str, object]] = []
    tool_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "read_file", "arguments": "{}"},
        }
    ]

    updated = builder.add_assistant_message(messages, content=None, tool_calls=tool_calls)

    assert updated[-1]["role"] == "assistant"
    assert updated[-1]["tool_calls"] == tool_calls
    assert "content" not in updated[-1]


def test_add_assistant_message_omits_content_when_empty_string(tmp_path) -> None:
    builder = ContextBuilder(tmp_path)
    messages: list[dict[str, object]] = []

    updated = builder.add_assistant_message(messages, content="")

    assert updated[-1]["role"] == "assistant"
    assert "content" not in updated[-1]


def test_add_assistant_message_keeps_non_empty_content_and_reasoning(tmp_path) -> None:
    builder = ContextBuilder(tmp_path)
    messages: list[dict[str, object]] = []

    updated = builder.add_assistant_message(
        messages,
        content="done",
        reasoning_content="chain-of-thought-summary",
    )

    assert updated[-1]["role"] == "assistant"
    assert updated[-1]["content"] == "done"
    assert updated[-1]["reasoning_content"] == "chain-of-thought-summary"


@pytest.mark.parametrize(
    "reasoning_content, expected_present, expected_value",
    [
        ("", True, ""),
        (None, False, None),
    ],
)
def test_add_assistant_message_reasoning_content_boundary(
    tmp_path,
    reasoning_content: str | None,
    expected_present: bool,
    expected_value: str | None,
) -> None:
    builder = ContextBuilder(tmp_path)
    messages: list[dict[str, object]] = []

    updated = builder.add_assistant_message(
        messages,
        content="done",
        reasoning_content=reasoning_content,
    )

    assert updated[-1]["role"] == "assistant"
    assert updated[-1]["content"] == "done"
    if expected_present:
        assert updated[-1]["reasoning_content"] == expected_value
    else:
        assert "reasoning_content" not in updated[-1]
