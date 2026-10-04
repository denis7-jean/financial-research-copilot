# Jev upgrade autonomy work log

Window authorized 2026-10-03; baseline `41d146db2e8d3973c3abb2668e1c7a4d969d4f8f`, branch phase0/baseline-instrumentation-eval. No AGENTS.md found in repository or workspace/ancestor locations. Read CLAUDE.md as project guidance; its Python 3.11 deployment target differs from the existing Python 3.13.12 verification environment. No environment change/install is authorized.

## Actual starting state and working plan

**A: deployment engineering.** Existing isolated benchmark has a pinned Jev HTTP client, schema checks, strict reservations, journal, seeded scheduling and metrics. Phase A is completed: 343 calls each to Haiku/Jev, 340 rules calls, estimated $0.171651; Jev 31/31 clear questions, local p50 123.6 ms versus Haiku 30/31 and 911.9 ms. This is in-sample evidence, not held-out qualification or Lambda latency. App dispatch still uses Haiku alone. Implement a mock-transport-only binary adapter and explicit fail-closed configuration, preserve threshold 0.6 -> qa and single-call behavior, exercise unchanged downstream dispatch, then complete offline packaging/configuration/rollback checks. No production/live/shadow mode becomes enabled.

**B: Reviewer Protocol v2.** Actual tenth Claude report and three private review files exist in 2026-10-03-claude-41d146d-reconciliation-refresh. Actual raw review says ACCEPTED and binds subject 5ecea37ee945023f77266f6cc9d15ad5e8c7db6d3442c24f69a2112892e0cf78; raw 6d5d691a6ff7a76bd9cc0c7c200ef56c254cd071312b89d975499ae6f2edfcbf, typed 6392f170e5d2bd52cd2efb1abacca58ff2bd1bb6953a705bb60eff27c692360e, index 600fb54a869d73a7585e2eb2fee0162001589a2665d40bc5c35009fb54e8e473. Canonical schema, UTC/raw/subject/contract/lemma/counts joins checked offline. Final wrappers/full chain and Freeze 1 remain pending. Leave the seventeen verification sources and accepted protocol semantics unchanged. Reviewer-qualified labels, external hold-out comparison and end-to-end/Phase B gates remain prerequisites to qualification/rollout, not prerequisites to synthetic app engineering. No actual wrappers, preparation or operational producer is assembled in this window.

**C: optional/outside critical path.** Multi-head Decision Layer ADR is Proposed: new taxonomy, grounded summarizer, company filtering, Sonnet, decomposition, Haiku-secondary fallback/circuit breaker/shadow policy need separate design/product decisions. Do not implement them or tune on heldout content. Optional preflight tests/catch-all are not part of this candidate.

Consolidate related code, run focused success/failure checks per batch and one integrated offline checkpoint, label Codex self-review explicitly, then measure source/test closures and write one combined handoff. Multiple explicit-path local commits authorized; no push. Stop when only review, owner decisions, external calls or operational actions remain. No promise of background work after the session.

## Preservation and billing boundary

Durable metadata-only snapshot: heldout-external/jev-upgrade-preservation/2026-10-03-41d146d/preservation-before.json. It includes existing protocol protection membership, actual new review/refresh artifacts, ten reports, proposed draft, archived Phase A/verification/baseline records, frozen benchmark code and pre-existing user files. Candidate source hashes are recorded separately as a mutable baseline. No .env credential contents are read.

Local reviewer-trial-v1.2-preflight section 7 records an earlier read-only report of Free plan expiry 2026-10-13 versus owner-reported credit expiry 2027-04-13; applicable model coverage remains unconfirmed. These are historical local records, not current verified expiry/credit coverage. The approximate ten-day planning window authorizes no charges or calls.

## Batches and resume point

### Batch 1: binary adapter and integration

