# Jev release observation capture helper — Claude handoff

Date: 2026-10-06. Offline implementation and synthetic validation only. Local commits, not pushed or merged.

**Status.** Codex reviewed the original commit `fa54782c150d0934fb8443e50267657ef3a7b135` and requested one change (OC-1). The review report is `docs/experiments/jev-release-observation-capture-codex-review.md` (raw SHA-256 `d59e57c8…`), left uncommitted and unmodified. This document now describes the **OC-1 correction**, a direct child of `fa54782`. **Codex's independent delta review of that correction is pending.** See "OC-1 correction" below; statements elsewhere about the original commit are historical.

| Item | Value |
|---|---|
| Branch | `phase0/jev-release-observation-capture` (new) |
| Worktree | `C:\Projects\AWS Project\worktrees\jev-release-observation-capture` (new) |
| Base commit | `aeee2e1597f06f365a789abefbda65368c81fe84` (accepted local integration) |
| Original commit (reviewed) | `fa54782c150d0934fb8443e50267657ef3a7b135`, the single child of the base, adding exactly the three paths below |
| OC-1 correction commit | the single child of `fa54782`, changing only the same three paths. A commit cannot contain its own hash; `git log -1` on this branch gives it. |

**Not authorized, and not done:**
- the live entry point was never exercised;
- no AWS reads or other calls, credential or secret access, network access, installs, builds or artifact execution;
- no deployment, push or merge;
- no historical-record rewriting;
- no Reviewer Protocol v2 change.

## Scope and separation

**Paths changed (all new):**
- `scripts/jev_release_observation_capture.py`
- `tests/test_jev_release_observation_capture.py`
- `docs/experiments/jev-release-observation-capture-handoff.md`

**Untouched:**
- the accepted checker and its `jev-saved-aws-response-v2` contract;
- the application, packaging and requirements;
- shared handoffs and work logs;
- Reviewer Protocol v2;
- all evidence.

**Separation from Codex's adapter.**
- Codex's adapter (`scripts/jev_saved_record_adapter.py`, its tests and handoff) converts **historical** selected-field projections. This helper captures **new** observations from explicitly planned, future read-only calls.
- Neither file exists on this branch. Nothing here imports or reads Codex's in-progress files.
- This helper never reads saved records at all. The plan is its only file input, and a plan cannot carry responses.

**Collision checks before creation:**
- the branch did not exist and the worktree path was free;
- `git worktree list` showed only `main`, `jev-integration` and `jev-release-preflight`;
- main's stash was empty.

The worktree was created with `git worktree add -b phase0/jev-release-observation-capture <path> aeee2e1`. The new worktree was clean at the base.

The helper's runtime imports are standard library only. `boto3` and `botocore` are imported lazily inside `boto3_client_factory`, which only `--live` reaches. A test asserts that the shared patterns, record schema, roles, integer bound and request keys are **identical** to the accepted checker's.

## Capture-plan contract (`jev-release-observation-capture-plan-v1`)

The plan is parsed with the checker's strict JSON rules:
- at most 64 KiB;
- UTF-8;
- no duplicate keys, NaN, Infinity or non-finite floats;
- integers of at most 64 digits;
- no unpaired surrogates;
- bounded nesting.

Unknown keys are rejected everywhere.

| Key | Rule |
|---|---|
| `schema` | exactly `jev-release-observation-capture-plan-v1` |
| `capture_id` | safe token `[A-Za-z0-9._:-]{1,128}` |
| `account_id` | 12 digits; STS must return exactly this account |
| `region` | checker region pattern; every client uses it |
| `timeouts` | exactly `connect_seconds` (integer 1–10) and `read_seconds` (integer 1–30). No retry setting can be supplied. |
| `observations` | 1–4 entries, each exactly `{role, operation, request}`, roles unique |
| `max_calls` | integer equal to `1 + len(observations)`; no headroom (`PLAN_CALL_LIMIT_INVALID`) |
| `authorization_reference` (optional) | `{label, sha256}`. Recorded as `REFERENCED_NOT_AUTHENTICATED` and never verified. |

**Permitted reads:**

