# Router benchmark: Haiku 4.5 vs deterministic rules vs TypeSafe Jev

**Status:** design only (Phase 0.5, 2026-09-28). Nothing here is implemented, and Jev has not
been called. Every paid call below needs explicit approval.

## 1. Question and scope

Can routing be made cheaper and faster without making routing decisions worse?

- **Routing only.** The benchmark measures the routing decision. It does not measure answer
  quality downstream.
- **Why this is worth measuring.** Phase 0 baseline (run `6a13ffb1`):
  - Routing is correct on **30/30** clear labels.
  - Routing costs **0.87 s p50 / 1.17 s p95**.
  - That is about **34% of QA-path latency at p50** (2.53 s), measured in-process.
- **Explicitly out of scope:**
  - changing downstream QA or summarization;
  - changing the production router;
  - deploying anything.

## 2. Candidates

All candidates implement the same interface, `route(query) -> {task_type, confidence, raw, outcome}`,
with the same taxonomy (`qa` | `summarize`) and the same final-decision rule (§4).

| Router | Implementation | Deterministic? |
|---|---|---|
| **Haiku 4.5 (control)** | The existing `app.agents.router.RouterAgent`, imported and called unchanged: same prompt, model ID and default inference parameters | No (default temperature) |
| **Rules** | A new experiment-only module. Keyword and phrase rules written **only from the router's taxonomy text**, then frozen and hashed before any run | Yes |
| **Jev** | A new experiment-only HTTP client for TypeSafe `jev-1.13.0`: one Choice question whose criteria are copied verbatim from the router's taxonomy | Unknown (not documented) |

**Isolation from downstream code:**
- Experiment code lives in a new `experiments/router_bench/` package, not in `app/`.
- It imports `RouterAgent` only. It never imports or calls `CopilotOrchestrator`, `QAAgent`,
  `SummarizerAgent`, the retriever or generation.
- A unit test makes those modules raise if they are touched during a benchmark run.
- No application file changes. Integrating a winner later would be a separate, approved phase.

## 3. Frozen dataset and labels

- **Queries:** the 34 cases in `eval/eval_queries.py`, frozen by recording a SHA-256 of
  `(id, query, expected_route, route_label_status)` for each case before the first call.
- **Strict set:** the **30 clear labels** (23 `qa`, 7 `summarize`). This is the only set used for
  headline accuracy.
- **Ambiguous set:** L13, L17, L19, L20 (see Appendix A).
  - Excluded from strict accuracy.
  - Reported separately: each router's prediction, agreement between routers, and agreement
    with a "default to `qa` when unclear" policy if you adopt one.
- **Relabelling rule:** if you approve relabels, they are applied **before** the benchmark as a
  new dataset version with a new hash. They are never applied to existing results.

**Statistical limit.**
- With n = 30, perfect accuracy has a 95% Wilson interval of **[88.6%, 100%]**. Routers that
  differ by less than about 10 points can't be told apart on this set.
- Accuracy here is a sanity check, not grounds for a production decision.
- A held-out routing set of at least 150 human-reviewed queries, written without reference to
  the rules, is recommended before any integration decision. Building it needs its own approval.

## 4. Decision criteria (identical for every router)

1. **Raw prediction:** the router's own label.
2. **Final decision:** the production-equivalent rule from `RouterAgent`:
   - invocation or parse failure → `qa` (`fallback_invoke_error` / `fallback_parse_error`);
   - chosen-label probability below **0.6** → `qa` (`fallback_low_confidence`).
3. **Comparable confidence scales.**
   - **Haiku:** its self-reported `confidence`.
   - **Jev:** `probabilities[choice]`, the probability of the chosen label. Jev's own `confidence`
     field is a rescaling of that probability (for 3 options the docs give `(3·p_max − 1)/2`, so
     for 2 options it is presumably `2·p_max − 1`; unverified). Thresholding it at 0.6 would be a
     different rule. It is recorded, not used.
   - **Rules:** confidence 1.0; the rules never fall back.
4. Accuracy is reported for both the raw and the final decision. A threshold sweep (0.5–0.9) is
   computed offline from the recorded probabilities, at no extra cost.

## 5. Measurements

