from __future__ import annotations

import threading
from collections import defaultdict


class MetricsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.request_total = 0
        self.request_by_status: dict[int, int] = defaultdict(int)
        self.request_by_route: dict[str, int] = defaultdict(int)
        self.request_duration_seconds_total = 0.0

    def observe(self, status_code: int, route: str, duration_seconds: float) -> None:
        with self._lock:
            self.request_total += 1
            self.request_by_status[status_code] += 1
            self.request_by_route[route] += 1
            self.request_duration_seconds_total += duration_seconds

    def render_prometheus(self) -> str:
        lines = [
            "# HELP sword_requests_total Total number of HTTP requests",
            "# TYPE sword_requests_total counter",
            f"sword_requests_total {self.request_total}",
            "# HELP sword_request_duration_seconds_total Total HTTP request duration in seconds",
            "# TYPE sword_request_duration_seconds_total counter",
            f"sword_request_duration_seconds_total {self.request_duration_seconds_total:.6f}",
            "# HELP sword_requests_by_status Requests grouped by status code",
            "# TYPE sword_requests_by_status counter",
        ]

        for status_code, count in sorted(self.request_by_status.items()):
            lines.append(f'sword_requests_by_status{{status="{status_code}"}} {count}')

        lines.extend(
            [
                "# HELP sword_requests_by_route Requests grouped by route path",
                "# TYPE sword_requests_by_route counter",
            ]
        )
        for route, count in sorted(self.request_by_route.items()):
            safe_route = route.replace('"', "'")
            lines.append(f'sword_requests_by_route{{route="{safe_route}"}} {count}')

        return "\n".join(lines) + "\n"