| Role | Operation | Request |
|---|---|---|
| implicit, always first | STS `GetCallerIdentity` | `{}` |
| `production_baseline`, `candidate` | Lambda `GetFunctionConfiguration` | `FunctionName` plain name; optional `Qualifier` = `$LATEST` or a numeric version |
| `rollback_target` | Lambda `GetFunctionConfiguration` | `FunctionName` plus a **required numeric** `Qualifier` (`PLAN_TARGET_NOT_EXPLICIT` otherwise) |
| `alias` | Lambda `GetAlias` | exactly `FunctionName` and an explicit non-numeric `Name` |

**Plan rejection codes:**
- Any other operation gives `PLAN_OPERATION_UNSUPPORTED`. That includes `GetFunction` (and its presigned code URL), `Invoke`, list, pagination and discovery operations, and IAM operations; so does a role paired with the wrong operation.
- ARNs, partial ARNs, alias qualifiers and leading-zero versions give `PLAN_REQUEST_UNSUPPORTED`.
- Missing, extra or non-string arguments give `PLAN_REQUEST_INVALID`.

The helper never discovers or infers aliases, versions, rollback targets or a release strategy. If a role is not planned, it is not read. The checker then reports it as missing.

**Validation order.** The order is: parse and validate the plan, then claim the output, then create clients.
- An invalid plan raises an input error before any directory exists and before the client factory is called.
- A failed output claim happens before any client exists.

## Read contract

- **Sequence.** STS first, then the planned observations in plan order. The Lambda client is created only after the account is verified. Each read is observed separately. A runtime counter enforces `max_calls`.
- **Client settings.** botocore uses `connect_timeout` and `read_timeout` from the plan, and `retries={"total_max_attempts": 1, "mode": "standard"}`, so no SDK retry happens. The client factory is injectable; tests use fakes only.
- **Any failure stops every later call.** That covers a stop code, a publication failure and an interrupted capture. The completed observations are kept. Account mismatch is one such failure.
- **Clocks.** Both the UTC clock and the monotonic clock are read before the call, so a clock failure there makes no call. After a response, a clock failure is recorded with the affected timing field left `null`; no time or duration is invented.

| Stop code | When |
|---|---|
| `ACCOUNT_MISMATCH` | STS `Account` ≠ plan account |
| `READ_FAILED` | the client raised; only the exception class name, a safe-token AWS error code and the response metadata are kept, never the message |
| `RESPONSE_NOT_JSON_REPRESENTABLE` | the response is not a mapping, or contains a non-JSON type (for example a datetime), a non-finite float, a >64-digit integer, a surrogate, or nesting deeper than 64 levels (`MAX_JSON_DEPTH`). It is rejected, not coerced. |
| `RESPONSE_SERIALIZATION_FAILED` | the canonical JSON round trip of a representable response still raised `RecursionError`, `TypeError` or `ValueError`. The response is not stored; the observation records the rejection. |
| `RETRY_METADATA_MISSING` / `UNEXPECTED_RETRY` | `ResponseMetadata.RetryAttempts` is absent or not an integer / is not 0 |
| `RESPONSE_FIELD_MISSING` / `RESPONSE_FIELD_INVALID` | a binding field is absent or malformed (below) |
| `RESPONSE_BINDING_MISMATCH` | the response identity differs from the request or plan |
| `CLOCK_INVALID` | the host clock is naive, a request start does not strictly increase, the response time precedes the request start, or a monotonic reading is non-numeric, non-finite or goes backwards |
| `CLOCK_READ_FAILED` | reading the UTC or monotonic clock raised. Before the call, no call is made; after a response, the response is still preserved. |
| `CLIENT_UNAVAILABLE` / `CALL_LIMIT_REACHED` | client construction failed / defensive call-limit guard |

**Binding fields checked by the helper.** Everything else is preserved untouched and judged later by the unchanged checker.
- **STS:** `Account` (12 digits, equal to the plan), `Arn` and `UserId` must be strings.
- **`GetFunctionConfiguration`:**
  - `FunctionName`, `FunctionArn`, `Version` and `CodeSha256` must be strings;
  - `Version` must be `$LATEST` or numeric;
  - `CodeSha256` must be the canonical 44-character base64 of 32 bytes;
  - the ARN account, region and name must equal the plan and request;
  - the ARN qualifier (absent means `$LATEST`), `Version` and the requested `Qualifier` (absent means `$LATEST`) must all agree.
