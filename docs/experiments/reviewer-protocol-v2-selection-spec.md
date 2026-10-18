# Reviewer Protocol v2: accepted external selection contract

Owner-authorized implementation of the accepted selection specification, based
on commit `182f13192809676a9a5d4fa27579df3d58211ce3`. This document and implementation
cover only 24 external items. No real selection or freeze has been executed.
The real `select()` entry point raises `selection_disabled_pending_real_authorization`;
the CLI exposes only the existing audit and verify operations.

## Authoritative inputs and paths

Project root is the workspace containing `main/` and `heldout-external/`.
Bindings contain relative POSIX paths, never machine-specific absolute paths.
Only those two roots are allowed; empty segments, dot segments, traversal,
backslashes and colons are rejected. Resolved paths must remain inside both the
project and the named approved root, including after symlink resolution.
The four private artifacts must occupy distinct paths under `heldout-external/`.

Population and historical eligibility ledger are hash-verified JSONL inputs.
Every ledger row must match the canonical population's `cand_id`, `question`,
`source`, `sampling_stratum`, `source_revision` and `context_group` strings.
Candidate IDs obey `c_[0-9a-f]{10}` and are globally unique; qualified identities
are therefore also unique. Source/native stratum pairs must be registered below.
All original question hashes are lowercase SHA-256 of strict UTF-8 question bytes,
without an added newline. Unpaired surrogates fail before ranking. The ledger's
`implementation_sha256` binds its historical audit implementation separately
from the new selector bundle.

The selector does not reopen eligibility or exposure discovery. It verifies the
historical dispositions (`SCREEN_PASS`, `DEPENDENCE_EXCLUDED`, `DIAGNOSTIC_ONLY`,
`INPUT_INVALID`), Boolean exposure flags `direct`, `native_group`, `near_duplicate`,
and Boolean `final_unexposed_screen_pass`. That final flag must equal
`disposition == SCREEN_PASS and not any(exposure flags)`. Only true final flags
enter ranking. Integers never accept JSON Booleans.

| Selection literal | Ledger source | Ledger sampling_stratum | Quota |
|---|---|---|---:|
| TAT-QA | tatqa | T1_qa | 4 |
| FinQA | finqa | T1_qa | 4 |
| FinLFQA numerical | finlfqa | num | 4 |
| FinLFQA interpretive | finlfqa | interp | 6 |
| FinLFQA other | finlfqa | other | 4 |
| FinLFQA mixed | finlfqa | mixed | 2 |

## Bytes, ranking and greedy scan

Define `B(value)` exactly as
`json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8", errors="strict")`.
There is no BOM, trailing newline, normalization, trimming or case conversion.
The seed is JSON integer `20261001`.

Rank preimage is
`["reviewer-protocol-v2-rank-v1",20261001,stratum,source,candidate_id]`.
Use the authoritative source and cand_id fields; never infer identity from text.
Within the current stratum, prepare keys for **all eligible candidates before
scanning**, then sort by raw 32-byte SHA-256 digest, strict UTF-8 candidate-ID
bytes, and strict UTF-8 source bytes, ascending in that order.

For each stratum in the table order, scan once. Compare each candidate with every
globally accepted external item in acceptance order. A native conflict is an
equal `(source, context_group)` pair. A direct similarity conflict is frozen
historical char-4-gram cosine `>= 0.90`; use the existing pure `grams` and `cos`
without normalization changes or epsilon. Record native conflict first and
similarity conflict second for each accepted item, even when both apply.
The similarity evidence is the exact `float.hex()` string. Skip candidates with
any conflict and accept the others. Skipped items never become comparison seeds.

Stop scanning immediately at quota; prepared but unscanned candidates receive
no decision or conflict inspection. Exhaustion below quota ends the entire run
as SHORTFALL, without preparing later strata. There is no backtracking, swap,
alternate seed, quota redistribution or repair. Partial identities exist only
in the private diagnostic receipt. No external ID, mapping or blind packet is
generated on SHORTFALL. General graph feasibility does not imply greedy success;
the accepted population's any-ranking completion proof is specific to that graph.

## IDs and external bytes

