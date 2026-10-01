# Reviewer Protocol v2: durable offline implementation receipt

Milestone 2 implements the accepted eligibility/exposure specification and reproduces the accepted population audit. It does not establish a frozen procedure or authorize sampling or execution. Codex is the single active writer; Claude Code's independent review remains deferred.

Owner authorization: Work chat `01a0f4d3-eeb5-7d20-b31c-f09234c0ef1d`, October 1, 2026, attachment `52667d5a-d82d-4b1b-8f97-e34b000fc0e8`. Base HEAD: `939660f0fcf0fd0cb8defa329271e79c4eabfd44`. The eight pre-existing untracked documents were preserved and are excluded from this change.

## Implemented scope

All implementation lives in `experiments/reviewer_protocol_v2/`:

| File | Purpose |
|---|---|
| `__init__.py` | Side-effect-free package import |
| `__main__.py` | Offline `audit` and `verify` commands; no rank/select/freeze/live command |
| `common.py` | Strict duplicate-key JSON parsing, finite canonical JSON, hashes, safe paths, runtime checks |
| `eligibility.py` | Exact accepted E01–E07 catalog, all independent matches, normalized spans and precedence |
| `fixtures.py` | All 100 registered synthetic fixtures and 37 additional checks; audit preflight |
| `similarity.py` | Faithful grams/cos isolation; source SHA and function AST equivalence verification |
| `known_inventory.py` | Fixed accepted provenance reconstruction, using specified files/locators only |
| `exposure.py` | Identity binding, complete-reference loading, exact text deduplication, every evidence record, three independent exposure flags |
| `constraints.py` | Counts-only simultaneous quota proof and direct pair/native-group diversity validation |
| `audit.py` | Unselected private ledger, aggregates, retention fractions, manifests, separate run receipts |
| `integrity.py` | Historical checksum/freeze and protected-file verification; audit manifest verification |
| `input_hashes.json` | Metadata-only baseline of 107 protected existing files, including the eight untracked documents |
| `.gitattributes` | Preserve LF package/pin bytes across Windows checkouts |
| `packet_validation.py` | Pure future packet binding/quota/eligibility/exposure/diversity validator; tested on synthetic records only |
| `selection.py` | Recovered approved constants and explicit fail-closed procedure blocker |
| `validation.py` | Approved four-field JSON vote schema/strict validation; service envelope disabled |
| `analysis.py` | Approved descriptive planned-denominator, class/anchor, source-family, owner-abstention and kappa calculations |

Five test files were added: `tests/test_reviewer_v2_eligibility.py`, `tests/test_reviewer_v2_exposure.py`, `tests/test_reviewer_v2_safety.py`, `tests/test_reviewer_v2_validation_analysis.py`, and `tests/test_reviewer_v2_regression.py`. This document is the only new human-readable tracked report. No existing source, test, document or historical artifact was edited.

## Contracts and limits

Original questions remain verbatim, with SHA-256 over strict UTF-8 and no added newline. Eligibility uses NFKC, casefold, collapsed Unicode whitespace and strip. Historical similarity uses lowercase and collapsed whitespace only, preserving leading/trailing spaces and omitting NFKC. Identity binds exact original hashes when an ID is provided; complete question-only evidence resolves exact text first, then registered normalized equality. These views are deliberately separate.

E01 is metadata only. E02–E04 imply dependence exclusion, E05–E06 diagnostic-only, E07 invalid input. All safely evaluable findings remain recorded. Winning precedence is INPUT_INVALID > DEPENDENCE_EXCLUDED > DIAGNOSTIC_ONLY > SCREEN_PASS. No routing label or source answer is accessed for screening, ranking or balancing.

Audit requires CPython **3.13.12** and Unicode **15.1.0**. The earlier repository Python 3.11 guidance does not silently relax the accepted matcher runtime. A changed runtime requires reviewed compatibility validation and a new implementation digest. The present math is the historical Python floating-point implementation; threshold comparisons use `>= 0.90` with no epsilon. Empty-string grams and genuinely empty counters retain their different historical behavior.

Similarity source SHA-256: `752a65fa744f04ae6854b2c8429fad9c43d3fc365fe763fb5d6600e64d7586a4`. The historical selector is never imported or executed: only its source hash and AST of the two pure functions are compared. No ranking function is evaluated.

