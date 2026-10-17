"""Invented inputs only; no real population reaches selection functions."""

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.reviewer_protocol_v2 import selection as s
from experiments.reviewer_protocol_v2.common import (
    ProtocolError, canonical, question_hash, sha_bytes, verified_bytes,
)


def synthetic_rows(extra=0):
    rows = []
    for entry in s.STRATUM_ENTRIES:
        for _ in range(entry["quota"] + extra):
            number = len(rows) + 1
            question = sha_bytes(f"invented synthetic question {number}".encode())
            rows.append(dict(cand_id=f"c_{number:010x}", question=question,
                             source=entry["source"], sampling_stratum=entry["native_sampling_stratum"],
                             source_revision="invented-revision", context_group=f"invented-group-{number}",
                             question_sha256=question_hash(question), implementation_sha256="a" * 64,
                             eligibility={"disposition": "SCREEN_PASS"},
                             exposure=dict(direct=False, native_group=False, near_duplicate=False),
                             final_unexposed_screen_pass=True))
    return rows


def bound_fixture(root, rows=None):
    rows = synthetic_rows() if rows is None else rows
    for relative in s.BUNDLE_PATHS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s.repository_source_path(relative), target)
    historical = "heldout-external/synthetic/select_pilot.py"
    target = root / historical
    target.parent.mkdir(parents=True, exist_ok=True)
    # Read frozen source code only, never its data or execute its selector.
    # External, frozen evidence is not a file in the executing checkout. A
    # nonstandard test workspace can supply its location, never a different pin.
    evidence_root = Path(os.environ.get("REVIEWER_TEST_EVIDENCE_ROOT", s.SOURCE_ROOT.parent))
    target.write_bytes(verified_bytes(
        evidence_root / "heldout-external/pilot-v1/select_pilot.py", s.SOURCE_SHA256,
    ))
    artifacts = {}
    for name, raw in (
        ("population", b"".join(canonical({k: row[k] for k in s.FIELDS}) for row in rows)),
        ("eligibility_ledger", b"".join(canonical(row) for row in rows)),
        ("exposure_inventory", canonical({"fixture": "invented inventory"})),
        ("selection_specification", b"invented synthetic specification\n"),
    ):
        relative = f"heldout-external/synthetic/{name}.jsonl"
        (root / relative).write_bytes(raw)
        artifacts[name] = dict(path=relative, sha256=sha_bytes(raw))
    code = {"ledger_audit_implementation_sha256": "a" * 64,
            "historical_similarity_source": dict(path=historical, sha256=s.SOURCE_SHA256),
            "selection_bundle": s.selection_bundle()}
    for name, filename in (("eligibility_module", "eligibility.py"), ("similarity_module", "similarity.py")):
        path = s.PREFIX + filename
        code[name] = dict(path=path, sha256=sha_bytes((root / path).read_bytes()))
    binding = dict(schema="reviewer-protocol-v2-selection-inputs-v1", artifacts=artifacts, code=code,
                   runtime=s.runtime_binding(), seed=s.SEED, strata=list(s.STRATUM_ENTRIES))
    return binding, sha_bytes(canonical(binding))


def test_two_identical_reproductions(tmp_path, capsys):
    outputs = []
    for name in ("first", "second"):
        root = tmp_path / name
        binding, digest = bound_fixture(root)
        assert str(root) not in canonical(binding).decode()
        outputs.append(s.select_bound_inputs(root, binding, digest))
    assert outputs[0] == outputs[1]
    print(json.dumps({name: sha_bytes(raw) for name, raw in outputs[0].items()}, sort_keys=True))


@pytest.mark.parametrize("mutation", [
    lambda r: r[0].update(cand_id=True),
    lambda r: r[0].update(source="finlfqa"),
    lambda r: r[0].update(sampling_stratum="interp"),
    lambda r: r[0].update(question_sha256="0" * 64),
    lambda r: r[0].update(final_unexposed_screen_pass=1),
    lambda r: r[0]["exposure"].update(direct=0),
    lambda r: r[0]["eligibility"].update(disposition="INPUT_INVALID"),
    lambda r: r[1].update(cand_id=r[0]["cand_id"]),
    lambda r: r[0].update(question="\ud800"),
])
def test_bad_inputs_before_ranking(tmp_path, monkeypatch, mutation):
    rows = synthetic_rows()
    mutation(rows)
    binding, digest = bound_fixture(tmp_path, rows)
    monkeypatch.setattr(s, "ranking_digest", lambda r: pytest.fail("ranking reached"))
    with pytest.raises((ProtocolError, UnicodeError)):
        s.select_bound_inputs(tmp_path, binding, digest)


