from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

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
) -> int:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    try:
        response = await client.post(
            f"{base_url}/rag/query",
            json={"question": question},
            headers=headers,
        )
        return response.status_code
    except httpx.HTTPError:
        return -1


async def run_load(args: argparse.Namespace) -> Counter[int]:
    limiter = asyncio.Semaphore(max(1, args.concurrency))

    async with httpx.AsyncClient(timeout=args.timeout) as client:
        async def wrapped() -> int:
            async with limiter:
                return await send_one(client, args.base_url, args.question, args.api_key)

        tasks = [asyncio.create_task(wrapped()) for _ in range(args.requests)]
        statuses = await asyncio.gather(*tasks)

    return Counter(statuses)


def main() -> None:
    args = parse_args()
    start = perf_counter()
    status_counter = asyncio.run(run_load(args))
    elapsed = perf_counter() - start

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

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label_suffix = f"_{args.label.strip().replace(' ', '_')}" if args.label.strip() else ""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"load_test_{timestamp}{label_suffix}.json"

    payload = {
        "timestamp_utc": timestamp,
        "base_url": args.base_url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "timeout_seconds": args.timeout,
        "label": args.label,
        "elapsed_seconds": round(elapsed, 4),
        "status_counts": {str(code): count for code, count in sorted(status_counter.items())},
        "success_rate": round(success / max(total, 1), 4),
        "throttled_rate": round(throttled / max(total, 1), 4),
    }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"artifact_path={output_path.as_posix()}")


if __name__ == "__main__":
    main()
