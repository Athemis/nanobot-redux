import json as _json
import unittest.mock as mock
from collections.abc import Callable
from typing import Literal

import httpx
import pytest

from nanobot.agent.tools.web import WebSearchTool
from nanobot.config.schema import WebSearchConfig


def _tool(config: WebSearchConfig, handler) -> WebSearchTool:
    return WebSearchTool(config=config, transport=httpx.MockTransport(handler))


def _assert_tavily_request(request: httpx.Request) -> bool:
    return (
        request.method == "POST"
        and str(request.url) == "https://api.tavily.com/search"
        and request.headers.get("authorization") == "Bearer tavily-key"
        and '"query":"openclaw"' in request.read().decode("utf-8")
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "config_kwargs", "query", "count", "assert_request", "response", "assert_text"),
    [
        (
            "brave",
            {"api_key": "brave-key"},
            "nanobot",
            1,
            lambda request: (
                request.method == "GET"
                and str(request.url)
                == "https://api.search.brave.com/res/v1/web/search?q=nanobot&count=1"
                and request.headers["X-Subscription-Token"] == "brave-key"
            ),
            httpx.Response(
                200,
                json={
                    "web": {
                        "results": [
                            {
                                "title": "NanoBot",
                                "url": "https://example.com/nanobot",
                                "description": "Ultra-lightweight assistant",
                            }
                        ]
                    }
                },
            ),
            ["Results for: nanobot", "1. NanoBot", "https://example.com/nanobot"],
        ),
        (
            "tavily",
            {"api_key": "tavily-key"},
            "openclaw",
            2,
            _assert_tavily_request,
            httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "OpenClaw",
                            "url": "https://example.com/openclaw",
                            "content": "Plugin-based assistant framework",
                        }
                    ]
                },
            ),
            ["Results for: openclaw", "1. OpenClaw", "https://example.com/openclaw"],
        ),
        (
            "searxng",
            {"base_url": "https://searx.example"},
            "nanobot",
            1,
            lambda request: (
                request.method == "GET"
                and str(request.url) == "https://searx.example/search?q=nanobot&format=json"
            ),
            httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "nanobot docs",
                            "url": "https://example.com/nanobot",
                            "content": "Lightweight assistant docs",
                        }
                    ]
                },
            ),
            ["Results for: nanobot", "1. nanobot docs", "https://example.com/nanobot"],
        ),
    ],
)
async def test_web_search_provider_formats_results(
    provider: Literal["brave", "tavily", "searxng"],
    config_kwargs: dict,
    query: str,
    count: int,
    assert_request: Callable[[httpx.Request], bool],
    response: httpx.Response,
    assert_text: list[str],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert assert_request(request)
        return response

    tool = _tool(WebSearchConfig(provider=provider, max_results=5, **config_kwargs), handler)
    result = await tool.execute(query=query, count=count)
    for text in assert_text:
        assert text in result


@pytest.mark.asyncio
async def test_web_search_from_legacy_config_works() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {"title": "Legacy", "url": "https://example.com", "description": "ok"}
                    ]
                }
            },
        )

    config = WebSearchConfig(api_key="legacy-key", max_results=3)
    tool = WebSearchTool(config=config, transport=httpx.MockTransport(handler))
    result = await tool.execute(query="constructor", count=1)
    assert "1. Legacy" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "config", "missing_env", "expected_title"),
    [
        (
            "brave",
            WebSearchConfig(provider="brave", api_key="", max_results=5),
            "BRAVE_API_KEY",
            "Fallback Result",
        ),
        (
            "tavily",
            WebSearchConfig(provider="tavily", api_key="", max_results=5),
            "TAVILY_API_KEY",
            "Tavily Fallback",
        ),
    ],
)
async def test_web_search_missing_key_falls_back_to_duckduckgo(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    config: WebSearchConfig,
    missing_env: str,
    expected_title: str,
) -> None:
    monkeypatch.delenv(missing_env, raising=False)

    called = False

    class FakeDDGS:
        def __init__(self, *args, **kwargs):
            pass

        def text(self, keywords: str, max_results: int):
            nonlocal called
            called = True
            return [
                {
                    "title": expected_title,
                    "href": f"https://example.com/{provider}-fallback",
                    "body": "Fallback snippet",
                }
            ]

    monkeypatch.setattr("nanobot.agent.tools.web.DDGS", FakeDDGS, raising=False)

    result = await WebSearchTool(config=config).execute(query="fallback", count=1)
    assert called
    assert "Using DuckDuckGo fallback" in result
    assert f"1. {expected_title}" in result


