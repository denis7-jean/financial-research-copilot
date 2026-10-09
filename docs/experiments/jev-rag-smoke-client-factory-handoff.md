# Lambda client factory — offline implementation handoff

Current CF-1/CF-2 correction is Codex implementation/self-review, pending Claude's
focused delta acceptance, with correction parent
`bf9255fd19cffeb6df3676144c57f569f05c2e6b`. Claude's preserved review is REQUEST
CHANGES at that subject, raw SHA-256
`145aef024ebb8bdecfb3e2ff85c836955aac589f3f855efb0f14010244e9f9d9`.
Only the same three paths are modified. No integration or execution is authorized.

Initial implementation history (not independently accepted). Exact parent:
`4eca9c8240d539e9ff3faedd589fddea54fad900`. Branch:
`phase0/jev-rag-smoke-client-factory`. Only additions are this document,
`scripts/jev_rag_smoke_client_factory.py` and
`tests/test_jev_rag_smoke_client_factory.py`. No integration or live CLI.

The cumulative consumer acceptance was verified at that exact subject, raw report
SHA-256 `0f80f495502f7ec0677ddf09133ad35864558c5ac8d520904f8e5b7a1bebc74f`.
Both consumer and both adapter reviews remain uncommitted and unchanged.

## Implemented boundary

`prepare(settings, access_key_id=..., secret_access_key=..., session_token=None)`
returns a zero-argument callable for unchanged `consume_adapter`. Preparation
uses standard-library definitions, validates/copies settings, and performs no
SDK imports, I/O, environment or credential lookup. Settings have the exact P0
keys, one attempt, and integer connect/read timeouts from 1 through 120 seconds.
Explicit signing strings are nonempty printable ASCII without spaces, at most
4096 characters; no source loader, identity selection or fallback is provided.
Only invented signing strings were used. Repr and fixed diagnostics omit them.

A lock claims one construction attempt before lazy SDK loading; failures and
concurrent calls cannot reuse it. CF-1 adds a refusal-only read of `SSLKEYLOGFILE`
after this claim and before SDK loading/construction. Any nonempty value rejects
with `CLIENT_CONFIG_INVALID`, conservatively even under ignore_environment.
Preparation still reads no environment. Values are never printed, mutated or used
as configuration. Changing the variable after prepare cannot bypass refusal;
changing it after this check is outside the dedicated-process trust boundary.
The persistent operator claim is distinct and
remains the durable execution boundary. Real consumer tests read the closed
claim and attempt-marker files inside the recording Session constructor, then
exercise the unchanged ParentTransport, full account-qualified ARN, canonical
payload, one send, uncertain failure, reservation retention and duplicate refusal.

Both boto3 and botocore must be exactly `1.42.96` before construction. The factory
uses a dedicated pinned botocore Session subclass, not a default boto3 Session.
This avoids an unnecessary resource/session wrapper and its ambient setup; both
SDK versions are still checked. Only Lambda, `us-east-1`, API `2015-03-31`, and
`https://lambda.us-east-1.amazonaws.com` are constructed. TLS verification stays
enabled; explicit timeouts and `total_max_attempts=1, mode=standard` apply.

Selected pinned SDK configuration errors and local SDK-file OSError map to the
existing consumer's `CLIENT_CONFIG_INVALID`; another construction attempt maps
to `PARENT_ALREADY_ATTEMPTED`. Missing SDK imports/version mismatch also reject.
Unexpected programming errors propagate as their original objects/tracebacks.
Rejected returned clients are closed; only secondary cleanup defects while a
primary error is escaping are suppressed. No broad exception-to-outcome conversion.
Returned metadata/configuration and invoke/close/event-registration interfaces
are validated against the unchanged adapter. No invocation is made by the factory.

## Installed SDK inspection and ambient settings

