# Router benchmark: Haiku 4.5 vs deterministic rules vs TypeSafe Jev

**Status:** design version 2 (2026-09-28).

**Approved:**
- L13 relabelled as clear `qa` in a new routing dataset version.
- "Unclear query → `qa`" adopted as an experimental policy for L19.

**In place (offline only):**
- Routing dataset v2 (`eval/routing_datasets.py`).
- An offline network guard that blocks TypeSafe and every other non-loopback host in all pytest
  runs.
- **The benchmark, implemented offline** in `experiments/router_bench/` (approved 2026-09-28;
  commits `95a01f0` and `e6f52a5`). The dry run is verified; see §13.

**Not yet approved or done:**
- Sending any text to TypeSafe.
- The Jev verification calls.
- Any paid call or benchmark run.

§12 lists the decisions still needed. Version 1 of this design (commit `264ee6b`) used the
30-case v1 labels.

## 1. Question and scope

Can routing be made cheaper and faster without making routing decisions worse?

- **Routing only.** The benchmark measures the routing decision, not answer quality
  downstream.
- **Why it is worth measuring.** In the Phase 0 baseline (run `6a13ffb1`), routing takes
  **0.87 s p50 / 1.17 s p95**. That is about **34% of QA-path latency at p50**, measured
  in-process.
- **Out of scope:**
  - changing downstream QA or summarization;
  - changing the production router or its fallback rule;
  - deploying anything.

## 2. Candidates

Every candidate implements `route(query) -> RouteRecord`, with the same taxonomy (`qa` |
`summarize`) and the same final-decision rule (§4). `RouteRecord` holds:
- the raw prediction and raw score;
- the final decision and outcome;
- any error class;
- latency.

| Router | Implementation | Deterministic? |
|---|---|---|
| **Haiku 4.5 (control)** | The existing `app.agents.router.RouterAgent`, imported and called unchanged: same prompt, model ID and default inference parameters | No (default temperature) |
| **Rules** | A new experiment-only module. Keyword and phrase rules written **only from the router's taxonomy text**, then frozen and hashed before any run | Yes |
| **Jev** | A new experiment-only HTTP client for TypeSafe `jev-1.13.0`: one Choice question with the router's taxonomy as criteria (§6) | Unknown (to be measured) |

**Isolation:**
- The code lives in `experiments/router_bench/`, not in `app/`.
- It imports `RouterAgent` only. A unit test makes `CopilotOrchestrator`, `QAAgent`,
  `SummarizerAgent`, the retriever and generation raise if they are touched.
- No application file changes.

## 3. Dataset: routing labels v2

- **Source:** `eval/routing_datasets.py`, version **v2**, SHA-256 `9d4f2da1…` (pinned). Any edit
  raises `DatasetDriftError`; changes need a new version.
- **Historical labels:** v1 (`f9011fd9…`) reproduces the baseline's labels exactly, which a test
  checks against the archived results. The eval harness keeps v1 labels, so its enforced-gate
  population is still 19. L13 is **not** gated.

