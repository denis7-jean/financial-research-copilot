# Current rule consolidation: implementation contract and receipt

Owner D1-D8 record SHA-256:
`78e34cedfb33e6deb3d328c2373f251bd94bc0b4ed714738678f646dfdfd8920`.
The proposed draft and all three Claude reports remain unchanged/uncommitted.
The separate current normative document is reviewer-protocol-v2-current-rules-v1;
it consolidates accepted draft sections 1-3 with D1-D8, not historical finalization.

## Before-implementation interface delta

E03c constructs alternatives from the three literals in, from, according to; never
whitespace-split the last literal. Empty eligibility views are NOT_EVALUABLE under
D4; metadata/ID/hash faults with usable text retain independent evaluation.

DR-1: RuleTextEvidence v3 and RuleAlgorithmEvidence v2 add section_locator
(nonempty string) to the existing exact fields. record_reference is document-level,
not a section locator. Same document hash/path/reference may support multiple
sections. Equal hashes at different paths or inconsistent document references fail.
Multiple citations never imply independent provenance: shared_origins stays a unique
hash/path map. Duplicate origin/section citations do not increase an evidence count.
ReviewEvidence v3 adds source_sections and algorithm_sections (nonempty sorted unique
locator lists) to each shared_origin_reviews entry. These must exactly equal the
source/algorithm locators citing the shared raw document. Raw-record and exact
contract hash checks remain. Text transcription is externally reviewed (DR-2), not
authenticated or mechanically validated as a faithful extraction.

RuleApplicability v2 adds normative_document_id and historical_ledger_policy.
For eligibility normative_document_id=reviewer-protocol-v2-current-rules-v1,
reconciliation=CURRENT_E01_METADATA_AND_E03C_LITERAL_CORRECTION, and
historical_ledger_policy=IDENTICAL_CORRECTED_ELIGIBILITY_SOURCE_ONLY. Other roles
retain UNCHANGED_POLICY with historical_ledger_policy=NO_NEW_LEDGER_POLICY.
All rule roles cite the new current normative document ID. No current/historical
procedure equality is claimed. Compatibility conservatively fails with
E03C_LEDGER_RECONCILIATION_REQUIRED when the verified historical eligibility source
hash differs from the corrected current eligibility source hash. This implements no
alternative-ledger evidence contract or override; those need separately reviewed
evidence/authorization. Synthetic positive fixtures bind corrected source bytes;
real unchanged historical ledgers cannot silently pass this new boundary.

FreezeManifest roles, InputBinding, PreparationReport, source-record hash recipes,
selection algorithms/domains/serialization and adapter roots stay unchanged.
Only nested evidence versions change. No real RuleSpecification bundles are built.

DR-3: __loader__.get_code, __spec__.loader.get_code, breakpoint, help, subclass
gadgets and code-object replacement are explicitly outside the static checker
guarantee. Non-executing probes document acceptance of those source strings. They
are never executed. No sandbox development or broad semantic-diff engine is added.

## Receipt and focused independent handoff

### Normative consolidation and reconciliation

[Current rules](reviewer-protocol-v2-current-rules-v1.md) SHA-256:
`f4a27c8da174e9c038c82d11209e334b5c7e4c21f1b324f18dd0a49da58d621a`.
[Decision/reconciliation record](reviewer-protocol-v2-current-rule-reconciliation.json)
binds that document, the owner D1-D8 raw-record hash and unchanged draft/report
hashes. It records pending independent semantic review, no historical-procedure
identity, no ledger-adoption approval and no Freeze 1 readiness. Narrow
.gitattributes entries preserve saved bytes for the new hash-bound current document
and metadata records; no historical receipt is normalized or rewritten.

D1-D8 are incorporated, including the complete 42-phrase E05 literal list expanded
from the accepted draft and checked against recovered S-576 text, independently of
implementation code. The original draft is not edited or relabelled as finalized.
Implementation changes are the E03c literal-alternatives construction and D4's
empty-view text_evaluable=False correction. E03a/E03b form separation, ASCII digit
lookahead, E05 whole-q spans, E06 pairing/independent spaces, and reference-hash
ordering retain the reviewed behavior. The 100 registered fixtures and 37
supplementary checks remain separate; this task does not add normative rules.

