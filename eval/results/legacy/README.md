# Legacy evaluation results (not a baseline)

`2026-06-04_pre_phase0_harness.json` was produced by the pre-Phase-0 harness. It is kept for
history only.

- **Not comparable** with current results. It judged only 10 router-selected queries (skipping
  the summarize path and the boundary queries), had no route labels, no reference answers, no
  run ID and no provenance.
- It has no `schema_version` field; current results use schema version 2 and carry a `run_id`,
  `provenance` and `run_validity`.
- CI never reads this directory, and `eval/llm_judge.py` refuses to write results here.
- The Mastercard figures in it came from a file that is actually Visa's 10-K (see
  `docs/runbooks/visa-source-migration.md`).
