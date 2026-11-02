"""Test-suite safety controls."""

import socket
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail every test that attempts real DNS resolution or socket access."""

    def blocked(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("Real network access is forbidden during tests")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    yield

