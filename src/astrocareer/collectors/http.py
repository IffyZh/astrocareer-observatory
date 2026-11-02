"""Restricted production HTTP transport for reviewed public sources."""

import ipaddress
import socket
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from astrocareer.collectors.base import RawSnapshot, RequestSpec
from astrocareer.sources import SourceDefinition


class TransportError(RuntimeError):
    """Base class for structured transport failures."""


class UnsafeRequestError(TransportError):
    """The requested URL or headers violate transport policy."""


class ResponseTooLarge(TransportError):
    """The remote response exceeds the configured byte limit."""


class UnexpectedContentType(TransportError):
    """The remote response type is not approved for this transport."""


class NetworkFailure(TransportError):
    """A bounded request failed before a usable response was received."""


class RateLimited(TransportError):
    """The source returned HTTP 429 and should be retried later."""

    def __init__(self, retry_after_seconds: int | None) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Source rate-limited the request; retry after {retry_after_seconds}")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class HTTPBackend(Protocol):
    def open(self, request: Request, timeout: float):
        """Open one request without automatically following redirects."""
        ...


class Resolver(Protocol):
    def resolve(self, hostname: str) -> Sequence[str]:
        """Return all addresses for a hostname."""
        ...


class SocketResolver:
    def resolve(self, hostname: str) -> Sequence[str]:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        }
        return tuple(sorted(addresses))


@dataclass(frozen=True)
class CacheValidators:
    etag: str | None = None
    last_modified: str | None = None


