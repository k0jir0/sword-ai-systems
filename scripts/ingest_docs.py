from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from backend.app.rag_pipeline import RAGPipeline

app = typer.Typer(help="Ingest local text-like documents into the Sword vector store.")
console = Console()


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []

    if chunk_size <= 0:
        return [normalized]

    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size.")

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = start + chunk_size
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break
        start = end - chunk_overlap

    return chunks


@app.command()
def run(
    path: str = ".",
    glob: str = "**/*.txt",
    chunk_size: int = 0,
    chunk_overlap: int = 0,
) -> None:
    base_path = Path(path).resolve()
    files = [candidate for candidate in base_path.glob(glob) if candidate.is_file()]

    if not files:
        console.print("No files matched the provided pattern.", style="yellow")
        raise typer.Exit(code=1)

    docs: list[str] = []
    metadatas: list[dict[str, str | int]] = []
    chunk_count_by_file: dict[Path, int] = {}

    for file_path in files:
        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            console.print(f"Skipping non-utf8 file: {file_path}", style="yellow")
            continue

        chunks = chunk_text(raw_content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunk_count_by_file[file_path] = len(chunks)

        for chunk_index, chunk in enumerate(chunks):
            docs.append(chunk)
            metadatas.append(
                {
                    "source_path": str(file_path.relative_to(base_path)),
                    "chunk_index": chunk_index,
                    "chunk_count": len(chunks),
                }
            )

    rag = RAGPipeline()
    indexed = rag.ingest(docs, metadatas=metadatas)
    non_empty_files = sum(1 for count in chunk_count_by_file.values() if count > 0)
    console.print(
        (
            f"Indexed {indexed} chunks from {non_empty_files} files "
            f"(matched files: {len(files)}, chunk_size={chunk_size}, chunk_overlap={chunk_overlap})."
        ),
        style="green",
    )


if __name__ == "__main__":
    app()
