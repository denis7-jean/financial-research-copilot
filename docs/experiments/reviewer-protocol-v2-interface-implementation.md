# Reviewer Protocol v2: pure control and trial interfaces

Owner authorization: current work-chat attachment
`52847c5a-dc83-4fc2-b6d6-8e0032c20bf2`, following implementation `08fa6d9`.
Codex is the active writer. Deferred independent Claude review is not waived.
This receipt implements only pure byte validators/serializers, not production
preparation, authorization, publication, owner sealing, freeze builders, provider
envelopes or runners. Actual control wording, keys and diagnostic policy
expectations remain unapproved. All exercised content is invented test data.

Five scoped additions:

- `experiments/reviewer_protocol_v2/control_serialization.py`
- `experiments/reviewer_protocol_v2/trial_interfaces.py`
- `tests/test_reviewer_v2_controls.py`
- `tests/test_reviewer_v2_trial_interfaces.py`
- This document.

No existing source, tests or specifications were changed. In particular the
accepted external-only selector, serializer, schemas and byte contracts remain
unchanged, and the real-selection CLI remains disabled.

## Implemented byte and schema contracts

Every private object has exactly the listed keys. All input private JSON and
JSONL must already use `common.canonical`: strict UTF-8, escaped Unicode,
sorted object keys, compact separators, finite numbers and one final LF.
Duplicate keys, extra fields, invalid types and noncanonical bytes fail.
Strings must be encodable in strict UTF-8. IDs/hashes are lowercase full SHA-256.
Original questions round-trip verbatim, including Unicode and embedded LF.

Notation: H = 64 lowercase hex characters; X = `x_` + H; R = `r_` + H;
FB = exactly `{path: string, sha256: H}`. FB resolves only through a caller-supplied
path-to-bytes dictionary and verifies those bytes; it never reads the filesystem.
Paths require `main/` or `heldout-external/`, with no absolute path, backslash,
colon, empty/dot/traversal segment. A future filesystem adapter must also apply
the accepted resolved-root/symlink protections. Presentation paths require
`heldout-external/` and three distinct destinations.

`v(name)` below expands exactly to `reviewer-protocol-v2-` + name + `-v1`.
These abbreviations are documentation notation, not permissive schema modes.

```text
ControlCatalog = {
  schema: v("control-catalog"),
  items: [{
    local_key: string matching [a-z][a-z0-9_-]{0,63},
    kind: "ANCHOR" | "DIAGNOSTIC",
    question: nonempty strict-UTF-8 string,
    provenance: {
      author: nonempty string, source_revision: nonempty string,
      approval_evidence: FB
    }
  }]
}
```

Exactly 21 records: 15 anchors and six diagnostics. Records sort by local-key
UTF-8 bytes and local keys are unique. The `source_wording_approvals` byte map
supplies independently existing source-wording approval evidence. It does not
include or establish the later approval/seal of the catalog and keys. Content
hash verification proves a supplied artifact binding, not human approval or
correctness of the wording. Later catalog/key approval managers are outside scope.

The dependency direction is source-wording evidence -> catalog -> references and
keys -> later catalog/key approval. No later seal is consumed to construct its
own catalog. Validators reject catalog/key bytes or their exact digest strings
as downstream self-references in the supplied wording evidence; they do not claim
to authenticate arbitrary approval prose or replace a future approval interface.

Using the unchanged accepted B-array encoding (compact ASCII-escaped finite
JSON, strict UTF-8, no LF/BOM), exact preimages are:

```text
reference preimage = [
  "reviewer-protocol-v2-control-reference-v1", catalog_sha256, local_key
]
reference = "r_" + SHA256(preimage).hexdigest()

visible ID preimage = [
  "reviewer-protocol-v2-control-id-v1", 20261003,
  reference_key, original_question_sha256
]
visible ID = "x_" + SHA256(preimage).hexdigest()
```