| Set | Cases | Use |
|---|---|---|
| **Strict** | **31 clear: 24 `qa`, 7 `summarize`** (v1's 30 plus L13 as `qa`) | Headline accuracy and recall |
| **Policy** | L19 "Goldman Sachs 2025", policy `unclear_defaults_to_qa` (required final decision: `qa`) | Policy compliance, reported separately. Never in accuracy |
| **Excluded** | L17 (a general definition), L20 (two intents) | Raw predictions and agreement between routers only |

**Denominators:**
- **Per repetition:** strict 31, `qa` 24, `summarize` 7, policy 1.
- **Across R repetitions:** repeated calls on the same 31 queries are not independent samples,
  so there are three views and none uses 31·R as the n for a Wilson interval:
  - **Majority view (primary).** Each case's modal final decision over R repetitions, with a tie
    counted as wrong. n = 31, with a 95% Wilson interval.
  - **Pooled view.** All 31·R final decisions, with a 95% case-cluster bootstrap interval:
    resample the 31 cases, 10,000 draws, fixed seed.
  - **Per-repetition view.** Minimum, median and maximum accuracy over the R repetitions.

**95% Wilson reference points** (from `wilson_interval` in `eval/routing_datasets.py`):

| Result | Interval |
|---|---|
| 31/31 | [89.0%, 100%] |
| 30/31 | [83.8%, 99.4%] |
| 29/31 | [79.3%, 98.2%] |
| 28/31 | [75.1%, 96.7%] |
| `qa` 24/24 | [86.2%, 100%] |
| `qa` 22/24 | [74.2%, 97.7%] |
| `summarize` 7/7 | [64.6%, 100%] |
| `summarize` 6/7 | [48.7%, 97.4%] |

**Statistical limit.**
- Routers less than about 10–15 points apart can't be told apart on 31 cases.
- `summarize` recall rests on 7 cases.
- Accuracy here is a sanity check, not grounds for a production decision. A held-out set of at
  least 150 human-reviewed queries is needed before any integration decision, and building it
  needs its own approval.

**Reference point.** The baseline Haiku routes, re-scored read-only against v2:
- **30/31**: the single error is L13, routed `summarize`;
- `summarize` recall **7/7**;
- L19 policy compliance **0/1**: routed `summarize`, and the summarizer then refused.

All 34 baseline decisions were direct model decisions; there were no fallbacks. The baseline did
**not** record router confidence.

## 4. Raw predictions vs final decisions

**Definitions (recorded for every call):**
- **Raw prediction:** the router's own label before any threshold or fallback.
  - It is null when there is none: an invocation error, a parse error, or a response that fails
    schema validation. The reason is recorded.
- **Raw score:** what each router reports about its prediction.

  | Router | Raw score | What it is |
  |---|---|---|
  | Haiku | `confidence` from its JSON output | A number the model writes as text. It is not a probability; its distribution and calibration are unknown |
  | Jev | `probabilities[choice]` | A model-output probability. Calibration is not documented. With 2 options it is always ≥ 0.5 |
  | Rules | none | A deterministic label |

- **Final decision:** the production-equivalent rule from `RouterAgent`:
  - no raw prediction → `qa`;
  - raw score < **0.6** → `qa`;
  - otherwise the raw prediction.

  The rules router never falls back.

**Capturing Haiku's raw prediction without changing the app.** `RouterAgent.route()` returns
only the final decision. The benchmark therefore wraps each call in `app.observability.
request_trace` and reads the trace's route fields:

| Outcome | Raw prediction |
|---|---|
| `model` | The returned `task_type` and `confidence` |
| `fallback_low_confidence` | `model_task_type` and `model_confidence` |
| `fallback_parse_error` / `fallback_invoke_error` | Null |

This matches `app/agents/router.py` at `a990609`.

**No assumed equivalence.** Applying 0.6 to both Haiku and Jev is **nominal parity** (the same
production rule). It is not calibrated equivalence, because the two scores mean different
things. Pre-registered handling:
1. **Primary: final decisions.** This is what production would do. The follow-up criteria (§10)
   use it.
2. **Raw-label accuracy, threshold-free, for every router.** This is the fairest
   classifier-to-classifier comparison. A gap between raw and final accuracy is attributed to
   the threshold, not the classifier.
3. **Fallbacks broken down by raw label.** A fallback to `qa` on a `qa` case looks correct, so
   it is reported separately as "correct by fallback".
4. **Score diagnostics, report-only:**
   - the score distribution;
   - score against correctness;
   - Brier score on the raw prediction;
   - a 3-bin reliability table.

   With 31 cases and few errors these are underpowered, so **no calibration claim** will be
   made.
5. **Threshold sweep** (0.5–0.95), computed offline from the recorded scores. It is
   **exploratory only**. It is never used to pick a winner or to tune a threshold before a
   held-out evaluation.
6. **Jev details:**
   - With 2 options, a threshold of 0.6 means a probability margin of at least 0.2.
   - Jev's own `confidence` field is recorded but not used. For 2 options it is presumably
     `2p − 1`, which is unverified (§7).

**Policy compliance (L19)** is reported per repetition as x/R on the final decision, split into:
- the raw label was `qa`;
- the raw label was `summarize`, but it fell back to `qa`;
- non-compliant.

It is experimental and report-only.

## 5. Measurements

| Measurement | Definition |
|---|---|
| Strict accuracy | Final decision and raw label vs v2 clear labels, in the three views of §3. Per-class recall and the confusion matrix |
| Policy compliance | §4, L19 only |
| Label stability | Per query, the share of repetitions that disagree with that router's majority raw label |
| Fallback rate | Share of calls that fell back, by reason (invoke error, parse error, schema error, low score, timeout) |
| Infrastructure error rate | 401/403/422/429/5xx/529 and timeouts. **Above 1% of calls → that router's run is invalid** |
| Latency | Client-side wall clock (`time.perf_counter`) around `route()`, including the network. p50/p95/p99 per router, with bootstrap 95% CIs for each and for the difference vs Haiku. Warm-up calls excluded. Haiku's server-side `metrics.latencyMs` recorded too |
| Cost | Recorded tokens × list price per call, and cost per 1,000 routing decisions |
| Agreement | Cohen's κ between each pair of routers: on the 31 strict cases, and on all 34 |
| Projected end-to-end effect | Router p50/p95 savings applied to the baseline QA-path latency, labelled as a projection |

**Repetitions, ordering and warm-up:**
- **Minimum 6, recommended 10** per router over all 34 queries.
- Within each repetition, routers are called round-robin per query in a seeded random order.
- 3 warm-up calls per router are discarded.
- The rules router needs one run.
- **Topology:**
  - **Phase A** runs locally. That biases absolute latency, because TypeSafe's serving region is
    not documented.
  - **Phase B** runs from AWS us-east-1 and needs separate approval.

## 6. Jev request and data sent

- **Endpoint:** `POST https://api.typesafe.ai/v1/systemone`. Only the official domain. Look-alike
  domains exist (jevapi.org, jev-ai.pro, tokenra.io).
- **Model:** `jev-1.13.0`, **pinned**. `jev-latest` and `jev-preview` are aliases that can move.
- **Client:** `httpx` (already pinned). Connect timeout 2 s, read timeout 5 s, **no retries**.
- **Request.** Its only variable is the question text:
  ```json
  {"state": "<approved question text>", "model": "jev-1.13.0",
   "questions": {"route": {"type": "choice",
     "instructions": "Classify this financial research query into exactly one category.",
     "criteria": {"qa": "<RouterAgent 'qa' definition and examples, verbatim>",
                  "summarize": "<RouterAgent 'summarize' definition and examples, verbatim>"}}}}
  ```
- **Data that leaves AWS** (needs your approval, §12):
  - the question text of the approved cases only;
  - the fixed instruction and criteria text. This is our taxonomy wording, containing no user
    data.

  Nothing else is sent: no trace IDs, no metadata, no other fields.
- **Retention.** TypeSafe documents zero data retention only for enterprise customers.
- **Parsing:**
  - `answers.route.choice`, `.probabilities` and `.confidence`;
  - the top-level `model`;
  - `usage.input_tokens` and `usage.output_tokens`.

  All of these are validated as in §7.

## 7. Jev API verification plan (1–3 calls, not executed)

**Purpose:** confirm the documented contract before building on it.

**Calls:**

| # | Case | Question | Checks |
|---|---|---|---|
| 1 | L01 (clear `qa`) | "What was JPMorgan Chase's total net revenue for fiscal year 2025?" | Schema, probabilities, tokens, latency |
| 2 | L12 (clear `summarize`) | "Summarize the key risks in Goldman Sachs 2025 annual report." | The other class |
| 3 (optional) | L01 again | Same request as call 1 | Determinism (identical probabilities?) and latency spread |

**Response-schema validation.** Any failure stops the plan and is recorded; nothing is retried.
- HTTP 200 and `Content-Type: application/json`.
- The top-level `model` equals `jev-1.13.0` exactly. A different string means the pin was not
  honored.
- `answers.route.choice` ∈ {`qa`, `summarize`}.
- `answers.route.probabilities`:
  - its keys are exactly {`qa`, `summarize`};
  - every value is a number in [0, 1];
  - the values sum to 1 ± 0.001;
  - `choice` is the argmax.
- `answers.route.confidence` is a number in [0, 1].
- `usage.input_tokens` is an integer > 0, and `usage.output_tokens` an integer ≥ 0.
- Unknown extra fields are recorded by name only.

**Probability interpretation (recorded, not assumed):**
- **2-option confidence formula.** Check whether `confidence ≈ 2·p(choice) − 1` (to within
  0.001). Record "confirmed" or the observed relation. It affects only documentation, because
  the decision rule uses `p(choice)`.
- **Margin.** Record `p(choice)`, and whether 0.6 would trigger a fallback for these clear
  queries.
- **Calibration.** No calibration conclusion is drawn from 1–3 calls.

**Token and cost accounting:**
- **Per call:** record `usage.input_tokens` and `usage.output_tokens`, alongside a local
  estimate (UTF-8 bytes ÷ 4) of the request, to validate the §9 assumption of 150–250 tokens.
- **Cost:** `input_tokens × $0.042 / 1M`. Output is free per the docs, but its token count is
  still recorded.
- **If `usage` is missing:** that is a schema failure. The call is costed at the documented
  maximum of 64k tokens per request, which is $0.0027.
- **Worst case for 3 calls: $0.008.**

**Headers:**
- Record `x-request-id` (or equivalent), `date` and `x-ratelimit-*` by allowlist.
- Never record `Authorization`, `set-cookie` or any request header.

**Stop conditions:**
- 401/403: stop, and check the key without printing it.
- 422: stop; the request contract differs from the docs.
- 429/529: stop; no retries.
- Timeout: stop.
- Schema failure: stop.

**Output:** `eval/results/experiments/jev-verification-<date>.json`. It holds:
- for each call: the case ID, the payload-template SHA-256, the validated response body, the
  allowlisted headers, the latency and the check results;
- the pinned model and the dataset fingerprint.

**Limits** (enforced independently, §8):
- at most 3 requests;
- at most $0.01;
- only case IDs L01 and L12.

## 8. Live-call safety (lessons from the 2026-09-28 incident)

See `docs/incidents/2026-09-28-unguarded-live-eval-test-run.md`.

1. **Offline by default.**
   - The benchmark and verification CLIs default to a **dry run**. They build the full call
     schedule against fake clients, then print the case IDs to be sent, the planned request
     counts per provider and the worst-case cost, and exit 0 without any network.
2. **Explicit live opt-in, per provider.**
   - Real clients are built only with `--live bedrock`, `--live typesafe` or both. The CLI turns
     these flags into a `LiveAuthorization` object.
   - The Jev and Bedrock client constructors refuse to build without one. No test and no default
     code path creates one.
   - The existing `--live` / `--run-live-eval` opt-ins for the eval harness are unchanged.
3. **Independent request-count and cost limits.** Two separate budgets per provider are checked
   **before** every call. Either one tripping stops the run, marks it invalid and writes partial
   results.
   - **Request caps:** the exact scheduled count. Verification: Jev 3. Phase A: Haiku 343, Jev
     343.
   - **Estimated-cost caps:**
     - Before each call, its worst-case cost is added: Jev at the 64k-token maximum, Haiku at
       2,000 input + 400 output tokens.
     - After the call, that is replaced by the recorded usage.
     - Caps: Bedrock $0.50, TypeSafe $0.05, $1.00 total.
   - **Also:** stop a router after 3 consecutive infrastructure errors, and pace Jev at no more
     than 60 requests per minute.
4. **Ordinary tests never contact TypeSafe:**
   - The offline guard now blocks httpx (sync and async), DNS and socket connects to any
     non-loopback host, and removes `TYPESAFE_API_KEY` (commit `f0f84c3`).
   - Unit tests for the Jev client use `httpx.MockTransport` only.
   - The client requires `LiveAuthorization`.
5. **API keys and authentication headers are never exposed:**
   - `TYPESAFE_API_KEY` is read only when a live Jev client is built. It is held in a wrapper
     whose `repr` is `[REDACTED]`, and placed only in the `Authorization` header.
   - The `httpx` and `httpcore` loggers are set to WARNING, and no request or response hooks log
     headers.
   - Errors are re-raised with the status code and error class only.
   - Before any results file is written, the serialized content is scanned for the key. The
     write is refused if the key is found, and a unit test checks this with a canary key.
   - The preflight reports only whether the key is present.
   - The key is local `.env` only: never committed, logged, or added to CI.
6. **Only approved question text is sent to TypeSafe:**
   - Requests are built from a case ID. The ID is looked up in the pinned v2 dataset (its
     fingerprint is checked at start) and must be in the approved-ID allowlist for that run.
   - Free text is rejected, and so is any ID outside the allowlist.
   - The payload template (instruction and criteria) is frozen and hashed.
   - The dry run prints the exact IDs, for approval.

## 9. Cost

| Item | Calls | Estimated cost |
|---|---|---|
| Jev verification (§7) | ≤ 3 | ≈ $0.00003 (cap $0.01) |
| Haiku router, Phase A (measured 214 in / 52 out per call) | 34 × 10 + 3 = 343 | ≈ **$0.16** (≈ $0.18 with a possible 10% `us.*` premium) |
| Jev, Phase A (150–250 input tokens per call assumed; checked by the verification) | 343 | ≈ **$0.003** (unverified pricing) |
| Rules | 34 | $0 |
| **Total, Phase A** | | **≈ $0.17–0.20** (caps: $1 total) |
| Optional: 150-query held-out set × 5 repetitions | 750 Haiku + 750 Jev | ≈ $0.36 + $0.01 |

## 10. Pre-registered reading of results

A candidate is **worth a follow-up** (a held-out set, then an end-to-end evaluation) only if
**all** of these hold. They are fixed now, before any Jev data exists. They were set after seeing
the baseline Haiku routes (30/31 under v2), and apply to every router, including the control.

| Criterion | Threshold | Basis |
|---|---|---|
| Strict accuracy, final decision, majority view | ≥ **29/31** (at most 2 errors) | Same tolerance as v1's ≥ 28/30 |
| Strict accuracy, final decision, pooled view | ≥ 93.5% (= 29/31) | Guards against a majority view that hides unstable cases |
| `summarize` recall, final decision, majority view | ≥ **6/7** | Unchanged |
| Infrastructure error rate | ≤ 1% of calls | Unchanged |
| Fallback rate | ≤ 5% of calls | Unchanged |
| p95 routing latency | ≥ 300 ms lower than Haiku, with the bootstrap CI of the difference excluding 0 | Unchanged |

**Report-only, never criteria:**
- raw-label accuracy;
- label stability;
- L19 policy compliance;
- score diagnostics;
- the threshold sweep;
- predictions on L17 and L20.

Neither result, positive or negative, is a production decision on its own. A decision also needs
the held-out set, an end-to-end evaluation through the unchanged downstream path (paid, and
approved separately), and a privacy decision about TypeSafe.

## 11. What is documented vs verified

| Item | Source | Status |
|---|---|---|
| Endpoint, auth header, request/response field names, Choice schema (≤ 255 options) | docs.typesafe.ai `/api`, `/primitives/choice` (checked 2026-09-28) | Documented; **not verified** (§7) |
| Pricing: $0.042 per 1M input tokens; output free | `/models` | Documented; not verified against a bill |
| Rate limits: 250k tokens/s, 1,200 requests/min, 64k tokens per request | `/models` | Documented; may change |
| Errors 401/422/429/529 | `/api` | Documented |
| `confidence` formula for 2 options | `/confidence` (3-option example only) | **Inferred**; checked in §7 |
| Calibration of probabilities; Haiku's verbalized confidence | not stated | **Unknown**; not assumed (§4) |
| Latency, determinism, serving region, default retention | not stated | **Unknown**; the benchmark measures the first two |
| Availability on Amazon Bedrock | none found | Not available as of 2026-09-27 |

## 12. Decisions requiring your approval

1. ~~Implement `experiments/router_bench/` offline~~: **done** (approved 2026-09-28; see §13).
2. **Data egress to TypeSafe.** Approve sending:
   - the question text of the listed case IDs;
   - the fixed instruction and criteria text (§6).

   **Set.** The benchmark supports all 34 frozen v2 questions (decided 2026-09-28). The egress
   approval for that set is still outstanding, and so is the verification pair (L01, L12).
   All questions are about public companies and contain no personal data.
3. **Jev verification:** calls 1–2 (optionally 3), on L01 and L12, with the $0.01 cap. This
   needs `TYPESAFE_API_KEY` in the local `.env`, which you add yourself.
4. **Phase A benchmark run:** 10 repetitions, Haiku and Jev, about $0.17–0.20, with the §8 caps.
   This should come only after items 1–3 and a dry-run review.
5. **The 20% application-error validity threshold** stays unchanged for this work (decided
   2026-09-28). Its limitations are recorded in `eval/README.md` for a separate review.

## 13. Implementation (offline) and unresolved assumptions

**Commands.** All of these are offline by default:

```bash
python -m experiments.router_bench                    # benchmark dry run: plan + simulated execution
python -m experiments.router_bench verify-jev         # §7 verification dry run (L01, L12)
pytest tests/test_router_bench*.py
```

Live runs exist but are **not authorized**:
- `--live typesafe` (verification);
- `--live bedrock --live typesafe` (benchmark).

A live run refuses to start in any of these cases:
- inside pytest;
- when a provider it calls is not authorized;
- for a benchmark, with fewer than 6 repetitions;
- when `TYPESAFE_API_KEY` is missing;
- when `BEDROCK_MODEL_ID` is not the pinned Haiku 4.5 model;
- when the Bedrock client would retry.

**Module map:**

| Module | Contents |
|---|---|
| `config.py` | Frozen parameters |
| `safety.py` | `LiveAuthorization`, `SecretValue`, `Ledger` (budgets), `DownstreamTripwire`, artifact checks |
| `payload.py` | Frozen Jev request, `ApprovedQuestions` allowlist |
| `routers.py` | Haiku (the unchanged `RouterAgent`), rules, Jev client and schema validation |
| `fakes.py` | Offline stand-ins for the providers |
| `runner.py` | Plans and execution |
| `persistence.py` | Crash-resistant, sanitized per-call journal |
| `metrics.py` | Everything in §3–§5 and the §10 criteria |
| `cli.py` | The command-line interface |

**Dry-run results** (`e6f52a5`):
- Questions: 34 (strict 24 `qa` and 7 `summarize`; policy L19; exploratory L17 and L20).
- Planned calls: Bedrock 343, TypeSafe 343, local rules 340.
- Estimated cost: $0.1662. Hard caps: $0.50, $0.05 and $1.00.
- Fingerprints:
  - dataset `9d4f2da1…`;
  - payload `54e2deaa…`;
  - rules `86cea35d…`.
- Downstream isolation: clean (no downstream module is even imported).
- Outbound network attempts: 0.

**Unresolved assumptions** (to settle during verification, or before Phase A):
1. **Jev request schema.** The `instructions` field and the `answers.route.*` / `usage.*` response
   fields come from the documentation and are unverified. A 422 on the first verification call
   stops everything.
2. **Jev tokens and price.** The 250 input tokens per call and $0.042 per 1M are assumed. The
   verification compares reported usage with a local byte/4 estimate.
3. **Haiku output limit.** Superseded by §13.1: the strict reservation assumes Haiku 4.5's
   documented 64,000-token output limit.
4. **Failed calls.** Jev failures are charged at worst case ($0.002688 each). Haiku failures cost
   $0 only when the request was not sent, or was rejected before inference (see §13.1);
   otherwise they are charged the full reservation.
5. **Bedrock retries.** A live `HaikuRouter` sets `AWS_MAX_ATTEMPTS=1` itself, and refuses to
   run unless the client's `total_max_attempts` is 1.
6. **Rules router contamination.** Its patterns come only from the taxonomy text, but the author
   had seen these 34 questions. Its dry-run score (31/31, deterministic and real) is **not** an
   unbiased estimate. The held-out set is needed.
7. **Simulated numbers.** Haiku and Jev metrics in a dry run come from seeded fakes and measure
   nothing.
8. **Region.** Phase A latency is client-side from this machine. TypeSafe's serving region is
   still undocumented.

### 13.1 Hardening after the independent audit of `037ad7b`

**Commits:** `1dfbf58`, `b691d48`, `29a0408`, `41c8ae9`.

**Authorization cannot be bypassed by injection.**
- `HaikuRouter` accepts an injected client only if it is an `OfflineFakeClient`; botocore clients
  are always refused. `JevClient` accepts only an `httpx.MockTransport`.
- Every other path needs a provider-specific `LiveAuthorization`.
- Authorization and the model pin are checked before `app.agents.router` is imported. That
  module calls `load_dotenv()` when first imported, and the import runs with `.env` loading
  disabled.

**Credentials.** A live run reads only the `.env` names its authorized providers need:
- TypeSafe: `TYPESAFE_API_KEY`, read straight into a `SecretValue` and never exported to
  `os.environ`;
- Bedrock: the AWS credential names and `BEDROCK_MODEL_ID`.

The CLI never calls `load_dotenv()`. Server-controlled text is never stored:
- schema errors are fixed codes;
- unknown field names and unsafe header values are redacted.

**Persistence.** Each live run writes a JSON-lines journal (`<artifact>.journal.jsonl`). Every
entry is sanitized, flushed and fsynced, and the file is never overwritten.
- `call_started` is written before every paid call, and each record as soon as it is settled.
- An interrupt or crash is recorded before the process exits.
- A record that fails the safety check is replaced by a minimal typed diagnostic.
- If the full artifact is refused, a minimal diagnostic artifact is written instead (exit 3).

**Model pinning.** The run refuses unless `BEDROCK_MODEL_ID`, the constructed agent and every
recorded call use `us.anthropic.claude-haiku-4-5-20251001-v1:0`.

**Budget guarantee.** `RouterAgent` and its generation settings are unchanged, so the benchmark
adapts its accounting instead.

| Reservation (`--haiku-reservation`) | Reserved per Haiku call | Guarantee |
|---|---|---|
| `strict` (default) | 2,000 input + 64,000 output tokens = **$0.322** | **Hard cap:** committed Bedrock spend cannot exceed the ceiling |
| `practical` | 2,000 input + 1,000 output = $0.007 | **Not a hard cap:** one call can overshoot the ceiling by up to **$0.315**, after which the run stops |

Jev reserves the documented 64,000-token request maximum ($0.002688), so the TypeSafe cap is
hard as well.

These guarantees rest on the following assumptions, which the dry run prints:
- Haiku 4.5's documented output maximum of 64,000 tokens;
- at most 2,000 input tokens per Haiku call;
- list prices;
- Jev output tokens are free;
- Bedrock does not bill requests it rejects before inference (throttling, authorization,
  validation, 503).

If the model limit or the prices are wrong, the "hard cap" is not guaranteed.

**Headroom caveat.** With the default caps, the strict reservation leaves only **$0.0154** of
Bedrock headroom at the expected cost:

> $0.50 cap − $0.1626 expected − $0.322 reservation = $0.0154

- If real per-call cost runs about 9% above the measured average, the last calls cannot reserve
  their worst case. The run then stops early and is invalid; no overspend occurs.
- Options, which need your decision:
  - raise the Bedrock cap to about $0.60;
  - accept the risk;
  - use `practical` mode, accepting the disclosed $0.315 overshoot.

**Latency intervals.**
- Latency now uses a two-way cluster bootstrap that resamples questions and repetitions.
- The Haiku comparison is paired on the same resampled cells.
- On synthetic data where 4 questions are slow, the new p95 interval is [370, 2063] ms. The old
  per-call bootstrap gave [2021, 2056] ms, far too narrow.
- Accuracy methods are unchanged.

**Validity.** One verdict combines:
- execution validity;
- per-router infrastructure errors above 1%;
- decision mismatches (the benchmark's rule vs `RouterAgent`'s own decision);
- harness errors.

The follow-up criteria can pass only when that verdict is valid.

## Appendix A. Route-label adjudication (decided 2026-09-28)

The taxonomy, from `RouterAgent`'s system prompt:
- **`qa`**: "a specific fact, figure, or answer retrieved from financial documents".
- **`summarize`**: "a high-level overview, narrative summary, or analysis of risks, themes, or
  trends".

Historical results and the eval harness keep the v1 labels. The decisions below apply only in
routing dataset v2.

| Case | Question | v1 label | Baseline router | v2 decision |
|---|---|---|---|---|
| **L13** | "What are the main business segments of JPMorgan Chase?" | `summarize` (needs review) | `summarize` | **Clear `qa`** (approved). A list of named segments is a specific, verifiable fact. The baseline router is now counted wrong on it |
| **L17** | "What is a financial statement?" | `qa` (needs review) | `summarize` | **Excluded.** A general definition; no taxonomy class fits |
| **L19** | "Goldman Sachs 2025" | `qa` (needs review) | `summarize` | **Policy case** (approved, experimental): "unclear → `qa`". Scored as compliance, not accuracy. Production routing is unchanged |
| **L20** | "What was JPMorgan Chase's revenue and also summarize their risk factors?" | `qa` (needs review) | `summarize` | **Excluded.** Two intents; handle multi-intent queries later |