### Single targeted recovery attempt and copies

The single authorized attempt inspected final responses and owner-turn locators in
session lines 583-1016. Recovered original JSONL records:

| Record | Bytes | SHA-256 |
|---|---:|---|
| Preliminary stop response S-803 | 5,990 | `0436d3d773070c468709126399364805fec157ca76c984d6577504f475cae714` |
| Provenance recovery response S-932 | 7,331 | `24c914c331cd715ed985e9d99ea988e705998847878f9894795f730770e2879d` |
| Accepted authoritative audit response S-1009 | 8,847 | `2aa29f9f8d9d9dc9ed8f5123387dac1f01a8dd582ebd9373707994ac0f833016` |

Intervening owner attachment records 78ab30aa and a5463e57 and the current D1-D8
record were also preserved with exact hashes. The accepted audit response reports
the 100/37 result; it does not establish a complete historical registration record
for each supplementary check or authenticate their past execution. No registration
evidence was manufactured. The preliminary stopped response is kept as provenance,
not promoted to an authoritative population result.

The data/ originals and old preservation.json remain byte-identical. New originals
are exclusive-created alongside them under data/reviewer-v2-evidence-recovery/
2026-10-02; audit-preservation.json hash is
`b18e1cbec87dcb84308cdadbf73ba95fb04734dfa85a57e4f1b40d7459604c6d`.
The [updated recovery inventory](reviewer-protocol-v2-recovered-records.json) is v2
and explicitly records S-576 trailing LF, the 2,721-line snapshot extent and
retained_source_complete=false. S-576 remains 28,909 bytes / 7e481873...;
its extraction remains 27,395 bytes / 539541e3...; original preservation manifest
remains 8e84755d... . The first 2,721 session lines still hash to bb64a779... .
The complete:false flag is acknowledged without declaring it erroneous or claiming
missing history recovered. Only the specifically recovered records are reported.

**14/14 hash-identical copies verified** against the recovery records and manifest
hashes. Directory: heldout-external/reviewer-v2-rule-evidence/2026-10-02/.
Directory and every destination were exclusive-created; no file was overwritten.
The [copy receipt](reviewer-protocol-v2-rule-copy-receipt.json) contains paths/hashes
only. Adapter roots are unchanged. Private record contents remain outside Git and
logs. These copies are not real RuleSpecification or InputBinding bundles; no real
preparation/adoption API consumed them.

### Exact validation

Commands run from the repository root:

```powershell
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_eligibility.py tests/test_reviewer_v2_review_remediation.py tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py -q --basetemp=.pytest_cache/reviewer-v2-current-rules-focused-01
$currentRuleTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' -and $_ -notmatch 'test_reviewer_v2_regression\.py$' })
& .venv\Scripts\python.exe -B -m pytest @currentRuleTests -q --basetemp=.pytest_cache/reviewer-v2-current-rules-regressions-02
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_adoption_encoding.py::test_complete_positive_and_deterministic_bytes -q -s --basetemp=.pytest_cache/reviewer-v2-current-rules-reproduction-02
.venv\Scripts\ruff.exe check experiments/reviewer_protocol_v2 tests/test_reviewer_v2*.py
.venv\Scripts\ruff.exe format --check experiments/reviewer_protocol_v2/eligibility.py experiments/reviewer_protocol_v2/procedure_evidence.py tests/test_reviewer_v2_eligibility.py tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py tests/test_reviewer_v2_review_remediation.py
git diff --check
```

Focused: **333 passed** before adding the two explicit old-reconciliation rejection
cases; both are covered by the final full run. Final allowed v2 regressions: **609 passed**, including
**35 new cases**. Deterministic two-root reproduction: **1 passed**. Ruff, six-file
formatting and whitespace checks passed. Existing asyncio_mode warning remains.
Offline guard intercepted four deliberate network probes in the full suite; none
were sent. test_accepted_population_regression remains excluded and unexecuted.
Its source is bound by the synthetic test manifest, not claimed as tested here.

