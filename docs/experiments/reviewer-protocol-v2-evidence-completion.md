# Evidence completion: schemas and verification order

This contract is specified before implementation. All new wrappers used in tests
are invented. No actual rule, preparation, adoption or Freeze 1 bundle is assembled.
Independent acceptance of these changes and the lemma remains pending.

## Bytes, evidence joins and versions

Use the existing canonical encoding: strict UTF-8 JSON, ensure_ascii=True, sorted
object keys, compact separators, finite numbers, one final LF. SHA-256 preimages
are those exact bytes. File bindings (FB) have exactly path:string and
sha256:lowercase-64-hex; existing relative-path/approved-root/resolved containment
and captured-byte hash verification apply. A binding never authenticates approval.

ReviewEvidence v4 adds normative_document:FB to v3's exact fields. RuleApplicability
v3 adds normative_document:FB and historical_ledger_reconciliation:FB|null to v2's
exact fields. Obsolete v3 reviews/v2 applicability are rejected. All three rule
applicability records and their reviews must bind the identical FB, not only the
existing normative_document_id. Raw normative bytes are checked. Other text and
algorithm evidence versions remain unchanged; their contract hashes now bind the
expanded mechanical contract. Mechanical equality is not independent rule authority.

The eligibility contract adds explicit normalization steps; sorted e05_phrases
(42), e05_terminal=["?","."], whole-question/full-span tokens; eight numbered
E07 condition tokens, required fields, exact ID and source/stratum contracts,
row-invalidation versus population-abort tokens; D4 evaluability and blocker
tokens; NOT_EVALUABLE semantics and E06 independent evaluation/preservation tokens.
The authoritative mapping is current-rules-v1 sections 1.2, E05, E06 and E07.
Finite patterns, dispositions, precedence and descriptive normalization label stay.

## HistoricalLedgerReconciliation v1

Exact fields besides schema:
manifest:FB; ledger:FB; historical_generating_bundle:FB;
historical_source:FB; current_source:FB; current_verification_bundle:{files:map
of approved source paths to 64-hex,sha256:64-hex}; lemma:FB; counts_evidence:FB;
independent_review:FB. This is nested only in the eligibility RuleApplicability;
the other roles require null. Existing FreezeManifest roles and InputBinding stay.

Only the manifest, ledger, generating digest and source transition identified in
the separate lemma are eligible. The lemma FB must match this shipped lemma's
exact raw hash. Historical source must equal the generating wrapper's eligibility
FB and the verified historical source map; the complete historical map's canonical
hash must equal its manifest implementation digest. Current source and full
current verification bundle must equal the verified executing-source bindings.
Other applicability checks continue unchanged. Absence leaves the original guard.
The eligibility policy token in applicability v3 is
IDENTICAL_SOURCE_OR_IDENTIFIED_RECONCILIATION. Non-eligibility roles retain
NO_NEW_LEDGER_POLICY. An invalid supplied reconciliation also fails when the
source hashes happen to be equal; it is never ignored as an optional override.

CountsEvidence v1 exact fields: schema; manifest_sha256:64-hex;
ledger_sha256:64-hex; procedure_sha256:64-hex; counts:object with exactly
total_rows,e03_rows,e03c_rows,union_rows,normalized_empty_question_rows (nonnegative
integers, excluding bool). procedure_sha256 is SHA-256(canonical(COUNT_PROCEDURE)),
the explicit mechanical counting descriptor exported by ledger_reconciliation.
It binds the specified procedure; the current bundle additionally binds its code.
Rows are counted, not occurrences. Strict unique-key, finite-number JSONL is parsed
only from the same captured ledger bytes whose hash was verified. Eligibility and
match structures/types are validated. No question classifier or normalizer runs.
Required counts are 104,0,0,0,0. Actual counts must equal declared counts.

ReconciliationReview v1 exact fields: schema; subject_sha256,contract_sha256,
lemma_sha256,counts_sha256 (64-hex); record_reference,record_path,record_sha256;
reviewer,recorded_utc,note. Nonempty strings, strict UTF-8, UTC
YYYY-MM-DDTHH:MM:SSZ, exact raw record hash required. Review subject is SHA-256 of
canonical reconciliation with independent_review removed and schema replaced by
reviewer-protocol-v2-historical-ledger-reconciliation-subject-v1. This avoids a
review/subject hash cycle while retaining every other binding. contract_sha256
is SHA-256(canonical(RECONCILIATION_CONTRACT)); lemma_sha256 and counts_sha256 join
the exact bindings in that subject. No self-asserted provenance/approval flag exists.
Authorship, independence, semantics, replay authenticity and trust remain external.

