# Actual evidence assembly for independent review

2026-10-03. Baseline: `25bde9388d41bd476984aecad6c66ac6e48b2c92`.
Authorization: owner attachment `dce7fefa-54ac-442b-b21c-dcac08c23215`, unchanged
raw copy SHA-256 `9e6f9244f0eff4a5229b1c84fb672fcd661abf341e9a073828b92f46bed6328b`.
Assembly only; this receipt declares no approval, adoption, compatibility or readiness.

## Private inventory and reviewable subjects

An exclusive-created directory contains the actual subjects, outside Git:
`C:/Projects/AWS Project/heldout-external/reviewer-v2-evidence-assembly/2026-10-03-25bde93/`.
Paths in this section are relative to that directory. The complete private index
records all 52 artifacts, schema versions, sizes, exact hashes, provenance,
transcription recipes, section sets and missing joins. Its own hash is recorded
here, outside its own inventory; helper and preservation bindings are in the index.

| File / subject | Exact raw-byte SHA-256 |
|---|---|
| assembly-index.json | 16cc736f6dea8672c920777f8365b4c4562d47abdfd61a9858e749d307ac1f3d |
| rules/eligibility_specification/rule-specification.json | d64cca70fff13c34459f66e643557179470edaf6fbf6523e08f7306c84daf8b1 |
| rules/exposure_specification/rule-specification.json | 365221ba6b4c995a7fdbb185071e7bb4a49aa52519467bd944760bdfe3bdff79 |
| rules/grouping_similarity_specification/rule-specification.json | cc1c9a4daceda978374afcd864f6d4e25f46d291b53517783b687a3265eb8dbe |
| historical-ledger-reconciliation-subject.json | 20252b1f3c161feaf2103597a8b28b0c899b1871f8545048cc9ac7018b01cf7f |
| current-owner-decisions.json | 7b26cba71d744e2747cfb82f2a200822eb7406624f9f17e7d7a1bfd086349844 |
| historical-generating-bundle.json | 2476cb7cb563c936172f55ba7e69f52476bb003a912fcca06cedcd4e6aabd6ae |
| current-verification-bundle.json | 94c45d6a68424018e0c15c3e101da0860521c6af58ec73650cbc2edfeff68199 |

The 52 artifacts comprise 22 RuleTextEvidence v3, three RuleAlgorithmEvidence v2,
three complete-schema RuleSpecification v2 subjects, one CurrentOwnerDecisions v1,
three explicitly incomplete applicability drafts, one defined reconciliation
review subject, sixteen historical Git blobs, one HistoricalGeneratingBundle v1,
one current verification descriptor and one unchanged authorization-record copy.
Complete schema does not mean independent review or owner approval.

## Sources, byte contract and fixed bindings

RuleText and RuleAlgorithm text comes exclusively from captured source/owner
records and the pinned normative document, with exact line-range transcription.
The existing accepted mechanical contract is serialized as a consistency target
inside RuleSpecification; code constants/fixtures are not source or algorithm
authority. The original proposed sections remain unchanged and are explicitly
superseded where current owner decisions resolve discrepancies.

The current decision record transcribes O-b6e lines 10, 12 and 14: E01 metadata-only,
separate historical/current evidence and the nine-field runtime binding. Its actual
raw-record hash was separately checked. It authenticates no approval, supplies no
historical runtime facts and makes no historical amendment. D1-D8 are preserved as
separate source excerpts and joined through the current normative document/metadata.

All new JSON records use unchanged `common.canonical`: UTF-8, sorted keys,
ensure_ascii=True, compact separators, finite values and exactly one final LF.
SHA-256 hashes the complete bytes. Text transcription strictly decodes UTF-8,
uses `splitlines(keepends=True)`, and concatenates stated inclusive ranges in listed
order without inserting separators. Individual fragment hashes and text hashes
are in the index. Source-record identity remains distinct from section locators.

For S-576, `record_path` points to the original raw JSONL record (including its LF),
SHA-256 `7e481873256e5e1e3684d19fc36199baf093202cf23404338b90bcbf625b4a3f`.
The cited one-based ranges, including E05 lines 283-329, refer to the derived
`specification-response-extracted.txt`, SHA-256
`539541e3a3f28885a4be3c1e3d27171ca45bb6a30980cdad3b818933c7e49373`.
Its recorded recipe, replayed exactly, is **UTF8 of JSON content text fields joined
by LF; no added final LF**. Locators explicitly give both hashes and this distinction.
The retained `complete:false` flag remains; its meaning is unestablished. The
100 registered / 37 supplementary checks distinction and limits on historical
registration/execution evidence remain. Neither is silently repaired.

Source and algorithm wrappers have different accepted schemas. They explicitly
share the normative document as their one common original; `shared_origins` and
the exact sorted source/algorithm section sets are preserved. No copied source is
represented as independent provenance. Whether it supports both roles is a required
independent semantic-review decision, not an assembly declaration.

Verified fixed subjects:

| Binding | SHA-256 |
|---|---|
| Normative document | 4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7 |
| Eligibility mechanical contract | 91d73119ae0f3474c350def0ef87a5850ab98e7d8489c44e09ba436f65614fa4 |
| Exposure mechanical contract | b0ca037ec36dd84f214286c281dfc162cfd2fbb593ea86833579a8b1671c507c |
| Grouping/similarity mechanical contract | 181913badd890b7050ef2d4d23e1ea61c712569130eaaf2f7223c5b8eee8a795 |
| Current verification digest (17) | ece125e0466cd89b280221bb89b9d38389fe060c7fb19a4a35d506ff41828a28 |
| Lemma | febaf27765974a35798e27652af90267978a4af6294821f718b3701d97c9f7ef |
| Existing counts receipt | 584d43ad6a02f7cdffa345a1fd92da04f9eef0ec72bc2b82dafed89ba82c417b |
| Original final-1 manifest | 057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4 |
| Original ledger | 6b3f97d8e987b9c01d091bce8f06b3c2e691ca5e9b4b2fc567e2919d2e07b7d2 |
| Original generating digest (16) | 105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc |

Historical sources were extracted byte-for-byte using Python
`subprocess.check_output(['git','show', COMMIT + ':' + PATH])`, then exclusive binary
writes. Each original Git blob identity/path is indexed. The full historical commit
is `182f13192809676a9a5d4fa27579df3d58211ce3`. AST inspection verifies the recovered
filename-to-raw-file-hash recipe; no historical module is imported or executed.
The implementation digest hashes the existing canonical filename/hash map with LF.
Current paths/hash maps remain separate, and match baseline Git bytes.

Historical runtime is only CPython 3.13.12 / Unicode 15.1.0 from the unchanged
manifest. No historical SDK/platform fact or proposed runtime/dependency lock was
invented. Original input-closure metadata is recoverable as 107 pins plus four
additional inputs (111); only the two original rule-design references were byte
checked for these drafts. Full historical input closure and current runtime/lock
verification were not performed. No actual InputBinding/preparation package exists.

## Checks completed and deliberately incomplete records

Sixteen component-check categories passed, followed by filesystem replay:

- Actual fixed raw bytes, safe resolved bindings and canonical new record bytes.
- All fourteen preserved copies equal their originals; exact S-576 extraction replay.
- Exact source excerpts, section relationships and three shared-origin sets.
- Existing `text_evidence`, `specification` and `current_decision` validators; the
  actual decision raw record was additionally verified with `source_record`.
- Sixteen historical source hashes/recipe and existing `_generating` component
  validation; manifest runtime and all four unchanged payload hashes.
- All seventeen current source files equal baseline Git bytes and reproduce the
  accepted current verification digest. No executing-history attestation is claimed.
- Existing counts-only `counts_receipt` replay equals the preserved receipt and
  required 104/0/0/0/0 counts. No classifier/normalizer or candidate output.
- Reconciliation subject uses the exact `review_subject` recipe: remove
  `independent_review`, replace schema with historical-ledger-reconciliation-subject-v1,
  then hash canonical bytes. The stored subject is those exact preimage bytes.
- All 61 protected files unchanged; zero forbidden operational hook attempts.

The existing offline guard was installed. No full tests were rerun for data assembly.
No implementation/schema/contract change or technical incompatibility was found in
the complete components. Existing static checks remain reviewed source checks, not
a Python sandbox; the reviewed R4 limitation is retained, not inferred from hashes.

Missing links are explicit in the index:

1. Three **ReviewEvidence v4** records and their actual raw review records. Each must
   join the exact RuleSpecification byte hash, role contract, pinned document FB
   and shared-origin section sets. Reviewer statements and UTC values are absent.
2. One **ReconciliationReview v1**, with actual raw record, joining subject
   `20252b1f...`, contract `fd1dfc6109428f6dc5651ee28996358f69514842b4a19efd18f2410292d8860e`,
   and the exact lemma/counts hashes above. Existing reports cannot fill this role.
3. Consequently, all three final **RuleApplicability v3** wrappers and the final
   **HistoricalLedgerReconciliation v1** wrapper remain unassembled. Drafts use a
   conspicuously different schema and omit missing review-dependent fields; no
   placeholder hashes, invented approvals or fake final records were supplied.

`rule_bindings` / full `verify_reconciliation` chains require those reviews and
were not invoked. No `_history`, `_freeze`, `verify_adoption` or preparation API,
dummy FreezeManifest, readiness/compatibility claim or operational manager was used.

## Exact validation commands

From `C:/Projects/AWS Project/main`, existing environment. Primary assembly command:

```powershell
Get-Content -Raw -LiteralPath '..\heldout-external\reviewer-v2-evidence-assembly\2026-10-03-25bde93\assembly_driver.py' | .\.venv\Scripts\python.exe -B -
```

