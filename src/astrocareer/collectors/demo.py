"""A fictional HTML collector used to prove the collector contract."""

from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

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


@dataclass
class _ParsedArticle:
    record_id: str
    url: str | None = None
    title: str | None = None
    institution: str | None = None
    location: str | None = None
    posted_at: str | None = None
    deadline: str | None = None
    contract: str | None = None
    salary: str | None = None
    employment_fraction: str | None = None
    start_date: str | None = None
    work_mode: str | None = None
    languages: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    international: str | None = None


class _DemoHTMLParser(HTMLParser):
    """Parse the deliberately small and documented demo fixture format."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_listing_marker = False
        self.explicitly_empty = False
        self.articles: list[_ParsedArticle] = []
        self._article: _ParsedArticle | None = None
        self._field: str | None = None
        self._list_kind: str | None = None
        self._text: list[str] = []

    @staticmethod
    def _attrs(attributes: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attributes}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = self._attrs(attrs)
        if tag == "main" and "data-astrocareer-listing" in attributes:
            self.has_listing_marker = True
        if tag == "p" and attributes.get("data-empty") == "true":
            self.explicitly_empty = True
        if tag == "article" and "data-job-id" in attributes:
            self._article = _ParsedArticle(record_id=attributes["data-job-id"])
            self._text = []
            return
        if self._article is None:
            return
        classes = set(attributes.get("class", "").split())
        if tag == "a" and "job-link" in classes:
            self._article.url = attributes.get("href")
            self._field = "title"
        elif tag == "p" and "institution" in classes:
            self._field = "institution"
        elif tag == "p" and "location" in classes:
            self._field = "location"
        elif tag == "p" and "international" in classes:
            self._field = "international"
        elif tag == "p" and "contract" in classes:
            self._field = "contract"
        elif tag == "p" and "salary" in classes:
            self._field = "salary"
        elif tag == "p" and "employment-fraction" in classes:
            self._field = "employment_fraction"
        elif tag == "p" and "start-date" in classes:
            self._field = "start_date"
        elif tag == "p" and "work-mode" in classes:
            self._field = "work_mode"
        elif tag == "time" and "posted" in classes:
            self._article.posted_at = attributes.get("datetime") or None
        elif tag == "time" and "deadline" in classes:
            self._article.deadline = attributes.get("datetime") or None
        elif tag == "ul" and "requirements" in classes:
            self._list_kind = "requirements"
        elif tag == "ul" and "skills" in classes:
            self._list_kind = "skills"
        elif tag == "ul" and "languages" in classes:
            self._list_kind = "languages"
        elif tag == "li" and self._list_kind:
            self._field = self._list_kind
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._article is not None and self._field is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._article is None:
            return
        if tag in {"a", "p", "li"} and self._field:
            value = " ".join("".join(self._text).split())
            if value:
                if self._field == "requirements":
                    self._article.requirements.append(value)
                elif self._field == "skills":
                    self._article.skills.append(value)
                elif self._field == "languages":
                    self._article.languages.append(value)
                else:
                    setattr(self._article, self._field, value)
            self._field = None
            self._text = []
        if tag == "ul":
            self._list_kind = None
        if tag == "article":
            self.articles.append(self._article)
            self._article = None
            self._field = None
            self._list_kind = None
            self._text = []


class DemoCollector:
    """Collect a fictional listing without depending on a real website."""

    source_id = "demo-html-source"
    listing_url = "https://careers.example-observatory.test/jobs/"

    def collect(
        self,
        transport: Transport,
        checkpoint: Checkpoint | None = None,
    ) -> CollectionBatch:
        del checkpoint  # The demo source always returns a complete listing.
        request = RequestSpec(
            source_id=self.source_id,
            url=self.listing_url,
            purpose="job_listing",
        )
        snapshot = transport.fetch(request)
        return self.parse(snapshot)

    def parse(self, snapshot: RawSnapshot) -> CollectionBatch:
        """Parse one demo listing snapshot without network or database access."""
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
        if not snapshot.content_type or "text/html" not in snapshot.content_type.lower():
            return self._failure(
                snapshot,
                "unexpected_content_type",
                f"Expected HTML, received {snapshot.content_type!r}.",
            )
        try:
            html = snapshot.content.decode("utf-8")
        except UnicodeDecodeError:
            return self._failure(
                snapshot,
                "invalid_encoding",
                "The response is not valid UTF-8.",
            )

        parser = _DemoHTMLParser()
        parser.feed(html)
        parser.close()
        if not parser.has_listing_marker:
            return self._failure(
                snapshot,
                "unexpected_page_structure",
                "The expected job-listing marker is missing.",
            )
        if not parser.articles:
            if parser.explicitly_empty:
                return CollectionBatch(
                    source_id=self.source_id,
                    status=CollectionStatus.SUCCESS,
                    snapshots=(snapshot,),
                    records=(),
                    issues=(),
                )
            return self._failure(
                snapshot,
                "zero_records_detected",
                "No job records were found and the source did not declare an empty listing.",
            )

        records: list[SourcePosting] = []
        issues: list[ParseIssue] = []
        seen_ids: set[str] = set()
        for article in parser.articles:
            if article.record_id in seen_ids:
                issues.append(
                    ParseIssue(
                        severity=IssueSeverity.ERROR,
                        code="duplicate_source_record_id",
                        message=f"Duplicate source record ID: {article.record_id}",
                        source_record_id=article.record_id,
                    )
                )
                continue
            seen_ids.add(article.record_id)
            missing = [
                name
                for name, value in (("title", article.title), ("url", article.url))
                if not value
            ]
            if missing:
                issues.append(
                    ParseIssue(
                        severity=IssueSeverity.ERROR,
                        code="missing_required_field",
                        message=f"Missing required fields: {', '.join(missing)}",
                        source_record_id=article.record_id,
                    )
                )
                continue
            records.append(
                SourcePosting(
                    source_id=self.source_id,
                    source_record_id=article.record_id,
                    snapshot_url=snapshot.url,
                    snapshot_sha256=snapshot.content_sha256,
                    canonical_url=urljoin(snapshot.url, article.url or ""),
                    official_title=article.title or "",
                    institution_text=article.institution,
                    location_text=article.location,
                    posted_at_text=article.posted_at,
                    deadline_text=article.deadline,
                    contract_text=article.contract,
                    salary_text=article.salary,
                    employment_fraction_text=article.employment_fraction,
                    start_date_text=article.start_date,
                    work_mode_text=article.work_mode,
                    language_texts=tuple(article.languages),
                    requirement_texts=tuple(article.requirements),
                    skill_texts=tuple(article.skills),
                    international_eligibility_text=article.international,
                )
            )

        if issues and not records:
            status = CollectionStatus.FAILED
        elif issues:
            status = CollectionStatus.PARTIAL
        else:
            status = CollectionStatus.SUCCESS
        return CollectionBatch(
            source_id=self.source_id,
            status=status,
            snapshots=(snapshot,),
            records=tuple(records) if status is not CollectionStatus.FAILED else (),
            issues=tuple(issues),
        )

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