## Verification order

1. Existing historical manifest/payload, sixteen generating sources/recipe,
   original input closure/runtime and current executing-source checks.
2. Existing specification, raw source record, exact contract, applicability and
   semantic-review checks; capture/hash normative document and require all joins.
3. If eligibility source equality fails, require the eligibility-only FB. Validate
   exact schema, pinned transition and canonical bundle relationships; verify
   manifest/ledger bindings against already captured historical buffers, and read
   both source FBs through safe paths.
4. Verify exact shipped lemma bytes; capture/hash counts wrapper; recompute its
   procedure-bound counts from the same captured ledger; require 104/zero counts.
5. Verify independent-review wrapper, exact subject/contract/lemma/count joins,
   raw review record, reviewer/UTC/note. Only then discharge the source mismatch.
6. Continue every remaining existing compatibility/runtime/dependency/input check.

Missing/malformed/bad versions, paths, bytes, joins or affected counts fail with
sanitized codes. No writes or operational hooks are available in this path.
Passing means technical evidence bindings verified, never adoption, authenticated
approval, established past execution, operational authorization or readiness.

## Private counts receipt

A repeat manifest-bound read-only count may exclusive-create only a counts-only
receipt outside Git. It records the two hashes, procedure hash, schema and counts.
It is not a reconciliation wrapper or a real review record. Historical artifacts
and four uncommitted Claude reports remain unchanged.

Implementation/test commands, current hashes, preservation checks and focused
Claude handoff follow below. Old receipts remain historical.

## Complete changed evidence envelopes

All fields below are required; extra keys fail. Hash strings are lowercase
64-hex. Existing source/algorithm wrappers continue to require exact raw-record
and mechanical-contract hashes and distinct structures/shared-origin review.

ReviewEvidence v4:

| Field | Type/constraint |
|---|---|
| schema | reviewer-protocol-v2-review-evidence-v4 |
| subject_sha256 | Exact RuleSpecification FB hash |
| contract_sha256 | SHA-256(canonical applicable mechanical contract) |
| record_reference | Nonempty document-level string |
| record_path | Existing approved relative path |
| record_sha256 | SHA-256 of captured raw review record |
| reviewer, note | Nonempty strict-UTF-8 strings; no authorship authentication |
| recorded_utc | Exact YYYY-MM-DDTHH:MM:SSZ |
| normative_document | Same FB as applicability; captured raw bytes verified |
| shared_origin_reviews | Existing exact list of record_path, record_sha256, supports_both_roles=true, note, source_sections, algorithm_sections; section lists equal sorted unique cited locators |

RuleApplicability v3:

| Field | Type/constraint |
|---|---|
| schema | reviewer-protocol-v2-rule-applicability-v3 |
| role | eligibility_specification / exposure_specification / grouping_similarity_specification |
| historical_implementation_sha256 | Verified original generating digest |
| historical_source | Exactly filename:string, sha256:hash, joined to original source map |
| current_source | FB joined to verified executing-source map |
| original_evidence | Nonempty original-input-closure FB list, exactly the enclosing rule list |
| specification | FB equal to applicable FreezeManifest specification role |
| decision_evidence | FB equal to specification's separate current decision evidence |
| semantic_review_evidence | FB for ReviewEvidence v4 |
| reconciliation | CURRENT_E01_METADATA_AND_E03C_LITERAL_CORRECTION for eligibility; UNCHANGED_POLICY otherwise |
| normative_document_id | reviewer-protocol-v2-current-rules-v1 |
| normative_document | Identical FB in every rule applicability and corresponding review |
| historical_ledger_policy | IDENTICAL_SOURCE_OR_IDENTIFIED_RECONCILIATION for eligibility; NO_NEW_LEDGER_POLICY otherwise |
| historical_ledger_reconciliation | FB or null for eligibility; null required for other roles |

RuleSpecification retains v2's envelope. An obsolete eligibility contract fails
normative_rule_contract because its canonical contract is incomplete. The stored
contract hash, source-text hash, algorithm hash, raw original-record hash, current
normative-document hash and review hash remain different evidence subjects.

