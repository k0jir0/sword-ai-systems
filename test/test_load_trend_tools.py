from __future__ import annotations

import json
from pathlib import Path

from scripts.check_load_thresholds import latest_artifact
from scripts.summarize_load_tests import format_payload_line, load_artifact_payloads


def test_load_artifact_payloads_reads_latest_first(tmp_path: Path) -> None:
    older = tmp_path / "load_test_20260101T000000Z.json"
    newer = tmp_path / "load_test_20260102T000000Z.json"

    older.write_text(json.dumps({"timestamp_utc": "older"}), encoding="utf-8")
    newer.write_text(json.dumps({"timestamp_utc": "newer"}), encoding="utf-8")

    payloads = load_artifact_payloads(tmp_path, limit=2)
    assert payloads[0]["timestamp_utc"] == "newer"
    assert payloads[1]["timestamp_utc"] == "older"


def test_format_payload_line_includes_key_fields() -> None:
    line = format_payload_line(
        {
            "timestamp_utc": "20260528T000000Z",
            "label": "baseline",
            "requests": 10,
            "concurrency": 2,
            "success_rate": 1.0,
            "throttled_rate": 0.0,
            "status_counts": {"200": 10},
            "_artifact_path": "data/load-testing-results/run.json",
        }
    )
    assert "timestamp=20260528T000000Z" in line
    assert "label=baseline" in line
    assert "status_counts={'200': 10}" in line


def test_latest_artifact_returns_most_recent_file(tmp_path: Path) -> None:
    (tmp_path / "load_test_20260101T000000Z.json").write_text("{}", encoding="utf-8")
    expected = tmp_path / "load_test_20260103T000000Z.json"
    expected.write_text("{}", encoding="utf-8")

    latest = latest_artifact(tmp_path)
    assert latest == expected
