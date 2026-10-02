# Reviewer Protocol v2: offline preparation and adoption verification

The `184a256` milestone is accepted subject to deferred review. Its receipt below
records that milestone's state and digest. The authorized synthetic-only follow-up
defines the encoding in the following section **before implementation**. This
section supersedes the old encoding blocker, not any evidence/approval prerequisite.

## Historical-adoption encoding v1 (delegated technical contract)

No FreezeManifest role or InputBinding field changes. Exactly the existing fifteen
Freeze 1 roles remain mandatory; phase is FREEZE_1. Notation: H is exactly 64
lowercase hexadecimal characters; FB is exactly `{path: string, sha256: H}` with
the existing lexical/resolved approved-root protections. `v(n)` is exactly
`reviewer-protocol-v2-` + n + `-v1`. All fields below are mandatory and exact;
there are no additional/approval fields. Maps have the stated exact key sets.

FreezeManifest.artifacts has exactly population, exposure_inventory,
eligibility_specification, exposure_specification, selection_specification,
remaining_interfaces_specification, eligibility_exposure_code_bundle,
selection_code_bundle, synthetic_test_manifest, grouping_similarity_specification,
historical_similarity_source, runtime_dependency_lock, historical_integrity_manifest,
definitive_heldout_exclusion_policy and design_approval_evidence, each an FB.
The enclosing exact fields remain schema=v("freeze-manifest"), phase=FREEZE_1
and artifacts. No approval, readiness or adopted flag is added to that envelope.

Every new object is `common.canonical`: UTF-8, ASCII Unicode escapes, sorted keys,
compact separators, finite JSON values, final LF, no BOM or duplicate keys.
Every FB hashes the complete referenced raw bytes, not decoded text. Object maps
sort canonically; stdlib_modules is a sorted, unique array of module-root names.
No reference points back to the enclosing procedure or FreezeManifest, avoiding
hash cycles. The FreezeManifest hash is always a separate caller input.

Existing role `eligibility_exposure_code_bundle` points to:

```text
HistoricalGeneratingBundle = {
  schema: v("historical-generating-bundle"),
  recipe: "SHA256_CANONICAL_FILENAME_HASH_MAP_LF_V1",
  sources: {each of the exact sixteen GENERATING_FILES filenames: FB},
  implementation_sha256: H
}
```

Each FB basename must equal its filename; all sixteen resolved source paths are
distinct and bytes exactly equal the separately supplied historical source bytes.
`implementation_sha256 = SHA256(canonical({filename: SHA256(source raw bytes)}))`.
The wrapper hash is separate from that historical digest. The original audit
recipe AST, complete source set and recorded digest checks from 184a256 remain.
The recipe label describes those recovered bytes; it introduces no new domain
prefix into the historical preimage.

Existing role `remaining_interfaces_specification` points to:

```text
AdoptionInterfaceBinding = {
  schema: v("adoption-interface-binding"),
  specification: FB,
  verification_bundle: {files: {each of 13 VERIFICATION_BUNDLE_PATHS: H}, sha256: H}
}
```

The specification FB binds the actual proposed interface specification separately
from executing code. Its bytes may not be a generating/current source file.
`verification_bundle.sha256 = SHA256(canonical(files))`. All thirteen file hashes
must match supplied executing source bytes, installed source paths and workspace
copies. Existing role `selection_code_bundle` retains exactly the current accepted
`{files, sha256}` wrapper and existing seven-source recipe. These current bundles
must remain distinct from the historical implementation digest.

Existing role `runtime_dependency_lock` points to:

```text
AdoptionRuntimeLock = {
  schema: v("adoption-runtime-lock"),
  scope: "OFFLINE_PREPARATION_SELECTION",
  runtime: {exact unchanged nine-field InputBinding runtime},
  stdlib_modules: [string, ...],
  third_party_distributions: []
}
```

Runtime values and types must match the actually executing accepted runtime and
the referenced InputBinding. stdlib_modules must equal the sorted set of all
absolute import roots in all thirteen executing source ASTs, excluding the
repository-local `experiments` root; every root must be in sys.stdlib_module_names.
This scan includes imports inside functions. Relative imports or a nonstdlib root
block this scoped lock; third_party_distributions must be exactly an empty list.
This is explicit dependency evidence for the current offline source closure,
not a historical dependency assertion, full binary environment attestation or a
provider/live SDK lock. No unrecorded historical SDK/platform fields are inferred.
Any broader procedure needs its separately applicable lock before readiness.

Existing role `historical_integrity_manifest` points to:

```text
HistoricalAdoption = {
  schema: v("historical-adoption"),
  audit: {
    manifest: FB,
    payloads: {inventory.json, population_ledger.jsonl, aggregate.json, integrity.json: FB}
  },
  generating_bundle: FB,
  recorded_runtime: {implementation: "CPython", python: "3.13.12", unicode: "15.1.0"},
  pin_map: FB,
  additional_inputs: {the exact four recovered full relative paths: H},
  input_closure: {every original pinned or additional input path: H},
  input_closure_sha256: H,
  rules: {each of RULE_ROLES: {
    original_evidence: FB, specification: FB, relationship_evidence: FB
  }},
  proposed_runtime_dependency_lock: FB,
  current_bindings: {selection_bundle: FB, remaining_interfaces: FB},
  selection_inputs: FB
}
```