The reconciliation reader receives verified history/current/generating context
from the existing adoption verifier. It is not a standalone provenance verifier;
untrusted dictionaries supplied directly to its internal join routine are not
independently verified history. Tests substitute the pinned TARGET solely with
invented subjects via monkeypatch. There is no production transition argument or
API override. The shipped pinned transition and lemma bytes are mandatory.

The counts checker validates the six eligibility keys, string rule/reason lists,
E01-E07 rule allowlist, four dispositions, boolean evaluability, string-or-null
normalized view, and exact match keys with string scalars and two ordered
nonnegative integer span offsets. Other row metadata is never evaluated or emitted.
Counters use set membership and any(subrule == E03c), so repeated matches/reasons
do not multiply row counts. Duplicate keys/non-finite values/noncanonical or
malformed JSON, blank rows, bad UTF-8 or missing final LF reject with
RECONCILIATION_LEDGER_STRUCTURE. Canonical re-encoding also rejects overflowing
finite-number syntax that decodes to infinity.

New repository dependency: ledger_reconciliation.py is the seventeenth current
verification source, imported by procedure_evidence. Its only added standard
library use is datetime (already covered by the reviewed dependency allowlist).
The synthetic test coverage map adds test_reviewer_v2_evidence_completion.py.
No dependency installation, selector/API change or static-checker expansion occurs.

## Explicit mechanical additions (implementation description)

The following exact fields supplement the unchanged finite_patterns,
normalization label, rule_dispositions and precedence. This description does not
provide independent authority or certify faithful extraction from raw sources.

```json
{
  "e05_algorithm": "Q_IN_P05_OR_ONE_TERMINAL_MARK_REMOVED_IN_P05",
  "e05_phrases": [
    "explain it",
    "explain that",
    "explain them",
    "explain these",
    "explain this",
    "explain those",
    "how did it compare",
    "how did that compare",
    "how did these compare",
    "how did they compare",
    "how did this compare",
    "how did those compare",
    "how do these compare",
    "how do they compare",
    "how do those compare",
    "how does it compare",
    "how does that compare",
    "how does this compare",
    "summarize it",
    "summarize that",
    "summarize them",
    "summarize these",
    "summarize this",
    "summarize those",
    "what are these",
    "what are they",
    "what are those",
    "what did it mean",
    "what did that mean",
    "what did this mean",
    "what does it mean",
    "what does that mean",
    "what does this mean",
    "what is it",
    "what is that",
    "what is this",
    "what was it",
    "what was that",
    "what was this",
    "what were these",
    "what were they",
    "what were those"
  ],
  "e05_span": "ENTIRE_NORMALIZED_Q_INCLUDING_PERMITTED_MARK",
  "e05_terminal": [
    "?",
    "."
  ],
  "e06_evaluation": {
    "bracketed": "ANYWHERE_NO_OUTER_BOUNDARIES",
    "delimiter_forms": "INDEPENDENT_PAIRED_DELIMITERS_INDEPENDENT_ZERO_OR_ONE_INNER_SPACE",
    "higher_precedence": "PRESERVE_MATCHES",
    "nested": "PRESERVE_ALL_REGISTERED_SUBRULE_SPANS",
    "non_evaluable": "NOT_EVALUABLE_NO_MATCHES_INCLUDING_EMPTY_VIEW",
    "usable": "ALL_REGISTERED_SUBRULES_INDEPENDENT_EVEN_ON_METADATA_INVALID_ROWS"
  },
  "e07_conditions": [
    "1_NOT_UNIQUE_KEY_JSON_OBJECT",
    "2_REQUIRED_FIELD_MISSING_OR_NONSTRING",
    "3_INVALID_OR_UNKNOWN_CAND_ID",
    "4_INVALID_EXACT_SOURCE_STRATUM_PAIR",
    "5_METADATA_REFERENCE_MISMATCH",
    "6_QUESTION_NOT_STRICT_UTF8",
    "7_NORMALIZED_EMPTY_QUESTION",
    "8_ORIGINAL_QUESTION_HASH_REFERENCE_MISMATCH"
  ],
  "e07_failure_scope": {
    "abort_conversion": "NEVER_PER_ROW_DISPOSITION",
    "population_abort": [
      "POPULATION_FILE_HASH_MISMATCH",
      "DUPLICATE_INDEX_ID"
    ],
    "row": "ANY_E07_CONDITION_INPUT_INVALID"
  },
  "e07_inputs": {
    "cand_id_fullmatch": "c_[0-9a-f]{10}",
    "extra_fields": "ALLOWED",
    "json_constants": "REJECT_NAN_AND_INFINITY",
    "metadata": "EXACT_UNNORMALIZED_UNCASEFOLDED",
    "metadata_fields": [
      "source",
      "sampling_stratum",
      "source_revision",
      "context_group"
    ],
    "prohibited_inputs": [
      "ROUTING_LABELS",
      "SOURCE_ANSWERS",
      "PROVISIONAL_LABELS"
    ],
    "reference": "IMMUTABLE_INDEX_FROM_HASH_VERIFIED_FROZEN_PILOT",
    "reference_fields": [
      "cand_id",
      "source",
      "sampling_stratum",
      "source_revision",
      "context_group",
      "question_sha256"
    ],
    "reference_question_hash": "SHA256_STRICT_ORIGINAL_UTF8_NO_ADDED_LF",
    "required_fields": [
      "cand_id",
      "question",
      "source",
      "sampling_stratum",
      "source_revision",
      "context_group"
    ],
    "source_stratum_pairs": [
      [
        "tatqa",
        "T1_qa"
      ],
      [
        "finqa",
        "T1_qa"
      ],
      [
        "finlfqa",
        "num"
      ],
      [
        "finlfqa",
        "interp"
      ],
      [
        "finlfqa",
        "other"
      ],
      [
        "finlfqa",
        "mixed"
      ]
    ]
  },
  "normalization_steps": [
    {
      "form": "NFKC",
      "operation": "UNICODE_NORMALIZE"
    },
    {
      "operation": "STR_CASEFOLD"
    },
    {
      "flags": "UNICODE",
      "operation": "RE_SUB",
      "pattern": "\\s+",
      "replacement": " "
    },
    {
      "characters": "PYTHON_UNICODE_WHITESPACE",
      "operation": "STR_STRIP"
    }
  ],
  "text_evaluable": {
    "all": [
      "VALID_UNIQUE_KEY_JSON_OBJECT",
      "STRING_QUESTION",
      "STRICT_UTF8_QUESTION",
      "NONEMPTY_NORMALIZED_VIEW"
    ],
    "blocks": [
      "INVALID_JSON",
      "DUPLICATE_KEYS",
      "MISSING_QUESTION",
      "NONSTRING_QUESTION",
      "INVALID_UTF8_QUESTION",
      "EMPTY_NORMALIZED_VIEW"
    ],
    "does_not_block": [
      "METADATA_FAULT",
      "UNKNOWN_ID",
      "QUESTION_HASH_MISMATCH"
    ],
    "non_evaluable": {
      "disposition": "INPUT_INVALID",
      "empty_normalized_view": "",
      "empty_reason": "normalized_empty_question",
      "matches": [],
      "text_rules": "E01_THROUGH_E06_NOT_EVALUABLE_NEVER_INFERRED",
      "unavailable_normalized_view": null
    }
  }
}
```

