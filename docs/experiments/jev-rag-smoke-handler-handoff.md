# Isolated offline RAG smoke handler increment

Codex implementation/self-review; Claude independent review pending. No live
handler execution, artifact build, owner-input approval or integration occurred.

## Subject and scope

Branch `phase0/jev-rag-smoke-handler`, direct base
`36494d478f00358611e33bd0e4a5121def347f86`.
The P0 Claude report was read and its ACCEPTED verdict verified at this exact
subject; raw SHA-256
`16f84e23bcb780c4aa2113b825e09073beb388227ee6098651a1fb2a24923886`.
The three P0 committed blobs retain their accepted hashes.

Nine paths: new handler, new focused tests, this handoff; explicit packaging
allowlist/layout tests; smoke-specific import/client isolation changes to
orchestrator, router, bedrock_client and retriever. The accepted policy,
contract/fixtures, normal entry point, app/main.py, requirements, lock and
allocation are unchanged. No shared production client is replaced with a smoke
client: dedicated objects live only on the current smoke policy.

## Invocation and trust contract

Future isolated function Handler: `app.rag_smoke_handler.handler`. The ordinary
generated root handler remains unchanged. The packager retains its ordinary
handler target contract; this increment only adds the new source to its fixed
allowlist. A future isolated-function configuration must explicitly bind the
separate entry point and undergo its own review/validation.

Exact envelope schema `rag-smoke-invocation-v1`:

| Field | Requirement |
| --- | --- |
| `schema` | Exact schema string |
| `query` | String, 1..300 characters, at most 1,200 UTF-8 bytes; joins policy query hash |
| `policy_utf8` | Explicit UTF-8 JSON text, 1..65,536 bytes, exact canonical policy bytes |
| `evidence_utf8` | Exactly Haiku/Titan text records, each 1..16,384 UTF-8 bytes |
| `bindings` | Exactly `policy_sha256`, `price_evidence_sha256` (Haiku/Titan map) |

The canonical event is limited to 131,072 bytes. Canonical encoding is the
accepted UTF-8, sorted compact JSON, ASCII escaping, no nonfinite numbers, one
terminal LF. An isolated-function configuration variable,
`COPILOT_RAG_SMOKE_PAYLOAD_SHA256`, must hold its exact SHA-256. Missing/malformed
configuration or a different event rejects before any client. Caller-supplied
approval fields are unknown fields and reject. No historical defaults supply
prices, bounds, ceilings, query, evidence, timeouts or data bindings.

Lambda passes a decoded event. This binding covers its canonical value, not
original wire whitespace, duplicate-key ingress behavior or the AWS request
payload's raw bytes. The future operator must send the exact canonical envelope
and bind those bytes. The handler preserves the embedded policy/evidence UTF-8
bytes and verifies their joins through the unchanged strict policy constructor.
The invocation cannot override keyword test seams; they are Python-only APIs.

Configuration hashing binds a configured event; it does not authenticate owner
approval, pricing, data permission, the invoker or the persistent parent claim.
The operator/IAM/configuration boundary must restrict the isolated function and
verify the accepted P0 claim before its one parent Invoke. P0 is never imported
into the deployment source closure. Expected-source minimum greater than the
bound source row count rejects before clients.

The new handler module's import is pure: no SDK construction, dotenv, credential
resolution or native import. Orchestrator imports smoke execution dependencies
only inside policy activation; it never constructs the normal orchestrator or
summarizer. Router/retriever/generation modules skip ordinary SDK creation and
their dotenv calls when first imported under an active smoke policy. Subsequent
ordinary use can lazily create its ordinary clients; normal requests, defaults
and financial-answer behavior pass existing regressions.

