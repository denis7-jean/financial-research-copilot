# Offline RAG smoke P0 preflight and execution claim

Codex implementation and self-review; independent Claude review pending. This
increment contains no invocation, credential loading, observation, resource
preparation, handler, completion producer or recovery manager. No actual smoke
plan, price, budget, data permission or execution has been approved here.

## Accepted base and scope

- Branch: `phase0/jev-rag-smoke-preinvoke`.
- Direct implementation base: `33b05d9cc6281c308d39523b9b6d24048c384b0a`.
- The integration Claude report was read and its ACCEPTED verdict verified at
  that exact base. Raw report SHA-256:
  `7165e17288c0de74707d454e8ad9a07d0898b9926044d28e1148c13eb7298b31`.
- Only three new files: this handoff,
  `scripts/jev_rag_smoke_preinvoke.py` and
  `tests/test_jev_rag_smoke_preinvoke.py`.
- Accepted application/policy code, declarative contract and its 48 scenarios
  remain unchanged. The scenarios are not an executable acceptance engine.

## API and strict input contract

`validate(plan_raw, policy_raw, *, evidence, expected_hashes)` is pure.
`publish_claim(..., root=...)` repeats all validation before exclusive creation.
Both consume supplied bytes; no prices, token bounds, budgets or sizing defaults
are selected. Raw inputs are nonempty and at most 1,048,576 bytes each.

`expected_hashes` is a separate caller input with exactly `plan`, `policy`,
`haiku`, `titan`, each a lowercase 64-hex SHA-256. `evidence` contains exactly
`haiku` and `titan` raw records. All four hashes must match before parsing.
Putting matching hashes in a plan alone is insufficient. Supplying a fabricated
but internally matching record still cannot establish authority.

Plan schema `jev-rag-smoke-preinvoke-plan-v1` permits exactly:

| Field | Type / validation |
| --- | --- |
| `schema` | Exact schema string |
| `plan_id`, `run_id` | ASCII `[A-Za-z0-9_-]{1,80}`; run joins the policy |
| `policy_sha256` | Equals separately supplied policy hash |
| `price_evidence_sha256` | Exact `haiku`, `titan` map; equals separate anchors |
| `references` | Exact eight-field hash map below |
| `owner_limits` | Exact five-field object below |
| `parent_invocation` | Exact `max_attempts`, `connect_seconds`, `read_seconds` |

References, all required lowercase 64-hex strings:
`artifact_sha256`, `artifact_manifest_sha256`, `artifact_review_sha256`,
`configuration_sha256`, `configuration_review_sha256`,
`owner_decisions_sha256`, `infrastructure_basis_sha256`, `event_sha256`.
These are explicit bindings, not verification of the referenced contents or
their authenticity. Their actual joins/reviews/approval remain external gates.

Owner limits contain `ceilings_usd` (exact `haiku`, `titan`, `total` map),
`infrastructure_allowance_usd`, `memory_mib`, `timeout_seconds`,
`ephemeral_storage_mib`. Money is a decimal string: up to nine integer digits,
up to twelve fractional digits, no exponent, sign, leading zero or nonfinite
value. Ceilings must be positive and equal the accepted policy's ceilings;
infrastructure must be nonnegative. Sizing values must be builtin integers
in 1..1,000,000. Those are structural parser bounds, not certification of AWS
service limits, actual configuration, or an adequate infrastructure allowance.

Parent attempts must be builtin integer `1`. Connect/read seconds must be
builtin integers in 1..120. These declarations neither configure a client nor
prove an actual client's retry behavior. There is no client here.

The unchanged `rag-smoke-policy-v2` constructor validates its complete schema,
object identity/hash/size conditions, metadata/source counts, output caps,
models, attempts, price/capacity records and evidence hash joins. This component
uses only its pure constructor, never activation or client hooks. It additionally
rejects `expected_source.minimum_hits` greater than the bound source row count
before any claim. It does not inspect an actual index, source or response.

## Deterministic bytes and accounting

Plan and policy bytes must equal the accepted canonical encoding: UTF-8 JSON,
sorted keys, compact separators, `ensure_ascii=True`, `allow_nan=False`, one
terminal LF. Strict parsing rejects duplicate keys, nonfinite numbers, invalid
JSON/Unicode and parser recursion failures. Price records retain their exact raw
hashes and the accepted policy's parsing rules; they need not be canonical.

