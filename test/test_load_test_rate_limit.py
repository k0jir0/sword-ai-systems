from __future__ import annotations

from argparse import Namespace
from collections import Counter

from scripts.load_test_rate_limit import build_summary_payload, percentile


def test_percentile_interpolates_expected_values() -> None:
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile(values, 0) == 10.0
    assert percentile(values, 50) == 25.0
    assert percentile(values, 95) == 38.5
    assert percentile(values, 100) == 40.0


def test_build_summary_payload_includes_latency_stats() -> None:
    args = Namespace(
        base_url="http://127.0.0.1:8080",
        requests=10,
        concurrency=2,
        timeout=20.0,
        label="test",
    )

    payload = build_summary_payload(
        args=args,
        elapsed_seconds=2.0,
        status_counter=Counter({200: 8, 429: 2}),
        latency_seconds=[0.1, 0.2, 0.15, 0.12],
        timestamp="20260528T000000Z",
    )

    assert payload["success_rate"] == 0.8
    assert payload["throttled_rate"] == 0.2
    assert payload["latency_ms"]["avg"] == 142.5
    assert payload["latency_ms"]["p50"] == 135.0
    assert payload["latency_ms"]["p95"] == 192.5
