"""Tests for the project command-line interface."""

from pathlib import Path

import pytest

from astrocareer.cli import main


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out == "astrocareer 0.0.0\n"


def test_empty_invocation() -> None:
    assert main([]) == 0


def test_database_init(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"

    assert main(["db", "init", str(database_path)]) == 0

    assert database_path.exists()
    assert "schema version 7" in capsys.readouterr().out


def test_database_seed_demo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"

    assert main(["db", "seed-demo", str(database_path)]) == 0
    assert main(["db", "seed-demo", str(database_path)]) == 0

    output = capsys.readouterr().out
    assert "Loaded fictional demonstration data" in output
    assert "already exists" in output


def test_database_sync_sources(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    registry_path = Path(__file__).parents[1] / "data" / "sources.toml"

    assert main(["db", "sync-sources", str(database_path), str(registry_path)]) == 0

    assert "Synchronized 4 source definition" in capsys.readouterr().out


def test_database_import_ror(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    project_root = Path(__file__).parents[1]
    arguments = [
        "db",
        "import-ror",
        str(database_path),
        str(project_root / "tests" / "fixtures" / "ror" / "schema-v2.1.json"),
        "--dataset-version",
        "v-test",
        "--registry",
        str(project_root / "data" / "sources.toml"),
    ]

    assert main(arguments) == 0
    assert main(arguments) == 0

    output = capsys.readouterr().out
    assert "ROR imported: version=v-test records=2 inserted=2 updated=0" in output
    assert "ROR reused: version=v-test records=2 inserted=2 updated=0" in output


def test_collect_fixture_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    project_root = Path(__file__).parents[1]

    assert (
        main(
            [
                "collect-fixture",
                "demo-html-source",
                str(project_root / "tests" / "fixtures" / "demo_source" / "normal.html"),
                "--database",
                str(database_path),
                "--registry",
                str(project_root / "data" / "sources.toml"),
                "--dry-run",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "dry-run: status=success" in output
    assert "records=2" in output
    assert "candidates=2" in output


def test_collect_planetary_feed_fixture_dry_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_path = tmp_path / "astrocareer.sqlite3"
    project_root = Path(__file__).parents[1]

    assert (
        main(
            [
                "collect-fixture",
                "planetary-research-jobs-feed",
                str(
                    project_root
                    / "tests"
                    / "fixtures"
                    / "planetary_research_feed"
                    / "normal.xml"
                ),
                "--database",
                str(database_path),
                "--registry",
                str(project_root / "data" / "sources.toml"),
                "--dry-run",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "dry-run: status=success" in output
    assert "records=2" in output
