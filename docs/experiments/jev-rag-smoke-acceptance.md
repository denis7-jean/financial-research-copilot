# Jev isolated RAG integration smoke — acceptance contract

Claude, 2026-10-07. This is an **implementation-independent** acceptance contract for the forthcoming isolated RAG smoke controls, written in parallel with Codex's offline implementation and **without reading it**.

**Revision 2** corrects RAC-1 to RAC-6 from Codex's independent review `jev-rag-smoke-acceptance-codex-review-20261007-73c2b980.md` (SHA-256 `ebe409d2…`). The contract was corrected on its merits, not adjusted to fit any implementation. Section 8 maps each correction.

It defines what any implementation must make true, when, and what it must never claim. The scenarios in `tests/fixtures/jev_rag_smoke_acceptance.json` are **declarative**: invented premises and required results, written so that a reviewer can map them onto whatever interface is eventually accepted. They are not executed by any acceptance engine, and none exists.

It is not:
- an execution framework, an API, or an owner approval;
- a budget, resource, IAM, disclosure or run authorization.

## 1. Bindings

| Input | SHA-256 / value |
|---|---|
| Base commit | `274e283e353261c4d50b0d4f18ee97366d80d7ef` |
| Proposal `dependency-acquisition\2026-10-06-rag-smoke-plan-7f467d10\plan.md` | `ac0e7ca4aecff038fc151d67471faac552863cf82e5e0297c2c222701bc0d4c3` |
| Proposed event `…\proposed-event.json` | `0401ca088ac62467e8e424ba2007d1b6dc5ec1e1731f15064929f91bcede26b9` |
| Static metadata scan `…\trusted-metadata-static.json` | `435d27de6d4b115fdcf2abbdc5acc061db2ba1fe79a2959788922c95b886df6f` (2,220 rows; five source counts sum to 2,220) |
| Trusted `financial_index.faiss` (`2026-10-04-65eae87\private`) | `3d2b3ebd4f992aad3c2be8a09761a18fbc9a17d08d63db99bf6853697abfa5e9`, 9,093,165 B |
| Trusted `financial_meta.json` (same folder) | `f771ba6ce75759ba88e4ad376c642746327592afb991e107bd63c09029317429`, 7,748,288 B |
| Local FAISS readability receipt | `95cad6ed2bbe9477861932d8df4b46d526abcc606f05258f7b683bfe7695155d` (numeric only; no semantic proof) |
| Health-only startup outcome | `ebc9eecf6af6dbba3317c35e4b0d7739fbd2b7ba02d918ca911b4f873f448cd9`: init 2,141.94 ms; max memory 155/155/156/156 MB of 512 MB |
| Baseline capture review | `dcf4cf081b51cc0c0594e018795b9b61b2c7dc45a93293ac15c9aa97671b8c29`. The production `$LATEST` only; one layer still attached. It is not the smoke target. |

Source behaviour cited, with blob SHA-256 at the base:
- **`app/agents/router.py` (`177d1f5e…`):**
  - an invoke error (l.86), a parse error (l.125) or confidence below 0.6 (l.127) all **fall back to `qa`**;
  - a router failure does not stop QA dispatch.
- **`app/services/retriever.py` (`af54b9b0…`):**
  - S3 `download_file` for the index and metadata (l.42–43) leads to `read_index` (l.45) with no hash gate;
  - Titan is called with `dimensions: 1024, normalize: true` (l.56);
  - the search loop skips `-1` but does not range-check other indices (l.99–108). A negative index such as `-2` would silently address a wrong row.
- **`app/services/bedrock_client.py` (`ce60f47a…`):**
  - empty retrieval returns `outcome: empty_retrieval` with HTTP 200 (l.28–34);
  - `citations` is the set of **retrieved** sources (l.76), not citations validated against the answer.
- **`app/agents/qa_agent.py` (`5163c220…`):** confidence is `1.0` if any citations, else `0.5` (l.52), a heuristic.

