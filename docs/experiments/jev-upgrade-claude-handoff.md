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


## Separate packaging delta: explicit target, offline wheelhouse, synthetic validation

Baseline **4a1e7146b083501e7429a76b8f67701dbe920bcb**; branch `phase0/baseline-instrumentation-eval`. Packaging implementation/test commit **cb58a99eb5ef8221e95c5cc1b68dfb7aeba17666**. This is Codex implementation/self-review pending independent review, separate from smoke source baseline **8104705eee79c444626865cb5952a82362be497d** and the exploratory smoke-02 evidence. No application or Reviewer v2 source changes. Prior sections and inventories retain their original subjects; this section does not refresh them.

### Actual target metadata observation

Observed **2026-10-04T03:17:42.207956+00:00**. Explicit local references (README deployment section and Visa migration runbook) identify `financial-copilot` in `us-east-1`. Used normally configured credentials without exposing their values. Exactly two read-only AWS operations: Lambda `GetFunctionConfiguration(FunctionName='financial-copilot')`, then `GetLayerVersion` for its exact attached version. Endpoint `https://lambda.us-east-1.amazonaws.com`, connect/read timeouts 2/8 seconds, `total_max_attempts=1`, no alternate identity. No STS, GetFunction, code/layer download, URL following, invocation or mutation.

| Observed field | Value |
|---|---|
| Runtime / architecture / package | python3.11 / x86_64 / Zip |
| Handler | lambda_handler.handler |
| Memory / timeout / ephemeral storage | 512 MiB / 30 s / 512 MiB |
| Function CodeSize | 5,475,624 bytes (compressed code, not current source identity) |
| Function CodeSha256 (AWS base64) | a4NBKw1a8jd3wlvvVeBc33v0J7tqLXnqsYUnO+6U0YI= |
| Configuration RevisionId | 5ce50a73-c488-4c52-8f84-c15c8fa2e542 |
| Attached layer version | arn:aws:lambda:us-east-1:981265949354:layer:financial-copilot-deps:2 |
| Layer CodeSize | 77,353,934 bytes (compressed archive) |
| Layer CodeSha256 (AWS base64) | Wwq1ZaVXgOVGBCFlK7G7HG/fNkAHcEkXJeq3AwZ24/Y= |
| Layer compatible runtime / architecture declaration | python3.11 / architecture not supplied |

Metadata confirms the repository's Python 3.11/ZIP assumptions and resolves x86_64. Root `lambda_handler.handler` differs from the source-only diagnostic's `app.lambda_handler.handler`; the repaired path explicitly supports either and the observed target requires the root copy. Neither handler nor runtime was changed. Layer contents, unpacked size, native compatibility, shadowing and actual importability remain unverified. The Linux platform string below is an explicit conservative build declaration, not an AWS-observed OS/glibc version.

### Five implementation/test files

- `scripts/package_lambda.ps1`: replace host-pip/destructive overwrite/eval-copy procedure with mandatory runtime, platform, architecture, handler, wheelhouse, lock, layer-metadata and new ZIP path arguments; invoke one focused helper and reject its nonzero exit. No deployment step.
- `scripts/lambda_package.py`: offline target/wheel/archive/source validation, isolated staging and exclusive atomic new-output publication. Does not import app, inspect credentials, contact AWS or resolve/download dependencies.
- `requirements-lambda.txt`: 26 runtime declarations reused exactly from existing pins. Includes boto3/botocore, FAISS/NumPy, FastAPI/Pydantic/Mangum and the shipped HTTPX adapter dependencies. Omits pytest/Ruff, uvicorn, unused model frameworks, evaluation and PyMuPDF indexing dependencies. It is NOT a resolved lock or evidence of Linux wheel availability.
- `tests/test_lambda_package.py`: 50 invented-workspace/wheel cases; all installers stubbed. No actual dependency assembly or app startup.
- `.github/workflows/eval-ci.yml`: separate Ubuntu/Python 3.11 guarded packaging-contract tests using test tools only. No package build, provider call or deployment job; not run remotely. Ubuntu tests alone will not establish Lambda-native compatibility.

### Build input and byte contracts (future use only)

`lambda-wheel-lock-v1` is a strict JSON object with exactly `schema`, `target`, `wheels`. `target` has exactly runtime/platform/architecture/handler and must equal the caller's explicit target. Each wheel entry has exactly `filename` (single local .whl basename) and lowercase raw-byte `sha256`. The lock must name the complete dependency closure including transitive artifacts; duplicates, unrelated distributions, incompatible versions or missing artifacts fail. The helper does not create a lock, invent wheel hashes or authenticate its author/approval. Every actual wheel is hashed and inspected, then copied and rehashed into owned staging before pip receives those exact paths.

Only explicit `python3.11` plus matching `manylinux2014_x86_64` / `manylinux_2_17_x86_64` (or explicitly declared arm64 equivalents) is supported. No host inference. Wheel filename tags, WHEEL tags, METADATA identity/Requires-Python, target-specific Requires-Dist closure and ELF class/endian/machine/ABI checks must agree. Patch/kernel-specific markers without target facts fail closed; unselected extras don't expand the runtime closure. Windows PE/.pyd/.dll, Mach-O, wrong ABI/machine, unsafe/duplicate paths, symlinks, startup .pth/customization files and package collisions fail. Header checks do not establish glibc/shared-library/CPU feature compatibility.

