"""Tests for collector plugin descriptors and lazy entry-point discovery."""

from dataclasses import dataclass

import pytest

from astrocareer.collectors import CollectionBatch, Transport
from astrocareer.plugins import (
    CollectorPlugin,
    PluginError,
    collector_plugin_references,
    get_collector_plugin,
)


@dataclass
class _ExternalCollector:
    source_id: str = "external-example-source"

    def collect(self, transport: Transport, checkpoint=None) -> CollectionBatch:  # noqa: ANN001
        raise AssertionError("Discovery must not run the collector")


def _external_plugin(source_id: str = "external-example-source") -> CollectorPlugin:
    return CollectorPlugin(
        source_id=source_id,
        collector_factory=_ExternalCollector,
        collector_version="external-1",
        normalizer_version="rules-1",
        fixture_content_type="application/json",
        max_response_bytes=100_000,
        supports_network=True,
    )


class _FakeEntryPoint:
    def __init__(self, name: str, value: str, loaded: object) -> None:
        self.name = name
        self.value = value
        self.loaded = loaded
        self.load_count = 0

    def load(self) -> object:
        self.load_count += 1
        return self.loaded


class _FakeEntryPoints(tuple):
    def select(self, *, group: str):
        return self if group == "astrocareer.collectors" else ()


def test_builtin_plugins_have_valid_descriptors() -> None:
    references = collector_plugin_references()

    assert set(references) >= {"demo-html-source", "planetary-research-jobs-feed"}
    planetary = get_collector_plugin("planetary-research-jobs-feed")
    assert planetary.supports_network is True
    assert planetary.create_collector().source_id == planetary.source_id


def test_external_entry_point_is_lazy_and_loadable(monkeypatch: pytest.MonkeyPatch) -> None:
    entry_point = _FakeEntryPoint(
        "external-example-source",
        "external_package.collector:plugin",
        _external_plugin(),
    )
    monkeypatch.setattr(
        "astrocareer.plugins.metadata.entry_points",
        lambda: _FakeEntryPoints((entry_point,)),
    )

    references = collector_plugin_references()
    assert references[entry_point.name].origin == f"entry-point:{entry_point.value}"
    assert entry_point.load_count == 0

    plugin = get_collector_plugin(entry_point.name)
    assert plugin.collector_version == "external-1"
    assert entry_point.load_count == 1


def test_external_entry_point_identity_must_match(monkeypatch: pytest.MonkeyPatch) -> None:
    entry_point = _FakeEntryPoint(
        "declared-source",
        "external_package.collector:plugin",
        _external_plugin(),
    )
    monkeypatch.setattr(
        "astrocareer.plugins.metadata.entry_points",
        lambda: _FakeEntryPoints((entry_point,)),
    )

    with pytest.raises(PluginError, match="provided plugin"):
        get_collector_plugin("declared-source")


def test_external_plugin_cannot_override_builtin(monkeypatch: pytest.MonkeyPatch) -> None:
    entry_point = _FakeEntryPoint(
        "demo-html-source",
        "external_package.collector:plugin",
        _external_plugin("demo-html-source"),
    )
    monkeypatch.setattr(
        "astrocareer.plugins.metadata.entry_points",
        lambda: _FakeEntryPoints((entry_point,)),
    )

    with pytest.raises(PluginError, match="Duplicate collector plugin"):
        collector_plugin_references()


def test_invalid_external_entry_point_name_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry_point = _FakeEntryPoint(
        "Invalid Source ID",
        "external_package.collector:plugin",
        _external_plugin(),
    )
    monkeypatch.setattr(
        "astrocareer.plugins.metadata.entry_points",
        lambda: _FakeEntryPoints((entry_point,)),
    )

    with pytest.raises(PluginError, match="Invalid collector entry-point name"):
        collector_plugin_references()


def test_unknown_plugin_is_rejected() -> None:
    with pytest.raises(PluginError, match="No collector plugin"):
        get_collector_plugin("missing-source")