Native grouping is `(source, context_group)`. Exposure similarity is direct pairwise comparison to direct-known references only. Group-derived or similarity-derived exclusions never enter the reference seed register. Future packet diversity separately requires every accepted pair to have similarity strictly below 0.90 and distinct native groups.

The counts-only feasibility solver computes independent-set **count vectors**, without ranking or retaining any witness. Conflict-free capacities are combined with conflict-component counts. It refuses components larger than 20 vertices rather than claiming an uncomputed result. The actual retained graph has one two-vertex component. This resource limit does not change eligibility, similarity, grouping or quotas.

Evidence timestamps use recorded events or the sealed audit receipt; file modification times are never treated as exposure dates. Each evidence stage is preserved, but a complete chronological ordering is not established. `earliest_known_exposure_stage` remains null with an explicit chronology note. Supported event timestamps are retained separately; none are invented.

Known inventory closure describes documented exposure; it does not prove absence of unknown human exposure or model-training exposure. The five accepted recoveries retain exact text hashes, authoritative IDs/revisions/fields and source bindings. The FinDER abbreviated response-hash discrepancy remains explicitly documented; it is not represented as a verified full-hash match. No retrieval or new exposure discovery was performed.

## Private storage and bytes

Private data lives outside Git at `C:\Projects\AWS Project\heldout-external\reviewer-protocol-v2-offline\`. New supporting extracts are `original-design-evidence.md`, `revised-design-evidence.md`, `document-quotes.json`, and `recovered-references.json`; their hashes are bound in the implementation. They preserve accepted conversation evidence and complete recovered text without putting source text in tracked code.

Each audit writes a **new** directory containing `inventory.json`, `population_ledger.jsonl`, `aggregate.json`, `integrity.json`, `manifest.json`, and a separate `receipt.json`. Outputs explicitly have `frozen: false`. The ledger preserves frozen input file order; that order is not a new ranking. No packet, acceptance ordering or witness is produced. Audit stdout contains counts and hashes only. CLI errors are sanitized to avoid disclosing questions or IDs.

Deterministic byte contract: UTF-8, escaped Unicode, sorted JSON keys, compact separators, finite numbers only, one LF terminator per JSON object. Original question strings are unchanged by reversible JSON escaping. Manifest excludes itself from its file-hash mapping; its exact-byte digest is recorded in the run receipt. Timestamps and other receipt fields do not affect deterministic outputs.

`historical-before.json` holds the pre-edit integrity snapshot. `reproduction-receipt.json` records final byte equality. Preliminary `run-a`/`run-b` audits are retained; final implementation audits are `final-1`/`final-2`. None claims frozen status. No historical output was overwritten, repaired or regenerated.

## Reproduction result

| Stratum | Original | Final unexposed SCREEN_PASS | Quota | Retained fraction |
|---|---:|---:|---:|---:|
| TAT-QA | 13 | 10 | 4 | 10/13 |
| FinQA | 13 | 11 | 4 | 11/13 |
| FinLFQA numerical | 14 | 10 | 4 | 10/14 |
| FinLFQA interpretive | 50 | 46 | 6 | 46/50 |
| FinLFQA other | 10 | 9 | 4 | 9/10 |
| FinLFQA mixed | 4 | 3 | 2 | 3/4 |
| Total | 104 | 89 | 24 | 89/104 |

Recomputed results: E01 one TAT-QA metadata match; E02–E07 zero matches. All 104 raw records SCREEN_PASS; zero other dispositions. Direct, native-group and near-duplicate masks contain the same 15 candidates; all three pairwise intersections and their three-way intersection are 15. Exactly one/two masks: zero; no masks: 89. The E01 match overlaps all three exposure masks. Outside-pilot reference threshold matches: zero.

Inventory: 15 direct pilot items, 48 complete outside references, 63 distinct complete computational texts, 1,480 evidence records, zero unresolved entries. Categories: historical packets 72; removed controls 2; planning disclosures 19; Work-history disclosures 5; owner audits 48; reviewer requests 216; other documented exposure 1,118. Population/reference comparisons: 6,552.

Retained pair comparisons: 3,916. One native-group conflict, interpretive versus mixed; zero similarity conflicts. All six quotas coexist. Conflict-free capacities are 10, 11, 10, 45, 9, 2; these alone already meet every quota. The general count-vector calculation independently confirms simultaneous feasibility without selecting a witness.

Both final runs have identical exact bytes and hashes:

| Output | SHA-256 |
|---|---|
| `inventory.json` | `03c5329c0a388734ee95c72b7e35901703b8c4c41adba8c96b89603aed108877` |
| `population_ledger.jsonl` | `6b3f97d8e987b9c01d091bce8f06b3c2e691ca5e9b4b2fc567e2919d2e07b7d2` |
| `aggregate.json` | `459a0f63a2a396fdd57ec991bad305505c7123fe491f6704c1a789fdd067bcbc` |
| `integrity.json` | `e22995446421857109140e07d78f5500dbfb28aecfccdf0b96f81def1718bf84` |
| `manifest.json` | `057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4` |

Implementation digest: `105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`. It binds all package Python files and the input pin file; it does not claim to bind future execution settings or the entire project. Protected-file snapshot SHA-256: `ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae`. Verified **72 historical checksum/freeze bindings and 107 protected existing files** before/after audits and at handoff.

## Exact successful offline commands

Run from `C:\Projects\AWS Project\main`, with the existing `.venv`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_eligibility.py tests/test_reviewer_v2_exposure.py tests/test_reviewer_v2_safety.py tests/test_reviewer_v2_validation_analysis.py tests/test_reviewer_v2_regression.py -q --tb=short --basetemp='C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-target-03'
.\.venv\Scripts\python.exe -B -m pytest tests/test_router_bench.py tests/test_router_bench_cli.py tests/test_router_bench_costs.py tests/test_router_bench_metrics.py tests/test_router_bench_persistence.py tests/test_router_bench_safety.py tests/test_routing_datasets.py tests/test_preflight.py tests/test_offline_guard.py -q --tb=short --basetemp='C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-existing-01'
.\.venv\Scripts\python.exe -B -m ruff check experiments/reviewer_protocol_v2 tests/test_reviewer_v2_eligibility.py tests/test_reviewer_v2_exposure.py tests/test_reviewer_v2_safety.py tests/test_reviewer_v2_validation_analysis.py tests/test_reviewer_v2_regression.py
.\.venv\Scripts\python.exe -B -m experiments.reviewer_protocol_v2 audit --output 'C:\Projects\AWS Project\heldout-external\reviewer-protocol-v2-offline\final-1'
.\.venv\Scripts\python.exe -B -m experiments.reviewer_protocol_v2 audit --output 'C:\Projects\AWS Project\heldout-external\reviewer-protocol-v2-offline\final-2'
.\.venv\Scripts\python.exe -B -m experiments.reviewer_protocol_v2 verify --directory 'C:\Projects\AWS Project\heldout-external\reviewer-protocol-v2-offline\final-1'
.\.venv\Scripts\python.exe -B -m experiments.reviewer_protocol_v2 verify --directory 'C:\Projects\AWS Project\heldout-external\reviewer-protocol-v2-offline\final-2'
```

