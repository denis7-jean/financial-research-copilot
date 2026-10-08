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

## OP-1 correction — focused offline delta

Correction base: `1ad9db2f01f348cd61e8c4ab557eda15d7597172`, same operator
branch/worktree. The preceding implementation/validation receipt is historical;
this increment does not overwrite it. Claude's REQUEST CHANGES report is preserved
uncommitted and unchanged at raw SHA-256
`6aa44c71f3e1ba092f1ecf4e7d1923ebbafd2c7a74acbe4a37c148358881ad7e`.
Codex correction/self-review remains pending Claude's focused OP-1 delta review.

Production code changes are confined to `inspect_handler` and new
`consumer_accounting`. AST comparison verifies all other module nodes are
unchanged. No accepted producer, operator dispatch/publication/confirmation,
P0, packaging or declarative-contract code is altered.

Checks are derived from the actual accepted
`SmokePolicy.accounting`, `record_extra_request`, `_returned_usage` and the
handler's exception/footer branches:

- unestablished_stages is a list of distinct strings from router/index/metadata/
  embedding/generation/unidentified_model_request. Wrong types/vocabulary return
  HANDLER_RESULT_INVALID; duplicates and inconsistent well-typed fields return
  HANDLER_RESULT_CONTRADICTORY.
- exposure_bound_established equals not unestablished_stages. Coverage has the
  producer precedence VIOLATED first, otherwise UNESTABLISHED when stages exist,
  otherwise WITHIN_RECORDED_RESERVATIONS. Positive known unreserved charges,
  attempt charges exceeding their reservation, and hash-bound usage journals
  reporting a token overrun require VIOLATED. Known token overruns can violate
  coverage even when the charge is below the reservation.
- A true ceiling requires an established bound and non-VIOLATED coverage. There
  is deliberately no inverse rule forcing a true ceiling: the actual producer
  also compares exposure to its caps, which are not arguments to this consumer.
  This is necessary consistency validation, not independent recomputation or
  authentication of prices, caps, every charge, or a whole-task budget pass.
- Attempts must have typed reservation/hold/settled fields. A settled attempt has
  zero hold; an unsettled one retains its reservation. Status uses the handler's
  exact unsettled nonzero-reservation test, plus unestablished stages and its
  three uncertain-failure codes. Ordinary SmokeStop statuses match that branch.
  Close/evidence failures, local execution errors and compact-output footer
  behavior retain their separate accepted rules. UNCERTAIN does not imply that
  the numeric bound is unestablished; STOPPED with a known settled overrun is valid.
- Never-delivered extras must have usage and charge_usd explicitly null, including
  rejection of a fabricated zero charge. Delivered/unknown extras still map to
  the contract violation regardless of a zero charge or local coverage. Unknown
  delivery or absent pricing/charge must retain the corresponding stage marker.
- Count and lowercase full list hash are required even when the list is omitted.
  Zero count binds canonical empty-list bytes. Present null is not omission.
  The actual handler's compact form has UNCERTAIN/RESULT_TOO_LARGE, no local_events
  and no extra_requests list; full answer-size rejection remains STOPPED. Missing
  compact list bytes stay INCOMPLETE, not established within or reconstructed.

All checks precede a returned mapping. Contradictions leave the index mapping
UNESTABLISHED and evidence_complete=false, with fixed sanitized
HANDLER_RESULT_CONTRADICTORY. Existing response.bin bytes/hash, request metadata,
P0 claim, full parent reservations and attempt marker remain intact. A second
entry is refused without a second factory/send or changing any prior file.
Local publication COMPLETE remains separate from evidence completeness and RAG
success; genuine failure evidence can still be complete. No reservation is
released and valid usage never becomes authorization.

### Reproduction and final validation

Fresh raw committed-base export reproduces both original defects: STOPPED with
router unestablished, bound=false, ceiling=true, WITHIN coverage; and a real
blocked extra transformed to delivery=NO with charge="5". **2 defect-presence
tests pass**, independently confirming both base results incorrectly publish
within/complete. No changing worktree code is used for that reproduction.

Corrected parent tests retain exact transformed raw bytes and assert rejection,
UNESTABLISHED mapping, incomplete evidence, one parent call, duplicate refusal
and byte-identical prior holds/files. Variations cover missing/malformed/duplicate/
unsupported stages, conflicting flags/status, blocked usage/zero charge, compact
missing/invalid hash/count and omission-versus-null/full-list contradictions.