## 2. Phases (RAC-5)

| Phase | Where and when | What must hold |
|---|---|---|
| **P0 — before the parent Invoke** | operator side, before any outbound call | **Approved bindings:** the artifact (code SHA), event and query, configuration, both trusted-object identities (AC-03), models, caps and evidence records. **Parent client:** the actually resolved invocation client has zero retries and a bounded timeout. **Owner decisions:** all of section 6 granted. **Worst-case sufficiency:** the sum of every approved inner attempt's worst-case reservation, plus the infrastructure allowance, fits the approved ceilings, and the task-wide reservation is recorded. **Exclusive operator claim:** one durable claim per authorized run, with no existing claim for the plan. A reviewed client *factory* or artifact is P0 evidence of **intended** inner behaviour only. |
| **P1 — inside the function, before each inner dispatch** | runtime, per stage | **Actual inner clients:** the resolved inner SDK clients (and any transfer) show zero retries, the exact timeouts and endpoint, and installed parameter and send gates, checked **before that client's first request**. **Stage gates:** each stage's gate (section 3) passes before the next dispatch. Per-attempt reservation precedes each dispatch. |
| **P2 — observations after dispatch** | runtime and operator | Observed sends and retries, request IDs, usage and charges, results, Lambda INIT/REPORT, evidence publication. |

**Ordering rules:**
- P2 observations never satisfy a P0 or P1 requirement. For example, zero observed retries do not show that retries were configured to zero.
- Per-attempt exposure checks at P1 do not replace P0 worst-case sufficiency, which remains a **future execution prerequisite**.

## 3. Acceptance clauses

- **AC-01 Attempt budget.**
  - **Limits:** at most **1** parent Invoke, **1** routing, **1** embedding and **1** QA-generation attempt; **0** SDK, provider or transfer retries; **0** replacements or resends.
  - **What counts:** every delivered request is counted individually, whatever its outcome.
  - **Not allowed:** no summarizer call, judge or second model.
  - **An extra send has two cases (RAC-3):**
    - **(a) blocked before delivery:** stop, with no new exposure for the blocked send.
    - **(b) already delivered, discovered afterwards:** stop. Record it as its own request with its own usage or exposure (AC-07). It is never authorized retroactively.
- **AC-02 Strict routing.** Any of the following stops the run **before** the index read, embedding and generation:
  - a router invoke error or parse failure;
  - confidence below the routing threshold;
  - any fallback marker;
  - a `summarize` route;
  - an unknown routing outcome.

  The production fallback behaviour stays unchanged **outside** the opt-in smoke.
- **AC-03 Trusted object identity before deserialization (RAC-1).** For **each** of the two objects, all of the following must hold:
  - **(a) approved identity:** the exact approved bucket owner, bucket and key;
  - **(b) conditional request:** the request carries the conditional identity: expected bucket owner plus `IfMatch` equal to the approved ETag, and `VersionId` equal to the approved version when the binding has one. When the binding records no version, that explicit null relationship is part of the binding;
  - **(c) response joins:** the response's ETag, version (or its absence) and content length equal the approved values;
  - **(d) exact bytes:** an exact byte size **and** a full raw SHA-256 equal to the approved values.

  **Size never substitutes for conditional identity:** matching size or hash does **not** cure a missing condition or a changed identity.
  - Both objects must pass before any metadata is consumed or the index is deserialized. Strict metadata parsing then applies: no duplicate keys or non-finite values; contiguous integer `chunk_id` equal to the row number; string source and text; sources in the allowlist.
  - **On any failure** (a missing condition, a changed identity, a failed precondition or an ambiguous read): stop. There is no alternate snapshot, retry, rebuild or repair.
- **AC-04 Index structure.** Before embedding is dispatched, the index must be:
  - flat inner-product (`IndexFlatIP`, inner-product metric);
  - dimension 1024;
  - `ntotal` equal to the metadata row count (2,220 for the bound snapshot).