Implemented app-only pinned Jev schema/payload parity, finite binary confidence, strict JSON, response-size and HTTP/timeout failure checks, fixed-code nonfatal errors, one-attempt qa fallback, choice-probability threshold and usage/latency/cost metadata. No credential input or real transport exists. Explicit environment configuration defaults to Haiku; Jev without exact MockTransport and every shadow configuration reject before routing. Orchestrator's existing output/dispatch contract is retained. Haiku malformed-confidence outputs now reject rather than allowing nonfinite/out-of-range/bool/string values; valid prompt/model/threshold behavior is unchanged. Parse failures no longer log provider output via validation exception strings. Haiku gets usage-based cost/latency telemetry at the historical list-price assumptions; unknown usage/model remains unknown, not zero.

Tests: `.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_candidate.py tests/test_router.py tests/test_agents.py tests/test_observability.py tests/test_api.py tests/test_router_bench.py -q --basetemp=.pytest_cache/jev-candidate-batch1-formatted`: **200 passed**, zero intercepted/outbound calls, including post-format repeat. Initial run: 190 passed/two setup errors due to Windows path lengths from autogenerated large fixture IDs; explicit short IDs fixed both. Existing asyncio_mode and FAISS SWIG warnings remain. Guarded Ruff format/check passed on five app files/new test. Formatting changed surrounding existing router/orchestrator layout; diff self-review confirms no retrieval/generation edits or changed dispatch decisions.

Codex self-review (not independent acceptance): accepted binary payload/response parity with frozen benchmark, no added Haiku-secondary call/retry, no real provider construction from Jev configuration, no private content in telemetry, and three new modules import without clients/.env reads. Known limits: injected MockTransport handlers are trusted test code, not a sandbox; configured HTTP phase timeouts are not a demonstrated whole-request deadline; probabilities/prices are not verified/calibrated. Next: synthetic run reproducibility, source-only packaging/config checks and offline CI safety.

### Batch 2: reproducible smoke, package checks and offline CI

Implemented six deterministic invented Jev/Haiku comparison scenarios, with twelve mock attempts, no provider calls, no latency/accuracy qualification claim and no output files. Existing benchmark/control code is unchanged. New source-only packager validates explicit nonsecret candidate defaults, checks Python 3.11 syntax, deterministic names/timestamps/permissions/raw hashes and bounded source reads, and constructs an in-memory ZIP. It excludes eval inputs/archives, credentials, JSON data and tests; includes no dependencies and labels itself NOT_DEPLOYABLE_DEPENDENCIES_NOT_INCLUDED. Configuration assertions are not actual environment observations. CLI performs diagnostics only; no write/install/deploy option. Existing package_lambda.ps1/deployment.zip remain untouched.

Removed automatic credential-bearing smoke/judge and deploy-ready jobs from push/PR CI. Offline jobs use the verification runtime, guard, no real-population regression, lint and synthetic smoke. CI was inspected locally, not invoked. Python 3.11 Linux execution/dependencies remain unverified; changing CI's verification interpreter does not change the production runtime/default.

Commands/results:

- `.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_candidate_tools.py tests/test_jev_candidate.py tests/test_router_bench.py -q --basetemp=.pytest_cache/jev-tools-final`: **107 passed, 1 skipped**, zero intercepted/outbound attempts. Native symlink creation denied by Windows; a separate simulated symlink regression passes.
- `.\.venv\Scripts\python.exe -B -m pytest tests/ eval/ -m "not llm and not integration" -k "not test_accepted_population_regression" -q --basetemp=.pytest_cache/jev-integrated`: **1259 passed, 1 skipped, 6 deselected**, 97.30s; **16 guard-probe attempts intercepted, none sent**. Includes golden serialization/payload, source/dependency/import checks and relevant v2/benchmark regressions. Four existing warnings (asyncio_mode plugin unavailable, FAISS SWIG). During this run package scope was narrowed from app+eval to app only; final package-focused rerun below verifies those final bytes. No app/verifier behavior changed afterward.
- `.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_candidate_tools.py -q --basetemp=.pytest_cache/jev-tools-package-final`: **15 passed, 1 skipped**, zero attempts, after the archive narrowing/explicit assertion.
- `.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check conftest.py app/ eval/ tests/ scripts/ experiments/`: passed.
- Same guarded Ruff entry, `format --check app/agents/router.py app/agents/orchestrator.py app/agents/jev_router.py app/agents/router_configuration.py app/agents/routing_contract.py tests/test_jev_candidate.py tests/test_jev_candidate_tools.py experiments/jev_candidate scripts/candidate_package.py`: ten files formatted.
- `git diff --check`: passed. `python -B -m scripts.candidate_package --config scripts/jev_candidate_config.json` (existing .venv): passed, source archive calculated in memory only.

