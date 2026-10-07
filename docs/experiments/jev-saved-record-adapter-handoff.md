# Offline saved-record adapter handoff

Codex implementation and self-review, pending Claude independent review. Base is the accepted integration commit `aeee2e1597f06f365a789abefbda65368c81fe84`. This increment is isolated on `phase0/jev-saved-record-adapter` in `C:\Projects\AWS Project\worktrees\jev-saved-record-adapter`; it is not merged or pushed. Final commit and raw working-copy versus committed-blob hashes are recorded in the private completion index and chat delivery.

Only three repository paths are added: `scripts/jev_saved_record_adapter.py`, `tests/test_jev_saved_record_adapter.py` and this handoff. The accepted checker/tests, application, dependencies, packaging, shared documents and all other worktrees are unchanged.

## Accepted context and preserved review

Claude's actual integration report is `C:\Projects\AWS Project\worktrees\jev-integration\docs\experiments\jev-integration-claude-final-review.md` (the supplied `jev-integration-claude-final-review\.md` spelling did not match the actual file). Its raw SHA-256 is `d8db1009c3b1ef6a71fc8a31aa3663e1e13a6260ed98363909532ef371e175ab`, verified before worktree creation. An exact private byte copy and preservation hashes retain this uncommitted report.

N-1 through N-4 remain nonblocking and were not corrected here. Preserve the N-4 assurance limit: Claude independently verified the 233 readable review-folder files; the inaccessible 1,004 files rely on Codex's recorded preservation checks. This task changes no Windows permissions or historical receipt/document. Startup C-1 remains an existing nonblocking labelling issue; no sealed record was rewritten.

## Supported source and verified closure

The only supported source is **`function-ready.json`**, from the accepted startup continuation. The inspected source recipe is pinned to exact raw file hashes:

| Capture source | Raw-file SHA-256 |
|---|---|
| `runtime.py` | `5de6bf0643143902994f6d580577ddf8aa9df7d1ca24c69f9e5019be384c228e` |
| `common.py` | `b55047150fa0f49ee68079bd5e50cadf332b208813ad51d0d8cb6187c3c52feb` |

The adapter reads these sources as bytes only. It never imports or executes them. A different recipe is unsupported, with no CLI override.

Verification order:

1. Require caller-supplied expected completion-index and source SHA-256 values. Hash the raw index before parsing its `jev-lambda-startup-continuation-index-v1` declaration.
2. Verify each consumed raw file against the index before use. Verify `runtime-source-bindings.json` joins for the two capture sources and `context.json`; check the fixed source recipe hashes.
3. Strictly parse JSON/JSONL using the accepted checker utilities. Bound reads to 8 MiB per file and reject nonregular files, links and resolved-path escapes.
4. Pair the sequential journal's BEFORE/terminal rows. Locate the unique successful `create_function`, then the successful `get_function_configuration` readiness calls before the isolation `get_policy` boundary. Require valid recorded timestamps, ordering, HTTP status, zero retries and unique request IDs for readiness calls.
5. Join each call by ordinal to its indexed `function-readiness-NN.json`. Check projection shape, request identity and that only the last readiness capture is Active/Successful. Reject excess indexed readiness captures. Require the final projection's original bytes to equal `function-ready.json` exactly: two filenames identify the same capture, not independent origins.
6. Preserve the projection's 27 fields and values without adding or deleting response fields. Form the candidate-only v2 envelope, then reuse the current checker's record/type/checksum/identity/common-environment safety validators. No release plan or candidate-specific owner environment expectations are constructed.

`function-created.json` is CreateFunction output and cannot be relabelled GetFunctionConfiguration. Intermediate readiness files are not selectable in this bounded adapter. `invoke-N-observed.json` is invocation metadata, not function configuration. These sources return explicit `UNSUPPORTED`. Missing or contradictory evidence produces fixed-code `INCOMPLETE` or `REJECTED` results, never a guessed wrapper.

## Output and byte contract

API: `adapt(evidence_dir, index_sha256, source_sha256, source="function-ready.json")`.

CLI:

```text
python -B -m scripts.jev_saved_record_adapter --evidence-dir DIRECTORY --index-sha256 EXPECTED_INDEX_HASH --source-sha256 EXPECTED_SOURCE_HASH [--source function-ready.json] [--emit-record]
```

No files are written by the adapter. Default stdout is metadata only. `--emit-record` explicitly adds the captured response record for private storage; it may contain captured values and must not be treated as sanitized diagnostics. Errors on stderr contain only the registered code, fixed schema/status and `release_authorized:false`. Exit 0 means conversion, exit 1 means unsupported/incomplete evidence, and exit 2 means rejected input.

The result schema is `jev-saved-record-adapter-result-v1`: status, record SHA-256, companion provenance/SHA-256 and `release_authorized:false`, plus `record` when requested. The checker receives only the separately serialized `record`, not this result wrapper or companion.

The record is the unchanged strict `jev-saved-aws-response-v2` envelope with six keys: schema, candidate role, GetFunctionConfiguration operation, recovered FunctionName request, journal AFTER UTC and preserved response. No baseline, aliases, published versions or rollback targets are emitted.

The separate `jev-startup-projection-provenance-v1` companion binds the canonical record hash, all consumed raw-file hashes, recipe/callsite, shared capture filename, exact journal line references, request ID, original BEFORE/AFTER timestamp strings and explicit provenance limitations. It is not injected into the strict record envelope.