- **AC-05 Embedding (RAC-4).** Before search or generation:
  - the vector has exactly 1,024 finite numeric (non-bool) values with an approximately unit norm (normalization was requested); the numeric tolerance is fixed at implementation review;
  - **the applicable usage is present and valid:** an input-token count that is a built-in non-negative integer within the supplied bound.

  **On failure:**
  - missing or malformed usage stops the run and retains the **full** reservation;
  - out-of-bound usage is recorded unclamped and stops the run;
  - zero usage is never inferred, and a valid vector never stands in for usage.
- **AC-06 Search and sources.**
  - Exactly **k = 5** results, with each index an integer in `[0, ntotal)`. Negative or out-of-range indices are a **stop**, never skipped or wrapped.
  - Indices are distinct, scores finite and non-increasing.
  - Every source is in the allowlist.
  - Expected-source presence (≥1 expected source for the bound question) is checked **before** generation. Failing it stops the run; it is never retried with another k or query.
- **AC-07 Accounting (RAC-2, RAC-3, RAC-4).**
  - **Records:** exact Decimal or integer money, with **one accounting entry per delivered request**.
  - **Reserve first:** each approved request is reserved before dispatch, within the P0 task-wide reservation.
  - **Settle:** settle only from usage that is independently valid **for that request**. A response rejected as a whole does not yield trustworthy usage unless its usage is separately established.
  - **Unknown outcomes:** missing, malformed or unestablished usage, a timeout after send, uncertain dispatch, or a function error after send all retain the **full** reservation.
  - **Overruns:** recorded **unclamped**; they latch abort.
  - **Unapproved delivered requests** (an extra send, a summarizer, an unexpected endpoint):
    - each is recorded separately, with its known usage or its unknown exposure;
    - none is folded into another stage's single reservation;
    - the reservation coverage is marked **violated** where it is exceeded, and the ceiling is marked **not established** unless it is independently provable.
  - **Infrastructure requests** (S3 reads, logs) are counted against the infrastructure allowance, never against a model reservation.
  - **Prior holds:** a refused or duplicate attempt **never** releases, refunds or alters another attempt's or run's claims, attempt records or holds.
- **AC-08 Evidence (RAC-6).** **Evidence completion** and the **experiment outcome** are independent.
  - **Evidence is complete and confirmed** only when the exclusive claim existed, the full ordered journal of every attempt, send, usage and stop was published, and the operator holds the successful returned status **and** a matching evidence-index hash.
  - **Evidence is incomplete** when publication is partial, unconfirmed or missing, or the Lambda REPORT is unavailable. **This holds even if the answer looks successful.** Partial files are disclosed and never bound as successful, and there is no rerun.
  - **Complete evidence of a failure** (for example an overrun, failed retrieval or a stop) is still complete evidence. It never implies RAG success, accounting success, qualification or release.
  - **Sanitization:** console and journal output carry no retrieved text, prompts, answers, secrets, signed URLs or provider messages.
- **AC-09 What "RAG success" (structural) means.** **All** of the following must hold:
  - complete, confirmed evidence (AC-08);
  - Lambda Invoke success **and** nested HTTP 200;
  - `task_type` `qa` from a successful, non-fallback route;
  - AC-03 to AC-06 passed;
  - a non-empty retrieved context;
  - valid usage for all three model calls, all within their reservations;
  - a non-empty answer that is neither the no-evidence answer, an empty-retrieval outcome, nor a **genuine abstention**.

  **Abstention is classified by the operator, not by code.** It is a recorded semantic classification of the privately retained answer, made under the approved disclosure, with the answer hash and the classifier's identity. It is not an automatic judge, and structural checks never prove answer correctness.

  HTTP 200 alone is **never** success.
