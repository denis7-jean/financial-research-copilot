# Thin RAG smoke execution launcher — independent review handoff

Codex implementation and self-review only. Independent launcher acceptance is
pending. This increment authorizes no execution, signing-source access, data
disclosure, budget, resource operation, deployment or qualification.

## Exact scope and accepted inputs

Base: `584cc55544cd6fb8bda0f1c81cb995dff4174a09`.
Branch: `phase0/jev-rag-smoke-execution`.
Worktree: `C:\Projects\AWS Project\worktrees\jev-rag-smoke-execution`.
Exactly three additions: this handoff, `scripts/jev_rag_smoke_execution.py`, and
`tests/test_jev_rag_smoke_execution.py`. All base source blobs remain unchanged.
The final commit, committed-blob hashes and distinct raw working-copy hashes
are recorded in the private commit receipt, avoiding a self-referential binding.

The Tail report and execution proposal remain uncommitted in the Tail worktree,
with their original raw hashes:

- Tail acceptance: `3cff6b883c7540f46a1fe9985e602843433c288035a8e07656f0e32977e0349e`.
- Proposal: `2b52d11857b51fe1ccad038d3230d0ddc1a96e85d035d62e6c61c36525d5fcb5`.

No proposal choice is adopted. Application, handler, policy, P0, consumer,
adapter, factory, schemas, packaging, requirements and locks are unchanged.

## Callable contract

There is no CLI or automatic live action. A future separately authorized
dedicated interpreter supplies four immutable byte inputs (Tail operator plan,
P0 plan, canonical invocation payload, policy), the two price-evidence byte
inputs, six independently trusted expected hashes, an existing persistent root,
client settings, external operational authorization bytes and their separately
trusted expected hash, and explicitly supplied in-memory signing strings.
An optional session token is explicit; no provider is selected. No environment,
dotenv, profile, credential file, SSO, process, metadata or refresh loader is added.

`prepare(...)` imports accepted pure component definitions lazily, validates the
unchanged consumer joins and root, requires the Tail-v2 plan, validates the
authorization, and calls unchanged `factory.prepare`. It constructs no SDK
session/client and publishes nothing. It returns a one-use callable object with
safe repr `RagSmokeExecution(single_use=True)`. Input mappings are copied and
bytes retained; caller mapping changes cannot substitute prepared inputs.
Python private attributes are not a security boundary against an untrusted
in-process caller.

### External authorization encoding

`jev-rag-smoke-execution-authorization-v1`, maximum 16,384 raw bytes, uses the
existing strict JSON parser and canonical serializer. Duplicate keys,
nonfinite values, noncanonical bytes and extra fields reject. Exact fields:

| Field | Requirement |
| --- | --- |
| `schema` | Exact schema token above |
| `operational_authorized` | Boolean `true`, supplied externally |
| `dedicated_process_confirmed` | Boolean `true`, external prerequisite assertion |
| `execution_scope` | `ONE_SYNCHRONOUS_TAIL_INVOKE_NO_OTHER_SERVICE_CALLS` |
| `target` | Exact validated account/region/function_name/qualifier object |
| `inputs_sha256` | Exact six-entry trusted map: operator/plan/invocation/policy/haiku/titan |
| `client_settings` | Byte-exact canonical match to caller settings and P0 parent_invocation |
| `persistent_root` | Exact resolved absolute root string validated by P0 |

The supplied expected authorization SHA-256 must equal SHA-256 of the complete
raw canonical authorization bytes. It must come from the trusted caller,
not be inferred from the record itself. Hash agreement authenticates neither
permission nor authorship. This is a small per-run binding check, not an approval
registry, signing protocol or authorization manager. No approval record was
created in this task. Synthetic test assertions are invented, not owner approvals.

Target and all input joins bind the payload, plans, policy and prices. Client
settings use canonical-byte equality: `true`/`1` and `10.0`/`10` are not identical.
Malformed authorization, hashes, roots, settings or signing format rejects
before claim/client/send. Missing required arguments fail at the callable boundary.

