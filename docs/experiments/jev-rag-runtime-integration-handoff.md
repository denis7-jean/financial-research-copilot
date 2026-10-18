# RAG runtime isolated integration handoff

2026-10-08. Status: **INTEGRATION PENDING CLAUDE INDEPENDENT REVIEW**.

This increment integrates four independently accepted offline component scopes. It does not establish integration acceptance, full declarative-contract enforcement, live readiness, qualification, deployment permission or Reviewer Protocol v2 readiness.

## Exact history and acceptance scopes

Branch: `phase0/jev-rag-runtime-integration`. Worktree: `C:\Projects\AWS Project\worktrees\jev-rag-runtime-integration`.

Integration base: `33b05d9cc6281c308d39523b9b6d24048c384b0a`. Accepted cumulative source tip: `5eae4c9945193e94e6ed6e04ea84b26a2d9ff7ae`. The base and all four reviewed component subjects are ancestors of the source tip. Branch/directory collision checks passed before creation.

Exactly one explicit non-fast-forward merge: `0cfcf61dc2d9283b3473469166ae4a19a7176c26`. Ordered parents:

1. `33b05d9cc6281c308d39523b9b6d24048c384b0a`
2. `5eae4c9945193e94e6ed6e04ea84b26a2d9ff7ae`

Merge tree: `62898ea487ee43cf99e4fe4a08a0e851d86a72ef`; exactly equal to the source tip tree, with no conflicts or implementation edits. The final documentation-only commit adds this handoff; its exact commit/blob bindings are recorded in the private completion receipt without a circular self-hash.

The acceptance reports below were read, hashed and checked for ACCEPTED at their exact subjects. They remain uncommitted in their original worktrees; none enters this integration history.

| Component | Accepted subject | Original report raw SHA-256 |
|---|---|---|
| P0 | `36494d478f00358611e33bd0e4a5121def347f86` | `16f84e23bcb780c4aa2113b825e09073beb388227ee6098651a1fb2a24923886` |
| Handler/H1 | `e513c8ea4b1846cd085620459c86c65c8e3ad5a9` | `cc0fe7a72599d203799349ede6a4193d476f6785e888fc3bed8070b99b7accc6` |
| N2 accounting | `474f54c1b918aefd82690c37b1ea6d6f2a28d2a5` | `bed36c99329183f86a71f91f3f7f89b456c75c616a8b7e538a0a0d7740d81250` |
| Cumulative operator including OP-1/OP-1b/OP-1c/R3/R3-a | `5eae4c9945193e94e6ed6e04ea84b26a2d9ff7ae` | `2e72450e311eec8ae066678a7b223556566b7d699630645fe03a829987c9a60a` |

Report paths are recorded in `acceptance-bindings.json`. These component acceptances retain their individual boundaries; the integration itself awaits Claude review.

## Preserved path and byte inventory

Exactly 20 paths differ from base to merged source. Final base-to-documentation-tip adds only this handoff, for 21 paths. SHA-256 below hashes raw Git blob bytes obtained by binary subprocess capture, separately from raw Windows working-copy bytes. All 20 Git blobs equal the accepted source tip. Their existing checkout CRLF forms remain unchanged. No protected file is normalized.