@pytest.mark.asyncio
async def test_web_search_brave_missing_key_without_fallback_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    tool = WebSearchTool(
        config=WebSearchConfig(
            provider="brave",
            api_key="",
            fallback_to_duckduckgo=False,
        )
    )

    result = await tool.execute(query="fallback", count=1)
    assert result == "Error: BRAVE_API_KEY not configured"


@pytest.mark.asyncio
async def test_web_search_searxng_missing_base_url_falls_back_to_duckduckgo() -> None:
    tool = WebSearchTool(config=WebSearchConfig(provider="searxng", base_url="", max_results=5))

    result = await tool.execute(query="nanobot", count=1)
    assert "DuckDuckGo fallback" in result
    assert "SEARXNG_BASE_URL" in result


@pytest.mark.asyncio
async def test_web_search_searxng_missing_base_url_no_fallback_returns_error() -> None:
    tool = WebSearchTool(
        config=WebSearchConfig(
            provider="searxng",
            base_url="",
            fallback_to_duckduckgo=False,
            max_results=5,
        )
    )

    result = await tool.execute(query="nanobot", count=1)
    assert result == "Error: SEARXNG_BASE_URL not configured"


@pytest.mark.asyncio
async def test_web_search_searxng_uses_env_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEARXNG_BASE_URL", "https://searx.env")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://searx.env/search?q=nanobot&format=json"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "env result",
                        "url": "https://example.com/env",
                        "content": "from env",
                    }
                ]
            },
        )

    config = WebSearchConfig(provider="searxng", base_url="", max_results=5)
    result = await _tool(config, handler).execute(query="nanobot", count=1)
    assert "1. env result" in result


@pytest.mark.asyncio
async def test_web_search_register_custom_provider() -> None:
    config = WebSearchConfig(provider="custom", max_results=5)
    tool = WebSearchTool(config=config)

    async def _custom_provider(query: str, n: int) -> str:
        return f"custom:{query}:{n}"

    tool._provider_dispatch["custom"] = _custom_provider

    result = await tool.execute(query="nanobot", count=2)
    assert result == "custom:nanobot:2"


@pytest.mark.asyncio
async def test_web_search_duckduckgo_uses_injected_ddgs_factory() -> None:
    class FakeDDGS:
        def text(self, keywords: str, max_results: int):
            assert keywords == "nanobot"
            assert max_results == 1
            return [
                {
                    "title": "NanoBot result",
                    "href": "https://example.com/nanobot",
                    "body": "Search content",
                }
            ]

    tool = WebSearchTool(
        config=WebSearchConfig(provider="duckduckgo", max_results=5),
        ddgs_factory=lambda: FakeDDGS(),
    )

    result = await tool.execute(query="nanobot", count=1)
    assert "1. NanoBot result" in result


@pytest.mark.asyncio
async def test_web_search_unknown_provider_returns_error() -> None:
    tool = WebSearchTool(
        config=WebSearchConfig(provider="google", max_results=5),
    )
    result = await tool.execute(query="nanobot", count=1)
    assert result == "Error: unknown search provider 'google'"


@pytest.mark.asyncio
async def test_web_search_dispatch_dict_overwrites_builtin() -> None:
    async def _custom_brave(query: str, n: int) -> str:
        return f"custom-brave:{query}:{n}"

    tool = WebSearchTool(
        config=WebSearchConfig(provider="brave", api_key="key", max_results=5),
    )
    tool._provider_dispatch["brave"] = _custom_brave
    result = await tool.execute(query="nanobot", count=2)
    assert result == "custom-brave:nanobot:2"