@pytest.mark.parametrize("field,value", [("seed", True), ("seed", "20261001"), ("seed", 20261002)])
def test_seed_types(tmp_path, field, value):
    binding, _ = bound_fixture(tmp_path)
    binding[field] = value
    with pytest.raises(ProtocolError):
        s.prepare_inputs(tmp_path, binding, sha_bytes(canonical(binding)))


@pytest.mark.parametrize("path", ["../main/a", "main/../a", "C:/a", "main\\a", "/main/a", "main//a"])
def test_paths_fail_closed(tmp_path, path):
    with pytest.raises(ProtocolError):
        s.bound_path(tmp_path, path)


def test_binding_types_hashes_and_module_closure(tmp_path):
    binding, digest = bound_fixture(tmp_path)
    s.prepare_inputs(tmp_path, binding, digest)
    assert set(s.selection_bundle()["files"]) == set(s.BUNDLE_PATHS)
    assert binding["code"]["ledger_audit_implementation_sha256"] != s.selection_bundle()["sha256"]
    for mutate in (
        lambda b: b["strata"][0].update(quota=True),
        lambda b: b["runtime"].update(float_radix=True),
        lambda b: b["code"].update(eligibility_module=[]),
        lambda b: b["artifacts"]["population"].update(sha256="0" * 64),
        lambda b: b["code"]["selection_bundle"]["files"].pop(s.BUNDLE_PATHS[0]),
        lambda b: b.update(extra=1),
    ):
        changed = copy.deepcopy(binding)
        mutate(changed)
        with pytest.raises(ProtocolError):
            s.prepare_inputs(tmp_path, changed, sha_bytes(canonical(changed)))


def test_raw_digest_ties(monkeypatch):
    rows = synthetic_rows()
    monkeypatch.setattr(s, "ranking_digest", lambda r: b"\x80" * 32)
    assert [r["cand_id"] for _, r in s.ranked_stratum(rows[::-1], "TAT-QA")] == sorted(r["cand_id"] for r in rows[:4])
    a = rows[0]
    b = dict(a, source="finqa")
    assert s.ranking_key(b) < s.ranking_key(a)
    assert s.ranking_key(a)[0] == b"\x80" * 32


def test_all_conflicts_in_acceptance_order():
    rows = synthetic_rows()
    first = rows[0]
    second = dict(first, cand_id="c_0000000099", context_group="separate")
    conflicts = s.conflicts_with(first, [first, second])
    assert [c["code"] for c in conflicts] == ["NATIVE_GROUP_CONFLICT", "DIRECT_SIMILARITY_CONFLICT", "DIRECT_SIMILARITY_CONFLICT"]
    assert conflicts[0]["similarity_hex"] is None
    assert [c["with_candidate_id"] for c in conflicts] == [first["cand_id"], first["cand_id"], second["cand_id"]]


def test_threshold_and_direct_pairs(monkeypatch):
    a, b, c = synthetic_rows()[:3]
    monkeypatch.setattr(s, "cos", lambda x, y: .9 if y == s.grams(a["question"]) and x == s.grams(b["question"]) else .89)
    assert s.conflicts_with(b, [a])[0]["similarity_hex"] == (.9).hex()
    assert not s.conflicts_with(c, [a])  # A skipped neighbor never propagates a conflict.