Opaque ID preimage is
`["reviewer-protocol-v2-external-id-v1",20261001,source,candidate_id,original_question_sha256]`.
Apply B and emit `x_` plus the full 64 lowercase SHA-256 hexadecimal characters.
Verify the original question hash first. Duplicate or colliding IDs are hard
errors. IDs are pseudonymous; they do not guarantee protection from reidentification.

Each blind record has exactly two string keys, `item_id` and `question`.
Preserve the original question verbatim, including Unicode, escapes and embedded
line breaks. Sort records by opaque-ID strict UTF-8 bytes. Each line is sorted-key,
compact, ASCII-escaped, finite JSON encoded UTF-8 with exactly one terminating LF.
The packet hash is SHA-256 of the concatenated exact line bytes. A production
packet has exactly 24 items and the table's exact quotas. The two-record vector
is a byte primitive fixture and cannot pass production validation.

## Exact private schemas

Every private object has exactly the listed keys, including nested objects.
Private JSON uses sorted keys, compact separators, escaped Unicode, finite
numbers, strict UTF-8 and one final LF (`common.canonical`). Hash those exact bytes.
`Hex256` means a string matching `[0-9a-f]{64}`. No timestamps occur in deterministic
selection artifacts. Each required integer uses exact integer type, excluding bool.

```text
FileBinding = {path: relative-path string, sha256: Hex256}
Identity = {source: source string, candidate_id: canonical-ID string}
StratumEntry = {
  stratum: exact selection literal, source: registered source string,
  native_sampling_stratum: registered native string, quota: positive integer
}
InputBinding = {
  schema: "reviewer-protocol-v2-selection-inputs-v1",
  artifacts: {
    population: FileBinding, exposure_inventory: FileBinding,
    eligibility_ledger: FileBinding, selection_specification: FileBinding
  },
  code: {
    ledger_audit_implementation_sha256: Hex256,
    eligibility_module: FileBinding, similarity_module: FileBinding,
    historical_similarity_source: FileBinding,
    selection_bundle: {files: {approved-code-path: Hex256}, sha256: Hex256}
  },
  runtime: {
    python_implementation: "CPython", python_version: "3.13.12",
    unicode_version: "15.1.0", platform: string, machine: string,
    byteorder: "little" or "big", float_radix: 2,
    float_mant_dig: 53, float_max_exp: 1024
  },
  seed: 20261001,
  strata: [the six exact StratumEntry objects in table order]
}
MappingEntry = {
  item_id: opaque-ID string, source: source string,
  candidate_id: canonical-ID string, stratum: selection literal,
  native_sampling_stratum: native string, original_question_sha256: Hex256,
  source_revision: original string, context_group: original string
}
Mapping = {
  schema: "reviewer-protocol-v2-external-map-v1",
  inputs_sha256: Hex256, packet_sha256: Hex256,
  items: [24 MappingEntry objects in opaque-ID UTF-8 byte order]
}
Conflict = {
  code: "NATIVE_GROUP_CONFLICT" or "DIRECT_SIMILARITY_CONFLICT",
  with_source: source string, with_candidate_id: canonical-ID string,
  similarity_hex: null for native, exact float.hex string for similarity
}
Decision = {
  stratum: selection literal, scan_index: positive integer,
  source: source string, candidate_id: canonical-ID string,
  rank_sha256: Hex256, decision: "ACCEPTED" or "SKIPPED",
  conflicts: [all Conflict objects in global acceptance order]
}
StratumResult = {
  stratum: selection literal, quota: exact positive integer,
  status: "FILLED" or "SHORTFALL" or "NOT_STARTED",
  scanned: nonnegative integer, accepted: nonnegative integer,
  skipped: nonnegative integer
}
Receipt = {
  schema: "reviewer-protocol-v2-selection-receipt-v1",
  status: "SUCCESS" or "SHORTFALL", inputs_sha256: Hex256, seed: 20261001,
  stratum_results: [six StratumResult objects in table order],
  decisions: [Decision objects in stratum/scan order],
  accepted_identities: [Identity objects in global acceptance order],
  stopped_stratum: null for success or exhausted selection literal,
  packet_sha256: Hex256 for success or null for shortfall,
  mapping_sha256: Hex256 for success or null for shortfall
}
```