Task-local driver SHA-256:
`61441cc25a62f29315db428f36087c1db48e28e1d7f99773cb0dc57487fc44d3`.
It records the exact extraction/check functions and contains no source transcripts.
This is an evidence-assembly helper, not an installed production module or operational
interface. **Do not rerun assembly in place:** exclusive creation refuses overwrite.
The directory was created with `Path.mkdir(exist_ok=False)` before its first files.
Private preservation snapshot SHA-256:
`fefd98dffaabad64eb8bebb6b883f62ae235065ff1a3d658c3ed2e039e942a49`.

The read-only filesystem replay command (PASS: 52 artifacts, three specification
components, fourteen copy equalities, 61 protected files):

```powershell
@'
from pathlib import Path
import json,subprocess
import tests
from experiments.reviewer_protocol_v2 import ledger_adoption as a, procedure_evidence as e, production_preparation as p, selection as s, ledger_reconciliation as r
from experiments.reviewer_protocol_v2.common import canonical,sha_bytes
from experiments.reviewer_protocol_v2.control_serialization import object_bytes
root=Path('..').resolve(); prefix='heldout-external/reviewer-v2-evidence-assembly/2026-10-03-25bde93'
raw=(root/prefix/'assembly-index.json').read_bytes(); index=object_bytes(raw)
assert sha_bytes(raw)=='16cc736f6dea8672c920777f8365b4c4562d47abdfd61a9858e749d307ac1f3d'
read=lambda fb:a.read_binding(root,fb)
for entry in index['artifacts']:
 raw=read(entry['binding']); assert len(raw)==entry['size_bytes']
 if entry['kind'] not in ('HISTORICAL_GIT_BLOB','ORIGINAL_OWNER_ATTACHMENT_COPY'):
  object_bytes(raw)
for role,item in index['rules'].items():
 e.specification(read(item['specification']),role,read)
 draft=object_bytes(read(item['applicability_draft']))
 assert draft['normative_document']==index['fixed_subjects']['main/docs/experiments/reviewer-protocol-v2-current-rules-v1.md']
 assert draft['normative_document']['sha256']==e.NORMATIVE_DOCUMENT_SHA256
 assert 'semantic_review_evidence' not in draft
 if role=='eligibility_specification':assert 'historical_ledger_reconciliation' not in draft
 else:assert draft['historical_ledger_reconciliation'] is None
receipt=object_bytes((root/'main/docs/experiments/reviewer-protocol-v2-rule-copy-receipt.json').read_bytes())
for fb in receipt['copies']:
 assert read(fb)==(root/'data/reviewer-v2-evidence-recovery/2026-10-02'/Path(fb['path']).name).read_bytes()
rec=object_bytes(read(index['reconciliation_review']['subject']))
assert 'independent_review' not in rec
assert r.review_subject(rec)==index['reconciliation_review']['subject_sha256']
protected=object_bytes((root/prefix/'preservation-before.json').read_bytes())
assert all(sha_bytes(Path(path).read_bytes())==digest for path,digest in protected.items())
current=p.verification_bundle({path:read({'path':path,'sha256':digest}) for path,digest in rec['current_verification_bundle']['files'].items()})
assert current==rec['current_verification_bundle']
assert not subprocess.check_output(['git','diff','--name-only'],text=True).strip()
assert not subprocess.check_output(['git','diff','--cached','--name-only'],text=True).strip()
print(json.dumps({'replay':'PASS','bound_artifacts':len(index['artifacts']),'complete_specification_components':len(index['rules']),'original_copy_equalities':len(receipt['copies']),'protected_files_unchanged':len(protected),'current_verification_bundle_sha256':current['sha256'],'overall_compatibility':'NOT_ASSESSED'}))
'@ | .\.venv\Scripts\python.exe -B -
git diff --check
```

The replay's empty-diff assertions describe the state before this receipt/handoff
was created; after their authorized local commit they again apply. All component
checks are metadata/binding checks, not independent semantic acceptance.

## Remaining prerequisites and scope receipt

The focused handoff is `reviewer-protocol-v2-actual-evidence-claude-handoff.md`.
Next: independent inspection of these exact subjects and real subject-bound review
records, then separately authorized completion/checks of the dependent wrappers.
Design/exclusion/content/rubric/interface/test approvals, full historical and current
runtime/dependency/input/inventory/procedure evidence and operational permissions
remain separate prerequisites. Preserve the accepted phase order and placement of
runtime/cost/terms/credit decisions. No prerequisite was waived or moved.

Only this receipt and the new focused handoff are authorized for explicit staging
and one local documentation commit. All private artifacts stay outside Git.
Six Claude reports, proposed draft, historical artifacts, private originals,
implementation and unrelated work remain unchanged.

Scope receipt: actual private evidence assembly and complete-component verification
only. No implementation edits, actual preparation/InputBinding, FreezeManifest,
adoption/sealing, ranking/sampling, packets, freezes, owner labeling, operational
tools, Claude/model invocation, AWS/external API calls, installs or push.
**Freeze 1 readiness remains unestablished.**