Codex self-review: static code/diff and targeted failure checks, not independent acceptance. No modification to financial answer/retrieval code, existing benchmark algorithms, v2 source/tests/contracts or historical data. Scope-only package is not a dependency lock, Python sandbox, build attestation or deployment artifact. CLI invalid/missing filesystem inputs emit fixed codes without exception paths. Synthetic Haiku throttling scenario is a generic failed mock; it does not simulate Bedrock's complete HTTP/error classification. Existing exact provider failure probes remain in regressions. No undocumented automatic retry or secondary model was added; legacy Haiku SDK retry policy is unchanged and must be checked under any future live configuration.

### Consolidated checkpoint and stop condition

All 337 protected raw hashes match the starting snapshot (SHA256 0a840d1f35a48bcef1621afe48abb95dbdedd9c57f9a65011e998bc3a0c8fd2d). New metadata-only candidate-final-checkpoint.json is outside Git beside that snapshot; hash 244a33a17c4e03a9facc40290f5e17eed910b1a5c05e927502c19569af285ad2. Forty-five current source/config/guard/benchmark/evaluation paths and nine focused test paths are hash-bound there. First exploratory metadata inventory omitted six eval source dependencies; retained candidate-checkpoint.json is superseded by the final inventory, not accepted evidence. Its initial command also referenced nonexistent test_safety.py, failed before writing, and was corrected to actual guard/safety test paths. No historical input was replayed.

Final router candidate inventory digest c65f0c6f52f03b24ea2b78213557578f25b389586053495e6c772daef1058535; test inventory e1298652dac73b049ecde3277e97107a5dd107a4a711a922ff4b1743b49a5602; in-memory source archive e0716a7abf463e1381aeef58adab57203fde971fb4b17591bc0e6d57caa9032f; archive manifest a8d07535142555f8774c686c4b36431b99e27c2acd83e9308f4e76401e124642; synthetic smoke 5d5c14509924ccda7889eed7b42851d38bd92ac802d8cde10e95db2464a44db8. Exact canonical map recipes and per-path hashes in final handoff/checkpoint. Existing v2 verification e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e remains unchanged. No source work remains in this bounded candidate without decisions/review/externally authorized execution; the final handoff is the precise resume point. No background process/work is claimed.

Local engineering commits: ad7fe23c8302983df3f9e360145739ec1270d303 (eight paths), f9a9d031b15eb42b7390d50ead4147f0262998a2 (seven paths, one existing log). Staged inventories/normalized bytes checked explicitly against validated files and final current maps. Delivery documentation only adds jev-upgrade-claude-handoff.md and this log checkpoint; terminal HEAD supplied in final receipt. Fifteen distinct scoped paths, all nineteen preexisting untracked files preserved/excluded. Next single task: Claude combined candidate review; independently, owner can settle exact live-run cost/privacy and operational producer policies. Actual wrapper assembly, full Freeze 1 evidence and broader qualified harness extension remain separately bounded work. No background waiting/work.

## Bounded follow-up: streaming limit and accepted replacement completion

The preceding sections describe the original autonomy window, not the current completion state. Owner separately authorized this follow-up at verified HEAD `f73914fa622fc3e64dbe03bda1b82f88ff0472aa`, same branch, preserving all nineteen preexisting untracked files. No AGENTS.md was added. Only the existing Jev adapter/test and these two combined documents change in Git. Private completion artifacts remain outside Git. No optional work or operational producer is added.

### Task A: streamed decoded-response enforcement

