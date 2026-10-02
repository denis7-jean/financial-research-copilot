# Reviewer Protocol v2: offline preparation and adoption verification

Owner authorization: the current work-chat request accepting `b22d0b7`, subject
to deferred independent review. Codex is the active writer. Four scoped additions:

- `experiments/reviewer_protocol_v2/production_preparation.py`
- `experiments/reviewer_protocol_v2/ledger_adoption.py`
- `tests/test_reviewer_v2_preparation.py`
- This implementation receipt.

Existing code, schemas, external selection bytes, analysis populations and private
artifacts are unchanged. Every invocation of either new filesystem API used only
invented test workspaces. Reading source/history and existing metadata to recover
the contract did not invoke either API on production inputs.

## Implemented preparation interface

`prepare(root, artifacts, code_bindings, generating_sources, historical_manifest,
expected_historical_manifest_sha256, executing_sources,
trusted_expected_inputs_sha256=None, proposed_freeze1=None,
trusted_expected_freeze1_sha256=None)` returns `(InputBinding bytes | None,
PreparationReport bytes)`. It never writes artifacts. The separate optional trusted
input hash checks evidence against a caller's previously trusted value. Without
it, a calculated hash remains evidence only. Neither branch authenticates owner
approval. There is no approval field accepted inside InputBinding.

InputBinding uses the unchanged exact six-field selection contract: schema,
artifacts, code, runtime, seed and strata. It retains the four artifact roles,
five code roles, seed 20261001 and six accepted stratum entries. The implementation
reuses `selection.prepare_inputs`, `verify_input_binding`, filesystem binding
checks, and `exposure.validate_inventory`. PreparationReport uses the accepted
exact schema, status, inputs_sha256, freeze1_sha256 and findings fields. Failures
return no InputBinding and one sanitized accepted finding code, with artifact=null.
No question, identity, annotation, arbitrary exception string or secret is returned.

Both JSON objects use the existing canonical encoder: UTF-8, escaped Unicode,
sorted keys, compact separators, finite values and final LF. SHA-256 hashes the
entire exact byte string. Existing population input bytes are not reformatted;
the original ledger must already satisfy its historical canonical JSONL format.

Verification covers lexical approved roots (`main/`, `heldout-external/`), resolved
root containment and approved-subtree containment, including symlink/junction
escapes. Exact artifact hashes are checked before parsing. It verifies original
identity and six metadata fields, question hashes, dispositions, Boolean exposure
flags and derived final flags, plus direct-exposure consistency with the inventory.
It does not recompute dependence, near-duplicate exposure or population screening.

The inventory is checked against the population and historical input/source
bindings. Original inventory/ledger bytes must match the original manifest's
payload hashes. Historical implementation provenance stays separate from current
selection and interface bundles. All thirteen supplied executing source files must
match both the installed source paths and the caller's workspace copies; the
unchanged selection runtime checks remain mandatory. This is disk-source binding
verification, not attestation of past execution or a protection against a
concurrently hostile process replacing files. No durable operational claim exists.

`validate_preparation(root, binding_raw, report_raw,
trusted_expected_inputs_sha256, trusted_expected_freeze1_sha256=None)` checks
canonical report/binding bytes, exact report allowlist, separately supplied trusted
hashes and the existing complete InputBinding/population/ledger validator. It is
a binding/report validator, not an independent replay of the historical evidence
checks in `prepare`, a human-approval authenticator or an operational readiness gate.

A successful pre-Freeze-1 report has `freeze1_sha256=null` and status PREPARED.
That status means only offline verification passed. A supplied proposed Freeze 1
cannot produce PREPARED while its historical-adoption encoding is unspecified.
No Freeze 1 evidence is generated. Runtime requirements are not relaxed.

## Recovered historical generating contract

Accepted evidence: `182f131` and its offline implementation receipt;
`08fa6d9` and the selection specification; the owner's phase/adoption amendment
in attachment `52847c5a-dc83-4fc2-b6d6-8e0032c20bf2`; and the current task.
Repository history at `182f13192809676a9a5d4fa27579df3d58211ce3`
provides the exact generating sources. `audit.implementation_hash` was:

```python
folder = Path(__file__).parent
files = {
    path.name: sha_bytes(path.read_bytes())
    for path in sorted(folder.iterdir())
    if path.suffix in {".py", ".json"}
}
return sha_bytes(canonical(files))
```

