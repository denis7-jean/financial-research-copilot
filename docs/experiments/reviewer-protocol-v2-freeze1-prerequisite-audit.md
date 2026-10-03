# Reviewer Protocol v2: Freeze 1 prerequisite audit

2026-10-03. Inspected HEAD: `a7a6961826ce51b9d6a277aa9f0659b544064df6`, matching the owner baseline.
Read-only audit; only this document is created. No readiness, approval, adoption or execution is conferred.

**Finding:** the accepted rule/reconciliation evidence is reusable at its current bindings. Several previously described “missing approvals” are actually accepted owner decisions whose final artifact bindings have not been assembled. The full Freeze 1 path remains unassessed. Technical reconciliation enforcement exists there, but operational enforcement and trusted phase/seal/authorization producers do not exist. Settle the gate integration and its source dependencies before assembling final procedure evidence around the current digest.

## Evidence and decision references

Paths below use the established workspace root `C:/Projects/AWS Project/`, containing `main/` and `heldout-external/`. All hashes are raw-byte SHA-256 unless explicitly labeled a bundle/closure/subject digest. Existing reports and receipts describe completed checks; they were read, not replayed.

| Ref | Existing path / schema | Verified hash or source |
|---|---|---|
| F | `main/docs/experiments/reviewer-protocol-v2-claude-final-evidence-review.md`, raw Markdown, sections 1–5 and conclusions | `567fa028570c16e9448560428c2d87d86fb92928e6b176383fa915f7132115cf` |
| C | `main/docs/experiments/reviewer-protocol-v2-final-evidence-completion.md`, raw Markdown | `6e6e7026b560d1121c74ef60c96fa6f310a09d57a184ab05f914d432aec7d7b9` |
| I | `heldout-external/reviewer-v2-evidence-completion/2026-10-03-626dc09/completion-index.json`, `private-evidence-completion-index-v1` | `8365f02f6bf9373d0a125279f5213fbcf5c98c04c14abe144c6dec646bf451bd` |
| T | Same completion directory, `technical-check-receipt.json`, `private-evidence-technical-check-receipt-v1` | `9a667a477163abcc18e31a303b189a4b955855100833bbabec5d797978a47566` |
| A | `heldout-external/reviewer-v2-evidence-assembly/2026-10-03-25bde93/assembly-index.json`, `private-evidence-assembly-index-v1` | `16cc736f6dea8672c920777f8365b4c4562d47abdfd61a9858e749d307ac1f3d` |
| V | `heldout-external/reviewer-v2-evidence-reviews/2026-10-03-claude-626dc09/review-index.json`, `private-evidence-review-index-v1` | `2885f29a04437288376af9fe902a3adcd9285788bea00137c164cba463ac5dc5` |
| N | `main/docs/experiments/reviewer-protocol-v2-current-rules-v1.md`, pinned normative document | `4a76c98044146d8a6f887e0c68df2975b595eec394224510a1508cfe7b66b0b7` |
| L | `main/docs/experiments/reviewer-protocol-v2-ledger-reconciliation-lemma.md`, raw Markdown | `febaf27765974a35798e27652af90267978a4af6294821f718b3701d97c9f7ef` |
| D0 | `heldout-external/reviewer-protocol-v2-offline/original-design-evidence.md`, raw design extract, sections I/J/M | `14d994451820984fe61e830670f9ed2f43137a96d93d9d84357d9279a9ae22d3` |
| D1 | Same offline directory, `revised-design-evidence.md`, sections 2/8 | `1e23b4cb6a2fcf052634c039fa91ad8173ef0e82cb13512e4e5f58291bc11fab` |
| S | `main/docs/experiments/reviewer-protocol-v2-selection-spec.md`, accepted byte contract; its old milestone hashes are historical | `c3cd25f4bf197dde4f7a65ce4dbf69a45c381a649da464174f260ea028dadcc6` |
| IF | `main/docs/experiments/reviewer-protocol-v2-interface-implementation.md`, accepted amended interface receipt | `ca1f65f5b8c9123f75bf7d99d1d166ba7414aba854eb2224f977038beb294789` |
| OA | `main/docs/experiments/reviewer-protocol-v2-owner-audit-interfaces.md`, accepted owner-analysis implementation receipt | `d7cf3a4bcf8e73160e4706dc1541e9c2e318be044251b827b6b9a39bc39e6b59` |
| E | `main/docs/experiments/reviewer-protocol-v2-review-remediation.md`, evidence/operational boundary, superseded schema versions where applicable | `f297d0162634d4b36a263818b3365ca490b8e6d345a0f0c6952bee99298cfb8a` |

