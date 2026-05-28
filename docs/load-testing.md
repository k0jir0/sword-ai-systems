# Load Testing and Trend Tracking

## Purpose

This guide explains how to run repeatable load probes against `/rag/query` and store artifacts for trend comparison.

## Run a Load Probe

Start the API first, then run:

```bash
python scripts/load_test_rate_limit.py --base-url http://127.0.0.1:8080 --requests 80 --concurrency 20 --label local_baseline
```

Output includes:
- status counts (for example `status_200`, `status_429`)
- success and throttled rates
- persisted artifact path

Artifacts are written to:
- `data/load-testing-results/`

## Summarize Recent Runs

```bash
python scripts/summarize_load_tests.py --results-dir data/load-testing-results --limit 10
```

This prints a compact history of recent run metrics so you can compare reliability trends over time.

## Suggested Practice

1. Run one baseline probe before changing rate-limit logic.
2. Run the same probe after changes.
3. Compare `success_rate`, `throttled_rate`, and `status_counts` across artifacts.
4. Attach artifact paths to completion evidence in `docs/completion-report.md`.

## Scheduled Trend Reporting

A scheduled workflow generates a trend summary artifact weekly and on-demand:

- Workflow file: `.github/workflows/load-trend-report.yml`
- Trigger options:
	- `workflow_dispatch` for manual runs
	- weekly cron schedule
- Output artifact:
	- `load-trend-summary` (contains summary text from recent persisted load runs)
