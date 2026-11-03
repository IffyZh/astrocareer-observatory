"""Tests for immutable local capture and offline replay transports."""

from pathlib import Path

import pytest

from astrocareer.collectors import RequestSpec
from astrocareer.collectors.capture import CaptureError, CaptureTransport, ReplayTransport
from astrocareer.collectors.fixture import FixtureTransport


def _request() -> RequestSpec:
    return RequestSpec(
        source_id="planetary-research-jobs-feed",
        url="https://jobs.planetary-research.org/feed",
        purpose="job_listing_feed",
    )


def test_capture_round_trip_preserves_snapshot(tmp_path: Path) -> None:
    fixture = (
        Path(__file__).parents[1]
        / "fixtures"
        / "planetary_research_feed"
        / "normal.xml"
    )
    capture_path = tmp_path / "feed.capture.zip"
    original = CaptureTransport(
        FixtureTransport(fixture, content_type="application/atom+xml; charset=utf-8"),
        capture_path,
    ).fetch(_request())

    replayed = ReplayTransport(capture_path).fetch(_request())

    assert capture_path.exists()
    assert replayed.content == original.content
    assert replayed.content_sha256 == original.content_sha256
    assert replayed.content_type == original.content_type
    assert replayed.observed_at == original.observed_at


def test_capture_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    capture_path = tmp_path / "feed.capture.zip"
    capture_path.write_bytes(b"existing evidence")

    with pytest.raises(CaptureError, match="will not be overwritten"):
        CaptureTransport(FixtureTransport(capture_path), capture_path)


def test_replay_rejects_capture_for_another_source(tmp_path: Path) -> None:
    fixture = (
        Path(__file__).parents[1]
        / "fixtures"
        / "planetary_research_feed"
        / "normal.xml"
    )
    capture_path = tmp_path / "feed.capture.zip"
    CaptureTransport(FixtureTransport(fixture), capture_path).fetch(_request())
    wrong_request = RequestSpec(
        source_id="different-source",
        url="https://jobs.planetary-research.org/feed",
        purpose="test",
    )

    with pytest.raises(CaptureError, match="source does not match"):
        ReplayTransport(capture_path).fetch(wrong_request)