Positive cases execute the actual accepted handler/accounting seams with invented
inputs/faults: structural success, ordinary stop, uncertain retained reservation,
router/index/metadata retry inconsistencies, token and charge overruns, identified
delivered/unknown/missing/unpriced/zero-charge extras, blocked send, unidentified
extra evidence, client close, local evidence, full answer-size rejection and
compact output. The compact tests lower the test-only result limit (as existing
handler regressions do); this exercises the stricter actual footer, not a
weakened producer. The older minimal transformed-extra fixture is replaced by
actual policy observation; its mapping/charge/success assertions are retained.

Final focused result: **395 passed**, no skips, one inherited asyncio_mode
warning. Operator 142, P0 83, accounting 31, handler 53, smoke 86. Interpreter
Python **3.11.15**, Ruff **0.15.14**, existing legal-agent environment. Inspected
pure-Python fake native modules and transports only. Offline guard active and
zero outbound attempts in tests and scoped Ruff. No packaging/lock regression
was run or encountered; its historical CRLF issue remains unchanged above.

```powershell
$env:HANDLER_TEST_ROOT = 'C:\Projects\AWS Project\worktrees\jev-rag-smoke-operator'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-operator-op1-20261008-29c6fd83\run_offline.py' -q -p no:cacheprovider --tb=short --basetemp='C:\Projects\AWS Project\dependency-acquisition\rag-operator-op1-20261008-29c6fd83\pytest-focused-final' tests/test_jev_rag_smoke_operator.py tests/test_jev_rag_smoke_preinvoke.py tests/test_jev_rag_smoke_accounting.py tests/test_jev_rag_smoke_handler.py tests/test_jev_rag_smoke.py
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-operator-op1-20261008-29c6fd83\run_ruff.py' check --no-cache scripts/jev_rag_smoke_operator.py tests/test_jev_rag_smoke_operator.py
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-operator-op1-20261008-29c6fd83\run_ruff.py' format --check scripts/jev_rag_smoke_operator.py tests/test_jev_rag_smoke_operator.py
git diff --check
```

Ruff cache and all new test outputs are outside Git. Lint, formatting and
whitespace pass. Staged raw blobs are joined to the validated working-copy
source/test hashes before the explicit three-path local commit. Final parent,
blob versus working-copy hashes and preservation bindings are in exclusive
private receipts under
`C:\Projects\AWS Project\dependency-acquisition\rag-operator-op1-20261008-29c6fd83`.
Twelve other worktrees, protected inputs/ZIP/sealed bindings and the exact
uncommitted OP-1 report are compared before/after. No permissions change or
protected line-ending normalization occurs. Claude's inaccessible preservation
scope remains the previously disclosed limitation, not new independent verification.

### Nonblocking limitations and review handoff

O1–O4 stay visible and unchanged:

1. Real SDK exception translation and partial-byte preservation belong to a
   separately reviewed future operational adapter; the simulated protocol is
   not expanded here.
2. Supplied REPORT memory values still accept finite nonnegative floats. Actual
   AWS capture/type/provenance remains an operational requirement.
3. confirm relies on the caller preserving the actual returned value; it cannot
   authenticate a reconstructed or forged return from index bytes.
4. Dispatch count includes an entered invoke whose parameter hook blocked before
   sending. It is conservative, not a delivered-call count.

Claude should review exactly this consumer/helper, status/footer exceptions,
compact/extra invariants and fresh counterexamples/producer positives. Do not
promote passing tests into independently accepted correction, authenticated
observations, full accounting/contract enforcement or execution readiness.
All prior operator/live-observer, owner/data/budget, credential/permissions,
artifact/native, confirmed execution evidence, semantic and qualification gates
remain. No live path, capture/recovery framework, source integration, AWS/network
call, credentials/.env, native execution, installation, container, build, paid
call, resource change, deployment, push or Reviewer Protocol v2 change occurred.
Stop for Claude's focused OP-1 delta review.

## OP-1b / OP-1c / R3 offline correction — 2026-10-08

Correction base: `20d34bcfdf25bcd872a5b640794591a9d7eed275`, on the existing
`phase0/jev-rag-smoke-operator` branch. Before editing, the three base Git blobs
and both uncommitted Claude reports were verified at their supplied SHA-256
bindings. Both reports remain untouched and excluded from staging.