Layer metadata is an explicit JSON list: each object has exactly `arn`, `code_size_bytes`, `code_sha256` (AWS base64 SHA256), `compatible_runtimes`, `compatible_architectures` (lists or null). It describes caller-supplied metadata, not verified contents. No runtime dependency is omitted for a layer. With any layer, aggregate unpacked size is UNRESOLVED_LAYER_CONTENTS, not passed; layer compressed size is reported separately. A no-layer declaration is not a change to the deployed target.

The installer command uses `python -B -m pip --isolated --disable-pip-version-check install --no-index --no-deps --only-binary=:all: --no-compile --no-warn-script-location --platform <explicit> --python-version 3.11 --implementation cp --abi cp311 --target <owned staging> <exact hash-verified wheel paths>`. Subprocess exit/300-second timeout checked; captured installer output never printed. No source-build or network fallback. Installed payload must match inspected bytes; pip host launchers/bookkeeping are excluded. Dist-info RECORD is regenerated as sorted CSV for shipped files only, with urlsafe SHA256 and byte sizes, avoiding host paths after library relocation.

Exactly 16 allowlisted application source files are copied, plus an identical root handler when required. `build_index.py`, arbitrary extra app files, eval/private data, .env, caches and bytecode are excluded. AST parses against Python 3.11, mapped runtime imports must have declarations/modules, and source/requirements bytes are rechecked after installation. No app initialization/import test is performed by this builder.

`lambda-build-manifest-v1` inside the ZIP binds builder hash, target, declarations/requirements hash, canonical lock hash, resolved inspected wheel names/versions/raw hashes/requires_dist, source/file raw hashes and size/layer/check limitations. JSON: sorted keys, compact separators, UTF-8, finite numbers, trailing LF. ZIP: sorted paths, timestamp 1980-01-01, 0644 files, DEFLATE. Artifact SHA256 is reported separately to avoid a circular self-hash. Output/result status always **NOT_QUALIFIED_LINUX_EXECUTION_REQUIRED**. Code alone exceeding 250 MiB unpacked or 50 MiB compressed direct-upload envelope fails; the builder does not silently introduce S3 delivery or claim a layer solves the limit. A reviewed alternative delivery/allocation may be necessary after actual wheel size inspection.

The output must be a new .zip path with an existing parent; `deployment.zip` and all existing paths are rejected. Same-filesystem hard-link publication occurs only after validation/ZIP integrity checks and is exclusive even if another writer races. No overwrite fallback. Only the helper's owned temporary staging is removed. No real build command was executed in this task.

Future command template, **not executed**, requiring separately authorized real wheel acquisition/lock and target/layer inputs:

```powershell
.\scripts\package_lambda.ps1 -Runtime python3.11 -Platform manylinux2014_x86_64 -Architecture x86_64 -Handler lambda_handler.handler -Wheelhouse <VERIFIED_LOCAL_WHEELHOUSE> -WheelLock <COMPLETE_HASH_LOCK_JSON> -LayersMetadata <EXACT_TARGET_LAYER_METADATA_JSON> -OutputZip <NEW_EXCLUSIVE_ZIP_PATH>
```

### Final validation and preservation