Local source/test commit: `1c0fe9a7dcb8e370ea53535e71292d76c56957b8`, exactly `app/agents/jev_router.py` and `tests/test_jev_candidate.py`. HTTPX context-managed streaming consumes `iter_bytes()` (HTTP-content-decoded bytes), rejects before appending a chunk that would exceed 65,536, stops pulling subsequent chunks and closes on success, oversized rejection, status rejection and read/transport failure. UTF-8 and existing strict JSON/schema validation occur only after a completed bounded response. Content-Length is not trusted. Binary mapping, threshold, one-attempt fallback, fixed-code error sanitization, cost/attempt accounting, exact MockTransport-only construction, Haiku default and disabled live/shadow remain unchanged. No retries or additional requests.

Guarantee: accumulated bytes used for JSON decoding never exceed 65,536. A transport/HTTPX decoder may already have allocated or delivered an oversized chunk; no bound on transport allocations, total process memory or total wall-clock deadline is claimed.

Eleven added synthetic cases cover split multibyte UTF-8, exact-limit bodies with absent/misleading headers, accumulated and single-chunk excess, unconsumed trailing chunks, compressed content at/exceeding the decoded limit, normal/status/oversize/read-failure closure, sanitized fallback and exactly one attempted mock request. Existing package tests cover success/failure/path protections and no source writes.