| Accepted path | Raw committed-blob SHA-256 | Raw working-copy SHA-256 |
|---|---|---|
| `app/agents/orchestrator.py` | `40af8c977c02912820d18c65c804be8bc438f12d50fe5633f536d32c0386393a` | `ef53dbfd898b551d22df5f92a1df0ed16336f4e54ae9d9ea7255af290b24928e` |
| `app/agents/qa_agent.py` | `7abc599077a4b8479fa6508af73207e7fb455f87381763bf1251e2b8b4adfca6` | `bc048320d402eb72b03c5ddf2c5d1bafb59d401739dad87257d9db6a2533a757` |
| `app/agents/router.py` | `552cf6297dc8015625b269cd3c3e075e10638ba462c75ba2dfaa0a590b3d9622` | `453a43a45c2b9f7553fb8b54e97e79d9ac270af022604971d5046dfeddd79c44` |
| `app/rag_smoke_handler.py` | `04adb0219cfa2337a671d09b5aef5e6d8739204e2eed70875e41a6cb3b17fc9c` | `e296146ef894479177d5921f013e6ec4e356c6193d44960822d3288daea655cb` |
| `app/services/bedrock_client.py` | `09baa31085a7980971e16ccb6b2b059406b20f31b355f7a3582b1257cc638e01` | `a1b6faa3d53db28b461099d6f337642ec61f6fac841c94990f323632a6c82081` |
| `app/services/rag_smoke_policy.py` | `f63d70433f49598e777a5f1dc5f323204a4b52547dd2c8f604f09552411ee91a` | `2a37a182987f9e631bbf24f06792b02b3770efa476af60006a164e5ea827801d` |
| `app/services/retriever.py` | `ae2d4bd92bfdc274e66038870c59f27c542b5b904ce4f354a1f32590ce556555` | `21f20a8307b227fec54522228bccaad1ea0789b6609b9bdf19316fde07bc3ecc` |
| `docs/experiments/jev-rag-smoke-accounting-handoff.md` | `61c59e37b329f54998fd54ee25b244f6d9ef01e1da5f7dfbebc2b65ad7fc239b` | `b2d51d268f40b959c91db552b1966d9bfd4e2b93c4a40736417fd74160706395` |
| `docs/experiments/jev-rag-smoke-handler-handoff.md` | `e27af1c00f528a9bdd9936a4b6e45c633e03ae84932a294e1825ac32467f310f` | `128b357a3f99009edc450fd6666843f29fb20f6fc28c21b75419bcfc2844b7ae` |
| `docs/experiments/jev-rag-smoke-operator-handoff.md` | `3affa706fe93220533648f36e6e20730fb6273cbca1a49146a8962b0c63cdbab` | `2fc4a67b052f808663696285e7b6db9e39d0f28b5ffd40a1ed530cb767e772be` |
| `docs/experiments/jev-rag-smoke-preinvoke-handoff.md` | `39139089a42aae4144a21be8b0cfa47ac6dd6f5cec766f9b8faac2c5af3e5376` | `4346d0d4783cd2ff2675185015b3332aac40250570ff16cba24d463868448cff` |
| `scripts/jev_rag_smoke_operator.py` | `3f0980565d771880843c673f52e314964803ab3cff14ac2cab7f6bd08fdb21b0` | `17cb61305471b0c02050a9592002b94b42174969dc8ee58f54be5eabaa0f6260` |
| `scripts/jev_rag_smoke_preinvoke.py` | `cf9cbe2de3dad8a183d8c45f20e2b46df153970b6e772b88dc7a21abbf08f6a8` | `770fad3d1d3808a3042944b025d212ec5c734b1699ff6f2b815afe4bb9a19414` |
| `scripts/lambda_package.py` | `b8cc5ae4670a404008b20fee09ec504b4a944fa63b7eddcabb1576c54cf78691` | `155ceab824b38c941c5d9463b6745f17239626992c11dd4f8a7762ba925d71ff` |
| `tests/test_jev_rag_smoke.py` | `5513c420204e313a93b6d5eedfb08c1374987ffae9f5ad23217c8ca5ce1fdf3c` | `e88554b817713c6e14005c1eb407fd69be3241446b52eb1db9b9193719ed97b6` |
| `tests/test_jev_rag_smoke_accounting.py` | `5dafe8ff8c1f4b0fdfe6db8fd693994bd08fad8f2c82a93811e5a884d9c5095d` | `62eb2c3d7dd05b4d47382bcc573d6731fb4b8ca665f49e6355b386e2657399b3` |
| `tests/test_jev_rag_smoke_handler.py` | `afa7a44c0d1ddeacc952123e1b04a971ec253fbb9939c2697b72bfa9c550d27d` | `8e874005e818babb2de6b4a2bd722ca7fe00fcb4a222cf9f7315238b130fb9b0` |
| `tests/test_jev_rag_smoke_operator.py` | `e2a0b5dfc974c6852f7fc12b0a533b1e2cbf796f05f0b4813f16d24c65e27e80` | `20f2f206793c12b174e103636d96bea55bd9bcea8f1bbc9e5e8d95f2e4f6bfa3` |
| `tests/test_jev_rag_smoke_preinvoke.py` | `2f43eddb69f9995fa072bbf4ebccdcc3cc33b5a79908505ff31f7321fc74912f` | `e66cb66f067c3f139505e154feccb5541a2191dd29b8491d0ad39884190df5c9` |
| `tests/test_lambda_package.py` | `eb7d47c27e3064780f598205bf7723fdb9c851a956e089d2917f8fb6068ae9f2` | `d4037cdbbb0a52b964f1cd0e409679098ea81a81c9bfe6e86e129a6b4e556a0d` |

