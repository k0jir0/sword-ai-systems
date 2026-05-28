from __future__ import annotations

from pathlib import Path

from scripts.eval_retrieval import grounding_hit, parse_probes


def test_parse_probes_supports_labeled_grounding_fragments(tmp_path: Path) -> None:
    probe_file = tmp_path / "grounding_probes.txt"
    probe_file.write_text(
        "What are the core concepts covered?|deep learning,transformer,rag|Neural networks,Transformer-based NLP workflows\n",
        encoding="utf-8",
    )

    probes = parse_probes(str(probe_file))
    assert probes == [
        (
            "What are the core concepts covered?",
            ["deep learning", "transformer", "rag"],
            ["neural networks", "transformer-based nlp workflows"],
        )
    ]


def test_grounding_hit_requires_all_labeled_fragments() -> None:
    assert grounding_hit(
        "Question: What are the core concepts covered?\nNeural networks and deep learning fundamentals. Transformer-based NLP workflows.",
        ["Neural networks", "Transformer-based NLP workflows"],
    )
    assert not grounding_hit(
        "Question: What are the core concepts covered?\nNeural networks and deep learning fundamentals.",
        ["Neural networks", "Transformer-based NLP workflows"],
    )