Validation (existing environment/offline guard):

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_candidate.py tests/test_router.py tests/test_agents.py tests/test_observability.py tests/test_api.py tests/test_router_bench.py tests/test_jev_candidate_tools.py -q --basetemp=.pytest_cache/jev-stream
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check app/agents/jev_router.py tests/test_jev_candidate.py scripts/candidate_package.py tests/test_jev_candidate_tools.py
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check app/agents/jev_router.py tests/test_jev_candidate.py scripts/candidate_package.py tests/test_jev_candidate_tools.py
git diff --check
git diff --cached --check
```

Results: **226 passed, 1 skipped, four existing warnings, 2.84s**; zero intercepted/outbound attempts. Skip is the existing Windows native-symlink privilege limitation; separate simulated escape tests pass. Warnings remain missing asyncio_mode plugin and three FAISS SWIG warnings. Ruff passes/four files already formatted; whitespace passes. No full-suite rerun or real-population regression. Codex source/diff self-review is not independent acceptance.

Current metadata-only checkpoint `heldout-external/jev-upgrade-streaming/2026-10-03-f73914f/candidate-checkpoint.json`, raw SHA256 `ee13222c6483f9294c97f14fe8691ef2e1d4d0f4d4c7aa05c5313cf42433fadb`. Same 45-source/nine-test membership and canonical map recipe as before; current source inventory `06b9b27763d063baa7a5e49f700502257a0d7b094c9331e7709739cb1ec3c77f`, test inventory `7648c5eef955083fc1a301ef2d22a7922039b9ed3e8efc2568b58263f4247bce`. Source-only ZIP built twice in memory: `da108d44d9f5120852cf4a5ad43c0d799f3698ee4099dad323a7b2207c339fbc`; manifest `1992978b9b19344641741edfa8f37068ec48348452a8e4cb5381a66a7d700495`. Reproducible smoke stays `5d5c14509924ccda7889eed7b42851d38bd92ac802d8cde10e95db2464a44db8`. No saved/deployable ZIP, dependency installation or Linux runtime verification. Prior checkpoint and hashes remain preserved at their original bindings.

### Task B: actual accepted subject, final joins and read-only chains

Reverified actual report raw hash `7c1617ff4e5a936dd69b14c6b83a4caa7d20d68d819be364f5c37f3a1c5f57af` and actual raw/typed/index hashes `6d5d691a…`, `6392f170…`, `600fb54a…` (full values in combined handoff). Canonical schemas/bytes, ACCEPTED disposition, recorded UTC `2026-10-03T19:28:06Z`, reviewer/raw/index/subject/contract/lemma/counts joins all verified before assembly. Existing accepted subject remains `5ecea37ee945023f77266f6cc9d15ad5e8c7db6d3442c24f69a2112892e0cf78`. No new independent review record or approval was created.

Exclusive-created private directory `heldout-external/reviewer-v2-reconciliation-completion/2026-10-03-f73914f/`:

| File | Raw SHA256 |
|---|---|
| historical-ledger-reconciliation.json | `7d09419b16a7a37a7140f84282b003c4a7a597b83b950be64d319534c9c3a00e` |
| rule-applicability-eligibility_specification.json | `3f48b05b279de950021251e21548f9a0fe5cf3e3ab33155f1e43eda3f9ff979a` |
| completion-index.json | `9de570d789e8374d74347a2399ad850b34c68b2025dd4c7d5f9016be6cc8e6ec` |
| technical-check-receipt.json | `a7bc3979cdeddc7c57ea12a88739650780051df353f31c2f051fbb75f533803a` |
| preservation-before.json | `f13c496020701abda6735fd101727d398ad5d61e1c8f3a4771ba6ced5e45a8df` |
| preservation-after.json | `428a6de3bb6b34256a6ad797bf21a674ac411791ff3931220f80cd1627ff7817` |
| completion_driver.py | `c6108ad9c98bbc4469f52cfb389cd8aea85861015c4ed8f7eb30b511e694d985` |

Final reconciliation changes only prescribed final-schema/review binding outside the accepted subject fields; `review_subject(final)` is exact accepted subject. Eligibility applicability changes only its reconciliation FB from the previously accepted version. Unchanged three semantic reviews and exposure/grouping applicability are reused, not rewritten. Existing `_history`, `_generating`, `_executing_sources`, direct `verify_reconciliation` and combined `rule_bindings` pass on genuine verified context. All 111 historical inputs (107 pins plus four recovered inputs) are hash-covered; counts-only check returns 104 rows and zero E03/E03c/union/normalized-empty-question rows. Current seventeen-source digest remains `e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e`; historical sixteen-source digest remains `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`.

Completed commands, both exit 0 under guard/zero intercepted/outbound attempts:

```powershell
Get-Content -Raw -LiteralPath '..\heldout-external\reviewer-v2-reconciliation-completion\2026-10-03-f73914f\completion_driver.py' | .\.venv\Scripts\python.exe -B - assemble
Get-Content -Raw -LiteralPath '..\heldout-external\reviewer-v2-reconciliation-completion\2026-10-03-f73914f\completion_driver.py' | .\.venv\Scripts\python.exe -B - check
```

Subsequent replay uses **check only**, writes nothing and reproduces exact canonical completion-index/technical-receipt bytes. Exclusive assembly refuses overwrite. Direct result **TECHNICAL_RECONCILIATION_VERIFIED_NOT_ADOPTED**; combined binding chain passes. All **355** protected artifacts, including all 111 inputs, ten reports and prior private records, preserve exact hashes. No classifier/historical code execution, full v2 synthetic rerun, `_freeze`, `verify_adoption`, preparation, reconciliation_preflight or selection invocation. The task-local in-memory adapter is not a production preparation package/InputBinding/FreezeManifest.

Diagnostics retained: initial metadata snapshot attempt applied an FB reader to protected data/ paths and stopped before writes; workspace-contained metadata reads corrected that without relaxing artifact validators. Initial assembly expected a reusable eligibility applicability entry absent by design from refresh metadata; it stopped before wrapper writes. Corrected transcription uses the pinned accepted old wrapper and changes only reconciliation FB. No evidence/pins were repaired or bypassed.

### Consolidated stop and review handoff

Task A is Codex implementation/self-review pending independent review. Task B uses actual Claude subject acceptance; Claude has not independently reviewed the newly assembled final joins. Hash joins do not authenticate approval or establish historical execution. No adoption occurred. Freeze 1 readiness remains unestablished. R4, S-576 complete:false, 37-check limitation and ledger-fidelity premise remain unchanged.

Focused review: combined `41d146d..1c0fe9a` app/config/tools/CI delta and precise streaming guarantee/tests; separately inspect new final subject/schema/review joins and eligibility-only FB replacement. Unchanged protocol evidence remains valid at its bindings; no unrelated interface/test/procedure/runtime evidence was refreshed. Remaining work is independent review, owner live-run/privacy/budget/operational-policy decisions, authorized live-factory/spending enforcement implementation after those decisions, Linux/dependency/AWS verification and accepted qualification/phase operations. No justified additional implementation is included in this bounded task. Documentation-only updates do not require another test run.

Scoped explicit-path documentation commit contains only this log and the existing combined handoff; terminal hash supplied in delivery. Private outputs/Claude reports/unrelated work excluded. No push, installs, live/model/provider/AWS/external calls, real preparation/bindings, adoption/sealing, ranking/selection/sampling, packets, freezes, owner labels or deployment. No background work is claimed.

## Owner-authorized isolated exploratory smoke: implementation and required stop

Verified baseline `8f4e9859d27d368233cd6bd20f08133b82d4ee8f`, same branch and nineteen unrelated untracked paths. The owner superseded the external-call prohibition only for official-document reads and six invented questions once per Jev/pinned Haiku, sequentially, zero retries, inference ceilings $0.02/$0.03/$0.05. No deployment, application live/shadow enablement, qualification or Reviewer v2 changes. Normally configured .env/environment TypeSafe and AWS signing credentials checked for presence, model/region printed only; no values printed or unrelated credential discovery.

Official price/model/tier preparation recorded `2026-10-04T00:41:03Z`: TypeSafe models https://docs.typesafe.ai/models confirms jev-1.13.0, $0.042/M input/free output, 64K request limit. AWS model card https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html confirms the configured US geographic inference ID `us.anthropic.claude-haiku-4-5-20251001-v1:0`, us-east-1 and Standard/default tier. Official AWS geographic table https://aws.amazon.com/jp/blogs/news/amazon-bedrock-now-supports-japan-cross-region-inference/ gives $1.10/$5.50/M for US geographic versus $1/$5 global. Pricing and service-tier/count-token references are retained in plan/handoff. No credits/free coverage assumed. CountTokens is free and exact for supported identical prompts, with a documented limitation for some CRIS-only Anthropic runtime models.

Source/test local commit `8373c34eb4a60c3c6524233c26302eb436c7d09d`, exactly two new paths: experiments/jev_candidate/live_smoke.py and tests/test_jev_live_smoke.py. The dedicated opt-in CLI uses an exclusive fixed run claim, no resume/resend. Candidate Jev still accepts exact MockTransport only; the isolated bridge returns a real streaming HTTPX response so its actual payload/stream/parser/route implementation is exercised. Only the isolated runner has real transport/credential wiring. Haiku inherits RouterAgent.route, with isolated boto3 constructor, maxTokens 256, default Standard serviceTier, standard performanceConfig, total_max_attempts=1. Haiku app constructor/default/prompt/threshold unchanged. HTTPX retries=0, redirects=false; explicit official endpoint guards plus one dispatch/wire permit; downstream tripwire; no test guard lift or monkeypatch. Candidate router_live=False remains app configuration metadata; runner actual_live independently indicates external-mode configuration. No universal sandbox or total-deadline claim.

Existing Ledger reserves before dispatch; existing RunJournal fsyncs call_started before paid call. Unknown billable usage retains full reservation, failures count, and any required stop ends all providers. Fixed six-by-two schedule sends only invented questions and existing router system/options; complete prompt/expected route/commit/source hash/model/price/limits recorded before preflight. Source map checks executing workspace bytes against commit, distinguishing CRLF normalization. Jev reservation $0.002688 per attempt ($0.016128 for six); historical expected estimate $0.00010332 total. Haiku needs exact CountTokens complete system/messages plus 256 output at $1.10/$5.50. For verified <=2048 input, six conditional maximum reservations $0.0219648; combined $0.0380928. No successful count means no actual Haiku reservation/expected estimate is established.

Validation commands:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_jev_live_smoke.py tests/test_jev_candidate.py tests/test_router.py tests/test_agents.py tests/test_observability.py tests/test_api.py tests/test_router_bench.py tests/test_jev_candidate_tools.py -q --basetemp=.pytest_cache/jev-live-integrated
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" check experiments/jev_candidate/live_smoke.py tests/test_jev_live_smoke.py
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff',run_name='__main__')" format --check experiments/jev_candidate/live_smoke.py tests/test_jev_live_smoke.py
git diff --check
git diff --cached --check
```

