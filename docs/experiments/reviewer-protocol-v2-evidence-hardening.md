# Reviewer Protocol v2: evidence hardening and residual fixes

Contract recorded before implementation. Owner accepts Claude's technical
conclusions on b328fdb within their stated scope; Freeze 1 readiness remains
unestablished. Both Claude reports remain unchanged and uncommitted.

## Proposed exact evidence delta

Existing FreezeManifest roles, InputBinding, PreparationReport, historical adoption
envelope and selection bytes remain unchanged. Canonical JSON is sorted keys,
ASCII escaping, compact separators, no NaN, UTF-8 with one final LF. H denotes
raw-byte SHA-256, 64 lowercase hex digits; FB is exact {path,sha256}. Original
records are hashed as raw bytes, never normalized or reconstructed. All referenced
record paths pass the existing approved-root/resolved-path protection. Evidence
adapters hash and return one buffer. Extracted text is not original-record bytes.

- RuleTextEvidence **v2** exact keys: schema, role, record_reference (nonempty
  locator), record_path (safe relative path), record_sha256 (H), contract_sha256
  (H), text (nonempty extracted text). Read record_path and compare raw bytes to
  record_sha256. Check contract_sha256 against H(canonical(contract)). Source
  evidence uses only this schema.
- RuleAlgorithmEvidence **v1** has the same keys with schema
  reviewer-protocol-v2-rule-algorithm-evidence-v1. Algorithm evidence must use this
  distinct schema and a different wrapper FB from every source-evidence entry.
  Source and algorithm wrappers may cite one shared original document; no duplicate
  document copies may pretend to provide independent provenance.
- RuleSpecification **v2** exact keys: schema, role, contract, source_evidence
  (nonempty RuleTextEvidence FB list), algorithm_evidence (RuleAlgorithmEvidence FB),
  decision_evidence (existing FB), shared_origins (FB list). Shared origins are
  exactly the raw-document hashes shared between algorithm and source evidence,
  with the same canonical record path and locator. Require one entry per shared
  hash, sorted by hash. Equal raw hashes with different paths or locators are
  rejected as origin aliases. Empty shared_origins is required when no origin is
  shared. Neither two extracted wrappers nor two byte-identical originals count
  as independent source provenance.
- ReviewEvidence **v2** exact keys: schema, subject_sha256 (specification wrapper
  H), contract_sha256 (H(canonical(contract))), record_reference, record_path,
  record_sha256, reviewer, recorded_utc, note, shared_origin_reviews. Raw review
  record bytes are verified. Each shared_origin_reviews entry is exactly
  {record_path,record_sha256,supports_both_roles,note}; supports_both_roles is true,
  note nonempty, order and origins match shared_origins exactly. This explicitly
  requires a declaration that the original supports both source and algorithm
  roles. Authorship, approval and semantic correctness remain external.
- Interface specifications retain their envelope and use RuleTextEvidence v2 for
  source evidence. Owner explanatory_note token becomes
  KEY_REQUIRED_NONEMPTY_IF_ABSTAINED_OR_CONCERN; a behavior test ties it to the
  existing audit validator. Other contract tokens remain consistency labels.

Verification order: validate canonical wrapper and exact schema; verify raw record
bytes and contract hash; validate distinct source/algorithm roles and shared-origin
map; validate existing original/current applicability joins; then verify review raw
bytes, subject, exact contract hash and shared-origin review declarations. A copied
hash declaration alone is insufficient. Semantic relevance and text transcription
are reviewed externally; no parser pretends to authenticate meaning or authorship.

## Static source and phase predicate delta

The checker is static checks on reviewed, hash-bound source, not a Python sandbox
or universal dynamic-code guarantee. Reject attribute exec/eval/compile and names
vars/globals/locals, alongside existing loader restrictions. Restrict stdlib module
attributes/imported members to explicitly reviewed access names. sys.modules is
allowed only as the exact sys.modules.get(module_name) call assigned to module in
_executing_sources in production_preparation.py. Reject aliases to module objects,
unsupported sys.path/meta_path/path_hooks, and re-exported module accesses.

SelectionAuthorization **v2** exact keys: schema, operation, inputs_sha256,
report_sha256, freeze1_sha256, ledger_seal_sha256, procedure_sha256,
destination_policy. Existing types/allowlists remain, adding report_sha256=H.
Predicate verifies H(canonical(assessment.binding))=assessment.inputs_sha256,
and grant.report_sha256=assessment.report_sha256. v1 grants fail closed. Replay
authenticity, phase evidence and trusted authorization hash remain supplied by
future independently reviewed operational tools. No such tool is implemented.

