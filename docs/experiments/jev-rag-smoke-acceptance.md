# Jev isolated RAG integration smoke — acceptance contract

Claude, 2026-10-07. This is an **implementation-independent** acceptance contract for the forthcoming isolated RAG smoke controls, written in parallel with Codex's offline implementation and **without reading it**.

It defines what any implementation must make true, when, and what it must never claim. The scenarios in `tests/fixtures/jev_rag_smoke_acceptance.json` are written so that a reviewer can drive them through whatever interface is eventually accepted.

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

## 2. Phases

| Phase | What holds | Evidence kind |
|---|---|---|
| **P0 — before the parent Invoke** | All of section 6 are approved and bound. The trusted inputs are hash-bound, the exact event is bound, client and transfer configuration is resolved to zero retries, caps and the Decimal reservation are recorded, the exclusive run claim is acquired, and no duplicate exists. | Prerequisites, all checkable **before** any outbound call |
| **P1 — inside the run, per stage** | Each stage's gate passes **before** the next external dispatch (section 3). | Gates that can stop the run |
| **P2 — after the run** | Returned results, usage, request IDs, send counts, Lambda INIT/REPORT, evidence completeness. | Observations; they can fail acceptance, but never retroactively "undo" dispatch |

A P2 observation never substitutes for a P0 prerequisite. For example, observing zero retries does not satisfy "zero retries configured".

## 3. Acceptance clauses

- **AC-01 Attempt budget.**
  - **Limits:** at most **1** parent Invoke, **1** routing, **1** embedding and **1** QA-generation attempt; **0** SDK, provider or managed-transfer retries; **0** replacements or resends.
  - **What counts:** an attempt counts when it is **sent**, whatever its outcome. An unknown outcome consumes the attempt.
  - **Not allowed:** no summarizer call, judge or second model of any kind.
- **AC-02 Strict routing.** Any of the following stops the run **before** the index read, embedding and generation:
  - a router invoke error or parse failure;
  - confidence below the routing threshold;
  - any fallback marker;
  - a `summarize` route;
  - an unknown routing outcome.

  The production fallback behaviour stays unchanged **outside** the opt-in smoke.
- **AC-03 Trusted inputs before deserialization.**
  - **Checks first:** exact bucket owner, key, ETag or size, then raw SHA-256 and size of **both** objects.
  - **Strict metadata parse:** no duplicate keys or non-finite literals; contiguous integer `chunk_id` equal to the row number; string source and text; source in the five-file allowlist.
  - All of this happens **before** `read_index` or any metadata use.
  - **On mismatch, a changed object or an ambiguous read:** stop. There is no deserialization, no alternate snapshot, no rebuild and no repair.
- **AC-04 Index structure.** Before embedding is dispatched, the index must be:
  - flat inner-product (`IndexFlatIP`, inner-product metric);
  - dimension 1024;
  - `ntotal` equal to the metadata row count (2,220 for the bound snapshot).
- **AC-05 Embedding.** The vector must have exactly 1,024 finite values with an approximately unit norm (normalization was requested); the numeric tolerance is fixed at implementation review. Usage, if reported, must be a non-negative integer.

  Any violation stops the run before search and generation.
- **AC-06 Search and sources.**
  - Exactly **k = 5** results, with each index an integer in `[0, ntotal)`. Negative or out-of-range indices are a **stop**, never skipped or wrapped.
  - Indices are distinct, scores finite and non-increasing.
  - Every source is in the allowlist.
  - Expected-source presence (≥1 JPMorgan source for the proposed question) is checked **before** generation. Failing it stops the run; it is never retried with another k or query.
- **AC-07 Accounting.**
  - **Reserve first:** exact Decimal or integer money is reserved before every dispatch, within an approved task-wide reservation made before the parent Invoke.
  - **Settle:** settle only from valid, built-in non-negative integer usage within the reserved bounds.
  - **Unknown outcomes:** missing or malformed usage, a timeout after send, an interrupted or uncertain dispatch, or a function error after send all **retain the full reservation** as potentially billed.
  - **Overruns:** an actual usage above a cap or reservation is **recorded unclamped**, latches abort, and forbids all later dispatch.
- **AC-08 Evidence.**
  - **Before any dispatch:** an exclusive, durable run claim. A duplicate or crashed prior claim is refused.
  - **Run journal:** a complete ordered journal of attempts and sends, plus request IDs, usage and stop reasons.
  - **Completion** requires a successful returned status **and** a matching evidence-index hash. Parseable bytes alone are not completion.
  - **Partial writes** are disclosed, never bound as successful, and never trigger a rerun.
  - **Sanitization:** console and journal output carry no retrieved text, prompts, answers, secrets, signed URLs or provider messages. Private retention follows the owner's disclosure decision.
- **AC-09 What "RAG success" means.** **All** of the following must hold:
  - Lambda Invoke success **and** nested HTTP 200;
  - `task_type` `qa` from a successful, non-fallback route;
  - AC-03 to AC-06 passed;
  - a non-empty retrieved context;
  - a non-empty answer that is neither the no-evidence answer nor an empty-retrieval outcome;
  - valid usage for all three model calls;
  - complete evidence (AC-08).

  HTTP 200 alone is **never** success. An empty retrieval, an abstention, a summary or a fallback can all be HTTP 200.
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
  - An unexpected service, endpoint or summarizer call is a violation and a stop.

## 4. Fixture use

`tests/fixtures/jev_rag_smoke_acceptance.json` (schema `jev-rag-smoke-acceptance-scenarios-v1`) holds invented, interface-neutral scenarios. Each scenario records:
- the clauses it exercises;
- the phase or stage at which the condition occurs;
- an invented `given`;
- the required `outcome`;
- `dispatches_allowed_after` (stages that may still send);
- `prohibited_after`, the required `accounting` and `claims_not_permitted`.

Vocabulary is defined in the file. Prices, caps, usage and texts are **invented placeholders**, not production facts or proposed limits. A reviewer maps each scenario onto the accepted implementation's actual seams and checks the outcome, the absence of later sends and the accounting. A scenario that cannot be expressed through the implementation is itself a review finding.

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
| D1 | Data disclosure and retention: the question to Titan and Haiku, top-5 public-corpus chunks and source strings to Haiku, private retention of full responses | One public JPMorgan FY2025 question; public corpus only; metadata-only logs |
| D2 | Optional numeric spot check | Structural only; a spot check needs a separately located authoritative filing |
| D3 | Output caps `R` (routing) and `G` (generation), and the gross inference spending ceiling | Worked example only: R=256, G=256/512; no ceiling selected |
| D4 | Infrastructure, log and retention allowance | None selected |
| D5 | Isolated resources and IAM: new function, role and log group; exact two-object S3 read; exact model and profile ARNs | Least-privilege outline in the plan |
| D6 | Memory, timeout, ephemeral storage, request deadline and log size | 512 MiB / 30 s / 512 MiB *if* approved; not proven for RAG |
| D7 | Execution authorization: one exact run binding the artifact, event, plan, caps and reservation; and a later, separate cleanup scope | Not granted |

## 7. Validation and scope receipt

- The fixture parses strictly: no duplicate keys or non-finite values, unique scenario IDs, every clause reference defined here, and every enumeration value from the declared vocabulary.
- All bindings above were re-hashed from saved evidence and the base tree.
- `git diff --check` is clean.
- **Not done:** no AWS or network calls, credential or `.env` access, model or native execution, index deserialization, installs, builds, resource changes, merge or push. Codex's in-progress implementation was not read.
