# Reviewer Protocol v2: bounded review remediation

Owner authorization: request attachment b6ea516b-0dbd-4025-90d2-a32ad575c706.
Claude's uncommitted report is preserved, not rewritten or committed. This document
records the remediation contract before implementation. Tests alone do not resolve
evidence gaps or establish independent acceptance; Claude must re-review.

## Evidence recovery and current decision

Owner records 051a6503-d589-48ac-a73b-4c5600623a83 and
52667d5a-d82d-4b1b-8f97-e34b000fc0e8 explicitly establish E01 as metadata only.
The current owner request reaffirms that decision. The new current-decisions.json
records this clarification outside the original input closure. It does not amend
historical design extracts or claim retrospective approval. The recovered records
reference finalized E02-E07 finite definitions but do not supply the complete
accepted regex/algorithm catalog. That normative source remains unavailable in
the supplied local accepted records (including the preserved E01 vocabulary and full
E05/E07 algorithms); it must not be reconstructed from code.
Code inspection may check a supplied catalog, not create authoritative evidence.

## Revised mechanical contracts

FreezeManifest role allowlist, InputBinding and PreparationReport v1 bytes are
preserved. Necessary encoding version proposal: HistoricalAdoption and
AdoptionInterfaceBinding become v2 because their rule/interface payload meanings
change. Old v1 proposed encodings are rejected for compatibility, never rewritten.
All newly introduced evidence record schemas remain v1. Existing canonical JSON/LF, FB path protections and raw-byte SHA-256
recipes apply. No approved flag or witness authenticates human approval.

- **RuleSpecification** (`rule-specification-v1`): exact schema, role,
  contract, source_evidence (nonempty FB array), decision_evidence (FB),
  algorithm_evidence (FB).
  Role is one of the three rule roles. Eligibility contract has normalization,
  rule_dispositions E01-E07, precedence and finite_patterns (full regex pattern/
  flags mapping), Exposure/grouping contract has
  direct_pair_only=true, transitive=false, threshold_hex=(0.9).hex(), native_group
  and comparison. The algorithm FB is separate from the contract hash
  to avoid a reference cycle. Each source/algorithm FB must be
  typed RuleTextEvidence: schema, role, record_reference, contract_sha256, text.
  This is evidence binding/content checks, not authentication of semantic approval.
  Exposure quote data cannot satisfy this schema. Finite matcher comparison uses
  code only as a consistency check; actual normative text must be supplied.
- **RuleApplicability** (`rule-applicability-v1`): exact schema, role,
  historical_implementation_sha256, historical_source {filename,sha256},
  current_source FB, original_evidence (nonempty FB array in original closure),
  specification FB (current, outside closure permitted), decision_evidence FB,
  semantic_review_evidence FB, reconciliation. Reconciliation is exactly
  CURRENT_E01_METADATA_CLARIFICATION for eligibility or UNCHANGED_POLICY for
  exposure/grouping. A typed ReviewEvidence (schema, subject_sha256,
  record_reference, reviewer, recorded_utc, note) must reference the specification.
  Explicit historical/current hashes replace the implicit byte-equality assumption;
  divergence is recorded, not silently treated as equivalent. Normative specification
  bytes no longer need to equal historical evidence bytes. Review declarations
  remain externally reviewable; their authorship/approval is not authenticated.
- **Remaining interfaces:** replace lone specification with an exact map of control,
  trial_presentation, owner_audit and analysis_population FBs. Each typed interface
  specification has schema, kind, contract and source_evidence FBs. Contract binds
  accepted counts/seeds/roles, raw annotation/abstention/context invariants and
  analysis inclusion populations. Verification closure includes owner_audit.py,
  analysis.py and the new pure evidence validator in addition to prior dependencies.
- **SyntheticTestManifest:** exact schema, sources (complete current closure hash
  map), tests (complete declared v2 test hash map), code_bundle_sha256. All source
  and test bytes are checked against installed paths and workspace copies. This
  binds coverage, not proof a test run passed.