- **`GetAlias`:**
  - `AliasArn`, `Name` and `FunctionVersion` must be strings;
  - `FunctionVersion` must be `$LATEST` or numeric;
  - the `AliasArn` qualifier must be an alias name (not `$LATEST` or a number) equal to the requested and returned `Name`;
  - the account, region and function must equal the plan and request.

## Output and provenance contract

**Output directory:**
- `--out` must be a new directory whose parent exists and whose name is a safe token.
- No ancestor may contain `.git` (`OUTPUT_INSIDE_REPOSITORY`), so private captures cannot land in any worktree.
- It is created with a non-reusing `mkdir`; an existing path gives `OUTPUT_EXISTS`. Any other filesystem error while checking or creating it, for example a permission error, gives `OUTPUT_UNAVAILABLE` before any client exists.
- Every file is written with exclusive create (`xb`). Nothing is overwritten, renamed or deleted.

| File | Content |
|---|---|
| `capture-plan.json` | the exact plan bytes; its SHA-256 is bound everywhere as `plan_sha256` |
| `NN-account_verification.observation.json` | the STS observation. It is never a checker record, because the checker has no STS role. |
| `NN-<role>.record.json` | written only for an accepted Lambda read: exactly the checker's `{schema, role, operation, request, observed_utc, response}` with `schema = jev-saved-aws-response-v2` |
| `NN-<role>.observation.json` | `jev-release-observation-v1` provenance. Once a call has been made, its observation file is attempted for every read outcome. It can be missing only when publishing it failed, and that interrupts the capture. |
| `capture-index.json` | `jev-release-observation-capture-index-v1`, written last |

**Observation provenance** (`jev-release-observation-v1`) holds:
- `kind: NEW_OBSERVATION`, the capture id, the plan hash, the sequence number and the label;
- the actual service, operation and exact request arguments;
- timing, with its semantics recorded;
- SDK settings (timeouts, `total_max_attempts: 1`);
- `response_metadata` (retry attempts, HTTP status, request id; only well-typed safe values);
- `outcome`, which is `ACCEPTED`, `REJECTED`, `READ_FAILED` or `PUBLICATION_FAILED` (the record file could not be published, but the response is kept here), with a `reason {code, field}`;
- `error {type, aws_error_code}` for a failed read;
- the faithful `response`, plus its canonical-JSON `response_sha256`;
- `record {file, sha256}` binding the checker record.

A rejected response is still preserved in full when it is representable and the filesystem permits. A non-representable or unserializable response cannot be preserved, so it is recorded as `null`.

**Faithful preservation.**
- A response is stored exactly as returned, including `ResponseMetadata` and unknown fields.
- The JSON round trip applies only after the representability check, and is the identity for JSON-native data.
- Omitted fields stay omitted, and malformed non-binding values stay malformed. The checker then blocks them; the test `test_malformed_nonbinding_field_is_preserved_not_repaired` covers this.

**Timestamps.**
- `request_started_utc` and `response_received_utc` are separate reads of the **host** UTC clock, with microsecond precision, immediately before and after the SDK call. `elapsed_ms` comes from the host monotonic clock.
- The checker record's `observed_utc` is the **request-start** time. That is the conservative choice for freshness.
- The provenance states `HOST_UTC_CLOCK_NOT_AWS_AUTHENTICATED`. Nothing implies AWS authenticated any time.

**Index.** The index records:
- `status`: `COMPLETE`, `STOPPED` or `INTERRUPTED`, with `stop {code, field}` and `interruption`;
- planned versus attempted calls, and `account_verified`;
- accepted records with their file and observation hashes;
- every other file's SHA-256;
- the authorization status;
- `live_opt_in: CLI_FLAG_IS_NOT_OWNER_AUTHORIZATION`;
- the timing semantics and limitations.