class HTTPTransport:
    """HTTP GET transport with source policy, SSRF, and response safeguards."""

    _ALLOWED_REQUEST_HEADERS = {"accept"}
    _REDIRECT_CODES = {301, 302, 303, 307, 308}

    def __init__(
        self,
        source: SourceDefinition,
        *,
        contact_url: str,
        backend: HTTPBackend | None = None,
        resolver: Resolver | None = None,
        timeout_seconds: float = 20.0,
        max_response_bytes: int = 5_000_000,
        max_redirects: int = 3,
        max_attempts: int = 2,
        retry_delay_seconds: float = 0.5,
        allowed_content_types: Sequence[str] = (
            "text/html",
            "application/xhtml+xml",
            "application/json",
            "application/xml",
            "text/xml",
            "application/rss+xml",
            "application/atom+xml",
        ),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self.contact_url = contact_url
        self.backend = backend or build_opener(_NoRedirect())
        self.resolver = resolver or SocketResolver()
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds
        self.allowed_content_types = frozenset(allowed_content_types)
        self.sleep = sleep
        self.cache: dict[str, CacheValidators] = {}
        if not contact_url.startswith("https://"):
            raise ValueError("contact_url must be an HTTPS URL")
        if timeout_seconds <= 0 or max_response_bytes <= 0:
            raise ValueError("Timeout and response limit must be positive")
        if max_redirects < 0 or not 1 <= max_attempts <= 3:
            raise ValueError("Redirects must be non-negative and attempts must be 1-3")
        if not 0 <= retry_delay_seconds <= 10:
            raise ValueError("Retry delay must be between 0 and 10 seconds")

    def fetch(self, request: RequestSpec) -> RawSnapshot:
        if request.source_id != self.source.source_id:
            raise UnsafeRequestError("Request source does not match transport source")
        if not self.source.enabled:
            raise UnsafeRequestError("HTTP access is blocked for a disabled source")
        if self.source.collection_method not in {"api", "feed", "html"}:
            raise UnsafeRequestError(
                f"HTTP access is unavailable for {self.source.collection_method} sources"
            )
        access_allowed = self.source.access_status == "approved" or (
            self.source.access_status == "api_only"
            and self.source.collection_method == "api"
        )
        if not access_allowed:
            raise UnsafeRequestError(
                f"HTTP access is not approved: {self.source.access_status}"
            )
        self._validate_collector_headers(request.headers)

        current_url = request.url
        for attempt in range(self.max_attempts):
            redirects = 0
            while True:
                self._validate_url(current_url)
                headers = self._headers_for(current_url, request.headers)
                urllib_request = Request(current_url, headers=headers, method="GET")
                try:
                    response = self.backend.open(urllib_request, timeout=self.timeout_seconds)
                except HTTPError as error:
                    if error.code in self._REDIRECT_CODES:
                        location = error.headers.get("Location")
                        if not location:
                            raise NetworkFailure(
                                "Redirect response has no Location header"
                            ) from error
                        redirects += 1
                        if redirects > self.max_redirects:
                            raise UnsafeRequestError("Maximum redirect count exceeded") from error
                        current_url = urljoin(current_url, location)
                        continue
                    if error.code == 304:
                        return self._snapshot_from_error(request.source_id, current_url, error)
                    if error.code == 429:
                        retry_after = self._retry_after(error.headers.get("Retry-After"))
                        raise RateLimited(retry_after) from error
                    if 500 <= error.code <= 599 and attempt + 1 < self.max_attempts:
                        break
                    return self._snapshot_from_error(request.source_id, current_url, error)
                except (URLError, TimeoutError, OSError) as error:
                    if attempt + 1 < self.max_attempts:
                        break
                    raise NetworkFailure("Network request failed after bounded retries") from error

                final_url = response.geturl()
                self._validate_url(final_url)
                return self._snapshot_from_response(request.source_id, final_url, response)

            if attempt + 1 < self.max_attempts:
                self.sleep(self.retry_delay_seconds * (attempt + 1))

        raise NetworkFailure("Network request failed")

    def _validate_collector_headers(self, headers: tuple[tuple[str, str], ...]) -> None:
        disallowed = {
            name
            for name, _ in headers
            if name.casefold() not in self._ALLOWED_REQUEST_HEADERS
        }
        if disallowed:
            raise UnsafeRequestError(
                f"Collector supplied disallowed request headers: {sorted(disallowed)}"
            )

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise UnsafeRequestError("Only HTTPS URLs are allowed")
        if parsed.username or parsed.password:
            raise UnsafeRequestError("Credentials in URLs are forbidden")
        if parsed.port not in {None, 443}:
            raise UnsafeRequestError("Only the default HTTPS port is allowed")
        hostname = parsed.hostname
        if not hostname or hostname not in self.source.allowed_hosts:
            raise UnsafeRequestError("URL host is outside the source allowlist")
        path_allowed = any(
            parsed.path == prefix
            or (prefix.endswith("/") and parsed.path.startswith(prefix))
            for prefix in self.source.allowed_path_prefixes
        )
        if not path_allowed:
            raise UnsafeRequestError("URL path is outside the source allowlist")
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            raise UnsafeRequestError("Literal IP addresses are forbidden")
        try:
            addresses = self.resolver.resolve(hostname)
        except OSError as error:
            raise NetworkFailure("Source hostname could not be resolved") from error
        if not addresses:
            raise NetworkFailure("Source hostname resolved to no addresses")
        if any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise UnsafeRequestError("Source hostname resolved to a non-public address")

    def _headers_for(
        self,
        url: str,
        collector_headers: tuple[tuple[str, str], ...],
    ) -> dict[str, str]:
        headers = {
            "User-Agent": f"AstroCareerObservatory/0.0.0 (+{self.contact_url})",
            "Accept": "text/html,application/xhtml+xml,application/json,application/xml;q=0.9",
        }
        headers.update(collector_headers)
        validators = self.cache.get(url)
        if validators:
            if validators.etag:
                headers["If-None-Match"] = validators.etag
            if validators.last_modified:
                headers["If-Modified-Since"] = validators.last_modified
        return headers

    def _snapshot_from_response(
        self,
        source_id: str,
        url: str,
        response,
    ) -> RawSnapshot:
        status_code = int(response.getcode())
        content_type = self._content_type(response.headers.get("Content-Type"))
        content = self._read_limited(response)
        if status_code == 200 and content_type not in self.allowed_content_types:
            raise UnexpectedContentType(f"Content type is not allowed: {content_type}")
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")
        self.cache[url] = CacheValidators(etag=etag, last_modified=last_modified)
        return RawSnapshot.create(
            source_id=source_id,
            url=url,
            observed_at=datetime.now(timezone.utc),
            status_code=status_code,
            content_type=content_type,
            content=content,
            etag=etag,
            last_modified=last_modified,
        )

    def _snapshot_from_error(
        self,
        source_id: str,
        url: str,
        error: HTTPError,
    ) -> RawSnapshot:
        content = b"" if error.code == 304 else self._read_limited(error)
        content_type = self._content_type(error.headers.get("Content-Type"))
        return RawSnapshot.create(
            source_id=source_id,
            url=url,
            observed_at=datetime.now(timezone.utc),
            status_code=error.code,
            content_type=content_type,
            content=content,
            etag=error.headers.get("ETag"),
            last_modified=error.headers.get("Last-Modified"),
        )

    def _read_limited(self, response) -> bytes:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_response_bytes:
            raise ResponseTooLarge("Content-Length exceeds the response limit")
        content = response.read(self.max_response_bytes + 1)
        if len(content) > self.max_response_bytes:
            raise ResponseTooLarge("Response body exceeds the response limit")
        return content

    @staticmethod
    def _content_type(value: str | None) -> str | None:
        return value.split(";", 1)[0].strip().lower() if value else None

    @staticmethod
    def _retry_after(value: str | None) -> int | None:
        if not value:
            return None
        try:
            return max(0, int(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return None
            now = datetime.now(timezone.utc)
            return max(0, int((retry_at - now).total_seconds()))