RULE_ROLES is exactly eligibility_specification -> eligibility.py,
exposure_specification -> exposure.py, grouping_similarity_specification ->
similarity.py. The original-evidence FB must join to the verified original input
closure and be separate from all generating/current source bytes. The proposed
specification FB must equal that exact FreezeManifest role binding, with the same
raw-byte hash as original_evidence. A copy may use a different approved path;
semantic equivalence or source-as-specification is not accepted.

Each relationship_evidence FB points to the following exact explicit witness:

```text
HistoricalRuleRelationship = {
  schema: v("historical-rule-relationship"),
  role: one RULE_ROLES key,
  original_evidence: FB,
  generating_source: {filename: the role's historical filename, sha256: H},
  specification: FB,
  relation: "IDENTICAL_EVIDENCE_BYTES"
}
```

Every witness field must equal its independently verified referenced evidence,
source mapping and frozen role binding. The witness documents the proposed
technical association; it does not authenticate original specification approval
or prove that a prose document semantically governed past execution. Content,
rule applicability and approval evidence remain separately reviewable prerequisites.
Witnesses cannot replace missing original rule/specification evidence.

The audit manifest FB must equal the caller's original binding and separately
supplied trusted manifest hash. Its four payload FBs must use the original manifest
directory/name and exact recorded hashes; no rewritten ledger is accepted.
generating_bundle must equal the frozen code role; pin_map must equal its exact
input_hashes.json FB and original integrity pins hash. additional_inputs is exactly
the two design evidence files, document-quotes.json and recovered-references.json
under heldout-external/reviewer-protocol-v2-offline/, as recovered from original
source literals. input_closure must equal the verified pins plus all four inputs,
including any exact overlaps; its preimage is `canonical(path-to-hash map)`.
No omitted, substituted, extra or merely declared input is permitted.

recorded_runtime must equal the original manifest/aggregate three-field record.
proposed_runtime_dependency_lock and both current_bindings FBs must equal their
corresponding frozen roles. selection_inputs points to an unchanged canonical
InputBinding, verified with existing validators and joins: population/inventory/
selection-specification FBs equal the frozen roles; ledger equals the original
payload FB; current selection code/runtime/historical implementation fields agree;
historical_similarity_source equals its frozen role. Preparation also compares
these complete InputBinding bytes to its independently constructed value.

The nine runtime fields are python_implementation, python_version, unicode_version,
platform, machine and byteorder (strings), plus float_radix, float_mant_dig and
float_max_exp (integers, excluding Booleans). Exact values and types come from the
unchanged executing runtime_binding; no fields are added.

Verification order: separately trusted FreezeManifest hash/envelope and all role
bytes; original population/inventory joins; exact adoption schema and audit FBs;
sixteen-source wrapper/recipe/raw bytes; pin/additional/full input closure;
recorded runtime; supplied executing source identity check; three original
rule-evidence/specification/witness joins; current interface/selection bundle joins; proposed scoped
runtime/dependency lock; complete InputBinding validation and cross-role joins.
The prior historical verifier executes before this compatibility procedure.

Missing evidence or any failed join returns a sanitized code and never compatibility=true;
compatibility is false when assessed, or null when failed provenance prevents
assessment. No successful adoption artifact is emitted. Self-declared approval/hash fields
are rejected by exact schemas. Caller hashes must be separately supplied and are
never obtained from an approval field. Matching hashes prove bindings, not the
trustworthiness of the caller, human approval or past execution. Success changes
only the ephemeral proposed_freeze_compatible flag to true; operational adoption
remains false. No overall Freeze 1 readiness is inferred, and unrelated Freeze
roles remain hash-checked evidence rather than independently approved content.

## Original 184a256 milestone receipt

This historic receipt retains its original synthetic hashes and bundle digest.
Current follow-up evidence and consolidated prerequisites appear at the end.

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
the InputBinding runtime is not automatically a dependency lock.

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

## Follow-up implementation and evidence

Owner's current delegation authorizes deterministic encoding choices without
additional schema-choice approval. Implementation follows the v1 contract above;
it does not change rules, adopt missing evidence or infer historical runtime facts.
The old FREEZE_ADOPTION_ENCODING_UNSPECIFIED blocker is replaced by complete
binding checks. Missing actual evidence still fails; compatibility is technical.

Six scoped files: the two verifiers, the existing preparation test, new
`tests/test_reviewer_v2_adoption_encoding.py`, this document and the new local
`reviewer-protocol-v2-claude-review-handoff.md`. No other tracked file changes.
The old missing-encoding test now checks missing encoding evidence rejection.
All other old tests and external selection/analysis/interface code remain intact.