Current code is the authority for accepted schema versions, not a substitute for normative rule authority. In particular, the older preparation receipt's v1 adoption/interface examples and 13-source closure are superseded by current v2 schemas and the 17-source closure.

Actual owner attachments were read at `C:/Users/Desktop/.codex/attachments/<UUID>/Pasted text.txt`; schema is raw owner text, not a manufactured approval declaration. Relevant records and exact hashes:

| Owner ref (UUID) | Decision actually made | SHA-256 |
|---|---|---|
| O139 `139c9e58-9d7a-41fa-82df-4ed39765668b` | Revised design accepted in principle; Option A/context metadata; then-provisional size/gates; no freeze grant | `be92ecfb4dc4a7930f00408fed9d9237d4e4176674f013a59a05f364a6b515eb` |
| O430 `430d7fe2-6b9a-4a78-816c-68a4b39a5e75` | Direct-pair exposure/diversity, separate native groups; provisional R2 and account checks accepted for that design stage | `767de137e4d1d6c1577871a7ab3644838eabb32884324eaf665bb3144866786e` |
| O051 `051a6503-d589-48ac-a73b-4c5600623a83` | Final E01 metadata-only decision; finite rules accepted for bounded audit | `80bd0ac8420571031e02aa28cf1e4b7a9e982cea872baadb25ccc4f1e33352c1` |
| O526 `52667d5a-d82d-4b1b-8f97-e34b000fc0e8` | Eligibility/exposure design and capacity accepted, authoritative inventory accepted, durable offline implementation allowed | `c33feb84248ada1425d5eda8a954d4679f12010d644d6590aa88f8eac9044c1d` |
| O16 `16afd8fd-1436-4611-a21f-7bdae9169207` | Offline milestone/test evidence accepted subject to independent review; selection bytes specified | `482c289c1fe85084cf69e211f13da098bac493c8ac962b8c8a7a7358c752ca06` |
| Oselect `f03c3135-f81d-4276-85cd-c500203ed6e7` | Completed selection specification, private schemas and vectors accepted; real CLI kept disabled | `b9c0f5bba7e4c29412b05512db1739c07e8eb31c36de4e938980fc03ab0bf616` |
| Ophase `52847c5a-dc83-4fc2-b6d6-8e0032c20bf2` | Exact phase sequence, control/presentation domains/seeds, 24/15/6, 135 zero-retry schedule, interface amendments and historical-adoption conditions accepted | `ba659230b9b886974be4e383c9649e4a21ff11c4d46c645e38a3535d2197f377` |
| Oaudit `a8870926-1314-4259-86c2-1a5f4a815b8a` | Interface implementation/test evidence accepted; authoritative owner inclusion/exclusion policy; actual wording/keys/rubric unapproved | `22fe0949dc6e2063c56854202aeaf00a74dbbca63ed7f71a76840ec254940df1` |
| Ob6 `b6ea516b-0dbd-4025-90d2-a32ad575c706` | E01 reaffirmation, separate historical/current authority, exact nine-field runtime requirement | `314c8fa0919eacab7e2787f4f45febd95e3ad9fac1517b4f386d3a0c6d0d3cc7` |
| OD `e3c1cb41-cbae-4ecd-9c8a-f29346976849` | D1–D8 normative consolidation/corrections, shared origins, 100 fixtures and preserved 37-check/S-576 limitations | `78e34cedfb33e6deb3d328c2373f251bd94bc0b4ed714738678f646dfdfd8920` |
| Ogate `373dd2bb-86b4-4ddc-a368-76384f0ec49c` | Identified reconciliation contract/lemma, counts prerequisites; explicit future operational enforcement and unchanged pure selector | `7128421731eaae8ac41fc2470bcdfd77700444946f6ee86769a71e5d8ddf413e` |
| Oassembly `dce7fefa-54ac-442b-b21c-dcac08c23215` | Exact normative/contracts/bundle/lemma/counts subjects fixed for evidence assembly; no wider approval | `9e6f9244f0eff4a5229b1c84fb672fcd661abf341e9a073828b92f46bed6328b` |
| Ocompletion `a7543fff-9d54-4de2-bddb-9ed2bd46712f` | Accepted subjects retained; final wrappers/read-only chains authorized, no overall Freeze 1 claim | `a79120cd4e0b0b8dacdf9d7f3ba5e59707b53721046afccb53f4613d5295bb68` |

The present direct owner instruction independently accepts final wrapper completion and authorizes this audit/document commit only. No timestamp or separate approval-record hash is invented for direct chat decisions. Prior direct acceptance of offline milestones is not an approval of a final, not-yet-assembled Freeze 1 subject map.

## Actual prerequisite inventory