**Publication failures (OC-1).** If writing any output file fails, the capture is interrupted:
- **Codes:** `PUBLICATION_FAILED` for an operating-system error, `PUBLICATION_COLLISION` when the file already exists, and `PUBLICATION_SERIALIZATION_FAILED` when the content could not be serialized.
- **No later reads.** No further AWS call is made.
- **Nothing is retried, overwritten, renamed or deleted.**
- **Record failure.** If a record file fails, the response is still written to its observation file when the filesystem permits.
- **Partial writes.** A partially written file is left in place, never listed in the index's `files`, and disclosed as `incomplete_file_possible: true`.
- **Index.** One attempt is made to write the index with `status: INTERRUPTED` and `interruption {code, stage, file, incomplete_file_possible, pending_stop}`. `stage` is `plan`, `record`, `observation` or `index`. That attempt is a different file, not a retry.
- **Unindexed.** If the index itself cannot be written, the console reports `INTERRUPTED_UNINDEXED` with `index_sha256: null`. This includes a capture whose reads all succeeded. Earlier files remain on disk, unindexed.
- **Never `COMPLETE`.** A publication failure never yields `COMPLETE`.

A directory without an index is an interrupted capture: for example, a failed filesystem or a killed process. Its completed observation files remain usable evidence, but are unindexed.

## Entry point and sanitized output

```powershell
python scripts/jev_release_observation_capture.py --plan <plan.json>                          # validate only; no client, no output
python scripts/jev_release_observation_capture.py --plan <plan.json> --out <new-private-dir> --live   # NOT exercised
```

**Opt-in rules.**
- `--live` and `--out` must be given together; either one alone gives `LIVE_OPT_IN_REQUIRED`.
- **`--live` is an operator opt-in, not owner authorization.** A live capture still needs separate, explicit owner authorization for the exact plan.
- At live time, credentials come from the standard boto3 chain. The helper does not load `.env`, read environment variables or print credentials.

**Exit codes:**
- 0: plan valid (validate-only) or capture `COMPLETE`;
- 1: `STOPPED`, `INTERRUPTED` or `INTERRUPTED_UNINDEXED`;
- 2: input rejected.

**Console output** is one JSON object:
- validate-only: `schema`, `status`, `calls_planned`, `plan_sha256`;
- live: `schema`, `status`, `stop_code`, `interruption_stage`, `calls_planned`, `calls_attempted`, `accepted_records`, `index_sha256`. On an interruption, `stop_code` is the publication code and `interruption_stage` its fixed stage name.

Input errors print `{status: INPUT_REJECTED, code}` on stderr. The console never prints:
- environment values or credentials;
- response bodies or ARNs, including role and caller ARNs;
- account IDs or function names;
- provider messages or paths;
- exception messages or tracebacks for the handled failures above: client, read, clock, serialization and publication failures, and output-claim filesystem errors.

An exception outside these handled boundaries would be a programming defect. It is deliberately not converted into a capture outcome.

**Private captures are sensitive.** They contain full configurations, including environment values and the role ARN. They must stay outside Git, and the helper enforces this for the output directory. **Outside Git is not confidentiality:** the helper neither sets nor audits restrictive ACLs. The operator must choose a private directory and a retention policy. Concurrent hostile replacement of reparse points or junctions is not ruled out.

## Validation of the original commit `fa54782` (historical)

The current OC-1 validation is in "OC-1 correction" below.