On final implementation bytes:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_lambda_package.py tests/test_jev_candidate_tools.py -q --tb=short --basetemp 'C:\Projects\AWS Project\.lambda-packaging-tests-07'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B -m pytest tests/test_lambda_package.py -q --tb=short --basetemp 'C:\Projects\AWS Project\.lambda-packaging-tests-08'
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff', run_name='__main__')" check scripts/lambda_package.py tests/test_lambda_package.py
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff', run_name='__main__')" format --check scripts/lambda_package.py tests/test_lambda_package.py
git diff --check
```

Repo Python 3.13.12: **64 passed, 2 skipped, 1 warning, 2.04 s** (new packaging + existing source-only tools). Skips: two Windows symlink-privilege cases; warning: existing asyncio_mode plugin absence. Existing Windows Python 3.11.15: **49 passed, 1 skipped, 1.53 s**, no warnings (packaging only). Offline guard active, zero intercepted/outbound attempts in both. PowerShell AST parser: zero errors, without invoking the wrapper. Ruff check/format and staged whitespace passed; explicit staged inventory exactly five files, normalized staged bytes matched validation. No broad/v2/real-population suite, historical replay, Linux execution, remote CI or smoke rerun.

Earlier default pytest temporary path access failed at fixture setup (3 passed/35 errors), fixed by fresh task-owned workspace basetemp paths without guard changes. First runnable checkpoint exposed ZIP separator normalization (36 passed/1 failed/1 skipped); corrected raw-entry validation/fixture, then passed. Later self-review added target marker/extras handling, launcher exclusion, shipped RECORD checks and a Python 3.11 Windows reparse-point guard; final results above supersede checkpoints. A too-long preservation-check command failed before process creation; bounded read-only batches verified **441 unchanged paths**, including the **367** existing protected artifacts, smoke-02 six records, all application/v2 sources, legacy ZIP and preexisting untracked files. Only allowed packaging/document paths differ; no historical inventory rewritten. Temporary fixtures are disposable, not deployment artifacts.

Packaging-only five-file map digest: **af857f29fb63de2499bb715a383741380e182a3cb438cb264909cf7476f1b83e**. Recipe: SHA256 of sorted compact ASCII JSON relative-main-path/raw-file-SHA256 map plus LF. Per-file hashes:

| File | Raw SHA256 |
|---|---|
| .github/workflows/eval-ci.yml | aaa9025acfc30b7e80748fcbf96e280c968af5b5afd8abdb182272ead70f6fee |
| requirements-lambda.txt | 8f80976d5b65d73aec075259129b3bbc3f5dba2a5ff075a0a8448fc3f0795d74 |
| scripts/lambda_package.py | 35987f3d1ac22a83a8a13532648a72d0efb5e3572e9f48ae52190f63e98d6712 |
| scripts/package_lambda.ps1 | d5fa9a82c8c77c721ae004447b7da8ec4d7290af69bba7ee0824e78ec463a3ff |
| tests/test_lambda_package.py | 2332dd56eacf856818ff712c706cad8b8324b0319898f37351496816e8349072 |

Legacy deployment.zip remains **0c1e890d60eadbc08e88cd532f97b94bb8c7d853dcfb0429e0231e62631dabe0**. Current Reviewer v2 binding remains **e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e**. The old source-only diagnostic/package and smoke inventories remain at their old bindings; they were not relabeled or rebuilt. CI/tooling has this separate delta identity. No actual dependency/deployment artifact exists for the new path yet.

### Focused independent-review and next-task handoff

Review `4a1e714..cb58a99`: explicit target/lock closure and markers; raw archive/native checks; installed-byte/RECORD transformation; fixed app allowlist/layout and stale-source detection; failure-safe exclusive publication/cleanup; layer/size limitations and non-deployable status; synthetic tests and offline Python 3.11 CI separation. This is additional packaging delta review, not inherited acceptance from routing smoke or prior v2 reviews. Prior combined router/streaming/Decimal smoke and reconciliation final-join review remain separate.

Smallest next engineering task: under a separate dependency-download authorization, resolve **only** the observed Python 3.11/x86_64 conservative Linux wheel closure using existing pins, inspect/hash actual wheels and produce the supplied complete lock; report unavailable wheels or conflicting metadata instead of inventing replacement versions. Do not install/build/deploy in that acquisition task. Afterwards actual dependency assembly, exact attached-layer content/size/native/shadowing inspection and matching Linux/Lambda import/link checks need their own scope. Layer retention/allocation or >50 MiB delivery changes require concrete reviewed choices once sizes are known. Qualification, owner enablement/cost grants, rollback verification and production authorization remain prior blockers.

Scope receipt: two exact-target AWS metadata reads; scoped local code/test/CI/doc changes; invented fixtures/stubbed installers and existing offline guard; explicit-path local commits only. No dependencies downloaded/installed or real deployment artifact built/qualified; no invocation/inference, push/remote CI, resource/IAM/billing change, production/default/router/answer change, private-evidence refresh, Reviewer v2 operation or deployment. All nineteen preexisting untracked entries preserved. Freeze 1 and deployment readiness remain unestablished.

## Dependency acquisition and exact-layer inspection: incomplete closure

Baseline **5a91fa93dd10e07f88bf639f86af5c949b29b333**, same branch and confirmed financial-copilot/us-east-1/python3.11/x86_64/ZIP/root lambda_handler.handler target. This is an acquisition/static-inspection delta, not application implementation, independent acceptance or a build. Only this document and the existing work log change in Git. Requirements, packager, source/test bundles, protected artifacts and all nineteen preexisting untracked entries remain unchanged. Downloads and metadata are retained exclusively outside Git at `C:\Projects\AWS Project\dependency-acquisition\2026-10-04-5a91fa9`.

### Target, resolution and concrete blockers

Official [Lambda runtime documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html) identifies Python 3.11 as Amazon Linux 2. AWS's [runtime comparison](https://aws.amazon.com/blogs/compute/introducing-the-amazon-linux-2023-runtime-for-aws-lambda/) identifies AL2 glibc 2.26, versus AL2023 glibc 2.34. [Packaging compatibility tags](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/) specify manylinux glibc minimums. These are documented target requirements, not an executed observation of this function's libraries. Windows Python, generic Ubuntu and matching filenames alone do not prove Lambda compatibility.

Credential-free, bounded, no-redirect/no-retry HTTPX acquisition used only official pypi.org and files.pythonhosted.org metadata/wheels. No pip install, source distribution, setup hook, downloaded-code execution or host-marker resolver was used. Markers were evaluated explicitly for CPython 3.11/Linux/posix/x86_64 with no requested extras; patch/kernel-specific facts are not invented. The `3.11.0` marker placeholder is a minor-bound representation, not an observed Lambda patch version. All 26 direct release pins were preserved. Actual wheel METADATA/WHEEL, Requires-Python/Dist, extras/markers, CRC, paths and raw SHA256 were inspected. Two unconstrained transitive dependencies resolved to annotated-doc 0.0.5 and typing-inspection 0.4.4; no version-constraint conflicts were found.

**No complete lock was generated.** Successfully downloaded 26 wheels (24 direct plus two transitive), totaling **19,049,578 compressed bytes** and **32,127,232 raw wheel-member bytes**. Every raw hash matches official PyPI. Twenty-five pass the unchanged packager's static inspector. Full closure remains blocked by:

| Binding | Exact failure / smallest prerequisite |
|---|---|
| faiss-cpu==1.13.2 | Published Linux x86_64 wheel is cp310-abi3-manylinux_2_27/2_28: ABI3 can cover Python 3.11, but glibc >=2.27 cannot support AL2 2.26. No compatible binary found; no alternative pin substituted. |
| numpy==2.4.4 | Published cp311 x86_64 wheel is manylinux_2_27/2_28, likewise beyond AL2. No compatible binary found. |
| jmespath==1.1.0 | Valid py3-none-any wheel is acquired, but scripts/lambda_package.py rejects optional `.data/scripts/jp.py` with `wheel_data_scheme`. This is a packager-policy limitation, not unavailable or ABI-incompatible JMESPath. |

Exact official sources: [FAISS files](https://pypi.org/project/faiss-cpu/1.13.2/#files), [NumPy files](https://pypi.org/project/numpy/2.4.4/#files), [PyPI metadata API](https://docs.pypi.org/api/json/). Only digest-verified PEP 658 metadata was downloaded for the two incompatible wheels; their binaries were not fetched. FAISS metadata requires NumPy >=1.25.0,<3 and packaging, satisfied as version constraints by the declarations; availability/platform compatibility is the blocker. Native Pydantic Core 2.46.3 is ELF64 x86_64/cp311, maximum observed required GLIBC_2.14; system shared-library resolution remains unexecuted.

Minimal reproduction, read-only and guarded, of the separate packager restriction (not repaired here):

```python
from pathlib import Path
from scripts.lambda_package import inspect_wheel, target_contract
inspect_wheel(Path(r'C:\Projects\AWS Project\dependency-acquisition\2026-10-04-5a91fa9\wheels\jmespath-1.1.0-py3-none-any.whl'), 'a5663118de4908c91729bea0acadca56526eb2698e83de10cd116ae0f4e97c64', target_contract('python3.11', 'manylinux2014_x86_64', 'x86_64', 'lambda_handler.handler'))
# PackageError: wheel_data_scheme
```

### Bound layer contents and allocation

Retrieved only `arn:aws:lambda:us-east-1:981265949354:layer:financial-copilot-deps:2`. Download completed **2026-10-04T20:14:24.191472+00:00**. Two bounded GetLayerVersion metadata calls, one archive transfer: initial overly specific S3 bucket-name validation stopped before transfer; a fresh response was checked against the exact ARN/hash and official service-provided HTTPS S3 endpoint. Signed URLs and raw sensitive AWS responses were not persisted or printed; no identity switch or other AWS operation.

Archive `financial-copilot-deps-v2.zip`: **77,353,934 bytes**, raw SHA256 **5b0ab565a55780e5460421652bb1bb1c6fdf36400770491725eab7030676e3f6**, equal to expected AWS base64 **Wwq1ZaVXgOVGBCFlK7G7HG/fNkAHcEkXJeq3AwZ24/Y=**. Before decompression, bounded paths/count/member/total size were validated; subsequent streaming reads verified every member's CRC/hash/size. No extraction or import. **1,658 entries**, sole root `python/`, **235,542,530 unpacked bytes**, no unsafe/duplicate paths, symlinks or encrypted members.

Distributions: NumPy **1.26.4**, FAISS-cpu **1.7.4**, PyMuPDF **1.23.8**, PyMuPDFb **1.23.7**. First two conflict with declared versions; last two are indexing dependencies excluded from current application runtime declarations. Thirty-three ELF native files are 64-bit little-endian x86_64, cp311 where indicated, with maximum observed required GLIBC_2.17. External NEEDED libraries include libc/libm/libpthread/librt/libdl/libutil/libz/libgcc_s/libstdc++ and the loader. Actual target resolution, CPU dispatch (including FAISS AVX2 variant) and imports remain untested. Distinct FAISS/NumPy copies share libgfortran and libquadmath basenames but have unequal hashes; duplicate fitz/fitz_new libmupdf copies have equal hashes. Loader-order compatibility is unresolved, not a confirmed execution failure.

[AWS import precedence](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html) places /var/task before layer paths. Function-bundled FAISS/NumPy would shadow older regular layer packages; partial packages must not assume file-by-file fallback into layers. Layer metadata/runtime declaration alone did not prove contents, and the inspected old versions cannot replace declared pins without separate approval.

[AWS quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html): direct ZIP upload 50 MiB compressed; larger uploads use S3; total unpacked code plus layers is 250 MiB (262,144,000 bytes). Existing layer leaves **26,601,470 bytes**. Just the immutable nonmetadata/non-.data payload of 25 accepted wheels is **31,247,974 bytes**, a known lower bound. Combined lower bound **266,790,504 bytes** exceeds the ceiling by **4,646,504 bytes**, before application files, other metadata, JMESPath or missing FAISS/NumPy. No function ZIP was assembled, and these are not its final sizes.

Recommended allocation is conditional **complete function-bundled closure, with explicit omission/detachment of this old layer in a later reviewed and authorized target change**, avoiding unused PDF payload and mixed versions. No precise current layer/function split satisfies the preserved pins. This recommendation cannot proceed until native version/runtime decisions and compatibility evidence are resolved. Nothing was removed, attached, published or deployed. Future >50 MiB compressed delivery, if needed, requires a separately authorized S3 path; aggregate unpacked limits still apply.

### Evidence, replay and focused next task

All paths below are under the outside-Git task directory. `completion-index.json` binds 78 retained raw artifacts (wheels, official metadata, sanitized layer metadata, archive, static reports and local inspection helpers). Index excludes itself and the later technical receipt to avoid self/circular hashes. Reports preserve limitations rather than naming the partial set a lock.

| Record | Schema / raw SHA256 |
|---|---|
| completion-index.json | lambda-dependency-acquisition-completion-v1 / **9d1fa15812cc78eb5618b59e689797a580155d81d3ea053b027807962c07ab24** |
| dependency-acquisition-final.json | lambda-dependency-acquisition-final-v1 / **b708fba864f80dac66a1b960030da3a00c55653cbbea9e954edcb957aceee608** |
| layer-static-inspection.json | lambda-layer-static-inspection-v1 / **371a6b3ed07292d3a8a09b3676263409d94a70a0646c7b6affb4bbc60c9fea23** |
| technical-check-receipt.json | lambda-acquisition-technical-check-v1 / **396140188bbbdfc46b4b3013fe43cce9a54c90041ba13c50d191fdc689754c05** |
| jmespath-packager-reproduction.json | **db0074a5dd8a9c5ee8c335eaf75043ed43a35634f01ff2c0cfbd9cc2a6f9bbeb** |
| read_only_replay.py | **4011c70282290d401eec979940aa8cdce4171061ba0603cbb7d579b7515dcd44** |

Executed reproducible static replay:

```powershell
.\.venv\Scripts\python.exe -B 'C:\Projects\AWS Project\dependency-acquisition\2026-10-04-5a91fa9\read_only_replay.py'
```

Result **STATIC_REPLAY_PASSED_NOT_QUALIFIED**: 78 artifact hash bindings, complete layer CRC/hash/size checks, 25 unchanged-packager wheel successes, exact JMESPath `wheel_data_scheme` rejection, incomplete closure `dependency_closure` rejection; existing offline guard reports zero network attempts. No application or downloaded code imported. A prior local helper diagnostic accidentally reran static inspection and hit exclusive FileExistsError before overwriting any record; function-only ELF reader and final replay avoid that side effect. No full pytest suite is warranted by acquisition/documentation only; whitespace and explicit staged-byte/prefix checks apply to this doc delta.

Preservation: 446 non-document baseline paths rehashed with zero changes; app/packager/pins, preexisting untracked entries, old ZIPs, all protected evidence/smoke/review records remain unchanged. Packaging digest **af857f29fb63de2499bb715a383741380e182a3cb438cb264909cf7476f1b83e**, Reviewer v2 digest **e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e**, legacy deployment.zip **0c1e890d60eadbc08e88cd532f97b94bb8c7d853dcfb0429e0231e62631dabe0** remain at their prior identities; no old inventories refreshed.

Single smallest independent offline implementation task, under new scope: narrowly support safe exclusion of optional wheel `.data/scripts` payload in the existing packager, with the verified JMESPath fixture and synthetic regressions; retain rejection of other unsupported schemes, unsafe paths and runtime omission. No broad framework rewrite. Separately, owner must choose approved AL2-compatible FAISS/NumPy pins or a reviewed runtime migration before a complete lock can exist; this task supplied neither substitution nor approval. After those prerequisites: reacquire/hash the revised closure, complete lock, then separately authorized assembly and matching Lambda/Linux import/link/startup checks. Independent packaging/candidate review, qualification and operational deployment gates remain.

Scope receipt: official metadata/docs and 26 binary-wheel downloads, two exact-layer metadata reads/one archive download, bounded static inspection and guarded replay, two appended docs/local commit only. No installation, source build, dependency assembly, downloaded-code execution, real deployable artifact, application import, inference/invocation, production/default change, AWS mutation, push, Reviewer v2 change or historical evidence refresh. Static identity/metadata compatibility is not Linux importability or deployment readiness.

## Optional JMESPath CLI repair and AL2 pin research (pending independent review)

Baseline **976d7b89d308424ef9c769a57d5948546fd8892a** matched, same branch. Separate source/test repair commit **a7ec6ae680d8da45b0d3815f6eb43dd98745cf64** changes only scripts/lambda_package.py and tests/test_lambda_package.py. This is Codex implementation/self-review pending Claude acceptance; no dependency declarations, application/runtime/layer configuration or v2 sources change.

JMESPath's acquired wheel raw hash remains **a5663118de4908c91729bea0acadca56526eb2698e83de10cd116ae0f4e97c64**. Baseline `wheel_data_scheme` rejection was reproduced before editing. Actual wheel has eight library modules, one `.data/scripts/jp.py` CLI, no entry_points.txt, and a RECORD row binding the 1,685-byte script. Static source inspection found no application CLI use; acquired boto3/botocore modules import/use jmespath library APIs, without referencing jp.py. No SDK or library code was executed.

Selected policy is an explicit Lambda runtime subset, not a full unmodified installation. Only jmespath 1.1.0's exact `jmespath-1.1.0.data/scripts/jp.py` is excluded, with script hash **3c33be32db89ef63e1efceabd80c34e70679ab6d86260b9ebfd1b4c415e8388f**, exact RECORD hash/size row and absence of entry-point metadata required. Other scripts/versions/schemes are rejected. Native, link/type, unsafe path and collision checks run before exclusion; same-wheel and cross-wheel collisions with bin/jp.py or Scripts/jp.py fail. If installer output includes those paths, only the original or installer-interpreter shebang (LF/CRLF line ending) and byte-identical remaining body pass; changed body/shebang fails `excluded_script_output_mismatch`. No arbitrary script is executed or shipped. Existing generated-launcher/bookkeeping policy is unchanged.

Manifest gains `installation_policy=RUNTIME_SUBSET_WITH_DECLARED_OPTIONAL_CLI_EXCLUSIONS` and per-wheel `excluded_files` with wheel_path/raw hash/reason/installer_paths. All required library bytes remain verified. Shipped RECORD is regenerated over precisely the retained paths, excluding the CLI, and manifest file hashes bind that RECORD. [Official wheel specification](https://packaging.python.org/en/latest/specifications/binary-distribution-format/) distinguishes `.data/scripts` relocation/shebang rewriting and installed RECORD updates; this build deliberately reports its subset policy. Target/closure/source/publication contracts remain enforced.

Added 26 synthetic cases using invented script/library bytes (only the test's policy digest is rebound): exact layout, all eight library modules, manifest/RECORD hashes, deterministic synthetic output, absent/Linux/Windows-style installer script output, LF/CRLF shebang rewriting, changed/missing libraries, altered script output, unrelocated scripts, traversal/nested/unknown scripts, unsupported headers, destination collisions, executable/unreviewed content, extra entry points, bad original RECORD, other distributions, symlink/FIFO/directory entries. All installers are stubs; no real wheel install or native import.

Final implementation validation:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_lambda_package.py tests/test_jev_candidate_tools.py -q --tb=short --basetemp 'C:\Projects\AWS Project\.lambda-script-tests-04'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B -m pytest tests/test_lambda_package.py -q --tb=short --basetemp 'C:\Projects\AWS Project\.lambda-script-tests-05'
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check scripts/lambda_package.py tests/test_lambda_package.py
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check scripts/lambda_package.py tests/test_lambda_package.py
git diff --check
git diff --cached --check
```