Coverage: exact E03c subrule/spans on valid literal prepositions; E02 still matching
invalid standalone to/according tails with E03 absent; evidence-derived corrected
contract accepted and split-word defect rejected; usable/invalid question and E05
punctuation behavior; multi-section and duplicate citations with one shared origin;
exact review section sets; changed historical source explicitly blocked; six DR-3
source probes parsed but never executed. Existing no-write/no-operational-hook,
offline guard, import-purity and selection/serialization regressions pass.

### Current bundle digests and synthetic vectors

All four current digests change because eligibility.py is shared. Verification
also includes the changed procedure_evidence.py. Selection algorithms, seeds,
domains and serialized byte contracts are unchanged; source binding hashes change.

| Bundle | SHA-256 |
|---|---|
| Verification, 16 | `a8cfbe13f79bfc7cafa087a64a9fec0b768cfc45bdf6a10481ec8c384b8ce7cf` |
| Selection, 7 | `0797dd5065486ecb142bed90fe7d1a74f8792e80659c1b64c9f495d71eba1187` |
| Control/trial, 10 | `2e4c224927c9450608afb414c4ad1f8c09932c8b8cc5be9cdc9de0eadd1fc0bf` |
| Owner/analysis, 12 | `492d688bd937cbc68e4ccc86c0c11a4be1dfcef77423133a3c826728d8a5a2b4` |

Synthetic reproduction hashes:
freeze `9559ed784f431a0c029ec0445748434439471aa6631b4f25bb72c1df598d5e6e`;
procedure `9b93c2a19d0168664bee63ba06b297b0b4876ce6894512d3a0e3139b708f47fb`;
report `41fa9dc3e71fcb301696d4a944b6ee031ea0a5a4f07490fab070c853a01f7961`;
technical result `2f0102f7e3f76a25c99e3a6c017cb7dc6164d2576f3c9c425b6bf3a93fa21261`.
Original historical generating hash 105be32b... and earlier receipts remain
unchanged; no historical artifacts are regenerated or real API inputs processed.

### Historical-ledger implications and Claude handoff

E03c changes rule IDs/subrules and normalized spans for the split forms, even though
E02 independently excludes their tails. The corrected according to phrase now
records its full span. D4 also corrects the empty-view evidence flag. Neither
synthetic tests nor previously reported aggregate counts prove that an unchanged
historical ledger accurately records the corrected procedure. The source-equality
gate is intentionally conservative, not a semantic-equivalence classifier. A
separate reviewed historical-ledger reconciliation contract/evidence is required
before any old-ledger compatibility claim; this task supplies no override or
operational adoption. Historical provenance verification remains distinct.

Focused independent review: compare this commit to 34a3edd; review the current
normative document against accepted proposed sections 1-3 and D1-D8; verify complete
vocabularies, algorithms, boundaries, every resolution and exact contract hash.
Inspect E03c construction and spans, D4 flag correction, versioned section locators,
shared-origin section declarations and conservative ledger guard. Inspect metadata
LF/snapshot/completeness and copy hashes. DR-2 transcription is not mechanically
authenticated; DR-3 probes document accepted static limitations. No approval
declaration is written for Claude, and Claude was neither invoked nor messaged.

Scoped inventory: eligibility.py, procedure_evidence.py; four focused test files;
current normative document, decision/reconciliation, implementation receipt, updated
recovery inventory and copy receipt; narrow byte-preservation attributes. All three
Claude reports and the proposed draft remain unchanged/uncommitted. Their full
hashes are recorded in the decision/reconciliation artifact.

Remaining prerequisites: Claude code/semantic review and actual contract-bound
review evidence; historical supplementary registration/execution limitations;
separately reviewed ledger reconciliation; actual content/rubric/design/interface
approvals and complete Freeze 1 runtime/dependency/input evidence; separately
authorized operational tools and phase/trust producers. Phase sequence and cost,
credit, terms and live prerequisites are unchanged. Freeze 1 is not ready.

Scope receipt: current normative consolidation, owner-authorized private evidence
preservation/copying and synthetic corrections only. No real population inspection,
screening, ranking/sampling, production packets, real rule/input bundles or
preparation/adoption APIs, operational adoption/seals/freezes, owner labeling,
operational managers, reviewer/router, AWS operation or external API call. Local
scoped commit only, no push; historical artifacts and unrelated work preserved.
