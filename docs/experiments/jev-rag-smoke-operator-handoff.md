# Offline RAG parent-operator seam — Codex implementation handoff

Base: `474f54c1b918aefd82690c37b1ea6d6f2a28d2a5`.
Branch: `phase0/jev-rag-smoke-operator`.
Worktree: `C:\Projects\AWS Project\worktrees\jev-rag-smoke-operator`.
Only three additions: `scripts/jev_rag_smoke_operator.py`,
`tests/test_jev_rag_smoke_operator.py`, and this handoff.
Codex implementation and self-review; **pending Claude independent review**.
No integration, real transport, live CLI, SDK session, credentials or execution
authorization. No accepted application/P0/accounting/packaging/contract bytes change.

Claude's N2 report was verified against raw SHA-256
`bed36c99329183f86a71f91f3f7f89b456c75c616a8b7e538a0a0d7740d81250`.
Its verdict explicitly accepts this exact base within offline N2 scope. The
report remains uncommitted in its accounting worktree. The inherited N2 handoff
is historical; its pending-review language is not rewritten. Claude verified
133 readable protected files, not the inaccessible remainder. Codex's separate
preservation checks do not expand Claude's verification or authenticate history.

## Input and API contract

`validate` is a local pure validation seam except existing-root metadata checks.
`simulate` takes an injected, explicitly simulated factory. `confirm` verifies
the returned publication and exact index/file bytes. `emit_confirmation` emits
only fixed-code metadata; it is not a live CLI. The module has no `main` and
imports no SDK, transport, dotenv or native package.

All JSON produced here uses the accepted `canonical`: sorted keys, compact
separators, ASCII escapes, no non-finite numbers, UTF-8 and exactly one terminal
LF. SHA-256 preimages are the entire raw bytes, including LF. Strict parsing
rejects duplicate keys and non-finite numbers. An invocation may arrive as normal
AWS-style JSON response bytes; received bytes are retained unchanged, not
canonicalized to manufacture provider fidelity.

The operator plan is canonical `jev-rag-smoke-operator-plan-v1`, with exactly:

| Field | Type/requirements |
|---|---|
| schema | Exact schema token |
| mode | `SIMULATED_OFFLINE` only |
| p0_plan_sha256 | Exact raw P0 plan hash |
| invocation_sha256 | Exact canonical invocation hash |
| target | Exact account/region/function_name/qualifier object |
| target.account | Explicit 12-digit string, no inferred account |
| target.region | `us-east-1` |
| target.function_name | Explicit plain Lambda name, 1–64 alphanumeric/underscore/hyphen characters |
| target.qualifier | `$LATEST` or positive decimal version string (up to 20 digits); aliases/ARN resolution unsupported |

Separate caller `hashes` must have exactly operator/plan/invocation/policy/haiku/
titan, all lowercase 64-hex SHA-256. These are byte anchors, not approval or
capture authentication. Actual accepted P0 validation checks the plan, policy,
price evidence, worst-case ROUTE/EMBED/GENERATE plus infrastructure allowance,
and limits. Actual handler `validate` checks the canonical event, trusted payload
binding, query/policy/evidence and local-root requirements before side effects.
The operator additionally requires byte-identical event policy/evidence to P0
inputs and P0 references.event_sha256 equal to the exact invocation hash.
Run identity is joined through those unchanged validators. Other P0 reference
hashes are retained as references: the operator does not invent their artifacts,
verify approvals, or treat historical health/baseline observations as smoke
artifact readiness. P0's eight external gates remain present and unresolved.

## Claims and one simulated dispatch

After all input joins, `publish_claim` creates P0's stable run-based exclusive
claim under the same existing outside-Git persistent root. Changes to a plan
hash do not authorize a repeat of that run. No directory/file is retried,
overwritten, deleted or repaired. Partial or even empty claims continue blocking
entry. Claim-read/publication failures return fixed errors before any factory.

Input copies and request.json are published exclusively. Valid pre-call host
clocks precede invocation-attempt.json, which retains full P0 reservations and
states OUTCOME_UNKNOWN. That marker is closed successfully **before factory
construction and before dispatch**. At most one call to injected client.invoke
is made. A clock/publication/configuration failure before it produces no Invoke.
Unknown outcomes never trigger replacement or release previous holds.

Exact simulated request: Invoke, explicit FunctionName/Qualifier,
InvocationType=RequestResponse, LogType=None, Payload=exact invocation bytes.
Client account is a simulated declaration, not STS evidence. Reviewed checks
require official regional Lambda endpoint, supplied P0 connect/read values,
standard total_max_attempts=1, and registered parameter/send hooks. The hooks
check operation/whole parameter object, POST URL, payload bytes and invocation/
log headers. Second parameter/send callbacks stop; blocked callbacks are not
reported as established deliveries. Response retry metadata must be integer zero.
Retries alone cannot supply exact send counts or extra usage. Hooks are static
reviewed checks on the injected protocol, not a sandbox or a universal transport
guarantee. A future live adapter must establish its actual endpoint, credential,
retry and observer behavior under its own review and authorization.