**H1 corrected in the focused follow-up:** the original handler commit inherited
QAAgent's unconditional module-level `load_dotenv()` call. Under the owner's
explicit three-path correction grant, QAAgent now uses the existing
`current_policy()` guard, matching router/retriever/generation. It skips the
loader under an active policy and preserves the ordinary import-time call when
there is no active policy. The recording-only cold probe observes zero loader
invocations throughout the valid smoke chain. No real loader, credential or .env
read is used to establish this result. Dedicated SDK credential-provider activity
remains a separate operational prerequisite; this guard does not remove it.

## Dedicated clients and actual application chain

After all envelope/policy/root checks, an isolated factory creates only S3 and
Bedrock Runtime clients with explicit `us-east-1` regional HTTPS endpoints,
supplied policy connect/read timeouts, and standard
`total_max_attempts=1`. The unchanged accepted binder inspects actual resolved
config/endpoint values and installs parameter/send hooks before requests.
Credential-provider activity is outside those hooks; no claim of zero credential
network activity or operational credential permission is made.

Dedicated clients are closed after the call, including stops. Expected factory
failures are sanitized; failure creating the second client closes the first.
Unexpected programming errors are not hidden by a new global exception catch.

`process_smoke` runs the actual RouterAgent -> QAAgent -> retriever -> generation
seams. Order is ROUTE, conditional index GET, conditional metadata GET, EMBED,
GENERATE. Source identities, exact sizes/full hashes and metadata validate before
native deserialization. Duplicated/out-of-range indices, nonfinite/increasing
scores or insufficient expected-source hits stop before generation. Equal scores
remain valid. No fallback, summarizer, replacement request or second model send
is added. Existing accepted policy guards/reservations are used unchanged.

Local function claims remain under `/tmp/<run_id>` (invented roots in tests).
Duplicate local claims refuse without modifying prior files/holds. This is warm
filesystem protection, not verification of the persistent parent claim, a
cross-container claim or distributed deduplication.

## Results and evidence limits

Response schema `rag-smoke-handler-result-v1` has exact fields: schema, scope,
status, code, run_id, policy_sha256, attempts, exposure_usd, local_events, result,
parent_claim_verified, publication_confirmed, qualification, release_authorized.
The final four flags are always false. Status is STRUCTURAL_SUCCESS, STOPPED or
UNCERTAIN. Fixed sanitized codes exclude provider messages, private paths and
input text. There is no HTTP status pretending to establish completion.

Private `result` contains answer (at most 16,384 UTF-8 bytes), sorted citations,
retrieval source/score pairs and router confidence. Retrieved text is not
duplicated. Answer/schema/total-output rejection preserves usage/holds, returns
no answer and leaves journals intact. The overall canonical result is at most
131,072 bytes; overflow returns bounded metadata only with an uncertain status.
No answer/query/retrieved text is printed. Existing QA logs contain metadata.

Returned local journals include their relative filenames, hashes and exact
parsed metadata records, including known token usage/charges. Their hashes bind
local bytes only. Missing/partial journals deny confirmation; no repair, retry,
overwrite or cleanup occurs. A local complete event, successful response or
matching local hashes does not establish a confirmed parent outcome or operator
publication. No semantic answer assessment or qualification is performed.

**N2 remains unresolved:** the accepted policy checks retries/send counts before
usage settlement. Retry mismatch/extra-send outcomes retain the authorized
reservation, and some otherwise valid usage is not settled. That single hold
does not cover already-delivered unauthorized extra requests. A regression makes
this limitation visible; this increment neither redesigns accounting nor makes
execution safe despite it.

## Offline validation and preservation

Existing Python 3.11.15 and Ruff 0.15.14; guard active, zero outbound attempts.
Every new handler test injects fake clients or a fake SDK session, pure-Python
native substitutes and a fake Lambda context. There is no real credential or
endpoint resolution. Cold imports use a recording-only dotenv spy and SDK
construction tripwires, restored before the final guard assertion.

