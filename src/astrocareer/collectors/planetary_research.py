"""Collector for the documented Planetary Research Jobs Atom feed."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

from astrocareer.collectors.base import (
    Checkpoint,
    CollectionBatch,
    CollectionStatus,
    IssueSeverity,
    ParseIssue,
    RawSnapshot,
    RequestSpec,
    SourcePosting,
    Transport,
)
from astrocareer.plugins import CollectorPlugin

ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
ATOM = f"{{{ATOM_NAMESPACE}}}"


@dataclass(frozen=True)
class _SummaryValue:
    text: str
    href: str | None = None


class _SummaryHTMLParser(HTMLParser):
    """Extract an allowlist-ready label map from the feed's summary box."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, _SummaryValue] = {}
        self._summary_depth = 0
        self._capturing_label = False
        self._label_parts: list[str] = []
        self._current_label: str | None = None
        self._value_parts: list[str] = []
        self._value_href: str | None = None

    @staticmethod
    def _attrs(attributes: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attributes}

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join(value.split())

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = self._attrs(attrs)
        classes = set(attributes.get("class", "").split())
        if tag == "div" and "job-summary-box" in classes:
            self._summary_depth = 1
            return
        if not self._summary_depth:
            return
        if tag == "div":
            self._summary_depth += 1
        elif tag == "span" and "job-label-header" in classes:
            self._finish_value()
            self._capturing_label = True
            self._label_parts = []
        elif tag == "br":
            self._finish_value()
        elif tag == "a" and self._current_label:
            self._value_href = attributes.get("href") or None

    def handle_data(self, data: str) -> None:
        if not self._summary_depth:
            return
        if self._capturing_label:
            self._label_parts.append(data)
        elif self._current_label:
            self._value_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._summary_depth:
            return
        if tag == "span" and self._capturing_label:
            label = self._clean("".join(self._label_parts)).rstrip(":").casefold()
            self._current_label = label or None
            self._capturing_label = False
            self._label_parts = []
        elif tag == "div":
            self._summary_depth -= 1
            if not self._summary_depth:
                self._finish_value()

    def close(self) -> None:
        super().close()
        self._finish_value()

    def _finish_value(self) -> None:
        if self._current_label:
            text = self._clean("".join(self._value_parts))
            if text or self._value_href:
                self.values.setdefault(
                    self._current_label,
                    _SummaryValue(text=text, href=self._value_href),
                )
        self._current_label = None
        self._value_parts = []
        self._value_href = None


