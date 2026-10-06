# Jev release preflight checker — Claude handoff

This handoff covers a bounded, offline implementation. It is local only and has not been pushed or merged. Codex review is pending.

| Item | Value |
|---|---|
| Branch | `phase0/jev-release-preflight` (new) |
| Worktree | `C:\Projects\AWS Project\worktrees\jev-release-preflight` (new) |
| Base commit | `9bf00d13dd9c83a635719dfd2acb7798c353866c` |
| Implementation commit | `e42d5e6ad900c91307fe35497143a35e417a13af` (checker and tests) |
| Final commit | the direct child of `e42d5e6`, which adds only this handoff. A commit cannot contain its own hash; `git log -1` on the branch gives it. |
| Date | 2026-10-06 |

**No collisions.** Before creation, the branch did not exist, the `worktrees` directory did not exist, and `git worktree list` showed only `main`. The worktree was created with `git worktree add -b phase0/jev-release-preflight <path> 9bf00d1`.

## Changed-file inventory (base..final)

| Path | Commit | Lines |
|---|---|---:|
| `scripts/jev_release_preflight.py` (new) | `e42d5e6` | 1,127 |
| `tests/test_jev_release_preflight.py` (new) | `e42d5e6` | 921 |
| `docs/experiments/jev-release-preflight-handoff.md` (new) | final | this file |

Nothing else changed. In particular, these are untouched:

- shared packaging code;
- application code;
- requirements and configuration;
- CI;
- the consolidated handoff and work log;
- Reviewer Protocol v2.

No additional dependency path was needed. The checker uses the standard library only and does not import `scripts/lambda_package.py`.

## Source and test hashes

These are SHA-256 hashes of the committed blob content (LF), reproducible with `git show <commit>:<path> | sha256sum`. The Windows working copy of the script uses CRLF endings, so hashing the raw working file gives a different value.

| Path | Blob SHA-256 | Git blob id |
|---|---|---|
| `scripts/jev_release_preflight.py` | `3d21d3dacce40007ac090863873112f3859f0af47f128720d7f35b2272bb5e3c` | `29b780495c2da3b42c6ca246f886b17f52963583` |
| `tests/test_jev_release_preflight.py` | `5af8bce7914e7deaf625deedd00f5747417fa7e5f269179ed9e7db33069e3977` | `68389c98dc5fa0c37bc375ec8818b2e709661315` |

## Checker contract

### Invocation

```
python -B -m scripts.jev_release_preflight --plan PLAN.json [--record SAVED.json ...] [--artifact candidate.zip] [--as-of ISO-8601]
```

**Output.**
- **stdout:** one sorted, compact JSON result.
- **stderr:** `{"status":"INPUT_REJECTED","code":...}`, written only when the input contract is broken.

**Exit codes.**

| Code | Meaning |
|---|---|
| 0 | `technical_status` is `CONSISTENT_PENDING_EXTERNAL_GATES` |
| 1 | `technical_status` is `BLOCKED` or `INCOMPLETE` |
| 2 | Input-contract rejection |

**What the module never does:**
- import boto3, botocore, socket, subprocess or any HTTP library;
- write, rename or delete files;
- extract or execute the archive.

It reads only the plan, the record files and the artifact (`rb`), plus the single manifest member of the ZIP. A test enforces this structurally.

### Release plan (`jev-release-plan-v1`, strict keys)

**Identity.**
- `plan_id`
- `account_id` (12 digits)
- `region`
- `production_function`
- `candidate_function`
- `max_fact_age_seconds`

**`artifact`.** `sha256` (raw hex), `manifest_sha256` and `zip_bytes`. The AWS `CodeSha256` form is derived from these, never typed in by hand.

**`intended_configuration`.**
- `runtime`
- `architectures` (exactly one)
- `handler`
- `package_type` (`Zip`)
- `layers` (an ordered list of layer-version ARNs; `[]` for the chosen complete-function allocation)
- `memory_size`, `timeout`, `ephemeral_storage`
- `environment`

**`environment`.** This has two keys:
- `variables`, keyed **only** by the names the application actually reads:
  - `BEDROCK_MODEL_ID`, `S3_BUCKET_NAME`, `FAISS_INDEX_S3_KEY`, `FAISS_META_S3_KEY`;
  - `COPILOT_ROUTER_PROVIDER`, `COPILOT_CW_REQUEST_LOG`, `ENABLE_EVALUATE_ENDPOINT`;
  - `EVALUATE_ENDPOINT_TOKEN`.

  Each name takes an `expect` of `absent`, `present`, `sha256` or `equals`. The secret `EVALUATE_ENDPOINT_TOKEN` cannot use `equals`, so it is compared by hash only. A plan expecting `COPILOT_ROUTER_PROVIDER` to be anything but absent or `haiku` is rejected, because production stays Haiku.