Run from the worktree, with fresh scratchpad basetemps:

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' --version
#   Python 3.11.15
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B -m pytest tests/test_jev_release_observation_capture.py -q --tb=short -p no:cacheprovider --basetemp <scratch>\cap-final-311
#   117 passed; offline guard active: 0 outbound network attempt(s) intercepted, none sent
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check --no-cache scripts/jev_release_observation_capture.py tests/test_jev_release_observation_capture.py
#   All checks passed!
& '...same guard...' format --check --no-cache scripts/jev_release_observation_capture.py tests/test_jev_release_observation_capture.py
#   2 files already formatted
git diff --cached --check   # clean
```

**Tests.** There are 37 test functions, giving 117 cases with parametrization. They cover:
- **Checker compatibility.**
  - Full four-role capture: the unchanged checker's `load_inputs` and `evaluate` give no errors, and only `ARTIFACT_FILE_NOT_VERIFIED` is missing.
  - The checker CLI reads the written record files.
  - An unresolved strategy with only the baseline captured is `INCOMPLETE`, with `CANDIDATE_RECORD_MISSING` and both unresolved decisions.
  - An alias strategy without alias or rollback captures reports them missing rather than inventing them.
- **Bindings.** Exact operation, request and response bindings; plan and file hashes.
- **Account.** A mismatch makes one call and creates no Lambda client.
- **Plan rejection.** 37 invalid-plan cases and 8 unreadable-plan cases, each with no factory call and no directory.
- **Response defects.** 16 function and 7 alias defects are rejected with the response preserved. Unrepresentable responses are rejected, not coerced.
- **Retries and failures.** Retry and missing-metadata stops; a failed read keeps no message; a client-construction failure makes no call.
- **Partial results** are preserved and indexed.
- **Timestamps.** They are distinct, increasing, separately read and in microsecond UTC format. Repeated or backwards clocks and a naive clock are rejected.
- **Output.** Duplicate claims, reuse of an existing directory, overwriting, and output inside a Git worktree are all refused.
- **CLI.** Opt-in rules and sanitized console output; the private file keeps the faithful secret.
- **Static checks.** Stdlib-only imports with a lazy SDK import, and no discovery, invocation, presigned-URL or `.env` paths.
- **Offline guard.** An autouse fixture asserts the guard is installed and that no test adds a blocked attempt.

**Mutation check.** I ran the test file against 13 deliberately broken copies of the helper in a scratch copy of the tree (`git archive HEAD`). The scratch copy has no `.git`, so one repository-location assertion fails there in every run. Every mutation produced **additional** failures:
- account mismatch continuing;
- retries ignored;
- overwrite allowed;
- directory reused;
- repeated start time allowed;
- version binding skipped;
- provider message kept;
- client created before validation;
- any qualifier accepted;
- a missing field fabricated;
- the Git-location check removed (caught by the earlier synthetic-`.git` assertion);
- `observed_utc` taken at receipt;
- continuing after a stop.

## Hashes

The script and tests are committed as LF blobs. Their working copies are also LF (0 CR bytes), so raw-file and committed-blob hashes are identical for them at commit time. A later checkout under `core.autocrlf=true` may produce CRLF working copies with different raw hashes. Always reproduce from raw `git show <commit>:<path>` bytes, without PowerShell text conversion.

**Original commit `fa54782` (historical, as reviewed by Codex):**

| Path | Committed-blob SHA-256 | Git blob id |
|---|---|---|
| `scripts/jev_release_observation_capture.py` | `1aabcaa199d3dcceca4c682b447478acc9aa6f09a05db297767aed5f598edf13` | `ebee4ae8a3b7c4492aa9765e68fa4526b2327bbd` |
| `tests/test_jev_release_observation_capture.py` | `15562466c5d7b8650cf4759fb0618d18aa6e6dc617a91df68eddf87f8a6f6172` | `67d9f039df2896f2a3d2d3d23eee72611d4baf99` |
| this handoff at `fa54782` | `8bdc50ca04cae4172fc66d077e020ac4833cdeb17d7f12b5ef3dd2d362f113d8` | `58ce67af39cb77a106c44b803208828cd6ea82a8` |

**OC-1 correction commit (current):**

| Path | Committed-blob SHA-256 | Git blob id |
|---|---|---|
| `scripts/jev_release_observation_capture.py` | `c84462b72f9b85cc5f15edb7e0cd05791dd45cbc7d48c19a3172706ed40c06a7` | `7b7dd5c965ec739e244ab1194ada1150d60516a9` |
| `tests/test_jev_release_observation_capture.py` | `b1877b5ee6ca557329f1e828f663f6db24970db2a6d870426f7a5d185a17de28` | `8be46c54b86ffc0c104e2b4e695ca2ce84918c75` |

Both correction working copies have 0 CR bytes, so their raw hashes equal these blob hashes when committed.

This handoff cannot contain its own hash.

## Preservation

- **Main:** HEAD `9bf00d13dd9c83a635719dfd2acb7798c353866c` on `phase0/baseline-instrumentation-eval`. Its two unstaged shared documents and 28 untracked entries are untouched. No stash, switch or staging.
- **Other worktrees:** `jev-integration` (`aeee2e1`, with my uncommitted final review) and `jev-release-preflight` (`86cd103`) are unchanged.
- **Evidence:** the sealed startup evidence, the accepted ZIP and all reports were not touched.
- **Scratch:** mutation copies and test basetemps live only in the session scratchpad.

## Remaining requirements before a future authorized capture

1. **Owner authorization.** Explicit, separately recorded owner authorization for one exact capture plan, by plan SHA-256. Under the Free-plan constraint, this includes confirming that the planned reads are free-tier, read-only API calls.
2. **Plan and decisions.** A reviewed plan naming the exact function, and only the versions and alias it actually requests. Alias and rollback decisions are prerequisites when those observations are requested, and for release evaluation. They are not needed for a narrower capture such as baseline-only, which the helper permits with an unresolved strategy. The helper never infers them.
3. **Credentials.**
   - A least-privilege, read-only principal, limited to `sts:GetCallerIdentity`, `lambda:GetFunctionConfiguration` and `lambda:GetAlias` on the named function.
   - Credentials supplied through the standard chain, outside the repository. No `.env`.
   - **The planned-call counter is not a total bound.** `max_calls` counts only the planned API calls. Credential acquisition or refresh by the standard boto3 chain can make additional requests or run a configured `credential_process`, under settings outside the helper's timeouts and retry configuration. That includes assume-role, web identity, SSO, and container or instance metadata. The capture therefore has no total wire-request count and no total wall-clock deadline. A future authorization must separately fix the allowed credential flow and endpoint configuration.
4. **Output location.** A new private output directory outside every Git worktree, with operator-established restrictive permissions; the helper does not set ACLs. It also needs a retention and handling decision for sensitive configuration.
5. **Before release.**
   - Review the capture's index and observation files.
   - Run the unchanged checker on the written records with the artifact and an explicit `--as-of`.
   - Complete qualification, the final integrated review and operational authorization.
6. **Known limits.**
   - Host-clock times are not AWS-authenticated.
   - The capture cannot prove response authenticity to a later reader.
   - IAM, VPC, KMS, concurrency and other checker-unchecked fields remain out of scope.

## Original review scope for Codex (historical; reviewed at `fa54782`)

1. **Base and paths.** The base is `aeee2e1`; the commit is its single child; exactly three new paths.
2. **Checker unchanged.** The checker blob is still `87f2a1d6…` and the tests' blob `21698346…`. No shared document, application, packaging or requirements changes.
3. **Plan validation is complete before effects.**
   - Every rejection happens before any directory or client exists.
   - Only `GetCallerIdentity`, `GetFunctionConfiguration` and `GetAlias` are reachable, with no discovery, `GetFunction`, invocation or presigned path.
   - The rollback target must be an explicit numeric version.
   - `max_calls` has no headroom.
4. **Read safety.**
   - Exactly one SDK attempt with bounded timeouts.
   - `RetryAttempts` must be present and 0.
   - Any failure, and account mismatch in particular, stops all later calls.
   - The Lambda client is created only after STS verification.
5. **Faithfulness.**
   - Responses are preserved as returned.
   - Nothing is fabricated, defaulted or repaired.
   - Non-representable data is rejected, not coerced.
   - Records are emitted only for accepted Lambda reads, exactly in the checker v2 envelope.
6. **Provenance.**
   - Request-start versus response-received semantics, with `observed_utc` = request start.
   - Host clock, not AWS-authenticated.
   - The bindings between record, observation and plan hash, and the index file map.
7. **Publication.** New directory only, outside Git; exclusive create; no overwrite, rename or delete; partial results preserved; index written last.
8. **Sanitization.** Console and stderr carry fixed codes, counts and hashes only. Failed reads keep no provider message.
9. **Opt-in.** `--live` plus `--out` is required, and is documented as not being owner authorization. The live path was not exercised.
10. **Test meaning.** Fakes and the guard only. The regressions fail under the mutations listed above.

## OC-1 correction (Codex review of `fa54782`)

**Base and report.**
- Correction base: `fa54782c150d0934fb8443e50267657ef3a7b135`. I verified it as HEAD and confirmed that the worktree was clean apart from Codex's report.
- The report, `docs/experiments/jev-release-observation-capture-codex-review.md`, was verified at raw SHA-256 `d59e57c841fa00df70c4e03b0f70e26f28336fd7a7b9cb475de8cf992a6c954b` before editing. It is left uncommitted and unmodified.
- Only OC-1 is fixed. N-1 to N-3 are clarified in documentation only, and N-4 is unchanged.

**What changed, by failure point.** Each failure now meets its boundary with fixed fields only:

| Failure point | Before (`fa54782`) | Now |
|---|---|---|
| Record publication (OS error, partial write, exclusive-create collision) | raw `OSError` / `FileExistsError` escaped `main()` | `PublicationError` → status `INTERRUPTED` (`PUBLICATION_FAILED` or `PUBLICATION_COLLISION`, stage `record`). The response is still written to its observation file (outcome `PUBLICATION_FAILED`) when possible. |
| Observation publication | raw exception escaped | `INTERRUPTED`, stage `observation`; a stop code already pending is kept as `pending_stop` |
| Plan-copy publication | raw exception escaped | `INTERRUPTED`, stage `plan`; no client is created |
| Final index publication | raw exception escaped | `INTERRUPTED_UNINDEXED`, `index_sha256: null`, exit 1. Never `COMPLETE`, even when every read succeeded. |
| Serializing our own output | raw `ValueError`, `TypeError` or `RecursionError` escaped | `PUBLICATION_SERIALIZATION_FAILED` for the affected stage |
| Response round trip | a 1,500-level response passed `representable()`, then `RecursionError` escaped | `representable()` now bounds nesting at `MAX_JSON_DEPTH = 64`, giving `RESPONSE_NOT_JSON_REPRESENTABLE`. Any remaining serializer error gives `RESPONSE_SERIALIZATION_FAILED`. Both stop with a rejected observation (`response: null`). |
| UTC or monotonic clock raising after a response | raw exception escaped; no observation | `CLOCK_READ_FAILED`. The response is preserved, and the failed timing field is `null`, not invented. A non-numeric or backwards monotonic value is `CLOCK_INVALID`. |
| Either clock raising before the call | raw exception escaped | `CLOCK_READ_FAILED`, and no call is made |
| Output-directory claim (for example a permission error) | raw `PermissionError` escaped | input code `OUTPUT_UNAVAILABLE`, exit 2; no client exists |

**Exception handling.**
- **Catches are specific:**
  - publication catches `FileExistsError` and `OSError` around `open("xb")` and `write`;
  - serialization catches `RecursionError`, `TypeError` and `ValueError` around `canonical`;
  - the claim catches `OSError`;
  - only the injectable clock reads use a broad `except Exception` (like the existing injectable client and factory), and they keep a fixed code only.
- **No catch-all.** There is no catch-all in `main()`. An unanticipated programming error still surfaces as a traceback, instead of being turned into a capture result.
- **Not added:** recovery, resend, publication retry, deletion of partial files, or directory reuse.

**Unchanged:** the normal path, the strict plan, the account gate, the retry checks, faithful preservation, checker compatibility, and the accepted historical adapter and its timestamp convention.

**Limits that remain.**
- A process killed mid-capture leaves an unindexed directory.
- An index written after an interruption reflects only what was durably published before it.
- `incomplete_file_possible` means the failed file was opened before the error. Its bytes are not trustworthy.

### OC-1 validation (exact commands and results)

Run from the worktree with fresh scratchpad basetemps; Codex's probe directories were not reused.

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' --version
#   Python 3.11.15
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B -m pytest tests/test_jev_release_observation_capture.py -q --tb=short -p no:cacheprovider --basetemp <scratch>\oc1-final-311
#   143 passed; offline guard active: 0 outbound network attempt(s) intercepted, none sent
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check --no-cache scripts/jev_release_observation_capture.py tests/test_jev_release_observation_capture.py
#   All checks passed!
& '...same guard...' format --check --no-cache scripts/jev_release_observation_capture.py tests/test_jev_release_observation_capture.py
#   2 files already formatted
git diff --cached --check   # clean
```

