from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize persisted load test artifacts.")
    parser.add_argument("--results-dir", default="data/load-testing-results")
    parser.add_argument("--limit", type=int, default=10, help="Number of most recent runs to display")
    return parser.parse_args()


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

    selected = files[: max(1, args.limit)]
    print(f"load_test_artifact_count={len(files)}")
    print(f"showing={len(selected)}")

    for artifact in selected:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        status_counts = payload.get("status_counts", {})
        print(
            " | ".join(
                [
                    f"timestamp={payload.get('timestamp_utc', 'unknown')}",
                    f"label={payload.get('label', '')}",
                    f"requests={payload.get('requests', 0)}",
                    f"concurrency={payload.get('concurrency', 0)}",
                    f"success_rate={payload.get('success_rate', 0):.2f}",
                    f"throttled_rate={payload.get('throttled_rate', 0):.2f}",
                    f"status_counts={status_counts}",
                    f"artifact={artifact.as_posix()}",
                ]
            )
        )


if __name__ == "__main__":
    main()