The dedicated-process assertion is not an environmental audit. Before a real
call, its external supplier must establish the exact-run authorization, permitted
signing source, private persistent-root permissions, pinned SDK, TLS/logging and
process prerequisites. The accepted factory independently refuses TLS key logging
and non-pinned SDK construction at its lazy post-claim seam. Such a late refusal
retains the claim and cannot dispatch. Outside Git does not prove confidentiality.
The launcher does not spawn or sandbox the process, install tools, inspect IAM,
or certify those external assertions.

### Execution and actual-return receipt

`prepared.run(stdout=..., stderr=...)` consumes its local one-use state, then
passes exact prepared inputs/hashes/root and the accepted factory to unchanged
`consume_adapter`. The consumer publishes and closes the persistent claim and
attempt marker before calling the factory. Only one synchronous, exact full-ARN,
qualified Tail Invoke is permitted. P0 persistent claims remain the cross-process
duplicate gate. No discovery, STS, polling, health, CloudWatch, replacement,
retry, reservation release or cleanup path is added.

Only after a real consumer return, publish `returned-status.json` exclusively
inside the claimed private directory. Maximum 32,768 bytes; canonical fields:

- `schema = jev-rag-smoke-returned-status-v1`;
- `authorization_sha256`, the already verified external record binding;
- `consumer_return`, the actual unmodified returned object.

Write, flush, fsync and successful close precede read-back byte equality and
receipt hashing. It is a companion receipt, not an amendment to the consumer's
index/file allowlist. Its own returned hash binds its bytes. Partial files,
collisions and failed close remain retained; nothing is overwritten, retried or
deleted. Fixed receipt errors are `RETURNED_STATUS_INVALID`,
`RETURNED_STATUS_TOO_LARGE`, `RETURNED_STATUS_PUBLICATION_FAILED`, and
`RETURNED_STATUS_UNCONFIRMED`.

A returned consumer `COMPLETE` goes through `confirm(actual_return, directory)`
with the exact object. This verifies the returned index hash and every accepted
published file binding. Then unchanged `emit_confirmation` emits only sanitized
consumer codes/bindings. No answer, query, path, raw log or signing values enter
the public confirmation. Console exit 3 returns launcher `UNCONFIRMED` with
`CONSOLE_CONFIRMATION_UNAVAILABLE`; it cannot return confirmed completion.
Handled incomplete consumer returns are receipted and emitted with exit 2,
without being confirmed. Receipt/confirmation faults never emit a clean COMPLETE.

The callable returns `jev-rag-smoke-launcher-result-v1`, containing status/code,
the actual consumer return, returned-status hash, publication_confirmed,
console_exit_code and `release_authorized=false`. `COMPLETE` means confirmed local
publication and successful console output, not RAG success. A FunctionError can
have complete local evidence publication. REPORT association, model accounting,
semantic assessment and external authority remain distinct; evidence_complete,
experiment_success and task_cost_established are not promoted.

If the consumer raises, no returned-status receipt or inferred completion is
fabricated from disk. Original programming exceptions and originating traceback
frames propagate, with accepted consumer partial evidence retained. No secondary
launcher action runs while that primary defect escapes. Lone unexpected receipt
or console defects also propagate; expected I/O faults have fixed codes. No
global catch-all, recovery or resend framework is introduced. Caller exception
context does not determine the launcher's completion state.

## Validation and synthetic limits

Fresh private directory:
`C:\Projects\AWS Project\dependency-acquisition\rag-execution-launcher-20261009-671c490e`.
All test logs, guard receipts, XML, metadata and snapshots are exclusively created.
Reusable guard helpers were inspected as text, then copied to this private root;
the scoped Ruff helper points to this worktree. No inherited helper was rewritten.
Pure-Python invented NumPy/FAISS and recording SDK constructors are installed
before collection/application imports. The existing offline guard stays active.
The guard replaces 16 constructor/provider entry points, with no counter resets.
Two inherited serializer cases use disclosed recording replacements, never real
SDK clients. No native code or credentials are used.

