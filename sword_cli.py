"""
Sword AI Systems — Interactive CLI
===================================
Sectioned main menu with sub-menus.
Run:  python sword_cli.py

Sections:
  [1] Server         — lifecycle, logs
  [2] RAG            — ingest, query, eval
  [3] Learning       — MLP demo, Transformer demo
  [4] Reliability    — tests, load test, completion checks
  [5] Configuration  — settings, metrics
  [0] Exit
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
LOGS_DIR = ROOT / "logs"
API_LOG_FILE = LOGS_DIR / "api-server.log"
FIXTURES_DIR = ROOT / "data" / "fixtures"
GROUNDING_PROBES = FIXTURES_DIR / "grounding_probes.txt"

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


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def run_command(command: list[str]) -> int:
    """Run a command in the project root, streaming output. Returns exit code."""
    completed = subprocess.run(command, cwd=ROOT)  # noqa: S603
    return completed.returncode


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def post_json(url: str, payload: dict, api_key: str = "") -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def get_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310
        return response.read().decode("utf-8")


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


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _sep(char: str = "-", width: int = 52) -> None:
    print(char * width)


def _header(title: str) -> None:
    _sep("=")
    print(f"  {title}")
    _sep("=")


def _prompt(text: str, default: str = "") -> str:
    if default:
        raw = input(f"  {text} [{default}]: ").strip()
        return raw if raw else default
    return input(f"  {text}: ").strip()


def _yn(question: str) -> bool:
    return _prompt(f"{question} (y/n)", "n").lower().startswith("y")


def _section_choice(section: str, options: list[tuple[str, str]]) -> str:
    _sep()
    print(f"  {section}")
    _sep()
    for key, label in options:
        print(f"  {key}) {label}")
    _sep()
    return input("  Choice: ").strip()


# ---------------------------------------------------------------------------
# [1] SERVER
# ---------------------------------------------------------------------------

def start_api(api_process: subprocess.Popen | None) -> subprocess.Popen | None:
    if api_process and api_process.poll() is None:
        print("  API server is already running.")
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
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with API_LOG_FILE.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(  # noqa: S603
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
    time.sleep(1.0)
    if process.poll() is not None:
        print(f"  API server failed to start.  Logs: {API_LOG_FILE}")
        return None
    if wait_for_api(DEFAULT_BASE_URL, timeout_seconds=20.0):
        print(f"  Started and verified healthy at {DEFAULT_BASE_URL}")
        print(f"  Logs: {API_LOG_FILE}")
    else:
        print(f"  Process started but /health not ready yet.  Logs: {API_LOG_FILE}")
    return process


def stop_api(api_process: subprocess.Popen | None) -> subprocess.Popen | None:
    if not api_process or api_process.poll() is not None:
        print("  API server is not running.")
        return None
    api_process.terminate()
    try:
        api_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        api_process.kill()
    print("  API server stopped.")
    return None


def restart_api(api_process: subprocess.Popen | None) -> subprocess.Popen | None:
    process = stop_api(api_process)
    time.sleep(0.5)
    return start_api(process)


def api_status(api_process: subprocess.Popen | None) -> None:
    if not api_process or api_process.poll() is not None:
        print("  Process: not running")
        return
    print(f"  Process: running (pid {api_process.pid})")
    for _ in range(3):
        try:
            payload = get_json(f"{DEFAULT_BASE_URL}/health")
            print(f"  Health:  {json.dumps(payload)}")
            return
        except urllib.error.URLError:
            time.sleep(0.5)
    print("  Health:  unreachable")


def view_server_logs(n_lines: int = 40) -> None:
    if not API_LOG_FILE.exists():
        print(f"  Log file does not exist yet: {API_LOG_FILE}")
        return
    raw = _prompt("Lines to show", str(n_lines))
    try:
        lines_to_show = int(raw)
    except ValueError:
        lines_to_show = n_lines
    all_lines = API_LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = all_lines[-lines_to_show:]
    _sep()
    print(f"  Last {len(tail)} lines from {API_LOG_FILE.name}:")
    _sep()
    for line in tail:
        print(f"  {line}")
    _sep()


def _section_server(api_process: subprocess.Popen | None) -> subprocess.Popen | None:
    while True:
        choice = _section_choice(
            "[1] SERVER",
            [
                ("1", "Start API server"),
                ("2", "Stop API server"),
                ("3", "Restart API server"),
                ("4", "API status"),
                ("5", "View server logs"),
                ("0", "Back"),
            ],
        )
        if choice == "1":
            api_process = start_api(api_process)
        elif choice == "2":
            api_process = stop_api(api_process)
        elif choice == "3":
            api_process = restart_api(api_process)
        elif choice == "4":
            api_status(api_process)
        elif choice == "5":
            view_server_logs()
        elif choice == "0":
            break
        else:
            print("  Unknown option.")
    return api_process


# ---------------------------------------------------------------------------
# [2] RAG
# ---------------------------------------------------------------------------

def ingest_via_script() -> None:
    path = _prompt("Path to docs directory", ".")
    glob = _prompt("Glob pattern", "**/*.txt")
    chunk_size = _prompt("Chunk size", "800")
    chunk_overlap = _prompt("Chunk overlap", "120")
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
    print(f"  Ingest script exited with code {code}.")


def ingest_via_api() -> None:
    print("  Enter documents to ingest.  Empty line to finish.")
    documents: list[str] = []
    while True:
        doc = input(f"  Document {len(documents) + 1}: ").strip()
        if not doc:
            break
        documents.append(doc)
    if not documents:
        print("  No documents provided.")
        return
    api_key = _prompt("x-api-key (optional)", "")
    try:
        payload = post_json(
            f"{DEFAULT_BASE_URL}/rag/ingest",
            {"documents": documents},
            api_key=api_key,
        )
        print(f"\n  Indexed: {payload.get('indexed_documents', '?')} document(s)")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        print(f"  HTTP {error.code}: {body}")
    except urllib.error.URLError as error:
        print(f"  Request failed: {error}")


def query_rag() -> None:
    question = _prompt("Question")
    if not question:
        print("  Question is required.")
        return
    top_k_raw = _prompt("top_k", "4")
    api_key = _prompt("x-api-key (optional)", "")
    try:
        top_k = int(top_k_raw)
    except ValueError:
        print("  top_k must be an integer.")
        return
    try:
        payload = post_json(
            f"{DEFAULT_BASE_URL}/rag/query",
            {"question": question, "top_k": top_k},
            api_key=api_key,
        )
        _sep()
        print(f"  Answer:   {payload.get('answer', '')}")
        print(f"  Provider: {payload.get('generation_provider', '')}")
        contexts = payload.get("contexts", [])
        print(f"  Contexts ({len(contexts)}):")
        for i, ctx in enumerate(contexts, 1):
            snippet = ctx[:120]
            suffix = "..." if len(ctx) > 120 else ""
            print(f"    [{i}] {snippet}{suffix}")
        _sep()
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        print(f"  HTTP {error.code}: {body}")
    except urllib.error.URLError as error:
        print(f"  Request failed: {error}")


def run_retrieval_eval(use_grounding_probes: bool = False) -> None:
    path = _prompt("Path to docs directory", ".")
    glob = _prompt("Glob pattern", "**/*.txt")
    top_k = _prompt("top_k", "4")
    min_recall = _prompt("Min keyword recall (0.0-1.0)", "0.5")

    command = [
        project_python(),
        "scripts/eval_retrieval.py",
        "--path",
        path,
        f"--glob={glob}",
        "--top-k",
        top_k,
        "--min-recall",
        min_recall,
    ]

    if use_grounding_probes:
        if not GROUNDING_PROBES.exists():
            print(f"  Grounding probe file not found: {GROUNDING_PROBES}")
            return
        min_grounding = _prompt("Min grounding recall (0.0-1.0)", "0.5")
        command += [
            "--probe-file",
            str(GROUNDING_PROBES),
            "--min-grounding-recall",
            min_grounding,
        ]

    code = run_command(command)
    print(f"\n  Eval script exited with code {code}.")


def _section_rag() -> None:
    while True:
        choice = _section_choice(
            "[2] RAG",
            [
                ("1", "Ingest documents via script"),
                ("2", "Ingest documents via API"),
                ("3", "Query"),
                ("4", "Run retrieval evaluation"),
                ("5", "Run retrieval eval (grounding probes)"),
                ("0", "Back"),
            ],
        )
        if choice == "1":
            ingest_via_script()
        elif choice == "2":
            ingest_via_api()
        elif choice == "3":
            query_rag()
        elif choice == "4":
            run_retrieval_eval(use_grounding_probes=False)
        elif choice == "5":
            run_retrieval_eval(use_grounding_probes=True)
        elif choice == "0":
            break
        else:
            print("  Unknown option.")


# ---------------------------------------------------------------------------
# [3] LEARNING SCRIPTS
# ---------------------------------------------------------------------------

def run_mlp_demo() -> None:
    print("  MLP fundamentals demo (make_moons binary classification)")
    seed = _prompt("Seed", "42")
    epochs = _prompt("Epochs", "300")
    batch_size = _prompt("Batch size", "64")
    lr = _prompt("Learning rate", "0.001")
    command = [
        project_python(),
        "scripts/train_mlp_demo.py",
        "--seed",
        seed,
        "--epochs",
        epochs,
        "--batch-size",
        batch_size,
        "--learning-rate",
        lr,
    ]
    code = run_command(command)
    print(f"\n  MLP demo exited with code {code}.")


def run_transformer_demo() -> None:
    print("  Transformer NLP demo (DistilBERT on IMDB subset)")
    print("  NOTE: downloads ~250 MB of model weights on first run.")
    model_name = _prompt("Model name", "distilbert-base-uncased")
    train_samples = _prompt("Train samples", "2000")
    test_samples = _prompt("Test samples", "500")
    epochs = _prompt("Epochs", "1")
    seed = _prompt("Seed", "42")
    output_dir = _prompt("Output dir", "./checkpoints/transformer_demo")
    command = [
        project_python(),
        "scripts/train_transformer_demo.py",
        "--model-name",
        model_name,
        "--train-samples",
        train_samples,
        "--test-samples",
        test_samples,
        "--epochs",
        epochs,
        "--seed",
        seed,
        "--output-dir",
        output_dir,
    ]
    code = run_command(command)
    print(f"\n  Transformer demo exited with code {code}.")


def _section_learning() -> None:
    while True:
        choice = _section_choice(
            "[3] LEARNING SCRIPTS",
            [
                ("1", "MLP fundamentals demo"),
                ("2", "Transformer NLP demo"),
                ("0", "Back"),
            ],
        )
        if choice == "1":
            run_mlp_demo()
        elif choice == "2":
            run_transformer_demo()
        elif choice == "0":
            break
        else:
            print("  Unknown option.")


# ---------------------------------------------------------------------------
# [4] RELIABILITY
# ---------------------------------------------------------------------------

def run_tests() -> None:
    print("  Running pytest -q ...")
    code = run_command([project_python(), "-m", "pytest", "-q"])
    print(f"\n  pytest exited with code {code}.")


def run_completion_checks() -> None:
    code = run_command([project_python(), "scripts/run_completion_checks.py"])
    print(f"\n  Completion checks exited with code {code}.")


def run_load_test() -> None:
    print("  Load test against /rag/query — API must be running.")
    requests_n = _prompt("Total requests", "60")
    concurrency = _prompt("Concurrency", "10")
    label = _prompt("Run label (optional)", "")
    api_key = _prompt("x-api-key (optional)", "")
    question = _prompt("Test question", "What are the core concepts covered?")

    command = [
        project_python(),
        "scripts/load_test_rate_limit.py",
        "--requests",
        requests_n,
        "--concurrency",
        concurrency,
        "--question",
        question,
    ]
    if label:
        command += ["--label", label]
    if api_key:
        command += ["--api-key", api_key]

    code = run_command(command)
    print(f"\n  Load test exited with code {code}.")


def run_load_test_profile() -> None:
    print("  Staged concurrency load test (concurrency profile).")
    profile = _prompt("Concurrency profile (comma-separated)", "5,10,20")
    requests_n = _prompt("Requests per stage", "30")
    label = _prompt("Run label (optional)", "profile")
    question = _prompt("Test question", "What are the core concepts covered?")

    command = [
        project_python(),
        "scripts/load_test_rate_limit.py",
        "--requests",
        requests_n,
        "--concurrency-profile",
        profile,
        "--question",
        question,
    ]
    if label:
        command += ["--label", label]

    code = run_command(command)
    print(f"\n  Profile load test exited with code {code}.")


def view_load_summary() -> None:
    print("  Load test summary dashboard:")
    code = run_command([project_python(), "scripts/summarize_load_tests.py"])
    print(f"\n  Summarize script exited with code {code}.")


def check_load_thresholds() -> None:
    print("  Checking load thresholds on latest artifact:")
    code = run_command([project_python(), "scripts/check_load_thresholds.py"])
    print(f"\n  Threshold check exited with code {code}.")


def _section_reliability() -> None:
    while True:
        choice = _section_choice(
            "[4] RELIABILITY",
            [
                ("1", "Run test suite (pytest)"),
                ("2", "Run completion checks"),
                ("3", "Run load test (single concurrency)"),
                ("4", "Run load test (staged concurrency profile)"),
                ("5", "View load test summary"),
                ("6", "Check load thresholds"),
                ("0", "Back"),
            ],
        )
        if choice == "1":
            run_tests()
        elif choice == "2":
            run_completion_checks()
        elif choice == "3":
            run_load_test()
        elif choice == "4":
            run_load_test_profile()
        elif choice == "5":
            view_load_summary()
        elif choice == "6":
            check_load_thresholds()
        elif choice == "0":
            break
        else:
            print("  Unknown option.")


# ---------------------------------------------------------------------------
# [5] CONFIGURATION
# ---------------------------------------------------------------------------

_SECRET_KEYS = {"api_key", "openai_api_key"}


def show_settings() -> None:
    env_file = ROOT / ".env"
    _sep()
    print("  Current settings (from .env + defaults):")
    _sep()

    env_values: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env_values[key.strip().lower()] = value.strip()

    defaults = {
        "app_env": "dev",
        "app_host": "127.0.0.1",
        "app_port": "8080",
        "vector_store_dir": "./vector_store",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "default_top_k": "4",
        "api_key": "(empty)",
        "rate_limit_per_minute": "60",
        "rag_llm_provider": "deterministic",
        "rag_llm_model": "llama3.1:8b",
        "ollama_base_url": "http://127.0.0.1:11434",
        "openai_api_key": "(empty)",
        "openai_base_url": "(empty)",
        "request_timeout_seconds": "45",
        "metrics_enabled": "true",
    }

    for key, default in defaults.items():
        raw_value = env_values.get(key, default)
        if key in _SECRET_KEYS and raw_value not in ("(empty)", ""):
            display = "****" + raw_value[-4:] if len(raw_value) > 4 else "****"
        else:
            display = raw_value
        print(f"  {key:<30} {display}")

    _sep()
    if not env_file.exists():
        print(f"  (.env not found at {env_file}; all values are defaults)")
    else:
        print(f"  Source: {env_file}")
    _sep()


def show_metrics() -> None:
    try:
        text = get_text(f"{DEFAULT_BASE_URL}/metrics")
        _sep()
        print("  Prometheus metrics:")
        _sep()
        for line in text.splitlines():
            print(f"  {line}")
        _sep()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            print("  Metrics endpoint returned 404 (metrics may be disabled).")
        else:
            print(f"  HTTP {error.code}")
    except urllib.error.URLError as error:
        print(f"  Request failed (is the API running?): {error}")


def show_provider_health() -> None:
    try:
        payload = get_json(f"{DEFAULT_BASE_URL}/health/provider")
        _sep()
        print("  Provider health:")
        _sep()
        for key, val in payload.items():
            print(f"  {key:<20} {val}")
        _sep()
    except urllib.error.URLError as error:
        print(f"  Request failed (is the API running?): {error}")


def _section_configuration() -> None:
    while True:
        choice = _section_choice(
            "[5] CONFIGURATION",
            [
                ("1", "Show current settings"),
                ("2", "Show metrics (Prometheus)"),
                ("3", "Provider health detail"),
                ("4", "View server log tail"),
                ("0", "Back"),
            ],
        )
        if choice == "1":
            show_settings()
        elif choice == "2":
            show_metrics()
        elif choice == "3":
            show_provider_health()
        elif choice == "4":
            view_server_logs()
        elif choice == "0":
            break
        else:
            print("  Unknown option.")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main() -> None:
    api_process: subprocess.Popen | None = None

    _header("Sword AI Systems — Control Plane")
    print(f"  Project:    {ROOT}")
    print(f"  Python:     {project_python()}")
    print(f"  API target: {DEFAULT_BASE_URL}")

    while True:
        _sep("=")
        print("  MAIN MENU")
        _sep("=")
        print("  1) Server")
        print("  2) RAG")
        print("  3) Learning Scripts")
        print("  4) Reliability")
        print("  5) Configuration")
        print("  0) Exit")
        _sep()
        choice = input("  Choice: ").strip()

        if choice == "1":
            api_process = _section_server(api_process)
        elif choice == "2":
            _section_rag()
        elif choice == "3":
            _section_learning()
        elif choice == "4":
            _section_reliability()
        elif choice == "5":
            _section_configuration()
        elif choice == "0":
            if api_process and api_process.poll() is None:
                if _yn("Stop running API server before exit?"):
                    stop_api(api_process)
            print("  Goodbye.")
            break
        else:
            print("  Unknown option.")


if __name__ == "__main__":
    main()