The final audit paths now exist: future reproductions must use new private directory names. Pytest basetemp points to test-owned workspace-local scratch storage; the first default temp attempt encountered Windows access denial. No protected directory is used for temporary tests.

The exact substantive byte comparison, independent of an agent scratchpad, is:

```powershell
@'
from pathlib import Path
from experiments.reviewer_protocol_v2.integrity import verify_historical, verify_output_manifest
from experiments.reviewer_protocol_v2.common import read_json, require
root = Path.cwd().parent
private = root / 'heldout-external/reviewer-protocol-v2-offline'
a, b = private / 'final-1', private / 'final-2'
require(verify_output_manifest(a) == verify_output_manifest(b), 'manifest_mismatch')
for name in list(read_json(a / 'manifest.json')['files']) + ['manifest.json']:
    require((a / name).read_bytes() == (b / name).read_bytes(), 'output_mismatch')
verify_historical(root)
print('Five deterministic files byte-identical; historical integrity verified.')
'@ | .\.venv\Scripts\python.exe -B -
```

Results: **184 targeted tests passed**, including all **100 fixtures + 37 additional checks**; **162 relevant existing offline tests passed**; Ruff passed. Failure tests cover altered/missing inputs, invalid identity, truncated/incomplete reference admission, differing text views, no transitive chaining or promotion of group-derived seeds, threshold/zero-vector behavior, precedence, quota and cross-stratum conflicts, packet binding, manifest mutation/path traversal, output placement/non-overwrite, disabled selection, prohibited audit flags and network interception. Strict JSON tests retain the historical extra-opening-brace and duplicate QA-components failure shapes as invalid.