## Implementation receipt

Parent HEAD: bf8295bfc42478fa428524f1526aaf5c62857ad4. No prior work was reverted.

S-1 adds mechanical fields only. eligibility.py, common.py, exposure.py,
similarity.py, selection.py and packet_serialization.py are raw-byte identical to
bf8295b. S-2 uses ReviewEvidence v4 / RuleApplicability v3 with raw normative FB
joins. S-3 changes exactly two editorial passages; prior normative bytes remain
at bf8295b with SHA-256 f4a27c8da174e9c038c82d11209e334b5c7e4c21f1b324f18dd0a49da58d621a.
The current companion reconciliation metadata now references the new hash; old
implementation receipts and Claude reports retain their historical hash anchors.

| Current evidence | SHA-256 |
|---|---|
| Editorially corrected normative document | 4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7 |
| Separate proposed lemma | febaf27765974a35798e27652af90267978a4af6294821f718b3701d97c9f7ef |
| Expanded eligibility mechanical contract | e69425077b073338e9beeb1ecee23518309967712697a58d60257a6ec386d49d |
| Counts procedure canonical descriptor | 1b8a7e5e0871ec01cdf31215a69a96123eb8ec61d6a18d2158bd2564818b5b8d |
| Exclusive-created private counts receipt | 584d43ad6a02f7cdffa345a1fd92da04f9eef0ec72bc2b82dafed89ba82c417b |

