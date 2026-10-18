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
- `eval/metrics.py` maps that exact legacy name to Visa (`V`). The metadata was migrated on
  2026-09-28, but warm Lambda containers may still return the old path. Remove the mapping
  after the Lambda refresh and the deletion of the old object.
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

## Tracked retrieval-quality issues (report-only)

Two issues seen in the 2026-09-28 production smoke tests are tracked. Neither is gated, and
retrieval ranking, prompts and generation are deliberately unchanged in Phase 0.

1. **Boilerplate ranked above the evidence.**
   - What happened: for "JPMorgan Chase FY2025 total net revenue", the top-ranked chunk
     (score 0.756) was forward-looking-statements boilerplate. The revenue table containing
     `182,447` ranked 3rd. The answer was still correct.
   - How it's tracked: `results[].evidence` records the rank of the first retrieved chunk that
     comes from the expected company **and** contains every evidence marker. Markers are listed
     per case in `eval_queries.py` and were checked against the indexed text.
   - Summary fields: `retrieval_quality_tracking.evidence_rank` reports the found rate, mean
     reciprocal rank, cases where the evidence was retrieved but not ranked first, and cases
     where it wasn't retrieved at all.
2. **Page number generated by the model.**
   - What happened: the same answer cited "page 50". Chunk metadata contains no page numbers,
     so this can't be verified against citations. The evidence is on PDF pages 46 and 49; the
     printed 10-K page numbering differs.
   - How it's tracked: `results[].page_references` lists page references in each answer, and
     `retrieval_quality_tracking.unverified_page_references` collects them.

## Outputs

- Default output is `eval/results/latest.json` (gitignored). Override it with `EVAL_RESULTS_PATH`.
- Schema version 2. Every run has a unique `run_id`, and the CI test checks that the file came
  from the current run.
- `eval/results/legacy/2026-06-04_pre_phase0_harness.json` is the last result from the old
  harness, archived for reference: context relevance 80% (8/10), faithfulness 80% (8/10), means
  3.8 / 4.6. It is not read by CI.

## Running

**Before any paid run**, run the offline preflight. It makes no AWS or model calls: a network
guard turns any attempt into a blocker.

```bash
python -m eval.preflight --results-path eval/results/baselines/2026-09-phase0-baseline.json
```

The preflight checks:
- **Dataset:** 34 cases, 19 gated. Labels, references, evidence markers and the Mastercard/Visa
  rules are all valid.
- **Contamination mapping and gates:** source-to-company mapping is correct, and the enforced
  thresholds are unchanged.
- **Results path:** not the legacy directory, and no silent overwrite.
- **Code:** the code under test is the local package and is committed.
- **Configuration:** model IDs are as expected and AWS credentials are present (values never
  shown).
- **Cost ceiling:** above the high estimate.

It exits 1 if anything blocks.

Then:

```bash
python -m eval.llm_judge --live
pytest eval/test_llm_judge.py -m llm --run-live-eval -v
pytest tests/test_eval.py tests/test_preflight.py -v
```

- `python -m eval.llm_judge --live`: live, billable. Without `--live` it refuses to start
  (exit 2). Exit 1 means the run stopped early (cost ceiling or harness failure).
- `pytest eval/test_llm_judge.py -m llm --run-live-eval -v`: live, billable. This is what the CI
  eval gate runs. It checks `run_validity` first, then the enforced gates.
- `pytest tests/test_eval.py tests/test_preflight.py -v`: offline unit tests.

**Live execution is opt-in at three levels** (see
`docs/incidents/2026-09-28-unguarded-live-eval-test-run.md`):
- **pytest:** a repository-root `conftest.py` keeps every pytest run offline. It forces fake
  credentials, disables `.env` and blocks botocore. `llm` tests are skipped unless
  `--run-live-eval` is given, and selecting only them without it is a usage error (exit 4).
  With the option, only `llm` tests may be selected.
- **Fixture:** the eval gate's fixture re-checks the opt-in and refuses to start while the guard
  is installed.
- **Harness:** `run_evaluation()` refuses to build real clients unless called with `live=True`.

**Environment variables**

| Variable | Default | Effect |
|---|---|---|
| `EVAL_RESULTS_PATH` | `eval/results/latest.json` | Where results are written. Writes into `eval/results/legacy/` are refused |
| `EVAL_MAX_COST_USD` | 5.0 | Cost ceiling. If the estimated spend exceeds it, the run stops and is marked incomplete and invalid |
| `EVAL_SLEEP_SECONDS` | 2 | Pause between cases |

**The run always uses the local code.** The harness imports `CopilotOrchestrator` in-process and
never calls the deployed Lambda, which still runs the June 2026 build.

## Run validity and provenance

**Validity.** `summary.run_validity.valid_for_baseline` is false if any of these happened:
- no case was evaluated, or no case produced a usable result (every case failed with a system
  error);
- an offline network guard blocked any system or judge call (`network_blocked`: the run never
  reached AWS);
- the system under test hit an infrastructure failure;
- a router fell back because of one;
- a judge call failed to invoke;
- the harness's evidence retrieval failed;
- unexpected application errors hit more than 20% of cases (systemic breakage);
- the harness raised an unexpected exception (the rows already evaluated are kept and written);
- the run stopped early.

"Infrastructure" means access denied, throttling, unavailable, timeout or misconfiguration.

Failures that are findings about the system, not the environment, count against the metrics and
do **not** invalidate the run:
- model-output failures: unusable output or model errors;
- sporadic application errors (at most 20% of cases).