- **AC-10 Lambda measurements.**
  - **Record:** INIT and REPORT duration, billed duration and max memory, separately from the client-observed duration.
  - **Health figures are context only:** 155–156 MB and a 2,141.94 ms init are health-only and are **not** RAG baselines.
  - **No invented thresholds:** none except owner-approved memory and time limits.
  - **On OOM, timeout or a runtime exit:** stop and record; no automatic memory or timeout increase and no rerun.
- **AC-11 Claim limits.** Acceptance establishes **structural and numeric consistency only**. In particular:
  - retrieved sources are not validated answer citations;
  - vector-to-row consistency does not prove semantic alignment;
  - the historical $182,447M JPMorgan figure is a recorded runbook reference, **not** freshly authenticated ground truth;
  - one request is not quality qualification, Jev readiness or release permission.
- **AC-12 Stop semantics.** A stop denies **further** dispatch only. A timeout or local abort does not cancel a request already delivered, and an uncertain provider outcome may already be billable (AC-07).
- **AC-13 Scope.**
  - The smoke controls are opt-in and isolated: there are no production default changes, no extra endpoints, and the custom request log stays off.
  - Behaviour outside the smoke stays golden-test identical.
  - An unexpected endpoint, service or summarizer is a violation and a stop, under AC-01 (a) or (b).

## 4. Fixture schema `jev-rag-smoke-acceptance-scenarios-v2` (changes from v1)

**Fields:**
- **`outcome` is split (RAC-6):** into `experiment_outcome` and `evidence_outcome`.
  - `experiment_outcome` adds `RESULT_NOT_ESTABLISHED`, for when evidence is incomplete.
  - `evidence_outcome` is one of `EVIDENCE_COMPLETE_CONFIRMED` or `EVIDENCE_INCOMPLETE`.
  - `PASS_STRUCTURAL` requires complete, confirmed evidence.
- **`accounting` changes from a stage→code map to a list of per-request entries (RAC-3):** `{request, stage, approved, delivered (YES|NO|UNKNOWN), usage, treatment}`.
- **`reservation_coverage` and `ceiling_status`** make guarantees explicit. A ceiling status is never asserted when it is not established.
- **`prior_run` (RAC-2):** the earlier claim, attempts and holds, with a required `UNCHANGED` post-state.

**Vocabulary changes:**
- `NO_DISPATCH` → `NO_DISPATCH_THIS_ATTEMPT`. It is scoped to the current attempt and **never** releases another attempt's hold.
- New treatments: `RECORD_UNRESERVED_ACTUAL`, `RECORD_UNRESERVED_EXPOSURE` and `INFRASTRUCTURE_ALLOWANCE`.
- New stage `INFRASTRUCTURE`.
- New usage states `VALID`, `VALID_OVER_BOUND`, `MISSING`, `MALFORMED`, `UNKNOWN`, `UNTRUSTED` and `NONE`.
- Claims: `COMPLETE` becomes `EVIDENCE_COMPLETE`; added `PRIOR_HOLD_RELEASED`, `SENDS_AUTHORIZED` and `CEILING_HELD`. The prohibited `REPORT_COMPLETE` becomes `REPORT_EVIDENCE_COMPLETE`.

**IDs.** Scenario IDs S01–S38 are kept. Split or added cases are S39–S48.

All values remain invented placeholders. They are not production facts, proposed limits, prices or approvals.

## 5. External prerequisites (not verified here; no live check authorized)

These must be verified before any run:
- current official Haiku and Titan V2 pricing, and the Titan input-token bound `T`;
- the exact Haiku inference-profile ARN and its destination regions;
- model access, SCP and encryption facts;
- the runtime IAM actually granted;
- release-preflight of the exact new artifact.

## 6. Owner decisions still required

Proposed values come from the plan. **None is approved or enforceable until the owner grants it.**