Private receipt location (outside Git):
heldout-external/reviewer-v2-ledger-counts-2026-10-02-evidence-completion/counts-receipt.json.
Only schema, manifest/ledger/procedure hashes and five counts are present. Actual
RuleSpecification, InputBinding, preparation, adoption, reconciliation/review or
FreezeManifest wrappers were not assembled. Counts: 104 / 0 / 0 / 0 / 0 in the
COUNT_KEYS order. Manifest and ledger remain 057d6331... and 6b3f97d8... respectively.

### Current bundles, separate from historical anchors

| Bundle | Count | Current SHA-256 |
|---|---:|---|
| Verification (replacement current) | 17 | 1ad392707e99ca25ce16275bcef27f9ed737bb2aae1c9a3767d189f30a619dd4 |
| Selection (unchanged current) | 7 | 0797dd5065486ecb142bed90fe7d1a74f8792e80659c1b64c9f495d71eba1187 |
| Control/trial (unchanged current) | 10 | 2e4c224927c9450608afb414c4ad1f8c09932c8b8cc5be9cdc9de0eadd1fc0bf |
| Owner/analysis (unchanged current) | 12 | 492d688bd937cbc68e4ccc86c0c11a4be1dfcef77423133a3c826728d8a5a2b4 |

Prior current verification at bf8295b (16) remains a historical receipt:
a8cfbe13f79bfc7cafa087a64a9fec0b768cfc45bdf6a10481ec8c384b8ce7cf.
Original historical generating digest remains
105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc.
All sixteen Git blobs at 182f131 reproduce that digest; historical eligibility
bytes also match 34a3edd. Sources were never executed to establish provenance.

### Validation commands and results

