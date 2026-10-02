# Deferred Claude review handoff: Reviewer Protocol v2

Local handoff only. Claude was not invoked or messaged. Independent review remains
required and unwaived. All milestones through 184a256 are owner-accepted as scoped
offline components, subject to this review. The current encoding follow-up is
implemented under delegated schema authority; acceptance/review is still pending.
No milestone acceptance authorizes real preparation, sampling, adoption or freezes.

## Commit and file inventory

Prefixes: P=`experiments/reviewer_protocol_v2/`, T=`tests/`, D=`docs/experiments/`.
The exact sixteen P generating filenames are enumerated in the preparation
encoding document. These identify history, not the later current package contents.

| Commit | Scope and files | Recorded v2 cases |
|---|---|---:|
| 182f131 | Eligibility/exposure/provenance/analysis: all sixteen P generating filenames plus P.gitattributes; Dreviewer-protocol-v2-design.md; Ttest_reviewer_v2_eligibility.py, exposure.py, regression.py, safety.py, validation_analysis.py (all five names use the test_reviewer_v2_ prefix) | 184 |
| 08fa6d9 | Pselection.py, packet_serialization.py; Dreviewer-protocol-v2-selection-spec.md; Ttest_reviewer_v2_selection.py, test_reviewer_v2_packet_serialization.py | 251 |
| de28891 | Pcontrol_serialization.py, trial_interfaces.py; Dreviewer-protocol-v2-interface-implementation.md; Ttest_reviewer_v2_controls.py, test_reviewer_v2_trial_interfaces.py | 354 |
| b22d0b7 | Powner_audit.py; Dreviewer-protocol-v2-owner-audit-interfaces.md; Ttest_reviewer_v2_owner_audit.py | 416 |
| 184a256 | Pledger_adoption.py, production_preparation.py; Dreviewer-protocol-v2-preparation-verifiers.md; Ttest_reviewer_v2_preparation.py | 465 |
| Current follow-up (this handoff's commit) | The same four 184a256 files extended, plus Ttest_reviewer_v2_adoption_encoding.py and this D handoff | 502 |

Exact inventory/diff retrieval (read only), from main:

```powershell
git log --oneline 182f131^..HEAD
git diff --stat 182f131^..HEAD
git show --format= --name-only 182f131
git show --format= --name-only 08fa6d9
git show --format= --name-only de28891
git show --format= --name-only b22d0b7
git show --format= --name-only 184a256
git show --format= --name-only HEAD
```

Review both the historical commits and current code. 184a256's missing-encoding
blocker is intentionally superseded by the current delegated contract; prior
byte schemas, selected analysis populations and historical hashes are preserved.

## Accepted decisions and review focus

- Historical provenance is an offline audit, not a retrospectively frozen or
  adopted ledger. The sixteen-file digest preimage is canonical filename-to-hash
  JSON plus LF, recovered from 182f131. Original manifest, four payloads, pin map,
  four additional input literals and recorded runtime must bind exactly.
- External-only selection uses the accepted InputBinding, seed 20261001, exact
  six strata/quotas, deterministic ordering and receipt replay. Real CLI remains
  disabled. SHORTFALL/failure evidence cannot be replaced by redraws/destinations.
- Combined membership is 24 external / 15 anchors / six diagnostics. Control seed
  20261003 and presentation seed 20261002 have separate accepted domains. Reviewer
  IDs/allowlists hide roles; three complete permutations and 135 zero-retry logical
  requests preserve identical membership. Diagnostics are unscored. Actual wording,
  keys, expectations and rubric remain unapproved.
- Owner abstention/context fields are independent, explanatory notes mandatory.
  Abstention has null label/certainty and empty components. Reviewer pair/Fleiss
  populations depend on valid external reviewer votes only. Owner comparison also
  requires a valid owner label, no abstention and no context concern. Keep raw
  records immutable, overlapping exclusions and planned denominators; empty
  agreement/kappa is undefined, not fabricated. No supplementary adjudication.
- Preparation checks artifacts, identities, question hashes, flag consistency,
  inventory provenance, source execution bindings and the mandatory runtime.
  Trusted expected hashes are separate caller inputs; no hash authenticates owner
  approval. PREPARED never implies selection readiness or authorization.
- New adoption encoding occupies existing roles only. Review original-evidence
  membership, exact specification bytes, explicit rule witnesses, sixteen-source
  wrapper/recipe, complete closure, historical/current separation and the scoped
  current runtime lock. Source bytes are never treated as approved specifications.
  The original three-field historical runtime remains separate from nine-field
  proposed runtime/dependency evidence. Successful compatibility is technical only.
- Check the entire success/failure call graph for ranking, ID construction,
  packet building, filesystem mutation, publication, sealing and freeze operations.
  None is authorized or implemented in the new verifier layer.

## Exact verification commands and latest evidence

Use existing `.venv` and default offline guard. Do not add live-test flags, fetch
dependencies, run population screening, call new APIs with real inputs or invoke
Claude/providers as part of reproducing this handoff. Invented pytest workspaces
remain beneath the workspace-owned basetemp.

```powershell
.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py -q -s --basetemp=.pytest_cache/reviewer-v2-adoption-encoding-02
$adoptionRegressionTests = @(rg --files tests | Where-Object { $_ -match 'test_reviewer_v2.*\.py$' })
& .venv\Scripts\python.exe -B -m pytest @adoptionRegressionTests -q --basetemp=.pytest_cache/reviewer-v2-adoption-encoding-regressions-01
.venv\Scripts\ruff.exe check experiments/reviewer_protocol_v2 tests/test_reviewer_v2*.py
.venv\Scripts\ruff.exe format --check experiments/reviewer_protocol_v2/ledger_adoption.py experiments/reviewer_protocol_v2/production_preparation.py tests/test_reviewer_v2_preparation.py tests/test_reviewer_v2_adoption_encoding.py
```

Latest: 86 focused cases and 502 relevant v2 cases pass; Ruff/formatting pass.
Existing asyncio_mode configuration warning remains. Four deliberate network
lookups were intercepted in the combined suite; none sent. Source import purity
matches thirteen verification files. Positive compatibility and no-writes tests
pass; nested traversal/junction, missing evidence, altered rules, runtime/dependency
mismatches, historical/current substitution, closure mismatch and stale/self-declared
hash cases fail as intended. Exact synthetic hashes are in the preparation receipt.

| Bundle | SHA-256 |
|---|---|
| Historical generating | 105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc |
| Unchanged selection | 1cd9a742c8a3a10a82ca660c0edeaea3da90229dcaa06454432c17d47890fbf4 |
| Unchanged control/trial | 3c6028eaa52f3d7b35bf92c67911d1e9a14b8776588808030bb6cfced227fc18 |
| Unchanged owner audit | 4d43a47492c543bf1a2d15e6f759515e0fe12aa109b0b262f97e085ccb3bb486 |
| Prior 184a256 verification (historical milestone) | 539c8563a3919a45e2b099c29a0075cd50f485042f373f9cda9fa2ed042a165b |
| New current verification | 151994fdd1185648040764212a715686e34f137755f247a17f412f9d4adf4802 |

Old read-only integrity APIs verified 107 protected files and 72 bindings; pins
`ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae`.
Both final-1/final-2 manifests/four payloads remain bound at manifest digest
`057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4`.
Real artifacts were never supplied to the new preparation/adoption APIs.

## Evidence limits and consolidated blockers

Hash/source agreement proves artifact bindings, not past execution, rule semantics,
human approval or trust in the caller. Rule relationship witnesses explicitly
associate bytes; applicability/approval still requires review. Dependency AST
evidence covers the current offline closure, not complete binary attestation,
unrecorded historical SDK/platform facts or a live/provider dependency lock.
There is no operational claim/adoption/seal/freeze implementation or readiness
assessment, and additional OpenAI review would be recorded separately.

1. Deferred Claude independent review and owner acceptance of this follow-up;
   supplied actual original rule/specification/source/input evidence, reviewed
   relationships and applicable proposed runtime/dependency evidence. Encoding
   choices are delegated and resolved; missing facts/approvals are not waived.
2. Actual private controls/keys/diagnostic expectations/rubric and applicable
   design/evidence approvals; complete Freeze 1 prerequisites and separate freeze
   authorization. No real preparation/bindings were created or assessed here.
3. Separately authorized operational tools and execution: trusted authorization,
   durable claims, ledger adoption/sealing, publication/recovery, owner sealing
   and Freeze builders. Preserve Freeze 1 -> ledger verification/sealing -> external
   selection -> owner audit -> Freeze 2 -> separately authorized live execution.
   Provider settings/request hashes, cost/token/terms/credit evidence, safeguards
   and recoverable backup remain in their accepted Freeze 2/live phases.

Scope receipt: local documentation handoff only; no Claude invocation/message,
real preparation/bindings, adoption, ranking/sampling, production packets, operational
seals/freezes, owner labeling, reviewer/router invocation, AWS/external API call or push.
