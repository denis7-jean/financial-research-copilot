# Lambda client factory — offline implementation handoff

Codex implementation/self-review; independent acceptance pending. Exact parent:
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
concurrent calls cannot reuse it. The persistent operator claim is distinct and
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
endpoint/HTTP/user-agent/plugin/credential source. Source hashes and exact findings:
`C:\Projects\AWS Project\dependency-acquisition\rag-client-factory-20261009-731d0c54\sdk-source-inspection.json`
SHA-256 `04ca967130632a259037745ec8f79695b7be8179d88fe4d100804f18f60cecf4`.

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

## Validation and exact evidence

Final source raw working-copy hashes (LF, identical to expected committed blobs):

- Script: `8699d47f980460e6a0a83b020f454ef678de0f0d51538097dc209edff6064c31`.
- Tests: `a2cd6c4db2df01a83fab20d0cdf8c22b556147558faa1353bf5cc785856e82bf`.

Private receipt root:
`C:\Projects\AWS Project\dependency-acquisition\rag-client-factory-20261009-731d0c54`.
Final commands from `C:\Projects\AWS Project`:

```powershell
& 'C:\Users\Desktop\miniconda3\envs\legal-agent\python.exe' -B dependency-acquisition/rag-client-factory-20261009-731d0c54/validate_constructor_v2.py test-integrated-v7
& 'C:\Projects\AWS Project\main\.venv\Scripts\python.exe' -B dependency-acquisition/rag-client-factory-20261009-731d0c54/validate_constructor_v2.py test-integrated-v8
```

The runner executes pytest through the existing offline guard, disabled external
plugins/cache, exclusive scratch temp/JUnit/log files and inspected invented
NumPy/FAISS substitutes. Eight complete files run: factory (62), consumer (92),
adapter (105), operator (202), P0 (83), accounting (31), handler (53), smoke (86).
Each environment: **714 passed**, zero outbound attempts; final constructor guard
reports zero real SDK Sessions/clients. Python 3.11.15 / SDK 1.43.14 is compatibility
evidence only: real version selection rejects it. Python 3.13.12 / SDK 1.42.96 uses
pinned definitions. Positive constructors are recording-only in both environments.

An initial validation mistake is preserved, not concealed: v3/v4 each ran two
inherited smoke cases that construct real Bedrock SDK clients with invented
credentials and replaced HTTP transport. No outbound attempt occurred, and the
new factory itself was never constructed through real SDK constructors. This
exceeded the task's stricter no-real-client testing boundary. Final v7/v8 replace
those constructors with disclosed recording clients using installed service/
serializer definitions, leaving accepted test source and assertions unchanged.
Their final pass does not establish actual SDK client/event/retry integration.
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
It binds final commands/logs/JUnit, helper hashes, actual environments and the
scope deviation. Final commit and blob/WC hashes are in `commit-receipt.json`;
the completion index binds receipts without signing material or private inputs.

## Preservation, review scope and remaining gates

Before/after metadata snapshots cover 18 preexisting worktrees, four reports,
133 readable sealed files, protected ZIPs/configuration/locks and pricing evidence.
1084 inaccessible sealed entries remain explicitly inaccessible; no permissions
were changed or fresh certification claimed. Accepted source trees are unchanged;
only the three additions may be committed in this new worktree. Historical
evidence and main/shared unstaged documents are preserved at their existing bindings.

Claude's next review should assess the pinned Session overrides against installed
SDK source, credential/provider exclusion, configuration and error boundaries,
one-use concurrency, secret-safe surfaces, and unchanged consumer/adapter seam.
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
