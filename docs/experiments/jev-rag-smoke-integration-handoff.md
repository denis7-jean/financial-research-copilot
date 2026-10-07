# Isolated RAG smoke integration — independent review handoff

2026-10-07. Local integration and offline validation only. **Awaiting Claude's final independent integration review.** This combines two separately accepted scopes without certifying full contract enforcement or authorizing a run, build, qualification or deployment.

Worktree: `C:\Projects\AWS Project\worktrees\jev-rag-smoke-integration`.
Branch: `phase0/jev-rag-smoke-integration`.
Exact base: `274e283e353261c4d50b0d4f18ee97366d80d7ef`.
Tested integrated source commit: `cdb8f026d5717137da96e700142fee3b8957419d`.
The final handoff-only commit and its raw blob binding are recorded in the private completion receipt; no implementation bytes change after this tested source commit.

## Accepted subjects and merge history

| Scope | Exact accepted subject | Independent report / raw SHA-256 |
|---|---|---|
| Offline controls, including focused F1/F2 correction | `2b4f507214e3d96816cad50118360c6eb89ce990` | Controls worktree `docs/experiments/jev-rag-smoke-controls-claude-f1f2-delta-review.md`: `6f554d2d3938710bfe53a314519a4eca0923376de7c2bcca8426a47ceaaf4fb1` |
| Declarative contract and schema-v2 scenarios | `4e2addd5a66ad5b43765c11a688d4b4459aa95a7` | Acceptance worktree `docs/experiments/jev-rag-smoke-acceptance-codex-delta-review-20261007-6f842a31.md`: `0c5a9510d730b6a855cceae2b225b2ef0e037bb5d41966dccd1717604ea6fce6` |

Both reports were read, their raw hashes verified, and their ACCEPTED verdicts checked against these exact subjects before creation of the new worktree. The implementation history is base -> `4103f1e2c05abd6360a1ac793bca3a6e139c801e` -> accepted correction. The contract history is base -> `e6fc6cd176f3bb8c411fd613fc82065103aabaf0` -> accepted correction. Reports remain uncommitted in their original locations; none was imported.

| Merge | Ordered parents |
|---|---|
| Implementation first: `e3858bdda2d1271e056f10acf3f15de2a757e2ce` | `274e283e353261c4d50b0d4f18ee97366d80d7ef`, `2b4f507214e3d96816cad50118360c6eb89ce990` |
| Contract second: `cdb8f026d5717137da96e700142fee3b8957419d` | `e3858bdda2d1271e056f10acf3f15de2a757e2ce`, `4e2addd5a66ad5b43765c11a688d4b4459aa95a7` |

Both merges explicitly used `--no-ff`; no conflicts occurred. Hooks were disabled for these local Git mutation commands with a per-command setting, not a global configuration change. The branch/directory were absent before creation. Existing worktrees were not switched, reset, merged or edited.

## Exact union and byte bindings

The source merge has exactly **nine implementation paths plus two contract/fixture additions**. This document is the twelfth base-to-final path. All eleven merged Git blobs are byte-identical to their accepted source subjects. No accepted source, tests, contract or fixtures were edited.

