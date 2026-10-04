# Jev offline candidate: consolidated review and execution handoff

2026-10-03. Original autonomy baseline `41d146db2e8d3973c3abb2668e1c7a4d969d4f8f`; this bounded follow-up verified baseline `f73914fa622fc3e64dbe03bda1b82f88ff0472aa` and branch `phase0/baseline-instrumentation-eval`. Engineering commits below are local only. Documentation commit/terminal HEAD are reported in the delivery receipt; use `git log -5 --oneline`. No live/shadow router is enabled, the Haiku default is preserved, and **qualification, Freeze 1 readiness and deployment are unestablished**. Task A's streaming delta is Codex implementation/self-review pending independent review. Task B's two final evidence wrappers and existing technical chains are now complete under the separate owner grant, using Claude's actual accepted subject review; Claude has not reviewed these newly assembled final joins. No background process is continuing.

## Candidate and exact inventory

| Commit | Explicitly committed paths | Capability |
|---|---|---|
| `ad7fe23c8302983df3f9e360145739ec1270d303` | `.env.example`; `app/agents/router.py`; `app/agents/orchestrator.py`; `app/agents/jev_router.py`; `app/agents/router_configuration.py`; `app/agents/routing_contract.py`; `tests/test_jev_candidate.py`; `docs/experiments/jev-upgrade-work-log.md` | Binary Jev mock adapter, explicit default/configuration, threshold/failure/privacy/telemetry checks and unchanged downstream dispatch. |
| `f9a9d031b15eb42b7390d50ead4147f0262998a2` | `.github/workflows/eval-ci.yml`; `experiments/jev_candidate/__init__.py`; `experiments/jev_candidate/smoke.py`; `scripts/candidate_package.py`; `scripts/jev_candidate_config.json`; `tests/test_jev_candidate_tools.py`; work log above | Reproducible invented comparison, source-only packaging diagnostics and automatic offline CI. |
| `f73914fa622fc3e64dbe03bda1b82f88ff0472aa` | This handoff and work-log checkpoint | Original review scope, hashes/reproduction and execution instructions. |
| `1c0fe9a7dcb8e370ea53535e71292d76c56957b8` | `app/agents/jev_router.py`; `tests/test_jev_candidate.py` | Task A: bounded decoded response streaming/closure, eleven additional synthetic cases. |
| Follow-up documentation commit | This handoff and work log only | Task A validation/new inventories; Task B exact final wrappers, technical replay and remaining gates. Private outputs/reports excluded. |

Fifteen distinct paths across the original window; this follow-up changes four existing paths (adapter, its test, handoff and log), adding no repository files. The two new test files now contain **82 cases**, including one native Windows symlink skip. No unrelated file staged; existing nineteen untracked user/report files remain untracked. Retrieval, QA/generation, summarizer, API, frozen benchmark and all v2 implementation/tests are unchanged. Existing router/orchestrator formatting changed with the original named functional delta.

Jev pins model 1.13.0 and the existing binary request/response contract. Choice probability below 0.6 and malformed/timeout/service failures produce one-attempt qa fallback; no secondary Haiku invocation, retry, redirect, new taxonomy or financial-answer change. Only an exact `httpx.MockTransport` is constructible. Setting COPILOT_ROUTER_PROVIDER=jev without it fails; shadow always fails. Haiku remains the unset/default provider. Invalid Haiku confidence (nonfinite/outside 0..1/bool/string) now fails validation; raw validation exceptions no longer log provider output. Valid Haiku prompts/model/threshold are unchanged.

Both adapters expose provider, attempts, latency and usage-estimated cost; Jev also exposes fixed HTTP/error/outcome/reservation metadata. Unknown failure costs remain unknown. Historical price assumptions are $0.042/M input for Jev and $1/$5/M input/output for Haiku, **not current verified pricing, bill or free coverage**. No hidden fallback calls are budgeted. Existing Haiku SDK retry policy was not changed; a future live caller must verify one attempt if its accepted run requires that.

## Actual prior evidence and dependency separation