Statuses distinguish accepted decisions, missing technical records and genuinely unresolved approvals. “Missing” is scoped to the available v2 evidence: repository documentation/source/tests, the v2 private directories under `heldout-external/` and `data/`, listed owner attachments and this conversation. Invented pytest workspaces and v1 artifacts are not v2 production evidence. Searches included ignored private files, not only Git-visible files. No production bindings were assembled to test absence.

| Prerequisite and precise source | Existing evidence / status | Smallest resolution and action class | Required boundary |
|---|---|---|---|
| Working design/context/size, exclusion semantics, quotas and selection procedure (O139/O430/O051/O526/Oselect/Ophase/OD) | **Satisfied decisions**, with provisional engineering tolerances still provisional. Rule subjects, semantic reviews and final joins accepted (A/V/I/F). Do not request the already made choices again. | Reuse accepted decisions; assemble their final applicable bindings. **Evidence assembly**, not a new policy decision. | Design/procedure definitions before Freeze 1; live tolerances retain their later acceptance requirement. |
| Final owner approval of the exact Freeze 1 artifact set (`freeze_roles`: DesignApprovalEvidence v1) | **Unresolved final release approval**; no actual `design-approval-evidence-v1` covering the final 13 other role hashes found. An in-principle design, technical review or task grant is not that release. | After final bytes exist, present exact subjects for owner acceptance and record actual actor/time/reference truthfully. **Owner decision + evidence assembly**. Never fill UTC from file times. | Before constructing/operationally designating Freeze 1. |
| Definitive heldout exclusion policy (`freeze_roles`, O430/O526) | **Satisfied semantics**: direct pair >=0.90, nontransitive, separate native groups; selection <0.90, SCREEN_PASS and exact accepted exposure inventory. **Missing** actual `definitive-exclusion-policy-v1` with population/ledger/inventory FBs and ledger-order context projection hash. | Transcribe existing decisions and bind the specific artifacts; resolve only any demonstrated unapproved change. **Evidence assembly**, then final subject approval above. | Freeze 1. No new exposure discovery or re-screening. |
| Current normative rules/applicability/reconciliation (`rule_bindings`, `verify_reconciliation`) | **Satisfied at existing hashes**: three RuleSpecification v2, ReviewEvidence v4, RuleApplicability v3; HistoricalLedgerReconciliation v1 and its v1 review. Exact final FBs in I/T, all accepted in F. | Reuse unchanged; refresh only dependencies actually changed by future implementation. **No action now**. | Freeze 1 rule joins and later adoption/selection gates. |
| Remaining interface decisions and four typed specifications (`interface_specifications`, Ophase/Oaudit, IF/OA) | **Satisfied decisions**: control, trial_presentation, owner_audit and analysis_population, including independent abstention/concern and overlapping exclusions. **Missing** actual `interface-specification-v1` records and supporting RuleTextEvidence v3; missing `adoption-interface-binding-v2` enclosing the four FBs and current verification bundle. | Assemble from actual owner records after applicable source dependencies settle; no synthetic content or key can be substituted. **Evidence assembly**. | Freeze 1 procedure/interfaces; physical trial outputs later. |
| Actual control wording, provenance, item keys and diagnostic policy expectations (Ophase/Oaudit, D0 section I) | **Missing/unapproved actual content**, not missing counts/domains. Existing approval expressly excludes wording/keys/expectations. No v2 approved catalog/key evidence found. | Privately author/review actual content and separately approve source wording, then complete catalog/keys without hash cycles. **Content work + owner decision + later assembly**. | Before use/sealing of controls and Freeze 2. No accepted requirement makes actual selected packets a Freeze 1 input. |
| Generic rubric (D0 sections E/F/I, D1 section 8, Oaudit) | **Unresolved actual rubric approval/artifact**. Semantic directions and local vote schema exist, but not a final digest-approved generic rubric. | Produce the generic artifact without item-specific hints, obtain owner approval and freeze it before owner labeling. **Content/owner decision + assembly**. | Before owner audit; bind complete package at Freeze 2. |
| Test plan, prior passing tests and exact test/source manifest (`freeze_roles`, O16/Oselect/Ophase/Oaudit, cleanup receipt) | **Satisfied prior synthetic test/review evidence** for unchanged code: cleanup reports 679 passed/one real-population test deselected, focused 64 and Ruff/goldens passed. **Missing** actual `synthetic-test-manifest-v1`: exact current source map, code digest and 15 `TEST_PATHS` source hashes. This schema binds coverage, not execution. | Assemble final hashes and link existing accepted run evidence; run targeted synthetic checks only for new changes. **Evidence assembly**, future **implementation validation** if changed, final owner artifact approval. | Freeze 1; do not re-screen to populate a manifest. |
| Intended offline runtime (`runtime_binding`, `check_runtime`, Ob6, `_freeze`) | **Observed matching**, not a frozen lock: nine actual fields below. `.venv/pyvenv.cfg` is supporting evidence, not AdoptionRuntimeLock. **Missing** actual runtime lock/accepted final binding on intended machine. | Record measured values only after source/machine choice is stable; review any actual machine change. **Evidence assembly + final owner binding approval**. | Freeze 1; no silent runtime relaxation. |
| Dependency closure (`dependency_modules`, `_freeze`, D0 section J) | **Available technical source evidence**: 17 reviewed files, 12 declared stdlib roots below. **Missing** `adoption-runtime-lock-v1` with scope OFFLINE_PREPARATION_SELECTION, exact runtime/stdlib list and empty third_party_distributions. `requirements.txt` is not this scoped lock. | Bind final AST closure and runtime after gate changes; preserve static-check limits. **Evidence assembly**. | Freeze 1. |
| Broader SDK/dependency/platform pins (D0 section J explicitly says before Freeze 1; D1 section 4 corrects Python assumption) | **Partially available**, final reviewed procedure scope unresolved: requirements pin boto3/botocore/s3transfer, installed metadata agrees; dev requirements include >= ranges. No complete approved broader lock found. The empty-third-party offline lock cannot claim to pin provider/test infrastructure. | Identify applicable scope and bind existing measured pins/source/environment evidence; resolve genuine version/scope changes explicitly. **Evidence assembly + owner decision for remaining intended pins/scope**. No install or API check needed in this audit. | Preserve the before-Freeze-1 pin requirement. API envelopes/inference configuration and execution lock remain Freeze 2 work. |
| Original and current population/input closure (`_history`, `_freeze`, `prepare_inputs`) | **Historical closure satisfied in accepted T/F**: 107 pins + four recovered inputs = 111, canonical closure digest below. Population FB is available in original pin map. **Missing** current InputBinding/its separately trusted expected hash and historical-adoption-v2 procedure joins. No changed population or current closure was inferred. | After code/runtime settle, separately authorize bounded real binding assembly/identity validation without ranking; retain all original closure evidence. **Evidence assembly**, later authorized **read-only technical validation**. | Freeze 1 input/procedure evidence; operational adoption remains later. |
| Inventory/provenance (O526; `_history`, `validate_inventory`, `_freeze`) | **Accepted inventory exists**: final-1 `known_exposure_inventory_v2`, hash below; 15 direct, 48 outside, 63 computational texts, 1,480 provenance entries and zero unresolved per accepted O526. **Missing final role/InputBinding/policy joins**, not missing exposure discovery. | Reuse unchanged inventory and supporting bindings; final joins under separate authorization. **Evidence assembly**. | Reviewed/hashed before Freeze 1; no expansion of known-exposure claim. |
| Complete historical adoption procedure (`_freeze`) | **Missing** actual `historical-adoption-v2`: audit/payloads, original 16-source wrapper, pin map/four extras/full closure, three rule joins, recorded historical runtime, proposed runtime lock, current selection/interface roles and selection_inputs FB. T's small adapter is not this artifact. | Assemble complete acyclic bindings only after dependencies and authorization; never invent absent evidence. **Evidence assembly**. | Freeze 1 compatibility, before later production adoption. |
| Full freeze path and independently trusted expected hash (`_freeze`, `verify_adoption`, `validate_preparation`) | **Implemented technical checks, unresolved actual compatibility**. No full FreezeManifest, InputBinding, runtime lock, procedure, policy/test/design records exist for the required path. Direct reconciliation/rule joins do not satisfy it. | Separately authorized complete evidence assembly and technical path validation; owner trusted hash/release must be separate from calculated evidence. **Assembly + read-only validation + owner decision**. Freeze operation separately authorized. | Before Freeze 1; no dummy envelope or successful preparation flag can substitute. |
| Reconciliation gate at operational boundaries (Ogate; code map below) | **Implemented on technical Freeze/adoption path; missing operational enforcement**. `select_bound_inputs` is intentionally pure/public; `select()` rejects; CLI only audit/verify. Phase predicate executes nothing and has no trusted producer. | Specify missing operational trust/phase/seal contract and implement the narrow preflight integration on invented inputs, then independent review. **Implementation** under separate authorization; see handoff. | Applicable procedure/code settled before final binding; enforce before post-Freeze-1 adoption/seal and before any authorized real ranking/IDs/packets. Operational use is later. |
| Trusted approvals, ledger seal, phase, claims/publication/recovery/freeze producers (Ophase, E, F) | **Missing operational tools and grants**, not a missing approval flag in the accepted envelopes. Pure seals/assessment/predicate do not provide durable history. | Separately implement/review bounded operational producers and fail-closed callers; separately authorize use. **Implementation + later operational execution/owner grants**. | Freeze construction at its gate; ledger verification/seal only after Freeze 1; selection/publication after that seal. |