| Path / purpose | Integrated committed-blob SHA-256 | Raw integration working-copy SHA-256 |
|---|---|---|
| `app/agents/orchestrator.py` — explicit injected `process_smoke` | `637e3c9318e85f36f01a5b41a4867c3124868aba9d78a14bf8beeb97e7074024` | `d3c42f58da7a6c35b70d26cbefe923d93b13165ac9e930a0afee5f8a7dea7fe5` |
| `app/agents/router.py` — strict opt-in Haiku route gate | `fa7469faac87519764491458e3536d062192e62460abf83b2963567dd0868596` | `441e0f89f06f6a7ec50ae324f0237ce308561f7d8291fa29eec83e25f8d2b113` |
| `app/services/bedrock_client.py` — bounded smoke generation seam | `f0b66ce108c65d805782c388b01f0039002cc5839da4a0dcf6d31ab711362d4c` | `de2696807ab6bc8ad73f96f89559a38cd158d55fa86f6226432d6ce44a408f8c` |
| `app/services/rag_smoke_policy.py` — v2 policy, reservations, claims, hooks and gates | `cdeb1fbd9d884eb00ae76535c58fa852a8e13b0702dca41056395008b5ebdff2` | `430a454217e4948801c907705f0da2456accc5aaa33611d2db7db7b2bdf79c40` |
| `app/services/retriever.py` — conditional object/metadata/native-adapter/search gates | `10f2a9071bb519b9508399a5d40d12afb4360821944aa0cea24ac696cf10a8ae` | `3abe3b3392f206f1326856988fc8f622cc1766f044220d94fae869444db7180c` |
| `docs/experiments/jev-rag-smoke-controls-handoff.md` — preserved implementation history | `d79d54379257d4e90cbca54262688777f58da1adbf572915c07d109bd418a277` | `b6b9d01c223e7695c5a86986a2871f928df61815593bc9ae606ad2848fcfbc0e` |
| `scripts/lambda_package.py` — explicit policy-module source inclusion | `355fcdf5cbbfc1942f204b02a899a19c41ad1c8a855d2d0f341dff47daf71342` | `b6f38a78bf808993ef1d1b854816188efab5c7207cb8c00f842ce2f757516877` |
| `tests/test_jev_rag_smoke.py` — 86 invented smoke cases | `9d840db7efc0726c65151b148a4fb1a1126e78a02018cfe4aab236d7e9059c7f` | `adf136f02a2e5529ead1761750ca4029db801f8c9a9742945a8ea095f6d68ba2` |
| `tests/test_lambda_package.py` — layout and closure regressions | `e889f58bcd331d6db480dd6f9bb9595ce5fc361d06f9e44c25dc33dbf4ac4eec` | `b1e28d31831693f00d20ec26b582d215f6f6b323129ce2e7fd72761f5cbe4c7b` |
| `docs/experiments/jev-rag-smoke-acceptance.md` — independent normative smoke acceptance contract | `bddb8a4b107c617c77d6f526edf1de402dfb96af8b0b331a856f3d31985b8c32` | `194bff3e77b9447ea25e09ed417c1040c1669e35e61e334e2d7e4b1e5d02f15c` |
| `tests/fixtures/jev_rag_smoke_acceptance.json` — 48 declarative v2 scenarios | `2a50608bfcff4fc6188de0132b212d957b5d5166315d966a5d608cb15843324c` | `f22bec1479e5d33f176c2a0f717b833121ea3c691d803d3ee67533db84d56360` |

The integration worktree checks out these eleven files with CRLF. The receipt records byte sizes and CRLF counts; their LF representation equals the accepted blobs. This is a reported checkout distinction, not a rewrite of protected worktree files or a change to canonical hashing requirements. Raw Git bytes were captured with Python `subprocess.check_output`, without PowerShell text-pipeline transformations.

Checker, adapter and capture source/tests are unchanged from the integration base, as are runtime requirements, wheel lock and layer allocation. Reviewer Protocol v2 has no source/binding change in the merged delta. Production still defaults to Haiku; application Jev live/shadow restrictions and ordinary answer behavior remain unchanged. `process_smoke` is an injected Python seam, not a live Lambda handler or environment-enabled production route.

## Offline validation

Actual interpreter: **Python 3.11.15**, `C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe`. Ruff: **0.15.14**.
Private receipt root: `C:\Projects\AWS Project\dependency-acquisition\rag-smoke-integration-20261007-7a94c18e`.

The inspected private bootstrap installs the existing network guard and injects invented pure-Python NumPy/FAISS substitutes before application imports. Fake vector/search/index operations run no native modules or financial index deserialization. All runs report **zero outbound attempts**; `.env` loading is disabled and only fake SDK credentials are used. Synthetic SDK transports and fake client responses are not AWS or provider calls.

