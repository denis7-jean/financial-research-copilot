# N2 offline accounting correction

Codex implementation/self-review; pending Claude independent N2 review. This
increment does not authorize a smoke execution, integration, artifact build or
deployment and does not establish complete acceptance-contract enforcement.

## Exact base and protected scopes

Branch `phase0/jev-rag-smoke-accounting`, new isolated worktree from
`e513c8ea4b1846cd085620459c86c65c8e3ad5a9`. The original handler report's raw
SHA-256 is `98d433791bd2b8167cd48bc7abd3099b69bf8aa10bdb22974473ed87f1ac95ac`;
the H1 ACCEPTED report is
`cc0fe7a72599d203799349ede6a4193d476f6785e888fc3bed8070b99b7accc6`.
Both were read, hash-verified and preserved uncommitted in the handler worktree.

Six paths: policy accounting, handler evidence output, two existing regression
files, a new focused accounting test file and this handoff. No change to
bedrock_client.py is necessary: its existing failure propagation preserves the
SmokeStop and policy evidence, demonstrated through the real generation seam.
H1, input envelope, policy configuration schema, prices/capacity input schema,
P0, accepted declarative contract/48 fixtures, packaging and ordinary behavior
remain unchanged. The existing handler handoff and all shared documents remain
historical records at their original bindings.

## Accounting behavior and limits

1. Validate returned usage separately from retry/send consistency. Built-in
   nonnegative integer input/output counts and an optional exact total are
   required; malformed or absent counts never produce a charge. Retain only
   those selected numeric fields, not arbitrary provider text.
2. Every returned usage record has scope `RETURNED_RESPONSE_ONLY`. With valid
   zero-retry metadata and one approved pre-send/parameter check, attribution is
   `AUTHORIZED_REQUEST` and its reservation settles to exact usage-estimated
   charge. Otherwise attribution is `UNATTRIBUTED_RESPONSE`: record the valid
   charge, retain the full authorized hold, stop, and mark exposure unestablished.
   Retry metadata alone supplies neither exact delivery counts nor extra-request
   usage, and never automatically creates an extra-request entry.
3. For an unattributed response, numeric `exposure_usd` adds its charge to the
   retained hold conservatively. The hold may overlap that charge. It is neither
   an exact invoice total nor an established upper bound when additional
   exposure is unknown. Summary fields distinguish known charges, holds, numeric
   accounting exposure and whether the model bound/ceiling is established.
4. A second before-send callback raises before transport delivery. It creates
   a separate `delivery=NO` observation, with no fabricated usage/charge or extra
   monetary exposure. Record callback, approved-before-send and blocked-before-
   send counts separately; a before-send approval is not a delivery receipt.
5. `record_extra_request(stage, *, delivery, request_evidence_sha256, model_id,
   region, tier, usage=None)` is a local observation seam, not a live producer.
   `stage` is router/embedding/generation; delivery is YES/UNKNOWN. The supplied
   digest must uniquely reference independently established evidence for that
   distinct request. Neither its syntax nor hashing authenticates the observation.
   Correct evidence acquisition/verification remains external; caller event
   fields cannot inject these observations or override the handler's test seams.
6. Each observed extra has its own generated request identity, evidence reference,
   delivery, normalized usage, pricing-binding status and charge. Only the pinned
   model, us-east-1 and standard tier can use this policy's price evidence. A
   different/unestablished pricing binding preserves valid counts with
   `VALID_UNPRICED`, no invented charge and an unestablished exposure bound.
   Missing/invalid usage or unknown delivery likewise preserves uncertainty.
7. Every extra stays `approved=false`, `reservation_usd=0`, `settled=false`.
   Known extra charges add separately; they never consume an authorized hold or
   another request's evidence. Positive unreserved charges flag coverage violated.
   Already observed extras can still be recorded after abort; all new dispatch
   remains forbidden. An extra with known zero charge still stops execution.
8. Reused/invalid extra evidence stops with a fixed code and unestablished scope;
   it cannot be recycled to justify a different request. Actual returned/extra
   overruns are recorded unclamped. Decimal products and aggregate additions
   preserve exact values even far beyond the approved bound. Unknown exposure
   is never assigned zero merely to fit a ceiling.

The reviewed parameter/send gates and standard `total_max_attempts=1` client
configuration remain in force. No extra request is permitted to measure its cost.
This is static/reviewed client instrumentation, not a universal network sandbox.
The default SDK does not manufacture independent extra-request provenance. When
only retry inconsistency is available, it reports that limitation and stops.
Arbitrary unapproved models/providers and infrastructure pricing are not added
to this seam; absent applicable pricing/delivery evidence remains unresolved.
S3/logs/parent costs still belong to the future operator's infrastructure allowance.

## Handler evidence contract

Invocation remains `rag-smoke-invocation-v1`, with the same trusted canonical
payload anchor, policy validation, import purity, client construction/closure,
route/output checks and false parent/publication/qualification/release flags.

Result is explicitly versioned `rag-smoke-handler-result-v2`: the previous v1
fields plus `accounting`. This avoids silently extending v1's exact field set.
`attempts` retains reservation/settled fields and adds retained hold, delivery,
selected returned usage/attribution, charge when valid, retry metadata when valid,
and pre-send check counts. Unestablished exposure makes status UNCERTAIN; a
known unauthorized extra still stops, regardless of its charge. No result
establishes confirmed parent completion or operational authorization.