## Response, accounting and logs

Payload is consumed incrementally, up to the accepted handler's 131,072-byte
limit. Overflow stops reading; the prefix is preserved with body_complete=false.
Read/close failure keeps representable partial bytes. The bound is on bytes the
operator consumes/preserves, not transport-internal allocation or a total
wall-clock deadline. The body is closed on all handled read paths, and client
close is attempted once. response.bin is published before metadata serialization,
post-read clocks or handler interpretation. Selected request/response metadata
has separate raw hash bindings. No discarded AWS headers are reconstructed.

The consumer explicitly admits `rag-smoke-handler-result-v2`, validates envelope,
run/policy joins, false authority flags, private result shape, accounting values,
local event hashes and supplied extra-observation list hash/count. It does not
re-execute the acceptance fixtures or claim complete contract enforcement. The
accepted handler remains the runtime enforcement seam.

Index assessment keeps parent transport, handler structure, model accounting,
contract-exposure mapping, evidence completeness, semantic assessment and whole
task cost separate. STRUCTURAL_SUCCESS is a handler result, not qualification.
FunctionError and STOPPED/UNCERTAIN can produce captured failure evidence; HTTP
200 does not make the experiment successful. experiment_success is always false,
semantic_assessment is UNASSESSED, task_cost_established is false. Compact extra
evidence has INCOMPLETE mapping; omitted observations are not reconstructed.

N2 distinctions preserved:

- Known charges and retained holds remain separate raw bound fields; unreserved
  charges are never erased or retroactively authorized.
- Extra counts include blocked delivery=NO entries. Those have no invented
  delivered charge. Coverage WITHIN_RECORDED_RESERVATIONS does not mean authorization.
- Unapproved delivery=YES or UNKNOWN maps to
  VIOLATED_RECORD_UNRESERVED_EXPOSURE even when N2's local label is UNESTABLISHED,
  or a known zero charge leaves numeric coverage WITHIN. This is contract
  violation mapping, not invented delivery counts or a newly priced exposure.
- Unattributed usage plus holds can conservatively overlap; these are exposure
  records, not invoices. P0 parent reservations are retained in full here; there
  is no task-total settlement/release implementation.
- Extra evidence hashes are not authenticated observations. The missing live
  observer stays an execution prerequisite.

Only caller-supplied log projection bytes are consumed; no log client exists.
Separate logs_sha256 binds those bytes. Schema `jev-rag-smoke-supplied-logs-v1`
has exactly schema/request_id/report. REPORT has request_id/duration_ms/
billed_duration_ms/memory_size_mib/max_memory_used_mib; init_duration_ms is
optional. Numeric values must be finite/nonnegative. Both request IDs must equal
the Invoke response ID. This is an explicitly unauthenticated selected-field
projection, not a claimed AWS log capture. Future capture must establish the
actual invocation-to-function-REPORT identity and provenance, not assume it.
Warm reuse, CPU dispatch and absence of errors remain UNESTABLISHED. Missing
REPORT leaves evidence_complete=false; the module does not infer absent init or
warm reuse. Host times are unauthenticated. response_received denotes the
post-body-preservation/metadata-publication sample, not server receipt or Lambda
duration. Bad clocks leave null invalid timing and preserved response bytes.

## Publication and confirmation

Files are exclusive binary writes, checked for short write/flush/fsync/close.
The index schema is `jev-rag-smoke-operator-index-v1`. File bindings contain raw
sha256/size_bytes; unsuccessful files are excluded and disclosed by relative
filename, fixed stage/code and may_be_incomplete. Maximum serialized record size
is 1 MiB. No filesystem permissions are changed; outside Git is not proof of
confidentiality, persistence or retention.

COMPLETE means **successful local publication**, not evidence success or readiness.
It can coexist with evidence_complete=false (e.g. missing supplied REPORT).
INTERRUPTED can still have a successfully published hash-bound partial index.
Index publication failure gives INTERRUPTED_UNINDEXED, null index_sha256,
index_failure_code and all returned failure disclosures; even readable COMPLETE
bytes after failed close cannot confirm publication. An unrelated programming
error propagates after client-close attempt; the persistent claim still blocks
reuse. Expected failures are caught locally, not by a catch-all.

Confirmation requires the actually returned COMPLETE plus matching index bytes
and every successful file binding. `emit_confirmation` gives 0 for a confirmed
COMPLETE return, 2 for interrupted return, and 3 when console serialization/write/
flush is unavailable, with fixed CONSOLE_CONFIRMATION_UNAVAILABLE fallback. A
future process consumer must not turn exit 3 or unconfirmed index bytes into a
completion result. Returned/printed metadata has no query/answer/provider text,
environment values or private paths. Raw responses and invocation stay private.

## Validation and self-review