SHA-256 always hashes raw bytes. The result and claim use the same canonical
encoder. `references_sha256` hashes the canonical references object. Decimal
products and sums use precision 80, exceeding the accepted bounded operands;
division is by exactly 1,000,000. Monetary output uses fixed decimal strings and
does not round down to a currency unit.

For each stage, `(input_bound * input_rate + output_cap * output_rate) / 1000000`:

- ROUTE: Haiku input bound plus router output cap.
- EMBED: Titan input bound, output zero under its accepted record contract.
- GENERATE: Haiku input bound again plus generation output cap.
- Haiku ceiling covers ROUTE + GENERATE; Titan covers EMBED.
- Whole-run total covers all three stages plus the explicit infrastructure
  allowance; it must fit the total ceiling before creation.

The result separately reports ROUTE, EMBED, GENERATE, Haiku, Titan, models,
infrastructure and whole-run initial reservations. An invented exact-fit example
is ROUTE=3, EMBED=1, GENERATE=5, models=9, infrastructure=0.1, whole_run=9.1.
A total ceiling of 9 fails even though the model subtotal fits. These are
synthetic units; they are not approved prices or a real run budget.

Validation status is `BUDGET_SUFFICIENT_EXTERNAL_GATES_UNRESOLVED`.
`owner_authorized`, `artifact_ready`, `invoke_authorized` are always false.
Unknown fields, including a caller's `owner_authorized=true`, reject.
The result reports unresolved price/token authority, owner decisions,
infrastructure basis, exact artifact/configuration/review, root security and
retention, actual parent/inner enforcement, native/handler validation and
per-delivered-request accounting/confirmed operator evidence. Matching hash
references prove neither current prices, approval nor historical execution.

## Persistent claim boundary

The caller supplies an existing absolute root outside Git with no symlink or
reparse ancestors. No directory permissions are changed. Security, persistence,
retention and exclusive single-operator ownership are external prerequisites.

Execution ID is lowercase SHA-256 of
`b"jev-rag-smoke-execution-id-v1\0" + run_id.encode("ascii")`.
The run identity deliberately stays stable across changed plan labels/bytes;
the claim separately binds the exact plan and policy hashes. Changing a plan's
hash cannot evade an existing same-run claim. The ID is not a signature or a
distributed deduplication identity.

After validation, the claim payload is serialized before mutation. The component
exclusively creates `root/<execution_id>/`, then `claim.json` with `xb`, checks
the full write, flushes and fsyncs the file. Payload schema is
`jev-rag-smoke-execution-claim-v1`, state
`FULL_RESERVATIONS_RETAINED_NO_DISPATCH`, with the complete preflight result.
Success returns `CLAIM_PUBLISHED_NO_DISPATCH_AUTHORIZATION` and the exact claim
hash. This records initial holds; no settlement, release or dispatch occurs.

An existing directory or file rejects with `EXECUTION_ALREADY_CLAIMED` without
reading, modifying, releasing, deleting or retrying prior claims/attempts/holds.
An empty or partial directory still blocks re-entry. Publication IO failures
return `CLAIM_PUBLICATION_FAILED_RETAINED`; caught KeyboardInterrupt returns
`CLAIM_INTERRUPTED_RETAINED`. An abrupt exit or unrelated programming error
propagates, leaves the exclusive marker, and provides no resend permission.
No recovery or automatic cleanup exists. Root/run substitution or loss is an
operational violation, not a supported retry mechanism.

File fsync is not a portable proof of directory-entry durability after power
loss. Tests cover controlled IO failure and interruption, not power-loss,
hostile concurrent filesystem changes or distributed Lambda cold starts.
Any ambiguity denies dispatch, regardless of whether a file parses.

## CLI and confirmation

Run from the worktree using the existing Python 3.11 interpreter:

```text
python -B -m scripts.jev_rag_smoke_preinvoke validate --plan <invented-plan> --policy <invented-policy> --haiku-evidence <record> --titan-evidence <record> --expected-hashes <separate-anchors>
python -B -m scripts.jev_rag_smoke_preinvoke claim --plan <invented-plan> --policy <invented-policy> --haiku-evidence <record> --titan-evidence <record> --expected-hashes <separate-anchors> --persistent-root <existing-invented-root>
```

No live flag exists. Validate mode refuses a root option and writes only its
sanitized result to stdout. Expected input/publication errors use fixed codes
and exit 2. Console serialization/write/flush/closed-stream failure uses
`CONSOLE_CONFIRMATION_UNAVAILABLE`, exit 3; the claim stays retained and must
not be re-entered. Partial stdout or a parseable file is not returned success.
These are publication statuses, not evidence of a parent Invoke. There is no
global exception catch that conceals unrelated programming defects.

