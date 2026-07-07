import asyncio
import socket

import httpx

from younilab_seo.geo_analysis.infrastructure.citation_resolver import (
    HttpCitationUrlResolver,
)


def test_citation_url_resolver_follows_vertex_redirect(monkeypatch) -> None:
    async def run() -> None:
        monkeypatch.setattr(socket, "getaddrinfo", _public_getaddrinfo)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.host == "vertexaisearch.cloud.google.com":
                return httpx.Response(
                    302,
                    headers={"Location": "https://publisher.example/news"},
                )
            return httpx.Response(200)

        resolver = HttpCitationUrlResolver()
        resolver._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        )

        result = await resolver.resolve(
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        )

        assert result == "https://publisher.example/news"

        await resolver.close()

    asyncio.run(run())


def test_citation_url_resolver_rejects_non_allowed_hosts() -> None:
    async def run() -> None:
        called = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200)

        resolver = HttpCitationUrlResolver()
        resolver._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        result = await resolver.resolve("https://example.com/redirect")

        assert result is None
        assert called is False

        await resolver.close()

    asyncio.run(run())


def test_citation_url_resolver_rejects_non_grounding_redirect_path() -> None:
    async def run() -> None:
        called = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200)

        resolver = HttpCitationUrlResolver()
        resolver._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        result = await resolver.resolve("https://vertexaisearch.cloud.google.com/other")

        assert result is None
        assert called is False

        await resolver.close()

    asyncio.run(run())


def test_citation_url_resolver_rejects_non_http_urls() -> None:
    async def run() -> None:
        resolver = HttpCitationUrlResolver()

        result = await resolver.resolve("file:///etc/passwd")

        assert result is None

    asyncio.run(run())


def test_citation_url_resolver_returns_none_on_request_error() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection failed", request=request)

        resolver = HttpCitationUrlResolver()
        resolver._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        result = await resolver.resolve(
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        )

        assert result is None

        await resolver.close()

    asyncio.run(run())


def test_citation_url_resolver_returns_none_for_private_redirect_target() -> None:
    async def run() -> None:
        requests: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(str(request.url))
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})

        resolver = HttpCitationUrlResolver()
        resolver._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        )

        result = await resolver.resolve(
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        )

        assert result is None
        assert requests == [
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        ]

        await resolver.close()

    asyncio.run(run())


def test_citation_url_resolver_returns_none_for_localhost_redirect_target() -> None:
    async def run() -> None:
        requests: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(str(request.url))
            return httpx.Response(302, headers={"Location": "http://localhost/admin"})

        resolver = HttpCitationUrlResolver()
        resolver._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        )

        result = await resolver.resolve(
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        )

        assert result is None
        assert requests == [
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        ]

        await resolver.close()

    asyncio.run(run())


def test_citation_url_resolver_returns_none_for_invalid_final_url() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(302, headers={"Location": "mailto:test@example.com"})

        resolver = HttpCitationUrlResolver()
        resolver._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        )

        result = await resolver.resolve(
            "https://vertexaisearch.cloud.google.com/grounding-api-redirect/token"
        )

        assert result is None

        await resolver.close()

    asyncio.run(run())


def _public_getaddrinfo(host, port, *args, **kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            ("93.184.216.34", 0),
        )
    ]
