# Bounded evidence cleanup after f9e19b6

Baseline: f9e19b674e126601ba8d64ef65db1fe2d41a8e23. Owner-authorized cleanup only;
actual evidence-wrapper assembly remains a separately authorized next task.

## Exact interface delta

EC-1: the owner-selected NORMATIVE_DOCUMENT_ID / NORMATIVE_DOCUMENT_SHA256 pair
is reviewer-protocol-v2-current-rules-v1 /
4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7.
rule_bindings first retains the existing raw-byte/safe-path check, then requires
this exact hash with RULE_NORMATIVE_DOCUMENT_IDENTITY, then retains cross-role
and review joins. A consistently substituted document is insufficient. This pin
is a version identity, not authenticated approval or code-derived authority. A
future version requires an independently reviewed replacement anchor. No runtime
argument replaces this pin. Wrapper versions/fields, FreezeManifest roles and
InputBinding remain unchanged.

Eligibility contract changes (mechanical descriptions of unchanged behavior):
- ledger_preservation has exactly rule_ids=ASCENDING_RULE_ID_ORDER,
  subrule_identifiers=PRESERVED, normalized_match_spans=PRESERVED,
  e07_reasons=PRESERVED, winning_disposition=NEVER_ERASES_OTHER_FINDINGS,
  e01_prevalence=REPORTED_SEPARATELY.
- text_evaluable.blocks explicitly includes NONOBJECT_JSON.
- text_rule_evaluation covers rules=[E01,E02,E03,E04,E05,E06],
  usable=ALL_REGISTERED_TEXT_RULES_INDEPENDENT_EVEN_ON_METADATA_INVALID_ROWS,
  non_evaluable=NOT_EVALUABLE_NO_MATCHES_INCLUDING_EMPTY_VIEW. These shared
  descriptions replace the misplaced e06_evaluation usable/non_evaluable fields.
- E06-specific bracketed, delimiter_forms, nested and higher_precedence tokens
  are unchanged. All other contract fields remain unchanged.

Current mechanical equality and hashes describe implementation consistency, not
independent rule authority. Obsolete mechanical contracts fail exact equality;
old contract hashes cannot be used for the forthcoming actual wrappers. Exposure
and grouping/similarity contracts stay unchanged. Source/matcher/audit behavior,
normalization, precedence, serializers and reconciliation policy are unchanged.

## S-576 locator clarification

“S-576 lines 283–329” means one-based lines of the **derived extraction**
specification-response-extracted.txt, SHA-256
539541e3a3f28885a4be3c1e3d27171ca45bb6a30980cdad3b818933c7e49373.
The recorded extraction recipe is exactly: “UTF8 of JSON content text fields joined
by LF; no added final LF”. This is not a locator into the session container or the
single-line original JSONL record.

The **original raw record**, specification-response-record-576.jsonl, separately
has SHA-256 7e481873256e5e1e3684d19fc36199baf093202cf23404338b90bcbf625b4a3f;
its original trailing LF is included. The recipe and relationship are recorded
in the preserved recovered-record inventory. The original record and extraction
remain byte-identical and distinguishable; neither is rewritten or re-extracted.
The current normative document remains byte-identical at its owner-selected hash.
Its text is not changed to add this clarification. complete:false and the
historical-registration/execution limitations persist.

## Synthetic regression coverage

The durable tests cover non-eligibility reconciliation roles
(RULE_RECONCILIATION_ROLE); invalid UTC parsing/offset/round-trip forms
(RECONCILIATION_REVIEW_UTC); counts paths outside allowed roots or traversing
parents (relative_path); and missing generating context
(RECONCILIATION_GENERATING_EVIDENCE_MISSING). They also cover a valid synthetic
technical baseline, consistent substituted document rejection, the shipped owner
pin and the mechanical description's correspondence to preserved synthetic
findings. No real candidate data enters the preparation/adoption/reconciliation
APIs. Test-local monkeypatch replaces the document pin with an invented document's
hash only where synthetic positive fixtures require it, just as the existing
reconciliation fixtures substitute TARGET. No production override is exposed.

