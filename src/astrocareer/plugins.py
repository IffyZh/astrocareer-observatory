"""Collector plugin contracts and lazy Python entry-point discovery."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import import_module, metadata

from astrocareer.collectors import Collector

COLLECTOR_PLUGIN_API_VERSION = 1
COLLECTOR_ENTRY_POINT_GROUP = "astrocareer.collectors"
_SOURCE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_BUILTIN_PLUGINS = {
    "demo-html-source": "astrocareer.collectors.demo:plugin",
    "planetary-research-jobs-feed": "astrocareer.collectors.planetary_research:plugin",
}


class PluginError(RuntimeError):
    """An installed collector plugin is missing, invalid, or ambiguous."""


@dataclass(frozen=True)
class CollectorPlugin:
    """Versioned descriptor for one source adapter."""

    source_id: str
    collector_factory: Callable[[], Collector] = field(repr=False)
    collector_version: str
    normalizer_version: str
    fixture_content_type: str
    max_response_bytes: int
    supports_network: bool
    api_version: int = COLLECTOR_PLUGIN_API_VERSION

    def __post_init__(self) -> None:
        if self.api_version != COLLECTOR_PLUGIN_API_VERSION:
            raise ValueError(
                f"Unsupported collector plugin API version: {self.api_version}"
            )
        if not _SOURCE_ID.fullmatch(self.source_id):
            raise ValueError(f"Invalid collector plugin source ID: {self.source_id!r}")
        for name, value in (
            ("collector_version", self.collector_version),
            ("normalizer_version", self.normalizer_version),
            ("fixture_content_type", self.fixture_content_type),
        ):
            if not value.strip():
                raise ValueError(f"Collector plugin {name} cannot be empty")
        if self.max_response_bytes <= 0:
            raise ValueError("Collector plugin response limit must be positive")

    def create_collector(self) -> Collector:
        """Create and validate a fresh collector instance."""
        try:
            collector = self.collector_factory()
        except Exception as error:
            raise PluginError(f"Plugin {self.source_id} could not create its collector") from error
        if not isinstance(collector, Collector):
            raise PluginError(f"Plugin {self.source_id} did not create a Collector")
        if collector.source_id != self.source_id:
            raise PluginError(
                f"Plugin {self.source_id} created collector for {collector.source_id}"
            )
        return collector


@dataclass(frozen=True)
class CollectorPluginReference:
    """A lazily loadable built-in or installed collector plugin."""

    source_id: str
    origin: str
    _loader: Callable[[], object] = field(repr=False)

    def load(self) -> CollectorPlugin:
        try:
            loaded = self._loader()
            plugin = (
                loaded()
                if callable(loaded) and not isinstance(loaded, CollectorPlugin)
                else loaded
            )
        except Exception as error:
            raise PluginError(
                f"Could not load collector plugin {self.source_id} from {self.origin}"
            ) from error
        if not isinstance(plugin, CollectorPlugin):
            raise PluginError(
                f"Collector entry {self.source_id} did not provide CollectorPlugin"
            )
        if plugin.source_id != self.source_id:
            raise PluginError(
                f"Collector entry {self.source_id} provided plugin {plugin.source_id}"
            )
        return plugin


def _load_attribute(location: str) -> object:
    module_name, attribute_name = location.split(":", 1)
    return getattr(import_module(module_name), attribute_name)


def collector_plugin_references() -> dict[str, CollectorPluginReference]:
    """Discover plugin names without importing external plugin modules."""
    references = {
        source_id: CollectorPluginReference(
            source_id=source_id,
            origin="built-in",
            _loader=lambda location=location: _load_attribute(location),
        )
        for source_id, location in _BUILTIN_PLUGINS.items()
    }
    entry_points = metadata.entry_points()
    selected = entry_points.select(group=COLLECTOR_ENTRY_POINT_GROUP)
    for entry_point in selected:
        source_id = entry_point.name
        if not _SOURCE_ID.fullmatch(source_id):
            raise PluginError(f"Invalid collector entry-point name: {source_id!r}")
        if source_id in references:
            raise PluginError(f"Duplicate collector plugin source ID: {source_id}")
        references[source_id] = CollectorPluginReference(
            source_id=source_id,
            origin=f"entry-point:{entry_point.value}",
            _loader=entry_point.load,
        )
    return dict(sorted(references.items()))


def get_collector_plugin(source_id: str) -> CollectorPlugin:
    """Load and validate the plugin registered for one source ID."""
    references = collector_plugin_references()
    try:
        reference = references[source_id]
    except KeyError as error:
        raise PluginError(f"No collector plugin is registered for {source_id}") from error
    return reference.load()