Final formatted implementation: **248 passed, 1 skipped, four existing warnings, 3.38s**, zero intercepted/outbound attempts. Initial focused run 114 passed before added config/tripwire/import tests. Existing Windows symlink skip and asyncio_mode/FAISS warnings unchanged. Synthetic success, monetary/request limits, unknown-cost failure retention, no replacement calls, re-entry rejection, exact prompts/output/tier, missing settings, stream closure/early stop, endpoint/duplicate-wire rejection, downstream rejection and import purity covered. Codex diff/self-review, not independent acceptance. Staged two explicit paths; staged normalized bytes matched validated workspace bytes.

One actual command outside pytest, no diagnostic inference:

```powershell
.\.venv\Scripts\python.exe -B -m experiments.jev_candidate.live_smoke --execute-owner-smoke
```

Run `2026-10-03-owner-routing-smoke-01` **STOPPED** at first Q1 `token_count_preflight`, sanitized `ValidationException`, nonzero exit. One Bedrock non-inference CountTokens operation; no counts returned. **Zero Jev/Haiku inference attempts**, no routes/scores/usage/inference latency, no downstream agents, no retries or replacement calls. Strict input-cost prerequisite failed, so no inference followed. Server message was intentionally not retained; the exact rejection reason beyond operation/code is unestablished. Runtime CRIS token-count support limitation is a possible explanation, not a verified cause. This claim remains consumed and is not rerun. Committed inference cost/retained unknown reservations $0; remaining ceilings $0.02 Jev/$0.03 Haiku/$0.05 total. No empirical accuracy/connectivity/Lambda/performance conclusions.

