# Reconciliation preflight: contract and implementation receipt

Baseline `ab85ba46ba0b5b6d37b50b3c9d9fae42a5c3d264`; owner authorization attachment `c396e06d-b5a7-46f9-8ec0-a421c3763aa0`. Synthetic implementation only. The following contract was documented after interface inspection and before source edits.

## Narrow API contract

`reconciliation_preflight(root, binding_raw, report_raw, authorization_raw, verification_context, *, phase, trusted_expectations=None)` returns an ephemeral technical dictionary. It creates no serialized protocol artifact, approval, seal or operational capability. Existing InputBinding/PreparationReport/authorization-v2/FreezeManifest roles and bytes remain unchanged.

Raw inputs are canonical accepted InputBinding v1, PreparationReport v1 and selection-authorization-v2 bytes. `verification_context` has exactly the existing required `prepare` arguments: root, artifacts, code_bindings, generating_sources, historical_manifest, expected_historical_manifest_sha256, executing_sources, proposed_freeze1 and trusted_expected_freeze1_sha256. No success flags or callbacks are admitted. The context must use the same root, artifact/code bindings, trusted Freeze hash and actual complete proposed Freeze bytes. The historical manifest expectation is already a separate required context input.

`trusted_expectations` is a separate keyword-only caller input, not read from an artifact. Its exact keys are inputs_sha256, report_sha256, freeze1_sha256, procedure_sha256, authorization_sha256, ledger_seal_sha256 and sealed_ledger. The six hashes are lowercase Hex256; sealed_ledger is an existing exact FileBinding. All fields are mandatory. Missing input and extra fields, including a supposed trusted Boolean, fail. Matching caller values validate consistency only: this API cannot distinguish an honest trusted caller from a malicious one or establish external trust.

`phase` must be FREEZE_1_LEDGER_SEALED, supplied by the future externally verified phase producer. The externally established seal association consists of (ledger_seal_sha256, sealed_ledger, inputs_sha256, freeze1_sha256, procedure_sha256); these expected values must join to the verified InputBinding ledger, proposed Freeze and its historical_integrity_manifest procedure FB, and the accepted authorization-v2 fields. This API uses that existing procedure role's raw hash for procedure_sha256, not the reconciliation counts-procedure hash. No authorization format is changed.

Verification order:

1. Require exact context/trusted input shapes and valid expected hashes; reject missing trust input or invalid phase before further work.
2. Hash/check canonical raw InputBinding, report, authorization and proposed Freeze against the separate expectations. Check context, artifact/code, procedure role and sealed-ledger relationships. Require report PREPARED, empty findings and exact input/Freeze joins; an isolated PREPARED report is insufficient.
3. Call existing verify_adoption with complete supplied proposed Freeze, sources and input bytes. Require verified historical provenance, proposed compatibility and BINDINGS_VERIFIED_NOT_ADOPTED. Its existing _history/_freeze/rule_bindings/verify_reconciliation chain validates the actual captured evidence and current bundle; propagate only its sanitized local failure code. Never adopt or seal.
4. Call existing validate_preparation with the complete context and separate input/Freeze hashes, requiring its actual replay and byte equality. Do not accept a caller-supplied assessment or verification-level flag.
5. Require the existing selection_phase_predicate on that regenerated assessment and authorization-v2 using the expected procedure/seal bindings. Return technical success only; invoke no selection or operational hook.

Result fields: status (TECHNICAL_PREFLIGHT_VERIFIED_NOT_AUTHORIZED or FAILED), code (None or sanitized local rejection), hashes (empty on failure; success includes input/report/Freeze/procedure/authorization/seal/ledger/current-bundle hashes), approval_authenticated=false, phase_history_authenticated=false, ledger_sealing_authenticated=false, operational_adoption_performed=false, operational_dispatch_performed=false, freeze1_readiness=NOT_ASSESSED. No question text, IDs, annotations, source text or arbitrary exception detail is returned. Unexpected malformed/IO exceptions use a fixed stage-specific code.

## Expressiveness and trust limits

The accepted authorization-v2 contains only an opaque ledger_seal_sha256. No accepted operational LedgerSeal schema, authoritative seal-to-ledger mapping, phase-history producer, trusted approval producer, claim/publication/recovery/freeze manager or real enforced caller exists. The separate API expectations above express the necessary technical association without inventing a serialized seal or amending authorization. They do not verify seal-record bytes or establish that sealing actually occurred. A future reviewed seal encoding/producer must establish that association externally before operational use; a self-declared hash or Boolean cannot do so. This is an explicit remaining gap, not a waived check or operational authorization.

Accepted order remains Freeze 1 -> production-ledger verification/sealing -> authorized external selection -> owner audit -> Freeze 2 -> separately authorized live execution. select() continues rejecting, the CLI remains audit/verify only, and select_bound_inputs is unchanged. No operational dispatch is added.

## Validation and digest receipt