Only new writable repository path: `docs/experiments/jev-rag-runtime-integration-handoff.md`. It is staged explicitly and committed alone after validation. Final handoff Git/working-copy hashes are in `completion-receipt.json`.

## Integrated behavior and limits

P0 establishes the persistent exclusive parent claim and invocation-attempt marker before client factory/dispatch, checks exact event/policy bindings and worst-case reservations including infrastructure. The isolated handler enters a hash-bound smoke policy and returns handler-result v2; the H1 QA dotenv guard is preserved, with ordinary-path behavior unchanged. N2 keeps independently valid usage/known charges distinct from authorization, settled reservations, uncertain retained holds and extras. The parent operator consumes v2 results and rejects contradictions, forged retained-hold totals and unsafe monetary representations without losing raw response bytes or permitting resend.

Existing synthetic seams check P0 claim-before-factory/dispatch, actual handler/accounting outputs, retained uncertain holds, blocked versus delivered/unknown extras, contradiction rejection, bounded Decimal parsing, publication failures and genuine hash-bound completion confirmation. A completed local publication is distinct from complete experiment evidence and from successful RAG. Hashes do not authenticate captures, owner approval, prices or host timestamps. No new runtime behavior or acceptance clauses were added by integration.

## Offline validation

Interpreter: `C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe`, actual Python **3.11.15** (Anaconda Windows AMD64). Ruff **0.15.14**. The existing offline guard remained active; **zero outbound attempts**. Test timeouts/resources are pytest/local observations, not Lambda measurements.

Private validation root:
`C:\Projects\AWS Project\dependency-acquisition\rag-runtime-integration-20261008-34ec729b`

Exact top-level commands:

```powershell
$integrationPython = 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe'
$integrationScratch = 'C:\Projects\AWS Project\dependency-acquisition\rag-runtime-integration-20261008-34ec729b'
& $integrationPython -B "$integrationScratch\validate.py" focused
& $integrationPython -B "$integrationScratch\validate.py" raw
& $integrationPython -B "$integrationScratch\validate.py" lint
& $integrationPython -B "$integrationScratch\validate.py" checkout-lock
```

`focused`: integration worktree, five suites: `test_jev_rag_smoke_operator.py` (201), `test_jev_rag_smoke_preinvoke.py` (83), `test_jev_rag_smoke_accounting.py` (31), `test_jev_rag_smoke_handler.py` (53), `test_jev_rag_smoke.py` (86). **454 passed**, no skips.

`raw`: fresh raw Git-byte export of the merge, all five suites above plus `test_agents.py`, `test_router.py`, `test_api.py`, `test_observability.py`, `test_errors.py`, `test_jev_candidate.py` and the complete `test_lambda_package.py`. **820 passed, 1 skipped**. Skip: `test_lambda_package.py:405`, Windows symlink privilege unavailable. Both pytest runs emit the inherited unknown `asyncio_mode` configuration warning.

Both pytest commands run `run_offline.py -q -ra -p no:cacheprovider --tb=short`, fresh scratch `--basetemp`, and JUnit outputs. Exact expanded argument lists, cwd, log hashes and interpreter versions are in the corresponding `validation-*.json` and `*-command.json` receipts. The single lock probe omits `-ra`; its exact command is also retained.

The inspected bootstrap substitutes NumPy/FAISS with invented pure-Python fixtures before importing application seams. It never executes those native packages; **native compatibility remains untested**. The raw source export is a validation workspace, not an artifact. It needed no export-only `.git` marker or repository scaffolding. Bootstrap fixture code, JUnit, caches and logs stay outside repository source. Guarded tests used the approved unsandboxed execution boundary for the previously demonstrated sandbox pytest-directory `Path.resolve` denial; no protected ACLs or test guards were changed.

`lint`: guarded Ruff `check --no-cache` on all 16 changed Python files: **passed**. `git diff --check BASE HEAD`: **passed**, and repeated after staging the handoff. No inherited files were reformatted; historical formatting drift is not corrected here.