No mismatched accepted subject was found. Missing records cannot be repaired by declaring approvals, borrowing v1 seals/rubrics, using a current digest as historical provenance, or treating reviewer acceptance as owner approval.

Accepted limitations are preserved, not promoted into new blockers: R4 is the independently reviewed non-normative similarity I/O change under UNCHANGED_POLICY, never inferred from unequal hashes. S-576 retains `complete:false`, whose meaning is unestablished; OD accepts the recovered content for current consolidation without claiming missing history was recovered. The 37 supplementary checks retain their historical registration/execution limitation and are not additional normative rules. Ledger fidelity remains a premise of the reviewed lemma. Artifact/provenance agreement does not establish historical execution, authenticate owner/reviewer authorship or prove semantic correctness by itself.

## Available runtime, dependency and historical input evidence

Read-only measurements from the existing `.venv`, under the installed offline guard; these are observations in an audit, not a newly assembled runtime lock or InputBinding:

```text
python_implementation=CPython; python_version=3.13.12; unicode_version=15.1.0
platform=Windows-11-10.0.26200-SP0; machine=AMD64; byteorder=little
float_radix=2; float_mant_dig=53; float_max_exp=1024
```

`.venv/pyvenv.cfg` raw hash: `4fd0e26a6bf8348c9f8f2de749dc027d88e53ade83b35c3474e32a5f186203fc`.
`main/requirements.txt` raw hash: `1d1c1772d15d9b27bbc2be1c40d3dd8c335106e6cf9971286e53272892f56d1d`.
Installed distribution metadata: boto3 1.42.96, botocore 1.42.96, s3transfer 0.16.1, pytest 9.0.3, Ruff 0.15.16. No SDK client was imported or called. These versions do not prove live compatibility, historical SDK versions or a complete environment lock.
Reviewed-current-source AST import roots: `ast, collections, datetime, hashlib, itertools, json, math, pathlib, platform, re, sys, unicodedata`. Repository dependencies are separately hash-bound. Static checks on reviewed source remain static checks, not a Python sandbox, universal dynamic-code guarantee or execution attestation.