def test_prepare_all_stop_at_quota(monkeypatch):
    rows = synthetic_rows(extra=1)
    prepared, scanned = [], []
    rank, conflicts = s.ranking_digest, s.conflicts_with
    monkeypatch.setattr(s, "ranking_digest", lambda r: (prepared.append(r["cand_id"]), rank(r))[1])
    def observe(row, accepted):
        label = s.stratum_label(row)
        assert all(r["cand_id"] in prepared for r in rows if s.stratum_label(r) == label)
        scanned.append(row["cand_id"])
        return conflicts(row, accepted)
    monkeypatch.setattr(s, "conflicts_with", observe)
    accepted, receipt = s.scan(rows, "a" * 64)
    assert len(prepared) == 30 and len(scanned) == len(accepted) == 24
    assert receipt["status"] == "SUCCESS"


def test_shortfall_no_later_preparation_or_ids(tmp_path, monkeypatch):
    from experiments.reviewer_protocol_v2 import packet_serialization as p
    rows = synthetic_rows()[1:]
    binding, digest = bound_fixture(tmp_path, rows)
    reached = []
    rank = s.ranked_stratum
    monkeypatch.setattr(s, "ranked_stratum", lambda rows, label: (reached.append(label), rank(rows, label))[1])
    monkeypatch.setattr(p, "external_id", lambda r: pytest.fail("ID reached"))
    monkeypatch.setattr(p, "build_external_outputs", lambda *a: pytest.fail("packet reached"))
    output = s.select_bound_inputs(tmp_path, binding, digest)
    assert set(output) == {"selection_receipt.json"}
    assert set(reached) == {"TAT-QA"}
    receipt = json.loads(output["selection_receipt.json"])
    assert receipt["status"] == "SHORTFALL" and receipt["packet_sha256"] is None
    assert all(r["status"] == "NOT_STARTED" for r in receipt["stratum_results"][1:])


def test_feasible_graph_can_greedy_shortfall():
    rows = synthetic_rows(extra=1)
    # Keep exactly two mixed candidates, and seven interpretive candidates.
    rows = [r for r in rows if s.stratum_label(r) != "FinLFQA mixed"] + [r for r in synthetic_rows() if s.stratum_label(r) == "FinLFQA mixed"]
    # Reassign globally unique synthetic IDs after combining invented rows.
    for i, r in enumerate(rows, 1):
        r["cand_id"] = f"c_{i:010x}"
        r["question"] = sha_bytes(f"invented feasible graph {i}".encode())
        r["question_sha256"] = question_hash(r["question"])
        r["context_group"] = f"invented-feasible-group-{i}"
    interp = [r for _, r in s.ranked_stratum(rows, "FinLFQA interpretive")]
    mixed = [r for r in rows if s.stratum_label(r) == "FinLFQA mixed"]
    interp[0]["context_group"] = mixed[0]["context_group"] = "invented-shared"
    _, receipt = s.scan(rows, "a" * 64)
    assert receipt["stopped_stratum"] == "FinLFQA mixed"
    witness = [r for r in rows if r is not interp[0]]
    _, alternative = s.scan(witness, "a" * 64)
    assert alternative["status"] == "SUCCESS"


@pytest.mark.parametrize("mutation", [
    lambda r: r.update(seed=True), lambda r: r.update(extra=0),
    lambda r: r["decisions"][0].update(scan_index=True),
    lambda r: r["decisions"][0].update(rank_sha256="0" * 64),
    lambda r: r["decisions"][0].update(conflicts=[{}]),
    lambda r: r["stratum_results"][0].update(accepted=True),
    lambda r: r["accepted_identities"].reverse(),
    lambda r: r.update(packet_sha256="0" * 64),
    lambda r: r["decisions"].pop(),
])
def test_receipt_mutations(tmp_path, mutation):
    from experiments.reviewer_protocol_v2.packet_serialization import validate_result
    binding, digest = bound_fixture(tmp_path)
    output = s.select_bound_inputs(tmp_path, binding, digest)
    receipt = json.loads(output["selection_receipt.json"])
    mutation(receipt)
    output["selection_receipt.json"] = canonical(receipt)
    with pytest.raises(ProtocolError):
        validate_result(tmp_path, binding, digest, output)