Private scratch/receipts:
`C:\Projects\AWS Project\dependency-acquisition\rag-handler-20261007-4c31e790`.
Focused initial handler + accepted smoke suite: 132 passed; extended cold/source
checks: 136 passed (50 new handler cases, 86 accepted smoke cases). Final broader
worktree run: 551 passed, 1 known lock/CRLF failure, 1 Windows symlink skip.
Exact raw Git-byte export: 552 passed, 1 Windows symlink skip. Exact
staged/committed/raw bindings are in private validation/completion receipts.
Outputs: working-final-results.xml and raw-results.xml; test scratch directories
pytest-working-final and pytest-raw, all under the private directory above.

Reproducible broader command (run twice with fresh output directories, once on
the untouched-CRLF worktree and once on a raw Git-byte source export):

```powershell
$env:HANDLER_TEST_ROOT = '<worktree-or-fresh-raw-byte-export>'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-handler-20261007-4c31e790\run_offline.py' tests/test_jev_rag_smoke_handler.py tests/test_jev_rag_smoke.py tests/test_jev_rag_smoke_preinvoke.py tests/test_agents.py tests/test_router.py tests/test_api.py tests/test_observability.py tests/test_jev_candidate.py tests/test_lambda_package.py -q -ra --basetemp '<fresh-private-test-directory>' --junitxml '<fresh-private-results.xml>' -p no:cacheprovider
```

The complete packaging file runs. The pre-existing operational-lock raw-byte
test fails on Windows CRLF copies; a fresh raw Git-byte export retains the
canonical lock without modifying protected files or weakening the assertion.
Windows symlink-creation privilege causes its existing skip. Plugin autoload is
disabled; the known asyncio_mode warning does not affect selected synchronous
tests. Static packaging closure checks now expect 19 sources, reject a missing
new handler and preserve the ordinary root handler bytes. No real application
artifact was assembled; packaging tests use invented wheels and stubbed installers.

Scoped guarded Ruff check and new/otherwise-formatted-file format checks pass.
Router, bedrock_client and retriever already fail formatting at the accepted
base under the same Ruff configuration; unrelated formatting is not rewritten.
Git whitespace is checked before commit.

Metadata preservation snapshots cover ten prior worktrees' HEAD/status/readable
changed files, fixed requirements/locks/allocation, accepted ZIP and 1,217 sealed
directory bindings. Historical inaccessible-review scope is not promoted into
new content verification. No permission changes or protected normalization was
used; private Reviewer v2 inputs were not opened or refreshed.

## Independent review and next gates

The original review covered the exact nine-path delta: canonical-event trust boundary,
complete validation before clients, cold import/client separation (including the
then-unconditional QA loader), actual SDK configuration/hooks, positive five-stage chain,
stop/uncertain behavior, output bounds, retained usage/local evidence, unchanged
ordinary behavior and explicit packaging closure.

Remaining gates: owner-approved actual data/query/source conditions, authoritative
prices/token bounds/budgets/infrastructure sizing; P0 operator integration and
persistent claim verification; credential/configuration/IAM boundaries; N2
resolution; confirmed hash-bound parent completion evidence; a new exact artifact
and native/startup validation; semantic assessment and later qualification.
No integration, live execution, build, resource change or deployment is implied.

## H1-only correction for focused Claude delta review

Correction direct base: `e6a5e1fb97b174d3c369f08526215310e951be07`.
The unchanged, uncommitted Claude report has raw working-copy SHA-256
`98d433791bd2b8167cd48bc7abd3099b69bf8aa10bdb22974473ed87f1ac95ac`.
Its REQUEST CHANGES disposition identifies H1 as the sole blocking defect.
The owner's new grant explicitly authorizes qa_agent.py in addition to this
handoff and the handler test file. These are the only three correction paths.

The production correction is one import and one conditional: the existing
module-level loader runs only when `current_policy() is None`. The standalone
ordinary loader remains unchanged. No handler, policy, P0, packaging, contract,
route, environment setting or ordinary entry point is modified.

