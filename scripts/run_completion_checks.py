from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_step(command: list[str], cwd: Path, label: str) -> None:
    print(f"\n== {label} ==")
    print("$", " ".join(command))
    completed = subprocess.run(command, cwd=str(cwd), check=False)
    if completed.returncode != 0:
        raise SystemExit(f"Step failed: {label} (exit code {completed.returncode})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Sword roadmap completion quality checks.")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--min-retrieval-recall", type=float, default=1.0)
    parser.add_argument("--min-keyword-recall", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    run_step([args.python, "-m", "pytest", "-q"], repo_root, "Test Suite")

    run_step(
        [
            args.python,
            "scripts/eval_retrieval.py",
            "--path",
            "data/fixtures",
            "--glob",
            "core_expectations.txt",
            "--probe-file",
            "data/fixtures/retrieval_probes.txt",
            "--top-k",
            str(args.top_k),
            "--min-retrieval-recall",
            str(args.min_retrieval_recall),
            "--min-keyword-recall",
            str(args.min_keyword_recall),
        ],
        repo_root,
        "Retrieval Baseline Gate",
    )

    print("\nAll completion checks passed.")


if __name__ == "__main__":
    main()
