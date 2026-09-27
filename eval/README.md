# Evaluation

The harness (`eval/llm_judge.py`) runs every case in `eval/eval_queries.py` through
`CopilotOrchestrator.process` (the same path as `POST /ask`). It then scores the output with
deterministic checks plus an LLM judge (`JUDGE_MODEL_ID`, Claude Sonnet 4.6, temperature 0).
Aggregation and gates are pure functions in `eval/metrics.py` and are unit-tested in
`tests/test_eval.py` without any AWS calls.

**Running the harness is live and billable.** It calls Bedrock for the system under test and
for the judge. See [Cost](#cost) below.

## Dataset

The dataset has 34 labeled cases:
- 18 of the 20 original queries, kept verbatim as `L01`–`L20`.
- 12 cases added in Phase 0 (`N01`–`N14`, without N12).
- 3 Visa cases (`V01`–`V03`).

When Visa replaced Mastercard as the fifth company:
- L11 and L16 (Mastercard summaries) were retired and replaced by V01 and V02.
- N12 (Morgan Stanley, out of corpus) was replaced by V03, keeping the total at 34.
- The original 20 queries are listed in `LEGACY_QUERIES_2026_06`. Their archived results are in
  `eval/results/legacy/`.

| Label | Meaning |
|---|---|
| `expected_route` | Route the router *should* choose, per the taxonomy in the router's system prompt |
| `route_label_status` | `clear` labels are gated. `needs_review` labels (L13, L17, L19, L20) are reported but not gated until a human adjudicates them |
| `expected_behavior` | `answer`, `abstain` (the filings don't contain the answer), or `either` (not scored for abstention) |
| `companies` | Tickers whose filing should supply the retrieved context |
| `reference_answer` / `reference_source` | Ground truth checked against the local PDFs in `../data` (file and page) |
| `forbidden_facts` | Strings that must not appear in the answer, such as Visa's figures in an answer about Mastercard |

**Corpus.** The five companies are JPMorgan Chase, Goldman Sachs, Bank of America,
BlackRock and **Visa**. Visa's FY2025 10-K has EDGAR accession `0001403161-25-000089` and a
fiscal year ending 2025-09-30.

**Mastercard is out of corpus.**
- L03 and L08 are Mastercard abstention cases (`out_of_corpus`, tagged `mastercard`).
- Retrieval will surface Visa chunks for them. Visa's figures are listed as `forbidden_facts`,
  and any leak is reported deterministically under `forbidden_fact_leaks`.

**Source names.** Visa's PDF was first uploaded as `docs/mastercard-10k-fy2025.pdf`.
- `eval/metrics.py` maps that exact legacy name to Visa (`V`) until the S3 rename is complete.
- Any other Mastercard file name maps to `MA`.
- See `docs/runbooks/visa-source-migration.md`.

## Metrics

| Metric | How | Population | Gate |
|---|---|---|---|
| Context relevance | Judge, 1–5; pass ≥ 3 | Gated QA population* | **Enforced ≥ 80%** |
| Faithfulness | Judge, 1–5 vs the retrieved context; pass ≥ 4 | Gated QA population* | **Enforced ≥ 80%** |
| Routing accuracy | Deterministic: predicted vs `expected_route` | Clear labels (all labels also reported) | Report-only, proposed 90% |
| Answer correctness | Judge vs the verified reference, 1–5; pass ≥ 4 | Cases with a reference | Report-only, proposed 80% |
| Abstention appropriateness | Judge detects abstention, compared with `expected_behavior` | `answer` and `abstain` cases | Report-only, proposed 80% |
| Summary grounding | Judge, 1–5, against top-5 chunks the harness retrieves *after* the summary is written; pass ≥ 4 | Cases answered by the summarize path | Report-only, proposed 80% |
| Cross-company contamination | Deterministic: share of retrieved chunks from an expected company's filing | Cases with retrieved context and expected companies | Reported |
| Latency / tokens / cost | From the request trace (`app/observability.py`) | All cases | Reported |

\* **Gated QA population**: `expected_route=qa`, `expected_behavior=answer`, and a clear route
label. This is 19 cases. It is fixed by the labels, so the router can't shrink it.

**Failures are never excluded.** A gated case that is misrouted, returns an error or an empty
answer, or gets a judge error (exception or unparseable output) counts as a **failure**.
Judge errors are also counted separately under `errors.judge_errors`.

**Always visible.** Boundary and out-of-corpus cases appear under
`boundary_and_out_of_corpus` in every results file. Checks for leaked facts from other
companies appear under `forbidden_fact_leaks`.

**Continuity.** `legacy_comparable` recomputes context relevance and faithfulness using the
pre-Phase-0 population rule (legacy queries routed to qa, boundary queries excluded). It is for
comparison only. It is not gated, because that population depends on what the router does.

### Known limitations of the metrics

- n = 19 for the enforced gates, so each case moves the pass rate by about 5.3 points.
- One run of a nondeterministic system. The judge is at temperature 0; the system under test is
  not (Phase 0 does not change inference parameters).
- Summary grounding penalizes true claims that don't appear in the 5 evidence chunks.
- Faithfulness gives full marks to a correct "not found" answer. Abstention and correctness are
  measured separately for that reason.
- Latency is measured in-process. It excludes Lambda initialization, the network hop to the
  Function URL, and response serialization.

## Outputs

- Default output is `eval/results/latest.json` (gitignored). Override it with `EVAL_RESULTS_PATH`.
- Schema version 2. Every run has a unique `run_id`, and the CI test checks that the file came
  from the current run.
- `eval/results/legacy/2026-06-04_pre_phase0_harness.json` is the last result from the old
  harness, archived for reference: context relevance 80% (8/10), faithfulness 80% (8/10), means
  3.8 / 4.6. It is not read by CI.

## Running

```bash
python -m eval.llm_judge
pytest eval/test_llm_judge.py -m llm -v
pytest tests/test_eval.py -v
```

- `python -m eval.llm_judge`: live, billable.
- `pytest eval/test_llm_judge.py -m llm -v`: live, billable. This is what the CI eval gate runs.
- `pytest tests/test_eval.py -v`: offline unit tests for the evaluation logic.

`EVAL_SLEEP_SECONDS` (default 2) sets the pause between cases.

## Cost

**Estimated, not measured.** Assumptions:
- Anthropic list prices: Haiku 4.5 at $1 / $5 per MTok, Sonnet 4.6 at $3 / $15 per MTok.
- About 4–5k tokens of context per QA call and per judge call over retrieved context.

Expected judge calls per run, about 90:
- Up to 3 per QA-path case (context relevance, faithfulness, answer assessment).
- 2 per summarize-path case (grounding, answer assessment).

| Component | Estimate per run |
|---|---|
| Judge (Sonnet 4.6) | ~$0.9–1.3 |
| System under test (Haiku 4.5 router, generation, summarizer; Titan) | ~$0.2–0.3 |
| **Total** | **~$1.1–1.6** |

Bedrock geographic (`us.*`) inference profiles may cost about 10% more; this is unverified. Each
run writes its own token counts and a price-based estimate to `tokens.estimated_cost_usd`. Real
spend comes from AWS billing.