Final results in each environment: **899 passed = 835 unchanged + 64 new**.

| Test file suffix | Count, both environments |
| --- | ---: |
| execution | 64 |
| live_adapter | 179 |
| adapter_consumer | 132 |
| client_factory | 69 |
| operator | 202 |
| preinvoke | 83 |
| accounting | 31 |
| handler | 53 |
| smoke (test_jev_rag_smoke.py) | 86 |

- Python 3.13.12, boto3/botocore 1.42.96, Ruff 0.15.16: pinned definitions.
- Python 3.11.15, boto3/botocore 1.43.14, Ruff 0.15.14: compatibility only.
- Both guard receipts: zero real constructions, zero provider invocations,
  zero outbound attempts. Two inert import-time client replacements and two
  inherited recording serializer replacements are explicitly disclosed.
- One inherited `asyncio_mode` warning because plugin autoload is disabled;
  the pinned interpreter also emits its inherited missing base-path notice.

Exact final integrated commands (each wrapper records its inner command):

```powershell
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-execution-launcher-20261009-671c490e\validate.py' test-integrated-313-final2
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-execution-launcher-20261009-671c490e\validate.py' test-integrated-311-final2
```

The inner guarded pytest invocation selects the nine files listed above, using
`-q -p no:cacheprovider --tb=short`, a fresh basetemp and fresh JUnit XML.
Scoped Ruff uses `check --no-cache` and `format --check` on only the new script
and test file, through the same private wrapper. Final whitespace checks are
`git diff --cached --check` and `git diff BASE HEAD --check`.

Coverage includes external authority absence/false/substitution, all six wrong
input hashes, strict encoding and settings types, invalid roots, no preclaim
construction/publication, exact Tail send, closed claim/marker before recording
construction, actual return identity and unchanged invented input files, secret
non-disclosure, FunctionError, parsing and partial read failures, original
programming defects and secondary cleanup/index failure, duplicate refusal,
receipt collision/write/partial-write/close/serialization/limit faults,
confirmation failure, console I/O/programming faults and caller-except contexts.
Claims, markers, input/response bytes and full parent reservations remain retained.

All intermediate failed checks are preserved. The first restricted-context run
could not resolve invented Windows scratch paths through the unchanged root
guard. Local unrestricted-process reruns passed without guard, ACL or claim-root
changes. Early fixture mistakes (FunctionError publication expectation, metadata
field spelling and import-spy setup order) were corrected to match the unchanged
contracts. Final integrated runs cover the final source/test bytes. The later
handoff addition requires no further application test run.

## Preservation and next review

Before/after metadata snapshots cover the 18 other recorded worktree states,
the factory and Tail worktrees separately, 16 fixed inputs, 10 protected artifacts,
the latest ZIP, 31,155 prior receipt files, eight proposal receipts and pointer,
supplemental research and sealed evidence. Previously inaccessible sealed files
remain explicitly `UNREADABLE_CURRENT_USER_NO_PERMISSION_CHANGE` and uncertified;
no permissions were changed.
The accepted ZIP and shipped application bytes were not rebuilt or refreshed.
No main merge, other-worktree edit, source amendment, actual approval, SDK client,
credential/.env access, network/AWS call, install, container, native execution,
artifact build, resource action, upload, deployment or push occurred.

Claude's focused review should inspect the small external authority binding,
canonical settings joins, read-only preparation, claim-before-factory seam,
actual-return receipt/confirmation ordering, primary defect preservation,
publication fault behavior, false authority/experiment promotion and the guarded
64-case increment plus unchanged baseline. Independent launcher review must occur
before integration. Data disclosure, semantic procedure, approved prices/token
bounds/budgets, current account/resource observations, private retention,
dedicated process/signing source and final exact-run permission remain separate
owner/operational gates. Tail A1–A6 and O1–O4 remain unchanged; a tail does not prove
complete logs or absence of dropped records. No live readiness is claimed.
