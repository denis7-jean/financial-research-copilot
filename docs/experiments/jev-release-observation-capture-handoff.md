# Jev release observation capture helper — Claude handoff

Date: 2026-10-06. Offline implementation and synthetic validation only. Local commit, not pushed or merged. **Codex's independent review is pending.**

| Item | Value |
|---|---|
| Branch | `phase0/jev-release-observation-capture` (new) |
| Worktree | `C:\Projects\AWS Project\worktrees\jev-release-observation-capture` (new) |
| Base commit | `aeee2e1597f06f365a789abefbda65368c81fe84` (accepted local integration) |
| Final commit | the single child of the base, changing exactly the three paths below. A commit cannot contain its own hash; `git log -1` on this branch gives it. |

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
- **Any failure stops every later call.** The completed observations are kept. Account mismatch is one such failure.

| Stop code | When |
|---|---|
| `ACCOUNT_MISMATCH` | STS `Account` ≠ plan account |
| `READ_FAILED` | the client raised; only the exception class name, a safe-token AWS error code and the response metadata are kept, never the message |
| `RESPONSE_NOT_JSON_REPRESENTABLE` | the response is not a mapping, or contains a non-JSON type (for example a datetime), a non-finite float, a >64-digit integer or a surrogate. It is rejected, not coerced. |
| `RETRY_METADATA_MISSING` / `UNEXPECTED_RETRY` | `ResponseMetadata.RetryAttempts` is absent or not an integer / is not 0 |
| `RESPONSE_FIELD_MISSING` / `RESPONSE_FIELD_INVALID` | a binding field is absent or malformed (below) |
| `RESPONSE_BINDING_MISMATCH` | the response identity differs from the request or plan |
| `CLOCK_INVALID` | the host clock is naive, a request start does not strictly increase, or the response time precedes the request start |
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
- It is created with a non-reusing `mkdir`; an existing path gives `OUTPUT_EXISTS`.
- Every file is written with exclusive create (`xb`). Nothing is overwritten, renamed or deleted.

| File | Content |
|---|---|
| `capture-plan.json` | the exact plan bytes; its SHA-256 is bound everywhere as `plan_sha256` |
| `NN-account_verification.observation.json` | the STS observation. It is never a checker record, because the checker has no STS role. |
| `NN-<role>.record.json` | written only for an accepted Lambda read: exactly the checker's `{schema, role, operation, request, observed_utc, response}` with `schema = jev-saved-aws-response-v2` |
| `NN-<role>.observation.json` | `jev-release-observation-v1` provenance for every attempted read, whatever its outcome |
| `capture-index.json` | `jev-release-observation-capture-index-v1`, written last |

**Observation provenance** (`jev-release-observation-v1`) holds:
- `kind: NEW_OBSERVATION`, the capture id, the plan hash, the sequence number and the label;
- the actual service, operation and exact request arguments;
- timing, with its semantics recorded;
- SDK settings (timeouts, `total_max_attempts: 1`);
- `response_metadata` (retry attempts, HTTP status, request id; only well-typed safe values);
- `outcome`, which is `ACCEPTED`, `REJECTED` or `READ_FAILED`, with a `reason {code, field}`;
- `error {type, aws_error_code}` for a failed read;
- the faithful `response`, plus its canonical-JSON `response_sha256`;
- `record {file, sha256}` binding the checker record.

A rejected response is still preserved in full. Only a non-representable response cannot be preserved, so it is recorded as `null`.

**Faithful preservation.**
- A response is stored exactly as returned, including `ResponseMetadata` and unknown fields.
- The JSON round trip applies only after the representability check, and is the identity for JSON-native data.
- Omitted fields stay omitted, and malformed non-binding values stay malformed. The checker then blocks them; the test `test_malformed_nonbinding_field_is_preserved_not_repaired` covers this.