Implementation adds one function to production_preparation.py and 39 synthetic cases to the existing remediation test file. The scoped inventory is exactly:

- experiments/reviewer_protocol_v2/production_preparation.py
- tests/test_reviewer_v2_review_remediation.py
- docs/experiments/reviewer-protocol-v2-reconciliation-preflight.md
- docs/experiments/reviewer-protocol-v2-reconciliation-preflight-claude-handoff.md

No other executable dependency is added. The current closure remains seventeen sources. AST-derived dependencies remain ast, collections, datetime, hashlib, itertools, json, math, pathlib, platform, re, sys and unicodedata. This observation does not provide a broader production dependency lock.

Commands below ran from main using the existing environment. Ruff was first applied with the same guarded command and `format` rather than `format --check`; only added source/test lines changed.

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_review_remediation.py -k preflight -q -s --basetemp=.pytest_cache/reviewer-v2-preflight-focused-01
$preflightTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' })
& .\.venv\Scripts\python.exe -B -m pytest @preflightTests -k 'not test_accepted_population_regression' -q --basetemp=.pytest_cache/reviewer-v2-preflight-regressions-01
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff', run_name='__main__')" check experiments/reviewer_protocol_v2/production_preparation.py tests/test_reviewer_v2_review_remediation.py
.\.venv\Scripts\python.exe -B -c "from tests.offline_guard import install; install(); import runpy; runpy.run_module('ruff', run_name='__main__')" format --check experiments/reviewer_protocol_v2/production_preparation.py tests/test_reviewer_v2_review_remediation.py
git diff --check
```

Focused results: **39 passed, 86 deselected**, 25.40 seconds; zero intercepted network attempts. Permitted v2 results: **718 passed, one deselected**, 76.79 seconds. Existing guard intercepted four intentional offline-guard probes; none were sent. Existing asyncio_mode configuration warning remains; nothing was installed. Ruff check/format and diff whitespace checks passed. Relevant existing byte/hash goldens, import-purity, dependency-closure and disabled-selection checks passed within that suite. The real-population regression was excluded; no historical closure/count replay ran.

The baseline constructs an invented complete workspace through the existing synthetic reconciliation fixture, then calls the real prepare/adoption/reconciliation/preparation replay chain. Existing reviewed test-local normative-identity and reconciliation TARGET fixture substitutions remain confined to invented workspaces; no production pin override or validator replacement is introduced. Exact rejection codes cover missing reconciliation, ledger-subject mismatch, stale bundle/review, tampered supplied source bytes, malformed evidence/context, stale expected hashes, absent separate trust, invalid phase, and input/report/procedure/Freeze/seal/authorization joins. Forbidden selection/ranking/ID/packet/classification hooks raise if reached. File snapshots plus forbidden Path write methods check no writes during both success and failure calls. Import purity uses the existing guarded subprocess test. These are scoped checks on reviewed code, not a universal dynamic-code or hostile-process guarantee; no publication or seal manager exists to call.

Two identical successful calls give canonical synthetic result SHA-256 `dec28dfe8a7985aa340ec95ab93626bde5c241ac39b68a3085b91b92cae36002`. This is an invented test result, not actual preparation, sealing or authorization evidence.

### Hash impact

The bundle recipe remains SHA256 of the canonical path-to-raw-file-SHA256 map: sorted keys, compact separators, ASCII JSON, finite values and one final LF. No descriptor is written by the measurement.

| Binding | SHA-256 | Change |
| --- | --- | --- |
| Current verification, seventeen sources | e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e | Replacement measurement |
| Prior accepted verification | ece125e0466cd89b280221bb89b9d38389fe060c7fb19a4a35d506ff41828a28 | Old evidence retained |
| Selection, seven sources | 0797dd5065486ecb142bed90fe7d1a74f8792e80659c1b64c9f495d71eba1187 | Measured unchanged |
| Control/trial, ten sources | 2e4c224927c9450608afb414c4ad1f8c09932c8b8cc5be9cdc9de0eadd1fc0bf | Measured unchanged |
| Owner/analysis, twelve sources | 492d688bd937cbc68e4ccc86c0c11a4be1dfcef77423133a3c826728d8a5a2b4 | Measured unchanged |
| Eligibility mechanical contract | 91d73119ae0f3474c350def0ef87a5850ab98e7d8489c44e09ba436f65614fa4 | Measured unchanged |
| Exposure mechanical contract | b0ca037ec36dd84f214286c281dfc162cfd2fbb593ea86833579a8b1671c507c | Measured unchanged |
| Grouping/similarity mechanical contract | 181913badd890b7050ef2d4d23e1ea61c712569130eaaf2f7223c5b8eee8a795 | Measured unchanged |

Validated raw source hash: `6431ec0570a264477f5f63e87201c271435a957c4cd4c4a491844493242b42d3`; validated raw test hash: `872e4e1792b6557bb6645833bf77985f122ec7e31865a21e75a56537c6747e73`. These exact bytes must match the staged/committed blobs; documentation-only completion does not require repeating the suite.

Exact read-only digest/dependency command:

```powershell
@'
from tests.offline_guard import install
install()
from experiments.reviewer_protocol_v2 import production_preparation as p, selection as s, trial_interfaces as t, owner_audit as o, ledger_adoption as a, procedure_evidence as e
from experiments.reviewer_protocol_v2.common import canonical, sha_bytes
import json
sources = {name: (s.SOURCE_ROOT / name).read_bytes() for name in p.VERIFICATION_BUNDLE_PATHS}
def digest(paths):
    return sha_bytes(canonical({name: sha_bytes(sources[name]) for name in paths}))
