# Adapter-backed parent consumer — offline implementation handoff

Codex implementation and self-review, pending Claude's independent review. This
increment authorizes no invocation, account access, artifact build or release.

## Subject and isolation

Exact direct base: `d2097e90f7157f9c25b2c8bf29f15342863f555e`.
Branch: `phase0/jev-rag-smoke-adapter-consumer`.
Worktree: `C:\Projects\AWS Project\worktrees\jev-rag-smoke-adapter-consumer`.
The commit receipt records the final child commit and all four final Git blobs.

Verified base ancestry includes runtime integration
`db9aa768eb9cb4c00cc6c72f6c0ce28580e5b90b`; base's direct parent is
`86395acf79c9a1937bad69e69a861d1dadb2175b`. Both uncommitted adapter reviews
remain in their original worktree with exact raw hashes:

- Original: `ae76bf27e223d528b6c207521ec714ff355af61b4942a1df313692b6a9f9b45f`.
- Cumulative AD-1 acceptance: `ed363edd165cc3f67e2fe0cc2eb88c80c940b5868ad8b615ac7a1500d24f2e10`, binding to the exact base.

Accepted adapter source/test/handoff blobs remain respectively:
`733212fdf28ab7b46d7e87c52e0d7a6e41a96a48e2e18875770ddb21881df62f`,
`c25c76725e83ed8880efb7b676e288e9eec9291f8ee73b6f962e6cb9926b5dd6`,
`d88ee441dbe018a1a61f0a81c6ac4a1cb0b921048ae314d9b302957f9f999107`.

## Four-path delta

- `scripts/jev_rag_smoke_operator.py`: distinct validation and injected adapter
  consumption; bounded evidence publication and conservative failure handling.
- `tests/test_jev_rag_smoke_operator.py`: one added legacy-plan separation test;
  inherited assertions remain intact.
- `tests/test_jev_rag_smoke_adapter_consumer.py`: 60 fresh synthetic cases using
  real accepted P0, adapter and handler/inspector seams, with invented clients.
- This handoff only. No shared handoff/work-log edits, review imports or merges.

## Explicit plan and entry contract

`validate_adapter` / `consume_adapter` require canonical LF-terminated compact,
sorted ASCII JSON with the existing strict parser, size caps, separately supplied
hashes and joins. Exact operator-plan fields remain `schema`, `mode`,
`p0_plan_sha256`, `invocation_sha256`, `target`. This path requires:

```json
{"schema":"jev-rag-smoke-adapter-operator-plan-v1","mode":"ADAPTER_BACKED"}
```

`target` remains the strict account/region/function_name/qualifier contract.
P0 policy/prices/budgets, persistent root, execution identity and event joins are
unchanged. `validate` / `simulate` remain schema
`jev-rag-smoke-operator-plan-v1`, mode `SIMULATED_OFFLINE`, and continue rejecting
non-simulation clients. Neither mode accepts the other's plan. Shared validation
was extracted into `_validate`; every other inherited function/class AST,
including `simulate`, `inspect_handler`, bounded monetary parsing, confirmation
and console handling, is unchanged.

`consume_adapter` requires a caller-supplied zero-argument `client_factory`.
There is no default SDK factory, Session, credential/environment loader, live CLI,
discovery, polling, fallback, replacement or retry. Only invented factories were
used here. A future real factory and exact-run authorization remain separate.

The durable P0 claim is published first; canonical inputs and full-ARN request
are preserved; the exclusive attempt marker is written, flushed, fsynced and
closed before either factory or `ParentTransport` construction. Any publication
failure prevents subsequent dispatch; the execution claim remains and prevents
resend. The adapter owns invocation/read/closure. A client rejected during adapter
construction is closed by the consumer, with targeted primary-defect precedence.

The request uses the exact account-bound full function ARN, separate qualifier,
RequestResponse, LogType None and canonical payload. The unchanged adapter checks
the regional HTTPS endpoint, bounded P0 timeouts, one total SDK attempt and exact
parameter/send hooks. Dispatch entries, approved callbacks and blocked callbacks
are distinct; none authenticates delivery or bills additional requests.

## Evidence and failure semantics

Before response interpretation the consumer attempts exclusive publication of:

- `response.bin`: exact received prefix, bounded by the unchanged 131,072-byte
  adapter limit; not a claim that an incomplete body is a complete response.
