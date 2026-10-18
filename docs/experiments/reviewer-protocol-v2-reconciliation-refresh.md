# Replacement reconciliation: reviewable-subject assembly receipt

2026-10-03; baseline `a587387036a656a185687e984b8c3cfd15c7aef5`, verified unchanged before assembly. Authorization: owner attachment `e83c7a5a-5165-4809-8403-8b00d7d452fb`; its raw hash/provenance is recorded in the private index. **Component assembly only: the new independent reconciliation review is absent. Full reconciliation verification and Freeze 1 compatibility/readiness are not established.**

## Source-dependency checkpoint

Read the accepted prerequisite audit, preflight receipt/refresh plan and ninth Claude report, `reviewer-protocol-v2-claude-reconciliation-preflight-review.md`, especially its digest impact and sequencing advice. Inspected current call sites and entry points. The concrete in-bundle preflight integration identified in the audit is implemented and independently accepted; no further required edit to a named member of the current seventeen-source closure, or a new import from that closure, is already planned. The optional tests/catch-all are not implemented.

Missing freeze designation, trusted approval/phase/seal producers and operational callers remain required at their respective boundaries. Their implementation contracts/paths/dependencies have not been settled; this task neither chooses them nor routes them outside review coverage. Freeze designation work must be settled before its use and final procedure assembly. The current evidence refresh is **version scoped**, not final Freeze 1 assembly or a code freeze. Any later change to these seventeen bytes or their executable closure requires another reviewed version and affected evidence refresh; separately implemented operational code needs its entire closure, runtime/procedure/tests and independent review bound, regardless of location.

## Exclusive-created private outputs

Root, outside Git:
`C:/Projects/AWS Project/heldout-external/reviewer-v2-reconciliation-refresh/2026-10-03-a587387/`.

Exactly 21 files: the following four and seventeen unchanged-byte current source captures under source-evidence/main/experiments/. No historical copy, actual review, final reconciliation or applicability wrapper is replaced or created.

| File | Exact raw-byte SHA-256 |
| --- | --- |
| current-verification-bundle.json | a5f30c12bb4c9e5761cacbcfb0614380633a90572886f17333159797bb426580 |
| historical-ledger-reconciliation-subject.json | 5ecea37ee945023f77266f6cc9d15ad5e8c7db6d3442c24f69a2112892e0cf78 |
| refresh-index.json (metadata only) | 7d6a4dad17a3ea966fb1238247c271bc7243d9a11200a3fe1a4b4331d6f3c46a |
| preservation-before.json (301-file metadata snapshot) | 3211c29e9e8e35de5e76734e7005aa3526e7827570fc41d3c8a95277e448997f |

Current seventeen-source digest:
`e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e`.
This is distinct from the complete descriptor's raw hash above.

The subject uses the existing `reviewer-protocol-v2-historical-ledger-reconciliation-subject-v1` schema and has no independent_review field. Its raw hash equals the defined review-subject hash above. Recipe: SHA256(common.canonical({all subject fields except independent_review, schema replaced with the subject-v1 token})). Canonical serialization remains sorted compact ASCII JSON, finite values and final LF. The descriptor remains the existing exact files/sha256 object; its digest is SHA256(common.canonical(path-to-raw-file-SHA256 map)). No protocol schema, role or authorization changes.

## Exact old/new differences and unchanged subjects

Old subject raw/review-subject hash:
`20252b1f3c161feaf2103597a8b28b0c899b1871f8545048cc9ac7018b01cf7f`.
Exactly one top-level field differs: current_verification_bundle. Within it:

| Nested field | Old | New | Reason |
| --- | --- | --- | --- |
| files.main/experiments/reviewer_protocol_v2/production_preparation.py | 07ec3553fce57fde420aff0b146c02a1ebd8e6f5fa89a55782a4cb1ea0e15ee8 | 6431ec0570a264477f5f63e87201c271435a957c4cd4c4a491844493242b42d3 | Accepted additive preflight |
| sha256 | ece125e0466cd89b280221bb89b9d38389fe060c7fb19a4a35d506ff41828a28 | e2646384cb06948625b4a985e07c10428af98ff2e24a5e27f8a1af938ddb265e | Same seventeen-source hash recipe |

All other sixteen source hashes, file membership, schema, historical manifest/ledger/generating-wrapper/source, current eligibility source, lemma and counts FileBindings are exactly preserved. The source copies are evidence captures only, never imported; descriptor keys continue binding the executing original paths. The index records each original/copy/Git-baseline relationship. No scope or premise is altered by this source delta.

Fixed subjects verified against actual raw bytes:

