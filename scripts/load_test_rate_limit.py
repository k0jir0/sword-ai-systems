from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple concurrent load harness for /rag/query.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--requests", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--question", default="What are the core concepts covered?")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--label", default="", help="Optional run label included in output artifact name")
    parser.add_argument(
        "--output-dir",
        default="data/load-testing-results",
        help="Directory where load test JSON artifacts are written",
    )
    return parser.parse_args()


async def send_one(
    client: httpx.AsyncClient,
    base_url: str,
    question: str,
    api_key: str,
) -> tuple[int, float]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    started = perf_counter()
    try:
        response = await client.post(
            f"{base_url}/rag/query",
            json={"question": question},
            headers=headers,
        )
        return response.status_code, perf_counter() - started
    except httpx.HTTPError:
        return -1, perf_counter() - started


async def run_load(args: argparse.Namespace) -> list[tuple[int, float]]:
    limiter = asyncio.Semaphore(max(1, args.concurrency))

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        async def wrapped() -> tuple[int, float]:
            async with limiter:
                return await send_one(client, args.base_url, args.question, args.api_key)

        tasks = [asyncio.create_task(wrapped()) for _ in range(args.requests)]
        results = await asyncio.gather(*tasks)

    return results


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return min(values)
    if q >= 100:
        return max(values)

    ordered = sorted(values)
    rank = (len(ordered) - 1) * (q / 100)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def build_summary_payload(
    args: argparse.Namespace,
    elapsed_seconds: float,
    status_counter: Counter[int],
    latency_seconds: list[float],
    timestamp: str,
) -> dict[str, Any]:
    total = sum(status_counter.values())
    success = status_counter.get(200, 0)
    throttled = status_counter.get(429, 0)

    return {
        "timestamp_utc": timestamp,
        "base_url": args.base_url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "timeout_seconds": args.timeout,
        "label": args.label,
        "elapsed_seconds": round(elapsed_seconds, 4),
        "status_counts": {str(code): count for code, count in sorted(status_counter.items())},
        "success_rate": round(success / max(total, 1), 4),
        "throttled_rate": round(throttled / max(total, 1), 4),
        "latency_ms": {
            "avg": round((sum(latency_seconds) / max(len(latency_seconds), 1)) * 1000, 2),
            "p50": round(percentile(latency_seconds, 50) * 1000, 2),
            "p95": round(percentile(latency_seconds, 95) * 1000, 2),
            "max": round((max(latency_seconds) if latency_seconds else 0.0) * 1000, 2),
        },
    }


def main() -> None:
    args = parse_args()
    start = perf_counter()
    results = asyncio.run(run_load(args))
    elapsed = perf_counter() - start

    status_counter: Counter[int] = Counter(status for status, _ in results)
    latency_seconds = [latency for _, latency in results]

    total = sum(status_counter.values())
    print(f"total_requests={total}")
    print(f"concurrency={args.concurrency}")
    print(f"elapsed_seconds={elapsed:.2f}")

    for status_code in sorted(status_counter.keys()):
        print(f"status_{status_code}={status_counter[status_code]}")

    success = status_counter.get(200, 0)
    throttled = status_counter.get(429, 0)
    print(f"success_rate={success / max(total, 1):.2f}")
    print(f"throttled_rate={throttled / max(total, 1):.2f}")
    print(f"latency_ms_p50={percentile(latency_seconds, 50) * 1000:.2f}")
    print(f"latency_ms_p95={percentile(latency_seconds, 95) * 1000:.2f}")

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label_suffix = f"_{args.label.strip().replace(' ', '_')}" if args.label.strip() else ""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"load_test_{timestamp}{label_suffix}.json"

    payload = build_summary_payload(
        args=args,
        elapsed_seconds=elapsed,
        status_counter=status_counter,
        latency_seconds=latency_seconds,
        timestamp=timestamp,
    )

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"artifact_path={output_path.as_posix()}")


if __name__ == "__main__":
    main()