print(json.dumps(dict(verification=digest(p.VERIFICATION_BUNDLE_PATHS), selection=digest(s.BUNDLE_PATHS), control=digest(t.INTERFACE_BUNDLE_PATHS), owner=digest(o.OWNER_BUNDLE_PATHS), contracts={role: sha_bytes(canonical(e.rule_contract(role))) for role in sorted(a.RULE_ROLES)}, dependencies=a.dependency_modules(sources), changed_files={name:sha_bytes((s.SOURCE_ROOT / name).read_bytes()) for name in ['main/experiments/reviewer_protocol_v2/production_preparation.py','main/tests/test_reviewer_v2_review_remediation.py']}), sort_keys=True))
'@ | .\.venv\Scripts\python.exe -B -
```

## Dependency-refresh plan and remaining prerequisites

The following are future separately authorized actions; **none is performed here**.

1. Obtain independent code-delta review of the four scoped files, full synthetic replay, sanitized failures, no dispatch, separate expected inputs and expressiveness/trust gap. Preserve all eight existing Claude reports. This handoff is prepared locally only.
2. Create a replacement current verification descriptor for the measured seventeen-source digest. Preserve the old descriptor and its acceptance. Create a new reconciliation subject binding that descriptor; obtain a new actual independent raw/typed review bound to that exact subject, then create a replacement final reconciliation wrapper. Existing subject `20252b1f3c161feaf2103597a8b28b0c899b1871f8545048cc9ac7018b01cf7f` and final wrapper `5f5183865ca85eb5837de4634e77a5a13a355c0e39bc433b8ded827162763eb9` stay accepted at their old bindings; acceptance does not transfer to the replacement.
3. Update eligibility applicability's reconciliation FileBinding, then the dependent completion index and technical-check receipt. Reuse exposure/grouping applicability and all three normative RuleSpecifications/semantic reviews only while their actual document/contract/source/policy/subject bindings remain unchanged. No rule or semantic-subject amendment is proposed.
4. Refresh the current verification reference in the interface-binding descriptor, the source/test manifest (including changed test bytes), and future historical-adoption procedure/current implementation bindings. Recheck intended runtime and AST/dependency evidence against the final closure; unchanged twelve-module observation does not waive before-Freeze-1 runtime/SDK/dependency/platform requirements. Separately trusted procedure/input/report/Freeze hashes and final owner-release subjects must bind the completed replacement artifacts.
5. Complete remaining actual evidence/content/rubric/runtime decisions and final subject-bound owner approvals in the accepted phase order. No code acceptance, task grant or technical pass substitutes for them. No real InputBinding, FreezeManifest or preparation package is assembled here.
6. Before operational use, provide reviewed trusted authorization/phase producers and a precise externally established seal-to-ledger association. The missing accepted operational seal record/producer is an explicit blocker. Implement and review every real adoption/sealing, selection/publication/recovery caller's enforcement separately; no alternative ungated route is authorized. Freeze 1 readiness remains unestablished.

The original sixteen-source generating digest `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`, historical inputs, lemma/counts receipt, actual owner records, private originals, subjects/reviews/wrappers and proposed draft are preserved. No historical execution is re-established by current byte consistency. Accepted R4 inspected limitation, S-576 complete:false extraction boundary, the 37-check limitation and ledger fidelity as a premise remain unchanged; this task does not broaden them into new blockers.

Preservation checks compare the pre-edit snapshot of 171 out-of-scope source/test/document/private-evidence files (excluding the one authorized test edit), the seventeen pre-existing untracked files, and validated scoped bytes. Staging is restricted to the four explicit paths above; all eight Claude reports and private artifacts remain excluded.

Scope receipt: synthetic technical preflight and tests/documentation only; one scoped local commit, no push. No actual evidence refresh, preparation/InputBinding/FreezeManifest assembly, historical replay, screening/classification, ranking/selection/sampling, IDs/packets, adoption/sealing/freezes, owner labels, operational producers/managers, Claude/model/router invocation, AWS/external API operations or installs. Technical success does not authenticate approval, phase history or sealing. **No ledger adoption occurred; Freeze 1 readiness remains unestablished.**