Exact six invented cases are in plan and combined handoff; expected Q1/Q2/Q3 qa, S1/S2/S3 summarize. Private directory heldout-external/jev-isolated-live-smoke/2026-10-03-owner-routing-smoke-01/:

| File | Raw SHA256 |
|---|---|
| plan.json | `5cf31613a34ecc87b6eabe92cd496644e4c89bc46443b699b26c36951f2f11ec` |
| result.json | `68f26dac5d2313d79bb655a2b96466a4fb458e221324a15f5978dfe025646cfc` |
| run.journal.jsonl | `7a781da0c0b99e8e37f1654e4e44253daedb475092d1c1729220053f68f421c5` |
| source-inventory.json | `b20e668b9f41b5cf0d717f832c74adc0e6a479c463d120688e798baa41edac03` |

The exact 56-path combined app/control/tool/guard/benchmark/test map (previous 45+9 plus two) digest `f3b543ff404d0293a4189df4cacfc5bf99e73b92cbde3c1cddc2b5836bbf0605`; sorted compact ASCII JSON relative-main-path/raw-hash map plus LF, distinct namespace from old absolute-path maps. App sources/source-only Lambda package unchanged; isolated runner excluded from that package. No new deployment artifact.

Durable metadata preservation under heldout-external/jev-live-smoke-preservation/2026-10-03-8f4e985/: before `83e20b6792ed999efc6c239f1440900c3e8c2f5bbbe32a4cfb13a938fa01a6b8`, after `dfbe00778e4df107184e331c95d9ccaa6b2cb4c30d6da81c3aee1960ab5f6332`. All 363 protected hashes match (prior 355 plus completion seven/checkpoint one). All seventeen current verifier source hashes match; digest remains `e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e`. Existing actual replacement wrappers/reviews unchanged, no repeat historical replay or new protocol evidence.

Stop/resume point: combined candidate/streaming/isolated runner and final joins await independent review. Another run requires a supported defensible pinned-Haiku cost-bound path plus a new owner grant after this required stop. Do not infer permission to repeat, change endpoints/models/tier or relax the prerequisite. Review the separate cost recalculation, permits, journal, CountTokens failure and no-inference evidence; existing v2 phase/qualification blockers remain. Documentation-only delivery adds no further tests or run attempts. Scope-only local commits, no push/install/deployment/default change/AWS resource changes/private data/adoption/selection/freeze. No background work.
