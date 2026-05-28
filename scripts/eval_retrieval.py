from __future__ import annotations

from pathlib import Path

import typer

from backend.app.rag_pipeline import RAGPipeline

app = typer.Typer(help="Run a lightweight retrieval quality check against local text files.")


@app.command()
def run(path: str = ".", glob: str = "**/*.txt", top_k: int = 4) -> None:
    root = Path(path).resolve()
    files = [entry for entry in root.glob(glob) if entry.is_file()]
    docs = [entry.read_text(encoding="utf-8", errors="ignore") for entry in files]

    if not docs:
        raise typer.BadParameter("No documents available for retrieval evaluation.")

    rag = RAGPipeline()
    rag.ingest(docs)

    probes = [
        "What are the core concepts covered?",
        "What production capability is expected?",
    ]

    matched = 0
    for probe in probes:
        result = rag.query(probe, top_k=top_k)
        if result.contexts:
            matched += 1

    recall_at_k = matched / len(probes)
    print(f"retrieval_probe_count={len(probes)}")
    print(f"retrieval_hit_count={matched}")
    print(f"recall_at_{top_k}={recall_at_k:.2f}")


if __name__ == "__main__":
    app()