- `response-metadata.json`: the adapter's bounded selected SDK-field projection.
- `transport-result.json`: accepted summary plus `hook_failed`; primary code,
  all fixed failures, counters, prefix/hash, EOF, body/client close state, metadata
  hash/state/provenance and explicit unauthenticated/REPORT limitations.

Missing/null distinctions retained by the adapter remain intact. Error messages,
raw headers, LogResult and other discarded AWS fields are not reconstructed.
Every failed publication remains disclosed and excluded from successful file
bindings. No file is retried, overwritten, deleted or repaired.

Clean consumption requires RETURNED **and** no failures, failed hook state or
blocked sends, exactly one dispatch/parameter/approved callback, complete EOF,
and successful body/client close. AD1-O1 is handled by retaining all failures
rather than primary-code precedence. AD1-O2 is handled by checking hook state
and counters even when a foreign layer swallowed a gate error. Only this complete
clean state reaches the unchanged `inspect_handler`. FunctionError is retained
as FUNCTION_ERROR without parsing it as a successful RAG result.

Unknown, invalid and programming-defect paths retain every original parent
reservation. Even clean structural results do not settle parent/infrastructure
holds here. The accepted inspector's v2 contradiction checks, exact monetary
parsing and unauthorized-extra mapping are reused unchanged. Known unreserved
charges remain distinct from authorization and retained holds.

Unexpected programming errors propagate the original exception and traceback.
Targeted finalization publishes available bounded transport evidence and an
INTERRUPTED index where possible. Narrow resource/evidence/index boundaries
suppress only secondary defects when a primary defect is already escaping;
ordinary unexpected errors are not converted into SDK outcomes. Such a path has
no successfully returned completion confirmation, even if an index was written.
Failed index publication returns INTERRUPTED_UNINDEXED, no index confirmation.
There is no recovery/re-entry path.

Index schema: `jev-rag-smoke-adapter-operator-index-v1`, mode ADAPTER_BACKED.
`COMPLETE` means local evidence publication without fixed failures; it can include
an honestly verified STOPPED/UNCERTAIN handler result or FunctionError. It is
separate from successful RAG, authenticated completeness and authorization.
Confirmation still requires the actually returned COMPLETE status, matching
index bytes and every successful file's exact size/hash. Interrupted publication
cannot confirm. Console confirmation failure retains the existing exit-3 rule.

REPORT evidence is always `INCOMPLETE_NOT_CAPTURED` on this path;
`evidence_complete`, `experiment_success`, `task_cost_established` and
`authenticated_observation` remain false. SDK RequestId is explicitly not a
Lambda execution/REPORT ID. No supplied simulation logs are accepted or used.
Host clocks are unauthenticated: started_utc is sampled before marker/factory;
received_utc is the post-transport, post-evidence-publication sample, not an exact
response-arrival timestamp. Client elapsed includes factory, cleanup and evidence
publication. Invalid timing is not fabricated.

## Validation

Final working-copy source bytes, tested before the documentation-only addition:

| Environment | SDK definitions | Result |
|---|---|---|
| Python 3.11.15 Anaconda, MSC v.1942 AMD64 | boto3/botocore 1.43.14 compatibility | **620 passed**, no skips |
| Python 3.13.12 Anaconda, MSC v.1942 AMD64 | boto3/botocore 1.42.96 pinned definitions | **620 passed**, no skips |

Per run: consumer 60; adapter 105; operator 202; P0 83; accounting 31; handler 53;
smoke 86. Existing guard active throughout, **zero outbound attempts**, invented
NumPy/FAISS only. No real SDK client/session, credential provider or native module
was constructed. One inherited unknown `asyncio_mode` warning per run remains.
Python 3.13 launcher also emits its inherited miniconda-location warning; exit and
actual interpreter/version checks succeeded. No guard/root assertion weakened;
synthetic P0 tests ran with normal Windows filesystem resolution, without ACL
changes, because the previously documented process-sandbox Path.resolve limit
would reject invented roots.

New tests cover validation before claim/factory, closed claim/marker before
construction, exact full-ARN hooks, real handler accounting/compact/unauthorized
extra cases, all-failure retention, FunctionError, installed SDK exceptions,
malformed metadata, partial/oversized bodies, cleanup, both AD-1 defects and
tracebacks, swallowed gates, each required clean-state field, duplicates,
publication collisions/partial-close failures, index confirmation refusal,
secondary publication defects, constructor/factory rejection, clocks and a
sanitized post-publication claim-stat failure with zero factory calls and resend
refusal. This last filesystem check was found during final Codex self-review;
it uses the existing CLAIM_READ_FAILED_RETAINED code without changing P0.