- `allow_unlisted`.

**`release_strategy`.**
- `{"type":"unresolved"}`, **or**
- `{"type":"alias", "alias_name", "phase": "pre_release"|"post_release", "candidate_version", "expected_alias_revision_id", "expected_candidate_revision_id"?, "additional_version_weights"}`.

The alias form requires `candidate_function == production_function`. The checker does not assume an alias exists and does not invent a strategy.

**`rollback`.** Either `null`, or `{"function_version", "code_sha256" (AWS base64), "expected_revision_id"?}`.

**`external_gates` (optional).** `qualification`, `independent_review` and `owner_authorization`, each `{label, sha256}` or `null`.

### Saved response record (`jev-saved-aws-response-v1`)

Each record has these fields:

- `schema`;
- `role`: `production_baseline`, `candidate`, `alias` or `rollback_target`, with one record per role;
- `operation`: `GetFunction` or `GetFunctionConfiguration` for function roles, `GetAlias` for the alias;
- `request`: `FunctionName`, `Qualifier` and `Name`;
- `observed_utc`: timezone required;
- `response`: the unmodified AWS response body.

The result reports each record's raw input SHA-256.

### Checks

1. **Artifact identity.**
   - The ZIP is streamed and hashed, and its raw SHA-256 and size are compared with the plan.
   - The single `lambda-build-manifest.json` member (at most 4 MiB, read only) is hashed. Duplicate or oversized entries are not trusted. It is then parsed as strict JSON.
   - The manifest `target` runtime, architecture and handler must equal the intended configuration.
   - The manifest's allocation and declared layers must agree with the planned layers.
   - Conversion between hex and AWS `CodeSha256` is exact. Only the canonical 44-character standard base64 of 32 bytes is accepted.
2. **Three separate configurations.**
   - The **production baseline** is reported, together with `planned_changes` (baseline versus intended). Its existing layer produces the notice `BASELINE_LAYERS_REMOVED_BY_PLAN`, never an error.
   - The **intended** configuration is the plan.
   - The **observed candidate** must equal the intended configuration exactly.
3. **Joins.**
   - Account, region and function name come from the `FunctionArn` and `FunctionName`.
   - The ARN qualifier must match `Version` and the request's `Qualifier`.
   - Runtime, architectures, handler, package type, ordered layers, memory, timeout, ephemeral storage and the environment are compared.
   - The candidate's `CodeSha256` must equal the derived AWS form, and its `CodeSize` must equal the ZIP size.
   - The candidate must be `State Active` with `LastUpdateStatus Successful`.
   - In every observed function environment: AWS credential variables, a non-Haiku `COPILOT_ROUTER_PROVIDER`, unexpected names (unless allowed) and any `Environment.Error` are flagged.
4. **Provenance and freshness.**
   - Every fact is labelled `kind: SAVED_RESPONSE` with its own `observed_utc`, `age_seconds` and `freshness` (`WITHIN_MAX_AGE`, `STALE` or `FUTURE_TIMESTAMP`). It is never labelled "current".
   - Stale facts make the result `INCOMPLETE`. A timestamp more than 300 s in the future blocks.
   - The evaluation time records whether it was `SUPPLIED` or taken from `HOST_CLOCK`.
5. **Version and alias, under the alias strategy.**
   - The candidate `Version` must equal `candidate_version`.
   - The alias ARN identity must be correct and use a non-numeric alias qualifier, and the alias name must match.
   - `FunctionVersion` must be published, never `$LATEST`. In `pre_release` it must equal the rollback version; in `post_release` it must equal the candidate.
   - `AdditionalVersionWeights` must exactly equal the planned weights. Each weight must be finite and strictly between 0 and 1, the total must be below 1, and the primary version must not appear in them.
   - Revision IDs must be present for the alias, candidate and rollback. They must equal the planned values, and a missing planned alias revision is its own error.
6. **Rollback.**
   - The target must be a numeric, immutable version. `$LATEST` or an alias name gives `ROLLBACK_TARGET_NOT_IMMUTABLE`.
   - The saved record is required. Its identity must be the production function at that exact version, and its `CodeSha256` must match the plan.
   - It must be `Active`, with a matching revision.
   - It must differ from the candidate version and from the candidate code.
   - If the rollback depends on layers, a notice reports that layer availability is not verified.
   - With an alias strategy, a missing rollback **blocks** (`ROLLBACK_TARGET_MISSING`). With an unresolved strategy, it is reported as the unresolved decision `ROLLBACK_TARGET_UNRESOLVED`.