- **DefinitiveExclusionPolicy:** exact schema, population/ledger/inventory FBs,
  context_groups_sha256, direct_pair_only, transitive, threshold_hex,
  native_group, eligible_disposition, selection_comparison, decision_evidence FB.
  Bind ledger projection [{source,context_group,cand_id}] in original ledger order,
  direct pair >=0.90, native groups separate, SCREEN_PASS and diversity <0.90.
- **DesignApprovalEvidence:** exact schema, actor, recorded_utc, record_reference,
  authority_evidence FB, subjects map. Subjects bind every frozen role except this
  evidence role and historical_integrity_manifest (acyclic), with hash equality.
  The referenced current decision record is typed and explicit. This validates
  declaration bindings only; it never authenticates owner approval.
- **SelectionSpecification:** exact schema, seed, strata, rank_domain,
  external_id_domain, tie_breakers, threshold_hex, comparison and shortfall.
  Match the accepted constants and fail on arbitrary text or altered quotas.
- All new object schema names use reviewer-protocol-v2-<name>-v1, with exact
  field allowlists. CurrentDecisionEvidence contains schema, record_reference,
  record_sha256, historical_amendment=false, decisions (exact E01/rule_evidence/
  runtime values above), approval_authenticated=false. Text/ref strings must be
  nonempty, UTC timestamps exact YYYY-MM-DDTHH:MM:SSZ and valid dates.

## Preparation and operational boundary

Keep PreparationReport v1 PREPARED as a technical status. Necessary API proposal:
validate_preparation returns a typed technical-preparation-assessment-v1 object
containing schema, binding, report_sha256, inputs_sha256, freeze1_sha256, verification_level (BINDING_ONLY or
EVIDENCE_REPLAYED), approval_assessed=false and operational_readiness=false.
With a Freeze 1 hash it requires complete verification_context and replays prepare,
comparing independently generated report/binding bytes. A forged report alone
cannot stand in for evidence validation. No existing serialized report is rewritten.

The accepted pure select_bound_inputs API remains public and is not an authorization
gate. A new pure future selection-phase predicate requires an EVIDENCE_REPLAYED
assessment with a proposed Freeze 1 binding, phase FREEZE_1_LEDGER_SEALED,
matching input/procedure/seal hashes and a separately supplied trusted authorization
digest. Typed authorization has schema, operation (SELECTION or
SELECTION_AND_PUBLICATION), inputs_sha256, freeze1_sha256, ledger_seal_sha256,
procedure_sha256 and destination_policy FB. Predicate failure returns false and
invokes nothing. Its phase/seal/trust inputs must eventually come from independently
verified operational tools; this task implements no such tool or execution history.

## I/O, dependencies and source checks

Selection/similarity verification will parse the same captured buffer it hashes.
Keep path-returning verify_input_binding compatibility but add a captured-buffer
internal path for preparation. File-binding reading must hash and return one read.
Equivalent new-verifier reads are checked likewise. This fixes verified-buffer
parsing, not hostile-process protection across a whole procedure.

Validate every absolute repository import against the complete declared closure,
including lazy imports; reject relative imports, importlib loading, __import__,
exec/eval, dynamic loaders and unsupported aliases/getattr loading. Stdlib module
names are dependency evidence, not network safety: socket/urllib/subprocess remain
under the existing offline guard, not automatically "safe" because stdlib.
Check loaded module origins against expected source paths, accurately describing
this as origin/disk checking, not loaded-bytecode attestation. Runtime remains the
exact nine-field contract; OS changes require reviewed replacement evidence.

Compatibility becomes false once supplied Freeze evidence and historical provenance
are present, including failures before _freeze. Sanitize LookupError and
RecursionError without echoing exception data. The local provider schema is not
a Freeze 2 provider envelope and must not be repurposed as one.

## Findings and validation receipt

These are writer dispositions, subject to Claude re-review. Passing synthetic tests
does not establish actual evidence approval or operational readiness.