**A: router engineering.** Existing Phase A archive `eval/results/experiments/2026-09-28-phase-a-benchmark/MANIFEST.md` reports 343 Haiku + 343 Jev + 340 rules calls, 31 clear questions, Jev 31/31 versus Haiku 30/31, local p50 123.6/911.9 ms and p95 183.7/1669.7 ms; estimated $0.171651, not invoice. It is completed in-sample/client-side evidence. Do not redo it or call it heldout, Lambda or answer-quality qualification. New smoke results are wholly simulated. Existing journal/reservations/scheduling are reusable engineering components, not authorization for another run.

**B: Reviewer Protocol v2.** Actual tenth report exists at `docs/experiments/reviewer-protocol-v2-claude-reconciliation-refresh-review.md`. It says ACCEPTED for replacement subject `5ecea37ee945023f77266f6cc9d15ad5e8c7db6d3442c24f69a2112892e0cf78` at verification digest `e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e`. Read actual raw and typed records, strict UTC, raw/subject/contract/lemma/count joins; no real input replay. This is observed independent disposition, not acceptance inferred from a filename or Codex self-review, and hashes do not authenticate authorship. Private directory `heldout-external/reviewer-v2-evidence-reviews/2026-10-03-claude-41d146d-reconciliation-refresh/` contains:

| File | Raw SHA-256 |
|---|---|
| raw-review-replacement-reconciliation.md | `6d5d691a6ff7a76bd9cc0c7c200ef56c254cd071312b89d975499ae6f2edfcbf` |
| reconciliation-review.json | `6392f170e5d2bd52cd2efb1abacca58ff2bd1bb6953a705bb60eff27c692360e` |
| review-index.json | `600fb54a869d73a7585e2eb2fee0162001589a2665d40bc5c35009fb54e8e473` |

The known in-bundle reconciliation preflight is already implemented/independently accepted at `a587387036a656a185687e984b8c3cfd15c7aef5`. Its TECHNICAL_PREFLIGHT_VERIFIED_NOT_AUTHORIZED output neither dispatches nor authenticates phase/approval/sealing. No additional concrete edit to those seventeen sources is required by this router candidate. The original autonomy window created no actual wrappers/review records. The now-authorized Task B completed replacement reconciliation/eligibility applicability/index/check-receipt joins, including real 111-input historical verification and counts-only checks; see the separate completion section below. No new independent review was created. Source changes here do not inherit independent review, and unchanged v2 acceptance does not approve app code.

Accepted phase sequence (actual owner record `52847c5a-dc83-4fc2-b6d6-8e0032c20bf2`, corroborated by the prerequisite audit): **Freeze 1 -> production-ledger verification/sealing -> authorized external selection -> owner audit -> Freeze 2 -> separately authorized live execution**. Reviewer qualification/clean heldout labels and pre-registered comparison/answer-quality/Phase B gates must precede a qualified rollout claim. They are not necessary for mock adapter implementation or source packaging. Historical ledger fidelity remains a lemma premise, not proven execution. Preserve R4's reviewed limitation, S-576 complete:false and its exact extraction boundary, and the 37-check historical limitation. No new blocker is inferred from them.

**C: optional.** ADR 0001 is Proposed. Multi-head taxonomy, company filtering, grounded summarizer, Sonnet, decomposition, secondary Haiku fallback, shadow and circuit-breaker policy are outside this candidate. Old heldout protocol includes proposed extension requirements; its obsolete staffing/content/threshold assumptions must not override accepted v2 decisions. There is no new heldout loader or qualified statistical harness in this candidate. Settle its exact approved dataset/label/analysis contract, then implement/test that extension offline; do not use actual selections to invent that contract.

## Validation and Codex self-review