Runtime fields must match the executing runtime, including exact field types.
Historical similarity source is content-hash checked and its two pure functions
are compared by AST without executing the historical selector. Bundle files must
match both the bound workspace files and the actually executing module files.
The trusted expected input-binding SHA-256 is supplied separately by the caller;
an untrusted self-declared hash is not an approval interface.

Hash direction is acyclic: canonical InputBinding hash binds selection; packet
bytes bind Mapping; packet and canonical Mapping hashes bind Receipt. Receipt
hash is external to Receipt. There is no mapping/receipt mutual hash dependency.

`select_bound_inputs(root, binding, expected_sha256)` verifies all inputs, scans,
constructs outputs only on success, then independently validates its returned
bytes. `replay_receipt` consumes recorded events against independently recomputed
ranking and direct conflicts without calling the scan producer. It checks exact
events, counters, accepted order, stop point and status. `validate_result` also
reconstructs packet and mapping, checking bijection, every metadata field,
canonical ordering and all output hashes. Neither API writes files. Failed
validation cannot return or publish a successful artifact set. A future caller
must validate completely before any separately authorized publication.

## Selection bundle and historical integrity

New bundle digest:
`1cd9a742c8a3a10a82ca660c0edeaea3da90229dcaa06454432c17d47890fbf4`.
It hashes the canonical relative-path-to-file-hash dictionary for this complete
repository-local executable dependency list:

```text
main/experiments/__init__.py
main/experiments/reviewer_protocol_v2/__init__.py
main/experiments/reviewer_protocol_v2/common.py
main/experiments/reviewer_protocol_v2/eligibility.py
main/experiments/reviewer_protocol_v2/similarity.py
main/experiments/reviewer_protocol_v2/selection.py
main/experiments/reviewer_protocol_v2/packet_serialization.py
```

Standard-library dependencies are covered by the accepted runtime binding;
historical source and specification are separately bound inputs, not executed
repository dependencies. Tests, the offline guard and audit/verify CLI are not
called by the bound selector. Importing the package has no operational side effects.

The old ledger-audit implementation digest remains
`105be32bc90bbb55a7827050817572bca7d8bf62b6585f08085d948302a60efc`.
It is intentionally distinct from the new bundle digest. No previous output or
manifest has been rewritten to align them. Post-implementation read-only checks
verified all 107 protected files and 72 historical bindings, with pin digest
`ecca3e2632420e537e864d876d736b28215f936adf3ae4badb103bf209a151ae`.
Both original final-1/final-2 manifests remain
`057d63310968ab7784a1f6d88fb5baeffadb5cb3ee4c3119b8a548fbd11e3ad4`;
their four bound payloads passed hash verification. Eight unrelated untracked
documents were preserved.

## Synthetic verification and commands

Only invented identities and questions reached new ranking, ID and serialization
functions. Tests include all 24 owner-supplied byte-length/hash assertions:
seven for each positive vector, two combined-packet assertions and eight negative
preimage assertions. Exact constants are recorded in
`tests/test_reviewer_v2_packet_serialization.py`.
Unicode/LF/escaping, ties, strict types, identity and hash mismatches, native and
direct conflicts, simultaneous reasons, threshold equality, no propagation from
skipped items, preparation before scanning, quota stop, shortfall, feasible greedy
failure, collisions, exact schemas, metadata bijection, canonical order, replay
mutations and audit/verify separation are exercised. Audit/verify separation uses
actual synthetic audit computation and actual manifest verification with all
selection/ID/packet hooks patched to fail if reached.
An isolated guarded subprocess also checks that every loaded repository-local
selector dependency appears in the seven-file bundle, with no missing dependency.

Two synthetic reproductions with distinct temporary roots yielded identical bytes:

| Synthetic output | SHA-256 |
|---|---|
| external_blind.jsonl | 8e852e69fbcecf08c6748a5aad173b6e60fbcd8bf501136589628cb351ade766 |
| private_mapping.json | c0a3022f2417a265a898869393f2d90de979917b116292458e898ed319ebe081 |
| selection_receipt.json | 55e9b28802c3cd867bb2d52aba500b35c2b8f1df7f56e40660460ab5e2009775 |