| Measurement | Definition |
|---|---|
| Strict accuracy | Final decision vs clear label, with 95% Wilson CI. Also per-class recall (especially `summarize`, n = 7) and the confusion matrix |
| Label stability | Per query, the share of repetitions that disagree with that router's majority label |
| Fallback rate | Share of calls that fell back, by reason (invoke error, parse error, low confidence, timeout) |
| Infrastructure error rate | 401/403/422/429/5xx/529, and timeouts. **Above 1% of calls → that router's run is invalid** |
| Latency | Client-side wall clock (`time.perf_counter`) around `route()`, including network. p50, p95 and p99 per router, with bootstrap 95% CIs for each and for the difference vs Haiku. Warm-up calls excluded. Haiku's server-side `metrics.latencyMs` recorded where available |
| Cost | Recorded tokens × list price per call, and cost per 1,000 routing decisions. Output tokens recorded for Jev too: the docs show a `usage.output_tokens` field, though output is stated to be free |
| Agreement | Cohen's κ between each pair of routers on all 34 queries |
| Projected end-to-end effect | Router p50 and p95 savings applied to the baseline QA-path latency. Labelled a projection |

**Repetitions.**
- **Minimum 6, recommended 10**, per router over all 34 queries. That gives 204–340 samples per
  router, so the nearest-rank p95 rests on 11–17 tail samples. (At 34 samples it is just the
  2nd-largest value.)
- The rules router needs one run for accuracy; its latency is in microseconds.

**Ordering and warm-up.**
- Within each repetition, routers are called round-robin per query, in a seeded random order, so
  network or time-of-day drift affects them equally.
- 3 warm-up calls per router per session are discarded and reported separately as connection
  setup.

**Network topology.**
- Phase A runs locally. That biases absolute latency: Bedrock is in us-east-1, while TypeSafe's
  serving region is **not documented**.
- An optional Phase B repeats the benchmark from an AWS us-east-1 environment for
  production-representative latency. That needs separate approval.

## 6. Jev integration (experiment-only)

- **Endpoint:** `POST https://api.typesafe.ai/v1/systemone`, with headers
  `Authorization: Bearer $TYPESAFE_API_KEY` and `Content-Type: application/json`.
- **Client:** `httpx`, already a pinned dependency. No new package, and the brand-new
  `typesafe-sdk` 0.7.2 isn't needed.
- **Timeouts:** connect 2 s, read 5 s.
- **Retries:** none. A failed call is recorded as an infrastructure error, and the router falls
  back to `qa`.
- **Request:**
  ```json
  {"state": "<query>", "model": "jev-1.13.0",
   "questions": {"route": {"type": "choice",
     "instructions": "Classify this financial research query into exactly one category.",
     "criteria": {"qa": "<RouterAgent 'qa' definition and examples, verbatim>",
                  "summarize": "<RouterAgent 'summarize' definition and examples, verbatim>"}}}}
  ```
- **Parsing:** read `answers.route.choice`, `.probabilities`, `.confidence`, the top-level
  `model`, and `usage.input_tokens` / `usage.output_tokens`.
- **Configuration:**

  | Variable | Value | Notes |
  |---|---|---|
  | `TYPESAFE_API_KEY` | secret | Local `.env` only. Never logged, committed or added to CI. Sent only in the `Authorization` header, and HTTP debug logging is disabled |
  | `JEV_MODEL` | `jev-1.13.0` | **Pinned.** `jev-latest` and `jev-preview` are aliases that can move to a new model |
  | `JEV_ENDPOINT` | `https://api.typesafe.ai/v1/systemone` | Only the official domain. The docs site has look-alikes (jevapi.org, jev-ai.pro, tokenra.io) |

- **Data sent to TypeSafe:** the 34 evaluation queries. They are public-company questions with no
  personal data, but they leave AWS. TypeSafe documents retention guarantees (zero retention)
  only for enterprise customers, so **sending them needs your approval**.

### Documented vs verified

| Item | Source | Status |
|---|---|---|
| Endpoint, auth header, request/response field names, Choice schema (≤ 255 options) | docs.typesafe.ai `/api`, `/primitives/choice` (re-checked 2026-09-28) | Documented; **not verified by a call** |
| Pricing: $0.042 per million input tokens, output free | `/models` | Documented; not verified against a bill |
| Rate limits 250k tokens/s and 1,200 requests/min, "adjusting dynamically" | `/models` | Documented; may change without notice |
| Errors 401/422/429/529; back off exponentially on 429/529 | `/api` | Documented |
| `confidence` formula for 2 options | `/confidence` (3-option example only) | **Inferred**, unverified |
| Calibration of probabilities | `/confidence`: "not stated" | **Unknown** |
| Latency, determinism, serving region, default data retention | not stated | **Unknown**. The benchmark measures the first two |
| Availability on Amazon Bedrock | none found | Not available as of 2026-09-27; it is an external HTTP dependency |