Canonical bytes for records, companions and JSON outputs use the accepted checker's serialization: sorted keys, compact separators, ASCII JSON escaping, finite numbers, one trailing LF, encoded as UTF-8. Hashes are SHA-256 of these exact bytes. Raw evidence file hashes do not normalize line endings.

## Provenance limits

- The response is a **selected-field projection**, not a verbatim AWS response. Discarded ResponseMetadata is never restored.
- The journal omits request arguments. FunctionName is recovered from the exact hash-bound callsite and context, joined to the projection identity. This is labelled `HASH_BOUND_RUNTIME_CALLSITE_AND_CONTEXT_NOT_RAW_REQUEST_LOG`, not a raw-request capture.
- `observed_utc` preserves the journal AFTER timestamp, explicitly labelled as the helper's post-return journal time, not a provider observation timestamp or file timestamp.
- Projection nulls are preserved. Because `config.get` produced them, original absent-versus-null status remains unknown. Fields omitted by the original recipe remain omitted.
- Hash agreement binds artifacts; it does not authenticate capture authorship, historical execution, approval or owner authorization. Code/history/journal ordering is not an independent proof that those exact bytes executed.
- Conversion is not a full release-preflight pass. Owner environment expectations, freshness, artifact/plan joins and all other roles remain separate. `PYTHON_DOTENV_DISABLED` remains an owner allow-unlisted/expectation decision; no new choice was inferred here.

## Validation and real read-only check

Actual pytest/read-only-check interpreter: **CPython 3.11.15**, `C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe`. Guarded Ruff used the existing main interpreter, **CPython 3.13.12**.

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B -m pytest tests/test_jev_saved_record_adapter.py tests/test_jev_release_preflight.py -q --tb=short -p no:cacheprovider --basetemp 'C:\Projects\AWS Project\dependency-acquisition\2026-10-06-saved-record-adapter-671c9b40\pytest-final'
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check --no-cache scripts/jev_saved_record_adapter.py tests/test_jev_saved_record_adapter.py
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check --no-cache scripts/jev_saved_record_adapter.py tests/test_jev_saved_record_adapter.py
git diff --cached --check
```

**186 passed in 1.93 s**: 48 new adapter cases and 138 relevant checker regressions. Zero outbound attempts. Lint/format passed. The initial 43-case run also passed; subsequent cases cover dynamic side-effect monitoring, malformed hash arguments, nonregular files and earlier capture identity. Static inspection and an active audit probe found no adapter mutation/network/subprocess path; this is reviewed-source evidence, not a universal Python sandbox guarantee.

Synthetic unit fixtures use invented records and capture bytes. They replace the two recipe digest pins with fixture digests using pytest monkeypatch; production exposes no such override. The separate real check exercises the unchanged production source pins and actual sealed closure.

Read-only real check, without executing operator scripts, creates separate private derived outputs under `C:\Projects\AWS Project\dependency-acquisition\2026-10-06-saved-record-adapter-671c9b40\real-readonly`:

| Output | Exact SHA-256 |
|---|---|
| `candidate-record.json` | `792711101c6e808b86db2baaf95da213594f60a2816fdef74cb6b304dfee091e` |
| `projection-provenance.json` | `a8c7ff9dd22fef96d7df6d8d347d67c16ffbf364ee73d11caa9b92ed3ef3c8fa` |
| `technical-check-receipt.json` | `dc1a2ec995a48b698969220af3b50b61facd55cce5d7c9b85304806b55879f4f` |

The actual final readiness source is honestly consumable by the current v2 record/type/identity/common-safety contract. Its source SHA-256 is `990c364d36889df2d04e38938a864ee88f26316618a6bd4090ee03f4e3519c7e`; its shared readiness-03 capture has the same raw bytes. Operation is GetFunctionConfiguration; request is the isolated task FunctionName; timestamp is journal line 121 AFTER UTC `2026-10-06T19:55:20.525180+00:00`, request ID `06b14797-8cfb-472d-b7ae-e00e2c11b71d`. No full release plan or other role was assembled or evaluated.

## Preservation and Claude review scope

Private task receipts distinguish raw working-copy hashes, normalized LF hashes before commit and actual committed-blob hashes after commit. Interpreter versions are explicit. Before/after snapshots protect 197 main files, 172 source files, 174 integration files including the uncommitted review, 85 sealed startup files and the accepted ZIP `46ace5c38c4cf24e131c01437419aa56244280e2e570a777ae2a0d5ff7cabed7`. Main, source and integration HEAD/status remain unchanged. Old reports, receipts, shared documents and sealed originals are preserved.

**Focused Claude independent review:** inspect the narrow pinned recipe and ordinal/shared-capture joins, recovered-request and journal-time honesty, missing/null handling, raw-versus-canonical hashes, strict checker interoperability, sanitized failure paths, synthetic test mocks versus the unmodified real check, read-only behavior and preservation. This is a new acceptance scope; do not infer it from the prior integration review. Stop before integrating this increment.

No AWS/network/provider call, IAM/resource change, upload, inference, native/runtime rerun, artifact rebuild, installation, main merge, push, sealed-record rewrite, permissions change or Reviewer Protocol v2 change occurred. The adapter does not authorize release or establish deployment readiness.