R4 limitation is recorded from Claude's independent inspection: through b328fdb,
similarity algorithms were unchanged and common.decode changed failure handling.
Unequal hashes do not automatically establish non-normative change. No semantic
diff framework or new source_relation inference is introduced here.

## Recovery, validation and delta-review receipt

### Targeted evidence recovery

The earlier inaccessible-source conclusion is narrowed by newly recovered session
evidence. The original finite-rule specification response is preserved from the
2026-09-30 session, exact JSONL response record at line 576, followed by the owner
051a6503 decision at line 583. It contains the E01 vocabulary and E01-E07 rule
sections, including E05/E07 algorithm sections. Owner attachment 051a6503 supplies
clarifications; 52667d5a accepts the subsequent authoritative audit. Original
proposal wording and later decision evidence must be reconciled explicitly; the
original proposal alone is not the finalized current normative specification.

Checked locations: all already accessible attachment text files for finite-rule
and E01/E05/E07 references; the matching 2026-09-30 and 2026-10-01 session records;
archived_sessions for the cited record identifiers; relevant tracked project
design/specification receipts. No real population files were inspected. No separate
finalized post-clarification finite-rule specification artifact was located. The
missing deliverable is therefore a reviewed current transcription/applicability
reconciliation of the recovered response and owner decision chain, not a replacement
invented from PATTERNS or fixtures. Evidence recovery stops at original records.

Private bytes are preserved outside Git at
`C:/Projects/AWS Project/data/reviewer-v2-evidence-recovery/2026-10-02`.
The [metadata-only inventory](reviewer-protocol-v2-recovered-records.json) records
exact locations, raw hashes, byte lengths, original-record provenance and the
explicit extraction recipe. No private text enters Git or user-facing logs.

| Original / derived record | SHA-256 |
|---|---|
| Owner 051a6503 | `80bd0ac8420571031e02aa28cf1e4b7a9e982cea872baadb25ccc4f1e33352c1` |
| Owner 52667d5a | `c33feb84248ada1425d5eda8a954d4679f12010d644d6590aa88f8eac9044c1d` |
| Owner b6ea516b | `314c8fa0919eacab7e2787f4f45febd95e3ad9fac1517b4f386d3a0c6d0d3cc7` |
| Earlier owner 430d7fe2 | `767de137e4d1d6c1577871a7ab3644838eabb32884324eaf665bb3144866786e` |
| Original specification response JSONL record | `7e481873256e5e1e3684d19fc36199baf093202cf23404338b90bcbf625b4a3f` |
| Derived text extraction, not original bytes | `539541e3a3f28885a4be3c1e3d27171ca45bb6a30980cdad3b818933c7e49373` |
| Private preservation manifest | `8e84755db4b5a90388d79746ba10bd25f1d857a49e42e0c8d90aba7b7a62159f` |

The old current-decisions.json remains unchanged; its b6ea516b hash now has a
preserved raw source. The recovered records are evidence preservation only, not
production InputBinding artifacts, verified real preparation or adoption evidence.
They were not passed to the new verifier APIs. Source hash agreement does not
authenticate authorship, approval, semantic correctness or execution history.

### Fix disposition and verification

| Residual | Writer disposition for delta re-review |
|---|---|
| R1 | Raw record bytes are verified for source, algorithm and semantic-review evidence; reviews bind exact contract hash. Distinct typed wrappers and shared-origin review prevent copied records from silently implying independent provenance. Meaning/authorship remain external. |
| R2 | Exact reported probes reject with specific codes. Explicit stdlib member allowlists and the single scoped sys.modules.get AST exception replace broad access. Re-export and function-global access probes reject. Static checks are not a sandbox. |
| R3 | Canonical assessment binding hash and grant report hash are checked. Authorization v2 rejects v1. A coherent invented assessment may still satisfy a structural predicate; trust and actual replay authenticity remain external. |
| R4 | Recorded Claude's independently inspected non-normative similarity/common changes through b328fdb. Those modules are unchanged here. No automatic semantic classification from hashes. |
| R5 | Corrected note-policy token; all four abstention/context combinations and missing note key tested against actual existing audit behavior. |
| R6 | Hash-only role tests now require schema_keys, alongside explicit rejection codes for the new record, review, dependency and shared-origin failures. |

Commands from the repository root:

```powershell
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_review_remediation.py tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py -q --basetemp=.pytest_cache/reviewer-v2-hardening-focused-02
$hardeningTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' -and $_ -notmatch 'test_reviewer_v2_regression\.py$' })
& .venv\Scripts\python.exe -B -m pytest @hardeningTests -q --basetemp=.pytest_cache/reviewer-v2-hardening-regressions-02
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_adoption_encoding.py::test_complete_positive_and_deterministic_bytes -q -s --basetemp=.pytest_cache/reviewer-v2-hardening-reproduction-01
.venv\Scripts\ruff.exe check experiments/reviewer_protocol_v2 tests/test_reviewer_v2*.py
.venv\Scripts\ruff.exe format --check experiments/reviewer_protocol_v2/procedure_evidence.py experiments/reviewer_protocol_v2/ledger_adoption.py experiments/reviewer_protocol_v2/production_preparation.py tests/test_reviewer_v2_adoption_encoding.py tests/test_reviewer_v2_review_remediation.py
git diff --check
```

Final permitted v2 regressions: **574 passed**, including **46 new cases** beyond
b328fdb. Earlier focused-02: 154 passed before the final five cases were added;
those five are covered by the final full run. Deterministic reproduction: 1 passed.
Ruff, five-file formatting and whitespace checks passed. Existing asyncio_mode
warning remains. Four intentionally attempted network operations were intercepted
by the offline guard in the full suite; none were sent. Excluded only the legacy
test_accepted_population_regression, which re-screens real data. Its file remains
hash-bound by the synthetic test manifest, not claimed as executed here.
No-write/no-operational-hook checks replay preparation and compatibility on invented
workspaces with writes, ranking, IDs and packet builders patched to fail.

### Current and synthetic digests

Only ledger_adoption.py, procedure_evidence.py and production_preparation.py change
current source bytes. The 16-source verification digest changes to
`083041b21ffe05e77fdd5ae58f34ebae74ee3af173b22e93ac1adef25fcbfd83`.
Other current bundles retain their b328fdb hashes:

| Bundle | SHA-256 |
|---|---|
| Selection, 7 | `1afa90ffc0b9389818c2c0a85b6d873f1896828cfea6178965f1d06df193b5ca` |
| Control/trial, 10 | `0837b7358abb11f9a68531ca78b61696d2167ba6a2ad724fe49e6c5f2dcfc151` |
| Owner/analysis, 12 | `5d91fb46bbdff29538ce56228f5c1f46525ff9f37803fcdcfc9ac2586e042427` |

Two invented roots reproduce the same bytes:

| Synthetic artifact | SHA-256 |
|---|---|
| Proposed freeze binding | `1ae999da4bb5f36ec8bd241aeb29dae3c28171663944194d389ae50fcd75e539` |
| Procedure | `3f5a491c16714c6993bd71ff739dbca6070b106f08c09b763487b553b27ef384` |
| Preparation report | `f0885c3dc1c876ef4c83c471a1d0e889ed10632fcea3fa0aceab37ad07fdd6cf` |
| Technical compatibility result | `4527da73c3ad6b2727fc277e837d786f8cdad62665b2f11a5981854cda70115a` |

Original historical sources/artifacts and all earlier receipts remain unchanged.
The prior historical generating hash `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`
is retained as recorded evidence, not recomputed through real APIs in this task.
No historical artifacts were regenerated.
Both uncommitted reports retain their exact hashes:
original `caba9fc167d372f95414e5f6d37e3b901f0c6b03e98ec8ba879f4bb7c5254f9b`;
re-review `5af319094d26a09e1145349fb733b56200117da396b637eb3852b8a0dd99589c`.

### Delta-review handoff and prerequisites

Review this commit against b328fdb using both preserved Claude reports. Scoped
inventory: three verifier sources named above; adoption_encoding and
review_remediation tests; this contract/receipt and the metadata-only recovery
inventory. Inspect raw-record reads, schema-version rejection, exact contract and
shared-origin joins, R2 exception shape/allowlists, and R3 binding/report checks.
Replay the final full and reproduction commands above. The positive fixtures are
invented, not approval evidence. No Claude invocation or message occurred here.

Remaining: independent delta review; reviewed current normative transcription and
applicability reconciliation of recovered originals; actual semantic/design/content,
rubric and procedure approvals; actual runtime/dependency and other Freeze 1
evidence; separately authorized operational tools and trusted phase/seal/approval
producers. Keep the accepted sequence and phase allocations unchanged. Freeze 1
readiness remains unestablished.

Scope receipt: bounded synthetic evidence-verifier corrections, tests, documentation
and owner-authorized original evidence preservation outside Git. No real population
inspection/screening, preparation/bindings, ranking/sampling, production packets,
adoption/sealing/freezes, owner labeling, operational managers, reviewer/router,
AWS operation or external API call. Local scoped commit only; no push.
