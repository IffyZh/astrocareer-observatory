"""Network-free tests for the restricted HTTP transport."""

from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from astrocareer.collectors import RequestSpec
from astrocareer.collectors.http import (
    HTTPTransport,
    NetworkFailure,
    RateLimited,
    ResponseTooLarge,
    UnsafeRequestError,
    UnexpectedContentType,
)
from astrocareer.sources import SourceDefinition


class FixedResolver:
    def __init__(self, addresses: tuple[str, ...] = ("93.184.216.34",)) -> None:
        self.addresses = addresses

    def resolve(self, hostname: str) -> tuple[str, ...]:
        del hostname
        return self.addresses


class FakeResponse:
    def __init__(
        self,
        *,
        url: str = "https://jobs.example.test/list",
        status: int = 200,
        content: bytes = b"<html>jobs</html>",
        headers: dict[str, str] | None = None,
    ) -> None:
        self._url = url
        self._status = status
        self._content = BytesIO(content)
        self.headers = headers or {"Content-Type": "text/html"}

    def geturl(self) -> str:
        return self._url

    def getcode(self) -> int:
        return self._status

    def read(self, size: int = -1) -> bytes:
        return self._content.read(size)


class FakeBackend:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.requests = []

    def open(self, request, timeout: float):  # noqa: ANN001
        self.requests.append((request, timeout))
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def _source(
    *,
    enabled: bool = True,
    access_status: str = "approved",
) -> SourceDefinition:
    return SourceDefinition(
        source_id="http-test-source",
        name="HTTP Test Source",
        organization="Example",
        homepage_url="https://jobs.example.test/",
        source_type="employer",
        authority_level="a",
        collection_method="html",
        enabled=enabled,
        access_status=access_status,
        robots_reviewed_at="2026-11-01",
        terms_reviewed_at="2026-11-01",
        allowed_hosts=("jobs.example.test",),
        allowed_path_prefixes=("/list",),
        minimum_interval_seconds=3600,
        redistribution_notes="Test only.",
    )


def _request(
    url: str = "https://jobs.example.test/list",
    *,
    headers: tuple[tuple[str, str], ...] = (),
) -> RequestSpec:
    return RequestSpec(
        source_id="http-test-source",
        url=url,
        purpose="listing",
        headers=headers,
    )


def _transport(
    backend: FakeBackend,
    *,
    source: SourceDefinition | None = None,
    resolver: FixedResolver | None = None,
    **overrides: object,
) -> HTTPTransport:
    return HTTPTransport(
        source or _source(),
        contact_url="https://project.example.test/contact",
        backend=backend,
        resolver=resolver or FixedResolver(),
        sleep=lambda _: None,
        **overrides,
    )


