"""Regressions for confirmed Claude findings. All API evidence is invented."""

import copy
import json
import sys
from pathlib import Path

import pytest

from experiments.reviewer_protocol_v2 import ledger_adoption as a
from experiments.reviewer_protocol_v2 import production_preparation as p
from experiments.reviewer_protocol_v2 import procedure_evidence as e
from experiments.reviewer_protocol_v2 import selection as s
from experiments.reviewer_protocol_v2 import similarity
from experiments.reviewer_protocol_v2.common import ProtocolError, canonical, sha_bytes
from tests.test_reviewer_v2_adoption_encoding import (
    complete_fixture,
    verify,
    artifact,
    replace_artifact,
)
from tests.test_reviewer_v2_preparation import adoption
from tests.test_reviewer_v2_selection import bound_fixture


@pytest.mark.parametrize(
    "raw",
    [
        b"import importlib\nimportlib.import_module('boto3')\n",
        b"__import__('botocore')\n",
        b"load=__import__\n",
        b"from experiments.router_bench import run\n",
        b"from importlib import import_module as loader\n",
        b"exec('import boto3')\n",
        b"eval('1')\n",
        b"getattr(object(), 'loader')()\n",
    ],
)
def test_demonstrated_dependency_bypasses(raw):
    with pytest.raises(ProtocolError):
        a.dependency_modules({"invented.py": raw})


def test_owner_and_lazy_dependency_closure(tmp_path):
    f, freeze = complete_fixture(tmp_path)
    assert s.PREFIX + "owner_audit.py" in p.VERIFICATION_BUNDLE_PATHS
    assert s.PREFIX + "analysis.py" in p.VERIFICATION_BUNDLE_PATHS
    sources = dict(f["executing_sources"])
    sources.pop(s.PREFIX + "owner_audit.py")
    with pytest.raises(ProtocolError, match="RUNTIME_REPOSITORY_CLOSURE"):
        a.dependency_modules(sources)
    before = {name for name in sys.modules if name.startswith("experiments.")}
    result = verify(f, freeze)
    assert result["proposed_freeze_compatible"] is True
    loaded = {
        str(Path(m.__file__).resolve())
        for name, m in sys.modules.items()
        if (
            name == "experiments" or name.startswith("experiments.reviewer_protocol_v2")
        )
        and m.__file__
    }
    expected = {
        str((s.SOURCE_ROOT / path).resolve()) for path in p.VERIFICATION_BUNDLE_PATHS
    }
    assert expected <= loaded
    assert {
        str(Path(sys.modules[name].__file__).resolve())
        for name in set(sys.modules) - before
        if name.startswith("experiments.") and sys.modules[name].__file__
    } <= expected


def test_non_specification_and_wrong_e01_are_rejected(tmp_path):
    f, freeze = complete_fixture(tmp_path)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    fb = procedure["rules"]["eligibility_specification"]["specification"]
    value = json.loads((tmp_path / fb["path"]).read_bytes())
    value["contract"]["rule_dispositions"]["E01"] = "DEPENDENCE_EXCLUDED"
    replace_artifact(f, freeze, "eligibility_specification", value)
    # Rejoin the procedure to the altered proposed specification to reach content validation.
    procedure["rules"]["eligibility_specification"]["specification"] = freeze[
        "artifacts"
    ]["eligibility_specification"]
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    assert verify(f, freeze)["code"] == "normative_rule_contract"
    procedure["rules"]["eligibility_specification"]["specification"] = dict(
        path="heldout-external/reviewer-protocol-v2-offline/document-quotes.json",
        sha256=sha_bytes(
            (
                tmp_path
                / "heldout-external/reviewer-protocol-v2-offline/document-quotes.json"
            ).read_bytes()
        ),
    )
    freeze["artifacts"]["eligibility_specification"] = procedure["rules"][
        "eligibility_specification"
    ]["specification"]
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    assert verify(f, freeze)["code"] == "schema_keys"


@pytest.mark.parametrize(
    "role",
    [
        "synthetic_test_manifest",
        "definitive_heldout_exclusion_policy",
        "design_approval_evidence",
        "selection_specification",
    ],
)
def test_hash_only_role_is_no_longer_sufficient(tmp_path, role):
    f, freeze = complete_fixture(tmp_path)
    replace_artifact(f, freeze, role, dict(approved=True))
    assert verify(f, freeze)["proposed_freeze_compatible"] is False


def test_altered_actual_test_binding(tmp_path):
    f, freeze = complete_fixture(tmp_path)
    value = artifact(f, freeze, "synthetic_test_manifest")
    value["tests"][e.TEST_PATHS[0]] = "0" * 64
    replace_artifact(f, freeze, "synthetic_test_manifest", value)
    assert verify(f, freeze)["code"] == "input_hash_mismatch"


def test_parse_hashed_population_buffer(tmp_path, monkeypatch):
    binding, digest = bound_fixture(tmp_path)
    target = (tmp_path / binding["artifacts"]["population"]["path"]).resolve()
    original = Path.read_bytes
    reads = 0

    def changing(path):
        nonlocal reads
        if path.resolve() == target:
            reads += 1
            if reads > 1:
                return b"unverified replacement buffer\n"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", changing)
    assert len(s.prepare_inputs(tmp_path, binding, digest)) == 24
    assert reads == 1


def test_parse_hashed_similarity_buffer(tmp_path, monkeypatch):
    binding, _ = bound_fixture(tmp_path)
    target = tmp_path / binding["code"]["historical_similarity_source"]["path"]
    original = Path.read_bytes
    reads = 0

    def changing(path):
        nonlocal reads
        if path.resolve() == target.resolve():
            reads += 1
            assert reads == 1, "Unverified historical source reread"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", changing)
    assert similarity.verify_isolation(target) == similarity.SOURCE_SHA256


