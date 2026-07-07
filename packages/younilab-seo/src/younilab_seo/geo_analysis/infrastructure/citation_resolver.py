from dataclasses import dataclass, field
import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlsplit
from urllib.parse import urljoin

import httpx


logger = logging.getLogger(__name__)
VERTEX_GROUNDING_REDIRECT_HOST = "vertexaisearch.cloud.google.com"


@dataclass
class HttpCitationUrlResolver:
    """Follows trusted provider citation redirects without reading page content."""

    timeout_seconds: float = 5.0
    max_redirects: int = 5
    allowed_redirect_hosts: frozenset[str] = frozenset(
        {VERTEX_GROUNDING_REDIRECT_HOST}
    )
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def resolve(self, url: str) -> str | None:
        if not self._is_allowed_redirect_url(url):
            return None
        original_host = _host(url)
        current_url = url
        try:
            for _ in range(self.max_redirects + 1):
                async with self._get_client().stream(
                    "GET",
                    current_url,
                    follow_redirects=False,
                ) as response:
                    if not _is_redirect_status(response.status_code):
                        if response.is_error:
                            logger.info(
                                "citation redirect resolved with HTTP error status",
                                extra={
                                    "originalHost": original_host,
                                    "finalHost": _host(current_url),
                                    "statusCode": response.status_code,
                                },
                            )
                        return current_url

                    location = response.headers.get("Location")
                    if not location:
                        return current_url
                    next_url = urljoin(current_url, location)
                    if not await _is_safe_redirect_target(next_url):
                        logger.info(
                            "citation redirect target rejected",
                            extra={
                                "originalHost": original_host,
                                "targetHost": _host(next_url),
                                "statusCode": response.status_code,
                            },
                        )
                        return None
                    current_url = next_url

            logger.info(
                "citation redirect exceeded maximum redirects",
                extra={
                    "originalHost": original_host,
                    "finalHost": _host(current_url),
                    "maxRedirects": self.max_redirects,
                },
            )
            return None
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            logger.info(
                "citation redirect resolution failed",
                extra={
                    "originalHost": original_host,
                    "errorClass": exc.__class__.__name__,
                },
            )
            return None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                max_redirects=self.max_redirects,
                timeout=self.timeout_seconds,
            )
        return self._client

    def _is_allowed_redirect_url(self, url: str) -> bool:
        parsed = urlsplit(url.strip())
        if parsed.scheme.lower() not in {"http", "https"}:
            return False
        host = parsed.hostname
        return (
            host is not None
            and _normalize_host(host) in self.allowed_redirect_hosts
            and parsed.path.startswith("/grounding-api-redirect/")
        )


def _is_http_url(url: str) -> bool:
    parsed = urlsplit(url.strip())
    return parsed.scheme.lower() in {"http", "https"} and parsed.hostname is not None


def _is_redirect_status(status_code: int) -> bool:
    return status_code in {301, 302, 303, 307, 308}


async def _is_safe_redirect_target(url: str) -> bool:
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    host = parsed.hostname
    if host is None:
        return False
    normalized_host = _normalize_host(host)
    if normalized_host == "localhost" or normalized_host.endswith(".localhost"):
        return False
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, normalized_host, None)
    except socket.gaierror:
        return False
    return all(_is_public_address(item[4][0]) for item in addresses)


def _is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _host(url: str) -> str | None:
    return urlsplit(url.strip()).hostname


def _normalize_host(host: str) -> str:
    return host.strip().lower().rstrip(".")