From `C:/Projects/AWS Project/main`, existing `.venv`; guard installed before app imports. Exact commands/results:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_candidate.py tests/test_router.py tests/test_agents.py tests/test_observability.py tests/test_api.py tests/test_router_bench.py -q --basetemp=.pytest_cache/jev-candidate-batch1-formatted
# 200 passed, zero attempts
.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_candidate_tools.py tests/test_jev_candidate.py tests/test_router_bench.py -q --basetemp=.pytest_cache/jev-tools-final
# 107 passed, one skipped, zero attempts
.\.venv\Scripts\python.exe -B -m pytest tests/ eval/ -m "not llm and not integration" -k "not test_accepted_population_regression" -q --basetemp=.pytest_cache/jev-integrated
# 1259 passed, one skipped, six deselected; 16 intentional guard-probe attempts intercepted, none sent
.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_candidate_tools.py -q --basetemp=.pytest_cache/jev-tools-package-final
# 15 passed, one skipped; final narrowed app-only packaging scope
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check conftest.py app/ eval/ tests/ scripts/ experiments/
# All checks passed
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check app/agents/router.py app/agents/orchestrator.py app/agents/jev_router.py app/agents/router_configuration.py app/agents/routing_contract.py tests/test_jev_candidate.py tests/test_jev_candidate_tools.py experiments/jev_candidate scripts/candidate_package.py
# Ten files formatted
git diff --check
git diff --cached --check
```

Integrated run includes existing golden payload/rules/serialization and dependency/import-purity tests. Final package narrowing occurred while that run was active; final package-specific rerun verifies the later bytes. No broader rerun after documentation-only delivery. Known warnings: missing pytest-asyncio plugin's asyncio_mode and three FAISS SWIG deprecations; no installs attempted. Native symlink fixture denied by Windows; synthetic is_symlink rejection also passes. Initial long pytest parameter IDs caused two Windows setup failures, fixed with short IDs and rerun. A metadata inventory command failed on a nonexistent test filename before writing; corrected paths and final closure are recorded. Work log retains these limitations.

Codex self-review is **not independent acceptance**. Checked valid/malformed/duplicate/nonfinite/UTF8/oversized responses; 301/401/403/422/429/500/529; timeout/transport errors; choice-vs-confidence; no credentials/real client construction on Jev; no private provider content in new metadata/error codes; both unchanged downstream routes; one attempt; imports without clients/.env reads; deterministic reports and no source mutation. Trusted mocks are not a sandbox. The original after-read limit is superseded by Task A below: retained HTTP-decoded JSON bytes are bounded while consuming, but delivered chunk/decoder/transport allocations remain unbounded, and HTTP phase timeouts are not a total wall-clock guarantee. No calibration, provider availability, real latency, actual bill, Linux runtime/dependencies, production configuration or qualified outcome is verified. A future live adapter still needs reviewed resource lifetime/deadline/input-size, credential handling and run-budget enforcement; merely removing MockTransport rejection is insufficient. Do not execute the old Windows/installing package script as a release recipe.

### Task A: current streaming candidate validation

`Client.stream("POST", ...)` encloses the response in a context manager. `iter_bytes()` applies HTTP content decoding before counting; Content-Length is not trusted. Before extending the body buffer, each decoded chunk is compared to the remaining 65,536-byte allowance. Over-limit chunks cause the existing response_too_large/schema-fallback code immediately, without requesting another chunk. Only the completed bounded buffer is UTF-8 decoded/strict-JSON parsed and validated. Success, HTTP rejection, oversize, parse/schema rejection and mid-stream read/transport failures exit through response closure. Binary labels/threshold, sanitized errors, exactly one attempted mock request, exact MockTransport construction, Haiku default and disabled live/shadow are unchanged.

Precise guarantee: the adapter's accumulated decoded body never exceeds 65,536 bytes; it stops pulling decoded chunks on excess. A chunk may already have been allocated by the transport or HTTP content decoder, and HTTPX may have decoded buffered raw bytes before yielding it. No bound on those allocations, aggregate process memory or total wall-clock time is claimed. Tests cover split UTF-8, absent/misleading length headers, exact limit, accumulated/single-chunk excess, no later chunk consumption, gzip decoded expansion and closure/error privacy/attempt accounting. HTTP errors close without reading the response body.

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_candidate.py tests/test_router.py tests/test_agents.py tests/test_observability.py tests/test_api.py tests/test_router_bench.py tests/test_jev_candidate_tools.py -q --basetemp=.pytest_cache/jev-stream
# 226 passed, one existing native-symlink skip, four existing warnings; zero intercepted/outbound attempts
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check app/agents/jev_router.py tests/test_jev_candidate.py scripts/candidate_package.py tests/test_jev_candidate_tools.py
# All checks passed
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check app/agents/jev_router.py tests/test_jev_candidate.py scripts/candidate_package.py tests/test_jev_candidate_tools.py
# Four files formatted
git diff --check
git diff --cached --check
```

This focused run includes package/configuration/no-writes/reproducibility and router/orchestrator/telemetry regressions. In-memory candidate package/report were recomputed twice and matched. No broad test rerun or v2 synthetic suite was needed for the two-file app delta or evidence assembly. Independent combined-candidate review, including this streaming delta, remains pending.

