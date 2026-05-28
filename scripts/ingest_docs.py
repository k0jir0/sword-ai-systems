from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from backend.app.rag_pipeline import RAGPipeline

app = typer.Typer(help="Ingest local text-like documents into the Sword vector store.")
console = Console()


@app.command()
def run(path: str = ".", glob: str = "**/*.txt") -> None:
    base_path = Path(path).resolve()
    files = [candidate for candidate in base_path.glob(glob) if candidate.is_file()]

    if not files:
        console.print("No files matched the provided pattern.", style="yellow")
        raise typer.Exit(code=1)

    docs: list[str] = []
    for file_path in files:
        try:
            docs.append(file_path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            console.print(f"Skipping non-utf8 file: {file_path}", style="yellow")

    rag = RAGPipeline()
    indexed = rag.ingest(docs)
    console.print(f"Indexed {indexed} documents from {len(files)} files.", style="green")


if __name__ == "__main__":
    app()
