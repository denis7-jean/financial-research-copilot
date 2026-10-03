# Focused independent review request: evidence completion after bf8295b

This is a local handoff only. Claude has not been invoked or messaged. Review and
acceptance of this delta remain pending. No actual evidence wrapper is approved,
historical ledger adopted, execution authenticated or Freeze 1 readiness claimed.

Review the scoped delta against bf8295b (working tree until the authorized local
commit is permitted) and its following documents:

- reviewer-protocol-v2-evidence-completion.md: exact schemas, byte preimages,
  verification order, explicit mechanical additions, commands, receipt and blockers.
- reviewer-protocol-v2-ledger-reconciliation-lemma.md: separately hash-bound proposed
  proof; raw SHA-256 febaf27765974a35798e27652af90267978a4af6294821f718b3701d97c9f7ef.
- current-rules-v1.md: exactly the two S-3 editorial corrections. New raw SHA-256
  4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7.
  Prior bytes remain in bf8295b; current companion metadata references the new hash.

## Requested checks

1. S-1: compare every mechanical addition with the normative document and accepted
   source/owner chain. Check the sorted 42 literal E05 phrases, terminal marks,
   whole-q/full-span semantics, eight E07 conditions, original/reference metadata,
   row invalidation versus aborts, exact normalization order, D4 evaluability,
   NOT_EVALUABLE and E06 independent evaluation. Code-derived mechanical equality
   is not normative authority or proof of faithful extraction.
2. S-2: ReviewEvidence v4 and RuleApplicability v3 must verify captured normative
   document bytes, require identical FBs across all three roles and their reviews,
   and reject obsolete versions. Preserve raw original record versus extraction,
   algorithm, specification, contract, normative document and review subjects.
   Shared-origin/source-section review remains required. InputBinding and
   FreezeManifest envelope/role allowlist remain unchanged.
3. S-3: inspect the two editorial-only replacements: neutral inventory attribution
   and S-576 literal-list locator 283-329. Other normative bytes are unchanged.
4. Lemma: independently inspect the complete three-hunk source diff and source
   provenance. Historical d3030b22... versus current 04e36326... is pinned. Verify
   the according-to substring/boundary argument and non-overlapping finditer
   existence argument; distinguish row-object equality from disposition/capacity.
   The proof assumes ledger fidelity to old execution and unchanged reference/
   runtime inputs; counts and hash agreement do not establish historical execution.
   The 324 invented probes are illustrations, not an exhaustive proof.
5. Typed reconciliation: inspect the pinned identified manifest/ledger/digest/source
   transition/lemma, all historical/current bundle and source FB joins, review
   subject preimage excluding only its review FB, contract/lemma/count hash joins,
   and raw review-record hash. Hashes do not authenticate reviewer independence,
   authorship, human approval, semantic correctness or replay trust.
6. Counts: recount only stored fields from the same captured hashed ledger buffer.
   Require 104 total and zero E03/E03c union/empty-reason rows; do not trust declared
   counts. The private receipt has schema and hashes/counts only, SHA-256
   584d43ad6a02f7cdffa345a1fd92da04f9eef0ec72bc2b82dafed89ba82c417b.
   The production verifier was tested only with invented subjects, never this
   ledger. There are no assembled actual reconciliation/review wrappers.
7. Boundary/failure paths: absence retains E03C_LEDGER_RECONCILIATION_REQUIRED;
   invalid supplied evidence also fails. No generic equivalence/approval flag or
   production TARGET override exists. Check remaining runtime, dependency, input,
   inventory and specification checks still execute. Synthetic tests monkeypatch
   TARGET explicitly; that is a test technique, not an operational input.
8. Dependency/safety: new pure ledger_reconciliation.py expands current verification
   to 17 source files and test coverage to 14 files. No new third-party dependency
   or static-checker allowance. Confirm no reachable classification, ranking, ID,
   packet, write, publication, operational adoption/sealing/freeze hooks. The pure
   selector remains unchanged; future operational tools must enforce these gates.

## Scoped inventory and validation

Code: procedure_evidence.py, ledger_reconciliation.py, ledger_adoption.py (one
forwarded verified context), production_preparation.py (one source-bundle member).
Tests: new test_reviewer_v2_evidence_completion.py, two existing fixture helpers in
test_reviewer_v2_adoption_encoding.py and test_reviewer_v2_preparation.py.
Documentation: current normative document and companion hash metadata, proposed
lemma, exact schema/implementation receipt and this handoff; one narrow
.gitattributes entry preserves the lemma's raw bytes.

Exact commands are in the implementation receipt. Focused 391 passed; permitted
v2 regressions 665 passed / one real-population test deselected, including 56 new
tests. Ruff and seven-file formatting passed. Four deliberate network probes were
intercepted in the full run, none sent. Existing asyncio_mode warning remains.
The pure selector's golden serialization outputs and API are unchanged.

Current verification digest (17):
1ad392707e99ca25ce16275bcef27f9ed737bb2aae1c9a3767d189f30a619dd4.
All three other current bundle digests are unchanged (see receipt). Historical
generating digest and all prior receipts remain separate and unchanged. All four
Claude reports remain unchanged/uncommitted. Private original evidence and
historical artifacts are untouched; the only new private artifact is counts-only.

Remaining prerequisites: this independent delta/lemma review; actual raw-record,
normative/specification/review/applicability and reconciliation wrappers reviewed
as assembled; actual content/rubric/design/interface/exclusion-policy approvals;
complete applicable Freeze 1 evidence; separately authorized operational tools and
trusted phase/approval/seal producers; unchanged Freeze 2/live prerequisites and
accepted phase sequence. Supplementary-registration/execution and S-576
complete:false limitations persist. No prerequisite is waived.
