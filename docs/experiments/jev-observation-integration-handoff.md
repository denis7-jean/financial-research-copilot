# Isolated observation integration handoff

Prepared by Codex on 2026-10-07. Local integration and offline validation only; **pending Claude final independent integration review**. No implementation bytes were edited, and no live capture, release or deployment is authorized by these results.

## Exact integration and acceptance scope

New worktree: `C:\Projects\AWS Project\worktrees\jev-observation-integration`. New branch: `phase0/jev-observation-integration`. Both branch and directory were absent before creation. Integration base: `aeee2e1597f06f365a789abefbda65368c81fe84`. Main and the previous integration worktree were not merged or changed.

The acceptance reports were read and verified as raw files before merging:

| Accepted input | Uncommitted report in its implementation worktree | Raw report SHA-256 |
| --- | --- | --- |
| Adapter `e88ada373d0e56c85d3f25e7bc26cc6b06d8d422` | `docs/experiments/jev-saved-record-adapter-claude-review.md` | `cafd592d2c143f16208bd9874eb4f9a42c11edbbd8bf565279451f8d2d8ef953` |
| Capture `e6aa45e7550ceb32316a580bac4e64412b1cddaa` | `docs/experiments/jev-release-observation-capture-codex-d123-review-20261007-85030bae.md` | `87e00ffbd3b957d248223faa14a8793db05910e0ffb621021145867e96342caf` |

The adapter is a direct child of the integration base. The capture history is the direct-parent chain `aeee2e1` -> `fa54782c150d0934fb8443e50267657ef3a7b135` -> `5c0461c3ea57079f7133d1ebcd157289a3ab4790` -> `e6aa45e7550ceb32316a580bac4e64412b1cddaa`. Each branch's total delta from the base adds its three authorized paths only. Report filenames were not treated as proof of acceptance; the actual dispositions and subject bindings were inspected.

Explicit non-fast-forward merges, in order, completed without conflicts:

| Merge | First parent | Second parent |
| --- | --- | --- |
| `e2d5da74b8e52c21f2914efa23a8375efb913a84` | `aeee2e1597f06f365a789abefbda65368c81fe84` | `e88ada373d0e56c85d3f25e7bc26cc6b06d8d422` |
| `5796268a136d39335a20261353b62b17ee9059f8` | `e2d5da74b8e52c21f2914efa23a8375efb913a84` | `e6aa45e7550ceb32316a580bac4e64412b1cddaa` |

The second merge is the validated implementation checkpoint. The following documentation-only commit adds this handoff; its final commit/hash is recorded in the private completion receipt rather than creating a self-referential document binding.

## Exact path and byte inventory

Base-to-merge delta is exactly the following six additions. The final delta also adds this handoff, and nothing else. No uncommitted review report was imported into Git.

| Added path | Purpose | SHA-256 of raw committed Git blob |
| --- | --- | --- |
| `scripts/jev_saved_record_adapter.py` | Read-only historical projection adapter and separate provenance companion | `2b4774777a6fa29e215d1416e0c61d32839baa6efa8855586a3de621991bff11` |
| `tests/test_jev_saved_record_adapter.py` | 48 synthetic adapter cases | `2eb66c3d7c87b454f6ea1fddbe5c4f6e761c416cb6797299d5e8200c0e7e3df8` |
| `docs/experiments/jev-saved-record-adapter-handoff.md` | Accepted adapter implementation handoff, preserved historically | `5f16ea1c1d39ce59fcf57f937cf749dd616493d23545c9fd07be812af3916df0` |
| `scripts/jev_release_observation_capture.py` | Opt-in bounded observation helper including accepted OC-1/D1-D3 fixes | `b5c48de053667982c5b0fde4e95ecedc5352cef2c0eadc28e4e033a64591878f` |
| `tests/test_jev_release_observation_capture.py` | 164 synthetic capture cases | `3425694ad5c56ff30d67b8f99d059507847c5f536eaa96de43d3a8e7386867f8` |
| `docs/experiments/jev-release-observation-capture-handoff.md` | Accepted capture implementation/correction handoff | `e476365bb75944dee9e377231ab255f54ae294add063c01afeef08b01a982e62` |

Committed blobs were obtained as raw bytes using Python `subprocess.check_output` of `git show COMMIT:PATH`, not a PowerShell text pipeline. All six new checkout files use CRLF. Their complete raw working-copy hashes, CRLF counts and equality after CRLF-to-LF normalization are separately recorded in `integrated-5796268a.json` and the final integrated binding receipt. This is a checkout line-ending difference only; no bytes were edited to normalize it.