Static inspection covered pinned session/config/provider/loader/client/args/
endpoint/HTTP/user-agent/plugin/credential source. Historical incomplete inspection:
`C:\Projects\AWS Project\dependency-acquisition\rag-client-factory-20261009-731d0c54\sdk-source-inspection.json`
SHA-256 `04ca967130632a259037745ec8f79695b7be8179d88fe4d100804f18f60cecf4`.
That immutable record omitted the TLS key-log path. The corrected inspection and
its binding are in the CF-1/CF-2 section below; the original is not overwritten.

Explicit keys in `Session.create_client` construct static Credentials directly.
However, stock code also calls `get_auth_token`, scoped/full config and configured
endpoint setup. The local subclass returns no auth token, provides empty profile/
services records, omits credential/token providers, and rejects fallback credential
access. Its store uses pinned scalar defaults with constant providers, not profile
or environment chains. Configured endpoint-provider lookup is disabled; explicit
endpoint plus `ignore_configured_endpoint_urls=True` remain in force.

Explicit empty proxies/proxy configuration and `verify=True` bypass ambient proxy
and CA-bundle selection in the inspected endpoint implementation. Endpoint
discovery, FIPS, dualstack, host-prefix injection and smart-default inference are
disabled; legacy defaults and parameter validation are explicit. CSM is off.
Models load only from SDK built-in data, excluding AWS_DATA_PATH and home models.
Session/client user-agent construction avoids environment-derived execution tags.
Nonempty process-global SDK initializers reject; environment-selected client
plugins are not loaded.

These are narrowly pinned overrides, not an SDK sandbox or authenticated-library
guarantee. Lazy SDK/module imports may compute host paths and optional-runtime
metadata, even though those values do not select signing sources or client
configuration here. SDK built-in model files, local TLS trust bundle, OS DNS/TLS,
installed-code integrity and in-process mutation remain trusted dependencies.
Future execution needs a reviewed dedicated process without concurrent SDK
initializer/event/plugin mutation. No real SDK construction/TLS behavior of this
factory has been tested; version strings alone do not prove library identity.

## Historical 714-test validation — CF-2 correction

Initial subject source hashes (LF working copies equal committed blobs at bf9255f):

- Script: `8699d47f980460e6a0a83b020f454ef678de0f0d51538097dc209edff6064c31`.
- Tests: `a2cd6c4db2df01a83fab20d0cdf8c22b556147558faa1353bf5cc785856e82bf`.

