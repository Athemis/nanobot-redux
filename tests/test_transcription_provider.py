"""Tests for GroqTranscriptionProvider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.providers.transcription import GroqTranscriptionProvider


def test_uses_env_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "env-key")
    p = GroqTranscriptionProvider()
    assert p.api_key == "env-key"


def test_explicit_api_key_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "env-key")
    p = GroqTranscriptionProvider(api_key="explicit")
    assert p.api_key == "explicit"


@pytest.mark.asyncio
async def test_transcribe_returns_empty_when_no_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    p = GroqTranscriptionProvider(api_key=None)
    result = await p.transcribe(tmp_path / "audio.mp3")
    assert result == ""


@pytest.mark.asyncio
async def test_transcribe_returns_empty_when_file_missing(tmp_path) -> None:
    p = GroqTranscriptionProvider(api_key="key")
    result = await p.transcribe(tmp_path / "nonexistent.mp3")
    assert result == ""


@pytest.mark.asyncio
async def test_transcribe_posts_to_groq_api(tmp_path) -> None:
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake-audio")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"text": "hello world"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    p = GroqTranscriptionProvider(api_key="test-key")
    with patch("nanobot.providers.transcription.httpx.AsyncClient", return_value=mock_client):
        result = await p.transcribe(audio_file)

    assert result == "hello world"


@pytest.mark.asyncio
async def test_transcribe_returns_empty_on_http_error(tmp_path) -> None:
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake-audio")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=Exception("connection refused"))

    p = GroqTranscriptionProvider(api_key="key")
    with patch("nanobot.providers.transcription.httpx.AsyncClient", return_value=mock_client):
        result = await p.transcribe(audio_file)

    assert result == ""
