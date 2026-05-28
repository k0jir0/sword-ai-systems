from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from backend.app.rag_pipeline import RAGPipeline

app = typer.Typer(help="Run a lightweight retrieval quality check against local text files.")
console = Console()


def parse_probes(probe_file: str | None) -> list[tuple[str, list[str]]]:
    if not probe_file:
        return [
            ("What are the core concepts covered?", ["deep learning", "transformer", "rag"]),
            ("What production capability is expected?", ["production", "deploy", "api"]),
            ("How is retrieval evaluated?", ["recall", "retrieval", "context"]),
        ]

    source = Path(probe_file)
    if not source.is_file():
        raise typer.BadParameter(f"Probe file not found: {probe_file}")

    probes: list[tuple[str, list[str]]] = []
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            raise typer.BadParameter(
                "Each probe line must be 'question|keyword1,keyword2'."
            )
        question, raw_keywords = line.split("|", maxsplit=1)
        keywords = [keyword.strip().lower() for keyword in raw_keywords.split(",") if keyword.strip()]
        if not question.strip() or not keywords:
            raise typer.BadParameter("Probe question and keyword list must be non-empty.")
        probes.append((question.strip(), keywords))

    if not probes:
        raise typer.BadParameter("Probe file did not contain any valid probe definitions.")

    return probes


def keyword_hit(contexts: list[str], expected_keywords: list[str]) -> bool:
    flat_context = "\n".join(contexts).lower()
    return any(keyword in flat_context for keyword in expected_keywords)


@app.command()
def run(path: str = ".", glob: str = "**/*.txt", top_k: int = 4, probe_file: str | None = None) -> None:
    root = Path(path).resolve()
    files = [entry for entry in root.glob(glob) if entry.is_file()]
    docs = [entry.read_text(encoding="utf-8", errors="ignore") for entry in files]

    if not docs:
        raise typer.BadParameter("No documents available for retrieval evaluation.")

    rag = RAGPipeline()
    rag.ingest(docs)

    probes = parse_probes(probe_file)

    retrieval_hits = 0
    keyword_hits = 0
    context_total = 0
    misses: list[str] = []

    for question, expected_keywords in probes:
        result = rag.query(question, top_k=top_k)
        context_count = len(result.contexts)
        context_total += context_count

        if context_count > 0:
            retrieval_hits += 1

        if keyword_hit(result.contexts, expected_keywords):
            keyword_hits += 1
        else:
            misses.append(question)

    probe_count = len(probes)
    retrieval_recall_at_k = retrieval_hits / probe_count
    keyword_recall_at_k = keyword_hits / probe_count
    average_contexts = context_total / probe_count

    console.print(f"retrieval_probe_count={probe_count}")
    console.print(f"retrieval_hit_count={retrieval_hits}")
    console.print(f"keyword_hit_count={keyword_hits}")
    console.print(f"retrieval_recall_at_{top_k}={retrieval_recall_at_k:.2f}")
    console.print(f"keyword_recall_at_{top_k}={keyword_recall_at_k:.2f}")
    console.print(f"avg_contexts_returned={average_contexts:.2f}")

    if misses:
        console.print("missed_probes:", style="yellow")
        for missed in misses:
            console.print(f"- {missed}", style="yellow")


if __name__ == "__main__":
    app()
