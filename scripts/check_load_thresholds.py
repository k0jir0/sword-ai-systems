from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate latest load-test artifact against thresholds.")
    parser.add_argument("--results-dir", default="data/load-testing-results")
    parser.add_argument("--max-p95-ms", type=float, default=2000.0)
    parser.add_argument("--max-throttled-rate", type=float, default=1.0)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Exit successfully when no artifacts exist.",
    )
    return parser.parse_args()


def latest_artifact(results_dir: Path) -> Path | None:
    candidates = sorted(results_dir.glob("load_test_*.json"), reverse=True)
    return candidates[0] if candidates else None


def load_latest_payload(results_dir: Path) -> tuple[Path, dict[str, Any]] | None:
    artifact = latest_artifact(results_dir)
    if artifact is None:
        return None

    payload = json.loads(artifact.read_text(encoding="utf-8-sig"))
    return artifact, payload


def evaluate_thresholds(
    payload: dict[str, Any],
    max_p95_ms: float,
    max_throttled_rate: float,
) -> list[str]:
    p95_ms = float(payload.get("latency_ms", {}).get("p95", 0.0))
    throttled_rate = float(payload.get("throttled_rate", 0.0))

    errors: list[str] = []
    if p95_ms > max_p95_ms:
        errors.append(f"Latency threshold failed: p95 {p95_ms:.2f}ms > allowed {max_p95_ms:.2f}ms")
    if throttled_rate > max_throttled_rate:
        errors.append(
            f"Throttled-rate threshold failed: {throttled_rate:.4f} > allowed {max_throttled_rate:.4f}"
        )
    return errors


def main() -> None:
    args = parse_args()
    results_dir = Path(args.results_dir)

    if not results_dir.exists():
        if args.allow_missing:
            print(f"No results directory found: {results_dir} (allowed)")
            return
        raise SystemExit(f"No results directory found: {results_dir}")

    latest = load_latest_payload(results_dir)
    if latest is None:
        if args.allow_missing:
            print(f"No load artifacts found in {results_dir} (allowed)")
            return
        raise SystemExit(f"No load artifacts found in {results_dir}")

    artifact, payload = latest
    p95_ms = float(payload.get("latency_ms", {}).get("p95", 0.0))
    throttled_rate = float(payload.get("throttled_rate", 0.0))

    print(f"artifact={artifact.as_posix()}")
    print(f"latency_ms_p95={p95_ms:.2f}")
    print(f"throttled_rate={throttled_rate:.4f}")

    errors = evaluate_thresholds(payload, args.max_p95_ms, args.max_throttled_rate)
    if errors:
        raise SystemExit("\n".join(errors))

    print("Load thresholds passed.")


if __name__ == "__main__":
    main()