7. **No invented strategy.** `release_strategy: unresolved` yields `RELEASE_STRATEGY_UNRESOLVED`, so the status is `INCOMPLETE`, never consistent. An alias record supplied without a strategy is noted as not evaluated.
8. **Separate gates.**
   - `technical_status` covers technical consistency only.
   - `release_authorized` is always `false`.
   - `separate_gates` reports qualification, independent review and owner authorization as `NOT_SUPPLIED` or `REFERENCED_NOT_AUTHENTICATED`. A hash reference never changes the status.
   - The fixed limitation `HASH_AGREEMENT_DOES_NOT_AUTHENTICATE_APPROVAL` is always emitted.
9. **Sanitized output.**
   - Every finding is a fixed `{code, role, field}`, and the codes come from registered sets (an unregistered code raises).
   - Environment **values** are never printed, only names, and names outside `[A-Za-z_][A-Za-z0-9_]*` become `UNPRINTABLE_NAME`.
   - Provider strings are printed only if they are plain identifiers.
   - `Code.Location` (a presigned URL), `StateReason`, status reasons, `Role`, `Description` and `Environment.Error` messages are never echoed.

### Result statuses

| `technical_status` | Meaning |
|---|---|
| `BLOCKED` | At least one error |
| `INCOMPLETE` | No errors, but missing or stale facts, or unresolved decisions |
| `CONSISTENT_PENDING_EXTERNAL_GATES` | Every supplied join holds. Qualification, review and authorization are still external. |

### Fixed codes

| Category | Codes |
|---|---|
| Errors (49) | the `ERROR_CODES` constant in the script |
| Missing / stale | `ARTIFACT_FILE_NOT_VERIFIED`, `PRODUCTION_BASELINE_MISSING`, `CANDIDATE_RECORD_MISSING`, `ALIAS_RECORD_MISSING`, `FACT_STALE` |
| Decisions | `RELEASE_STRATEGY_UNRESOLVED`, `ROLLBACK_TARGET_UNRESOLVED` |
| Notices | the `NOTICE_CODES` constant in the script |
| Input | `INPUT_UNREADABLE`, `INPUT_NOT_JSON`, `INPUT_DUPLICATE_KEY`, `INPUT_NONFINITE_NUMBER`, `PLAN_INVALID`, `RECORD_INVALID`, `RECORD_DUPLICATE_ROLE`, `AS_OF_INVALID` |

## Limitations

- It checks saved responses only. It makes no live AWS observation and gives no proof of IAM permissions, atomic deployment, alias-update behaviour or successful rollback.
- Layer-version availability for a rollback target is not verifiable offline.
- **Fields not compared:** execution role, VPC, logging/tracing configuration, KMS key, reserved or provisioned concurrency, SnapStart, tags, `Description` and `ConfigSha256`. Under the no-model startup plan, the test function's role intentionally differs from production's, so binding the role is an open decision.
- Only the alias strategy has version/alias semantics. Other strategies, such as an in-place `$LATEST` update, are deliberately unsupported until a reviewed decision defines them.
- Paginated `ListVersionsByFunction` is not consumed. Version facts come from qualified `GetFunctionConfiguration` / `GetFunction` records.
- Freshness depends on the stated `observed_utc` provenance. The checker cannot authenticate who captured a record or when.
- Manifest checks read only the embedded manifest. The full-archive verification is the separate accepted artifact evidence.

## Validation (exact commands and results)

All commands were run from the worktree with the main repository's `.venv`, unless noted otherwise. `<scratch>` is the session scratchpad.

```powershell
# Focused tests (the repository-root conftest installs tests/offline_guard.py)
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B -m pytest tests/test_jev_release_preflight.py -q --tb=short -p no:cacheprovider --basetemp <scratch>\rp-bt3
#   92 passed, 1 existing warning (unknown asyncio_mode); offline guard: 0 outbound attempts intercepted
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B -m pytest tests/test_jev_release_preflight.py -q --tb=short -p no:cacheprovider --basetemp <scratch>\rp-bt311
#   existing Windows CPython 3.11.15: 92 passed; offline guard: 0 outbound attempts
# Guarded Ruff
& '...\python.exe' -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check --no-cache scripts/jev_release_preflight.py tests/test_jev_release_preflight.py
#   All checks passed!
& '...\python.exe' -B -c "...same guard..." format --check --no-cache scripts/jev_release_preflight.py tests/test_jev_release_preflight.py
#   2 files already formatted
git diff --check; git diff --cached --check   # clean
```

**Development history.** The first full run had 2 failures, both in a test assertion: the sentinel values `jev` / `invented` also occur inside legitimate schema and fixture names. The assertion was corrected to exact JSON-string matching; the checker was not loosened.

