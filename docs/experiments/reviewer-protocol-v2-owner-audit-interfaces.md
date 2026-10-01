# Reviewer Protocol v2: pure owner-audit interfaces

Owner authorization and authoritative inclusion policy: work-chat attachment
`a8870926-1314-4259-86c2-1a5f4a815b8a`, following acceptance of `de28891`.
Codex is the active writer. Independent Claude review remains deferred/unwaived.

Three additions only: `experiments/reviewer_protocol_v2/owner_audit.py`,
`tests/test_reviewer_v2_owner_audit.py`, and this record. All prior source,
external selection and control/trial contracts remain unchanged. No production
annotation, approval, operational sealing, claim/recovery manager or freeze is
implemented or performed. Actual rubric/control content remains unapproved.

## Completed annotation and binding contract

Private objects use the accepted exact-key canonical byte contract: strict UTF-8,
escaped Unicode, sorted keys, compact finite JSON and one terminating LF.
Duplicate keys, extra fields, wrong types and noncanonical input bytes fail.
Questions retain their original strings. H denotes 64 lowercase hex characters;
X denotes `x_` + H. Every listed key is required.

```text
OwnerAudit = {
  schema: "reviewer-protocol-v2-owner-audit-v1",
  packet_sha256: H,
  rubric_sha256: H,
  records: [{
    item_id: X,
    label: "qa" | "summarize" | "multi_intent" | "out_of_scope" | "unclear" | null,
    components: [] | ["qa","summarize"],
    certainty: "sure" | "unsure" | null,
    abstained: Boolean,
    context_concern: Boolean,
    note: strict-UTF-8 string
  }]
}
```

Exactly 24 external IDs occur once, in opaque-ID UTF-8 order, matching the
supplied canonical two-field external question packet. Caller-supplied expected
packet/rubric hashes must match both actual bytes and audit fields. The question
view permits only item_id/question; annotation records have no questions, source
metadata, controls, answer keys or reviewer votes. Production callers must first
establish the external packet using the accepted upstream selection replay; an
opaque ID's shape alone cannot establish class or selection authorization.

Abstention and concern are independent exact Booleans. For abstention, require
null label/certainty, empty components and a nonempty explanatory note. Concern
also requires a nonempty note, with either abstention or a label. For a labeled
record, require an accepted label, non-null sure/unsure certainty, and exactly
[qa,summarize] for multi_intent or empty components for other labels. Notes may
contain Unicode and line breaks and are not subject to model-rationale limits.

`validate_audit` validates completed audits only. An unfinished template is not a
completed artifact: missing labels/certainty/notes or a template schema fail.
There is no automatic label filling, note generation, repair or permissive mode.
`serialize_audit` canonicalizes a supplied value and validates before returning
bytes; it does not annotate questions or publish anything. Validators assess
structure/bindings, never correctness of owner interpretations.

## Supplied seal evidence: pure validation only

```text
OwnerAuditSeal = {
  schema: "reviewer-protocol-v2-owner-audit-seal-v1",
  freeze1_sha256: H,
  audit_sha256: H,
  packet_sha256: H,
  rubric_sha256: H,
  external_mapping_sha256: H,
  owner_attestation: {
    no_ai_assistance: true,
    no_reviewer_votes_seen: true
  },
  sealed_utc: "YYYY-MM-DDTHH:MM:SS.ffffffZ"
}
```

`validate_seal` checks all exact-byte hash bindings against supplied expected
hashes and bytes, validates the completed audit and accepted external packet/map
consistency, checks exact attestation keys and Boolean true values, and validates
both UTC spelling and calendar validity. Attestation is a supplied statement,
not independent proof. Expected Freeze 1 and mapping hashes must come from the
trusted calling interface; self-computed hashes do not constitute authorization.

This function does not create a seal, acquire an exclusive claim, verify an
operational owner action, enforce no-overwrite, authenticate approvals, recover
an interrupted operation or build a freeze. Synthetic seal JSON in tests is
invented evidence; passing validation establishes none of those operational acts.

## Authoritative primary inclusion policy

The owner replaced the earlier interface receipt's proposed concern treatment.
The prior receipt stays immutable historical evidence; this policy supersedes it.