Repo Python 3.13.12: **90 passed, 2 skipped, 1 existing asyncio_mode warning, 2.80s**. Existing Windows Python 3.11.15: **75 passed, 1 skipped, 2.22s**, no warnings. Skips are existing Windows symlink-privilege limitations; synthetic link/type probes pass. Guards report zero intercepted/outbound attempts. Initial checkpoint 72 passed/1 skipped; final self-review added non-regular-script probes and Windows shebang-line handling, with final results above. Ruff/format/whitespace and staged-byte checks pass. Actual acquired wheel now passes guarded static inspection: **13 retained files, eight library modules, one exact exclusion**, all retained bytes unchanged. This establishes neither installation nor Linux importability.

New records are separately retained under `C:\Projects\AWS Project\dependency-acquisition\2026-10-04-976d7b8`, not Git or the prior acquisition directory. Final real-wheel check `real-wheel-final-static-check.json` raw hash **0e63aa2f6c04cb34e6894b1643b4082466da6d7f62e2311fc3c68f0eaf1ac527**; candidate metadata report `compatibility-metadata-report.json` **7d68230a3ab6f6818aab3e1c67fee063029b3b2807799886b08ccf472474c403**. The earlier checkpoint record is retained separately. Prior acquisition index/rejection/static receipts remain unchanged historical outcomes against their original inspector, not relabeled as current results; the old expected-rejection replay was not rerun or rewritten.