| Available historical/input record | Schema / binding | Exact hash / evidence basis |
|---|---|---|
| `heldout-external/pilot-v1/out/candidates.jsonl` | Population JSONL; FB recovered from unchanged original pin map, not reread in this audit | `89d840aacdd353928649bc72daa08921b428af217f9362786d524ef2a23e6775`; T/F accepted closure check |
| `heldout-external/pilot-v1/out/manifest.json` | Original population manifest; pin-map binding | `e7929883b6ab73052aee912b8fd0a8ad97e4dd11a59adbd653f717688dac38b6`; T/F |
| `heldout-external/reviewer-protocol-v2-offline/final-1/manifest.json` | `offline_audit_manifest_v2`, `frozen:false`; metadata bytes read/hash checked, not adopted | `057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4` |
| Same final-1 directory, `inventory.json` | `known_exposure_inventory_v2`; schema/supporting-file metadata inspected, no question/ID output | `03c5329c0a388734ee95c72b7e35901703b8c4c41adba8c96b89603aed108877` |
| Same final-1 directory, `population_ledger.jsonl` | Historical ledger binding from manifest and accepted T/F; not opened/count-replayed here | `6b3f97d8e987b9c01d091bce8f06b3c2e691ca5e9b4b2fc567e2919d2e07b7d2` |
| Same final-1 directory, `integrity.json` | Historical integrity binding, not current procedure | `e22995446421857109140e07d78f5500dbfb28aecfccdf0b96f81def1718bf84`, from manifest/A/T |
| Assembly directory, `historical-sources/input_hashes.json` | Original 107-entry raw pin map; recipe metadata only | `ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae` |
| Assembly directory, `historical-generating-bundle.json` | `reviewer-protocol-v2-historical-generating-bundle-v1` | `2476cb7cb563c936172f55ba7e69f52476bb003a912fcca06cedcd4e6aabd6ae` |
| Historical closure | Original pin map + original source literals for `original-design-evidence.md`, `revised-design-evidence.md`, `document-quotes.json`, `recovered-references.json`; 111 total | Canonical closure-map digest `1a1af4787c75f64c95b46c3e804660d8832420e622c351c899ad2fbf837ce9a4` (A metadata, validated closure T/F); no rerun |

Original recorded runtime remains only CPython 3.13.12 / Unicode 15.1.0. No historical SDK/platform fields are inferred. The historical audit is an unselected audit, not an operationally frozen/adopted ledger merely because earlier instructions call its bytes “sealed.”