| Finding | Disposition and remaining limitation |
|---|---|
| 1. Rule authority / E01 | Confirmed defect: typed rule text and applicability now replace arbitrary data and historical byte equality. Recovered owner decisions establish metadata-only E01. Complete authoritative finite-rule text remains unavailable; no production rule evidence is approved here. |
| 2. Procedure coverage | Confirmed defect: closure now includes owner audit, analysis and evidence validation; four exact interface specifications cover their procedure families. Actual specification/content approval remains separate. |
| 3. Preparation / selection boundary | Report evidence can now be replayed and assessed explicitly. The accepted pure selector stays public. A separate pure phase predicate fails closed, but no operational authorization manager exists. |
| 4. Hash-only evidence roles | Confirmed defect: test, policy, design and selection evidence receive typed content/reference validation. Declarations do not authenticate approval or prove tests ran. |
| 5. Import bypasses | Demonstrated dynamic loaders and undeclared repository imports, including lazy imports, are rejected. Static inspection is not hostile-process or execution attestation. |
| 6. Verify/reread | Confirmed defect: selection inputs and similarity source are parsed from the same captured bytes that were hashed. Selection algorithms and serialization domains are unchanged. |
| 7. Executing-source limitation | Module origins plus installed/workspace/supplied bytes are checked. This is disk/origin checking, not attestation of loaded instructions or past execution. |
| 8. Runtime strictness | Owner decision retained: all nine runtime fields must match; an OS change needs reviewed replacement evidence. |
| 9. Compatibility / sanitized failures | Compatibility becomes false after verified provenance with a supplied proposal, including subsequent bundle failure; LookupError and RecursionError are sanitized. |
| 10. Old/current rule join | Explicit historical implementation/source, current source, original evidence, normative specification and semantic-review references replace the implicit join. Semantic equivalence is not inferred. |
| 11. Provider schema boundary | Documented latent integration constraint: the local validation schema is not an approved Freeze 2 provider envelope. No provider invocation or schema migration occurs. |
| 12. Derivable witness | Typed subject-bound review declarations replace the automatic witness. Actual independent semantic review and authenticated owner approval remain external prerequisites. |

### Exact validation commands

Commands run from the repository root with its existing virtual environment:

```powershell
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_review_remediation.py tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py -q --basetemp=.pytest_cache/reviewer-v2-remediation-focused-03
$remediationTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' -and $_ -notmatch 'test_reviewer_v2_regression\.py$' })
& .venv\Scripts\python.exe -B -m pytest @remediationTests -q --basetemp=.pytest_cache/reviewer-v2-remediation-regressions-02
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_adoption_encoding.py::test_complete_positive_and_deterministic_bytes -q -s --basetemp=.pytest_cache/reviewer-v2-remediation-reproduction-01
.venv\Scripts\ruff.exe check experiments/reviewer_protocol_v2 tests/test_reviewer_v2*.py
.venv\Scripts\ruff.exe format --check experiments/reviewer_protocol_v2/common.py experiments/reviewer_protocol_v2/similarity.py experiments/reviewer_protocol_v2/ledger_adoption.py experiments/reviewer_protocol_v2/production_preparation.py experiments/reviewer_protocol_v2/procedure_evidence.py tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py tests/test_reviewer_v2_review_remediation.py
git diff --check
```

Results: focused 113 passed; permitted v2 regressions 528 passed (27 new remediation
cases); deterministic reproduction 1 passed; Ruff check and eight-file format check
passed. Existing pytest asyncio_mode warning remains. Offline guard intercepted
four deliberately attempted network operations in the full suite; none were sent.
The one excluded legacy test, test_accepted_population_regression, reruns real
population screening and is prohibited by this task. Its test file remains bound
in the 13-file test manifest; hashing it is not a claim it ran in this task.
The minimal selection.py I/O patch preserves its legacy formatting.

### Replacement bundle and synthetic evidence hashes

The existing canonical filename-to-file-hash map recipe is retained. Earlier
receipts and original artifacts retain their original digests. Three shared I/O
sources changed, so current bundles necessarily receive new hashes:

| Bundle | SHA-256 |
|---|---|
| Verification, 16 sources | `854f7754af573a0604e9f5e2051e3b024273f038e18c3f890d61204430322322` |
| Selection, 7 sources | `1afa90ffc0b9389818c2c0a85b6d873f1896828cfea6178965f1d06df193b5ca` |
| Control/trial, 10 sources | `0837b7358abb11f9a68531ca78b61696d2167ba6a2ad724fe49e6c5f2dcfc151` |
| Owner/analysis, 12 sources | `5d91fb46bbdff29538ce56228f5c1f46525ff9f37803fcdcfc9ac2586e042427` |
| Original historical generating bundle, unchanged | `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc` |

Two invented workspaces reproduced identical canonical bytes and hashes:

| Synthetic artifact | SHA-256 |
|---|---|
| Proposed Freeze binding | `d6d5eef937c1cb3a8b729d2bb4ad4ac5bc184415aea7e5f73846db58028663af` |
| Procedure | `55272b8688cba12f2330d423a5c7b890400a1791de9c494c42f410552481ea92` |
| Preparation report | `1b7a7149b1c4628963d49940667968b48212a21ef1a5977382acacd0bf8a5667` |
| Technical compatibility result | `4527da73c3ad6b2727fc277e837d786f8cdad62665b2f11a5981854cda70115a` |

Read-only original integrity validators confirm 107 protected files and 72
historical bindings. Original pin digest remains
`ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae`;
final1/final2 manifest remains
`057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4`.
Claude's report remains byte-identical, SHA-256
`caba9fc167d372f95414e5f6d37e3b901f0c6b03e98ec8ba879f4bb7c5254f9b`.
No real artifact was passed to the new preparation/adoption APIs.

### Consolidated re-review handoff and prerequisites

Review the original milestone range 182f131 through c845b31 together with this
remediation commit. Preserve the original Claude report as the finding baseline.
Changed source inventory: common.py, similarity.py, selection.py (captured-buffer
I/O only), ledger_adoption.py, production_preparation.py and new
procedure_evidence.py. Tests: preparation, adoption_encoding and new
review_remediation. Documents: current-decisions.json, this specification/receipt
and the prior preparation receipt's supersession notice. Exact replay commands
appear above; do not run the excluded real-screening test under this authorization.

Re-review priorities: rule authority/applicability and E01 reconciliation; complete
owner/analysis procedure coverage; typed evidence roles; dependency bypasses and
same-buffer parsing; technical assessment versus operational authorization. Inspect
actual reference joins and fail-closed behavior, not just test totals. There is no
new independent-review acceptance in this receipt, and Claude was not invoked.

Consolidated remaining prerequisites:

1. Recover the actual accepted finite normative rule/specification text and its
   provenance, including preserved E01 vocabulary and E05/E07 algorithm details;
   obtain explicit semantic reconciliation/review of applicable current specs.
2. Complete Claude re-review of all milestones and this remediation; independently
   approve actual procedure/design/exclusion evidence and control content/rubrics.
3. Satisfy actual Freeze 1 runtime/dependency, source, inventory, input and complete
   procedure evidence requirements. Original runtime remains CPython 3.13.12 /
   Unicode 15.1.0, separate from current nine-field runtime lock. No historical
   unrecorded platform or SDK facts are inferred.
4. Implement/review operational preparation, adoption, sealing, authorization,
   publication and freeze tools under separate authorization. Trusted phase,
   approval and seal evidence must come from those tools; this predicate executes
   no operation. Technical compatibility never certifies Freeze 1 readiness.
5. Preserve the accepted sequence: Freeze 1, production-ledger adoption/seal,
   authorized selection/publication, then Freeze 2/live prerequisites. Runtime,
   cost, terms, credits, provider-envelope review and reviewer/router authorization
   stay in their accepted phases; none is waived or reassigned here.

Scope receipt: synthetic verifier remediation, focused tests and local documentation
only. Historical bytes and unrelated work preserved. No real screening, preparation,
bindings, adoption, ranking, IDs, sampling, packets, operational seal/freeze, owner
labeling, reviewer/router invocation, cloud operation or external API call; no push.