## Exact hashes, coverage and preservation reproduction

Metadata-only outputs outside Git: `C:/Projects/AWS Project/heldout-external/jev-upgrade-preservation/2026-10-03-41d146d/`.

| Evidence | SHA-256 |
|---|---|
| preservation-before.json: 337 protected files, 27 separate mutable candidate-baseline files, exact nineteen preexisting untracked paths | `0a840d1f35a48bcef1621afe48abb95dbdedd9c57f9a65011e998bc3a0c8fd2d` |
| candidate-final-checkpoint.json: final current inventory/observations, no approval | `244a33a17c4e03a9facc40290f5e17eed910b1a5c05e927502c19569af285ad2` |
| Current forty-five-path source/config/guard review inventory | `06b9b27763d063baa7a5e49f700502257a0d7b094c9331e7709739cb1ec3c77f` |
| Current nine-path focused test inventory | `7648c5eef955083fc1a301ef2d22a7922039b9ed3e8efc2568b58263f4247bce` |
| Current source-only ZIP, constructed twice in memory, not saved/deployable | `da108d44d9f5120852cf4a5ad43c0d799f3698ee4099dad323a7b2207c339fbc` |
| Current embedded archive manifest | `1992978b9b19344641741edfa8f37068ec48348452a8e4cb5381a66a7d700495` |
| Synthetic comparison report | `5d5c14509924ccda7889eed7b42851d38bd92ac802d8cde10e95db2464a44db8` |

Raw file hashes bind executing workspace bytes. Inventory digests are SHA256 of sorted compact ASCII JSON path->raw-SHA256 maps, finite values, final LF (`scripts.candidate_package.canonical`). Original candidate-final-checkpoint.json retains its original maps/hashes as prior-version metadata; it no longer matches today's adapter/test. Current per-file maps are in `heldout-external/jev-upgrade-streaming/2026-10-03-f73914f/candidate-checkpoint.json`, raw hash `ee13222c6483f9294c97f14fe8691ef2e1d4d0f4d4c7aa05c5313cf42433fadb`. Membership/recipes unchanged: app Python files, six non-test/non-archive eval Python sources, new smoke package, frozen benchmark Python files, experiments/__init__, package checker/config, requirements/.env.example/CI and three guard/root-conftest paths. Test membership is explicit in checkpoint; v2's existing fifteen-path TEST_PATHS manifest is unchanged and not replaced. First candidate-checkpoint.json is retained as superseded exploratory metadata (omitted eval-source dependencies), not accepted evidence. Inventory is review scope/AST coverage, not a complete transitively installed dependency lock. Earlier observed SDK/runtime metadata (CPython 3.13.12 Windows, boto3/botocore 1.42.96, httpx 0.28.1, pydantic 2.13.3, pytest 9.0.3, Ruff 0.15.16) is not refreshed into a runtime lock; requirements retains dev ranges.

Protected membership includes private original evidence, historical ledger/manifests/source captures, ten actual Claude reports plus the prior handoff, proposed draft, past evaluation archives, frozen benchmark and all preexisting user files. Hashes match; no question contents/IDs are logged. Reproduce read-only (existing environment):

```powershell
@'
from pathlib import Path
import json, hashlib
from tests.offline_guard import install
install()
from scripts.candidate_package import canonical, digest
root=Path('..').resolve()
folder=root/'heldout-external/jev-upgrade-preservation/2026-10-03-41d146d'
raw=(folder/'preservation-before.json').read_bytes()
assert digest(raw)=='0a840d1f35a48bcef1621afe48abb95dbdedd9c57f9a65011e998bc3a0c8fd2d'
snap=json.loads(raw)
assert all(digest((root/p).read_bytes())==h for p,h in snap['protected_files'].items())
meta=json.loads((root/'heldout-external/jev-upgrade-streaming/2026-10-03-f73914f/candidate-checkpoint.json').read_bytes())
for map_name, hash_name in [('source_files','source_bundle_sha256'),('test_files','test_bundle_sha256')]:
    assert all(digest(Path(p).read_bytes())==h for p,h in meta[map_name].items())
    assert digest(canonical(meta[map_name]))==meta[hash_name]
print('Protected and candidate maps verified; no artifact writes or content output')
'@ | .\.venv\Scripts\python.exe -B -
.\.venv\Scripts\python.exe -B -m experiments.jev_candidate.smoke
.\.venv\Scripts\python.exe -B -m scripts.candidate_package --config scripts/jev_candidate_config.json
```