**Test composition: 143 cases.** That is the original 117 plus 26 new `test_oc1_*` cases:
- **Defect regressions (24):**
  - publication failure at the plan, record and observation stages;
  - index failure reported unindexed;
  - a partial write kept and disclosed;
  - an existing-file collision;
  - an injected serializer failure keeping a rejected observation;
  - a serializer failure everywhere, disclosed as unindexed;
  - actual 1,500-level nesting;
  - a UTC clock exception after the response;
  - a monotonic exception and a non-numeric value after the response;
  - UTC and monotonic exceptions before a call;
  - an unwritable output parent;
  - eight CLI-boundary cases (record, observation, index, partial, collision, serializer, nesting, clock), each asserting sanitized stdout and stderr, exit 1, no `COMPLETE` and no later client call;
  - the CLI unwritable-output case.
- **Positive and preservation checks (2):** the depth bound accepts exactly 64 levels and rejects 65 (it references the new `MAX_JSON_DEPTH` constant); and the `PublicationError` fixed-field contract.

**Existing tests (4 updated, 1 helper extended).**
- Three assertions now include the new `interruption_stage` status key: complete capture, and console complete and failed-read.
- `test_publisher_never_overwrites` now expects `PublicationError(PUBLICATION_COLLISION)` instead of a raw `FileExistsError`.
- The test fake can now run a scripted side effect, used for the collision and deep-response cases. Deep responses go through it so the fake never deep-copies them.

