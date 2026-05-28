# Release Checklist

Use this checklist before tagging a Sword release.

## 1. Functional Validation

- [ ] API starts successfully with documented command.
- [ ] `GET /health` returns status `ok`.
- [ ] `GET /health/provider` returns expected provider status.
- [ ] `POST /rag/ingest` and `POST /rag/query` succeed on fixture corpus.

## 2. Quality Gates

- [ ] `pytest -q` passes locally.
- [ ] Retrieval baseline gate passes locally:
  - `python scripts/eval_retrieval.py --path data/fixtures --glob "core_expectations.txt" --probe-file data/fixtures/retrieval_probes.txt --top-k 2 --min-retrieval-recall 1.0 --min-keyword-recall 1.0`
- [ ] Unified completion checks pass:
   - `python scripts/run_completion_checks.py`
- [ ] GitHub Actions workflow is green on latest main commit.

## 3. Documentation Validation

- [ ] README commands match repository structure.
- [ ] Architecture docs updated for any component changes.
- [ ] Completion report updated with latest evidence links.

## 4. Operational Readiness

- [ ] `.env.example` reflects all required settings.
- [ ] Auth and rate-limit behavior validated.
- [ ] Metrics endpoint returns expected counters.

## 5. Versioning and Tagging Guidance

Recommended version pattern: semantic versioning (`MAJOR.MINOR.PATCH`).

- Increase PATCH for fixes and documentation improvements.
- Increase MINOR for backward-compatible feature additions.
- Increase MAJOR for breaking API/contract changes.

Tagging sequence:

1. Ensure all checklist sections are complete.
2. Create release commit if needed.
3. Tag release:
   - `git tag vX.Y.Z`
   - `git push origin vX.Y.Z`
4. Attach release notes summarizing:
   - feature changes
   - testing evidence
   - migration notes (if any)