`accounting.scope` is `LOCAL_MODEL_ACCOUNTING_NOT_TASK_TOTAL`. It carries exact
known-charge and retained-hold totals, exposure/ceiling flags, coverage status,
unestablished stages, extra count, and canonical extra-list SHA-256. The normal
result includes the extra list. On bounded-output rejection, compact output
retains totals/flags/count/hash and attempts; full extra observations remain in
exclusive local journals. No journal is repaired, overwritten or deleted.
Journal envelope remains `rag-smoke-event-v1`; new observation kinds are
`blocked-send` and `extra-request`, and usage records disclose scope/settlement.
Publication failures never promote local bytes into confirmed evidence.

## Regression evidence

Private scratch:
`C:\Projects\AWS Project\dependency-acquisition\rag-accounting-20261008-a421b96d`.
Committed-base probes independently reproduced valid usage disappearing on
RetryAttempts=1 and a missing distinction between two send callbacks versus one
actual invented transport send: 2 passed defect-detection probes.

The focused accounting/smoke/handler suites pass 170 cases, including 31 new
accounting cases. They cover retry/missing/malformed metadata, invalid usage,
blocked sends, multiple distinct delivered extras, uncertain/unpriced extras,
zero-cost unauthorized extras, evidence reuse, exact unclamped arithmetic,
embedding and generation failures, duplicate preservation, sanitization and
bounded handler evidence. The generation probe initially altered shared fake
metadata and stopped at routing; replacing that one fixture record correctly
reached generation. That fixture error is not a production defect.

S41 is reproduced through the actual application/policy seams using invented
transport observations: a 3-unit hold remains, a distinct known 1-unit extra
charge is recorded, exposure is 4, coverage is VIOLATED and ceiling_established
is false. No index/embedding/generation operation follows routing failures.
The fixture is read declaratively for its arithmetic; no acceptance engine is
claimed. Existing positive settlement, normal application behavior and H1 cold
loader tests remain in the regression set.

Validation details and final preservation/commit bindings are appended below.

## Final validation and preservation receipt

Actual interpreter: Python 3.11.15, existing legal-agent environment; Ruff 0.15.14.
The offline guard is active in every test/lint process, with zero outbound
attempts. NumPy/FAISS are inspected pure-Python invented substitutes, not executed
native libraries. Test-only loader spies/guard prohibit actual .env reads.

Final broad run from raw staged Git source bytes: **586 passed, 1 skipped**;
all validated Python blobs are verified identical to the final committed blobs.
The same run against the new worktree: **585 passed, 1 failed, 1 skipped**.
The sole failure is the pre-existing operational-lock CRLF-versus-canonical-byte
assertion. The lock is untouched: raw Git SHA-256
`01fe426a5e28b274c4cc1bdb3ef6423203564b43ded257149bec35b7879c5bb8`;
checkout SHA-256
`226aafe6c2aab570bebb7d495e214422206fdb7e97058875ac17b069d54d38ab`.
The skip is unavailable Windows symlink privilege. The disabled plugin autoload
causes the existing nonblocking asyncio_mode configuration warning.

Exact final test command (worktree run changes only ROOT/output directories):

```powershell
$env:HANDLER_TEST_ROOT = 'C:\Projects\AWS Project\dependency-acquisition\rag-accounting-20261008-a421b96d\staged-export'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-accounting-20261008-a421b96d\run_offline.py' tests/test_jev_rag_smoke_accounting.py tests/test_jev_rag_smoke_handler.py tests/test_jev_rag_smoke.py tests/test_jev_rag_smoke_preinvoke.py tests/test_agents.py tests/test_router.py tests/test_api.py tests/test_observability.py tests/test_jev_candidate.py tests/test_lambda_package.py -q -ra -p no:cacheprovider --basetemp 'C:\Projects\AWS Project\dependency-acquisition\rag-accounting-20261008-a421b96d\pytest-staged-export-final' --junitxml 'C:\Projects\AWS Project\dependency-acquisition\rag-accounting-20261008-a421b96d\staged-export-final.xml'
```

Scoped guarded Ruff check/format --check on the five changed Python files passes;
Git staged and final whitespace checks pass. No unrelated file is reformatted.
No real packaging, artifact execution, historical reconciliation or paid smoke
was run. The earlier focused failure was an invented shared-metadata fixture
error and is fixed; the final runs have no unexplained failures.

Before/after metadata receipts cover eleven existing worktrees, both handler
reports, protected fixed inputs, the accepted ZIP and 1,217 sealed bindings.
No inaccessible file is silently promoted into verified content and no
permissions are changed. The handler worktree retains its two untracked reports;
its accepted source is unchanged. Reviewer v2 sources and records are untouched.
The completion receipt records exact parent/final commit, six-path delta, raw
committed-blob versus working-copy hashes, validated export/test hashes and
preservation. Receipts are private exclusive files outside Git. The two changed
runtime source blobs require a future newly bound artifact; the accepted ZIP and
historical hashes are preserved, not rewritten to match this increment.

## Independent review and remaining gates

Claude should review the six-path delta: usage-before-mismatch handling,
attribution and conservative overlap, blocked versus delivered observations,
per-extra evidence uniqueness/model-price joins, unclamped arithmetic, abort
latching, partial publication and compact result evidence. This is an N2
implementation claim pending independent acceptance, not full live readiness.

Remaining gates: integrated reviewed operator/P0 claim and zero-retry parent
Invoke; owner-approved data/query/object/source bindings, prices, token bounds,
budgets and infrastructure allowance; authentic per-request observation/usage
evidence where extras are detected; actual credential/endpoint/IAM boundaries;
new exact artifact and native/startup validation; confirmed parent response,
REPORT and hash-bound publication; semantic assessment and later qualification.
N1/N3-N5 and source-hit feasibility remain as previously documented. No operator,
live observer, distributed deduplication or semantic classifier is implemented.
No Reviewer v2 evidence or readiness status is changed.
