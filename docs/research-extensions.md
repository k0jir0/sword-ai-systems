# Research Extensions for Sword

This document translates the project paper into implementable research tracks.

## 1. Retrieval Calibration and Uncertainty

Objective:
- Estimate confidence in retrieved evidence and surface uncertainty in answer responses.

Potential implementation:
- Add distance-based confidence score from ChromaDB retrieval results.
- Include `retrieval_confidence` field in API response schema.
- Define threshold-based refusal behavior when confidence is low.

## 2. Adaptive Chunking

Objective:
- Improve retrieval quality by chunking around semantics rather than fixed windows.

Potential implementation:
- Add sentence/paragraph-aware chunking mode in `scripts/ingest_docs.py`.
- Benchmark fixed-size vs adaptive chunking using `scripts/eval_retrieval.py`.

## 3. Hybrid Retrieval

Objective:
- Combine dense embeddings with lexical matching for better faithfulness.

Potential implementation:
- Integrate a lightweight BM25 retriever alongside dense vectors.
- Merge rankings with reciprocal rank fusion.

## 4. Hallucination Mitigation

Objective:
- Reduce unsupported claims in generated outputs.

Potential implementation:
- Enforce answer citation format and verify citation-context overlap.
- Add refusal templates when context support is insufficient.

## 5. Cost-Aware Provider Routing

Objective:
- Route requests by complexity, latency target, and cost budget.

Potential implementation:
- Add a routing policy layer before `build_llm_client`.
- Classify queries into deterministic, local, or hosted generation tiers.

## 6. Online Feedback Learning

Objective:
- Use user feedback to improve retrieval and answer quality over time.

Potential implementation:
- Store feedback labels (`helpful`, `not_helpful`) with request IDs.
- Re-rank retrieval candidates based on historical utility signals.

## 7. Formal Service Guarantees

Objective:
- Define measurable service-level quality targets beyond uptime.

Potential implementation:
- Track p95 latency, retrieval coverage, and answer refusal rates.
- Add CI gate checks for latency and retrieval regression thresholds.

## Suggested Research Execution Sequence

1. Add retrieval confidence and citation checks.
2. Implement adaptive chunking and benchmark against baseline.
3. Add hybrid retrieval and compare recall@k improvements.
4. Introduce cost-aware provider routing policy.
5. Add feedback loop and monitor quality trends.