The exact sixteen filenames are __init__.py, __main__.py, analysis.py, audit.py,
common.py, constraints.py, eligibility.py, exposure.py, fixtures.py,
input_hashes.json, integrity.py, known_inventory.py, packet_validation.py,
selection.py, similarity.py and validation.py. The hash preimage is the canonical
filename-to-file-SHA-256 mapping, not concatenated sources or a current package
digest. Replaying that recipe on Git source bytes independently reproduced
`105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`.
No historical source was imported or executed to reproduce it.

The verifier requires the complete exact source set, validates the hash function's
AST against that recovered recipe without execution, and checks the resulting
digest against the original manifest and ledger/aggregate implementation fields.
It verifies the four original payloads, manifest byte contract, nonfrozen audit
type, canonical bytes and independently supplied expected manifest hash.

Original `input_hashes.json` bytes are hashed exactly, without imposing a later
layout. The original integrity payload must bind those bytes and the identical
pin map. Every pinned input is read through the approved-root adapter. The four
additional original input hashes are recovered as literal AST values from
`integrity.DESIGN_HASHES`, `integrity.RECOVERY_SHA256` and
`known_inventory.DOC_QUOTES_SHA256`, and their file bytes are checked too.
Inventory supporting-file hashes and evidence source hashes must join to this
historical input closure. A current digest or semantic similarity cannot replace
any of those bindings. Sources are data, never imported or evaluated as code.

Original recorded runtime is exactly CPython / 3.13.12 / Unicode 15.1.0. The old
manifest does not record the later platform/float fields or a complete dependency
lock. The verifier checks the recorded three-field contract; it does not invent
past SDK versions, broaden that evidence or declare the live runtime lock complete.

## Adoption results and genuinely missing contract

`verify_adoption(root, manifest_binding, expected_manifest_sha256,
generating_sources, population_binding, ledger_binding, selection_binding,
proposed_freeze1=None, expected_freeze1_sha256=None)` returns an ephemeral technical
result: historical_provenance_verified, proposed_freeze_compatible,
operational_adoption_performed, code and hashes. It produces no adoption record,
seal, claim, repaired artifact or authorization.

Without proposed Freeze 1 evidence, verified original bindings yield provenance=true,
compatibility=null, operational_adoption_performed=false and code
BINDINGS_VERIFIED_NOT_ADOPTED. Current selection binding/source copies are checked
separately. A verified provenance flag establishes artifact bindings only; it
does not independently prove execution history or authenticate human approval.

The accepted FreezeManifest role envelope is recoverable, but the exact content
encoding for explicit historical-generating implementation, rule, runtime and input
bindings is not specified by the accepted adoption amendment. In particular a
Python rule source is not automatically an approved specification artifact, and
the ten-field InputBinding runtime is not automatically a dependency lock.

For a supplied proposed Freeze 1, the verifier checks the canonical accepted
envelope, phase, exact role set, independently supplied expected hash, all bound
artifact bytes, original population binding and original inventory binding.
If these checks pass, it returns FREEZE_ADOPTION_ENCODING_UNSPECIFIED with
compatibility=false, retaining verified historical provenance. Earlier inconsistencies
return their specific failure. No invented source-file-as-specification or
runtime-as-lock convention can yield a compatibility success.

**Remaining owner decision:** approve the exact Freeze 1 encoding that explicitly
binds the complete historical generating source mapping, original rule artifacts,
recorded runtime and original input closure, including the four extra inputs.
After acceptance, extend compatibility validation using invented fixtures. The
current task does not establish that encoding or a successful operational adoption.

## Validation evidence

Commands executed from `main` using existing local tools; no installs:

```powershell
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_preparation.py -q -s --basetemp=.pytest_cache/reviewer-v2-preparation-03
$verificationTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' })
& .venv\Scripts\python.exe -B -m pytest @verificationTests -q --basetemp=.pytest_cache/reviewer-v2-preparation-regressions-01
.venv\Scripts\ruff.exe check experiments/reviewer_protocol_v2 tests/test_reviewer_v2*.py
.venv\Scripts\ruff.exe format --check experiments/reviewer_protocol_v2/ledger_adoption.py experiments/reviewer_protocol_v2/production_preparation.py tests/test_reviewer_v2_preparation.py
```

49 new cases pass; combined v2 suite: **465 passed**, including 416 unchanged
regressions. Ruff and formatting checks pass. The existing asyncio_mode config
warning remains; these tests are synchronous. Four deliberate network-guard
lookups were intercepted by the combined suite; none sent. Ordinary Windows
symlink creation required a privilege unavailable here, so the test exercises
the escape with a test-owned directory junction instead; no test was skipped.