Git staging was explicit-path; staged bytes compared to validated workspace bytes after Git's CRLF->LF normalization. No protected input normalizations occurred. Raw runtime hashes and normalized Git blobs are distinguishable; a fresh checkout with different line endings must calculate/review its own raw inventory rather than assume these hashes.

## Task B: accepted replacement evidence technically completed

Exclusive-created directory outside Git: `C:/Projects/AWS Project/heldout-external/reviewer-v2-reconciliation-completion/2026-10-03-f73914f/`. No previous evidence/review/index/receipt was overwritten. Reverified report raw hash `7c1617ff4e5a936dd69b14c6b83a4caa7d20d68d819be364f5c37f3a1c5f57af`; raw/typed/index hashes above, schemas, canonical bytes, ACCEPTED disposition, reviewer/strict recorded UTC `2026-10-03T19:28:06Z`, exact subject/contract/lemma/counts/raw/index joins all pass before use. Hash agreement does not authenticate authorship/approval.

| New private file | Exact raw SHA-256 |
|---|---|
| historical-ledger-reconciliation.json | `7d09419b16a7a37a7140f84282b003c4a7a597b83b950be64d319534c9c3a00e` |
| rule-applicability-eligibility_specification.json | `3f48b05b279de950021251e21548f9a0fe5cf3e3ab33155f1e43eda3f9ff979a` |
| completion-index.json | `9de570d789e8374d74347a2399ad850b34c68b2025dd4c7d5f9016be6cc8e6ec` |
| technical-check-receipt.json | `a7bc3979cdeddc7c57ea12a88739650780051df353f31c2f051fbb75f533803a` |
| preservation-before.json (355 protected files) | `f13c496020701abda6735fd101727d398ad5d61e1c8f3a4771ba6ced5e45a8df` |
| preservation-after.json | `428a6de3bb6b34256a6ad797bf21a674ac411791ff3931220f80cd1627ff7817` |
| completion_driver.py (task-local assembly/read-only replay helper) | `c6108ad9c98bbc4469f52cfb389cd8aea85861015c4ed8f7eb30b511e694d985` |

Final reconciliation preserves every accepted subject field, adds the prescribed v1 final schema and actual independent_review FB `6392f170…`. `review_subject(final)` remains exactly `5ecea37ee945023f77266f6cc9d15ad5e8c7db6d3442c24f69a2112892e0cf78`. Final eligibility RuleApplicability v3 differs from the previously accepted `abffd3bf…` bytes in **only** historical_ledger_reconciliation FB. Its semantic review/specification/document/decision/original evidence fields are unchanged. Exposure and grouping applicability retain `ed6a582f…` / `9ee08419…` and null reconciliation; all three semantic reviews remain their actual accepted records.

Existing `_history` passed original manifest/payload canonical/provenance checks, recovered sixteen-source filename/hash recipe, recorded CPython 3.13.12/Unicode 15.1.0 and the 111-input closure (107 pins plus four recovered inputs). All 111 inputs are covered by the durable snapshot. `_generating` passed on the unchanged original wrapper and sources. `_executing_sources` verified all seventeen actual origins/disk/raw/Git-baseline joins; digest stays `e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e`. Historical generating digest stays `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`. Direct `verify_reconciliation` returns **TECHNICAL_RECONCILIATION_VERIFIED_NOT_ADOPTED**. Combined `rule_bindings` passes normally, including its reconciliation chain. Counts-only validation is 104 total, zero E03/E03c/union/normalized-empty-question rows. No classifiers, normalization or historical code execution occurred.

The helper reconstructs genuine verified in-memory verifier arguments, not a production procedure package, InputBinding or FreezeManifest. It invokes no `_freeze`, `verify_adoption`, preparation, reconciliation_preflight or selection entry point. Assembly and read-only replay both exit 0, guard installed, zero intercepted/outbound attempts, 355 protected files unchanged. Replay requires exact canonical receipt/index byte equality and writes nothing:

```powershell
# Completed assembly command; exclusive creation refuses any overwrite.
Get-Content -Raw -LiteralPath '..\heldout-external\reviewer-v2-reconciliation-completion\2026-10-03-f73914f\completion_driver.py' | .\.venv\Scripts\python.exe -B - assemble
# Use ONLY check for reproducible subsequent read-only replay.
Get-Content -Raw -LiteralPath '..\heldout-external\reviewer-v2-reconciliation-completion\2026-10-03-f73914f\completion_driver.py' | .\.venv\Scripts\python.exe -B - check
```

Task B uses the existing actual independent subject review; **Claude has not independently reviewed the newly assembled final joins**. Technical success is not owner approval, historical execution proof, full Freeze 1 compatibility or readiness. **No adoption occurred.** R4's reviewed limitation, S-576 complete:false and 37-check limitations remain. No unrelated interface/test/procedure/runtime evidence was refreshed. Initial metadata preservation diagnostic used an FB reader on data/ metadata paths and stopped before writes; metadata-only workspace containment corrected this without changing verifier path allowlists. Initial helper assembly assumed a reusable eligibility applicability entry, but the refresh intentionally omits that pending entry; it stopped before wrapper writes, and was corrected to transcribe the pinned accepted old wrapper, changing only the reconciliation FB. No accepted evidence or validators were repaired.

## Minimal remaining path and genuine decisions

| Sequence / scope | Remaining action | Kind and boundary |
|---|---|---|
| 1, A independent | Claude review of combined app/config/tool/CI delta and exact tests below. Validate pinned binary semantics and deliberate malformed-Haiku repair; owner accepts resulting integration direction. | Independent review; no paid call or B freeze prerequisite for this review. |
| 2, A first exploratory evaluation | Decide run input allowlist, exact intended live adapter/config, credentials source, timeout/size/lifetime policy and per-provider/total ceilings/request limits; review minimal fail-closed live factory/budget patch, preserving Haiku default. Only then separately authorize execution. Existing isolated benchmark can verify availability under its own grant, but Phase A need not be repeated. | Owner run/cost/privacy decision + bounded implementation/review + later external execution. Smoke/availability remains exploratory, not qualification. |
| 3, B evidence | Replacement reconciliation/eligibility applicability/index/check receipt are technically complete above under explicit owner authorization; focused final-join review remains separate. Runtime/AST lock, broader applicable SDK/platform pins, policy/test/design/interface/procedure/current input closure/inventory and trusted final subject hashes still need actual bound evidence. | Evidence assembly; exact before-Freeze-1 requirements in accepted prerequisite audit remain before Freeze 1. No broader production/freeze evidence assembled. |
| 4, B operational dependency | Settle/implement/review trusted freeze/phase/approval/seal and selection/publication/recovery producers/callers. Bind complete executable closures; enforce accepted preflight before real computation and validated output checks before publication. | Owner operational-policy decisions + implementation/review; no operational use until separately granted. No undecided trust schema invented. |
| 5, B qualification | Exact final owner release subjects, technical full-path verification, then authorized Freeze 1, ledger verification/sealing, selection, approved rubric before owner audit; actual controls/keys/diagnostic expectations approved before use/seal; Freeze 2 before live reviewers. Bind API envelopes/inference settings and required cost/terms/credit decisions at their accepted gates. | Actual content/approval, operational execution and review remain distinct; task grants/code acceptance cannot substitute. Accepted counts/domains/phase/policy need no new decision. |
| 6, A qualified evaluation then rollout | Qualified reviewers/clean heldout labels feed approved frozen router experiment; complete synthetic tested dataset loader/paired/stratified analysis contract, pre-register tolerances and run configuration before seeing outputs. Paired routing and unchanged-answer end-to-end evaluation, then authorized AWS Phase B/runtime/network/latency tests and reviewed deployment/rollback plan. | Dataset/analysis decisions and technical harness work; separately capped external runs. Existing in-sample/judge results or new mocks cannot qualify a new candidate. |

Genuine owner decisions, prioritized: (1) first live experiment's exact scope, input/privacy permissions, request/per-provider/total ceilings and acceptable terms/credit basis; (2) intended production binary Jev policy/configuration and remaining quality/latency/cost tolerances, including handling requests beyond the benchmark's 300-character bound; (3) trusted operational producer/recovery/destination history policy, intended before-Freeze-1 runtime/broader dependency scope and eventual exact final release hashes; (4) actual control wording/reference keys/diagnostic expectations and generic rubric at their later approved phases; (5) exact qualified heldout/analysis extension contract. Do not request accepted 24/15/6 counts, seeds, IDs, owner abstention/inclusion or rule/exclusion semantics again.