@pytest.mark.asyncio
async def test_web_search_searxng_rejects_invalid_url() -> None:
    tool = WebSearchTool(
        config=WebSearchConfig(
            provider="searxng",
            base_url="ftp://internal.host",
            max_results=5,
        ),
    )
    result = await tool.execute(query="nanobot", count=1)
    assert "Error: invalid SearXNG URL" in result


# ---------------------------------------------------------------------------
# Helpers for patching httpx.AsyncClient to use a MockTransport
# ---------------------------------------------------------------------------


def _patch_async_client(transport):
    """Return a context manager that injects *transport* into AsyncClient.

    Note: patched_init mirrors the (*args, **kwargs) signature of the original
    __init__ to avoid silently dropping positional arguments if the httpx API
    changes in the future.
    """
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)

    return mock.patch.object(httpx.AsyncClient, "__init__", patched_init)


# ---------------------------------------------------------------------------
# _validate_url helper — missing domain and exception paths
# ---------------------------------------------------------------------------


def test_validate_url_missing_domain() -> None:
    from nanobot.agent.tools.web import _validate_url

    ok, msg = _validate_url("http://")
    assert not ok
    assert "Missing domain" in msg


def test_validate_url_non_http_scheme() -> None:
    from nanobot.agent.tools.web import _validate_url

    ok, msg = _validate_url("ftp://example.com")
    assert not ok
    assert "ftp" in msg


def test_validate_url_valid() -> None:
    from nanobot.agent.tools.web import _validate_url

    ok, msg = _validate_url("https://example.com/path")
    assert ok
    assert msg == ""


# ---------------------------------------------------------------------------
# _format_results helper — empty results path
# ---------------------------------------------------------------------------


def test_format_results_empty() -> None:
    from nanobot.agent.tools.web import _format_results

    result = _format_results("myquery", [], 5)
    assert result == "No results for: myquery"


# ---------------------------------------------------------------------------
# WebSearchTool — Brave HTTP error path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_brave_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    tool = _tool(
        WebSearchConfig(provider="brave", api_key="brave-key", max_results=5),
        handler,
    )
    result = await tool.execute(query="nanobot", count=1)
    assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# WebSearchTool — Tavily missing key without fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_tavily_missing_key_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    tool = WebSearchTool(
        config=WebSearchConfig(
            provider="tavily",
            api_key="",
            fallback_to_duckduckgo=False,
        )
    )
    result = await tool.execute(query="anything", count=1)
    assert result == "Error: TAVILY_API_KEY not configured"


# ---------------------------------------------------------------------------
# WebSearchTool — Tavily HTTP error path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_tavily_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    tool = _tool(
        WebSearchConfig(provider="tavily", api_key="tavily-key", max_results=5),
        handler,
    )
    result = await tool.execute(query="nanobot", count=1)
    assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# WebSearchTool — DuckDuckGo no results path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_duckduckgo_no_results() -> None:
    class EmptyDDGS:
        def text(self, keywords: str, max_results: int):
            return []

    tool = WebSearchTool(
        config=WebSearchConfig(provider="duckduckgo", max_results=5),
        ddgs_factory=lambda: EmptyDDGS(),
    )
    result = await tool.execute(query="obscurequery", count=1)
    assert result == "No results for: obscurequery"


# ---------------------------------------------------------------------------
# WebSearchTool — DuckDuckGo exception path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_duckduckgo_exception() -> None:
    class BrokenDDGS:
        def text(self, keywords: str, max_results: int):
            raise RuntimeError("network failure")

    tool = WebSearchTool(
        config=WebSearchConfig(provider="duckduckgo", max_results=5),
        ddgs_factory=lambda: BrokenDDGS(),
    )
    result = await tool.execute(query="nanobot", count=1)
    assert "Error: DuckDuckGo search failed" in result
    assert "network failure" in result


