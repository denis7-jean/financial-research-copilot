# Jev offline candidate: consolidated review and execution handoff

2026-10-03. Baseline `41d146db2e8d3973c3abb2668e1c7a4d969d4f8f`, branch `phase0/baseline-instrumentation-eval`. Engineering commits below are local only. Documentation commit/terminal HEAD are reported in the delivery receipt; use `git log -3 --oneline`. No live/shadow router is enabled, production remains Haiku, and **qualification, Freeze 1 readiness and deployment are unestablished**. Work is stopped at review/decision/external-operation boundaries; no background process is continuing.

## Candidate and exact inventory

| Commit | Explicitly committed paths | Capability |
|---|---|---|
| `ad7fe23c8302983df3f9e360145739ec1270d303` | `.env.example`; `app/agents/router.py`; `app/agents/orchestrator.py`; `app/agents/jev_router.py`; `app/agents/router_configuration.py`; `app/agents/routing_contract.py`; `tests/test_jev_candidate.py`; `docs/experiments/jev-upgrade-work-log.md` | Binary Jev mock adapter, explicit default/configuration, threshold/failure/privacy/telemetry checks and unchanged downstream dispatch. |
| `f9a9d031b15eb42b7390d50ead4147f0262998a2` | `.github/workflows/eval-ci.yml`; `experiments/jev_candidate/__init__.py`; `experiments/jev_candidate/smoke.py`; `scripts/candidate_package.py`; `scripts/jev_candidate_config.json`; `tests/test_jev_candidate_tools.py`; work log above | Reproducible invented comparison, source-only packaging diagnostics and automatic offline CI. |
| Delivery documentation commit | This handoff and work-log checkpoint | Review scope, exact hashes/reproduction and remaining execution instructions. |

Fifteen distinct paths across the window. New test files collect **71 cases**, including one native Windows symlink skip. No unrelated file staged; existing nineteen untracked user/report files remain untracked. Retrieval, QA/generation, summarizer, API, frozen benchmark and all v2 implementation/tests are unchanged. Existing router/orchestrator formatting changed with the named functional delta.

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

The known in-bundle reconciliation preflight is already implemented/independently accepted at `a587387036a656a185687e984b8c3cfd15c7aef5`. Its TECHNICAL_PREFLIGHT_VERIFIED_NOT_AUTHORIZED output neither dispatches nor authenticates phase/approval/sealing. No additional concrete edit to those seventeen sources is required by this router candidate. Actual final reconciliation/applicability/completion joins remain pending; no wrapper or actual independent record was created in this window. Source changes here do not inherit independent review, and unchanged v2 acceptance does not approve app code.

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

Codex self-review is **not independent acceptance**. Checked valid/malformed/duplicate/nonfinite/UTF8/oversized responses; 301/401/403/422/429/500/529; timeout/transport errors; choice-vs-confidence; no credentials/real client construction on Jev; no private provider content in new metadata/error codes; both unchanged downstream routes; one attempt; imports without clients/.env reads; deterministic reports and no source mutation. Trusted mocks are not a sandbox. HTTP phase timeouts and after-read size checking are not a streamed-byte or total wall-clock guarantee. No calibration, provider availability, real latency, actual bill, Linux runtime/dependencies, production configuration or qualified outcome is verified. A future live adapter needs reviewed resource lifetime, streaming/deadline/input-size, credential handling and run-budget enforcement; merely removing MockTransport rejection is insufficient. Do not execute the old Windows/installing package script as a release recipe.

## Exact hashes, coverage and preservation reproduction

Metadata-only outputs outside Git: `C:/Projects/AWS Project/heldout-external/jev-upgrade-preservation/2026-10-03-41d146d/`.

| Evidence | SHA-256 |
|---|---|
| preservation-before.json: 337 protected files, 27 separate mutable candidate-baseline files, exact nineteen preexisting untracked paths | `0a840d1f35a48bcef1621afe48abb95dbdedd9c57f9a65011e998bc3a0c8fd2d` |
| candidate-final-checkpoint.json: final current inventory/observations, no approval | `244a33a17c4e03a9facc40290f5e17eed910b1a5c05e927502c19569af285ad2` |
| Forty-five-path source/config/guard review inventory | `c65f0c6f52f03b24ea2b78213557578f25b389586053495e6c772daef1058535` |
| Nine-path focused test inventory | `e1298652dac73b049ecde3277e97107a5dd107a4a711a922ff4b1743b49a5602` |
| Source-only ZIP, constructed twice in memory, not saved/deployable | `e0716a7abf463e1381aeef58adab57203fde971fb4b17591bc0e6d57caa9032f` |
| Embedded archive manifest | `a8d07535142555f8774c686c4b36431b99e27c2acd83e9308f4e76401e124642` |
| Synthetic comparison report | `5d5c14509924ccda7889eed7b42851d38bd92ac802d8cde10e95db2464a44db8` |