def test_provenance_verified_failure_is_false_and_sanitized(tmp_path, monkeypatch):
    f, freeze = complete_fixture(tmp_path)
    f["code_bindings"]["selection_bundle"] = {}
    result = verify(f, freeze)
    assert (
        result["historical_provenance_verified"]
        and result["proposed_freeze_compatible"] is False
    )
    for exception in (
        IndexError("private sentinel"),
        LookupError("private sentinel"),
        RecursionError("private sentinel"),
    ):

        def fail(*args):
            raise exception

        monkeypatch.setattr(a, "_history", fail)
        result = adoption(f)
        assert result["code"] == "MALFORMED_OR_MISSING_EVIDENCE"
        assert "sentinel" not in canonical(result).decode()


def test_forged_report_and_phase_gate(tmp_path):
    f, freeze = complete_fixture(tmp_path)
    raw = canonical(freeze)
    digest = sha_bytes(raw)
    binding, report = p.prepare(
        **f, proposed_freeze1=raw, trusted_expected_freeze1_sha256=digest
    )
    with pytest.raises(ProtocolError, match="preparation_replay_evidence_required"):
        p.validate_preparation(tmp_path, binding, report, sha_bytes(binding), digest)
    context = dict(f, proposed_freeze1=raw, trusted_expected_freeze1_sha256=digest)
    assessment = p.validate_preparation(
        tmp_path,
        binding,
        report,
        sha_bytes(binding),
        digest,
        verification_context=context,
    )
    assert (
        assessment["approval_assessed"] is False
        and assessment["operational_readiness"] is False
    )
    grant = canonical(
        dict(
            schema="reviewer-protocol-v2-selection-authorization-v1",
            operation="SELECTION",
            inputs_sha256=sha_bytes(binding),
            freeze1_sha256=digest,
            ledger_seal_sha256="a" * 64,
            procedure_sha256="b" * 64,
            destination_policy=dict(
                path="heldout-external/invented-policy.json", sha256="c" * 64
            ),
        )
    )
    assert p.selection_phase_predicate(
        assessment,
        grant,
        sha_bytes(grant),
        "FREEZE_1_LEDGER_SEALED",
        "a" * 64,
        "b" * 64,
    )
    for phase, trust, seal in [
        ("PRE_FREEZE_1", sha_bytes(grant), "a" * 64),
        ("FREEZE_1_LEDGER_SEALED", None, "a" * 64),
        ("FREEZE_1_LEDGER_SEALED", "0" * 64, "a" * 64),
        ("FREEZE_1_LEDGER_SEALED", sha_bytes(grant), "0" * 64),
    ]:
        assert not p.selection_phase_predicate(
            assessment, grant, trust, phase, seal, "b" * 64
        )
    broken = copy.deepcopy(context)
    path = tmp_path / broken["artifacts"]["selection_specification"]["path"]
    path.write_bytes(b"Altered invented specification")
    with pytest.raises(
        ProtocolError, match="preparation_evidence_replay|input_hash_mismatch"
    ):
        p.validate_preparation(
            tmp_path,
            binding,
            report,
            sha_bytes(binding),
            digest,
            verification_context=broken,
        )


@pytest.mark.parametrize("kind", ["owner_audit", "analysis_population"])
def test_missing_owner_specification_coverage(tmp_path, kind):
    f, freeze = complete_fixture(tmp_path)
    value = artifact(f, freeze, "remaining_interfaces_specification")
    value["specifications"].pop(kind)
    replace_artifact(f, freeze, "remaining_interfaces_specification", value)
    assert verify(f, freeze)["code"] == "interface_specification_set"


@pytest.mark.parametrize(
    "field,value",
    [
        ("transitive", True),
        ("threshold_hex", (0.89).hex()),
        ("context_groups_sha256", "0" * 64),
        ("native_group", False),
    ],
)
def test_exclusion_policy_content(tmp_path, field, value):
    f, freeze = complete_fixture(tmp_path)
    policy = artifact(f, freeze, "definitive_heldout_exclusion_policy")
    policy[field] = value
    replace_artifact(f, freeze, "definitive_heldout_exclusion_policy", policy)
    assert verify(f, freeze)["code"] == "exclusion_policy_binding"


def test_origin_check_and_exact_runtime(tmp_path, monkeypatch):
    f, freeze = complete_fixture(tmp_path)
    module = sys.modules["experiments.reviewer_protocol_v2.owner_audit"]
    monkeypatch.setattr(
        module.__spec__, "origin", str(tmp_path / "invented-other-source.py")
    )
    assert verify(f, freeze)["code"] == "executing_source_origin"
    monkeypatch.undo()
    lock = artifact(f, freeze, "runtime_dependency_lock")
    lock["runtime"]["platform"] = "Invented updated OS"
    replace_artifact(f, freeze, "runtime_dependency_lock", lock)
    assert verify(f, freeze)["code"] == "ADOPTION_PROPOSED_RUNTIME"


def test_current_decision_is_not_historical_input_or_approval(tmp_path):
    f, freeze = complete_fixture(tmp_path)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    record = procedure["rules"]["eligibility_specification"]
    spec = json.loads((tmp_path / record["specification"]["path"]).read_bytes())
    decision = spec["decision_evidence"]
    assert decision["path"] not in procedure["input_closure"]
    value = json.loads((tmp_path / decision["path"]).read_bytes())
    value["approval_authenticated"] = True
    raw = canonical(value)
    with pytest.raises(ProtocolError, match="current_owner_decision"):
        e.current_decision(raw)