# ---------------------------------------------------------------------------
# WebSearchTool — fallback DDG itself errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_fallback_duckduckgo_itself_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)

    class BrokenDDGS:
        def text(self, keywords: str, max_results: int):
            raise RuntimeError("ddg is down")

    tool = WebSearchTool(
        config=WebSearchConfig(
            provider="brave", api_key="", fallback_to_duckduckgo=True, max_results=5
        ),
        ddgs_factory=lambda: BrokenDDGS(),
    )
    result = await tool.execute(query="nanobot", count=1)
    assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# WebSearchTool — SearXNG HTTP error path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_searxng_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    tool = _tool(
        WebSearchConfig(provider="searxng", base_url="https://searx.example", max_results=5),
        handler,
    )
    result = await tool.execute(query="nanobot", count=1)
    assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# WebFetchTool — constructor and tool properties
# ---------------------------------------------------------------------------


def test_web_fetch_tool_properties() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool(max_chars=12345)
    assert tool.name == "web_fetch"
    assert tool.description
    assert tool.max_chars == 12345
    assert "url" in tool.parameters["properties"]


# ---------------------------------------------------------------------------
# WebFetchTool — URL validation failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_invalid_url() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()
    result = await tool.execute(url="ftp://bad-scheme.example.com")
    data = _json.loads(result)
    assert "error" in data
    assert "URL validation failed" in data["error"]


# ---------------------------------------------------------------------------
# WebFetchTool — successful HTML fetch with markdown extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_html_markdown() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()

    html_body = (
        "<!doctype html><html><head><title>Test Page</title></head>"
        "<body><p>Hello <a href='https://example.com'>World</a></p>"
        "<h2>Section</h2><ul><li>Item one</li></ul></body></html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=html_body, headers={"content-type": "text/html; charset=utf-8"}
        )

    transport = httpx.MockTransport(handler)
    with _patch_async_client(transport):
        result = await tool.execute(url="https://example.com/page")

    data = _json.loads(result)
    assert data["status"] == 200
    assert data["extractor"] == "readability"
    assert "text" in data
    assert data["truncated"] is False


# ---------------------------------------------------------------------------
# WebFetchTool — successful JSON fetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_json_content() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()
    payload = {"key": "value", "numbers": [1, 2, 3]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=payload,
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    with _patch_async_client(transport):
        result = await tool.execute(url="https://api.example.com/data")

    data = _json.loads(result)
    assert data["extractor"] == "json"
    assert "key" in data["text"]


# ---------------------------------------------------------------------------
# WebFetchTool — raw text fetch (non-HTML, non-JSON content-type)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_raw_text() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="plain text content here",
            headers={"content-type": "text/plain"},
        )

    transport = httpx.MockTransport(handler)
    with _patch_async_client(transport):
        result = await tool.execute(url="https://example.com/data.txt")

    data = _json.loads(result)
    assert data["extractor"] == "raw"
    assert "plain text content here" in data["text"]


# ---------------------------------------------------------------------------
# WebFetchTool — truncation path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_truncation() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool(max_chars=20)
    long_text = "A" * 500

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=long_text,
            headers={"content-type": "text/plain"},
        )

    transport = httpx.MockTransport(handler)
    with _patch_async_client(transport):
        result = await tool.execute(url="https://example.com/long")

    data = _json.loads(result)
    assert data["truncated"] is True
    assert len(data["text"]) == 20