Only `consumer_accounting` changes in production; its AST comparison proves
every other operator function/class unchanged. Every prior test/helper AST is
also preserved, including both original OP-1 counterexamples. The accepted
producer, handler, P0, contract/fixtures, packaging and application behavior are
unchanged.

### Necessary consumer joins

- **OP-1b:** the unchanged producer settles only via `_returned_usage` with
  attributable returned usage. A settled model attempt now requires a valid
  nonnegative finite charge, the producer's two-field usage representation
  (`inputTokens` and `outputTokens`, exact nonnegative integers), and
  `AUTHORIZED_REQUEST` attribution. Embedding output remains zero. Missing or
  contradictory settlement evidence cannot release a hold. Valid zero usage
  and zero charge remain accepted; valid settled token overruns remain recorded.
- **OP-1c:** an unsettled charged attempt, including zero charge, or an attempt
  marked `UNATTRIBUTED_RESPONSE` must retain its stage in `unestablished_stages`.
  Genuine retry-inconsistency output remains consumable as failure evidence:
  returned usage/charge survive, the full hold remains, and the bound is not
  established. Retry metadata does not establish delivery counts or usage scope
  for any other request.
- **R3:** independently group attempt holds as the accepted producer does:
  router/generation to Haiku, embedding to Titan, excluding index/metadata from
  model totals. Sum with the existing exact `money_total` helper and require
  exact Decimal equality to each reported retained-hold total. No rounding,
  clamping, reservation release or price/charge recomputation occurs. Expected
  arithmetic failures reject with sanitized `HANDLER_RESULT_INVALID`; unrelated
  programming errors still propagate.

Well-typed contradictory evidence returns fixed `HANDLER_RESULT_CONTRADICTORY`.
Invalid charge representations retain `HANDLER_RESULT_INVALID`. These checks
establish necessary internal consistency only, not authenticated usage,
authorization, full accounting verification or execution readiness.

### Reproduction and validation

Fresh raw committed-base source export and invented real-handler seams reproduce
all three gaps: settlement after a generation timeout without usage/charge;
removing the retry charge's stage and claiming an established WITHIN bound; and
reporting zero Haiku holds alongside a three-unit retained attempt. **3
defect-presence probes pass** on the unchanged committed base. The initial
sandbox runs instead stopped at the filesystem claim gate: `Path.resolve`
denied access to pytest-created directories. Guarded tests then ran outside the
process sandbox; no protected permission changes or validator bypass occurred.

Corrected full-operator tests assert direct `inspect_handler` rejection, exact
response.bin bytes and hash retention, claim and attempt marker preservation,
incomplete evidence, UNESTABLISHED mapping, confirmation refusal, duplicate
refusal, one parent call, and unchanged full parent reservations. Variations
exercise missing/invalid usage, charge and attribution, wrong provider/hold
totals, and stage removal. Positive cases preserve the original actual-producer
coverage: settled success/overrun, uncertain numerically bounded holds, retries,
blocked sends, priced/zero-charge/unknown/unpriced extras and compact results.
Additional actual journal-write failures preserve settled or held accounting
without later downstream calls. A separately labelled invented consumer fixture
checks sums beyond default Decimal precision and S3/model grouping; it is not
represented as a producer-emitted price policy.

Final focused validation: **423 passed**, no skips, one inherited unknown
`asyncio_mode` warning. Operator 170; P0 83; accounting 31; handler 53; smoke 86.
Python **3.11.15**, Ruff **0.15.14**. The guard remains active with **zero outbound
attempts**. Only invented transports and inspected pure-Python native substitutes
are used. Scoped Ruff lint/format and whitespace pass. No packaging test or
canonical lock check was rerun; the earlier checkout lock/CRLF limitation remains
unchanged. Git's LF-to-CRLF notices are not whitespace failures.

```powershell
$op1bcPython = 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe'
$op1bcScratch = 'C:\Projects\AWS Project\dependency-acquisition\rag-operator-op1bc-r3-20261008-6bd981ac'
& $op1bcPython -B "$op1bcScratch\validate.py" working -v3
# This executes run_offline.py -q -p no:cacheprovider --tb=short, with a fresh
# --basetemp and JUnit receipt, against exactly these five suites:
# tests/test_jev_rag_smoke_operator.py tests/test_jev_rag_smoke_preinvoke.py
# tests/test_jev_rag_smoke_accounting.py tests/test_jev_rag_smoke_handler.py
# tests/test_jev_rag_smoke.py
# It also executes guarded Ruff check --no-cache and format --check on exactly
# scripts/jev_rag_smoke_operator.py and tests/test_jev_rag_smoke_operator.py,
# then git diff --check. Exact commands/results/hashes are in its JSON receipt.
& $op1bcPython -B "$op1bcScratch\checks.py" export
& $op1bcPython -B "$op1bcScratch\validate.py" raw
```