An invalid run is not a quality verdict. Each verdict records `rules_version` (currently 2).
Archived results keep the verdict recorded when they ran.

### The 20% application-error threshold (rules version 2)

Unexpected application errors are failures classified as kind `internal`: an exception the app
did not classify as infrastructure or model output.

**Why a threshold at all.** The old rules counted every such error as a quality finding. A run
where nothing worked could therefore pass the validity gate (run `c7aba364`: 34/34 cases
errored, zero model calls, marked valid). The threshold separates two situations:
- **Sporadic defect:** a real finding. It counts against the metrics.
- **Systemic breakage:** the run did not measure quality. It is invalid.

**Why 20%.** It mirrors the tolerance of the enforced gates, which require at least 80%. Once
more than a fifth of cases fail with unexpected errors, the gate outcome can be decided by the
breakage rather than by retrieval quality. The value was set before any run was judged by it.
Existing data sit far from it: the baseline had 0% application errors and the incident run
100%.

**Limitations:**
- **Not empirically calibrated.** Only one valid run exists. Treat 20% as provisional.
- **Coarse steps.** With 34 cases, 6 errors (17.6%) leave the run valid and 7 (20.6%) make it
  invalid. With very small custom sets, a single error can cross it. A run where every case
  errors is invalid regardless, through "no usable results".
- **Counts cases, not causes.** One bug that breaks a whole path makes the run invalid instead
  of scoring it as a quality regression. For example, all 11 summarize-routed cases is 32%.
  CI still fails (the validity test runs first), but that run's metric numbers must not be
  compared with valid runs.
- **A contained bug stays a finding.** A real bug affecting 20% of cases or fewer is a finding.
  If it spares the 19 gated cases, the enforced gates can still pass. It stays visible under
  `run_validity.application_errors`.
- **`internal` mixes causes.** It covers application bugs and environmental exceptions the app
  does not classify. Examples are a non-botocore network error or a local file problem. Only the
  offline guard's `NetworkBlockedError` is recognized as environmental, by its code.
- **Fatal errors only.** Only the error that ended a case is counted. Non-fatal `internal`
  errors in traces are not.

**Alternatives considered:**
- a per-route share;
- clustering by error code (the same code in 3 or more cases means systemic);
- zero tolerance (any `internal` error invalidates the run).

Revisit the threshold once there are at least 3 valid runs.

### Measurement definition history

Recorded results are never rewritten. A definition change applies to new runs. Where it
matters, the archived baseline is re-scored in a separate, read-only view. The enforced gates
(metrics, thresholds and the 19-case population) have not changed since Phase 0.

| Commit | Definition | Change | Archived baseline `6a13ffb1`: recorded → re-scored |
|---|---|---|---|
| `26511e1` | Summary grounding | A refusal can no longer pass (`refusal: true`, score 0); substantive rate reported | 2/11 → 0/11 (3 refusals; 0/8 substantive) |
| `da0c3d3` | Evidence markers | Alternative phrasings for L06 and N06 (dataset SHA-256 `f1d0da26…` → `734f6e1c…`; labels unchanged) | Evidence found 13/19 → 15/19 |
| `0ee6b19` | Retrieval reporting | Report-only `answer_evidence` and context-relevance score distribution; judge tokens by kind | New fields only |
| `a9f105c` | Run validity, rules version 2 | See above | Valid → still valid (34/34 usable) |
| `9d6f98e` | Routing labels, routing benchmark only | `eval/routing_datasets.py` v2: L13 → clear `qa`; L19 scored by the experimental "unclear → qa" policy. The harness keeps v1 labels | Routing 30/30 (v1) → 30/31 under v2 (L13 routed `summarize`); L19 policy compliance 0/1 |

**Provenance.** `summary.provenance` records:
- the git SHA, and whether tracked files had uncommitted changes;
- the dataset SHA-256;
- the corpus actually loaded: vector count, metadata rows and metadata SHA-256. The expected
  metadata SHA-256 is `f771ba6c…`, the post-migration S3 object.

Every result row carries the case's `trace_id`.

## Cost

**Measured (Phase 0 baseline, run `6a13ffb1`):**
- 193 paid requests: 68 Haiku, 34 Titan, 91 Sonnet judge. There were 3 fewer judge calls than
  the label-based count because 3 questions were routed to the summarizer.
- Estimated **$1.11** at list prices: $0.16 for the system under test and $0.95 for the judge.
- Real spend comes from AWS billing.

**Estimate for the next run** (`python -m eval.preflight`): **~$1.17**, range ~$0.87–$1.92. The
range includes a possible, unverified 10% premium for `us.*` profiles.

The per-call token counts in `TOKEN_ASSUMPTIONS` (`eval/preflight.py`) are calibrated from the
baseline:
- **Measured:** router, embedding, QA generation and summarizer averages.
- **Derived:** the per-judge-kind split. The baseline recorded judge totals only. The split
  reproduces them within 1% under the observed routing (a regression test enforces this).

Runs from Phase 0.5 onward record judge tokens by kind (`tokens.judge.by_kind`); re-calibrate
from those.

| Paid requests per run (label-based) | Count |
|---|---|
| Haiku 4.5: router, QA generation, summarizer | 68 |
| Titan V2 embeddings (QA retrieval plus harness evidence for summaries) | 34 |
| Sonnet 4.6 judge (3 per QA case, 2 per summary) | 94 |
| **Total** | **196** |