**The 92 cases cover:**
- the code-conversion vectors;
- a full alias pre-release join, and post-release targeting;
- an unresolved strategy against a separate test function;
- missing records and missing artifact;
- six artifact-identity failures, plus a duplicate manifest entry and size mismatch;
- layer contradictions in both directions;
- 13 candidate configuration, checksum, state and revision failures;
- five identity and request-join failures, and a candidate version mismatch;
- seven malformed-response shapes;
- 12 alias failures, including unexpected and invalid weights, a primary-version weight and revision gaps, plus exact planned weights;
- stale and future snapshots, and host-clock provenance;
- 11 rollback-binding failures;
- environment rules, with value non-disclosure checked on the CLI output;
- external gates that are referenced but not authenticated;
- 15 input-contract rejections;
- code registration;
- static checks for no AWS, network, subprocess or write paths;
- a CLI run that is read-only over its inputs.

**Read-only run against the real accepted artifact.** No AWS records were supplied. A scratch plan bound the accepted values: account `981265949354`, `financial-copilot`, 512 / 30 / 512, no layers, unresolved strategy.

```
python -B -c "from tests.offline_guard import install; install(); from scripts.jev_release_preflight import main; raise SystemExit(main())" --plan <scratch>\rp-real\plan.json --artifact "C:\Projects\AWS Project\dependency-acquisition\2026-10-05-9bf00d1-artifact\build\candidate.zip" --as-of 2026-10-06T20:00:00Z
```

| Item | Result |
|---|---|
| Exit code | 1 |
| `technical_status` | `INCOMPLETE` |
| `artifact.verification` | `FILE_HASHED_MANIFEST_READ` |
| SHA-256 | `46ace5c38c4cf24e131c01437419aa56244280e2e570a777ae2a0d5ff7cabed7` |
| Manifest | `b30d5edf1cfc76b65be276e3e13a9d291c0f82235186c5412ddb51d0b68a73c8` |
| AWS `CodeSha256` form | `Rqzlw4xM8k4THAFDdBmqViRCgOLlcKd3rioNX/fKvtc=` |
| Manifest allocation | `complete-function-no-layers`, with 0 declared layers |
| Errors | 0 |
| Missing facts | production baseline and candidate |
| Unresolved decisions | strategy and rollback |

This is expected without saved AWS responses. The ZIP hash was unchanged before and after the run.

## Protected evidence preservation

- **Main worktree.** HEAD is still `9bf00d1`. The two pre-existing unstaged document modifications are Codex-owned; I did not edit them, and they continue to change only through Codex. The untracked-entry count is still 25. No stash, reset, switch or staging was done.
- **Unchanged after this task:**
  - accepted ZIP `46ace5c3…`;
  - artifact receipt `63c767e2…` and completion index `cde3d056…`;
  - runtime receipt `95cad6ed…`;
  - packaging-preparation preflight `c82e55eb…`;
  - Claude review reports `cee98d21…`, `4d24abaa…`, `03ce24d2…`, `7afdfedc…`, `c36ca926…` and `abb1fa34…` (artifact review).
- **Codex's in-progress records.** The `jev-startup-*` continuation directories were not opened as evidence. They appeared only as file names in a filename search for saved-response field names.
- **Not performed:**
  - AWS or provider calls;
  - uploads, installs or builds;
  - container runs;
  - extracting or executing the artifact;
  - push or merge.

## Remaining decisions and integration prerequisites

1. **Release strategy.** This is still unresolved. The README records production as `$LATEST` only, with no alias. An alias strategy would first need an authorized publication of the current production code as an immutable version, so that a numeric rollback target exists. That is an AWS mutation outside this task.
2. **Rollback target.** There is no immutable previous version yet, for the same reason.
3. **Saved-record adapter.** Codex's sealed startup records must be wrapped as `jev-saved-aws-response-v1` records, keeping the raw AWS response, request and `observed_utc` unmodified. The wrapper's own hash becomes `input_sha256`. Whether to add a reviewed adapter, or have the capture step emit this schema directly, is an integration decision.
4. **Production baseline record.** This needs a separately authorized, read-only `GetFunction` capture. Historical README facts are not saved responses.
5. **Environment expectations.** The owner must state the required application variables and their expectations. For example, `S3_BUCKET_NAME` and the `FAISS_*` keys need values for RAG, while the logs-only startup function deliberately has none. The evaluation token is compared by SHA-256 only.
6. **Memory and timeout.** The intended 512 MiB / 30 s mirrors the observed configuration. Any change should follow the measured startup evidence.
7. **Fields to bind later.** Whether to bind the execution role, logging, concurrency and similar fields is open; see Limitations.
8. **Integration.** Merge this branch into the integration worktree only after Codex's independent review, then run the final integrated review.