Private receipt root:
`C:\Projects\AWS Project\dependency-acquisition\rag-client-factory-20261009-731d0c54`.
Historical commands from `C:\Projects\AWS Project`:

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B dependency-acquisition/rag-client-factory-20261009-731d0c54/validate_constructor_v2.py test-integrated-v7
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B dependency-acquisition/rag-client-factory-20261009-731d0c54/validate_constructor_v2.py test-integrated-v8
```

The runner executes pytest through the existing offline guard, disabled external
plugins/cache, exclusive scratch temp/JUnit/log files and inspected invented
NumPy/FAISS substitutes. Eight complete files run: factory (62), consumer (92),
adapter (105), operator (202), P0 (83), accounting (31), handler (53), smoke (86).
Each environment: **714 passed**, zero outbound attempts. The v7/v8 console,
summary and completion index's zero-real-construction claims are inaccurate:
the per-test guard missed S3 and Bedrock clients constructed during collection.
At least two real clients per v7/v8 run are supported by the unchanged import path;
exact Session/total construction counts were not instrumented. Python 3.11.15 /
SDK 1.43.14 is compatibility only; production version selection rejects it.
Python 3.13.12 / SDK 1.42.96 uses pinned definitions. The factory itself was never
constructed through real SDK constructors; that is distinct from the whole suite.

v3/v4 each also ran two inherited cases with real Bedrock SDK clients and replaced
HTTP transport: together with collection, at least four real clients per run.
The earlier disclosure counted only those two cases and underreported construction.
Exact Session counts and any additional constructions remain unestablished.
No outbound attempt occurred. v7/v8 replace the two inherited case constructors
with recording clients and installed serializer definitions, but still miss
collection. Their passes do not establish whole-run zero construction or actual
SDK signing, TLS, event, retry or client integration. Accepted assertions are unchanged.
v5/v6 had two private-harness teardown errors while each test temporarily replaced
the guarded send method; v7/v8 restore that synthetic method before guard-identity
checks. All failed logs are retained.

Focused preparation/configuration/rejection/cleanup/defect/concurrency tests and
consumer-seam tests pass. Invalid keys/settings/version fail before constructors;
secrets do not enter recorded arguments/results. Legitimate optional-token and
timeout-boundary cases remain valid. Legacy simulation and REPORT/authority
limitations are covered by the unchanged suites.

Scoped guarded Ruff check and format --check pass on the two new Python files in
both environments; whitespace is checked before publication. Commands are recorded
by `validate.py` modes `lint-v2`, `format-check-v3`, `lint-v3`, `format-check-v4`.
One inherited warning: unknown `asyncio_mode` with plugin autoload disabled. The
pinned interpreter emits a preexisting missing-base-path launcher notice but
successfully reports/runs Python 3.13.12.

`validation-summary.json` SHA-256:
`a4768a8323909ad286b80b83f2b0aa612bbe278a7098fad64874499b6cbf8dc6`.
It historically binds commands/logs/JUnit and environments but contains the
incorrect zero-construction assertions described above. Historical commit and
blob/WC hashes are in `commit-receipt.json`;
the completion index binds receipts without signing material or private inputs.

## CF-1/CF-2 correction evidence and validation

Fresh private root:
`C:\Projects\AWS Project\dependency-acquisition\rag-client-factory-cf12-20261009-0d8a3271`.
The entire original receipt directory is inventoried before/after and preserved
byte-for-byte where readable; original logs, summaries, inspection and completion
index remain unchanged. No original false claim is relabeled as corrected evidence.

`evidence-correction.json`, SHA-256
`cf54726ca8fa57504835d26aa76ec2df3d9464b16af20b7fcf4f0372ccaf2827`,
identifies original inaccurate claims, original hashes, historical source/control
paths and supported minimums. v3/v4 are at least four clients per run; v5/v6/v7/v8
and the original focused runs are at least two. Exact total/Session counts are
unestablished. The old 714-test count is retained; no outbound-attempt finding is
promoted to a no-construction finding.

`sdk-source-inspection.json`, SHA-256
`19a01527689fadb474d79318b7cb1956a49e61f38f0d3590042a23889a31b8a4`,
rechecks the original installed-source hashes and records the missing pinned TLS
path: httpsession.create_urllib3_context sets context.keylog_filename from nonempty
SSLKEYLOGFILE unless ignore_environment. URLLib3Session pool construction reaches
it. Factory refusal now occurs before this path; no TLS context/function, key-log
file or real constructor was used in reproduction. No global TLS function changes.

Committed-base CF-1 reproduction uses exact raw Git factory bytes, a nonempty
invented setting, recording constructors, and an absent destination that remains
absent. It demonstrates the missing check without TLS/network activity.
CF-2's fresh import probe keeps the old per-test guard's counters at zero while
the new outer guard records two inert S3/Bedrock import replacements. The probe
does not construct SDK clients. A separate probe checks all 16 guard surfaces:
15 stub refusals plus one inert client replacement, with no original constructor
or provider entered. This deliberate refusal probe is separate from suite counters.

The new runner installs permanent boto3/botocore constructor/provider controls
BEFORE any application/test module is imported or collected. Entry points include
boto3 client/resource/default-session helpers, boto3 Session init/client/resource,
botocore get_session/Session init/create_client/credential and token access,
ClientCreator/BaseClient, and credential/token resolver factories. No counters
are reset after collection. Import replacement attempts remain separate from
execution serializer replacements and refused construction/provider attempts.
Inert import clients fail on use. The same inspected two-case recording client
uses installed model/serializer definitions, never real Sessions/clients. Its
synthetic pass cannot establish real SDK signing/TLS/event/retry/client integration.
The offline guard remains active; no accepted test or assertion is modified.

Final commands from `C:\Projects\AWS Project`:

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B dependency-acquisition/rag-client-factory-cf12-20261009-0d8a3271/validate.py test-integrated-v4
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B dependency-acquisition/rag-client-factory-cf12-20261009-0d8a3271/validate.py test-integrated-v5
```