**Timestamps.**
- `request_started_utc` and `response_received_utc` are separate reads of the **host** UTC clock, with microsecond precision, immediately before and after the SDK call. `elapsed_ms` comes from the host monotonic clock.
- The checker record's `observed_utc` is the **request-start** time. That is the conservative choice for freshness.
- The provenance states `HOST_UTC_CLOCK_NOT_AWS_AUTHENTICATED`. Nothing implies AWS authenticated any time.

**Index.** The index records:
- `status`: `COMPLETE` or `STOPPED`, with `stop {code, field}`;
- planned versus attempted calls, and `account_verified`;
- accepted records with their file and observation hashes;
- every other file's SHA-256;
- the authorization status;
- `live_opt_in: CLI_FLAG_IS_NOT_OWNER_AUTHORIZATION`;
- the timing semantics and limitations.

A directory without an index is an interrupted capture, for example after an operating-system write failure. Its completed observation files remain usable evidence, but are unindexed.

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
- 1: `STOPPED`;
- 2: input rejected.

**Console output** is one JSON object:
- validate-only: `schema`, `status`, `calls_planned`, `plan_sha256`;
- live: `schema`, `status`, `stop_code`, `calls_planned`, `calls_attempted`, `accepted_records`, `index_sha256`.

Input errors print `{status: INPUT_REJECTED, code}` on stderr. The console never prints:
- environment values or credentials;
- response bodies or ARNs, including role and caller ARNs;
- account IDs or function names;
- provider messages or paths.

**Private captures are sensitive.** They contain full configurations, including environment values and the role ARN. They must stay outside Git; the helper enforces this for the output directory.

## Validation (exact commands and results)

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

| Path | Committed-blob SHA-256 | Git blob id |
|---|---|---|
| `scripts/jev_release_observation_capture.py` | `1aabcaa199d3dcceca4c682b447478acc9aa6f09a05db297767aed5f598edf13` | `ebee4ae8a3b7c4492aa9765e68fa4526b2327bbd` |
| `tests/test_jev_release_observation_capture.py` | `15562466c5d7b8650cf4759fb0618d18aa6e6dc617a91df68eddf87f8a6f6172` | `67d9f039df2896f2a3d2d3d23eee72611d4baf99` |

This handoff cannot contain its own hash.

## Preservation

- **Main:** HEAD `9bf00d13dd9c83a635719dfd2acb7798c353866c` on `phase0/baseline-instrumentation-eval`. Its two unstaged shared documents and 28 untracked entries are untouched. No stash, switch or staging.
- **Other worktrees:** `jev-integration` (`aeee2e1`, with my uncommitted final review) and `jev-release-preflight` (`86cd103`) are unchanged.
- **Evidence:** the sealed startup evidence, the accepted ZIP and all reports were not touched.
- **Scratch:** mutation copies and test basetemps live only in the session scratchpad.

## Remaining requirements before a future authorized capture

1. **Owner authorization.** Explicit, separately recorded owner authorization for one exact capture plan, by plan SHA-256. Under the Free-plan constraint, this includes confirming that the planned reads are free-tier, read-only API calls.
2. **Plan and decisions.** A reviewed plan naming the exact function, versions and alias. Owner decisions on release strategy and the rollback version must exist first; this helper will not infer them.
3. **Credentials.**
   - A least-privilege, read-only principal, limited to `sts:GetCallerIdentity`, `lambda:GetFunctionConfiguration` and `lambda:GetAlias` on the named function.
   - Credentials supplied through the standard chain, outside the repository. No `.env`.
4. **Output location.** A new private output directory outside every Git worktree, with a retention and handling decision for sensitive configuration.
5. **Before release.**
   - Review the capture's index and observation files.
   - Run the unchanged checker on the written records with the artifact and an explicit `--as-of`.
   - Complete qualification, the final integrated review and operational authorization.
6. **Known limits.**
   - Host-clock times are not AWS-authenticated.
   - The capture cannot prove response authenticity to a later reader.
   - IAM, VPC, KMS, concurrency and other checker-unchecked fields remain out of scope.

## Focused independent-review scope for Codex

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