`verify_adoption` adds optional `executing_sources` and `input_binding_raw` caller
parameters, without changing the ephemeral result schema. A proposed Freeze 1
requires the supplied executing source map; a separately supplied current binding
must match selection_inputs exactly. Preparation passes both its already verified
source map and independently constructed canonical InputBinding bytes. It can
now return PREPARED with the supplied trusted proposed Freeze 1 hash when technical
compatibility succeeds. No authorization or readiness follows from that report.

New wrappers and witnesses are validated/read only. Tests assemble their invented
bytes with the existing canonical encoder; no production writer or freeze builder
was introduced. All referenced original artifacts remain unchanged. Reports retain
sanitized codes and hashes; no question text, identities or annotations are emitted.

Commands run from `main`:

```powershell
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py -q -s --basetemp=.pytest_cache/reviewer-v2-adoption-encoding-02
$adoptionRegressionTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' })
& .venv\Scripts\python.exe -B -m pytest @adoptionRegressionTests -q --basetemp=.pytest_cache/reviewer-v2-adoption-encoding-regressions-01
.venv\Scripts\ruff.exe check experiments/reviewer_protocol_v2 tests/test_reviewer_v2*.py
.venv\Scripts\ruff.exe format --check experiments/reviewer_protocol_v2/ledger_adoption.py experiments/reviewer_protocol_v2/production_preparation.py tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py
```

Focused suite: **86 passed**, comprising 49 previous verifier cases and 37 new
encoding cases. Entire relevant v2 suite: **502 passed**, with the existing
asyncio_mode configuration warning. Ruff and formatting checks pass. Four deliberate
network attempts were intercepted by the combined guard, none sent. The two
junction-escape tests use test-owned paths; no skips. No-writes tests cover successful
compatibility and preparation, with ranking/ID/packet/schedule entry points patched
to fail if reached. No publication/seal/freeze operational manager exists or is imported.

Two independent invented workspaces produced identical bytes (current runtime):

| Synthetic artifact | SHA-256 |
|---|---|
| Proposed FreezeManifest fixture | b85b6c2a754bc1172cae2a488409c026951afd484dc55b2050f37496aab8b91f |
| HistoricalAdoption | 78aa8b33027e0f2a1616f801010c80450f11556077e4e4bf21fcad368e980fa8 |
| PreparationReport with proposed binding | 6a261978533bd8ac70144f55918326ae850368e5eda6d783c1c7e42e46cde15c |
| Ephemeral compatibility result | 4527da73c3ad6b2727fc277e837d786f8cdad62665b2f11a5981854cda70115a |

New thirteen-file verification bundle digest, reported separately:
`151994fdd1185648040764212a715686e34f137755f247a17f412f9d4adf4802`.
Prior selection/control/owner/historical generating digests above are unchanged.
Direct stdlib imports in the verified current source closure are exactly ast,
collections, hashlib, json, math, pathlib, platform, re, sys and unicodedata.
Fresh-process import purity still matches the thirteen-file closure and permits
no filesystem reads/writes or outbound network access during import.

Read-only old integrity APIs again verified 107 protected files, 72 historical
bindings and both final-1/final-2 four-payload manifests at the unchanged hashes
above. No new verifier API received real historical/production data. Eight
unrelated untracked documents remain untouched. No push or Claude invocation.

## Current consolidated prerequisite list

1. **Review and actual evidence:** deferred independent Claude review across all
   milestones remains required/unwaived; owner acceptance of this implementation
   remains pending. Actual applicable original rule/specification evidence and its
   reviewed relationship, original full input/source closure, proposed scoped lock
   and procedure bindings must be supplied and verified. Technical schemas are
   now defined; no further owner decision is needed just to choose bytes. Hashes
   and witnesses do not authenticate approval or independently establish execution.
2. **Content and Freeze 1:** private control wording, keys, diagnostic expectations,
   rubric and all applicable design/content/evidence approvals remain outstanding.
   The offline scoped lock does not satisfy broader live/provider dependencies.
   Full Freeze 1 prerequisite completion and explicit freeze authorization remain
   separate; this task declares no readiness and creates no operational freeze.
3. **Operational implementation and execution:** trusted authorization, durable
   claims, publication/recovery, production-ledger adoption/seal, operational owner
   seal and Freeze builders are not implemented. Separate authorization is required
   for real preparation and operations. Accepted order remains Freeze 1 -> production
   ledger verification/sealing -> authorized external selection -> owner audit ->
   Freeze 2 -> separately authorized live execution. Freeze 2/live provider settings,
   request hashes, cost/token/terms/credit evidence, safeguards and recoverable backup
   remain in their accepted phases. No actual owner labels or content approval here.

Scope receipt: only verifier extensions, focused synthetic tests and documentation;
no real preparation/bindings, ledger adoption, real ranking/IDs, sampling, production
packets, operational seals/freezes, owner labeling, reviewer/router invocation,
AWS operation, external API call, Claude message/invocation or push.