Each: **721 passed**, one inherited asyncio_mode warning. Counts: factory **69**
(was 62), consumer 92, adapter 105, operator 202, P0 83, accounting 31, handler 53,
smoke 86. Each receipt records two PRE_COLLECTION inert replacements (S3, Bedrock),
two EXECUTION serializer replacements, zero refused real construction/provider
attempts, zero real Sessions/clients and zero outbound attempts throughout collection
and execution. Python 3.11.15 / SDK 1.43.14 remains compatibility only, with the
production pin rejection exercised; Python 3.13.12 / SDK 1.42.96 is pinned-definition
evidence. The missing-base-path launcher notice remains historical/environmental.

New regressions cover unset/empty/nonempty key-log values, preparation purity,
post-prepare changes, conservative ignore-flag behavior, simultaneous refusal and
duplicate blocking, consumer claim/hold retention and fixed non-disclosing errors.
The unchanged consumer→recording factory→accepted adapter seam retains its ordering,
exact request binding, clean/uncertain returns, holds and duplicate refusal.
Scoped guarded Ruff lint/format and whitespace checks cover the changed Python
files. One unused test import was removed after initial lint rejection; complete
suites were rerun on final source bytes. No protected files were reformatted.

`validation-summary-final.json` SHA-256:
`130b2b5b4a3532cebe1c6131918eeee7e6efdfc6cdb2834e57a9386950bb22e9`.
It binds final logs/JUnit, per-file counts, guard counters/helpers and tested source.
Final correction commit and separate blob/WC hashes are in the new commit receipt;
the new completion index binds receipts, preserving the original completion index.

Nonblocking CF review observations remain explicit: suppressed original exception
context remains in memory; process-global SDK handlers are mutable; host DEBUG
logging can expose request content. Dedicated trusted process, sanitized logging
and absence of concurrent environment/handler mutation remain operational gates.
No logging framework, SDK sandbox, authorization or recovery system is added.

## Preservation, review scope and remaining gates

Historical before/after metadata snapshots cover 18 preexisting worktrees, four reports,
133 readable sealed files, protected ZIPs/configuration/locks and pricing evidence.
1084 inaccessible sealed entries remain explicitly inaccessible; no permissions
were changed or fresh certification claimed. The correction additionally preserves
Claude's factory report and the original receipt directory; other worktrees and
accepted source trees are unchanged. Only the three authorized correction paths
may be committed here; the factory review stays untracked. Historical
evidence and main/shared unstaged documents are preserved at their existing bindings.

Claude's focused next review should assess CF-1 refusal timing/purity/one-use
semantics and CF-2's evidence correction, pre-collection controls and coverage limits.
All other accepted/reviewed boundaries remain unchanged.
This implementation/self-review is not independent acceptance. The inherited
O1–O4 limitations remain: actual SDK/live observation proof is not supplied by
synthetic translation tests; REPORT provenance/type remains external; confirm
requires the authentic returned status; dispatch entry is not delivered-call proof.

Separate acceptance/integration, explicit static-signing-source authorization,
identity/permission/access verification, vetted endpoint/TLS/private output flow,
owner inputs/data/prices/token bounds/budget and infrastructure-inclusive P0
sufficiency, exact artifact/configuration/native gates, authentic REPORT/observation
joins, confirmed execution, semantic assessment and qualification remain required.
No account/IAM validity, live capture/invocation, paid run, deployment, qualification,
or release authorization is established. Stop for independent factory review.