For undecided operational contracts, **minimal proposal, unapproved/non-operational**: an external owner-controlled local record supplies immutable exact subject references and separately trusted hashes to a producer; preflight never calculates its own approval. Freeze designation validates the full accepted fifteen-role envelope and prerequisites before recording designation. Post-Freeze-1 seal producer verifies unchanged ledger/procedure and records a new seal, not a historical rewrite. Selection callers require authenticated phase/seal association and the accepted preflight before any ranking; publication validates all outputs, destination and exact SUCCESS/SHORTFALL/failure receipt; recovery uses one registered history/attempt policy. Define these producer-record formats/history/conflict rules in one bounded design task before implementation; no new role, cryptographic identity, universal Python sandbox or moved phase is proposed. This statement is not an operational design acceptance.

Known credit evidence: earlier local `reviewer-trial-v1.2-preflight.md` section 7 reports Free plan expiry 2026-10-13 versus owner credit date 2027-04-13; current account expiry/coverage cannot be established locally. Ten-day urgency is planning only. Exact eligible services/models, remaining credits, applicable prices and account rules require separately authorized verification; no amount is assumed free.

## Evidence refresh map for this candidate

| Binding | Effect |
|---|---|
| Current app/router run/package/test subjects | New 45-source/nine-test inventories above; future review/run records must name these bytes. Haiku invalid-output change means archive Phase A control acceptance cannot be silently reused as acceptance of the changed code. |
| Accepted seventeen-source v2 bundle | Unchanged `e2646384…`; descriptor raw `a5f30c12bb4c9e5761cacbcfb0614380633a90572886f17333159797bb426580` and accepted replacement subject unchanged. No new reconciliation subject or semantic review needed merely for these app/tool edits. |
| Three normative rule subjects, contracts, source/algorithm/shared origins, semantic reviews; historical sources/manifest/ledger/lemma/counts | Unchanged and reusable at exact bindings. Task B read-only verification did not amend/regenerate these artifacts or establish historical execution. Historical generating digest remains `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`. |
| Replacement final reconciliation/eligibility applicability/completion | Completed and technically replayed at the accepted subject above; new final byte bindings differ. Earlier records unchanged. Focused independent final-join checking still separate; no fabricated new review. |
| Any later operational source/closure edit | Bind its complete code/runtime/procedure/test closure and independent review. If a named v2 member/import changes, recompute seventeen-source descriptor and subject-bound reconciliation review plus downstream applicability/completion/procedure/test/final owner subjects. Do not hide caller code outside coverage. Consolidate changes first. |
| Future live enablement, Linux build or other app edit | New app/run/package inventory and independent delta review required; today's mock/self-review doesn't transfer to it. No actual final Freeze 1 evidence built around this changing broader application candidate. |

## Focused Claude review request

Review `git diff 41d146d..1c0fe9a` plus this handoff/work log; no Claude invocation/message occurred. Prioritize (1) pinned payload/schema parity and confidence/error privacy repair; (2) default Haiku, invalid-config/real-transport/shadow rejection, no hidden model/fallback/retry and unchanged financial output; (3) the streamed decoded-body bound/early stop/context-managed closure, gzip/headers/multibyte probes, precise allocation/deadline exclusions and telemetry/cost semantics; (4) synthetic runner's guard-before-import, mock-only injection, deterministic non-qualification records; (5) source archive path/symlink protections, no credentials/eval inputs/writes/dependencies or runtime-attestation claim; (6) automatic CI billing removal and absence of deploy-readiness claims; (7) test failures/skips/digests/protected hash reproduction. Separately inspect Task B's final subject-preserving/schema/review FB joins, eligibility-only reconciliation change, unchanged reusable roles and deterministic check receipt/helper. Its existing independent subject acceptance does not itself independently review these new final joins. Record candidate code review and final-join review separately from owner/operational approval. Do not reopen unchanged semantic subjects or repeat historical replay merely for reassurance.