def test_cli_disabled_audit_verify_disconnected(tmp_path, monkeypatch):
    from experiments.reviewer_protocol_v2 import audit, packet_serialization as p
    from experiments.reviewer_protocol_v2.__main__ import main
    def fail(*a, **k):
        pytest.fail("selection operation reached through audit/verify")
    for module, name in ((s, "ranking_digest"), (s, "select_bound_inputs"), (p, "external_id"), (p, "build_external_outputs")):
        monkeypatch.setattr(module, name, fail)
    with pytest.raises(ProtocolError, match="selection_disabled"):
        s.select([])
    with pytest.raises(SystemExit):
        main(["select"])
    # Actual audit computation, writing and manifest verification, with invented inputs.
    population = [{k: r[k] for k in s.FIELDS} for r in synthetic_rows()]
    inventory = dict(schema="known_exposure_inventory_v2", pilot_items=[], outside_items=[],
                     references=[], evidence=[], unresolved=[])
    monkeypatch.setattr(audit, "load_population", lambda *a: population)
    monkeypatch.setattr(audit, "reconstruct", lambda *a: inventory)
    monkeypatch.setattr(audit, "verify_historical", lambda *a: {"fixture": "invented integrity"})
    monkeypatch.setattr(audit, "verify_isolation", lambda *a: s.SOURCE_SHA256)
    output = tmp_path / "heldout-external/reviewer-protocol-v2-offline/synthetic"
    assert main(["audit", "--root", str(tmp_path), "--output", str(output)]) == 0
    assert main(["verify", "--directory", str(output)]) == 0


def test_direct_skip_does_not_propagate(monkeypatch):
    rows = synthetic_rows(extra=1)
    first = [r for r in rows if s.stratum_label(r) == "TAT-QA"]
    monkeypatch.setattr(s, "ranking_digest", lambda r: int(r["cand_id"][2:], 16).to_bytes(32, "big"))
    links = {(first[0]["question"], first[1]["question"]),
             (first[1]["question"], first[2]["question"])}
    vectors = {tuple(sorted(s.grams(r["question"]).items())): r["question"] for r in rows}
    def score(a, b):
        pair = (vectors[tuple(sorted(a.items()))], vectors[tuple(sorted(b.items()))])
        return .9 if pair in links or pair[::-1] in links else 0.
    monkeypatch.setattr(s, "cos", score)
    accepted, receipt = s.scan(rows, "a" * 64)
    assert first[1] not in accepted and first[2] in accepted
    assert receipt["decisions"][1]["decision"] == "SKIPPED"
    assert receipt["decisions"][1]["conflicts"][0]["similarity_hex"] == (.9).hex()


def test_shortfall_receipt_rejects_extra_packet(tmp_path):
    from experiments.reviewer_protocol_v2.packet_serialization import validate_result
    binding, digest = bound_fixture(tmp_path, synthetic_rows()[1:])
    output = s.select_bound_inputs(tmp_path, binding, digest)
    output["external_blind.jsonl"] = b"invented invalid partial packet\n"
    with pytest.raises(ProtocolError):
        validate_result(tmp_path, binding, digest, output)


def test_population_ledger_metadata_mismatch(tmp_path, monkeypatch):
    binding, _ = bound_fixture(tmp_path)
    path = tmp_path / binding["artifacts"]["eligibility_ledger"]["path"]
    rows = s.jsonl_records(path.read_bytes())
    rows[0]["source"] = "finqa"  # Valid native pair, wrong authoritative identity.
    raw = b"".join(canonical(r) for r in rows)
    path.write_bytes(raw)
    binding["artifacts"]["eligibility_ledger"]["sha256"] = sha_bytes(raw)
    monkeypatch.setattr(s, "ranking_digest", lambda r: pytest.fail("ranking reached"))
    with pytest.raises(ProtocolError, match="ledger_metadata"):
        s.select_bound_inputs(tmp_path, binding, sha_bytes(canonical(binding)))


def test_bundle_covers_loaded_repository_dependencies():
    program = '''
from tests.offline_guard import install
install()
import sys
from experiments.reviewer_protocol_v2 import selection as s, packet_serialization
loaded = {m.__file__ for name, m in sys.modules.items()
          if name == "experiments" or name.startswith("experiments.")}
expected = {str(s.repository_source_path(p)) for p in s.BUNDLE_PATHS}
assert loaded == expected, "unbound repository dependency"
'''
    result = subprocess.run([sys.executable, "-B", "-c", program], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