## Validation and preservation

Actual interpreter: Python 3.11.15; existing Ruff 0.15.14. Private scratch:
`C:\Projects\AWS Project\dependency-acquisition\rag-preinvoke-20261007-0e35f2a9`.
The copied, inspected guarded runner installs invented pure-Python NumPy/FAISS
fixtures before application imports; no native modules execute. SDK and
subprocess tripwires apply to the component paths. The existing offline guard
reported zero outbound attempts, none sent.

Exact final focused command (PowerShell environment selector is process-local):

```powershell
$env:PREINVOKE_TEST_ROOT = 'C:\Projects\AWS Project\worktrees\jev-rag-smoke-preinvoke'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-preinvoke-20261007-0e35f2a9\run_offline.py' tests/test_jev_rag_smoke_preinvoke.py tests/test_jev_rag_smoke.py -q -ra --basetemp 'C:\Projects\AWS Project\dependency-acquisition\rag-preinvoke-20261007-0e35f2a9\pytest-final-closed-streams' --junitxml 'C:\Projects\AWS Project\dependency-acquisition\rag-preinvoke-20261007-0e35f2a9\final-closed-stream-results.xml' -p no:cacheprovider
```

Result: **169 passed** (83 new, 86 accepted smoke/policy regressions), 1.70 s.
One known `asyncio_mode` warning reflects disabled plugin autoload; selected
tests contain no asynchronous tests. Initial 162-pass/3-failure results are
retained: those failures were test tripwires changing the guard's hook identity
and an overly broad AST restriction on an existing lazy exception-type import.
Only new tests were corrected; accepted guard/application code was unchanged.

The suite covers exact arithmetic/ceilings/infrastructure, malformed/stale
inputs, impossible source counts, duplicate preservation including uncertain
holds, permission/partial/short/flush/fsync/interruption errors, abrupt exit,
serializer failures, root links/Git rejection, console failures, read-only
validation and no client/network/subprocess use. It does not execute a parent
Invoke or an acceptance engine.

Scoped guarded Ruff commands use `run_ruff.py` in the same private scratch:

```text
python -B run_ruff.py check --no-cache scripts/jev_rag_smoke_preinvoke.py tests/test_jev_rag_smoke_preinvoke.py
python -B run_ruff.py format --check --no-cache scripts/jev_rag_smoke_preinvoke.py tests/test_jev_rag_smoke_preinvoke.py
git diff --cached --check
```

Before/after metadata receipts cover nine prior worktrees' HEAD/status and
readable changed-file bytes, fixed locks/requirements/allocation, accepted ZIP,
sealed startup/baseline evidence and adapter outputs. Reviewer v2 tracked
bindings are preserved through unchanged prior HEAD/status and this three-file
add-only delta; private Reviewer v2 evidence was not opened or inventoried anew.
Inaccessible review-folder scope stays disclosed by the inherited inventory;
no permissions were changed to read it. No protected files were normalized.
Raw working-copy and staged/committed-blob hashes are recorded separately in
private receipts. Only the three authorized new paths are staged and committed.

## Focused independent review and remaining gates

Claude should review the complete three-file delta: strict inputs/trust joins,
independent stage accounting including infrastructure, expected-source
feasibility, stable run identity/plan binding, exclusive and ambiguous claim
semantics, serialization/console failures, dependency purity and exact tests.
Acceptance of this engineering increment would not approve actual inputs,
prices/budgets or execution, and integration remains separate.

N1's missing whole-run calculation now has an isolated P0 implementation;
using it before an actual parent Invoke is still future operator work. O1's
impossible source minimum rejects upfront. N2 (extra sends/retry mismatch and
known usage), N3 (generic metadata Unicode handling), N4 (hash-bound confirmed
completion producer) and N5 (distributed/runtime claim limits) remain visible
and unchanged. This single-operator persistent claim does not solve distributed
deduplication. No acceptance clause is silently amended.

Next prerequisites remain owner-approved authoritative prices/token bounds,
data/expected-source/limits/infrastructure decisions, exact artifact/configuration
review, suitable retained claim root, persistent parent execution integration
with zero-retry invocation, explicit smoke handler and actual inner-client
checks, new native-validated artifact, confirmed hash-bound operator evidence,
semantic assessment and later qualification. No live operation, artifact build,
integration, merge into main, deployment or Reviewer v2 change occurred.