| # | Decision | Proposed (unapproved) |
|---|---|---|
| D1 | Data disclosure and retention: the question to Titan and Haiku, top-5 public-corpus chunks and source strings to Haiku, private retention of full responses, and operator abstention review | One public JPMorgan FY2025 question; public corpus only; metadata-only logs |
| D2 | Optional numeric spot check | Structural only; a spot check needs a separately located authoritative filing |
| D3 | Output caps `R` (routing) and `G` (generation), the gross inference ceiling, and the expected-source condition | Worked example only: R=256, G=256/512; no ceiling selected |
| D4 | Infrastructure, log and retention allowance | None selected |
| D5 | Isolated resources and IAM: new function, role and log group; exact two-object S3 read; exact model and profile ARNs | Least-privilege outline in the plan |
| D6 | Memory, timeout, ephemeral storage, request deadline and log size | 512 MiB / 30 s / 512 MiB *if* approved; not proven for RAG |
| D7 | Execution authorization: one exact run binding the artifact, event, plan, caps and reservation; and a later, separate cleanup scope | Not granted |

## 7. Validation and scope receipt

- The fixture parses strictly: no duplicate keys or non-finite values, and every enumeration value comes from the declared vocabulary.
- Every clause is defined and covered by at least one scenario.
- **Structural rules checked:**
  - settlement only with valid usage;
  - `NO_DISPATCH_THIS_ATTEMPT` only for undelivered requests;
  - unapproved delivered requests never settle or share a reservation;
  - `PASS_STRUCTURAL` only with complete, confirmed evidence;
  - prior holds unchanged.
- **Invented arithmetic counterexamples** (S05, S41) hold.
- All bindings in section 1 were re-hashed, and `git diff --check` is clean.
- **Not done:** no AWS or network calls, credential or `.env` access, model or native execution, installs, builds, merge or push.

## 8. RAC-1 to RAC-6 correction map

| Finding | Contract change | Fixture change |
|---|---|---|
| RAC-1 object identity | AC-03 rewritten: approved identity, conditional request identity, explicit version relationship, response joins, size **and** hash; size never substitutes | S14 limited to a failed precondition or ambiguous read; new **S39** (same size and hash, condition missing) and **S40** (identity changed, bytes identical) |
| RAC-2 duplicate accounting | AC-07 prior-hold rule | S05 gains `prior_run` (claim, attempts, 9.000000 hold) with an `UNCHANGED` post-state; `NO_DISPATCH_THIS_ATTEMPT` is scoped; new claim `PRIOR_HOLD_RELEASED` |
| RAC-3 extra sends | AC-01 (a)/(b), AC-07 per-request entries and infrastructure allowance | S10 is a second send blocked before delivery; **S41** is an extra routing send already delivered (3.000000 held plus 1.000000 unreserved actual, so coverage is violated and the ceiling not established); S37 is an endpoint blocked before delivery; **S42** is a delivered summarizer as its own `SUMMARIZE` entry; **S43** is a delivered infrastructure request |
| RAC-4 embedding usage | AC-05 requires valid usage; AC-07 adds "whole-response rejection gives no trusted usage" | S16 and S18 state the valid-usage premise; S17 changes to `UNTRUSTED` → retain the full reservation; S19 adds malformed variants; new **S44** for an embedding usage overrun |
| RAC-5 phases | Section 2 rewritten as P0 (bindings, parent client, sufficiency, operator claim), P1 (actual inner clients and send gates), P2 (observations) | S04 is the parent client at P0; new **S45** is the inner client resolved with retries at P1, before its first request; S03 is worst-case sufficiency at P0 |
| RAC-6 outcomes | AC-08 separates the evidence and experiment meanings; AC-09 adds operator abstention classification | All scenarios gain both outcomes; S24 and S26 are complete, confirmed failure evidence; S28 is operator-classified; S33 and S34 are incomplete with the result not established; new **S46** (answer looks successful but publication is unconfirmed), **S47** (confirmed failed-retrieval record) and **S48** (structural success with full confirmed evidence) |