| Measure | Inclusion | Owner metadata effect | Denominator |
|---|---|---|---|
| Reviewer pair agreement/Cohen kappa | Both reviewer votes valid, external items only | Neither abstention nor concern filters this population | Included n, coverage n/24 |
| Reviewer Fleiss kappa | All three reviewer votes valid, external items only | Neither abstention nor concern filters this population | Complete-panel n, coverage n/24 |
| Owner-versus-reviewer agreement/Cohen kappa | Reviewer valid; owner label valid; abstained=false; context_concern=false | Both reasons explicitly exclude from primary comparison | Included n, coverage n/24; matches/24 remains the approved planned alignment calculation |
| Context-qualified supplementary analysis | Not implemented | Concern is not a dependence determination, adjudication or automatic supplementary filter | Requires a separate approved population rule |

`analyze_owner` first requires a valid completed audit. Therefore an invalid owner
annotation stops analysis instead of becoming an imputed label. It accepts only
already-extracted local vote texts for planned external/reviewer pairs. Strict
accepted vote validation determines valid/invalid reviewer observations. Missing
means the pair is absent; a present invalid value, including None, is attempted
invalid, not missing. There is no service-envelope admission or vote repair.

The function reuses unchanged `analysis.analyze_external` agreement/kappa and
planned-denominator calculations with a separate comparison projection. Eligible
owner labels enter that projection; excluded annotations do not become kappa
labels/disagreements. Raw parsed records and input bytes are never changed.
The same primary-owner eligibility applies to the existing owner-majority
alignment calculation, retaining its planned denominator of 24.

Actual owner-label availability is reported from raw non-abstained records:
labeled concerns remain available labels, even though excluded from comparison.
Owner-abstention counts remain actual abstentions and are not inflated by concerns.
The legacy label-only analysis API remains unchanged for compatibility; production
completed-audit analysis must use the new metadata-aware wrapper.

The private returned population view has schema
`reviewer-protocol-v2-owner-comparison-populations-v1`, with:

- `primary`: reused descriptive results, preserving reviewer-only calculations,
  validity, coverage, yield and planned denominators; no new gate or correctness claim.
- `owner_counts`: abstentions, context concerns and their intersection.
- `reviewer_only`: ordered included-ID/coverage views for each pair and Fleiss.
- `owner_comparison`: per-reviewer included IDs/coverage, excluded IDs with every
  applicable reason, reason totals and disjoint exact-reason-combination counts.

Reason order is OWNER_ABSTAINED, OWNER_CONTEXT_CONCERN, REVIEWER_MISSING,
REVIEWER_INVALID. Missing and invalid are mutually exclusive; either can overlap
either owner reason. Totals may exceed the number excluded because overlaps are
retained. Exact combination counts account for each excluded item once. All views
retain opaque-ID order; reason-combination dictionary keys serialize canonically.

Empty owner populations have n=0, coverage 0/24 and undefined conditional
agreement/kappa, with the accepted no-shared-valid-labels reason. Planned
matches/24 remains zero, not a fabricated score on excluded labels. All primary
reviewer-only and planned external calculations remain unaffected by owner flags.

## Synthetic verification, commands and hashes

62 new synthetic cases plus all 354 existing v2 cases passed: **416 total**.
The first targeted pass contained 61 cases; the nondegenerate kappa exclusion
case was then added. Tests cover all four abstention/concern combinations,
five labels/two certainties, exact bindings and IDs, duplicate/missing/foreign/
control IDs, unfinished annotations, note requirements, type/canonical failures,
seal/rubric/packet/mapping/hash mismatches, UTC calendar/spelling, attestations,
empty populations, overlapping reasons, immutable raw data and unaffected
reviewer-only calculations. Fresh-process import tests block file opening,
read/write and network hooks, detect environment mutation/cloud imports, and
verify complete repository-local dependency coverage. No real data entered new APIs.

Two synthetic reproductions yielded identical bytes:

| Invented artifact | SHA-256 |
|---|---|
| Completed audit | 8e5da62b7e14ad50ac32eb392da1cc6402c7034ab528e5a9d43827d607fdff7d |
| Supplied seal evidence | c696f2a0042a2b6cd8137882afd1683668321f0520c6a56f7d4317363e398b47 |
| Population view | df695fbc64e58a08a2ab497ebaf073cec8db25ef460dc7773e645af5c2ea01cc |

Commands executed from `C:\Projects\AWS Project\main`:

```powershell
.\.venv\Scripts\python.exe -B -c 'from tests.offline_guard import install; install(); import runpy; runpy.run_module("ruff", run_name="__main__")' format experiments/reviewer_protocol_v2/owner_audit.py tests/test_reviewer_v2_owner_audit.py
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_owner_audit.py -q --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-owner-01'
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_owner_audit.py tests/test_reviewer_v2_controls.py tests/test_reviewer_v2_trial_interfaces.py tests/test_reviewer_v2_selection.py tests/test_reviewer_v2_packet_serialization.py tests/test_reviewer_v2_eligibility.py tests/test_reviewer_v2_exposure.py tests/test_reviewer_v2_regression.py tests/test_reviewer_v2_safety.py tests/test_reviewer_v2_validation_analysis.py -q --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-owner-02'
.\.venv\Scripts\python.exe -B -c 'from tests.offline_guard import install; install(); import runpy; runpy.run_module("ruff", run_name="__main__")' check experiments/reviewer_protocol_v2/owner_audit.py tests/test_reviewer_v2_owner_audit.py
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_owner_audit.py::test_deterministic_reproduction -q -s --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-owner-03'
.\.venv\Scripts\python.exe -B -c 'from tests.offline_guard import install; install(); import json; from experiments.reviewer_protocol_v2.integrity import verify_historical, verify_output_manifest; from experiments.reviewer_protocol_v2.selection import SOURCE_ROOT, selection_bundle; from experiments.reviewer_protocol_v2.trial_interfaces import interface_bundle, INTERFACE_BUNDLE_PATHS; from experiments.reviewer_protocol_v2.owner_audit import owner_bundle, OWNER_BUNDLE_PATHS; v=verify_historical(SOURCE_ROOT); print(json.dumps({"protected_files":v["protected_files"],"historical_bindings":v["frozen_bindings"],"pins_sha256":v["pins_sha256"],"audit_manifests":{n:verify_output_manifest(SOURCE_ROOT / "heldout-external/reviewer-protocol-v2-offline" / n) for n in ("final-1","final-2")},"selection_bundle":selection_bundle()["sha256"],"interface_bundle":interface_bundle({p:(SOURCE_ROOT/p).read_bytes() for p in INTERFACE_BUNDLE_PATHS})["sha256"],"owner_bundle":owner_bundle({p:(SOURCE_ROOT/p).read_bytes() for p in OWNER_BUNDLE_PATHS})},sort_keys=True,indent=2))'
git diff --check
```

Ruff passed. One existing asyncio_mode warning remains; suites are synchronous.
The guard intercepted three deliberate safety lookups in the combined suite,
none sent. Reproduction alone intercepted zero. No broader checks/install needed.

## Dependency coverage and preservation

New owner bundle digest:
`4d43a47492c543bf1a2d15e6f759515e0fe12aa109b0b262f97e085ccb3bb486`.
Its canonical path-to-source-hash mapping covers these twelve loaded dependencies:

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
main/experiments/reviewer_protocol_v2/analysis.py
main/experiments/reviewer_protocol_v2/owner_audit.py
```

The pure bundle helper hashes supplied source bytes; future production tooling
must establish that they match executing code and the approved runtime lock.
It does not perform filesystem authentication or confer approval.

Unchanged selection bundle:
`1cd9a742c8a3a10a82ca660c0edeaea3da90229dcaa06454432c17d47890fbf4`.
Unchanged control/trial interface bundle:
`3c6028eaa52f3d7b35bf92c67911d1e9a14b8776588808030bb6cfced227fc18`.
Historical audit implementation remains separately
`105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`.
No old outputs were regenerated to align implementation hashes.

Read-only checks verified 107 protected files, 72 historical bindings, unchanged
pin digest `ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae`,
and both original final-1/final-2 audit manifests and payloads, manifest digest
`057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4`.
Eight unrelated untracked documents and all private artifacts were preserved.

## Remaining tasks

Independent Claude review covers 182f131, 08fa6d9, de28891 and this addition;
additional OpenAI review must be recorded separately. Actual controls/keys and
rubric need private approval. Preparation, exact historical ledger adoption,
trusted operation authorization/publication/recovery, operational owner sealing
and Freeze builders remain unimplemented. Provider envelopes/settings, actual
request hashes, cost/token/terms/credit evidence, safeguards and recoverable
independent backup remain Freeze 2/live prerequisites. Supplementary adjudication
or context-qualified analysis requires a separate accepted specification/task.
No approval of this pure interface implies approval of those operations.

Scope receipt: three additions only, invented fixtures only; no actual owner
labeling, control approval, real bindings, ranking/IDs, sampling, real packet,
operational seal/freeze, reviewer/router invocation, AWS/external API call or push.