class PlanetaryResearchFeedCollector:
    """Read one public Atom feed without following announcement links."""

    source_id = "planetary-research-jobs-feed"
    feed_url = "https://jobs.planetary-research.org/feed"
    _host = "jobs.planetary-research.org"
    _record_id = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
    _content_types = {
        "application/atom+xml",
        "application/xml",
        "text/xml",
    }
    _maximum_entries = 1_000

    def collect(
        self,
        transport: Transport,
        checkpoint: Checkpoint | None = None,
    ) -> CollectionBatch:
        del checkpoint  # HTTP validators are managed by the shared transport.
        snapshot = transport.fetch(
            RequestSpec(
                source_id=self.source_id,
                url=self.feed_url,
                purpose="job_listing_feed",
                headers=(("Accept", "application/atom+xml,application/xml;q=0.9"),),
            )
        )
        return self.parse(snapshot)

    def parse(self, snapshot: RawSnapshot) -> CollectionBatch:
        if snapshot.source_id != self.source_id:
            raise ValueError("Snapshot belongs to a different source")
        if snapshot.status_code == 304:
            return CollectionBatch(
                source_id=self.source_id,
                status=CollectionStatus.NOT_MODIFIED,
                snapshots=(snapshot,),
                records=(),
                issues=(),
            )
        if snapshot.status_code != 200:
            return self._failure(
                snapshot,
                "unexpected_http_status",
                f"Expected HTTP 200, received {snapshot.status_code}.",
            )
        content_type = (snapshot.content_type or "").split(";", 1)[0].strip().lower()
        if content_type not in self._content_types:
            return self._failure(
                snapshot,
                "unexpected_content_type",
                f"Expected an Atom/XML response, received {snapshot.content_type!r}.",
            )
        upper_prefix = snapshot.content[:4096].upper()
        if b"<!DOCTYPE" in upper_prefix or b"<!ENTITY" in upper_prefix:
            return self._failure(
                snapshot,
                "unsafe_xml_declaration",
                "DTD and entity declarations are not accepted.",
            )
        try:
            root = ET.fromstring(snapshot.content)
        except ET.ParseError as error:
            return self._failure(snapshot, "malformed_xml", f"Invalid XML: {error}.")
        if root.tag != f"{ATOM}feed":
            return self._failure(
                snapshot,
                "unexpected_feed_structure",
                "Expected an Atom feed root in the standard namespace.",
            )
        feed_id = self._element_text(root.find(f"{ATOM}id"))
        if feed_id != self.feed_url:
            return self._failure(
                snapshot,
                "unexpected_feed_identity",
                f"Expected feed ID {self.feed_url!r}, received {feed_id!r}.",
            )

        entries = root.findall(f"{ATOM}entry")
        if len(entries) > self._maximum_entries:
            return self._failure(
                snapshot,
                "entry_limit_exceeded",
                f"Feed contains more than {self._maximum_entries} entries.",
            )

        records: list[SourcePosting] = []
        issues: list[ParseIssue] = []
        seen_ids: set[str] = set()
        for index, entry in enumerate(entries):
            try:
                record = self._parse_entry(entry, snapshot)
            except ValueError as error:
                issues.append(
                    ParseIssue(
                        severity=IssueSeverity.ERROR,
                        code="malformed_feed_entry",
                        message=str(error),
                        locator=f"entry[{index}]",
                    )
                )
                continue
            if record.source_record_id in seen_ids:
                issues.append(
                    ParseIssue(
                        severity=IssueSeverity.ERROR,
                        code="duplicate_source_record_id",
                        message=f"Duplicate source record ID: {record.source_record_id}",
                        source_record_id=record.source_record_id,
                        locator=f"entry[{index}]",
                    )
                )
                continue
            seen_ids.add(record.source_record_id)
            records.append(record)

        if entries and not records:
            status = CollectionStatus.FAILED
        elif issues:
            status = CollectionStatus.PARTIAL
        else:
            status = CollectionStatus.SUCCESS
        updated = self._element_text(root.find(f"{ATOM}updated"))
        return CollectionBatch(
            source_id=self.source_id,
            status=status,
            snapshots=(snapshot,),
            records=tuple(records) if status is not CollectionStatus.FAILED else (),
            issues=tuple(issues),
            next_checkpoint=Checkpoint(updated) if updated else None,
        )

    def _parse_entry(self, entry: ET.Element, snapshot: RawSnapshot) -> SourcePosting:
        entry_id = self._required_text(entry, "id")
        title = self._required_text(entry, "title")
        canonical_url = self._entry_link(entry)
        record_id = self._validated_record_id(entry_id, canonical_url)
        published = self._element_text(entry.find(f"{ATOM}published"))
        category = self._element_text(entry.find(f"{ATOM}summary"))

        summary_fields: dict[str, _SummaryValue] = {}
        content = entry.find(f"{ATOM}content")
        if content is not None and content.get("type", "").casefold() == "html" and content.text:
            parser = _SummaryHTMLParser()
            parser.feed(content.text)
            parser.close()
            summary_fields = parser.values

        def value(label: str) -> str | None:
            item = summary_fields.get(label)
            return item.text if item and item.text else None

        raw_fields: list[tuple[str, str]] = []
        for output_name, label in (
            ("source_category", "category"),
            ("department", "department"),
            ("number_of_positions", "number of positions"),
            ("extension_terms", "can be extended"),
            ("reference_code", "reference code"),
        ):
            raw_value = category if label == "category" else value(label)
            if raw_value:
                raw_fields.append((output_name, raw_value))
        official = summary_fields.get("official announcement")
        if official and official.href:
            raw_fields.append(("official_announcement_url", official.href))

        # Contact names, email addresses, poster names, ORCIDs, and the full job
        # description are intentionally excluded from SourcePosting.
        return SourcePosting(
            source_id=self.source_id,
            source_record_id=record_id,
            snapshot_url=snapshot.url,
            snapshot_sha256=snapshot.content_sha256,
            canonical_url=canonical_url,
            official_title=title,
            institution_text=value("institution"),
            location_text=value("location"),
            posted_at_text=value("posted") or published,
            deadline_text=value("application deadline"),
            contract_text=value("duration"),
            salary_text=value("salary"),
            start_date_text=value("start date"),
            work_mode_text=value("work arrangement"),
            raw_fields=tuple(raw_fields),
        )

    def _entry_link(self, entry: ET.Element) -> str:
        links = entry.findall(f"{ATOM}link")
        candidates = [
            link.get("href", "")
            for link in links
            if link.get("rel", "alternate") in {"alternate", ""}
        ]
        url = next((candidate for candidate in candidates if candidate), "")
        if not url:
            raise ValueError("Entry is missing its canonical link")
        return url

    def _validated_record_id(self, entry_id: str, canonical_url: str) -> str:
        if entry_id != canonical_url:
            raise ValueError("Entry ID and canonical link do not match")
        parsed = urlparse(canonical_url)
        if parsed.scheme != "https" or parsed.hostname != self._host:
            raise ValueError("Entry URL is outside the reviewed source host")
        if parsed.query or parsed.fragment:
            raise ValueError("Entry URL must not contain a query or fragment")
        record_id = parsed.path.strip("/")
        if "/" in record_id or not self._record_id.fullmatch(record_id):
            raise ValueError("Entry URL does not contain a valid stable record ID")
        return record_id

    def _required_text(self, entry: ET.Element, local_name: str) -> str:
        value = self._element_text(entry.find(f"{ATOM}{local_name}"))
        if not value:
            raise ValueError(f"Entry is missing required Atom field: {local_name}")
        return value

    @staticmethod
    def _element_text(element: ET.Element | None) -> str | None:
        if element is None or element.text is None:
            return None
        value = " ".join(element.text.split())
        return value or None

    def _failure(
        self,
        snapshot: RawSnapshot,
        code: str,
        message: str,
    ) -> CollectionBatch:
        return CollectionBatch(
            source_id=self.source_id,
            status=CollectionStatus.FAILED,
            snapshots=(snapshot,),
            records=(),
            issues=(
                ParseIssue(
                    severity=IssueSeverity.ERROR,
                    code=code,
                    message=message,
                ),
            ),
        )


plugin = CollectorPlugin(
    source_id=PlanetaryResearchFeedCollector.source_id,
    collector_factory=PlanetaryResearchFeedCollector,
    collector_version="planetary-research-feed-1",
    normalizer_version="rules-1",
    fixture_content_type="application/atom+xml; charset=utf-8",
    max_response_bytes=2_000_000,
    supports_network=True,
)
