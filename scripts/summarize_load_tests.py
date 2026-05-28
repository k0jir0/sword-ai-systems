from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.check_load_thresholds import evaluate_thresholds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize persisted load test artifacts.")
    parser.add_argument("--results-dir", default="data/load-testing-results")
    parser.add_argument("--limit", type=int, default=10, help="Number of most recent runs to display")
    parser.add_argument("--format", choices=("text", "markdown"), default="text")
    parser.add_argument("--max-p95-ms", type=float, default=None)
    parser.add_argument("--max-throttled-rate", type=float, default=None)
    return parser.parse_args()


def load_artifact_payloads(results_dir: Path, limit: int) -> list[dict[str, Any]]:
    files = sorted(results_dir.glob("load_test_*.json"), reverse=True)
    selected = files[: max(1, limit)]

    payloads: list[dict[str, Any]] = []
    for artifact in selected:
        payload = json.loads(artifact.read_text(encoding="utf-8-sig"))
        payload["_artifact_path"] = artifact.as_posix()
        payloads.append(payload)

    return payloads


def format_payload_line(payload: dict[str, Any]) -> str:
    status_counts = payload.get("status_counts", {})
    return " | ".join(
        [
            f"timestamp={payload.get('timestamp_utc', 'unknown')}",
            f"label={payload.get('label', '')}",
            f"requests={payload.get('requests', 0)}",
            f"concurrency={payload.get('concurrency', 0)}",
            f"success_rate={payload.get('success_rate', 0):.2f}",
            f"throttled_rate={payload.get('throttled_rate', 0):.2f}",
            f"status_counts={status_counts}",
            f"artifact={payload.get('_artifact_path', '')}",
        ]
    )


def render_markdown_dashboard(
    payloads: list[dict[str, Any]],
    max_p95_ms: float | None = None,
    max_throttled_rate: float | None = None,
) -> str:
    lines = ["# Load Test Dashboard", "", f"Runs shown: {len(payloads)}", ""]
    columns = ["timestamp", "label", "success_rate", "throttled_rate", "p95_ms", "artifact"]
    include_thresholds = max_p95_ms is not None and max_throttled_rate is not None
    if include_thresholds:
        columns.insert(5, "thresholds")

    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")

    for payload in payloads:
        latency_ms = payload.get("latency_ms", {})
        row = [
            str(payload.get("timestamp_utc", "unknown")),
            str(payload.get("label", "")),
            f"{float(payload.get('success_rate', 0.0)):.2f}",
            f"{float(payload.get('throttled_rate', 0.0)):.2f}",
            f"{float(latency_ms.get('p95', 0.0)):.2f}",
        ]
        if include_thresholds:
            errors = evaluate_thresholds(payload, max_p95_ms, max_throttled_rate)
            row.append("pass" if not errors else "fail")
        row.append(str(payload.get("_artifact_path", "")))
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"No results directory found: {results_dir}")
        return

    files = sorted(results_dir.glob("load_test_*.json"), reverse=True)
    if not files:
        print(f"No load test artifacts found in: {results_dir}")
        return

    payloads = load_artifact_payloads(results_dir, args.limit)
    if args.format == "markdown":
        print(render_markdown_dashboard(payloads, args.max_p95_ms, args.max_throttled_rate))
        return

    print(f"load_test_artifact_count={len(files)}")
    print(f"showing={len(payloads)}")

    for payload in payloads:
        print(format_payload_line(payload))


if __name__ == "__main__":
    main()