Tests cover deterministic preparation/provenance, separate trusted hashes, stale
and self-declared evidence, missing/altered artifacts, metadata/question/flag joins,
source/runtime/dependency mismatches, incomplete generating evidence, original
runtime/input/inventory failures, historical/current separation, proposed-freeze
mismatch and unresolved encoding, traversal/junction escape, sanitized errors,
unchanged workspace bytes, forbidden ranking/ID/packet/schedule hooks, import
purity and the offline guard. No operational sealing function exists to invoke.

Two independently located invented workspaces produced identical exact bytes:

| Synthetic artifact | SHA-256 |
|---|---|
| InputBinding | a03a72606dfefacee5f0bb160fbca8ea67f5c237b92d044f52ddeebb65e37b51 |
| PreparationReport | ef1a39ae81d284de39ec9ae381bc1fd1106eba5ea7d4d11087a84cf87712b2b3 |
| Ephemeral provenance result, canonicalized for testing | ebf513f3f7ceffd421291371e5dcd6e3fa21a8f18833f10238b08a3526eac4d1 |

InputBinding/PreparationReport hashes include the accepted current runtime and
therefore are specific to this runtime; they are not portable approval hashes.

## Dependency coverage and integrity

Fresh-process import closure exactly equals the thirteen VERIFICATION_BUNDLE_PATHS:
the ten existing interface dependencies plus exposure.py, ledger_adoption.py and
production_preparation.py. Supplied source bytes are checked against installed
sources and workspace copies. Verification bundle digest:
`539c8563a3919a45e2b099c29a0075cd50f485042f373f9cda9fa2ed042a165b`.
This separately reported bundle does not add a field to accepted InputBinding.

Existing bundle digests remain unchanged:

- Selection: `1cd9a742c8a3a10a82ca660c0edeaea3da90229dcaa06454432c17d47890fbf4`.
- Control/trial: `3c6028eaa52f3d7b35bf92c67911d1e9a14b8776588808030bb6cfced227fc18`.
- Owner audit: `4d43a47492c543bf1a2d15e6f759515e0fe12aa109b0b262f97e085ccb3bb486`.

Read-only existing `integrity.verify_historical` verified 107 protected files and
72 historical bindings, pin digest
`ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae`.
Existing `verify_output_manifest` verified both final-1/final-2 four-payload
manifests unchanged at
`057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4`.
These checks used the old integrity APIs, not the new preparation/adoption APIs.
Eight unrelated untracked documents and all private artifacts are preserved.

## Consolidated remaining work and phase boundary

Accepted sequence stays: Freeze 1 -> production-ledger verification/sealing ->
authorized external selection -> owner audit -> Freeze 2 -> separately authorized
live execution.

| Area | Status / remaining work |
|---|---|
| Pure offline components | Existing eligibility/exposure, selection/serialization, control/trial and owner-audit components remain accepted subject to review. New preparation and historical provenance verifiers implemented with synthetic validation; owner acceptance and independent review pending. Proposed Freeze 1 adoption compatibility remains unresolved as above. |
| Operational tools | No production CLI, trusted authorization manager, durable claim, publication/recovery manager, production adoption seal, operational owner seal or Freeze builder implemented by this task. They need separately authorized implementation and execution. |
| Actual content | Control wording, item-specific keys, diagnostic expectations and rubric still require private approval; no owner labels authored. |
| Independent review | Claude review remains deferred/unwaived across 182f131, 08fa6d9, de28891, b22d0b7 and this change. Any additional OpenAI review is separately recorded. |
| Freeze 1 | Exact adoption encoding, explicit historical procedure bindings, complete applicable runtime/dependency evidence, accepted design/content prerequisites and independent review remain prerequisites; no freeze/readiness declared. |
| After Freeze 1 | Separate authorization for actual preparation/bindings and production-ledger adoption/sealing; then approved external selection/publication, owner audit and operational owner sealing in accepted order. |
| Freeze 2 / live | Provider envelopes/settings, exact request hashes, cost/token/terms/credit evidence, safeguards and recoverable independent backup remain in their accepted phases. Freeze 2 and live execution require their own prerequisites and authorization; none moved to claim readiness. |

The next bounded implementation after owner acceptance of the missing encoding
is a synthetic-only extension of proposed-Freeze-1 compatibility validation.
It must preserve these byte contracts and perform no operational adoption/freeze.

Scope receipt: four additions only; synthetic API inputs only; no real preparation
or bindings, ledger adoption, ranking/IDs, sampling, production packets, operational
seals/freezes, owner labeling, reviewer/router invocation, AWS operation, external
API call or push. Deferred Claude independent review is unwaived.