The synthetic test-manifest source list adds test_reviewer_v2_evidence_cleanup.py.
Current verification remains 17 source files; only procedure_evidence.py changes
among them. No dependency installation, new source dependency, static-loader
guarantee, authorization redesign or operational manager is introduced.

## Scoped inventory

Exactly six files; no evidence wrappers or private content are included:

| File | Change |
|---|---|
| experiments/reviewer_protocol_v2/procedure_evidence.py | Owner version pin, eligibility descriptions, synthetic test-source registration |
| tests/test_reviewer_v2_adoption_encoding.py | Invented document identity fixture |
| tests/test_reviewer_v2_review_remediation.py | Import invented identity fixture; isolate origin mock restoration so it preserves that fixture |
| tests/test_reviewer_v2_evidence_completion.py | Import fixture; use shared evaluation field in existing assertion |
| tests/test_reviewer_v2_evidence_cleanup.py | 14 synthetic cases covering the cleanup |
| docs/experiments/reviewer-protocol-v2-evidence-cleanup.md | This receipt and review handoff |

## Validation commands and results

From C:/Projects/AWS Project/main, using the existing environment and guard:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_evidence_cleanup.py tests/test_reviewer_v2_review_remediation.py::test_origin_check_and_exact_runtime tests/test_reviewer_v2_preparation.py -q -p no:cacheprovider --basetemp=.pytest_cache/reviewer-v2-evidence-cleanup-targeted-01 --tb=short
$cleanupTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' })
& .\.venv\Scripts\python.exe -B -m pytest @cleanupTests -k 'not test_accepted_population_regression' -q -p no:cacheprovider --basetemp=.pytest_cache/reviewer-v2-evidence-cleanup-regressions-01 --tb=short
.\.venv\Scripts\python.exe -B -m ruff check experiments/reviewer_protocol_v2 tests/test_reviewer_v2*.py
.\.venv\Scripts\python.exe -B -m ruff format --check experiments/reviewer_protocol_v2/procedure_evidence.py tests/test_reviewer_v2_adoption_encoding.py tests/test_reviewer_v2_review_remediation.py tests/test_reviewer_v2_evidence_completion.py tests/test_reviewer_v2_evidence_cleanup.py
git diff --check
```

Focused: **64 passed**. Permitted v2 regressions: **679 passed, one deselected**
(the real-population regression). Ruff passed; five scoped Python files formatted;
whitespace check passed. Existing asyncio_mode warning persists. Guard intercepted
one deliberate network probe focused and four in the full suite; none sent.
Existing selection/packet-serialization golden byte/hash vectors passed, including
test_seven_assertions_per_vector, test_combined_vector_two_assertions and
test_eight_negative_vector_assertions. Deterministic two-root synthetic records,
no-write/no-operational-hook checks and import-purity regressions also passed.

Initial diagnostics: one command named a nonexistent preparation test file and
collected no tests. The first runnable focused subset had 355 passes and one
fixture failure: monkeypatch.undo() restored the production pin as well as the
mocked source origin. Replaced it with an origin-only monkeypatch.context(); the
64-case follow-up and complete permitted suite above passed. No production check
was weakened. The new UTC/path probes cover Claude's reported failure categories;
the report did not supply the exact scratch strings, so these are invented probes.

## Replacement hashes and preserved bindings

Contract preimage: existing common.canonical(rule_contract(role)): UTF-8 JSON,
sorted keys, ensure_ascii=True, compact separators, allow_nan=False, one final LF.
Bundle preimage: existing common.canonical({relative_source_path: SHA256(raw_source
bytes)}) over the bundle's unchanged exact path set. No hash recipe changes.

| Binding | SHA-256 |
|---|---|
| Eligibility contract, replacement | 91d73119ae0f3474c350def0ef87a5850ab98e7d8489c44e09ba436f65614fa4 |
| Prior eligibility contract, historical receipt only | e69425077b073338e9beeb1ecee23518309967712697a58d60257a6ec386d49d |
| Exposure contract, unchanged | b0ca037ec36dd84f214286c281dfc162cfd2fbb593ea86833579a8b1671c507c |
| Grouping/similarity contract, unchanged | 181913badd890b7050ef2d4d23e1ea61c712569130eaaf2f7223c5b8eee8a795 |
| Current verification bundle (17), replacement | ece125e0466cd89b280221bb89b9d38389fe060c7fb19a4a35d506ff41828a28 |
| Prior verification bundle, historical receipt only | 1ad392707e99ca25ce16275bcef27f9ed737bb2aae1c9a3767d189f30a619dd4 |
| Selection bundle (7), unchanged | 0797dd5065486ecb142bed90fe7d1a74f8792e80659c1b64c9f495d71eba1187 |
| Control/trial bundle (10), unchanged | 2e4c224927c9450608afb414c4ad1f8c09932c8b8cc5be9cdc9de0eadd1fc0bf |
| Owner/analysis bundle (12), unchanged | 492d688bd937cbc68e4ccc86c0c11a4be1dfcef77423133a3c826728d8a5a2b4 |
| Normative document, unchanged | 4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7 |
| Lemma, unchanged | febaf27765974a35798e27652af90267978a4af6294821f718b3701d97c9f7ef |
| Counts receipt, unchanged | 584d43ad6a02f7cdffa345a1fd92da04f9eef0ec72bc2b82dafed89ba82c417b |
| Historical final-1 manifest, unchanged | 057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4 |
| Historical final-1 ledger, unchanged | 6b3f97d8e987b9c01d091bce8f06b3c2e691ca5e9b4b2fc567e2919d2e07b7d2 |
| Historical generating digest (16), retained | 105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc |

Read-only in-memory hashing confirmed all **49 protected files** unchanged from
the task's initial snapshot: private recovery/copy/counts evidence, raw original
and extraction, historical manifests/ledgers, normative document, lemma, five
Claude reports, proposed draft and pre-existing untracked files. No ledger objects
were inspected for this check; no counts were rerun. All fifteen existing behavior
and interface source files checked against baseline Git blobs remained byte-identical
(including eligibility, exposure, similarity, common, audit, selection, serializers,
adoption, preparation and reconciliation). Existing historical receipts stay intact;
the historical generating digest is retained, not substituted by the current bundle
and not evidence of historical execution. No new dependency or runtime claim.

## Focused Claude delta-review handoff (not sent)

Review the six-file diff against f9e19b6 and the commands/results above:
1. EC-1 pins the owner-selected version/hash after captured-byte verification and
   before existing joins; all three applicability and review roles retain their
   document joins. A consistently rehashed invented substitute must reject.
2. Confirm the ledger-preservation fields and shared E01–E06 evaluation description
   accurately describe the unchanged normative bytes and implementation. Review
   the replacement contract hash; E06-specific fields and the other contracts
   remain unchanged. No source authority or approval authentication is claimed.
3. Inspect the four reconciliation failure categories and their exact rejection
   codes, valid technical baseline, and test-local invented identity substitution.
   It supplies no production override or operational permission. Existing source
   checks remain static checks on reviewed, hash-bound sources, not a sandbox.
4. Confirm the extraction/raw-record locator distinction and preservation evidence.
   The S-576 complete:false and historical registration/execution limitations remain.

## Remaining prerequisites and scope receipt

- Independent review of this cleanup remains required; no Claude invocation occurred.
- Actual evidence-wrapper assembly is the next bounded task under separate
  authorization. It must use the replacement eligibility/verification bindings,
  distinct source/algorithm/raw-record evidence, decision/specification wrappers,
  three applicability/review wrappers, reconciliation and its independent raw review.
  Subsequent semantic review and actual approvals remain required.
- Design, exclusion policy, content/rubric, interface/test-manifest approvals and
  complete Freeze 1 runtime/dependency/input/inventory/procedure evidence remain
  distinct from these technical checks. Missing evidence is not waived.
- Operational tools and adoption/selection permissions remain separate. Preserve
  Freeze 1 → production-ledger verification/sealing → authorized external selection
  → owner audit → Freeze 2 → separately authorized live execution; later
  runtime/cost/terms/credit decisions remain in their accepted phases.

Synthetic cleanup only; explicit six-file staging and one local commit authorized,
no push. No actual wrapper assembly, real screening/preparation, ledger adoption,
ranking/sampling, packets, operational tools, seals/freezes, owner labeling, models,
AWS or external APIs. Protected evidence and unrelated work preserved.
**Freeze 1 readiness remains unestablished.**