## Full Freeze 1 path and operational dependency

Read-only source inspection establishes this existing chain:

```text
prepare(proposed_freeze1 supplied) -> verify_adoption -> _history -> _freeze
_freeze -> _generating + _executing_sources -> rule_bindings -> verify_reconciliation
_freeze -> interface_specifications + freeze_roles + runtime/dependency lock
        -> current InputBinding + identity/inventory/payload/runtime joins
validate_preparation(trusted Freeze 1 hash supplied) -> prepare replay and byte equality
selection_phase_predicate -> necessary structural predicate only; no dispatch
select_bound_inputs -> prepare_inputs -> scan -> IDs/packets -> validate_result
select() -> rejects; current CLI -> audit/verify only
```

The last computation path has no reconciliation/Freeze/seal/approval gate by design. `prepare()` without a proposed freeze is a pre-Freeze-1 technical preparation path; its PREPARED status cannot make selection ready. `verify_adoption()` without a proposal verifies historical provenance only. `selection_phase_predicate` checks canonical assessment input hash, report hash in authorization-v2, EVIDENCE_REPLAYED level, phase FREEZE_1_LEDGER_SEALED, matching grant/input/Freeze/procedure/seal/destination hashes. It authenticates none of the external trust/history it receives.

Operational enforcement must cover (a) production adoption/sealing of this historical ledger, using verified Freeze 1 and full compatibility including reconciliation; (b) every real selection entry/caller, including future CLI, API or recovery route, before ranking or ID/packet construction; and (c) publication/designation as successful of selection outputs, preserving validated SUCCESS or SHORTFALL/failure evidence without replacement. Recovery must not supply an alternate ungated route. Freeze designation needs the complete prerequisites and release grant, not a reconciliation-only PASS. No gate needs to be added to historical audit/verify or pure serialization helpers merely because they exist; they must not be promoted into operational selection routes.

**Existing enforcement is sufficient for the accepted technical chain, insufficient for operational completion.** No currently enabled real CLI is discovered. Repository call-site inspection finds no operational consumer of `selection_phase_predicate`; the chain callers are the verifier modules, with tests exercising invented evidence. This is source/call-site inspection, not a universal dynamic-call proof. Additional preflight/caller integration and trusted producers are required. No accepted pure selector/API change is necessary or authorized here.

The exact FreezeManifest envelope stays v1, phase FREEZE_1, with these fifteen roles and no additions:

```text
population, exposure_inventory, eligibility_specification, exposure_specification,
selection_specification, remaining_interfaces_specification,
eligibility_exposure_code_bundle, selection_code_bundle, synthetic_test_manifest,
grouping_similarity_specification, historical_similarity_source,
runtime_dependency_lock, historical_integrity_manifest,
definitive_heldout_exclusion_policy, design_approval_evidence
```

The historical code role holds the original sixteen-source wrapper; current code is bound separately by the selection descriptor and `adoption-interface-binding-v2.verification_bundle`. `_freeze` also requires the complete `historical-adoption-v2` object, exact original audit/input closure, proposed lock, four typed interface specifications, three accepted rule joins, test/policy/design records, canonical selection descriptor and current InputBinding. That InputBinding remains `reviewer-protocol-v2-selection-inputs-v1`; no fields change. Its four private artifact paths must be distinct under heldout-external, and all reads retain approved-root/resolved-path protections. Full `_freeze` success is technical compatibility only, not approval authentication or Freeze 1 readiness.

## Digest impact and precise refresh scope

Accepted current verification digest: `ece125e0466cd89b280221bb89b9d38389fe060c7fb19a4a35d506ff41828a28`.
Descriptor `A/current-verification-bundle.json` raw hash: `94c45d6a68424018e0c15c3e101da0860521c6af58ec73650cbc2edfeff68199`.
Here `A/` means the assembly directory containing reference A. Its current source buffers were read/hash-compared with that descriptor, without importing/executing the verifiers.

Every raw-byte edit in these seventeen paths changes that digest and makes the existing reconciliation's bound current bundle fail, regardless of unchanged eligibility semantics:

```text
main/experiments/__init__.py
main/experiments/reviewer_protocol_v2/__init__.py
main/experiments/reviewer_protocol_v2/analysis.py
main/experiments/reviewer_protocol_v2/common.py
main/experiments/reviewer_protocol_v2/control_serialization.py
main/experiments/reviewer_protocol_v2/eligibility.py
main/experiments/reviewer_protocol_v2/exposure.py
main/experiments/reviewer_protocol_v2/ledger_adoption.py
main/experiments/reviewer_protocol_v2/ledger_reconciliation.py
main/experiments/reviewer_protocol_v2/owner_audit.py
main/experiments/reviewer_protocol_v2/packet_serialization.py
main/experiments/reviewer_protocol_v2/production_preparation.py
main/experiments/reviewer_protocol_v2/procedure_evidence.py
main/experiments/reviewer_protocol_v2/selection.py
main/experiments/reviewer_protocol_v2/similarity.py
main/experiments/reviewer_protocol_v2/trial_interfaces.py
main/experiments/reviewer_protocol_v2/validation.py
```