| Subject | SHA-256 |
| --- | --- |
| Original manifest | 057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4 |
| Unchanged ledger | 6b3f97d8e987b9c01d091bce8f06b3c2e691ca5e9b4b2fc567e2919d2e07b7d2 |
| Historical generating wrapper | 2476cb7cb563c936172f55ba7e69f52476bb003a912fcca06cedcd4e6aabd6ae |
| Sixteen-source generating digest | 105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc |
| Historical eligibility source | d3030b229c498db254ba936352d40262a24ad2df5a114fa2c0432d69f8811e37 |
| Current eligibility source | 04e36326c5445419a5e9ec0e6517c4d9623c52f6688c27b095005da597c3cc92 |
| Pinned normative document | 4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7 |
| Lemma | febaf27765974a35798e27652af90267978a4af6294821f718b3701d97c9f7ef |
| Counts receipt | 584d43ad6a02f7cdffa345a1fd92da04f9eef0ec72bc2b82dafed89ba82c417b |
| Reconciliation contract, canonical digest | fd1dfc6109428f6dc5651ee28996358f69514842b4a19efd18f2410292d8860e |

The original manifest/payload hashes, recorded historical runtime (CPython 3.13.12; Unicode 15.1.0), exact sixteen historical source/Git bindings and recovered filename-hash recipe agree. No historical code was executed, no unrecorded runtime fields inferred, and no full historical input closure replay performed.

All three RuleSpecification v2 subjects and actual ReviewEvidence v4 records remain reusable: their raw source records, mechanical contracts, normative document, decision evidence, distinct source/algorithm evidence and shared-origin section joins remain unchanged and component-checked. Exposure/grouping RuleApplicability v3 records retain their exact raw hashes, unchanged historical/current sources, semantic review joins and null reconciliation. The index records their precise FileBindings. Eligibility applicability remains accepted at the old final reconciliation; it awaits a replacement. Old reconciliation acceptance does not transfer to the new subject.

## Checks and reproducible preservation

The existing environment and offline guard were used for in-memory assembly/check commands; no installed helper or operational tool was added. Writes used Path.mkdir(exist_ok=False) for the new directory and binary open('xb') for each output; safe resolved paths and captured-byte hash equality were checked before/after creation. Existing validators used include object_bytes/object_header, read_binding/bound_path/checked hash joins, generating_bundle's AST recipe check, specification/evidence_header/source_record/utc, dependency_modules, _executing_sources, verification_bundle and review_subject. All component checks passed.

The three original indexes were read and verified at their accepted hashes: assembly `16cc736f6dea8672c920777f8365b4c4562d47abdfd61a9858e749d307ac1f3d`, review `2885f29a04437288376af9fe902a3adcd9285788bea00137c164cba463ac5dc5`, completion `8365f02f6bf9373d0a125279f5213fbcf5c98c04c14abe144c6dec646bf451bd`. Their referenced artifact hashes and 102 captured bindings were checked. Current source buffers equal baseline committed blobs and existing module origins/disk; the seventeen new captures equal those same buffers. The existing static checker accepts the unchanged twelve-module stdlib closure. This is reviewed-source checking, not a Python sandbox or execution attestation.

Counts receipt schema, raw hash and recorded manifest/ledger/count-procedure/counts joins were checked. **No counts replay was needed or run**: the current eligibility transition, lemma and ledger bytes are unchanged, and the existing actual review retains the counts validation at its original bindings. The ledger was only read for hashing, never parsed into questions or screened.

A separate read-only filesystem check verified all twenty-one output files, canonical descriptor/subject/index/snapshot bytes, source captures, subject preimage and all **301 protected files unchanged**. The durable snapshot covers original assembly/review/completion directories, historical artifacts, originals/recovered records, all nine Claude reports, proposed draft, current sources/tests/docs and pre-existing unrelated files. Its membership and hashes are stored outside Git, making this task's preservation claim reproducible; it does not retroactively supply the previous task's unavailable in-memory snapshot. No private content is placed in Git or output logs. Only metadata, safe paths and hashes are recorded.

Exact read-only reproduction command, from main:

```powershell
@'
from tests.offline_guard import install, blocked_requests
install()
from pathlib import Path
from experiments.reviewer_protocol_v2 import production_preparation as p, selection as s, ledger_adoption as a, ledger_reconciliation as r
from experiments.reviewer_protocol_v2.common import sha_bytes, require, canonical
from experiments.reviewer_protocol_v2.control_serialization import object_bytes
import json, subprocess
root=Path('..').resolve()
folder='heldout-external/reviewer-v2-reconciliation-refresh/2026-10-03-a587387'
index_raw=(root/folder/'refresh-index.json').read_bytes()
require(sha_bytes(index_raw)=='7d6a4dad17a3ea966fb1238247c271bc7243d9a11200a3fe1a4b4331d6f3c46a','REFRESH_INDEX_HASH')
index=object_bytes(index_raw)
snapshot=object_bytes(a.read_binding(root,index['preservation_snapshot']))
require(len(snapshot['files'])==301,'REFRESH_PROTECTION_COUNT')
for path,digest in snapshot['files'].items():
    checked=(root/path).resolve()
    require(checked.is_relative_to(root) and sha_bytes(checked.read_bytes())==digest,'REFRESH_PROTECTED_BYTES')
descriptor=object_bytes(a.read_binding(root,index['replacement_descriptor']))
subject_raw=a.read_binding(root,index['replacement_subject'])
subject=object_bytes(subject_raw)
require(sha_bytes(subject_raw)==r.review_subject(subject)==index['review_subject_sha256']=='5ecea37ee945023f77266f6cc9d15ad5e8c7db6d3442c24f69a2112892e0cf78','REFRESH_SUBJECT')
sources={name:a.read_binding(root,item['captured_copy']) for name,item in index['source_evidence'].items()}
require(p._executing_sources(root,sources)==descriptor==subject['current_verification_bundle'],'REFRESH_SOURCE_DESCRIPTOR')
require(all(raw==subprocess.check_output(['git','show',index['baseline_head']+':'+name.removeprefix('main/')],stderr=subprocess.PIPE) for name,raw in sources.items()),'REFRESH_GIT_BYTES')
old=object_bytes(a.read_binding(root,index['prior_subject']))
require([key for key in old if old[key]!=subject[key]]==['current_verification_bundle'],'REFRESH_SUBJECT_DELTA')
require(len(list((root/folder).rglob('*.*')))==21 and not blocked_requests,'REFRESH_INVENTORY_OR_NETWORK')
print(json.dumps(dict(component_result='REVIEWABLE_SUBJECT_COMPONENT_CHECKS_ONLY',protected_files=301,source_copies=17,review_pending=True,full_reconciliation_verified=False,offline_intercepted=0)))
'@ | .\.venv\Scripts\python.exe -B -
```

Outcome: REVIEWABLE_SUBJECT_COMPONENT_CHECKS_ONLY; 301 protected files and 17 copies verified; review_pending=true; full_reconciliation_verified=false; offline_intercepted=0. Assembly and check exited 0; guard intercepted zero attempts, no outbound calls. No full suite, old completion-chain replay, verify_reconciliation/rule_bindings, _history/_freeze/verify_adoption, preparation or selection entry point was invoked. Those operational/full-chain routes and counts/classification functions were blocked in the task-local assembly invocation. No production validator or pin was patched into success.

## Missing joins, later updates and scope receipt

Next: independently review this exact replacement subject and, only if accepted, issue actual raw and typed ReconciliationReview v1 bound to its subject/contract/lemma/counts hashes. No new reviewer statement, timestamp, acceptance or placeholder hash exists. The index lists pending joins without claiming success.

Later, separately authorized updates are: replacement final reconciliation (new actual independent_review FB); eligibility applicability (replacement final reconciliation FB); completion index/technical-check receipt; current interface/source/test/procedure bindings and applicable runtime evidence. Unchanged semantic subjects/reviews and exposure/grouping applicability may be reused only while their actual bindings remain valid. Future full path validation, exact owner-release approvals and trusted producers/callers remain separate prerequisites.

Ledger fidelity remains a premise; byte/hash agreement establishes neither past execution nor approval/reviewer authenticity or semantic correctness. R4's inspected non-normative limitation, S-576 complete:false extraction boundary and the 37-check limitation are preserved. Accepted phase order is unchanged: Freeze 1 -> production-ledger verification/sealing -> authorized external selection -> owner audit -> Freeze 2 -> separately authorized live execution.

Repository inventory is exactly this new receipt and reviewer-protocol-v2-reconciliation-refresh-claude-handoff.md. They alone are staged by explicit path for one authorized local commit. Private outputs, all nine reports and unrelated files are excluded; no push.

Scope receipt: reviewable evidence assembly and component/hash/preservation checks only. No implementation/normative edit, fabricated review/approval, replacement final wrapper/applicability, actual InputBinding/preparation package/FreezeManifest, screening/classification/counts replay, adoption/sealing, ranking/selection/sampling, packets/freezes, owner labels, operational producers, Claude/model/router invocation, AWS/external API operations or installs. **No ledger adoption occurred. Freeze 1 readiness remains unestablished.**