| Suite | Committed-byte export result |
|---|---|
| RAG smoke | 86 passed |
| Router, agents, Jev candidate, observability, errors, isolated live-smoke tests | 234 passed (52 + 32 + 66 + 12 + 33 + 39) |
| Existing API regressions | 44 passed |
| Complete packaging test file | 126 passed, 1 skipped |
| Release preflight / saved-record adapter / observation capture | 138 / 48 / 164 passed |
| Total | **840 passed, 1 skipped**, no failures |

The packaging skip is **Windows symlink privilege unavailable**; no permission change was made. Synthetic reparse checks still run. The warning is the existing `asyncio_mode` configuration with plugin autoload disabled; no selected tests require the async plugin.

The corresponding worktree run is **839 passed, 1 failed, 1 skipped**. Its only failure is `test_operational_lock_preserves_reviewed_inner_bytes`:

- Raw unchanged CRLF lock: `226aafe6c2aab570bebb7d495e214422206fdb7e97058875ac17b069d54d38ab`.
- Canonical/raw committed lock: `01fe426a5e28b274c4cc1bdb3ef6423203564b43ded257149bec35b7879c5bb8`.
- Committed lock is identical to the integration base. No lock bytes, hash checks, requirements or global Git line-ending settings were changed.

A fresh export of **141 raw committed files** permits canonical-byte tests without normalizing any protected file. The final export has an explicitly invented empty `.git` marker directory: one unchanged capture test requires its own source root to be recognized as a repository. This is test-environment setup, not Git initialization, a live capture or a validator bypass.

Earlier results are retained, not replaced:

- Initial worktree run: 828 passed, 1 failed, 1 skipped, 11 API setup errors. The inherited private fake lacked `numpy.stack`; a new scratch runner supplies the inspected row-stacking behavior. No accepted test/application changes were made.
- First raw export: 839 passed, 1 failed, 1 skipped. Canonical packaging passed; the capture source-root repository test failed because that first export had no `.git` marker. A second exclusive export supplies the missing environment premise and passes. Its files remain the same committed bytes.

Strict parsing of the integrated schema-v2 fixture confirms all **48** unique scenarios, **149** per-request accounting entries, all **13** clause references and declared vocabulary joins. Negative controls reject duplicate keys, NaN/Infinity and float overflow. PASS_STRUCTURAL requires confirmed complete evidence; incomplete outcomes remain RESULT_NOT_ESTABLISHED. **These are declarative checks, not acceptance-engine execution or proof of code conformance.**

Scoped Ruff `check --no-cache` passes all eight changed Python files. `format --check --no-cache` flags router, bedrock_client and retriever; five files are already formatted. Bedrock/retriever also fail formatting at the integration base. Router is format-clean at that base but its drift is already present in the accepted implementation blob. No accepted or unrelated code was reformatted. Git whitespace checks pass on the merge range and handoff-only staged delta.

### Exact final test command

For the working-copy run set `INTEGRATION_TEST_ROOT` to the integration worktree and use `pytest-worktree-v2` / `worktree-v2-results.xml`. For the committed-byte run:

```powershell
$env:INTEGRATION_TEST_ROOT = 'C:\Projects\AWS Project\dependency-acquisition\rag-smoke-integration-20261007-7a94c18e\committed-export-v2'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-smoke-integration-20261007-7a94c18e\run_offline_v2.py' tests/test_jev_rag_smoke.py tests/test_router.py tests/test_agents.py tests/test_jev_candidate.py tests/test_observability.py tests/test_errors.py tests/test_jev_live_smoke.py tests/test_api.py tests/test_lambda_package.py tests/test_jev_release_preflight.py tests/test_jev_saved_record_adapter.py tests/test_jev_release_observation_capture.py -q -ra --basetemp 'C:\Projects\AWS Project\dependency-acquisition\rag-smoke-integration-20261007-7a94c18e\pytest-committed-v2' --junitxml 'C:\Projects\AWS Project\dependency-acquisition\rag-smoke-integration-20261007-7a94c18e\committed-v2-results.xml' -p no:cacheprovider
```

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-smoke-integration-20261007-7a94c18e\canonical_and_fixture.py'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-smoke-integration-20261007-7a94c18e\run_ruff.py' check --no-cache app/agents/orchestrator.py app/agents/router.py app/services/bedrock_client.py app/services/rag_smoke_policy.py app/services/retriever.py scripts/lambda_package.py tests/test_jev_rag_smoke.py tests/test_lambda_package.py
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-smoke-integration-20261007-7a94c18e\run_ruff.py' format --check --no-cache app/agents/orchestrator.py app/agents/router.py app/services/bedrock_client.py app/services/rag_smoke_policy.py app/services/retriever.py scripts/lambda_package.py tests/test_jev_rag_smoke.py tests/test_lambda_package.py
git -c safe.directory='C:/Projects/AWS Project/worktrees/jev-rag-smoke-integration' -C 'C:\Projects\AWS Project\worktrees\jev-rag-smoke-integration' diff --check 274e283e353261c4d50b0d4f18ee97366d80d7ef cdb8f026d5717137da96e700142fee3b8957419d
```

The validation receipt also records exact initial/worktree/export commands, baseline format comparison and result bindings. Final checks run on unchanged accepted bytes; the only subsequent edit is this documentation.

## Remaining contract gates — not implemented by integration

| Clauses / phase | Present accepted offline behavior | Gate still required before claiming an actual smoke result |
|---|---|---|
| AC-01/07/12, P0 | Per-attempt model reservation/checks and filesystem claims; unknown attempts retain holds | Approved full worst-case model chain plus infrastructure allowance must fit provider/total ceilings **before parent Invoke**; durable persistent parent execution claim; exact zero-retry bounded parent client; unknown-parent handling. Per-stage settlement-dependent affordability is insufficient. |
| AC-03/07/13, P0 | Strict owner-supplied policy/evidence byte joins | Owner-approved prices and actual token/capacity bounds, caps, query/data disclosure, exact object identities, expected-source condition, retention, infrastructure allowance and limits. Hashes/references do not authenticate these decisions or semantic facts. |
| AC-01/02/03/04/05/06/13, P1 | Injected smoke seam enforces strict Haiku routing; conditional exact-byte object gates; metadata/native-adapter/vector/search/source gates | Separately reviewed explicit isolated smoke handler/operator activation and actual resolved inner-client/transfer/parameter/send checks in its real runtime. Intended factories and post-run observations are not actual pre-dispatch enforcement. No new live handler exists here. |
| AC-07/12/13, P1/P2 | Approved single-request settlement, stop latch and conservative holds | Preserve each actually delivered request's independent usage/actual charge/unknown exposure, including unauthorized extras and retry violations. No single reservation covers multiple delivered sends; authorization failure never erases known cost evidence. N2 remains. |
| AC-08/09/10, P2/operator | Application returns a structural result and writes metadata events | Full ordered operator evidence, actual attempt/send/retry/usage/cost records, Lambda INIT/REPORT, private response handling, successful returned completion and a matching published index hash. Unknown parent outcome or parseable partial `complete` bytes cannot establish success. |
| AC-04/05/06/10/13, artifact/runtime | Explicit source closure includes policy module; synthetic validation | New exact artifact/source/manifest/code bindings, accepted lock raw-byte handling, matching Linux native/import/link/CPU checks, isolated startup/RAG validation and source identity. The old accepted ZIP does not exercise this delta; old native/health evidence does not qualify a future artifact. |
| AC-09/11, semantic/operator/later evaluation | Structural source-hit and numeric consistency checks | Authorized operator abstention assessment bound to privately retained answer and classifier identity; separately grounded optional numerical check. Retrieved sources are not validated answer citations, nor proof of semantic alignment or answer correctness. Later quality qualification is separate. |

Owner D1–D7 and the contract's external prerequisites remain unresolved until separately granted/verified. No budget, runtime threshold, model access, IAM/resource creation, actual invocation or cleanup grant follows from integration. Reviewer Protocol v2 is neither reopened nor changed; this structural smoke does not itself supply its later qualification evidence.

### Retained N1–N5 and source-hit observation

- **N1:** policy construction does not establish whole-run worst-case sufficiency. Future operator P0 must enforce it, including infrastructure and provider subceilings.
- **N2:** retry metadata mismatch precedes valid usage journaling; actual extra sends require separate exposure evidence. The approved send hook's second-send rejection is not proof of coverage for multiple genuinely delivered sends.
- **N3:** unencodable metadata stops under the existing generic code. No error-taxonomy change was made.
- **N4:** application `complete` is a returned result/event, not hash-bound operator publication. Partial completion bytes followed by a stop cannot be treated as confirmed completion.
- **N5:** claims are filesystem-scoped, not distributed cold-instance deduplication. A persistent exclusive parent execution boundary is still required.
- **Nonblocking O1 — source-hit feasibility:** constructor validation permits `minimum_hits > source_counts[source]`. Retrieval then stops before generation, after earlier authorized stages may incur costs. A future upfront plan gate should reject impossible conditions before parent Invoke; no constructor or policy change was made here. Source hits remain structural provenance, not answer quality.

## Private receipts and preservation

| Private file | Raw SHA-256 |
|---|---|
| `accepted-inputs.json` | `a4e680a81da7e103504c6b6567dfe9c25cab7df8ca3de0c34d0e011df3e4e2fe` |
| `merge-and-export.json` | `150beaaa7448c339f152da8d3fd71ba848730c3beeebccac5bcb24d5a409bcd1` |
| `validation.json` | `0f81eb9f16094f32636c047e5061809b7d529e737881d4ada815a9ccf2d1db80` |
| `committed-v2-results.xml` | `bb199e31bc84c0f37a82867752a9ab17240d1f6384a74081867c8131d94d8392` |
| `preservation-before.json` / `preservation-after-validation.json` | both `4bc461672f271d5b4ef87cd7096372af116dee5db837e9bc6086ba48ceff5551` |

The inventories match across all eight existing worktrees: HEAD/branch/status and raw modified/untracked file bindings. Main remains `9bf00d13dd9c83a635719dfd2acb7798c353866c`, including its accumulated shared-document changes and 31 existing status file entries. Existing controls/acceptance reviews remain uncommitted in their original worktrees. No inaccessible item occurred within the recorded inventory; no permissions were changed.

Protected checks include the accepted ZIP, unchanged locks/requirements/allocation, prior adapter and implementation receipts, plan/event/static-metadata receipt, and 1,217 metadata-only file bindings across the specified sealed startup/baseline/capture-plan/adapter directories. This is scoped preservation, not a replay, semantic inspection, new historical proof or universal recertification of every ignored private artifact. Private corpus/index contents were not inspected for tuning or executed. Reviewer-v2 tracked source is unchanged and its existing untracked reports retain their bindings.

After committing only this handoff, the private final completion receipt records final HEAD, twelve-path delta, ordered merge parents, all eleven still-identical accepted blobs, handoff raw/committed hash, clean new-worktree status and the final preservation snapshot. No shared handoff/work log or prior receipt was edited.

## Focused Claude integration review

Verify the two acceptance report hashes/subjects, base and ordered non-fast-forward parents, nine-plus-two source union and handoff-only twelfth path. Recompute all accepted blobs independently; confirm checker/adapter/capture, requirements/lock/allocation and Reviewer-v2 are unchanged. Reproduce the guarded focused suites using invented native fakes and raw committed inputs; distinguish working-copy CRLF, source-export repository marker and historical formatting drift from source regressions. Check that this handoff does not promote independent controls acceptance or independent declarative-contract acceptance into full conformance, owner authorization or operational readiness. Preserve N1–N5, O1 and the future P0/P1/P2 gates.

Stop for that final independent integration review. No main merge or push. No AWS/network calls, real credentials or `.env` access, native/index execution, installation, containers, dependency/ZIP build, inference, resource changes, deployment or Reviewer Protocol v2 modifications occurred.