From C:/Projects/AWS Project/main, existing environment and default offline guard:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_evidence_completion.py tests/test_reviewer_v2_review_remediation.py tests/test_reviewer_v2_adoption_encoding.py tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_eligibility.py -q -p no:cacheprovider --basetemp=.pytest_cache/reviewer-v2-evidence-completion-focused-02 --tb=short
$evidenceCompletionTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' })
& .\.venv\Scripts\python.exe -B -m pytest @evidenceCompletionTests -k 'not test_accepted_population_regression' -q -p no:cacheprovider --basetemp=.pytest_cache/reviewer-v2-evidence-completion-regressions-01 --tb=short
.\.venv\Scripts\ruff.exe check experiments/reviewer_protocol_v2 tests/test_reviewer_v2*.py
.\.venv\Scripts\ruff.exe format --check experiments/reviewer_protocol_v2/ledger_reconciliation.py experiments/reviewer_protocol_v2/procedure_evidence.py experiments/reviewer_protocol_v2/ledger_adoption.py experiments/reviewer_protocol_v2/production_preparation.py tests/test_reviewer_v2_evidence_completion.py tests/test_reviewer_v2_adoption_encoding.py tests/test_reviewer_v2_preparation.py
git diff --check
```

Focused: 391 passed. All permitted v2 regressions: 665 passed, one deselected
(the real screening test), including 56 new tests. Ruff passed; seven scoped Python
files already formatted; whitespace check passed. Existing asyncio_mode warning
persists. Guard intercepted one deliberate network probe focused and four in the
full suite, none sent. Existing selection/serialization golden outputs pass.

Two-root synthetic contract/count bytes agree. Full invented 104-row proposed
compatibility passes with classification, normalization, ranking, ID generation,
packet/trial builders and writes patched to fail. A remaining runtime mismatch
still rejects after valid reconciliation. Static source checks remain reviewed
hash-bound checks, not a Python sandbox. No operational manager is introduced.
The 324 invented regex containment probes illustrate the lemma, not an exhaustive
proof or historical execution. Tests temporarily replace TARGET with invented
subjects; no such override is exposed through production APIs.

Initial diagnostics: the first scratch path had no parent (45 tests passed, 78
setup errors; an isolated diagnostic also failed setup). The first runnable focused
subset had 170 passes and one test-harness failure from patching external_id in the
wrong module. Corrected the hook location; the isolated hooks test passed. Final
focused and full results above supersede those unsuccessful validation attempts.
No implementation behavior was changed to accommodate a failed synthetic result.

### Preservation and remaining prerequisites

The four Claude reports remain unchanged and uncommitted:

| Report | Raw SHA-256 |
|---|---|
| Original review | caba9fc167d372f95414e5f6d37e3b901f0c6b03e98ec8ba879f4bb7c5254f9b |
| Re-review | 5af319094d26a09e1145349fb733b56200117da396b637eb3852b8a0dd99589c |
| Delta review | e773ff214e3226c49f985b754a19e12df51cf92c732fe97c6dfb6a94708de493 |
| Current-rules review | 07c5125137b50e816103c0b9047e6c08be5fa7fc93c076a69de119c6bd76a1b1 |

Historical artifacts/private originals are untouched. The sole new real-data
artifact is the explicitly authorized counts-only receipt. All real verifier
inputs remain unassembled. Unrelated tracked/untracked work is preserved.

Consolidated prerequisite list:
1. Independent Claude review of S-1/S-2/S-3, the source-diff lemma, typed
   reconciliation, byte subjects and failure paths. No independent acceptance is
   claimed for this milestone, and Claude was neither invoked nor messaged.
2. Actual raw-source/algorithm/decision/specification/applicability/review wrappers
   binding the corrected normative document and complete mechanical contract,
   with independent semantic review of those actual wrappers. S-576 complete:false
   and supplementary-check registration/execution limitations remain explicit.
3. Actual reviewed reconciliation subjects and raw review record, including this
   ledger-bound counts evidence; technical compatibility does not adopt the ledger
   or authenticate approval/past execution.
4. Actual design/exclusion-policy, content, anchor/diagnostic references, rubric,
   interface and test-manifest approvals, plus complete applicable Freeze 1
   input/inventory/procedure and runtime/dependency evidence. None is waived.
5. Separately authorized operational preparation/adoption/selection/publication/
   freeze tools and trusted phase/seal/approval producers. Future operational
   selection must enforce applicable adoption/reconciliation gates. Freeze 2/live
   runtime, cost, terms, credit and content prerequisites and accepted phase order
   remain unchanged. Freeze 1 readiness remains unestablished.

Scope receipt: evidence/verifier code, focused synthetic tests, exact schemas,
editorial changes, proposed lemma, implementation receipt and local review handoff;
one repeat real counts-only check and exclusive private receipt. No real screening,
classification, ranking/sampling, rule/input/preparation/freeze bundles, adoption,
sealing/freezes, packets, owner labeling, operational managers, reviewer/router,
Claude invocation, AWS operation or external API call. Local scoped commit only;
no push. Technical implementation is distinct from approval and authorization.

### Exact private receipt command

This ran once from the repository root. Exclusive creation intentionally stops
if the destination exists; no overwrite or recovery is authorized by this command.
It uses only the counts path, never preparation/adoption or reconciliation.

```powershell
@'
from tests import offline_guard
from pathlib import Path
from experiments.reviewer_protocol_v2.common import canonical, sha_bytes
from experiments.reviewer_protocol_v2.control_serialization import object_bytes
from experiments.reviewer_protocol_v2.selection import read_file_binding
from experiments.reviewer_protocol_v2.ledger_reconciliation import counts_receipt, RECONCILIATION_CONTRACT
try:
    assert offline_guard.is_installed()
    root = Path.cwd().parent.resolve()
    folder = 'heldout-external/reviewer-protocol-v2-offline/final-1'
    manifest_hash = '057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4'
    ledger_hash = '6b3f97d8e987b9c01d091bce8f06b3c2e691ca5e9b4b2fc567e2919d2e07b7d2'
    manifest = object_bytes(read_file_binding(root, dict(path=folder+'/manifest.json',sha256=manifest_hash)))
    assert manifest['files']['population_ledger.jsonl'] == ledger_hash
    raw = read_file_binding(root,dict(path=folder+'/population_ledger.jsonl',sha256=ledger_hash))
    receipt = counts_receipt(manifest_hash,raw)
    assert object_bytes(receipt)['counts'] == RECONCILIATION_CONTRACT['counts']
    destination = root / 'heldout-external/reviewer-v2-ledger-counts-2026-10-02-evidence-completion'
    assert destination.resolve().is_relative_to(root / 'heldout-external')
    destination.mkdir(exist_ok=False)
    with (destination/'counts-receipt.json').open('xb') as stream:
        stream.write(receipt)
    print('counts_receipt_sha256='+sha_bytes(receipt))
    print(receipt.decode('ascii').strip())
    print('exclusive_private_counts_receipt=PASS; offline_guard='+str(offline_guard.is_installed()))
except Exception:
    print('counts_receipt_failure=SANITIZED_STOP')
    raise SystemExit(1) from None
'@ | .\.venv\Scripts\python.exe -B -
```