The guard intercepted one deliberate network probe in targeted tests and ten in existing safety tests; none was sent. Imports were checked in a fresh process for environment mutation, network activity and cloud/credential-loader imports. The environment lacks `pytest-asyncio`, producing the pre-existing `asyncio_mode` warning; these selected synchronous suites still pass. No dependency installation or live test was performed. Existing FAISS/SWIG deprecation warnings were also observed.

## Unresolved definitions and Freeze 1 prerequisites

Completed offline work is reviewable, but Milestone 2 does not silently complete missing design definitions.

- [ ] Owner review of this implementation and provenance extracts, and deferred Claude independent challenge. Codex authored and verified the implementation; this is not independent reviewer acceptance.
- [ ] Exact selection byte contract: protocol-version literal, delimiter/escaping, seed/field serialization, newline handling and digest ordering. Approved evidence says “versioned, explicitly delimited string” but does not give the string bytes.
- [ ] Complete candidate scan/skip procedure, global pair/native conflicts and deterministic shortfall receipt behavior. Known fragments: seed **20261001**, fixed table order, candidate-ID tie-break, stop on shortage, no redistribution/substitution. No pilot-v1 ranking semantics were inherited. Selector skip/shortfall tests remain blocked with the procedure; only the disabled selector and independent synthetic quota/diversity validators are tested.
- [ ] Exact opaque-ID generation and packet serialization. Packet validation exists as a pure synthetic-tested function, without packet generation.
- [ ] Final review/binding of runtime, rule code/data/tests, private inventory/supporting evidence, quotas, source hashes and dependency/platform lock. The accepted matcher runtime is explicitly enforced; future reviewer SDK/settings are separate.
- [ ] Final residual-context/owner-audit record schema and rubric/anchor/diagnostic artifacts. No owner audit or anchor packet was created or sealed.
- [ ] Separate authorization to construct Freeze 1 and perform actual sampling in the approved sequence. No freeze-building operation is implemented or invoked here.

The approved local vote object is implemented: exactly label/components/certainty/rationale, fixed enums, components `["qa","summarize"]` only for multi_intent, single-line nonempty rationale ≤25 words and ≤300 Unicode characters, strict parsing, duplicate rejection, no repair. Approved descriptive analysis is implemented for extracted JSON texts, with planned denominators, class separation, anchor correctness against supplied keys, FinLFQA unanimity, owner abstentions, pairwise agreement and descriptive Cohen/Fleiss kappa. No new gate or agreement metric was added. These are pure offline functions, not a full service-response or live-trial report pipeline.

Service-envelope validation remains disabled pending exact approved stop-reason and per-model reasoning-block whitelists and their precedence within groups. These are **reviewer runtime/schema settings**, separate from the selection serialization blocker. Exact decoding, reasoning/output limits, region/profile/SDK settings and raw response admission remain unresolved. Provisional MiniMax R2 and its accepted account-level availability do not establish those settings or live reliability.

Conservative input/output/reasoning token-cost bounds, current supporting price/terms evidence, candidate-specific credit coverage, per-model/total ceilings and recoverable independent backup evidence remain unresolved for future execution. No current price, credit or terms check was performed. These do not block the completed eligibility/exposure/audit components, and are not claimed resolved by offline tests.

After any authorized future selection/Freeze 1, a fresh sealed owner audit, reviewed anchors/diagnostics, complete execution package/Freeze 2, safeguards and a manifest-bound live authorization remain separate prerequisites. Historical v1.2 authorization does not transfer.

## Scope receipt

Changed files: the 17 new package files listed above, five new test files, and this new document. Private additions: four supporting extracts, pre-edit snapshot, four new audit directories and a reproduction receipt under the new offline-only directory. Successful commands, final hashes, tests and integrity evidence are recorded above. Initial fixture/temp failures were corrected without changing accepted rules or quotas. Any scoped local commit is identified in the handoff; private artifacts and unrelated documents are excluded.

No real ranking, sampling, real packet/witness construction, Freeze 1/2, model invocation, AWS operation, external data/API call, deployment, remote Git mutation or push occurred. Internal app-history reads were used to recover prior accepted design evidence. No secrets were opened. Private questions/IDs were not printed or committed. The designated writer ends edits at handoff; independent acceptance remains outstanding.