Fresh committed-base export reproduction used a recording-only spy installed
before cold imports. It recorded exactly one QAAgent call with no arguments,
under an active policy, after the dedicated-client factory. No loader or file
read occurred. The same private probes independently reproduced the unchanged
CRLF lock failure using the original committed test assertion and showed that
the canonical committed lock passes it: 2 probes passed. This is defect detection,
not an assertion that the original smoke chain was loader-free.

The corrected existing cold test now requires zero loader invocations across
the complete five-stage smoke chain with ordinary SDK construction forbidden.
Three new cases cover ordinary-first and smoke-first execution followed by
ordinary router/QA use, plus cold malformed-input purity. Direct recording spies
check invocation, irrespective of the guard's dotenv-disabling environment flag.
The ordinary-first case positively observes QAAgent's no-policy import loader;
subsequent ordinary use retains/recreates ordinary fake clients and pinned Haiku
defaults, never adopting dedicated smoke clients or changing ordinary index caches.
The malformed case observes no loader, client, factory or downstream operation.
All patch/module state is restored before the final offline-guard assertion.

Validation used Python 3.11.15, Ruff 0.15.14 and inspected pure-Python native
substitutes, with zero outbound attempts. Focused handler: 53 passed. Broader
working copy: 554 passed, 1 unchanged lock/CRLF failure, 1 Windows symlink skip.
The fresh raw staged Git-byte export (bound to identical final committed source
blobs) passes 555 tests with the same one skip. The complete packaging file runs
without changing the lock, requirements or canonical-byte assertions. Plugin
autoload is disabled; the existing asyncio_mode warning remains nonblocking.

Private task directory:
`C:\Projects\AWS Project\dependency-acquisition\rag-handler-h1-20261008-7d892b61`.
Reproducible final source-byte validation command:

```powershell
$env:HANDLER_TEST_ROOT = 'C:\Projects\AWS Project\dependency-acquisition\rag-handler-h1-20261008-7d892b61\staged-export'
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B 'C:\Projects\AWS Project\dependency-acquisition\rag-handler-h1-20261008-7d892b61\run_offline.py' tests/test_jev_rag_smoke_handler.py tests/test_jev_rag_smoke.py tests/test_jev_rag_smoke_preinvoke.py tests/test_agents.py tests/test_router.py tests/test_api.py tests/test_observability.py tests/test_jev_candidate.py tests/test_lambda_package.py -q -ra -p no:cacheprovider --basetemp 'C:\Projects\AWS Project\dependency-acquisition\rag-handler-h1-20261008-7d892b61\pytest-staged' --junitxml 'C:\Projects\AWS Project\dependency-acquisition\rag-handler-h1-20261008-7d892b61\staged.xml'
```

Guarded Ruff `check app/agents/qa_agent.py tests/test_jev_rag_smoke_handler.py`
passes, as does `format --check tests/test_jev_rag_smoke_handler.py`. QAAgent's
format drift is present in the raw committed correction base and retained;
unrelated formatting is not rewritten. Git whitespace checks pass. The earlier
working-copy broader run preceded test-only formatting; the raw staged run covers
the final Python bytes. Documentation-only additions do not require another suite.

Metadata snapshots verify ten other worktrees' HEAD/status/readable changed
files, protected fixed inputs, accepted ZIP, 1,217 sealed bindings and this
uncommitted Claude report unchanged. Final receipt distinguishes raw working-copy
and committed-blob SHA-256 values and binds validation outputs. No protected
line-ending normalization, private credential read or permission change occurred.

Claude's next review scope is exactly this H1 guard, direct loader spies,
ordinary/smoke import-order isolation and the three-path diff. Codex validation
and self-review do not establish independent acceptance. N2 and every remaining
operator, credential, data, budget, evidence, artifact/native, semantic and
qualification gate above remain unresolved. Stop for focused H1 delta review;
there is no integration or live-execution authorization in this correction.