Raw file hashes bind executing workspace bytes. Inventory digests are SHA256 of sorted compact ASCII JSON path->raw-SHA256 maps, finite values, final LF (`scripts.candidate_package.canonical`). Per-file maps are in final checkpoint. Source membership: app Python files, six non-test/non-archive eval Python sources, new smoke package, frozen benchmark Python files, experiments/__init__, package checker/config, requirements/.env.example/CI and three guard/root-conftest paths. Test membership is explicit in checkpoint; v2's existing fifteen-path TEST_PATHS manifest is unchanged and not replaced. First candidate-checkpoint.json is retained as superseded exploratory metadata (omitted eval-source dependencies), not accepted evidence. Inventory is review scope/AST coverage, not a complete transitively installed dependency lock. SDK/runtime observations are actual CPython 3.13.12 Windows, boto3/botocore 1.42.96, httpx 0.28.1, pydantic 2.13.3, pytest 9.0.3, Ruff 0.15.16 and other versions in metadata; requirements retains dev ranges.

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
meta=json.loads((folder/'candidate-final-checkpoint.json').read_bytes())
for map_name, hash_name in [('source_files','source_bundle_sha256'),('test_files','test_bundle_sha256')]:
    assert all(digest(Path(p).read_bytes())==h for p,h in meta[map_name].items())
    assert digest(canonical(meta[map_name]))==meta[hash_name]
print('Protected and candidate maps verified; no artifact writes or content output')
'@ | .\.venv\Scripts\python.exe -B -
.\.venv\Scripts\python.exe -B -m experiments.jev_candidate.smoke
.\.venv\Scripts\python.exe -B -m scripts.candidate_package --config scripts/jev_candidate_config.json
```

Git staging was explicit-path; staged bytes compared to validated workspace bytes after Git's CRLF->LF normalization. No protected input normalizations occurred. Raw runtime hashes and normalized Git blobs are distinguishable; a fresh checkout with different line endings must calculate/review its own raw inventory rather than assume these hashes.

## Minimal remaining path and genuine decisions

| Sequence / scope | Remaining action | Kind and boundary |
|---|---|---|
| 1, A independent | Claude review of combined app/config/tool/CI delta and exact tests below. Validate pinned binary semantics and deliberate malformed-Haiku repair; owner accepts resulting integration direction. | Independent review; no paid call or B freeze prerequisite for this review. |
| 2, A first exploratory evaluation | Decide run input allowlist, exact intended live adapter/config, credentials source, timeout/size/lifetime policy and per-provider/total ceilings/request limits; review minimal fail-closed live factory/budget patch, preserving Haiku default. Only then separately authorize execution. Existing isolated benchmark can verify availability under its own grant, but Phase A need not be repeated. | Owner run/cost/privacy decision + bounded implementation/review + later external execution. Smoke/availability remains exploratory, not qualification. |
| 3, B evidence independently completable | With separate assembly authorization, use existing actual accepted review to finish new reconciliation, eligibility applicability and dependent completion records. Preserve old bindings. Runtime/AST lock, broader applicable SDK/platform pins, policy/test/design/interface/procedure/current input closure/inventory and trusted final subject hashes still need actual bound evidence. | Evidence assembly; exact before-Freeze-1 requirements in accepted prerequisite audit remain before Freeze 1. This window assembled none. |
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
| Three normative rule subjects, contracts, source/algorithm/shared origins, semantic reviews; historical sources/manifest/ledger/lemma/counts | Unchanged and reusable at exact bindings. No amendment, replay or new historical execution claim. Historical generating digest remains `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`. |
| Replacement final reconciliation/eligibility applicability/completion | Still pending actual authorized assembly at new accepted subject. Do not alter earlier final wrappers or manufacture approval/review fields. |
| Any later operational source/closure edit | Bind its complete code/runtime/procedure/test closure and independent review. If a named v2 member/import changes, recompute seventeen-source descriptor and subject-bound reconciliation review plus downstream applicability/completion/procedure/test/final owner subjects. Do not hide caller code outside coverage. Consolidate changes first. |
| Future live enablement, Linux build or other app edit | New app/run/package inventory and independent delta review required; today's mock/self-review doesn't transfer to it. No actual final Freeze 1 evidence built around this changing broader application candidate. |

## Focused Claude review request

Review `git diff 41d146d..f9a9d03` plus this handoff/work log; no Claude invocation/message occurred. Prioritize (1) pinned payload/schema parity and confidence/error privacy repair; (2) default Haiku, invalid-config/real-transport/shadow rejection, no hidden model/fallback/retry and unchanged financial output; (3) cost/latency/unknown-cost semantics, HTTP limits and declared live gaps; (4) synthetic runner's guard-before-import, mock-only injection, deterministic non-qualification records; (5) source archive path/symlink protections, no credentials/eval inputs/writes/dependencies or runtime-attestation claim; (6) automatic CI billing removal and absence of deploy-readiness claims; (7) test failures/skips/digests/protected hash reproduction. Inspect preserved actual tenth report separately only to confirm its exact reusable disposition; do not repeat historical replay/accepted semantic subjects for reassurance. Record this candidate review separately from that reconciliation review and from owner/operational approval.

Recommended next single task: independent review of these two engineering commits and exact candidate inventory. While review is unavailable, owner can independently decide the live-run/privacy/cost scope and operational producer contract; do not rerun tests or create actual evidence merely to stay busy.

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

Scope receipt: offline/synthetic local engineering, metadata-only preservation/checkpoint and explicit-path local commits only. No push, install, live/model/provider/AWS/external API call, heldout content tuning, actual wrappers/preparation/InputBinding/FreezeManifest, adoption/sealing, real ranking/selection/sampling/packets, owner labeling or freeze designation. Independent candidate review remains required; **Freeze 1 and deployment readiness remain unestablished**.
