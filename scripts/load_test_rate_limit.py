from __future__ import annotations

import argparse
import asyncio
from collections import Counter
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

    response = await client.post(
        f"{base_url}/rag/query",
        json={"question": question},
        headers=headers,
    )
    return response.status_code


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


if __name__ == "__main__":
    main()
