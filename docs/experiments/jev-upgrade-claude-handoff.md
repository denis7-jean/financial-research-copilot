# Jev offline candidate: consolidated review and execution handoff

2026-10-03 local / 2026-10-04 UTC. Original autonomy baseline `41d146db2e8d3973c3abb2668e1c7a4d969d4f8f`; streaming/evidence follow-up baseline `f73914fa622fc3e64dbe03bda1b82f88ff0472aa`; isolated smoke grant baseline `8f4e9859d27d368233cd6bd20f08133b82d4ee8f`, branch `phase0/baseline-instrumentation-eval`. Engineering commits below are local only. Documentation commit/terminal HEAD are reported in delivery receipts. Application live/shadow remain disabled, Haiku default is preserved, and **qualification, Freeze 1 readiness and deployment are unestablished**. Independent candidate review remains pending. Task B's two final evidence wrappers use Claude's actual accepted subject review; Claude has not reviewed the newly assembled final joins. The separately authorized isolated smoke stopped at its first free token-count preflight: **zero inference attempts**. No background process is continuing.

## Candidate and exact inventory

| Commit | Explicitly committed paths | Capability |
|---|---|---|
| `ad7fe23c8302983df3f9e360145739ec1270d303` | `.env.example`; `app/agents/router.py`; `app/agents/orchestrator.py`; `app/agents/jev_router.py`; `app/agents/router_configuration.py`; `app/agents/routing_contract.py`; `tests/test_jev_candidate.py`; `docs/experiments/jev-upgrade-work-log.md` | Binary Jev mock adapter, explicit default/configuration, threshold/failure/privacy/telemetry checks and unchanged downstream dispatch. |
| `f9a9d031b15eb42b7390d50ead4147f0262998a2` | `.github/workflows/eval-ci.yml`; `experiments/jev_candidate/__init__.py`; `experiments/jev_candidate/smoke.py`; `scripts/candidate_package.py`; `scripts/jev_candidate_config.json`; `tests/test_jev_candidate_tools.py`; work log above | Reproducible invented comparison, source-only packaging diagnostics and automatic offline CI. |
| `f73914fa622fc3e64dbe03bda1b82f88ff0472aa` | This handoff and work-log checkpoint | Original review scope, hashes/reproduction and execution instructions. |
| `1c0fe9a7dcb8e370ea53535e71292d76c56957b8` | `app/agents/jev_router.py`; `tests/test_jev_candidate.py` | Task A: bounded decoded response streaming/closure, eleven additional synthetic cases. |
| `8f4e9859d27d368233cd6bd20f08133b82d4ee8f` | This handoff and work log only | Task A validation/new inventories; Task B exact final wrappers, technical replay and remaining gates. Private outputs/reports excluded. |
| `8373c34eb4a60c3c6524233c26302eb436c7d09d` | `experiments/jev_candidate/live_smoke.py`; `tests/test_jev_live_smoke.py` | Isolated fixed six-by-two owner-smoke runner, strict reservations, durable no-resend claim, restricted transport bridge and synthetic tests. No app configuration change. |

Fifteen distinct paths across the original window; this follow-up changes four existing paths (adapter, its test, handoff and log), adding no repository files. The two new test files now contain **82 cases**, including one native Windows symlink skip. No unrelated file staged; existing nineteen untracked user/report files remain untracked. Retrieval, QA/generation, summarizer, API, frozen benchmark and all v2 implementation/tests are unchanged. Existing router/orchestrator formatting changed with the original named functional delta.

The later isolated-smoke grant adds two repository paths above: seventeen distinct paths across all engineering work. Its 22 synthetic cases bring the relevant targeted checkpoint to 248 passed/one existing skip. The earlier fifteen-file inventory/82-case statement describes the original plus streaming candidate, not the new runner's test count.

