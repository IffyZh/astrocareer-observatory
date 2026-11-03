"""Local read-only web browser for an AstroCareer SQLite database."""

import json
import sqlite3
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlparse


_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


def _read_only_connection(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"{database_path.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _value(document: dict[str, object], *keys: str) -> object | None:
    current: object = document
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def load_browser_records(database_path: Path) -> list[dict[str, object]]:
    """Return the latest reviewable candidate for every stable source record."""
    if not database_path.is_file():
        raise FileNotFoundError(f"Database does not exist: {database_path}")
    with _read_only_connection(database_path) as connection:
        rows = connection.execute(
            """
            WITH ranked AS (
                SELECT
                    sro.source_id,
                    sro.source_record_id,
                    sro.observed_at,
                    nc.normalizer_version,
                    nc.review_status,
                    nc.candidate_json,
                    row_number() OVER (
                        PARTITION BY sro.source_id, sro.source_record_id
                        ORDER BY sro.observed_at DESC, nc.created_at DESC
                    ) AS candidate_rank
                FROM normalization_candidates nc
                JOIN source_record_observations sro
                  ON sro.source_record_observation_id = nc.source_record_observation_id
                JOIN sources source
                  ON source.source_id = sro.source_id
                WHERE nc.review_status IN ('pending', 'accepted')
                  AND source.enabled = 1
            )
            SELECT * FROM ranked
            WHERE candidate_rank = 1
            ORDER BY observed_at DESC, source_record_id
            """
        ).fetchall()

    records: list[dict[str, object]] = []
    for row in rows:
        candidate = json.loads(row["candidate_json"])
        compensation = candidate.get("compensation") or {}
        records.append(
            {
                "source_id": row["source_id"],
                "source_record_id": row["source_record_id"],
                "observed_at": row["observed_at"],
                "normalizer_version": row["normalizer_version"],
                "review_status": row["review_status"],
                "title": candidate.get("normalized_title") or candidate.get("official_title"),
                "official_title": candidate.get("official_title"),
                "category": candidate.get("source_category_text"),
                "job_family": _value(candidate, "job_family", "value"),
                "job_family_availability": _value(
                    candidate, "job_family", "availability"
                ),
                "institution": candidate.get("institution_text"),
                "department": candidate.get("department_text"),
                "location": candidate.get("location_text"),
                "posted_at": _value(candidate, "posted_at", "value"),
                "deadline": _value(candidate, "application_deadline_at", "value"),
                "positions": _value(candidate, "positions_available", "value"),
                "positions_availability": _value(
                    candidate, "positions_available", "availability"
                ),
                "duration_months": _value(
                    candidate,
                    "employment_terms",
                    "contract_duration_months",
                    "value",
                ),
                "duration_text": _value(
                    candidate,
                    "employment_terms",
                    "contract_duration_months",
                    "official_text",
                ),
                "start_date": _value(
                    candidate, "employment_terms", "start_date", "value"
                ),
                "start_date_text": _value(
                    candidate, "employment_terms", "start_date", "official_text"
                ),
                "work_mode": _value(
                    candidate, "employment_terms", "work_mode", "value"
                ),
                "work_mode_text": _value(
                    candidate, "employment_terms", "work_mode", "official_text"
                ),
                "extension_possible": _value(candidate, "extension_possible", "value"),
                "extension_text": _value(
                    candidate, "extension_possible", "official_text"
                ),
                "salary_text": compensation.get("official_text"),
                "salary_min": compensation.get("amount_min"),
                "salary_max": compensation.get("amount_max"),
                "salary_currency": compensation.get("currency"),
                "salary_period": compensation.get("pay_period"),
                "salary_availability": compensation.get("availability"),
                "reference_code": candidate.get("reference_code_text"),
                "canonical_url": candidate.get("canonical_url"),
                "official_announcement_url": candidate.get("official_announcement_url"),
            }
        )
    return records


def _asset(name: str) -> bytes:
    return (
        files("astrocareer")
        .joinpath("browser_assets")
        .joinpath(name)
        .read_bytes()
    )


def _handler(database_path: Path) -> type[BaseHTTPRequestHandler]:
    class BrowserHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/postings":
                try:
                    payload = json.dumps(
                        load_browser_records(database_path),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                except (FileNotFoundError, json.JSONDecodeError, sqlite3.Error) as error:
                    self._send(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        json.dumps({"error": str(error)}).encode("utf-8"),
                        "application/json; charset=utf-8",
                    )
                    return
                self._send(HTTPStatus.OK, payload, "application/json; charset=utf-8")
                return
            asset = _ASSETS.get(path)
            if asset is None:
                self._send(
                    HTTPStatus.NOT_FOUND,
                    b"Not found",
                    "text/plain; charset=utf-8",
                )
                return
            name, content_type = asset
            self._send(HTTPStatus.OK, _asset(name), content_type)

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'none'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    return BrowserHandler


def serve_database(
    database_path: Path,
    *,
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    """Serve the browser on loopback until interrupted."""
    load_browser_records(database_path)
    server = ThreadingHTTPServer(("127.0.0.1", port), _handler(database_path))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"AstroCareer database browser: {url}")
    print("Read-only local service. Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.2, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDatabase browser stopped.")
    finally:
        server.server_close()