def _http_error(
    code: int,
    *,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> HTTPError:
    return HTTPError(
        "https://jobs.example.test/list",
        code,
        "test",
        headers or {},
        BytesIO(body),
    )


def test_success_adds_identifiable_user_agent_and_returns_snapshot() -> None:
    backend = FakeBackend(
        FakeResponse(headers={"Content-Type": "text/html; charset=utf-8", "ETag": '"v1"'})
    )

    snapshot = _transport(backend).fetch(_request())

    request, timeout = backend.requests[0]
    headers = dict(request.header_items())
    assert snapshot.status_code == 200
    assert snapshot.content_sha256
    assert snapshot.etag == '"v1"'
    assert "AstroCareerObservatory" in headers["User-agent"]
    assert timeout == 20.0


@pytest.mark.parametrize(
    "source",
    [
        _source(enabled=False),
        _source(access_status="pending_review"),
        _source(access_status="prohibited"),
    ],
)
def test_disabled_or_unapproved_source_is_blocked(source: SourceDefinition) -> None:
    backend = FakeBackend(FakeResponse())

    with pytest.raises(UnsafeRequestError):
        _transport(backend, source=source).fetch(_request())

    assert backend.requests == []


def test_import_source_cannot_use_http_transport() -> None:
    source = _source()
    source = SourceDefinition(
        **{
            **source.__dict__,
            "collection_method": "import",
        }
    )
    backend = FakeBackend(FakeResponse())

    with pytest.raises(UnsafeRequestError, match="unavailable for import"):
        _transport(backend, source=source).fetch(_request())

    assert backend.requests == []


@pytest.mark.parametrize(
    "url",
    [
        "http://jobs.example.test/list",
        "https://outside.example.test/list",
        "https://user:password@jobs.example.test/list",
        "https://jobs.example.test:8443/list",
        "https://jobs.example.test/unreviewed",
    ],
)
def test_unsafe_urls_are_blocked_before_request(url: str) -> None:
    backend = FakeBackend(FakeResponse())

    with pytest.raises(UnsafeRequestError):
        _transport(backend).fetch(_request(url))

    assert backend.requests == []


def test_private_dns_resolution_is_blocked() -> None:
    backend = FakeBackend(FakeResponse())

    with pytest.raises(UnsafeRequestError, match="non-public"):
        _transport(backend, resolver=FixedResolver(("127.0.0.1",))).fetch(_request())

    assert backend.requests == []


def test_redirect_outside_allowlist_is_blocked() -> None:
    backend = FakeBackend(
        _http_error(302, headers={"Location": "https://outside.example.test/list"})
    )

    with pytest.raises(UnsafeRequestError, match="allowlist"):
        _transport(backend).fetch(_request())

    assert len(backend.requests) == 1


def test_response_size_is_limited_even_without_content_length() -> None:
    backend = FakeBackend(FakeResponse(content=b"123456"))

    with pytest.raises(ResponseTooLarge):
        _transport(backend, max_response_bytes=5).fetch(_request())


def test_unexpected_success_content_type_is_rejected() -> None:
    backend = FakeBackend(FakeResponse(headers={"Content-Type": "application/pdf"}))

    with pytest.raises(UnexpectedContentType):
        _transport(backend).fetch(_request())


def test_sensitive_collector_header_is_rejected() -> None:
    backend = FakeBackend(FakeResponse())

    with pytest.raises(UnsafeRequestError, match="headers"):
        _transport(backend).fetch(_request(headers=(("Authorization", "secret"),)))

    assert backend.requests == []


def test_etag_is_reused_and_304_becomes_snapshot() -> None:
    backend = FakeBackend(
        FakeResponse(headers={"Content-Type": "text/html", "ETag": '"v1"'}),
        _http_error(304, headers={"ETag": '"v1"'}),
    )
    transport = _transport(backend)

    first = transport.fetch(_request())
    second = transport.fetch(_request())

    second_headers = dict(backend.requests[1][0].header_items())
    assert first.status_code == 200
    assert second.status_code == 304
    assert second.content == b""
    assert second_headers["If-none-match"] == '"v1"'


def test_429_is_not_slept_through() -> None:
    backend = FakeBackend(_http_error(429, headers={"Retry-After": "120"}))

    with pytest.raises(RateLimited) as exc_info:
        _transport(backend).fetch(_request())

    assert exc_info.value.retry_after_seconds == 120


def test_transient_network_failure_retries_with_bound() -> None:
    backend = FakeBackend(URLError("temporary"), FakeResponse())
    sleeps: list[float] = []
    transport = HTTPTransport(
        _source(),
        contact_url="https://project.example.test/contact",
        backend=backend,
        resolver=FixedResolver(),
        sleep=sleeps.append,
        max_attempts=2,
        retry_delay_seconds=0.25,
    )

    snapshot = transport.fetch(_request())

    assert snapshot.status_code == 200
    assert len(backend.requests) == 2
    assert sleeps == [0.25]


def test_repeated_network_failure_raises_structured_error() -> None:
    backend = FakeBackend(URLError("one"), URLError("two"))

    with pytest.raises(NetworkFailure):
        _transport(backend).fetch(_request())