Commands (exact expanded argv/cwd/interpreter/log hashes in each private receipt):

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-adapter-consumer-20261009-764f3d92\validate.py' test-integrated-311-final-v2
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-adapter-consumer-20261009-764f3d92\validate.py' test-integrated-313-final-v2
# Each invokes run_offline.py with the seven files, -q -p no:cacheprovider,
# --tb=short and separate scratch --basetemp/--junitxml outputs.
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-adapter-consumer-20261009-764f3d92\validate.py' lint-v3
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-adapter-consumer-20261009-764f3d92\validate.py' format-check-v3
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-adapter-consumer-20261009-764f3d92\validate.py' lint-v4
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-adapter-consumer-20261009-764f3d92\validate.py' format-check-v4
git diff --check
git diff --cached --check
```

Scoped Ruff 0.15.14/0.15.16 lint and format checks passed. All previous assertions
remain; no unrelated formatting. Initial attempts and logs are preserved: copied
wrappers initially pointed at the source worktree (file-not-found, no tests run;
format reported both existing files unchanged). New seam tests then caught P0
API/settings and inspector return-shape mistakes, corrected solely here. Final
successful receipts supersede those failed checks without erasing them.

## Byte and preservation receipts

Private receipts: `C:\Projects\AWS Project\dependency-acquisition\rag-adapter-consumer-20261009-764f3d92`.
`source-self-review-final.json` records Codex self-review, all inherited function ASTs,
separate raw working-copy/normalized Git hashes and line-ending counts. The commit
receipt records actual Git blob bytes obtained without a PowerShell text pipe.
CRLF operator/script test working copies and LF Git blobs are different byte
bindings; no protected file or global Git line-ending setting was normalized.

| Path | Git LF bytes SHA-256 | Raw working-copy SHA-256 |
|---|---|---|
| scripts/jev_rag_smoke_operator.py | c5328d64f9679f205445c88d6cdd8add8af2ca384c7e39913d8bfe55b9c2bc28 | 0548719b1a785f3ca0ce5a1062da16558c6aa422fc532c4114e596eb76b2b044 |
| tests/test_jev_rag_smoke_operator.py | 47295f220bafae5c273eb2a6fb2c53150ee37abde128d5136b0629ee273d29f7 | 4498843e758b08a00938d9c5a8f704a5df61537cedeaebe42d875dcf43718f36 |
| tests/test_jev_rag_smoke_adapter_consumer.py | d2d02568ca8b693e57bef08ed0db53e986805b0a1d838f476594c5e2fe9751e0 | d2d02568ca8b693e57bef08ed0db53e986805b0a1d838f476594c5e2fe9751e0 |

Before/after metadata snapshots match for all seventeen existing worktrees, their
HEAD/status/changed and untracked readable files, both adapter reviews, protected
artifacts, fixed inputs, fifteen pricing-research files and sealed evidence.
The 1,084 inaccessible sealed paths remain disclosed, not newly certified;
permissions were not changed. Historical inventories were reused read-only.
Caches/image were not operated on. Accepted adapter/application/P0/contracts,
packager, pins/locks, ZIPs, receipts and Reviewer v2 remain unchanged. No package
or verification bundle was rebuilt/refreshed for this host-only increment.

## Focused Claude review and remaining gates

Review the explicit plan separation, durable ordering, full-state clean predicate,
evidence-before-inspection, all-failure projection, original-defect precedence,
FunctionError handling, unchanged inspector reuse, and actual-return/index-hash
confirmation. Component adapter acceptance does not accept this new consumer.

Keep O1–O4 and adapter AD1-O1–O4 limitations visible. This seam does not provide a
live factory/CLI, credential-provider/endpoint approval, private permissions,
request/log authenticated provenance, REPORT join or recovery consumer. The
existing adapter's rare foreign metadata-get defect can still preclude body
closure; its state rejects clean consumption here, without an adapter rewrite.
The adapter's accepted KeyboardInterrupt mapping remains unchanged.

Before any future run: independent consumer acceptance; separately reviewed
operational factory and request/REPORT observation enforcement; exact owner
inputs/data consent, prices, defensible token bounds/limits/budgets including
infrastructure allowance; credential/endpoint/private-output gates; exact
artifact/native/configuration bindings and explicit run authority. Parent claims
and local hashes are not cryptographic approval or authenticated execution.
Semantic assessment and qualification remain later and separate. Stop here for
Claude's independent review; no main merge, push or live action occurred.
