from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
VENV_CANDIDATE_DIRS = [
    ROOT,
    ROOT.parent,
    ROOT.parent.parent,
]


def find_venv_python() -> Path | None:
    for base_dir in VENV_CANDIDATE_DIRS:
        candidate = base_dir / ".venv" / "Scripts" / "python.exe"
        if candidate.exists():
            return candidate
    return None


VENV_PYTHON = find_venv_python()


def project_python() -> str:
    if VENV_PYTHON is not None:
        return str(VENV_PYTHON)
    return sys.executable


def run_command(command: list[str]) -> int:
    """Run a command in the project root and return its exit code."""
    completed = subprocess.run(command, cwd=ROOT)
    return completed.returncode


def post_json(url: str, payload: dict, api_key: str = "") -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def wait_for_api(base_url: str, timeout_seconds: float = 20.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            payload = get_json(f"{base_url}/health")
            if payload.get("status") == "ok":
                return True
        except urllib.error.URLError:
            pass
        time.sleep(0.5)
    return False


def start_api(api_process: subprocess.Popen[str] | None) -> subprocess.Popen[str] | None:
    if api_process and api_process.poll() is None:
        print("API server is already running.")
        return api_process

    command = [
        project_python(),
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8080",
    ]
    process = subprocess.Popen(command, cwd=ROOT)  # noqa: S603
    time.sleep(1.0)
    if process.poll() is not None:
        print("API server failed to start. Check dependency installation and environment.")
        return None

    if wait_for_api(DEFAULT_BASE_URL, timeout_seconds=20.0):
        print("Started API server at http://127.0.0.1:8080")
    else:
        print("API process started but is not healthy yet; it may still be initializing.")
    return process


def stop_api(api_process: subprocess.Popen[str] | None) -> subprocess.Popen[str] | None:
    if not api_process or api_process.poll() is not None:
        print("API server is not running.")
        return None

    api_process.terminate()
    try:
        api_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        api_process.kill()
    print("Stopped API server.")
    return None


def check_health(base_url: str) -> None:
    last_error: urllib.error.URLError | None = None
    for _ in range(3):
        try:
            payload = get_json(f"{base_url}/health")
            print(json.dumps(payload, indent=2))
            return
        except urllib.error.URLError as error:
            last_error = error
            time.sleep(0.5)

    print(f"Health request failed: {last_error}")


def check_provider_health(base_url: str) -> None:
    try:
        payload = get_json(f"{base_url}/health/provider")
        print(json.dumps(payload, indent=2))
    except urllib.error.URLError as error:
        print(f"Provider health request failed: {error}")


def ingest_docs() -> None:
    path = input("Path to docs (default='.'): ").strip() or "."
    glob = input("Glob pattern (default='**/*.txt'): ").strip() or "**/*.txt"
    chunk_size = input("Chunk size (default=800): ").strip() or "800"
    chunk_overlap = input("Chunk overlap (default=120): ").strip() or "120"

    command = [
        project_python(),
        "scripts/ingest_docs.py",
        "--path",
        path,
        f"--glob={glob}",
        "--chunk-size",
        chunk_size,
        "--chunk-overlap",
        chunk_overlap,
    ]
    code = run_command(command)
    print(f"Ingest finished with exit code {code}")


def query_rag(base_url: str) -> None:
    question = input("Question: ").strip()
    if not question:
        print("Question is required.")
        return

    top_k_raw = input("top_k (default=4): ").strip() or "4"
    api_key = input("x-api-key (optional): ").strip()

    try:
        top_k = int(top_k_raw)
    except ValueError:
        print("top_k must be an integer.")
        return

    try:
        payload = post_json(
            f"{base_url}/rag/query",
            {"question": question, "top_k": top_k},
            api_key=api_key,
        )
        print(json.dumps(payload, indent=2))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        print(f"Query failed: HTTP {error.code}\n{body}")
    except urllib.error.URLError as error:
        print(f"Query request failed: {error}")


def run_completion_checks() -> None:
    code = run_command([project_python(), "scripts/run_completion_checks.py"])
    print(f"Completion checks finished with exit code {code}")


def print_menu() -> None:
    print("\nSword CLI Menu")
    print("1) Start API server")
    print("2) Stop API server")
    print("3) Check /health")
    print("4) Check /health/provider")
    print("5) Ingest documents")
    print("6) Query /rag/query")
    print("7) Run completion checks")
    print("8) Exit")


def main() -> None:
    base_url = DEFAULT_BASE_URL
    api_process: subprocess.Popen[str] | None = None

    print("Sword CLI: numbered access to common project actions.")
    print(f"Project root: {ROOT}")
    print(f"Python interpreter for actions: {project_python()}")
    if VENV_PYTHON is None:
        print("Warning: .venv interpreter not found; falling back to current Python executable.")

    while True:
        print_menu()
        choice = input("Select option (1-8): ").strip()

        if choice == "1":
            api_process = start_api(api_process)
        elif choice == "2":
            api_process = stop_api(api_process)
        elif choice == "3":
            check_health(base_url)
        elif choice == "4":
            check_provider_health(base_url)
        elif choice == "5":
            ingest_docs()
        elif choice == "6":
            query_rag(base_url)
        elif choice == "7":
            run_completion_checks()
        elif choice == "8":
            api_process = stop_api(api_process)
            print("Goodbye.")
            return
        else:
            print("Invalid selection. Choose a number from 1 to 8.")


if __name__ == "__main__":
    main()