# ---------------------------------------------------------------------------
# WebFetchTool — HTTP error exception path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_http_error() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(handler)
    with _patch_async_client(transport):
        result = await tool.execute(url="https://example.com/missing")

    data = _json.loads(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# WebFetchTool — kwargs extractMode and maxChars forwarding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_kwargs_extract_mode_and_max_chars() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool(max_chars=50000)
    html_body = (
        "<!doctype html><html><head><title>KW Test</title></head>"
        "<body><p>Content here that is longer than fifty characters total</p></body></html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html_body, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    with _patch_async_client(transport):
        result = await tool.execute(
            url="https://example.com/kw",
            extractMode="text",
            maxChars=50,
        )

    data = _json.loads(result)
    assert data["extractor"] == "readability"
    assert len(data["text"]) <= 50


# ---------------------------------------------------------------------------
# WebFetchTool — HTML fetch with text extraction mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_html_text_mode() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()
    html_body = (
        "<!doctype html><html><head><title>Text Mode</title></head>"
        "<body><p>Simple content</p></body></html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html_body, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    with _patch_async_client(transport):
        result = await tool.execute(url="https://example.com/textmode", extract_mode="text")

    data = _json.loads(result)
    assert data["extractor"] == "readability"
    assert "text" in data


# ---------------------------------------------------------------------------
# WebFetchTool — HTML detected via body sniff (no text/html content-type)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_fetch_html_sniffed_from_body() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()
    html_body = (
        "<!doctype html><html><head><title>Sniffed</title></head><body><p>Hi</p></body></html>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, text=html_body, headers={"content-type": "application/octet-stream"}
        )

    transport = httpx.MockTransport(handler)
    with _patch_async_client(transport):
        result = await tool.execute(url="https://example.com/sniff")

    data = _json.loads(result)
    assert data["extractor"] == "readability"


# ---------------------------------------------------------------------------
# WebFetchTool — _to_markdown method directly
# ---------------------------------------------------------------------------


def test_web_fetch_to_markdown_links_headings_lists() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()
    html = (
        "<h1>Title</h1>"
        "<p>Para with <a href='https://x.com'>link text</a></p>"
        "<ul><li>Item A</li><li>Item B</li></ul>"
        "<div>end</div>"
        "<br/>"
        "<hr>"
    )
    result = tool._to_markdown(html)
    assert "# Title" in result
    assert "[link text](https://x.com)" in result
    assert "- Item A" in result
    assert "- Item B" in result


def test_web_fetch_to_markdown_headings_h2_h3() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()
    html = "<h2>Second</h2><h3>Third</h3>"
    result = tool._to_markdown(html)
    assert "## Second" in result
    assert "### Third" in result


def test_web_fetch_to_markdown_section_and_article_breaks() -> None:
    from nanobot.agent.tools.web import WebFetchTool

    tool = WebFetchTool()
    html = "<section>content</section><article>more</article>"
    result = tool._to_markdown(html)
    assert "content" in result
    assert "more" in result


def test_validate_url_exception_returns_error() -> None:
    from nanobot.agent.tools.web import _validate_url

    with mock.patch("nanobot.agent.tools.web.urlparse", side_effect=ValueError("parse error")):
        ok, msg = _validate_url("https://example.com")
    assert not ok
    assert "parse error" in msg


# ---------------------------------------------------------------------------
# _strip_tags — closing tag whitespace (CodeQL / CodeRabbit fix)
# ---------------------------------------------------------------------------


def test_strip_tags_removes_script_with_whitespace_before_close() -> None:
    """_strip_tags must strip <script> blocks even when </script > has whitespace before >."""
    from nanobot.agent.tools.web import _strip_tags

    html = "before<script type='text/javascript'>alert(1)</script >after"
    result = _strip_tags(html)
    assert "alert(1)" not in result
    assert "before" in result
    assert "after" in result


def test_strip_tags_removes_style_with_whitespace_before_close() -> None:
    """_strip_tags must strip <style> blocks even when </style > has whitespace before >."""
    from nanobot.agent.tools.web import _strip_tags

    html = "before<style type='text/css'>body{color:red}</style >after"
    result = _strip_tags(html)
    assert "color:red" not in result
    assert "before" in result
    assert "after" in result


def test_strip_tags_removes_script_with_attributes_in_closing_tag() -> None:
    """_strip_tags must strip <script> blocks with extra attributes before the closing >."""
    from nanobot.agent.tools.web import _strip_tags

    html = "before<script>alert(1)</script\t\n bar>after"
    result = _strip_tags(html)
    assert "alert(1)" not in result
    assert "before" in result
    assert "after" in result


def test_strip_tags_removes_style_with_attributes_in_closing_tag() -> None:
    """_strip_tags must strip <style> blocks with extra content before the closing >."""
    from nanobot.agent.tools.web import _strip_tags

    html = "before<style>body{color:red}</style type='text/css'>after"
    result = _strip_tags(html)
    assert "color:red" not in result
    assert "before" in result
    assert "after" in result