Both control roles use the same visible ID procedure and shape as external IDs.
No role, key or provenance field appears in reviewer records. Reference or visible
ID collisions are errors, with no repairs or seed changes.

```text
ControlMapping = {
  schema: v("control-map"), catalog: FB, packet_sha256: H,
  items: [{
    item_id: X, reference_key: R, local_key: string,
    kind: "ANCHOR" | "DIAGNOSTIC", original_question_sha256: H
  }]
}
ControlKeys = {
  schema: v("control-keys"), catalog_sha256: H, rubric_sha256: H,
  entries: [AnchorKey | DiagnosticKey]
}
AnchorKey = {
  reference_key: R, kind: "ANCHOR", original_question_sha256: H,
  expected_label: one of the accepted five labels,
  expected_components: ["qa","summarize"] for multi_intent, otherwise [],
  generic_rationale: nonempty string
}
DiagnosticKey = {
  reference_key: R, kind: "DIAGNOSTIC", original_question_sha256: H,
  category: "OMITTED_COMPANY_OR_PERIOD" | "ESSENTIAL_UNSEEN_MATERIAL" |
            "BOUNDARY_INTERPRETATION",
  policy_expectation: nonempty string, scoring_permitted: false
}
```

Mapping items sort by item ID; keys sort by reference. Require complete 21-item
bijections, question/role/reference bindings, three anchors per approved label,
two diagnostics per category, and exact Boolean false for diagnostic scoring.
No diagnostic correctness key is introduced. Keys bind the separately supplied
expected rubric digest. These validators do not approve the rubric or keys.

Control packet: exactly 21 canonical JSONL records with only string `item_id`
and `question`, sorted by opaque-ID UTF-8 bytes.

```text
Membership = {
  schema: v("trial-membership"),
  external_packet_sha256: H, external_mapping_sha256: H,
  control_packet_sha256: H, control_mapping_sha256: H,
  control_keys_sha256: H, rubric_sha256: H, combined_packet_sha256: H,
  items: [{
    item_id: X, kind: "EXTERNAL" | "ANCHOR" | "DIAGNOSTIC",
    reference_key: X for external, R for controls,
    original_question_sha256: H
  }]
}
```

Combined packet: exact union of 24 external and 21 controls, 45 canonical
two-field records in item-ID order. Membership is private, in the same order,
and requires exact 24/15/6 counts and complete joins to all source artifacts.
The external packet/map consistency validator reconstructs the accepted
external ID/map bytes and quotas. It does not certify eligibility, authorize
selection, or replace the accepted upstream ledger/receipt replay. A future
production caller must validate that accepted selection result first.

ID collisions and exact duplicate-question hashes anywhere in the combined
membership fail assembly. Builders return bytes only and never mutate inputs or
write files. The external selection remains intact. There is no redraw,
substitution or silent control rewriting, and no added similarity exclusion.

Reviewer presentation uses a separate accepted domain and seed:

```text
presentation preimage = [
  "reviewer-protocol-v2-presentation-order-v1", 20261002,
  reviewer_slot, item_id
]
sort key = (raw SHA-256 digest bytes, strict UTF-8 item-ID bytes)
```

Apply independently to all 45 fixed members for R1, R2 and R3. This is ordering,
not external candidate selection. Each reviewer sees exactly the same questions
and IDs once, without class/private metadata. Questions can suggest their origin;
uniform IDs do not guarantee semantic concealment or prevent reidentification.

```text
PresentationManifest = {
  schema: v("presentation-manifest"), combined_packet_sha256: H,
  membership_sha256: H,
  domain: "reviewer-protocol-v2-presentation-order-v1", seed: 20261002,
  reviewers: [{
    reviewer_slot: "R1" | "R2" | "R3",
    item_ids: [45 unique X values], packet: FB
  }]
}
LogicalSchedule = {
  schema: v("logical-schedule"), presentation_manifest_sha256: H,
  retry_limit: integer 0,
  items: [{
    schedule_index: positive integer, reviewer_slot: "R1" | "R2" | "R3",
    presentation_index: positive integer, item_id: X, record_sha256: H
  }]
}
```