`checkout-lock`: single canonical-lock assertion on Windows checkout: **1 expected inherited failure** at `test_lambda_package.py:1402` (CRLF versus LF at byte 3802). The same assertion passes on raw committed bytes. Raw Git lock SHA-256 `01fe426a5e28b274c4cc1bdb3ef6423203564b43ded257149bec35b7879c5bb8`; unchanged raw checkout SHA-256 `226aafe6c2aab570bebb7d495e214422206fdb7e97058875ac17b069d54d38ab`. In-memory comparison establishes the line-ending-only difference; no file or global Git line-ending setting was changed. This discrepancy is reported separately from passing committed-byte packaging regressions.

No entire historical/real-population suite, live smoke, native run or artifact build occurred. Source validation is reused after this documentation-only addition; all accepted blobs are checked again before/after commit.

## Preservation and receipts

Before/after metadata snapshots cover all 13 preexisting worktrees (HEAD, branch, status and readable changed/untracked bytes), including main's accumulated shared-document additions and reports. Main remains at `9bf00d13dd9c83a635719dfd2acb7798c353866c` with its 31 preexisting status entries. The new integration worktree is recorded separately. Protected ZIP, fixed inputs, locks, requirements, allocation and sealed evidence remain at their original bindings.

Of 1,217 inherited sealed inventory paths, 133 readable file bindings are checked unchanged and 1,084 prior pytest files are inaccessible to the current user. Their contents are not newly verified; no permissions were changed. Ten protected artifacts and 16 fixed input bindings are also retained. The accepted historical ZIP SHA-256 remains `46ace5c38c4cf24e131c01437419aa56244280e2e570a777ae2a0d5ff7cabed7`; it does not cover the new integrated runtime sources.

Private receipts: `acceptance-bindings.json`, `accepted-cumulative-blobs.json`, `merge-receipt.json`, `raw-export-receipt.json`, `preservation-before.json`, `preservation-after.json`, validation command/log/JUnit receipts and `completion-receipt.json`. Completion records exact final HEAD, ordered merge parents, 21-path delta, separate Git/checkout hashes, helpers and receipt SHA-256 bindings. No review report, credentials, private data or downloaded binary is staged.

## Remaining gates and focused review handoff

O1–O4 remain unresolved:

1. Real SDK exception translation and partial-byte preservation require a separately reviewed operational adapter; current transport protocol is simulated.
2. Supplied REPORT memory values still accept finite nonnegative floats. Actual AWS capture/type/provenance is an operational requirement.
3. `confirm` relies on preserving the actual returned result; index bytes cannot authenticate a reconstructed or forged return.
4. Dispatch count includes entering invoke whose parameter hook blocks before sending; it is conservative, not a delivered-call count.

Further gates remain separate:

- Reviewed live parent adapter, actual zero-retry SDK invocation, persistent claim before dispatch, unknown-outcome handling and no automatic resend.
- Permitted credential-provider/endpoint flow, least required runtime permissions, suitable private output/retention, authenticated provenance of observations and response/log/REPORT joins. These were not inspected or granted here.
- Owner-approved public data/query/object/index/metadata identities, expected-source condition and minimum-hit feasibility, semantic expected answer; current authoritative prices, token bounds, provider/task limits and whole-task infrastructure allowance. Worst-case sufficiency must be established **before parent Invoke**, not inferred from inner settlement.
- Actual inner-client enforcement and trustworthy separately attributed usage/extra-request evidence; passing these local seams does not establish enforcement for a deployed artifact.
- New exact artifact including this runtime, with native/link/import/startup verification and isolated-target configuration review. Historical ZIP/native results do not automatically transfer to this source tree.
- Successful actual returned completion plus matching index/file bindings, independent evidence review, semantic assessment and later answer-quality qualification. No live result, release authorization or Reviewer Protocol v2/Freeze 1 readiness follows from integration.

Inherited N1/N3–N5 and source-hit feasibility limitations remain visible in the component handoffs; N2's accepted accounting correction is preserved, not generalized into complete accounting or provenance guarantees.

Claude's next task: independent integration review at the final receipt-bound tip, verify the one ordered merge/tree equality, 20 exact accepted blobs plus handoff-only addition, raw-byte regressions and preservation limits. Do not reopen accepted component subjects merely for reassurance; inspect their composition and stated seam evidence. Stop for that review before any further integration or operational action.

Scope receipt: one isolated local merge and handoff-only commit, offline invented-fixture validation and metadata receipts. No main/other-worktree changes, functional fixes, push, AWS/network/credentials/.env access, native execution, install, container, artifact build, inference, resource change, deployment or Reviewer Protocol v2 modification.