Recommended next single task: independent review of the combined three engineering commits and exact candidate inventory, with Task B final joins checked separately. While review is unavailable, owner can independently decide the live-run/privacy/cost scope and operational producer contract; do not rerun tests or create actual evidence merely to stay busy.

## Unexecuted future commands and rollback

These templates are **not executed or authorized**. Placeholders must come from separately reviewed inputs/grants, not guessed resource names or preserved .env contents. Prior budget caps cannot be carried forward. No new automatic workflow enables them.

```powershell
# Optional vendor availability check, NOT a new qualification run.
# Requires explicit TypeSafe egress/terms/input and cost authorization.
python -m experiments.router_bench verify-jev --live typesafe --max-cost-typesafe <OWNER_CAP> --max-cost-total <OWNER_TOTAL_CAP> --output <EXCLUSIVE_APPROVED_PATH>
# Existing in-sample exploratory benchmark, only if a new concrete need exists.
# Requires both providers authorized, approved IDs/schedule, strict reservation
# feasibility, actual prices and ceilings. --live itself is not owner approval.
python -m experiments.router_bench benchmark --routers haiku,jev --ids <APPROVED_PUBLIC_CASE_LIST> --repetitions <REVIEWED_N> --warmup <REVIEWED_WARMUPS> --seed <REVIEWED_SEED> --haiku-reservation strict --live bedrock --live typesafe --max-cost-bedrock <OWNER_BEDROCK_CAP> --max-cost-typesafe <OWNER_TYPESAFE_CAP> --max-cost-total <OWNER_TOTAL_CAP> --output <EXCLUSIVE_APPROVED_PATH>
# Billable full application/judge check. Existing harness defaults to Haiku;
# it does not test a live Jev candidate until the later reviewed factory/config
# and bounded run budgeting are integrated. These old commands lack a cost cap,
# so an approved enforced bounded wrapper is required BEFORE running them.
python -m scripts.smoke_check --base-url <AUTHORIZED_TEST_ENDPOINT>
python -m pytest eval/test_llm_judge.py -m llm --run-live-eval -v
```

No heldout live command exists yet; don't invent a --dataset option or run real packets through the old benchmark. First complete the approved harness/qualification chain. For deployment, separately authorize AWS operations and an explicit financial ceiling for storage/Lambda/log/network/inference costs. Verify actual function, architecture, runtime, IAM, model access, networking, aliases and previous immutable rollback version/config under that grant. Build/test a reviewed Linux-compatible dependency artifact (not today's source ZIP), with exact wheels/layers and no install workarounds. Authorize a test-version/alias run before any production alias switch; live/shadow remain disabled until their reviewed enablement grant.

```powershell
# Separate AWS deployment authorization required; only a REVIEWED DEPLOYABLE ZIP.
aws lambda update-function-code --function-name <VERIFIED_FUNCTION> --zip-file fileb://<REVIEWED_LINUX_DEPLOYMENT_ZIP> --publish
# Only after approved qualification/canary, version/config and cost gates.
aws lambda update-alias --function-name <VERIFIED_FUNCTION> --name <VERIFIED_PRODUCTION_ALIAS> --function-version <APPROVED_NEW_VERSION> --revision-id <OBSERVED_ALIAS_REVISION>
# Rollback under an explicit incident/rollback grant, restoring prior immutable
# version/config (Haiku); compare alias revision to prevent concurrent overwrite.
aws lambda update-alias --function-name <VERIFIED_FUNCTION> --name <VERIFIED_PRODUCTION_ALIAS> --function-version <VERIFIED_PREVIOUS_VERSION> --revision-id <OBSERVED_CURRENT_ALIAS_REVISION>
```

If this project has no verified alias/version rollback mechanism, implement/review it first rather than assume these templates apply. Preserve old ZIPs/configuration and evidence; never substitute the source-only package or a guessed prior version. Offline tests do not prove a successful rollback.

Scope receipt: Task A offline/synthetic streaming implementation; Task B explicitly authorized two actual final wrappers and existing read-only real-evidence chains; metadata preservation and explicit-path local commits only. No push, install, live/model/provider/AWS/external API call, heldout content tuning, actual preparation/InputBinding/FreezeManifest, adoption/sealing, classification, real ranking/selection/sampling/packets, owner labeling or freeze designation. Independent candidate and new final-join review remain separate; **Freeze 1 and deployment readiness remain unestablished**.