Manifest reviewer order is R1/R2/R3. Presentation packet records follow each
permutation, with canonical line bytes. The logical schedule interleaves
position 1 R1/R2/R3, position 2 R1/R2/R3, through position 45: exactly 135 entries,
each reviewer/item pair once. Record hashes include the canonical record LF.
Booleans are rejected for seed, retry limit and indexes. Complete reconstruction
checks manifest and schedule bytes, including all nested fields and ordering.
Provider request serialization, actual model identities and runtime response
envelopes remain separate Freeze 2 requirements.

## Public pure API and validation boundary

`serialize_catalog`, `validate_catalog`, `serialize_keys`, `validate_keys`,
`build_controls`, `validate_controls`, `build_trial`, `validate_trial`,
`build_presentations`, `validate_presentations`, `build_schedule` and
`validate_schedule` operate only on supplied values/bytes. No file creation,
credentials, network, operational approval or seal/freeze occurs.

Full `validate_trial` reconstruction joins the external/control artifacts.
Presentation helpers additionally check membership structure and question hashes,
but cannot establish provenance without those source artifacts. Run the full
joins first; a self-consistent membership manifest is not a trusted approval.
Builders/validators fail before returning valid outputs. No CLI was added.

## Verification and reproducibility

103 new invented-fixture cases plus all 251 existing v2 cases passed: **354 total**.
Tests cover counts, private keys/references, reconstructions, Unicode/LF/escaping,
collisions, duplicate-question preservation, metadata masking, complete joins,
three permutations, exact raw-digest ties, all 135 schedule entries, zero retries,
types, schemas, hashes, paths, canonical failures and import purity. They patch
ranking and filesystem read/write hooks to fail while exercising the pure pipeline.
A fresh subprocess checks imports without file-opening, network or environment
side effects, with no cloud/credential-loader imports and exact dependency closure.

Initial targeted run: 88 passed, two negative mutations made no actual change;
those fixture mistakes were corrected. Subsequent targeted run: 90 passed.
Additional serialization/binding/IO-isolation cases brought the new total to 103.
One pre-existing `asyncio_mode` configuration warning remains. Two deliberate
network safety probes were intercepted in the combined suite; none was sent.
Ruff and Git whitespace checks passed.

Two invented reproductions are byte-identical; hashes:

| Output | SHA-256 |
|---|---|
| Control packet | 5d023be6631f3decb1ff55aa4a420c06eed2f27e25841c6c9e7f495d399d156c |
| Control mapping | d765258415e127b781b9a2171515bee9866735046f7775584693c3ec606fa765 |
| Combined packet | 5f0a08118b6604f2e96e09b6b0476ca2fd178c19b04ff7b1c3f29b36f66cbe5f |
| Membership | b9cb91635a4868ec43b927fe11af019db51d390774c6b566b5352c5bf9dbed78 |
| R1 presentation | 4152ce32b7db03f77641cb7471b9e56b43963fe7bf155076d7902c8f5edda697 |
| R2 presentation | 4730c59808a34f2d813fb256eb5eee42bd429fa00e7ba234bf99d67b0d967065 |
| R3 presentation | 5972f1a587adec7d04f798d14eed96f0eddc3b21cc00a1110d80523cb065dfaf |
| Presentation manifest | 80a99519d876d66c44cd99832338da7c8e9ea764475c7c015f2ef5bda431f82d |
| Logical schedule | 773cf9eabd4988172a856552e5675a99ff04421db458b8cee3a133fa94cb8450 |