Jev pins model 1.13.0 and the existing binary request/response contract. Choice probability below 0.6 and malformed/timeout/service failures produce one-attempt qa fallback; no secondary Haiku invocation, retry, redirect, new taxonomy or financial-answer change. Only an exact `httpx.MockTransport` is constructible. Setting COPILOT_ROUTER_PROVIDER=jev without it fails; shadow always fails. Haiku remains the unset/default provider. Invalid Haiku confidence (nonfinite/outside 0..1/bool/string) now fails validation; raw validation exceptions no longer log provider output. Valid Haiku prompts/model/threshold are unchanged.

Both adapters expose provider, attempts, latency and usage-estimated cost; Jev also exposes fixed HTTP/error/outcome/reservation metadata. Unknown failure costs remain unknown. Historical price assumptions are $0.042/M input for Jev and $1/$5/M input/output for Haiku, **not current verified pricing, bill or free coverage**. No hidden fallback calls are budgeted. Existing Haiku SDK retry policy was not changed; a future live caller must verify one attempt if its accepted run requires that.

The isolated runner independently prices/reserves at the newly verified $0.042/$0 Jev and US geographic Standard Haiku $1.10/$5.50 rates below. It never uses the app's historical Haiku cost estimate for run accounting. Its client has exactly one SDK attempt. Those overrides do not change the production RouterAgent constructor or pricing metadata.

## Isolated owner-smoke delta and stopped actual run

The owner explicitly authorized only six invented routing inputs once per pinned provider, sequentially, zero retries, at $0.02 Jev/$0.03 Haiku/$0.05 combined gross inference ceilings. No retrieval, generation, judge, deployment, account/resource/billing change or Reviewer v2 operation. Independent review is not inferred from this permission.

Implementation at `8373c34…` preserves the app Jev exact-MockTransport constructor: only this dedicated runner supplies a MockTransport bridge to a separately authorized direct HTTPX streaming client. The candidate's actual payload/streamed JSON/schema/route code still runs. Its `router_live=False` telemetry describes the candidate's app configuration; the runner separately records `actual_live`, and does not mislabel an external bridge as an offline simulation. Haiku uses inherited `RouterAgent.route`, with isolated constructor wiring to pure boto3 Converse, maxTokens 256, performanceConfig standard and serviceTier default (Standard). No prompt/threshold/model changes. No public application live factory/env toggle is added.

Allowed egress: exact TypeSafe POST /v1/systemone, exact us-east-1 Bedrock CountTokens/Converse paths and pinned model. Explicit configured AWS environment/.env signing keys avoid unrelated credential discovery. HTTPX retries=0, redirects=false, trust_env=false; boto3 total_max_attempts=1, explicit endpoint/region, no proxies. Pre-dispatch permit plus before-send wire permit block extra dispatches/retries. Existing test guard is never lifted or monkeypatched; live CLI refuses pytest/guard processes. Downstream tripwire and fixed routing-only imports remain distinct from a universal Python sandbox guarantee.

Run ID `2026-10-03-owner-routing-smoke-01`, fixed exclusive private directory `C:/Projects/AWS Project/heldout-external/jev-isolated-live-smoke/2026-10-03-owner-routing-smoke-01/`. Existing directory means no re-entry/resume; a crash/unknown outcome cannot cause automatic resend. Plan includes exact complete prompts/options, expected labels, model IDs, source map/commit, prices, limits and order before token-count preflight. Journal flush/fsync precedes paid dispatch. Existing Ledger reserves before every call and retains full reservation for unknown usage, including failures. All-provider failure stops the schedule; differing valid routes do not retry/tune.

| ID | Exact invented question | Expected |
|---|---|---|
| Q1 | What was the fictional Maple Bank's net revenue in 2025? | qa |
| Q2 | How much total debt did the fictional Cedar Fund report at year-end? | qa |
| Q3 | What was the fictional Birch Company's diluted earnings per share? | qa |
| S1 | Summarize the main business risks in the fictional Maple Bank's annual report. | summarize |
| S2 | Give a high-level overview of the fictional Cedar Fund's investment strategy. | summarize |
| S3 | Summarize the major financial performance trends for the fictional Birch Company. | summarize |

