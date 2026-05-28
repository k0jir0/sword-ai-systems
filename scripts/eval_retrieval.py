from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from backend.app.rag_pipeline import RAGPipeline

app = typer.Typer(help="Run a lightweight retrieval quality check against local text files.")
console = Console()


def parse_probes(probe_file: str | None) -> list[tuple[str, list[str], list[str]]]:
    if not probe_file:
        return [
            (
                "What are the core concepts covered?",
                ["deep learning", "transformer", "rag"],
                ["neural networks and deep learning fundamentals"],
            ),
            (
                "What production capability is expected?",
                ["production", "deploy", "api"],
                ["API deployment with authentication and rate limiting"],
            ),
            (
                "How is retrieval evaluated?",
                ["recall", "retrieval", "context"],
                ["End-to-end ingestion and retrieval query flow"],
            ),
        ]

    source = Path(probe_file)
    if not source.is_file():
        raise typer.BadParameter(f"Probe file not found: {probe_file}")

    probes: list[tuple[str, list[str], list[str]]] = []
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            raise typer.BadParameter(
                "Each probe line must be 'question|keyword1,keyword2' or 'question|keyword1,keyword2|fragment1,fragment2'."
            )
        parts = line.split("|", maxsplit=2)
        if len(parts) == 2:
            question, raw_keywords = parts
            raw_fragments = ""
        else:
            question, raw_keywords, raw_fragments = parts
        keywords = [keyword.strip().lower() for keyword in raw_keywords.split(",") if keyword.strip()]
        if not question.strip() or not keywords:
            raise typer.BadParameter("Probe question and keyword list must be non-empty.")
        answer_fragments = [fragment.strip().lower() for fragment in raw_fragments.split(",") if fragment.strip()]
        probes.append((question.strip(), keywords, answer_fragments))

    if not probes:
        raise typer.BadParameter("Probe file did not contain any valid probe definitions.")

    return probes


def keyword_hit(contexts: list[str], expected_keywords: list[str]) -> bool:
    flat_context = "\n".join(contexts).lower()
    return any(keyword in flat_context for keyword in expected_keywords)


def grounding_hit(answer: str, expected_fragments: list[str]) -> bool:
    if not expected_fragments:
        return False

    normalized_answer = answer.lower()
    return all(fragment.lower() in normalized_answer for fragment in expected_fragments)


@app.command()
def run(
    path: str = ".",
    glob: str = "**/*.txt",
    top_k: int = 4,
    probe_file: str | None = None,
    min_retrieval_recall: float = 0.0,
    min_keyword_recall: float = 0.0,
    min_grounding_recall: float = 0.0,
) -> None:
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
    grounding_hits = 0
    grounding_probe_count = 0
    context_total = 0
    misses: list[str] = []

    for question, expected_keywords, answer_fragments in probes:
        result = rag.query(question, top_k=top_k)
        context_count = len(result.contexts)
        context_total += context_count

        if context_count > 0:
            retrieval_hits += 1

        if keyword_hit(result.contexts, expected_keywords):
            keyword_hits += 1
        else:
            misses.append(question)

        if answer_fragments:
            grounding_probe_count += 1
            if grounding_hit(result.answer, answer_fragments):
                grounding_hits += 1
            else:
                misses.append(question)

    probe_count = len(probes)
    retrieval_recall_at_k = retrieval_hits / probe_count
    keyword_recall_at_k = keyword_hits / probe_count
    grounding_recall_at_k = grounding_hits / grounding_probe_count if grounding_probe_count else 0.0
    average_contexts = context_total / probe_count

    console.print(f"retrieval_probe_count={probe_count}")
    console.print(f"retrieval_hit_count={retrieval_hits}")
    console.print(f"keyword_hit_count={keyword_hits}")
    console.print(f"retrieval_recall_at_{top_k}={retrieval_recall_at_k:.2f}")
    console.print(f"keyword_recall_at_{top_k}={keyword_recall_at_k:.2f}")
    console.print(f"grounding_probe_count={grounding_probe_count}")
    console.print(f"grounding_hit_count={grounding_hits}")
    console.print(f"grounding_recall_at_{top_k}={grounding_recall_at_k:.2f}")
    console.print(f"avg_contexts_returned={average_contexts:.2f}")

    if misses:
        console.print("missed_probes:", style="yellow")
        for missed in misses:
            console.print(f"- {missed}", style="yellow")

    if retrieval_recall_at_k < min_retrieval_recall:
        console.print(
            (
                f"retrieval recall gate failed: {retrieval_recall_at_k:.2f} "
                f"< required {min_retrieval_recall:.2f}"
            ),
            style="red",
        )
        raise typer.Exit(code=1)

    if keyword_recall_at_k < min_keyword_recall:
        console.print(
            (
                f"keyword recall gate failed: {keyword_recall_at_k:.2f} "
                f"< required {min_keyword_recall:.2f}"
            ),
            style="red",
        )
        raise typer.Exit(code=1)

    if min_grounding_recall > 0.0 and grounding_probe_count == 0:
        console.print(
            "grounding recall gate failed: no labeled answer fragments were provided",
            style="red",
        )
        raise typer.Exit(code=1)

    if grounding_recall_at_k < min_grounding_recall:
        console.print(
            (
                f"grounding recall gate failed: {grounding_recall_at_k:.2f} "
                f"< required {min_grounding_recall:.2f}"
            ),
            style="red",
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