**Proposed pre-benchmark verification (1–3 calls, needs approval, about $0.0001):** confirm the
response schema, the confidence scale for 2 options, token counting and the error format before
running repetitions.

## 7. Cost and safeguards

| Item | Calls (10 repetitions + warm-up) | Estimated cost |
|---|---|---|
| Haiku router (measured 214 in / 52 out per call) | 34 × 10 + 3 = 343 | ≈ **$0.16** (≈ $0.18 with a possible 10% `us.*` premium) |
| Jev (≈ 150–250 input tokens per call, assumed) | 343 | ≈ **$0.003** (unverified pricing) |
| Rules | 34 | $0 |
| **Total (Phase A)** | | **≈ $0.17–0.20** |
| Optional: 150-query held-out set × 5 repetitions | 750 Haiku + 750 Jev | ≈ $0.36 + $0.01 |

**Safeguards:**
- A hard cost ceiling of $1 per benchmark run, using the same mechanism as the eval harness.
- Per-router call caps.
- Stop a router after 3 consecutive infrastructure errors, and mark its results invalid.
- Jev calls paced to at most 60 per minute, far below the documented 1,200.
- No calls to downstream agents (enforced by a test).
- Results go to `eval/results/experiments/router-bench-<date>/` with provenance: git SHA,
  dataset hash, rules hash, the Jev `model` string as returned, and the environment.
- The API key is never written to logs or results.

## 8. Pre-registered reading of results

A candidate is **worth a follow-up held-out and end-to-end evaluation** only if all of these hold:

| Criterion | Threshold |
|---|---|
| Strict accuracy | ≥ 28/30 on the final decision |
| `summarize` recall | ≥ 6/7 |
| Infrastructure error rate | ≤ 1% |
| Fallback rate | ≤ 5% |
| p95 routing latency | ≥ 300 ms lower than Haiku, with the bootstrap CI of the difference excluding 0 |

Neither result, positive or negative, is a production decision on its own. A decision needs:
- the held-out set;
- an end-to-end eval run through the unchanged downstream path (paid, separately approved);
- a privacy decision on sending queries to TypeSafe.

## Appendix A. Route-label adjudication (no labels changed)

The taxonomy, from `RouterAgent`'s system prompt:
- **`qa`**: "a specific fact, figure, or answer retrieved from financial documents".
- **`summarize`**: "a high-level overview, narrative summary, or analysis of risks, themes, or
  trends".

Every existing result keeps its original label. All four cases stay `needs_review` and excluded
from strict accuracy until you decide.

| Case | Question | Current label | Baseline router | Alternatives | Effect on router evaluation | Recommendation |
|---|---|---|---|---|---|---|
| **L13** | "What are the main business segments of JPMorgan Chase?" | `summarize` (answer expected, reference exists) | `summarize` | **`qa`**: a list of named segments is a specific, verifiable fact on one page. `summarize` is also defensible ("overview") | Under `summarize`, the router looks correct, but the answer takes the ungrounded path (the baseline said "four segments", correctness 2). Under `qa`, the same routing would count as an error | **Disputed.** I recommend relabelling to clear `qa`, which would make it gated with its verified reference. **Needs your approval** |
| **L17** | "What is a financial statement?" | `qa` (behavior "either") | `summarize` | `qa`, `summarize`, or "out of scope". It's a general definition, not about the filings | No taxonomy class is correct, so any accuracy score measures the label, not the router | **Keep excluded** from strict accuracy. Report separately |
| **L19** | "Goldman Sachs 2025" | `qa`, a safe default, not a judgment of intent | `summarize` (the summarizer then refused) | `summarize` (implied overview), `qa`, or ask for clarification | The label encodes a policy ("unclear → `qa`"), not a correct answer | **Keep excluded.** If you adopt "unclear → `qa`" as policy, measure it as a separate policy-compliance number. **Needs your approval** |
| **L20** | "What was JPMorgan Chase's revenue and also summarize their risk factors?" | `qa` (answer expected) | `summarize` (lost the revenue figure; correctness 2) | `qa`, `summarize`, or both. Two intents can't be expressed with two classes | Either label is partly wrong, so accuracy on this case is uninformative | **Keep excluded.** Handle multi-intent questions later (splitting them, or a taxonomy change) |