Raw staged source/test blobs are matched to validated working-copy hashes. The
same focused suites run on the fresh raw Git export, without normalizing any
protected checkout files. Private receipts distinguish committed blobs from
working-copy hashes; exports are source validation inputs, not build artifacts.
Final commit, ordered parent, exact three-path delta and receipt bindings are
recorded in the exclusive task completion receipt outside Git.

### Preservation and next review

Twelve other worktree HEAD/branch/status and readable changed-file bindings,
twelve fixed inputs, ten protected artifacts (including the accepted ZIP), both
review hashes and all 194 untouched operator Git blobs are compared. Against
the earlier sealed preservation inventory, **133 of 1217 files are readable and
match**; **1084 prior pytest files are inaccessible** under the current Windows
user. Their contents are not newly certified. No ACL changes or access workaround
occur. New task outputs stay in the private scratch directory above.

Claude's focused delta review should inspect the settlement evidence check,
unattributed-stage join, exact provider hold sums and the full-parent regressions
at the new commit, separately from the two earlier accepted/rejected subjects.
O1–O4 remain as documented above. Real transport/SDK exception mapping, trusted
operator and log evidence, owner data/prices/token bounds/limits, credentials and
private permissions, pre-Invoke sufficiency, new exact artifact/native validation,
confirmed parent completion, semantic assessment and qualification remain gated.

No AWS/network calls, credential or .env access, native execution, installs,
containers, builds, paid calls, integration, deployment, push or Reviewer
Protocol v2 changes occurred. Stop for Claude's OP-1b/OP-1c/R3 delta review.

## R3-a offline correction — 2026-10-08

Base: `2d9a385ea31a803a0dd1d2f6779bc505e8f1671e`, existing operator branch.
The exact HEAD, three committed-blob hashes and all three uncommitted Claude
reports were verified before editing. The latest REQUEST CHANGES report binds
to this base and raw SHA-256
`7592e0aade30f2bbb39d42bc4afdeb34c17cebd3202152f0adbe0914fe049c9f`.
All reviews remain unchanged and excluded from staging.

### Numeric domain and bounded-cost proof

Only `decimal_value` changes in production. Accepted producer `money_total`,
policy, handler and P0 remain untouched. The consumer now admits only:

- a string of at most **512 characters**, as before;
- a finite nonnegative Decimal with at most **512 coefficient digits**;
- a tuple exponent **at least -512** and adjusted magnitude **at most 511**.

Checks use `as_tuple`, `adjusted`, `is_finite` and `is_zero`, without fixed-point
expansion, context normalization or rounding. For every nonzero operand,
`adjusted = exponent + coefficient_length - 1`; its exponent therefore lies in
**[-512, 511]**. A zero's adjusted value equals its exponent: an extreme-exponent
zero fails the same checks. An admitted zero returns exact `Decimal(0)` so its
irrelevant quantum cannot amplify the subsequent sum. Source strings and raw
response bytes remain unchanged, including signed or fractional zero evidence.

The bounds follow the existing 512-character representation budget: it already
permits 512-digit ordinary integer coefficients, whose maximum adjusted value
is 511. The fractional span allows scientific values down to `1E-512`; it is far
larger than the accepted producer's price scale (at most 12 fractional digits,
then division by a million). It preserves `1E-12`, long exact sums and admitted
unclamped charges, including the 90-digit-token producer regression. An arbitrary
small positive amount below that quantum or magnitude at/above `1E+512` is now
intentionally outside the consumer domain, even when scientific text is short.
Bounds apply to the supplied coefficient/quantum: an equivalent trailing-zero
representation outside them also rejects; it is not normalized to bypass them.