The existing checker remains bound to `87f2a1d6d317352a4326909cc7787a80212a0a8f3ed363decfdb4c29b39c2f47`; its tests remain `21698346ae923d629153a4f9bb0b3c929dd74083d4e6f8866522ffa3736bfd42`. Application, packaging, dependency declarations and Reviewer Protocol v2 blobs are unchanged because the complete tree delta is restricted to these additions.

## Reproduced offline validation

Tests and interoperability probes used **CPython 3.11.15**, `C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe`. Guarded Ruff used **CPython 3.13.12**, `C:\Projects\AWS Project\main\.venv\Scripts\python.exe`. No tool installation or environment upgrade occurred.

From the new worktree:

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B -m pytest tests/test_jev_release_preflight.py tests/test_jev_saved_record_adapter.py tests/test_jev_release_observation_capture.py -q --tb=short -p no:cacheprovider --basetemp 'C:\Projects\AWS Project\dependency-acquisition\2026-10-07-observation-integration-92c5dbee\pytest-311'
# 350 passed in 3.64s; offline guard: 0 outbound attempts intercepted, none sent.
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check --no-cache scripts/jev_release_preflight.py scripts/jev_saved_record_adapter.py scripts/jev_release_observation_capture.py tests/test_jev_release_preflight.py tests/test_jev_saved_record_adapter.py tests/test_jev_release_observation_capture.py
# All checks passed.
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check --no-cache scripts/jev_release_preflight.py scripts/jev_saved_record_adapter.py scripts/jev_release_observation_capture.py tests/test_jev_release_preflight.py tests/test_jev_saved_record_adapter.py tests/test_jev_release_observation_capture.py
# 6 files already formatted.
git -c safe.directory='C:/Projects/AWS Project/worktrees/jev-observation-integration' diff --check aeee2e1597f06f365a789abefbda65368c81fe84 HEAD
# Clean; also rechecked after adding this handoff.
```

Composition: 138 checker + 48 adapter + 164 capture cases. The guard stayed active; no live test flags were used. Validation logs and exact command arguments are retained in the private receipt directory. No broad regressions, historical population replay, native execution, artifact build or AWS call was performed.

The additional guarded private probe is reproducible with:

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\2026-10-07-observation-integration-92c5dbee\interoperability.py'
```

It uses an exclusive invented-capture directory, so repeat execution requires a new private fixture output path; never reuse or remove a real capture claim. It validates the real prepared plan only, captures invented responses with injected fake clients, and runs the integrated adapter against immutable evidence in memory. The historical phase has an additional audit hook rejecting writes, subprocesses and network activity. No old operator/evidence-producing script is executed.

Results:

- A baseline-only invented capture makes exactly two **fake** service calls, returns COMPLETE and has a verified index hash. Its v2 record reaches the unchanged checker. Missing artifact/candidate/rollback facts and unresolved strategy remain **INCOMPLETE**, with `release_authorized:false` and no checker errors. This does not represent current AWS state.
- The actual prepared plan, raw SHA-256 `e8e4864fc55cccf863671258d419988e1dcbb4da8fd9a7bfb6a6dc1e5b0026cf`, returns exit 0 / PLAN_VALID_NO_CALLS_MADE. Only STS GetCallerIdentity and Lambda GetFunctionConfiguration for financial-copilot, $LATEST are planned. The injected forbidden client factory and patched SDK constructors were never reached. The proposed sensitive output directory remains nonexistent.
- The integrated adapter reproduces the existing historical candidate record `792711101c6e808b86db2baaf95da213594f60a2816fdef74cb6b304dfee091e` and provenance `a8c7ff9dd22fef96d7df6d8d347d67c16ffbf364ee73d11caa9b92ed3ef3c8fa` byte-for-byte. The prior technical receipt `dc1a2ec995a48b698969220af3b50b61facd55cce5d7c9b85304806b55879f4f` is unchanged. No new historical derived record is written and no release plan using that historical candidate is constructed.
- All probes have zero real SDK constructions and zero outbound attempts. An initial scratch assertion compared equivalent ISO timestamp spellings as unequal strings; it was corrected to compare parsed times and the actual timing-field join. Its script, note and invented files were retained separately. No accepted source changed and no application defect was inferred from that scratch error.

## Interoperability and operational limits