Exact commands, from `C:\Projects\AWS Project\main` (execution paths only, never
serialized into deterministic artifact bindings):

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_controls.py tests/test_reviewer_v2_trial_interfaces.py -q --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-interfaces-01'
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_controls.py tests/test_reviewer_v2_trial_interfaces.py -q -s --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-interfaces-02'
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_controls.py tests/test_reviewer_v2_trial_interfaces.py tests/test_reviewer_v2_selection.py tests/test_reviewer_v2_packet_serialization.py tests/test_reviewer_v2_eligibility.py tests/test_reviewer_v2_exposure.py tests/test_reviewer_v2_regression.py tests/test_reviewer_v2_safety.py tests/test_reviewer_v2_validation_analysis.py -q --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-interfaces-03'
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_trial_interfaces.py::test_complete_membership_and_reproductions -q -s --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-interfaces-04'
.\.venv\Scripts\python.exe -B -c 'from tests.offline_guard import install; install(); import runpy; runpy.run_module("ruff", run_name="__main__")' format experiments/reviewer_protocol_v2/control_serialization.py experiments/reviewer_protocol_v2/trial_interfaces.py tests/test_reviewer_v2_controls.py tests/test_reviewer_v2_trial_interfaces.py
.\.venv\Scripts\python.exe -B -c 'from tests.offline_guard import install; install(); import runpy; runpy.run_module("ruff", run_name="__main__")' check experiments/reviewer_protocol_v2/control_serialization.py experiments/reviewer_protocol_v2/trial_interfaces.py tests/test_reviewer_v2_controls.py tests/test_reviewer_v2_trial_interfaces.py
.\.venv\Scripts\python.exe -B -c 'from tests.offline_guard import install; install(); from pathlib import Path; import json; from experiments.reviewer_protocol_v2.integrity import verify_historical, verify_output_manifest; from experiments.reviewer_protocol_v2.selection import selection_bundle, SOURCE_ROOT; from experiments.reviewer_protocol_v2.trial_interfaces import interface_bundle, INTERFACE_BUNDLE_PATHS; v=verify_historical(SOURCE_ROOT); print(json.dumps({"protected_files":v["protected_files"],"historical_bindings":v["frozen_bindings"],"pins_sha256":v["pins_sha256"],"old_manifests":{n:verify_output_manifest(SOURCE_ROOT / "heldout-external/reviewer-protocol-v2-offline" / n) for n in ("final-1","final-2")},"unchanged_selection_bundle":selection_bundle()["sha256"],"interface_bundle":interface_bundle({p:(SOURCE_ROOT/p).read_bytes() for p in INTERFACE_BUNDLE_PATHS})},sort_keys=True,indent=2))'
git diff --check
```

The guard is installed automatically for pytest and explicitly for Ruff/integrity.
No broader suite or dependency installation was needed.

## Dependencies and historical preservation

New interface bundle digest:
`3c6028eaa52f3d7b35bf92c67911d1e9a14b8776588808030bb6cfced227fc18`.
It hashes the canonical mapping of the following complete loaded repository-local
dependency paths to exact source hashes, verified in a fresh subprocess:

```text
main/experiments/__init__.py
main/experiments/reviewer_protocol_v2/__init__.py
main/experiments/reviewer_protocol_v2/common.py
main/experiments/reviewer_protocol_v2/eligibility.py
main/experiments/reviewer_protocol_v2/similarity.py
main/experiments/reviewer_protocol_v2/selection.py
main/experiments/reviewer_protocol_v2/packet_serialization.py
main/experiments/reviewer_protocol_v2/validation.py
main/experiments/reviewer_protocol_v2/control_serialization.py
main/experiments/reviewer_protocol_v2/trial_interfaces.py
```

`interface_bundle` accepts explicit source bytes without IO. A future production
adapter must verify those bytes against the actually executing code; the pure
hash helper itself does not authenticate arbitrary supplied source bytes.
Standard-library behavior remains covered by the accepted runtime lock.

Unchanged external selection bundle:
`1cd9a742c8a3a10a82ca660c0edeaea3da90229dcaa06454432c17d47890fbf4`.
Historical audit implementation stays separately
`105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`.
No historical output is regenerated to match the current package hash.

Read-only integrity verification passed for 107 protected files and 72 historical
bindings, with unchanged pin digest
`ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae`.
Original final-1/final-2 audit manifest hashes and their bound payloads remain
`057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4`.
Eight unrelated untracked documents are preserved. No new private production
artifact was created outside Git; pytest scratch directories contain invented data.

## Accepted amendments recorded for deferred work

The accepted sequence is Freeze 1 -> production-ledger verification/sealing ->
authorized external selection -> owner audit -> Freeze 2 -> separately authorized
live execution. No milestone beyond pure offline implementation is authorized here.

Owner abstention and context concern are independent Booleans. Abstention needs
null label/certainty, empty components and a nonempty explanatory note; it does
not require a context concern. A concern also needs a note and can accompany
either a label or abstention. Sealed observations are never replaced or used to
silently rewrite eligibility or populations. Owner audit/sealing is not implemented.

Before any owner-analysis implementation, explicitly accept this inclusion table.
The first two rows restate the accepted primary valid-vote populations; metadata
handling and supplementary filtering must not be inferred from schema validity:

| Measure | Primary inclusion | Denominator/reporting | Context concern handling |
|---|---|---|---|
| Reviewer-only pair agreement/Cohen kappa | External items with both reviewer votes valid | Shared-valid n and n/24; retain planned coverage/unconditional measures | Owner abstention or concern does not silently filter reviewer-only data |
| Reviewer-only Fleiss kappa | External items with all three votes valid | Complete-panel n and n/24; no imputation | Same primary population, independent of owner metadata |
| Owner-versus-reviewer agreement/kappa | External items with that reviewer valid and a non-abstained valid owner label | Eligible n plus planned-denominator reporting; abstentions separately | Concern alone is not an abstention and does not imply automatic primary exclusion; explicit policy acceptance required |
| Context-qualified supplementary analysis | Unresolved: requires a separately accepted concern/adjudication population rule | Exact included/excluded counts and reasons, alongside primary report | A Boolean concern alone does not prove dependence; never replace primary measures |

Historical ledger adoption is allowed only after Freeze 1 explicitly binds the
actual audit-generating implementation, rules, runtime and inputs and those exact
bindings can be verified. Adoption is a new production seal of unchanged bytes,
not retrospective rewriting/freezing of the original audit. Semantic similarity
to current code is insufficient; report the specific missing/mismatched binding.
No adoption verifier or seal builder was implemented in this task.

Preparation, selection, validation and publication remain distinct technical
operations. One explicit owner grant can authorize selection plus saving fully
validated results when it binds the input, exact procedure and destination policy;
no redundant second confirmation is required. Read-only replay/integrity checks
are not new sampling attempts. Failed/interrupted operations require registered
recovery and cannot be concealed by alternate destinations. No authorization
manager, durable claim or recovery runner was implemented.

## Remaining tasks and review

- Independent Claude review of `182f131`, `08fa6d9` and these additions. Additional
  OpenAI review, if requested, must be recorded separately.
- Private approval of actual control content, provenance, keys and diagnostic
  policy expectations; final generic rubric artifact. Synthetic keys are not approvals.
- Complete Freeze 1 dependency/runtime/test bindings and separately authorized
  freeze construction; exact audit-source ledger adoption verification/sealing.
- Production preparation, trusted authorization, validated publication and durable
  recovery/claim operations, with the accepted authorization granularity.
- Owner audit interface/sealing and explicit analysis-population acceptance.
- Complete Freeze 2 runtime/provider envelopes, prompts, actual request hashes,
  reviewer identities/settings, gates, cost/token bounds, terms/credit evidence,
  safeguards and independent recoverable backup evidence.
- Separately authorized live execution only after required independent review.

Scope receipt: five additions only; invented fixtures only; external contract,
unrelated work and historical/private artifacts preserved; no actual controls,
real bindings, real rankings/IDs, sampling, real packet, operational seal/freeze,
owner labeling, reviewer/router invocation, AWS/external API operation or push.