Editing only a new external caller or the currently unbundled `__main__.py` does not by itself change these seventeen bytes. That does **not** make its operational code covered by this digest: its entire executable closure, applicable procedure/runtime/test evidence and independent review must be bound separately. Silently importing a new file from the reviewed closure would also require closure changes. Do not hide an operational dependency outside the reviewed bundle to avoid review refresh.

For the smallest proposed integration in existing `production_preparation.py` (current raw hash `07ec3553fce57fde420aff0b146c02a1ebd8e6f5fa89a55782a4cb1ea0e15ee8`), plus existing focused tests, the required refresh is:

1. Independently review the code delta, synthetic no-dispatch failure paths and dependency closure; recompute the 17-source descriptor. Selection/control/owner bundles remain unchanged if their files do not change (current seven-source selection digest `0797dd5065486ecb142bed90fe7d1a74f8792e80659c1b64c9f495d71eba1187`).
2. Create a new reconciliation subject binding the new current bundle, preserving the original manifest/ledger/generating wrapper, eligibility source transition, lemma/counts/premises if unchanged. Its subject hash changes; the existing subject-bound independent review does not accept this replacement. Obtain a new actual subject-bound raw/typed reconciliation review, then assemble a new final reconciliation wrapper. Preserve every old record.
3. Create a new eligibility applicability wrapper referencing the replacement reconciliation; that FB changes its bytes. Exposure/grouping applicability and all three RuleSpecifications/semantic reviews remain reusable if their actual subjects, source/contract/document/policy bindings remain unchanged. No automatic semantic re-review of unchanged subjects is proposed.
4. Refresh dependent completion index/check receipt, interface-binding descriptor, synthetic source/test manifest, and future historical-adoption procedure/current bindings. Recheck applicable runtime/AST dependencies; do not invent a changed lock merely because a code hash changes. New final owner subject hashes and separately trusted expected procedure/input/freeze hashes must bind the replacement artifacts.

The current reconciliation subject `20252b1f3c161feaf2103597a8b28b0c899b1871f8545048cc9ac7018b01cf7f` and final wrapper `5f5183865ca85eb5837de4634e77a5a13a355c0e39bc433b8ded827162763eb9` remain accepted at the old digest. Their acceptance is not revoked historically; it cannot be transferred to new bytes. Historical sixteen-source digest stays `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`. No new lemma, counts run, rule amendment or historical source reconstruction is needed merely for a preflight-only change that leaves the lemma's source transition unchanged; any newly demonstrated contrary dependency must be reported.

## Minimum sequence and focused next-task handoff

Accepted order (Ophase) is **Freeze 1 -> production-ledger verification/sealing -> authorized external selection -> owner audit -> Freeze 2 -> separately authorized live execution**. Historical verification and proposed technical compatibility may precede Freeze 1; operational adoption/sealing may not. No earlier v1 authorization transfers. The following preparation order is a proposal for completing prerequisites, not a new authorization or amendment of that accepted phase sequence:

1. **Next single bounded task: operational reconciliation preflight contract and synthetic integration only.** Define the minimum trusted-evidence inputs for the missing phase/ledger-seal relationship before implementation; use the accepted authorization-v2 and existing replay/compatibility chain. Implement one fail-closed preflight in `production_preparation.py`, with existing preparation/remediation tests and a receipt. Keep `select()`, the real CLI and every operational dispatch disabled. Do not implement trust/claim/seal/publication/recovery/freeze managers or weaken the pure selector contract. A successful preflight is still a necessary technical condition, not authenticated approval or completed operational enforcement. This resolves the immediate integration/source-dependency gap without touching real evidence.
2. **Review and refresh changed dependencies** as enumerated above, using newly issued actual independent review records. Only then assemble final source-dependent runtime, test, interface and procedure bindings. Do not assemble a final Freeze 1 evidence set around code already planned to change.
3. **Complete technical evidence assembly and actual release approval.** Separately authorize real bindings without ranking; join existing population/inventory/111-input provenance to the final sources/lock/specifications/test/policy/procedure artifacts. Validate independently complete components first and present the concrete exact subject set for actual owner approval. Only then transcribe the truthful DesignApprovalEvidence actor/time/reference/13-subject map: `_freeze` requires this record, so a fabricated declaration cannot be used to validate an otherwise incomplete package in advance. Obtain the separate trusted expected hash and run full technical compatibility on complete authorized evidence. No self-declared hash or PREPARED receipt is approval. Separately implement/review/authorize the necessary freeze designation tool; a conditional owner grant may cover designation after successful checks without redundant confirmation. Freeze 1 is not a side effect of technical validation.
4. **Later operational stages, with separate grants:** implement/review trusted phase/approval/seal producers and all real callers before their first use; after Freeze 1, verify/adopt/seal unchanged ledger bytes; only then authorize selection/publication with complete validation and durable failure/recovery preservation. Later callers must enforce the reviewed preflight plus externally established trust, not accept arbitrary caller Booleans. Any source edit within the frozen procedure needs a replacement version/review, not a post-freeze patch.
5. **Owner audit -> Freeze 2 -> live.** Approve/freeze the generic rubric before owner labels; approve actual controls/keys/diagnostic expectations before use and bind them in Freeze 2. Complete provider envelopes, exact reviewers/API/settings/request hashes, zero retries, analysis/gates, budget/token/price reservations, terms/credit/account evidence, locks/recovery and independently recoverable backup. Separately authorize manifest-bound live execution afterward.

Independent work need not wait for gate code: index/transcribe already accepted owner decision references, privately prepare generic rubric/control content for approval under separate scope, and identify intended machine/broader dependency pins. Final hash-bearing source/test/procedure records must wait for their actual dependencies; actual selected packets and owner labels must wait for their operational stages. The offline lock is not the live lock. D0's before-Freeze-1 Python/SDK/dependency/platform pin requirement is retained; complete provider inference configuration and cost/terms/credit gates remain in their accepted Freeze 2/live phases, not silently waived or moved.

Genuine owner decisions are consolidated: approve the final Freeze 1 artifact subjects/release when reviewable; resolve remaining intended runtime/dependency scope or version choices, if any; approve actual rubric/control wording/provenance/keys/diagnostic expectations before their use; later approve remaining engineering tolerances, provider settings/budgets/terms/credit/backup and each operational grant in its phase. Accepted context/exclusion/selection/interface/analysis choices do not need reapproval absent a material change. Merely authorizing the next synthetic task resolves none of these approvals.

Next-task handoff acceptance checks: absent/invalid reconciliation, stale current bundle/review subject, mismatched InputBinding/report/procedure/Freeze/seal hashes, invalid phase and authorization lacking the separately supplied trusted input must fail before any ranking/ID/packet/publication hook. A matching self-declared raw hash cannot establish external trust; the preflight must state that trust's external boundary, not claim to authenticate it. Include one invented complete baseline and specific sanitized codes, unchanged golden bytes, no writes/import side effects and the existing guard. Exercise the actual technical chain in invented workspaces; do not substitute flags or monkeypatch production validators. Record missing trusted-producer contracts explicitly. Run focused tests and permitted v2 regressions excluding `test_accepted_population_regression`, plus Ruff, only in that future implementation task. Report exact changed digests and the subject-review refresh handoff separately. This is a proposed task, not its authorization or execution.

## Audit checks and scope receipt

Read-only commands used included `git rev-parse HEAD`, `git status --short`, targeted `rg`/file reads of the listed records/current code, and `Get-Content` of the final review/receipt. In-memory Python read/hash/schema metadata inspection and AST inspection used the existing `.venv` with `-B`; it did not import the preparation/adoption/selection modules or call their entry points. The guard was installed for runtime/import-metadata observation: zero blocked attempts and no outbound calls. No historical input closure/count/technical-chain replay or full tests were run. One metadata probe initially treated the guard's request list as callable and failed before output; corrected to `len(blocked_requests)`. A text-display probe hit the console encoding on an arrow; UTF-8 display corrected it. Neither diagnostic wrote evidence or changed verification requirements.

Only this new document is staged by explicit path and committed locally. All eight Claude reports, the proposed draft, accepted/private evidence, historical artifacts and unrelated files remain excluded and unchanged. Final checks compare the read evidence/source/original snapshot, the exact one-file staged/committed bytes and unchanged pre-existing working-tree inventory; they are preservation checks, not technical replay.

Scope receipt: prerequisite inventory and forward plan only. No code/evidence-wrapper changes, preparation package/InputBinding/FreezeManifest, adoption/sealing, classification/screening, selection/ranking/sampling, packets/freezes, owner labels, operational tools, model/router/Claude invocation, AWS/external API operations, installs or push. **No ledger adoption occurred. Overall Freeze 1 compatibility was not assessed; Freeze 1 readiness remains unestablished.**