Commands below were executed in `C:\Projects\AWS Project\main`; these machine
paths describe execution evidence only and are never included in deterministic
input or output bindings. Pytest installs the existing network guard automatically.

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_selection.py tests/test_reviewer_v2_packet_serialization.py -q --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-selection-01'
# Initial fixture verification: 60 passed, 3 fixture failures, corrected.
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_selection.py tests/test_reviewer_v2_packet_serialization.py -q -s --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-selection-02'
# 63 passed; subsequently strengthened isolation/direct-pair/input tests.
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_selection.py tests/test_reviewer_v2_packet_serialization.py tests/test_reviewer_v2_eligibility.py tests/test_reviewer_v2_exposure.py tests/test_reviewer_v2_regression.py tests/test_reviewer_v2_safety.py tests/test_reviewer_v2_validation_analysis.py -q --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-selection-03'
# 250 passed: 66 new synthetic cases plus 184 existing v2 cases.
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_selection.py::test_two_identical_reproductions -q -s --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-selection-04'
# 1 passed; reproduced the three hashes above after all test edits.
.\.venv\Scripts\python.exe -B -m pytest tests/test_reviewer_v2_selection.py tests/test_reviewer_v2_packet_serialization.py tests/test_reviewer_v2_eligibility.py tests/test_reviewer_v2_exposure.py tests/test_reviewer_v2_regression.py tests/test_reviewer_v2_safety.py tests/test_reviewer_v2_validation_analysis.py -q --basetemp 'C:\Projects\AWS Project\main\.pytest_cache\reviewer-v2-selection-05'
# Final verification after adding the independent dependency-closure check:
# 251 passed: 67 new synthetic cases plus 184 existing v2 cases.
.\.venv\Scripts\python.exe -B -c 'from tests.offline_guard import install; install(); import runpy; runpy.run_module("ruff", run_name="__main__")' check experiments/reviewer_protocol_v2/selection.py experiments/reviewer_protocol_v2/packet_serialization.py tests/test_reviewer_v2_selection.py tests/test_reviewer_v2_packet_serialization.py
# All checks passed.
.\.venv\Scripts\python.exe -B -c 'from tests.offline_guard import install; install(); from pathlib import Path; from experiments.reviewer_protocol_v2.integrity import verify_historical, verify_output_manifest; from experiments.reviewer_protocol_v2.selection import selection_bundle; import json; root=Path.cwd().parent; v=verify_historical(root); manifests={name:verify_output_manifest(root / "heldout-external/reviewer-protocol-v2-offline" / name) for name in ("final-1", "final-2")}; print(json.dumps({"protected_files":v["protected_files"],"historical_bindings":v["frozen_bindings"],"pins_sha256":v["pins_sha256"],"historical_manifests":manifests,"selection_bundle":selection_bundle()},sort_keys=True,indent=2))'
# 107 protected files, 72 bindings, both original manifests and new bundle verified.
```

One existing `asyncio_mode` configuration warning appears because pytest-asyncio
is absent; these suites are synchronous. The combined suite deliberately tested
one blocked network lookup: one intercepted, none sent. No outbound call occurred.

## Remaining interfaces and Freeze 1 prerequisites

Independent code review of both the earlier offline components and this change
remains deferred. This implementation does not supply an authorized real-selection
CLI, a production binding-preparation/publishing interface, or permission to run
real ranking. Those require a separate bounded owner authorization after review.
Any future approved real execution must bind exact current private inputs, the
accepted specification and runtime, preserve original audit bindings, and pass
complete replay validation before designating outputs as successful.

Anchor and diagnostic IDs, combined trial order, reviewer-specific presentation
order, owner-audit packets and service-envelope serialization remain unresolved
interfaces outside this external-only contract. Freeze 1 requires the applicable
remaining interfaces to be specified and accepted, required independent review,
successful separately authorized preparation/validation and explicit owner approval.
Freeze 2 and live/model/AWS execution remain separate approval gates.

Scope receipt: five authorized files only; invented selection fixtures only;
historical artifacts and unrelated documents preserved; no real ranking, real IDs,
sampling, real packet, freeze, model invocation, AWS operation, external API call
or push.