### Metadata-supported pin recommendation only

Public official PyPI JSON was read for FAISS 1.8.0.post1/1.9.0/1.10.0/1.11.0 and NumPy 1.26.4. No additional wheels, sources or layer archives were downloaded. For the unchanged Python 3.11/AL2/glibc 2.26/x86_64 target:

| Candidate | Published CPython 3.11 x86_64 wheel / constraints | Assessment |
|---|---|---|
| **FAISS 1.9.0 + NumPy 1.26.4** | Both cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64; FAISS Python>=3.9, NumPy>=1.25,<3 plus packaging; NumPy Python>=3.9 | Preferred candidate for further verification; published tags/requirements fit. |
| FAISS 1.8.0.post1 + NumPy 1.26.4 | Same compatible tags; FAISS Python>=3.8, NumPy>=1,<2 plus packaging | Conservative alternative with explicit NumPy 1.x cap; older FAISS release. |
| Examined FAISS 1.10.0/1.11.0 | cp311 x86_64 Linux wheels require manylinux_2_28 | Rejected for current AL2 baseline, despite satisfactory Python/version constraints. |

Official references: [FAISS 1.9.0 metadata](https://pypi.org/pypi/faiss-cpu/1.9.0/json), [NumPy 1.26.4 metadata](https://pypi.org/pypi/numpy/1.26.4/json), [FAISS 1.8.0.post1 metadata](https://pypi.org/pypi/faiss-cpu/1.8.0.post1/json), [manylinux requirements](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/). Candidate wheel identities published in metadata, NOT binaries acquired or inspected:

- faiss_cpu-1.9.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl: **27,474,817 bytes**, published SHA256 **2baeed5f1d8b006533c71184cc29065892647774a3df9c6f6dc31c1b694f57fa**.
- numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl: **18,252,005 bytes**, published SHA256 **666dbfb6ec68962c033a450943ded891bed2d54e6755e35e5835d63f4f6931d5**.

Wheel-maintainer [v1.9.0 build declarations](https://raw.githubusercontent.com/faiss-wheels/faiss-wheels/v1.9.0/pyproject.toml) use NumPy>=2,<3 for build, while declaring runtime NumPy>=1.25,<3. That is declared support, not an observed binary ABI test. [NumPy troubleshooting](https://numpy.org/doc/stable/user/troubleshooting-importerror.html) documents the 1.x/2.x extension ABI boundary. Retaining NumPy 1.26.4 avoids assuming older 1.x-built extensions support 2.x. The alternative [post1 release](https://github.com/faiss-wheels/faiss-wheels/releases/tag/v1.8.0.post1) explicitly added NumPy<2 and packaging, without functionality changes. FAISS 1.9.0 dates to 2024; [NumPy 1.26.4 release notes](https://numpy.org/doc/stable/release/1.26.4-notes.html) describe it as the last planned 1.26.x release. Maintenance age/later fixes require review; no security-support or all-version compatibility claim.

Application source uses read_index/ntotal/search in app/services/retriever.py with np.array(dtype=np.float32). Indexing source app/services/build_index.py uses IndexFlatIP(1024), add/write_index and float32 arrays. These APIs predate the blocked declared versions and are represented in upstream [FAISS 1.9.0 tutorial](https://github.com/facebookresearch/faiss/blob/v1.9.0/tutorial/python/1-Flat.py) and [index I/O documentation](https://github.com/facebookresearch/faiss/wiki/Index-IO,-cloning-and-hyper-parameter-tuning). No source-level dependency on FAISS 1.13.2 or NumPy 2.4.4 was found in the shipped runtime. Indexing/migration scripts are distinct from application startup.

Non-sensitive local provenance in docs/runbooks/visa-source-migration.md records IndexFlatIP, dimensions 1024, ntotal 2220 and index SHA256 **3d2b3ebd4f992aad3c2be8a09761a18fbc9a17d08d63db99bf6853697abfa5e9**, with historical object timing. It does not identify the generating FAISS version or prove today's S3 bytes. No S3/index/financial content was read or deserialized here. No general cross-version serialized-index guarantee was established. Upstream I/O docs require integrity verification before loading; shared API names and this historical hash alone cannot prove candidate read compatibility.

Before approving a pin change: independently review this recommendation/maintenance tradeoff; authorize candidate wheel acquisition, verify actual METADATA/RECORD/native libraries and complete closure; then authorize isolated matching AL2/Python 3.11/x86_64 imports, shared-library/CPU-dispatch checks and synthetic IndexFlatIP add/search/read-write checks. Separately authorize an integrity-bound load of the existing trusted index, validate dimensions/type/ntotal/metadata alignment and retrieval equivalence without model calls; resolve missing writer provenance rather than presuming it. Review complete function/layer allocation and final unpacked sizes. No real lock can be issued from this metadata-only research, and no pins or target were changed. Existing old-layer mismatch/size problem remains.

Current five-file packaging digest **5470c4fef2e19213a4d3ee0f67f21bc9f40e2fce9818f619984d2b69a716dd5f**, same sorted compact ASCII relative-path/raw-SHA256 map plus LF recipe. Changed helper **697e981f986bd56e8e8c49a52bf6a362705dd4933a14b521facf87f9cbdd5d21**; test **50a7eeb20b10bd14d3fb708e7e4f5e667839143dc0982d76318c37561c00bb4d**. Prior packaging receipts/digest remain historical. Reviewer v2 digest **e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e** unchanged. Rehash checks: 444 prior protected/unrelated paths and 261 current baseline paths (overlapping sets), zero differences; includes all 80 prior acquisition files. Prior nineteen untracked entries preserved.

Claude delta-review focus: exact version/path/content/RECORD exclusion gate; installer shebang normalization and collision checks; explicit subset manifest and shipped RECORD; synthetic coverage/static real-wheel result; evidence versus recommendation distinctions, maintenance/ABI/index uncertainties. This packaging delta is separate from router/smoke/v2 review. Scope receipt: two source/test changes and two appended docs, synthetic/stubbed checks and official metadata/docs only; no dependency changes, additional binary downloads, installs, native/application execution, real assembly/build, AWS/model calls, layer/configuration change, deployment/push or v2/evidence refresh. Stop after this repair/recommendation.

## B-1 SDK attempt telemetry correction (pending narrow independent review)

Owner task baseline **bc560feb02c57c7f36dd0f147a5a9d28832d0cbb**, branch phase0/baseline-instrumentation-eval, matched. Actual consolidated Claude report docs/experiments/jev-upgrade-claude-consolidated-review.md, raw SHA256 **cee98d216e60fcc22186d234e8228cbd2d41ce58c5a9433fb73359db5888a78e**, remains unchanged and untracked. That report accepts scopes A, C and D at their exact reviewed bindings and accepts B except B-1. This appended delta supersedes the earlier pending-review wording only for those reviewed scopes; it does not claim Claude accepted this fix or authorize qualification/deployment.

Separate implementation/test commit **9ae51946c9f7bfa346d7acde38b7813bd7b0666a** changes three files:

- app/agents/router.py: replace unconditional 1 with SDK-reported attempts from successful response or ClientError.response, captured before usage/output parsing. Exact built-in nonnegative int RetryAttempts yields 1 + retries; bool, string, float, negative, missing/non-object metadata yields None, serialized as existing JSON null. Extraction never invokes custom mapping methods. Reset unknown on every route call; an SDK ParamValidationError that rejects parameters before dispatch records factual zero. Transport failures without usable metadata remain unknown. No production send hook or universal failure-measurement claim.
- tests/test_router.py: real botocore retry decisions, signing and response/error parsing with an in-process before-send stub; explicit test-only legacy five-attempt cap, invented credentials, isolated absent config/credentials paths, temporarily cleared AWS_MAX_ATTEMPTS/AWS_RETRY_MODE, local sleep stub, restored hooks/environment. The existing DNS/socket/HTTP guard stays active. Tests cover no retry, throttling/success, exhaustion, malformed final output, strict malformed metadata, ClientError metadata, unknown transport failure, per-call reset, schema-failure preservation, factual pre-dispatch zero and non-throwing extraction. Assertions cover fallback and sanitized logging.
- tests/test_jev_live_smoke.py: successful fake SDK responses now supply realistic RetryAttempts=0. Three new cases prove the unchanged isolated runner stops on missing metadata, bool or two reported attempts, with no following requests. Its existing known-usage settlement precedes this gate and remains unchanged. The runner source is not modified; no consumer coerces unknown to one or zero. Observability already preserves null; the existing runner's ==1 gate correctly fails closed.

Reproduced B-1 before implementation using the real retry machinery:

| Explicit synthetic policy/case | Observed stub sends | Before telemetry | Fixed telemetry |
|---|---:|---:|---:|
| No retry, successful output | 1 | 1 | 1 |
| Two throttles, then success | 3 | 1 | 3 |
| Exhausted test-only five-attempt cap | 5 | 1 | 5 |
| Two throttles, then malformed model output | 3 | 1 | 3 |

Five is the fixture's verified policy, not a universal production configuration. SDK metadata is the count's evidence, not a measurement of every possible send/failure. Constructor/client retry configuration, environment behavior, model/prompt, output schema, threshold, fallback, classification, pricing/usage logic, Haiku default and Jev restrictions are unchanged. Optional B-2/B-3/B-4 findings are not amended.

Exact commands:

```powershell
# Intentional pre-fix reproduction: 3 failed, 1 passed, 20 deselected.
.\.venv\Scripts\python.exe -B -m pytest tests/test_router.py -k sdk_retry_sends_match_attempt_telemetry -q --tb=short --basetemp 'C:\Projects\AWS Project\.b1-router-tests-01'
# Final formatted implementation bytes, before staging/commit:
.\.venv\Scripts\python.exe -B -m pytest tests/test_router.py tests/test_observability.py tests/test_jev_candidate.py tests/test_jev_live_smoke.py -q --tb=short --basetemp 'C:\Projects\AWS Project\.b1-router-tests-05'
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check app/agents/router.py tests/test_router.py tests/test_jev_live_smoke.py
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check app/agents/router.py tests/test_router.py tests/test_jev_live_smoke.py
git diff --check
git diff --cached --check
```

Final result: **169 passed, 4 warnings, 2.28s**, Python 3.13.12, zero intercepted/outbound network attempts. Warnings are existing unknown asyncio_mode plus three SWIG deprecations. Intermediate integrated runs exposed missing retry metadata in old runner fakes (153 passed/12 failed) and an incorrect new-test expectation of retained reservation despite known usage (166 passed/3 failed); only test fixtures/assertions changed to reflect the existing SDK/accounting behavior. Final tests, Ruff and formatting/whitespace checks pass, no unresolved test failure. Staging was explicit-path only; staged bytes equal validated working bytes after Git's CRLF-to-LF normalization. No broad suite, historical replay, real-population test or live smoke was run.

New metadata-only inventory outside Git: **C:\Projects\AWS Project\jev-b1-telemetry\candidate-source-inventory.json**, raw SHA256 **9fa958da4a42b99ae134a2ff18a72192ba342da8df53d5308d3a79f1a85befe9**. Groups use SHA256(sorted compact ASCII JSON relative-path/raw-file-SHA256 map plus LF). This is candidate source identity, not a package manifest or build:

| New binding | SHA256 |
|---|---|
| app/agents/router.py raw bytes | **177d1f5e99a547d25b69f90d39856ea5fdfc97160c15ca36dc58e737b0a34e18** |
| tests/test_router.py raw bytes | **18bd2e6d95907067ef825664702153900338ca21d4973c6030c63d59dbda41db** |
| tests/test_jev_live_smoke.py raw bytes | **b03b58cb7d2736e02b1dbbe242b026da285569c04b6ff64ff6c3493a9cec3b57** |
| Three-file B-1 delta | **0ad6463b4534c830d5e706042db1b77a9e6f3612c9c44f323333ccbac021fe16** |
| 16 app sources enumerated by unchanged packager SOURCE_NAMES | **a446220cb3bd58c80c9ed2864620e7e9a3508f83ccf9e9cb5187d80140349420** |
| Current 56-path combined app/control/tool/guard/benchmark/test map, same path set as smoke-02 | **ccd8f85b9f40f0cf98429444eb5e65bc7f724cd1460dbda68bdefb48a38c3ae8** |
| Unchanged five-file packaging digest | **5470c4fef2e19213a4d3ee0f67f21bc9f40e2fce9818f619984d2b69a716dd5f** |
| Unchanged 17-source Reviewer v2 verification digest | **e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e** |

Old smoke inventories/results/claims, source-only package receipts and protocol evidence remain bound to their historical bytes. App source identity changes for a future candidate; no artifact was built or historical receipt rewritten. Reproduction helper C:\Projects\AWS Project\jev-b1-telemetry\inventory_check.py reads hashes only, with the guard active; its output files use exclusive creation and are not overwritten on re-entry. It imports only guard/pure verifier constants, calls no preparation or evidence-verification entry point.

Preservation: **533 distinct protected/unrelated files unchanged**, union of 271 retained current-baseline entries and 441 retained prior-preservation entries; sets overlap. The sole additional authorized exception in the 272-entry baseline is the isolated runner's test fixture file, not its source or evidence. Original maps remain untouched. New preservation-after.json SHA256 **ce20eb7c47233648de9596ea992919dfe7366136aecf68d9a2152991b239a870** in the same directory; before raw hash **9fe57bcbb5ac5e174d1fe32ca7ec8a3c4997a303be4e63adaa50c47710420546**, extra-before raw hash **a769702ccf35755bb2efe7efce403b8aa6ab39cd91cf6b5c1638ff6527fa04b2**. All twenty preexisting untracked entries, including the actual consolidated review, remain preserved and excluded from staging.

Focused Claude B-1 follow-up: inspect the three-file implementation/test delta, strict SDK count/unknown/pre-dispatch semantics and preservation before parse/schema failure; replay the four real-retry stub cases with guards/config restoration; inspect unchanged runner gate and realistic fake metadata. Codex implementation/self-review only, independent acceptance pending. Existing pin/target, native import/index, qualification and operational authorization requirements remain; this task resolves none of those or the optional findings. Scope receipt: three source/test files and two appended documents, offline tests/hash metadata and scoped local commits only. No AWS/provider calls, inference, downloads/install, build/deployment, production/retry/routing change, push, Reviewer v2 modification/evidence refresh or historical evidence mutation. Stop after B-1 delivery.