Price retrieval recorded `2026-10-04T00:41:03Z` (official-document preparation window): [TypeSafe models](https://docs.typesafe.ai/models) pins jev-1.13.0, $0.042/M input, free output, 64K input request bound; [AWS official geographic pricing table](https://aws.amazon.com/jp/blogs/news/amazon-bedrock-now-supports-japan-cross-region-inference/) distinguishes US geographic Haiku $1.10/$5.50 from global $1/$5; [Bedrock pricing](https://aws.amazon.com/bedrock/pricing/), [Haiku card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html), [Standard tier](https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html) corroborate the pinned US profile/us-east-1/default tier. No credits or tax assumptions. [CountTokens](https://docs.aws.amazon.com/bedrock/latest/userguide/count-tokens.html) is free and promises billed-input equivalence for identical supported prompts; it also warns some CRIS-only Anthropic models lack runtime token-count support. The original inference profile is never substituted.

Jev reservation: 64,000 * $0.042/M = $0.002688 per attempt, six-call maximum $0.016128. Expected historical-usage estimate: six * 410 input tokens = $0.00010332, not a guarantee. Haiku reservation design: exact CountTokens for the complete system/messages + 256 output at $1.10/$5.50; inputs must count at <=2048. Worst conditional six-call Haiku reservation at that bound is $0.0219648; combined $0.0380928 fits the grant. An actual Haiku expected cost/reservation requires successful exact prompt counts; it was **not established** in this run. No inference can use the conditional 2048 check as an unverified assertion.

Offline command on final committed runner/test bytes:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_live_smoke.py tests/test_jev_candidate.py tests/test_router.py tests/test_agents.py tests/test_observability.py tests/test_api.py tests/test_router_bench.py tests/test_jev_candidate_tools.py -q --basetemp=.pytest_cache/jev-live-integrated
# 248 passed, 1 skipped, 4 existing warnings, 3.38s; zero intercepted/outbound attempts
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check experiments/jev_candidate/live_smoke.py tests/test_jev_live_smoke.py
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check experiments/jev_candidate/live_smoke.py tests/test_jev_live_smoke.py
git diff --check
git diff --cached --check
```

All lint/format/whitespace checks passed. Initial focused run 114 passed before added policy/tripwire/import tests; integrated run validates final formatted bytes. Existing native-symlink skip and asyncio_mode/three FAISS warnings unchanged. Synthetic cases prove reservations/count caps before dispatch, failures retained/counted, one-claim re-entry rejection, streamed oversize early stop/closure, fixed-code sanitization, model/usage failures, exact prompt/output/tier binding, missing settings, wire allowlists, duplicate wire rejection, downstream rejection and import purity. Codex self-review only.

Actual command, executed once outside pytest with owner authorization:

```powershell
.\.venv\Scripts\python.exe -B -m experiments.jev_candidate.live_smoke --execute-owner-smoke
```

**STOPPED at Q1 token_count_preflight: ValidationException.** One non-inference Bedrock CountTokens operation was attempted; it returned no input count. No inference dispatch to Jev or Haiku occurred, no replacement/diagnostic inference and no retry. All six cases remain unattempted for both providers; routes/confidence/probabilities/usage/inference latency are unavailable. Actual inference attempts 0/0/0; committed inference cost $0, unknown-cost reservations $0; remaining ceilings $0.02/$0.03/$0.05. Process returned nonzero. The provider error message was deliberately not persisted; this evidence establishes the operation/phase/error code, not a specific underlying server rejection reason. The documented runtime CountTokens restriction for CRIS models is a possible explanation, not an independently verified diagnosis. Do not rerun this claim or infer successful TypeSafe connectivity from zero calls.

| Private output | Raw SHA256 |
|---|---|
| plan.json | `5cf31613a34ecc87b6eabe92cd496644e4c89bc46443b699b26c36951f2f11ec` |
| result.json | `68f26dac5d2313d79bb655a2b96466a4fb458e221324a15f5978dfe025646cfc` |
| run.journal.jsonl | `7a781da0c0b99e8e37f1654e4e44253daedb475092d1c1729220053f68f421c5` |
| source-inventory.json | `b20e668b9f41b5cf0d717f832c74adc0e6a479c463d120688e798baa41edac03` |

Run's exact 56-path app/control/guard/tool/benchmark/test closure map digest is `f3b543ff404d0293a4189df4cacfc5bf99e73b92cbde3c1cddc2b5836bbf0605`: sorted compact ASCII JSON relative-main-path/raw-hash map + LF. Baseline 45-source/nine-test membership retained plus isolated runner/test. Executing raw bytes checked against normalized Git blobs at `8373c34eb4a60c3c6524233c26302eb436c7d09d`. This combined map has a different relative-path namespace from the prior candidate maps; it does not replace protocol bundles. App sources/source-only Lambda archive remain unchanged; runner is outside that package. Seventeen-source v2 digest and actual reconciliation evidence unchanged.

Metadata preservation directory `C:/Projects/AWS Project/heldout-external/jev-live-smoke-preservation/2026-10-03-8f4e985/`: preservation-before.json `83e20b6792ed999efc6c239f1440900c3e8c2f5bbbe32a4cfb13a938fa01a6b8`; preservation-after.json `dfbe00778e4df107184e331c95d9ccaa6b2cb4c30d6da81c3aee1960ab5f6332`. All 363 protected raw hashes unchanged: previous 355 plus seven completion outputs and streaming checkpoint. No private/historical overwrite or new v2 bindings.

Next bounded action: independently review this runner plus earlier combined candidate/final joins; resolve a supported pinned-Haiku token-count/cost-bound path before another run. Fresh provider diagnostics or a new claim need a new owner authorization after this required stop; no automatic restart. Official documentation can guide diagnosis, but do not silently switch to Mantle/global/another model or relax the bound. No qualified results or deployment readiness follow from this stopped smoke.

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

Review `git diff 41d146d..8373c34` plus this handoff/work log; no Claude invocation/message occurred. Prioritize (1) pinned payload/schema parity and confidence/error privacy repair; (2) default Haiku, invalid-config/real-transport/shadow rejection, no hidden model/fallback/retry and unchanged financial output; (3) the streamed decoded-body bound/early stop/context-managed closure, gzip/headers/multibyte probes, precise allocation/deadline exclusions and telemetry/cost semantics; (4) original synthetic runner's guard-before-import/mock-only/deterministic records, separately from the new isolated explicitly granted real bridge; (5) source archive path/symlink protections/no credential or runtime-attestation claim; (6) automatic CI billing removal; (7) new smoke's exact claims/limits/tier/output/pricing/CountTokens/strict budget/journal/wire permits/downstream guard and stopped actual record. Separately inspect Task B's final subject-preserving/schema/review FB joins, eligibility-only reconciliation change, unchanged reusable roles and deterministic check receipt/helper. Existing subject acceptance does not independently review final joins. Keep code, final-join, owner-run authorization and qualification dispositions distinct. Do not reopen unchanged semantic subjects or repeat historical replay merely for reassurance.

Recommended next single task: independent review of the combined four engineering commits and exact candidate inventories, with Task B final joins checked separately. The isolated smoke's owner scope/budget decision is now explicit and its stopped run is preserved; a supported pinned-Haiku input bound and new run authorization are required for any further attempt. Other operational producer/qualification decisions remain separate. Do not rerun tests or create actual evidence merely to stay busy.

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

Scope receipt: prior synthetic candidate/streaming work and authorized replacement wrappers; new isolated smoke implementation/tests, official-document reads and one authorized non-inference AWS token-count operation, which stopped before any inference. Metadata preservation/explicit-path local commits. No push, install, production/live-default change, deployment, private-data transmission/tuning, downstream model calls, AWS resource/billing changes, actual preparation/InputBinding/FreezeManifest, adoption/sealing, classification, real ranking/selection/sampling/packets, owner labeling or freeze designation. Independent candidate/new final-join review remain separate; **Freeze 1 and deployment readiness remain unestablished**.


## Successor smoke-02: exact capacity accounting and completed exploratory run

This update supersedes only the prior smoke's monetary/counting prerequisite and next-run stop point. Baseline `4d631094854fbbdb8679d36ccb81f0ba41e39e25`, branch phase0/baseline-instrumentation-eval. Source/test commit **8104705eee79c444626865cb5952a82362be497d** changes exactly experiments/jev_candidate/live_smoke.py and tests/test_jev_live_smoke.py. Codex implementation/self-review; independent review remains pending. Documentation-only delivery commit hash is reported in chat.

Owner explicitly authorized one fresh successor `2026-10-03-owner-routing-smoke-02`, gross inference ceilings $0.02 Jev/$1.33 Haiku/$1.35 combined, same six prerecorded questions/labels once per provider, sequential, zero retries, no downstream. Smoke-01 and its zero-inference result remain immutable. Live execution verified its original plan raw hash `5cf31613a34ecc87b6eabe92cd496644e4c89bc46443b699b26c36951f2f11ec` and exact cases plus both providers' complete prompt identity before dispatch. Inputs digest `21558d9dd2450cdc9b04d6f855149c71f2868ff21a3eebec3091e9aae7e0afa0`. This is an isolated owner-authorized exploratory path; production defaults and application live/shadow configuration are unchanged.

Official reads recorded 2026-10-04T01:20:55Z: AWS Haiku 4.5 model card https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html lists 200K context, exact `us.anthropic.claude-haiku-4-5-20251001-v1:0`, us-east-1 US geographic support and default Standard tier. https://platform.claude.com/docs/en/build-with-claude/context-windows explains input/output context accounting. Reserving 200000 input **plus** 256 output is deliberately conservative relative to total context; no extended context, additional model fields or tools. Current official AWS geographic table https://aws.amazon.com/jp/blogs/news/amazon-bedrock-now-supports-japan-cross-region-inference/ confirms $1.10/$5.50 per million for US geographic; https://aws.amazon.com/bedrock/pricing/ and https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html consulted. TypeSafe https://docs.typesafe.ai/models confirms jev-1.13.0, 64K total input, $0.042/M input/free output. No tax/credit/free-tier assumption.

CountTokens is removed from the runner, and its wire operation is rejected. No alternative counter endpoint added or called. Decimal-only isolated accounting reuses shared journal safety/fsync and ledger account structures without changing shared benchmark code. All money serializes as exact decimal strings in v2 plan/reservation/result records. Per-attempt reservations $0.002688 Jev/$0.221408 Haiku; full six-by-two worst case $0.016128/$1.328448/$1.344576. Pre-call reservation and durable call_started precede the single permitted dispatch. Known well-formed usage settles at verified rates; unknown/timeout/interruption retains the whole allowance. Well-formed out-of-bound usage and its actual computed charge are retained without clamping, then stop further calls; malformed usage is sanitized and retains the allowance. No floating epsilon, downward rounding or CountTokens equality check remains. Haiku prompt/Converse target/default tier/maxTokens 256, adapter streamed parsing, schema/route checks, thresholds and fallback behavior are unchanged. Boto3 total_max_attempts=1, HTTPX retries=0 and redirects=false; existing endpoint/dispatch/downstream controls remain.

Final validation **262 passed, 1 skipped, 4 existing warnings, 3.39s**, offline guard **0 intercepted/outbound attempts**. Skip is the existing Windows symlink privilege limitation; warnings are asyncio_mode/FAISS. Focused first run 31 passed/1 failed: its assertion confused an input-bound breach with monetary overrun when output use was below its allowance. Corrected expectation and added actual charge-overrun case. Subsequent integrated checkpoint 260 passed/1 skipped; final added missing Haiku usage/exact ceiling tests yielded 262. No real-population regression or Reviewer v2 tests ran. Ruff check/format and whitespace clean. Staged normalized bytes matched validated source/test bytes. Tests cover complete schedule and exact decimal settlement; nanodollar-below caps before dispatch; full unknown retention; malformed/missing/out-of-bound usage; interrupted/failed calls; no counting; no retries; no downstream calls; prompt identity; duplicate claims; streaming failure/closure and import purity. Focused-only tripwire probe intercepted one attempted network access before module preloading; none sent, and final integrated guard count is zero.

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_live_smoke.py tests/test_jev_candidate.py tests/test_router.py tests/test_agents.py tests/test_observability.py tests/test_api.py tests/test_router_bench.py tests/test_jev_candidate_tools.py -q --basetemp=.pytest_cache/jev-successor-final
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check experiments/jev_candidate/live_smoke.py tests/test_jev_live_smoke.py
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check experiments/jev_candidate/live_smoke.py tests/test_jev_live_smoke.py
git diff --check
git diff --cached --check
# Actual single successor execution, completed; do not repeat this command.
.\.venv\Scripts\python.exe -B -m experiments.jev_candidate.live_smoke --execute-owner-smoke
```

Actual run **COMPLETED**, six Jev and six Bedrock inference attempts, twelve total; no CountTokens/diagnostic inference/retry/replacement/shadow/downstream call. No stop conditions or fallback. All twelve chosen routes match the prerecorded labels. Scores below are Jev's chosen-route probability and Haiku's self-reported confidence; no calibration inference. Latencies are client-observed, including local dispatch/provider handling, **not Lambda latency**.

| Case | Provider | Chosen route | Fallback | Score | Client ms | Input/output tokens | Usage-estimated USD |
|---|---|---|---|---|---|---|---|
| Q1 | typesafe | qa | False | 1.0 | 315.188 | 407/33 | $0.000017094 |
| Q1 | bedrock | qa | False | 0.95 | 928.363 | 214/48 | $0.0004994 |
| Q2 | typesafe | qa | False | 1.0 | 109.154 | 405/33 | $0.00001701 |
| Q2 | bedrock | qa | False | 0.95 | 849.910 | 214/56 | $0.0005434 |
| Q3 | typesafe | qa | False | 1.0 | 118.123 | 403/33 | $0.000016926 |
| Q3 | bedrock | qa | False | 0.95 | 821.599 | 214/48 | $0.0004994 |
| S1 | typesafe | summarize | False | 1.0 | 136.806 | 407/35 | $0.000017094 |
| S1 | bedrock | summarize | False | 0.95 | 934.841 | 216/56 | $0.0005456 |
| S2 | typesafe | summarize | False | 1.0 | 104.936 | 405/35 | $0.00001701 |
| S2 | bedrock | summarize | False | 0.95 | 934.953 | 214/56 | $0.0005434 |
| S3 | typesafe | summarize | False | 1.0 | 116.149 | 405/35 | $0.00001701 |
| S3 | bedrock | summarize | False | 0.95 | 959.444 | 215/55 | $0.000539 |

Total reported tokens Jev 2432 input/204 output, Haiku 1287 input/319 output. Usage-estimated inference charges Jev **$0.000102144**, Haiku **$0.0031702**, combined **$0.003272344**; retained unknown reservations **$0**, outstanding **$0**, reservations exceeded **0**. Remaining ceilings $0.019897856/$1.3268298/$1.346727656. These estimates are not provider invoices. Spend stayed in the earlier small-request range, far below the capacity allowance. Jev's earlier 410-input-token estimate was $0.00010332 for six requests, close to observed charge. No exact pre-run Haiku expectation existed because original counting failed; the 52-output-token historical assumption is close to this run's descriptive mean of 53.17 output tokens. No p95/heldout accuracy/Lambda/deployment claim.

Private directory **C:/Projects/AWS Project/heldout-external/jev-isolated-live-smoke/2026-10-03-owner-routing-smoke-02/**. Raw hashes:

| File | SHA-256 |
|---|---|
| plan.json | `363b401465ac9963b03c9d097dcfee15c259242965719660a99e1c83e558c001` |
| reservations.json | `9f51ba8da74e123bc087abd87ef9386305eb71581595143d03511cb07f88c246` |
| result.json | `1bda6a377431d8138a1defe86266ce7d14c98824a345833ba9f998a9331d8a12` |
| run.journal.jsonl | `4c2332a7d012de88cb33d9630ee5deec2c548eafe51a4fa86205d3165bfb723c` |
| source-inventory.json | `36474468191434a058315d915b02074042e19435b21d13099406de4811028230` |
| completion-index.json | `24a75d888e9df6932336b7f4a64bf02515a6459d4113038f5a5c957de4f61d40` |

The journal has 26 events: run_started, twelve call_started/call_completed pairs, run_finished; no redacted events. Source inventory is the exact 56-path combined candidate/control/tool/guard/test map; digest `f34b8fcd9523319047276c6165ff4c37a019c21e61eb855095cabb3ce4fe2d73` (sorted compact ASCII JSON relative-main-path/raw-hash map plus LF). Changed raw source `34272576c008de0f8d112ba31ac4c4dc726d11f5dde60fe250231a51ac62d0d7`, test `ac4564eab20d0904ce4d2496442401c70857e2dc03d18a77365f6be05477ba8a`. App source/deployment package inputs unchanged; no package rebuild or deployment check claimed.

Durable metadata snapshot **C:/Projects/AWS Project/heldout-external/jev-live-smoke-preservation/2026-10-03-4d63109-successor/** covers **367** protected artifacts, including historical inputs/artifacts, reports, prior private wrappers and all four smoke-01 records. before SHA `b0b417f8d9fd97981b916c34fa4c7172b12bf6351bb5b5e181396c95e19d3777`, after SHA `9164b47550cbb596dd0b4f6855724a29233234182fa1d488644b3801637e655f`; every protected raw hash unchanged. Initial metadata script used an incorrect map key and stopped before creating/writing files; corrected to existing protected_files schema. Current Reviewer v2 sources/bundle remain unchanged at **e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e**; no evidence refresh/replay or protocol changes.

Focused Claude handoff: review combined router/streaming candidate, prior actual final reconciliation joins, and now `8104705eee79c444626865cb5952a82362be497d` isolated successor accounting delta. Inspect exact Decimal serialization/caps/overrun preservation, predecessor hash/prompt joins, blocked counting endpoint, reservations before dispatch, one-wire/zero-retry controls and real journal/usage settlement. Acceptance of prior subjects does not cover this code. Actual results are **EXPLORATORY_SMOKE_NOT_QUALIFICATION**. Six cases do not establish heldout accuracy, calibrated confidence, meaningful p95 improvement, Lambda behavior, qualification or deployment readiness. Live run authorization is consumed; no repeat grant inferred.

Remaining path: independent review and owner disposition of combined candidate/final joins; separately authorized qualified evaluation following accepted Reviewer v2 prerequisite/phase order; Linux/dependency and AWS deployment configuration verification with explicit operational authorization; deployment/rollback authorization only after required evidence/gates. Current production Haiku default and disabled application live/shadow remain. No additional owner decision is needed for this completed smoke, but it grants no qualification/deployment/freeze approval. No push/install/AWS resource/IAM/billing change/private-data use/adoption/selection/packets/freezes. No background work.