Each provider's hold sum has at most three operands (two Haiku stages plus the
initial zero; Titan has one stage plus zero). The unchanged `money_total` recipe
therefore requests at most
`max(80, 511 - (-512) + len(str(3)) + 3) = 1027` precision digits. Each operand
has at most 512 coefficient digits. Parsing/metadata and exact addition are thus
bounded independently of short scientific exponent text. The worst permitted
span is tested with a 1024-digit exact result; an unrepresentable/rounded reported
total cannot pass the existing representation budget and equality join. No
MemoryError catch, global catch-all, rounding, clamping or reservation release
is added. Unsafe money retains fixed `HANDLER_RESULT_INVALID`.

### Regression and validation evidence

Five fresh instrumented probes on raw committed-base bytes show that
`1E-999999999`, `1E-999999999999`, excessive positive magnitude and zeros with
positive/negative extreme exponents reach the former sum boundary. The instrument
records tuple metadata and immediately raises a private signal: it never calls
the real sum or widens precision. **5 base defect-presence probes pass**. No
large-allocation or gigabyte experiment is performed.

The corrected tests instrument the boundary only after the unchanged producer
emits its response. Unsafe holds, reservations, charges and aggregate monetary
fields reject before any sum. Full-operator cases preserve byte-exact response
and hash, claim/attempt marker and full parent reservations; keep accounting null,
mapping UNESTABLISHED and evidence incomplete; refuse confirmation and repeat
entry; and perform one simulated parent send. Boundary and just-outside cases,
equivalent supported notation, safe zero metadata, 70/90/512-digit exact sums and
unclamped actual producer charges are covered. Every original operator test and
helper AST is preserved, including OP-1, OP-1b, OP-1c and R3 counterexamples and
real-producer positives. The only changed production-function AST is
`decimal_value`.

Final focused validation: **454 passed**, no skips, one inherited unknown
`asyncio_mode` warning. Operator 201; P0 83; accounting 31; handler 53; smoke 86.
Python **3.11.15**, Ruff **0.15.14**, offline guard active with **zero outbound
attempts**. Fake transports and inspected pure-Python native substitutes only.
Scoped lint/format and whitespace pass. Guarded tests run outside the process
sandbox because of its previously demonstrated denial of pytest-directory
`Path.resolve`; no protected permissions or validators are changed.

Private scratch/receipts:
`C:\Projects\AWS Project\dependency-acquisition\rag-operator-r3a-20261008-27c594bd`.
Exact commands, log hashes, JUnit, Python version, raw source exports and
committed-blob versus working-copy bindings are retained there.

```powershell
$r3aPython = 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe'
$r3aScratch = 'C:\Projects\AWS Project\dependency-acquisition\rag-operator-r3a-20261008-27c594bd'
& $r3aPython -B "$r3aScratch\validate.py" working
# Guarded run_offline.py -q -p no:cacheprovider --tb=short, fresh --basetemp/JUnit:
# tests/test_jev_rag_smoke_operator.py tests/test_jev_rag_smoke_preinvoke.py
# tests/test_jev_rag_smoke_accounting.py tests/test_jev_rag_smoke_handler.py
# tests/test_jev_rag_smoke.py
# Then guarded Ruff check --no-cache and format --check on only the two changed
# Python files, plus git diff --check.
& $r3aPython -B "$r3aScratch\prepare.py" export
& $r3aPython -B "$r3aScratch\validate.py" raw
```

The raw staged export runs the same focused suites. Staged blobs are joined to
validated source/test hashes before the explicit three-path local commit.
Protected checkout bytes and line-ending policy are not normalized; the prior
lock/CRLF limitation remains unchanged and its packaging suite is not rerun.

### Preservation and focused handoff

Compare twelve other worktrees' HEAD/branch/status and readable changed bytes,
all 194 untouched operator Git blobs, three report hashes, ten protected artifacts
including the accepted ZIP, and twelve fixed inputs. The sealed inventory remains
133 readable matching files and 1084 inaccessible prior pytest files, out of 1217;
the latter are not newly content-certified and no permissions are changed.
All task outputs are exclusive new private records; historical receipts remain
unchanged.

Claude should independently review this exact numeric domain, zero handling,
1027-digit cost proof, safe base instrumentation and full-parent rejection
evidence. O1–O4 and all previously documented operator, trusted-observation,
owner/data/price/budget, credential/permissions, artifact/native, confirmed parent,
semantic and qualification gates remain unresolved. This is necessary offline
consistency, not full cost verification or execution authorization.

No AWS/network calls, actual credentials/.env reads, native execution, installs,
containers, builds, paid calls, integration, deployment, push or Reviewer
Protocol v2 changes. Stop for Claude's focused R3-a delta review.