The adapter emits only a candidate v2 envelope from the supported selected-field projection, plus a separate provenance companion. It does not restore ResponseMetadata, relabel CreateFunction, authenticate the capture or manufacture missing values. Its `observed_utc` is the historical journal **AFTER** time. The capture helper uses the **request-start** time as `observed_utc` and retains response-received time separately. These are different disclosed timestamp conventions, not identical freshness semantics. Historical candidate evidence is not a current observation.

The capture's COMPLETE status describes its bounded capture only. An index whose publication/close failed can contain parseable internal COMPLETE bytes; those are unconfirmed. Completion requires the successful returned status and matching index hash. Console fallback cannot confirm completion. This integration adds no consumer or recovery framework.

Planned service-call limits and retries do not bound SDK credential-provider acquisition/refresh/process activity. Permitted credential-provider and endpoint flow, suitable private output permissions/retention, dated API pricing and explicit owner live authorization remain operational prerequisites. No real credentials were inspected. Outside-Git placement is not a claim of restrictive ACLs. Hashes and opt-in flags do not authenticate approvals.

Release strategy, alias/rollback facts and further observations remain separate release requirements; they are not required to validate the prepared baseline-only plan. Missing release facts still fail to establish readiness. No current production configuration was inferred from README or startup evidence.

## Preservation and private receipts

Private receipt directory: `C:\Projects\AWS Project\dependency-acquisition\2026-10-07-observation-integration-92c5dbee`.

| Receipt | Raw SHA-256 |
| --- | --- |
| `input-verification.json` | `92504c8a01b785849e507574e2fc76a20f7171e0b14c10cbe6929871b0c0caab` |
| `integrated-5796268a.json` | `57e54f7757dd0d40d51327b54857794f17e73b1410f22717a1d7d8d87fbde1d6` |
| `validation-commands.json` | `254a09ab087c045323270307e2286eb82dc35d1a5cb786ff98c37b49fb4d8f73` |
| `interoperability-results.json` | `a11519966a0c183ec2d1cf3c55bd80d9e589352a8e4945bdb647cdbbbf6e2f99` |
| `preservation-before.json` and `preservation-after.json` | `7620c31ec3990c10387e8abcd789186a4ab03833f747a23c8f8f2a27f2f8bcd5` each |
| `rv2-preservation-before.json` and `rv2-preservation-after.json` | `7f344b65c85c230a76024e6b5bab634708040072e11e4b618c5d255c52c0913e` each |

The before/after metadata inventories cover 197 main files, 174 old integration files, 172 preflight files, 177 adapter files and 179 capture files, with HEAD/branch/status joins for all five existing worktrees. Main remains at `9bf00d13dd9c83a635719dfd2acb7798c353866c`, with its two unstaged shared-document additions and 28 top-level untracked status entries unchanged. All implementation review reports remain uncommitted and unchanged. The original integration's Claude report remains outside this branch.

Additional raw-byte inventories cover all 85 sealed startup files, 1,095 prior adapter evidence/scratch files, both prepared plan/receipt files, 251 files under the actual shared `C:\Projects\AWS Project\heldout-external` directory, and the accepted ZIP `46ace5c38c4cf24e131c01437419aa56244280e2e570a777ae2a0d5ff7cabed7`. The initial generic inventory's nonexistent main/heldout-external path had no files; the separate rv2 inventory explicitly covers the actual shared directory. This task had no inaccessible files in its enumerated preservation scope and changed no permissions. That observation does not revise Claude's historical limitation: his review independently checked readable review-folder files; its inaccessible remainder relies on Codex's recorded preservation checks. Historical receipts are unchanged.

Final commit, handoff committed/raw hashes, final seven-path delta, final protected-state comparison, exact private helper/log hashes and actual new-worktree clean status are bound in the completion index written after the handoff commit.

## Focused Claude final integration review

Verify the exact base, merge parents, six accepted blobs and unchanged checker; the seventh path is this handoff only. Reproduce the three focused suites and inspect the invented baseline-to-checker and historical in-memory adapter bindings. Check timestamp-convention disclosure, INCOMPLETE/false-authorization results, the unconfirmed-index limitation and preservation inventories. This is an integration seam review; it does not reopen accepted implementation limitations or authorize baseline capture.

Stop after local integration. No main merge, push, AWS/network call, credential access, live capture, installation, container, artifact rebuild, upload, resource/layer/alias change, inference or Reviewer Protocol v2/evidence change occurred.
