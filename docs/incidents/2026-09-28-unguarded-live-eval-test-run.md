# Incident: unguarded pytest run of the live evaluation (2026-09-28)

**Status:** fixed locally (commits `ef00197`, `acf21df`, `a9f105c`), not pushed.
**Billing impact:** probably one partial billable evaluation run. **Unverified.** Check Bedrock
usage for about 03:28–03:33 UTC on 2026-09-28 (see "Second run").

## Summary

During a read-only context-recovery check, the assistant ran pytest twice without
`-m "not llm"`. Earlier phases had always filtered that marker. Both runs executed the live
evaluation fixture in `eval/test_llm_judge.py`, which called `run_evaluation()`.

1. **First run: whole suite (`pytest`).** The network guard in `tests/conftest.py` was loaded,
   because pytest also collected `tests/`. Every AWS request was blocked, so nothing was billed.
   The run wrote `eval/results/latest.json`: 34 of 34 cases failed, and there were zero model
   calls. It was still marked `valid_for_baseline: true`.
2. **Second run: `pytest eval/test_llm_judge.py::test_enforced_gate` only.** `tests/` was not
   collected, so the guard never loaded. `.env` supplied real credentials. The fixture started
   a live evaluation, and the assistant stopped it after more than 2 minutes. It wrote no
   results file.

## Root causes

1. **The guard was scoped to a directory.** The fake credentials and the blocked botocore
   transport lived in `tests/conftest.py`. Pytest loads a conftest only when it collects that
   directory, so selecting `eval/` alone bypassed the guard.
2. **Live tests were opt-out, not opt-in.** The `llm` marker only labelled the tests. Nothing
   stopped them from running unless the caller remembered `-m "not llm"`. The fixture and
   `run_evaluation()` had no authorization check of their own, and the eval test module loaded
   `.env` at import time.
3. **The validity check had a blind spot.** The guard's `NetworkBlockedError` is classified by
   the app as kind `internal`. The harness counted that as an application finding, not an
   infrastructure failure, and nothing required any case to succeed. A run that measured
   nothing therefore passed the validity gate.

## Diagnostics preserved from the first run

`eval/results/latest.json` has been left in place. It is gitignored, 127,563 bytes, SHA-256
`4d6783f5bebc3f2106dee9303d0446016f7d15555c812c84c5e5a7ca56aec63f`.

| Field | Value |
|---|---|
| Run ID | `c7aba364551f4b468235b38368610af4` |
| Window | 2026-09-28 03:27:16 → 03:28:23 UTC (34 cases × 2 s sleep) |
| Code | `264ee6b`, clean tree. Dataset SHA-256 `734f6e1c…`. Corpus fingerprint `null` (index never loaded) |
| Completion | 34/34 evaluated, `complete: true` |
| Model calls | System: none recorded. Judge: 0 calls. Estimated cost $0.00 |
| Fatal error, all 34 cases | stage `retrieval.index_load`, kind `internal`, code `NetworkBlockedError` |
| Non-fatal error, all 34 cases | router `NetworkBlockedError` → `fallback_invoke_error` |
| Blocked URLs | `bedrock-runtime…/model/us.anthropic.claude-haiku-4-5-20251001-v1%3A0/converse`, `unit-test-bucket.s3…/index/unit-test.faiss` |
| Validity as recorded | `valid_for_baseline: true`, all 34 cases filed under `application_errors` |
| Validity under the fix | **invalid**: no usable results (0/34), network blocked in 34 cases, 34 cases degraded |
| Enforced gates | Context relevance 0.0, faithfulness 0.0 (the two test failures observed) |

The fake bucket name `unit-test-bucket` shows that the guard's forced environment was in effect.
The archived Phase 0 baseline (`b24cb185…`, `4c403dda…`) was not touched. Under the new rules
it remains valid (34/34 usable).

## Second run (unguarded)

- **Command:** `pytest -q -p no:cacheprovider "eval/test_llm_judge.py::test_enforced_gate"`,
  started shortly after the first run finished. The assistant's tool timed out at 120 s and
  moved it to the background, and the assistant stopped it soon after.
- **Evidence:** none local. The harness writes results only at the end of a run, and
  `latest.json` kept the first run's timestamp.
- **Likely effect:** real Bedrock Converse calls (the Haiku system under test and the Sonnet
  judge), Titan embeddings and S3 reads of the FAISS index. It made no S3 writes. If
  `COPILOT_CW_REQUEST_LOG` was enabled in `.env`, it may also have written request-log entries
  to CloudWatch.
- **Estimated cost:** at most about $0.50. The full baseline cost about $1.11 over 5.7 minutes.
  The $5 cost ceiling was in force.
- **Unverified:** confirming this needs AWS access, which was not authorized. The account owner
  should check Bedrock usage or Cost Explorer.

## Fixes

| Commit | Change |
|---|---|
| `ef00197` | A root `conftest.py` installs the guard (`tests/offline_guard.py`) for every pytest invocation. Importing the `tests` package installs it too, so `--noconftest` is also covered. The guard disables `.env` loading, hides shared credential and config files, disables instance metadata, and removes profile, session, bearer-token and container credentials. Live tests are skipped unless `--run-live-eval` is given. A selection containing only live tests, without the option, is a usage error (exit 4). With the option, only live tests may be selected. The fixture re-checks the opt-in itself. CI passes `--run-live-eval`. |
| `acf21df` | `run_evaluation()` refuses to build real clients unless `live=True`. `python -m eval.llm_judge` refuses to start without `--live` (exit 2). |
| `a9f105c` | `run_validity` marks a run invalid in these cases: no case evaluated; no usable result; any call blocked by the network guard (new class, `network_blocked`); unexpected application errors above 20% of cases; or an unexpected harness exception. A harness exception now stops the run, keeps the rows already evaluated and writes them. Sporadic application errors and model-output failures remain quality findings. |

Verification was done entirely offline. The full suite ran through an outer wrapper that
supplied dummy credentials, disabled `.env` loading and routed traffic through an unreachable
proxy, so a defect in the new guard still could not have reached AWS.

## Safe testing commands

```bash
# Offline, the default. No AWS access is possible; live tests are skipped.
pytest
pytest tests/ -m "not llm and not integration" -v    # what the CI unit-tests job runs

# Selecting only live tests without authorization is refused (exit 4):
pytest eval/test_llm_judge.py

# LIVE, billable. Run only with explicit approval, and after the preflight:
python -m eval.preflight
python -m eval.llm_judge --live
pytest eval/test_llm_judge.py -m llm --run-live-eval -v
```

## Remaining risks

- **Live runs still need to be authorized by a person.** The opt-in stops accidents, not a
  deliberate `--live` or `--run-live-eval`.
- **The guard is inside pytest.** A Python script run outside pytest that imports the app and
  calls AWS directly is not covered. `python -m eval.llm_judge` and `run_evaluation()` are
  covered by their own opt-ins. `scripts/smoke_check.py` and `app/services/*` `__main__`
  blocks remain live by design.
- **The guard patches botocore's transport.** An SDK other than botocore (for example a future
  `httpx`-based Jev client) is not blocked by it. Any such client needs its own guard before
  Jev work starts.
- **CI secrets:** the `integration-tests` job (the smoke check) is live and has no opt-in beyond
  running on pushes and pull requests to `main`. That is unchanged.