**Regressions reproduce the defect.** I ran this test file against the original `fa54782` helper, in a `git archive` scratch tree with the new test file copied in: **31 failed, 112 passed.**
- **Defect regressions (24):** all fail by the original defect, an escaped raw `OSError`, `FileExistsError`, `PermissionError`, `RuntimeError`, `ValueError`, `RecursionError` or `TypeError`.
- **Interface-dependent checks (2):** the depth-bound and `PublicationError` contract tests fail because the new constant and class are absent.
- **Changed contracts (4):** the four updated existing assertions.
- **Scratch-tree artifact (1):** `test_output_inside_a_git_worktree_is_refused` fails only because a `git archive` tree has no `.git`. It passes in the worktree and is not counted as a detection.
- **The 112 passing** are the unchanged existing behaviour.

### OC-1 preservation

- **Main:** HEAD `9bf00d13dd9c83a635719dfd2acb7798c353866c`, status unchanged.
- **Other worktrees:** integration (`aeee2e1`, with my uncommitted final review), release-preflight (`86cd103`) and saved-record adapter (`e88ada3`, with my uncommitted adapter review) are unchanged.
- **Codex's capture review report:** unchanged and uncommitted.
- **Evidence:** sealed startup evidence, the accepted ZIP, the adapter's private outputs and Codex's probe directories were not touched or reused.

### Focused OC-1 delta-review scope for Codex

1. **Delta shape.** `fa54782..HEAD` is one commit changing only the three authorized paths. Codex's report is unchanged.
2. **Every OC-1 site.** Each site in the report (`Publisher.write_bytes/write_json`, `Capture.observe` clock, serialization and publication points, final index, `main`) now returns fixed codes. No raw message, path or traceback reaches stdout or stderr for these failures.
3. **No later reads.** Every new failure stops further reads, with no later client call.
4. **No false completion.** `COMPLETE` is impossible after any publication failure, and `INTERRUPTED_UNINDEXED` is honest when the index cannot be written.
5. **Preservation.** Nothing is overwritten, retried or deleted. Partial files are disclosed and excluded from `files`. The response survives a record-publication failure when the filesystem permits.
6. **No fabrication.** No timestamp, elapsed time or response field is fabricated, and failed timing fields are `null`.
7. **Depth bound.** `MAX_JSON_DEPTH` is consistent between `representable()` and the serializer, and the plan parser is also covered.
8. **Catch scope.** Catches stay narrow. Only injectable clock reads use broad catches, and there is no catch-all in `main()`.
9. **Behaviour preserved.** The normal path, strict plan, account gate, retry and checker-compatibility behaviour are unchanged.
