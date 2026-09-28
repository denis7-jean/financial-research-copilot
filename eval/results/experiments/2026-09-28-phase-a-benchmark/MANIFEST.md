# Phase A router benchmark: record manifest

One live run, authorized on 2026-09-28: Haiku 4.5 (the existing `RouterAgent`), the
deterministic rules router, and TypeSafe Jev. **Do not edit the result files.** The hashes below
make any change detectable, and `.gitattributes` stores the files byte-for-byte.

## Files

| File | Bytes | SHA-256 |
|---|---|---|
| `benchmark-20260928T233432Z.json` (artifact) | 530,754 | `11c44b86c7f727f953f048006db4c23c5fee418af0a310e7f12cb1a64562fcaf` |
| `benchmark-20260928T233432Z.json.journal.jsonl` (per-call journal) | 559,358 | `7cb04355766d8ce9768ed545b443a966720aee9b47f320d7607226f3b8ad57d4` |
| `benchmark-20260928T233432Z.console.log` (CLI output) | 3,389 | `d62e672ed9c64577c05b9bf24edf5debb7d4918f3f516dc8a47ccccc0a536eae` |

The artifact and journal were written by the CLI to `eval/results/experiments/` (opened with
`"x"`, so they cannot overwrite anything) and then moved here. Their bytes are unchanged: the
SHA-256 values were checked before and after the move. The console log is a copy of the CLI's
stdout and stderr.

## Run identity and provenance

| Item | Value |
|---|---|
| Run ID | `benchmark-20260928T233432Z`. `created_at` 2026-09-28T23:34:32.097Z; wall clock 23:34:31 → 23:42:50 UTC |
| Command | `python -m experiments.router_bench --live bedrock --live typesafe`: run once, no retries or reruns |
| Code | `fe5564e` on `phase0/baseline-instrumentation-eval`, clean tree (`tracked_changes_uncommitted: false`) |
| Environment | Python 3.13.12 on Windows 11 (10.0.26200), local machine. Client-side latency includes the network path from here |
| Mode | `live`. Authorized: bedrock and typesafe. Real clients: `bedrock-runtime`, `typesafe`. `AWS_MAX_ATTEMPTS=1` |
| Models | Bedrock `us.anthropic.claude-haiku-4-5-20251001-v1:0` (all 343 calls). TypeSafe `jev-1.13.0` (returned on all 343 calls) |
| Fingerprints | Routing dataset v2 `9d4f2da1393b3ddd42728740d5c8c08e9ccc0051edc7ae0746260cb456cc5e5d` · Jev payload template `54e2deaa70a529ca7eb70d5e896c6118e8a7993b228013ca3b9e53ec8f67c0c9` · rules `86cea35d458a75af6456803eec068b288dab748d0d001ef89a1f43ec8b352ab9` |
| Configuration | 34 questions (strict 24 `qa` / 7 `summarize`; policy L19; exploratory L17, L20). 10 repetitions; 3 warm-ups per paid router; seed 20260928, round-robin order. Threshold 0.6 → `qa`. Strict reservation ($0.322 per Haiku call; $0.002688 per Jev call). Ceilings: Bedrock $0.60, TypeSafe $0.05, total $1.00. Request caps 343 / 343 |
| Ceiling approval | The plan prints "Bedrock $0.60 proposed … pending final approval" because that is a static string in `config.py`. The ceiling was **approved** in the Phase A authorization of 2026-09-28, before the run |

## Execution

- **Completeness:** complete and valid. All 1,026 of 1,026 scheduled calls ran:
  - Haiku: 343 (3 warm-up + 340);
  - Jev: 343 (3 + 340);
  - rules: 340.
- **Failures:** no infrastructure errors, harness errors, decision mismatches or schema errors.
  No router was stopped.
- **Downstream isolation:** clean. No QA, summarization, retrieval or generation module was
  imported.
- **Ledger** (estimated from recorded usage at list prices; not a bill):

  | Provider | Requests | Committed | Worst-case charges | Reservations exceeded |
  |---|---|---|---|---|
  | Bedrock | 343 / 343 | **$0.165786** of $0.60 | 0 | 0 |
  | TypeSafe | 343 / 343 | **$0.005865** of $0.05 | 0 | 0 |
  | **Total** | | **$0.171651** of $1.00 | | |

- **Journal:** 1,715 lines: provenance, run_started, 686 call_started, 1,026 records and
  run_finished. Every paid record is preceded by its call_started entry. No record was redacted.

## Content checks (before archiving)

All three files were checked:
- no `.env` secret value (5 checked, values never printed);
- no AWS access-key pattern;
- no "bearer" text, and no authorization or header fields;
- no retrieved-chunk, context or document fields;
- no long token-like strings other than hex hashes;
- no question text.

The longest string in the artifact is 215 characters (a method or description string).

## Headline observations (details in the Phase A report)

| | Haiku 4.5 | Rules | Jev |
|---|---|---|---|
| Strict accuracy, majority (n = 31) | 30/31 (Wilson [83.8%, 99.4%]) | 31/31 ([89.0%, 100%]) | 31/31 ([89.0%, 100%]) |
| Strict accuracy, pooled (310) | 96.8% (cluster CI [90.3%, 100%]) | 100% | 100% |
| Raw-label accuracy, pooled | 96.8% | 100% | 100% |
| Fallbacks | 0 | 0 | 7 (2.1%), all on exploratory L20 (p < 0.6) |
| L19 policy compliance (`qa`) | 0/10 | 10/10 | 0/10 |
| Latency p50 / p95 (client-side) | 911.9 / 1669.7 ms | 0.01 / 0.02 ms | 123.6 / 183.7 ms |
| Estimated cost of 340 measured calls | $0.1644 | $0 | $0.0058 |

The rules router's result is in-sample: its author had seen these questions. Accuracy intervals
rest on 31 labeled questions; repetitions are not independent samples.
