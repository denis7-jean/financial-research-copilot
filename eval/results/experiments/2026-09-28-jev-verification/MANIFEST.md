# Jev API verification: record manifest

The first real TypeSafe Jev requests, approved on 2026-09-28: two calls, L01 and L12. **Do not
edit the result files.** The hashes below make any change detectable, and `.gitattributes`
stores the files byte-for-byte.

| Item | Value |
|---|---|
| Artifact | `jev-verification-20260928T204426Z.json`, 6,038 bytes, SHA-256 `646f7735e9c16f4e833e6049e7757d7c8c3e8a4d75de4a6a036a6f4faf3940eb` |
| Journal | `jev-verification-20260928T204426Z.json.journal.jsonl`, 2,978 bytes, SHA-256 `812d30ba25ead7ffd67e9413eb1ddc92749761c180fc7495485cee7ff7aab287` |
| Run | 2026-09-28 20:44 UTC. Command: `python -m experiments.router_bench verify-jev --live typesafe` |
| Code | `c0c2f42`, clean tree |
| Authorization | Live for TypeSafe only. No Bedrock or AWS calls. Only `TYPESAFE_API_KEY` was read from `.env` |
| Data sent | The question text of L01 and L12, plus the frozen instruction and criteria. Payload template SHA-256 `54e2deaa…`; routing dataset v2 `9d4f2da1…` |
| Limits | 2 requests, $0.01 cap, `jev-1.13.0` pinned, no retries, stop on first failure |
| Outcome | 2/2 calls, complete and valid. Ledger: 2 requests, $0.000034 committed, nothing charged at worst case |
| Journal | 7 lines: provenance, run_started, call_started L01, record L01, call_started L12, record L12, run_finished. No record redacted |

## Observations

| | L01 (clear `qa`) | L12 (clear `summarize`) |
|---|---|---|
| Returned model | `jev-1.13.0` | `jev-1.13.0` |
| Choice | `qa` | `summarize` |
| Probabilities | qa 1.0, summarize 0.0 | qa 0.0, summarize 1.0 |
| Confidence | 1.0 | 1.0 |
| Input / output tokens | 410 / 33 | 408 / 35 |
| Estimated cost (input only, $0.042 per 1M) | $0.00001722 | $0.00001714 |
| Client-side latency | 187.5 ms (includes connection setup) | 133.6 ms |

- **Response fields:** `model`, `answers`, `usage`. `answers.route` has `choice`,
  `probabilities`, `confidence` and an undocumented `type` (only the name is recorded).
- **Response headers:** only `date` matched the allowlist. No `x-request-id`/`request-id` or
  `x-ratelimit-*` headers were returned under those names.

## Secret and content checks (2026-09-28, before archiving)

Both files were checked:
- no `.env` secret value (5 checked, values never printed);
- no AWS access-key pattern;
- no "bearer" or authorization field;
- no private key, and no long token-like strings other than hex hashes;
- no question text;
- both parse as JSON (the journal line by line).

The files were moved here from `eval/results/experiments/` with their bytes unchanged; the
SHA-256 values above were checked before and after the move.