Python **3.11.15**, existing legal-agent interpreter; Ruff **0.15.14**.
Final guarded run: **352 passed**, no skips, one inherited asyncio_mode warning
because plugin autoload is disabled. Suites: operator 99, P0 83, accounting 31,
handler 53, smoke 86. Pure-Python invented NumPy/FAISS substitutes only; offline
guard active and **zero outbound attempts**. No SDK live clients or real .env
reads. No broad suite, packaging execution, historical replay or paid smoke.

Fresh tests cover real accepted P0/handler chain, exact claim-before-factory/
dispatch order, input/self-declared hash and event joins, exact operation/URL/
payload/headers, one send and blocked second send, zero retries, unknown outcome
duplicate refusal including changed plan hashes, valid structural success and
confirmed failure evidence, stopped handler with zero later sends, malformed v2
outputs, bounded/read/close failures, missing/mismatched REPORT, partial/collision/
permission/close publication failures, combined record/index failures, serializer/
console failures, huge/nonfinite/backwards clocks, representable response
preservation, fixed diagnostics and propagated unrelated programming errors.
The N2 3-unit hold + 1-unit unreserved charge counterexample runs through actual
handler/accounting seams and remains 4 units against one 3-unit reservation.
Independent invented executions with fixed clocks produce identical index hashes.

Initial development run used pytest's inaccessible default temp area (setup
errors); subsequent runs use fresh task-owned scratch basetemps without permission
changes. Two initial fixture/consumer issues (existing harmless QA metadata log
and valid hyphenated journal filename) were corrected. Final runs have no
unexplained failures. Tests do not rely on real native code or bypass the guard.

Exact final commands:

```powershell
$env:HANDLER_TEST_ROOT = 'C:\Projects\AWS Project\worktrees\jev-rag-smoke-operator'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-operator-20261008-53f7c8a1\run_offline.py' -q -p no:cacheprovider --tb=short --basetemp='C:\Projects\AWS Project\dependency-acquisition\rag-operator-20261008-53f7c8a1\pytest-final-v5' tests/test_jev_rag_smoke_operator.py tests/test_jev_rag_smoke_preinvoke.py tests/test_jev_rag_smoke_accounting.py tests/test_jev_rag_smoke_handler.py tests/test_jev_rag_smoke.py
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-operator-20261008-53f7c8a1\run_ruff.py' check --no-cache scripts/jev_rag_smoke_operator.py tests/test_jev_rag_smoke_operator.py
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-operator-20261008-53f7c8a1\run_ruff.py' format --check scripts/jev_rag_smoke_operator.py tests/test_jev_rag_smoke_operator.py
git diff --check
```

Scoped lint and formatting pass. Staged/final whitespace and committed-byte joins
are recorded in the private completion receipt. The operational lock is unchanged:
raw Git `01fe426a5e28b274c4cc1bdb3ef6423203564b43ded257149bec35b7879c5bb8`,
checkout `226aafe6c2aab570bebb7d495e214422206fdb7e97058875ac17b069d54d38ab`.
Its previously reproduced packaging/CRLF failure is not encountered by these
focused suites and is not concealed or rerun. No protected file normalization.

## Preservation, next review and gates

Private receipt directory:
`C:\Projects\AWS Project\dependency-acquisition\rag-operator-20261008-53f7c8a1`.
Raw committed-blob and working-copy bindings are recorded separately, with test
commands/log hashes/interpreter and the exact direct parent/final commit. New
source/test bytes are matched to validated bytes. Preservation compares twelve
prior worktrees' actual HEAD/status/readable changed files, reports, fixed inputs,
the accepted ZIP and 1,217 sealed readable bindings. It never reads credential
files or changes permissions. Inaccessible scope is not promoted into verified
content. Previous receipts are not overwritten and this worktree adds no report
from another branch. Main remains untouched.

Claude's focused review: exactly the three additions, P0/event/reference joins,
claim/marker ordering and stable duplicate denial, bounded response fidelity,
v2 consumer and N2 contract mapping, report-ID/provenance limits, layered outcomes,
partial/index/console publication failures, clocks and sanitization. Review tests
as invented evidence, not actual Lambda observations or qualification.

Remaining gates: independent acceptance and separately authorized integration;
owner data/query/object/source permissions and expected answer; authoritative
prices/token bounds/limits/whole-task infrastructure reservation; persistent
private root/retention/single-operator requirements; reviewed operational parent
adapter with actual zero-retry invocation and credential/endpoint/IAM boundaries;
actual inner-client/extra observer enforcement and trustworthy per-request usage;
new exact artifact with native/link/startup validation; exact isolated target and
configuration review; real response/log provenance and confirmed publication;
semantic assessment and later qualification. N1/N3–N5 and source-hit feasibility
remain visible in inherited controls/handler handoffs. No owner values, resources,
credentials, retention policy, semantic outcome or operational authorization are
chosen by this increment. No Reviewer Protocol v2 bytes or readiness change.

Stop for Claude's independent operator review. No live CLI, network/AWS calls,
credentials, native execution, installs, containers, builds, inference, resource
changes, integration, deployment or push occurred.
