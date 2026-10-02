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
    result = verify(f, freeze)
    assert result["proposed_freeze_compatible"] is False
    assert result["code"] == "schema_keys"


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
            schema="reviewer-protocol-v2-selection-authorization-v2",
            operation="SELECTION",
            inputs_sha256=sha_bytes(binding),
            report_sha256=sha_bytes(report),
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


@pytest.mark.parametrize(
    "raw,code",
    [
        (
            b"import sys\nsys.modules['builtins'].exec('import socket')",
            "RUNTIME_DYNAMIC_LOADING",
        ),
        (b"import sys\nsys.modules['builtins'].eval('1')", "RUNTIME_DYNAMIC_LOADING"),
        (
            b"import sys\nsys.modules['experiments.router_bench']",
            "RUNTIME_STDLIB_ACCESS",
        ),
        (
            b"import sys\nvars(sys.modules['builtins'])['__im'+'port__']('socket')",
            "RUNTIME_DYNAMIC_LOADING",
        ),
        (b"import platform\nplatform.os.system('invented')", "RUNTIME_STDLIB_ACCESS"),
        (b"import sys\nsys.path.insert(0, 'invented')", "RUNTIME_STDLIB_ACCESS"),
        (b"object().exec('invented')", "RUNTIME_DYNAMIC_LOADING"),
        (b"object().eval('invented')", "RUNTIME_DYNAMIC_LOADING"),
        (b"object().compile('invented')", "RUNTIME_DYNAMIC_LOADING"),
        (b"globals()", "RUNTIME_DYNAMIC_LOADING"),
        (b"locals()", "RUNTIME_DYNAMIC_LOADING"),
        (b"import sys as s\ns.modules.get('invented')", "RUNTIME_STDLIB_ACCESS"),
        (b"from sys import modules", "RUNTIME_STDLIB_ACCESS"),
        (b"from platform import os", "RUNTIME_STDLIB_ACCESS"),
        (b"import sys\nsys.meta_path.append(object())", "RUNTIME_STDLIB_ACCESS"),
        (b"import sys\nsys.path_hooks.clear()", "RUNTIME_STDLIB_ACCESS"),
        (b"import platform\nalias = platform\nalias.os", "RUNTIME_MODULE_ALIAS"),
        (b"import json\njson.sys.modules", "RUNTIME_STDLIB_ACCESS"),
        (
            b"import platform\nplatform.platform.__globals__['os']",
            "RUNTIME_DYNAMIC_LOADING",
        ),
        (b"object().globals()", "RUNTIME_DYNAMIC_LOADING"),
    ],
)
def test_r2_exact_probes_and_access_rejections(raw, code):
    with pytest.raises(ProtocolError) as failure:
        a.dependency_modules({"invented.py": raw})
    assert str(failure.value) == code


def test_r2_only_reviewed_sys_modules_shape():
    path = s.PREFIX + "production_preparation.py"
    raw = b"import sys\ndef _executing_sources():\n    module = sys.modules.get(module_name)\n"
    assert a.dependency_modules({path: raw}) == ["sys"]
    for bad in [
        raw.replace(b"_executing_sources", b"unreviewed"),
        raw.replace(b"module_name", b"'builtins'"),
        raw.replace(b"module =", b"other ="),
        raw.replace(b"get(module_name)", b"get(module_name, None)"),
    ]:
        with pytest.raises(ProtocolError) as failure:
            a.dependency_modules({path: bad})
        assert str(failure.value) == "RUNTIME_STDLIB_ACCESS"
    assert a.dependency_modules(
        {"invented.py": b"import re\nre.compile('invented')"}
    ) == ["re"]


def write_evidence(root, fb, value):
    raw = canonical(value)
    (root / fb["path"]).write_bytes(raw)
    return dict(path=fb["path"], sha256=sha_bytes(raw))


def rule_context(root):
    f, freeze = complete_fixture(root)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    history = a._history(
        root,
        f["historical_manifest"],
        f["expected_historical_manifest_sha256"],
        f["generating_sources"],
    )

    def read(fb):
        return a.read_binding(root, fb)

    return f, freeze, procedure, history, read


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("same_wrapper", "algorithm_evidence_distinct"),
        ("same_schema", "schema_version"),
        ("missing_shared", "evidence_shared_origins"),
        ("copied_origin", "evidence_origin_alias"),
        ("altered_raw", "input_hash_mismatch"),
        ("stale_hash", "input_hash_mismatch"),
        ("escape", "relative_path"),
    ],
)
def test_r1_source_and_algorithm_bindings(tmp_path, mutation, code):
    f, freeze, _, _, read = rule_context(tmp_path)
    fb = freeze["artifacts"]["eligibility_specification"]
    spec = json.loads(read(fb))
    text_fb = spec["source_evidence"][0]
    text = json.loads(read(text_fb))
    if mutation == "same_wrapper":
        spec["algorithm_evidence"] = text_fb
    elif mutation == "same_schema":
        algorithm = json.loads(read(spec["algorithm_evidence"]))
        algorithm["schema"] = "reviewer-protocol-v2-rule-text-evidence-v2"
        spec["algorithm_evidence"] = write_evidence(
            tmp_path, spec["algorithm_evidence"], algorithm
        )
    elif mutation == "missing_shared":
        spec["shared_origins"] = []
    elif mutation == "copied_origin":
        algorithm = json.loads(read(spec["algorithm_evidence"]))
        copied = algorithm["record_path"] + ".copy"
        (tmp_path / copied).write_bytes(
            (tmp_path / algorithm["record_path"]).read_bytes()
        )
        algorithm["record_path"] = copied
        spec["algorithm_evidence"] = write_evidence(
            tmp_path, spec["algorithm_evidence"], algorithm
        )
    else:
        if mutation == "altered_raw":
            (tmp_path / text["record_path"]).write_bytes(
                b"Changed invented original record"
            )
        elif mutation == "stale_hash":
            text["record_sha256"] = "0" * 64
        else:
            text["record_path"] = "heldout-external/../invented-escape"
        spec["source_evidence"] = [write_evidence(tmp_path, text_fb, text)]
    with pytest.raises(ProtocolError) as failure:
        e.specification(canonical(spec), "eligibility_specification", read)
    assert str(failure.value) == code


def test_r1_record_hash_is_checked_even_with_unverifying_adapter():
    value = dict(
        record_reference="Invented",
        record_path="heldout-external/invented.txt",
        record_sha256="0" * 64,
    )
    with pytest.raises(ProtocolError) as failure:
        e.source_record(value, lambda fb: b"Invented raw bytes")
    assert str(failure.value) == "source_record_hash"


def test_r1_distinct_originals_require_no_shared_claim(tmp_path):
    _, freeze, _, _, read = rule_context(tmp_path)
    spec = json.loads(read(freeze["artifacts"]["eligibility_specification"]))
    fb = spec["algorithm_evidence"]
    algorithm = json.loads(read(fb))
    raw = b"Invented genuinely different algorithm source record.\n"
    algorithm["record_path"] += ".different"
    algorithm["record_sha256"] = sha_bytes(raw)
    algorithm["record_reference"] = "Invented distinct algorithm source"
    (tmp_path / algorithm["record_path"]).write_bytes(raw)
    spec["algorithm_evidence"] = write_evidence(tmp_path, fb, algorithm)
    spec["shared_origins"] = []
    assert e.specification(canonical(spec), "eligibility_specification", read) == spec


@pytest.mark.parametrize("kind", ["source", "review"])
def test_r1_missing_original_record_is_sanitized(tmp_path, kind):
    f, freeze, procedure, _, read = rule_context(tmp_path)
    rule = procedure["rules"]["eligibility_specification"]
    if kind == "source":
        spec = json.loads(read(rule["specification"]))
        record = json.loads(read(spec["source_evidence"][0]))
    else:
        witness = json.loads(read(rule["relationship_evidence"]))
        record = json.loads(read(witness["semantic_review_evidence"]))
    (tmp_path / record["record_path"]).unlink()
    result = verify(f, freeze)
    assert result["code"] == "missing_input"
    assert result["proposed_freeze_compatible"] is False
    assert record["record_path"] not in canonical(result).decode()


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("contract", "RULE_REVIEW_CONTRACT"),
        ("raw", "input_hash_mismatch"),
        ("hash", "input_hash_mismatch"),
        ("missing_shared", "RULE_REVIEW_SHARED_ORIGINS"),
        ("not_both_roles", "RULE_REVIEW_SHARED_ORIGINS"),
        ("wrong_origin", "RULE_REVIEW_SHARED_ORIGINS"),
    ],
)
def test_r1_review_original_contract_and_shared_roles(tmp_path, mutation, code):
    f, freeze, procedure, history, read = rule_context(tmp_path)
    record = procedure["rules"]["eligibility_specification"]
    witness = json.loads(read(record["relationship_evidence"]))
    fb = witness["semantic_review_evidence"]
    review = json.loads(read(fb))
    if mutation == "contract":
        review["contract_sha256"] = "0" * 64
    elif mutation == "raw":
        (tmp_path / review["record_path"]).write_bytes(
            b"Changed invented review original"
        )
    elif mutation == "hash":
        review["record_sha256"] = "0" * 64
    elif mutation == "missing_shared":
        review["shared_origin_reviews"] = []
    elif mutation == "not_both_roles":
        review["shared_origin_reviews"][0]["supports_both_roles"] = False
    else:
        review["shared_origin_reviews"][0]["record_sha256"] = "0" * 64
    witness["semantic_review_evidence"] = write_evidence(tmp_path, fb, review)
    record["relationship_evidence"] = write_evidence(
        tmp_path, record["relationship_evidence"], witness
    )
    with pytest.raises(ProtocolError) as failure:
        e.rule_bindings(
            procedure,
            freeze["artifacts"],
            history,
            p.verification_bundle(f["executing_sources"]),
            read,
            a.RULE_ROLES,
        )
    assert str(failure.value) == code


@pytest.mark.parametrize("mutation", ["binding", "report", "v1", "stale_trust"])
def test_r3_binding_report_and_version_fail_closed(mutation):
    binding = {"invented": "structural assessment only"}
    assessment = dict(
        schema="reviewer-protocol-v2-technical-preparation-assessment-v1",
        binding=binding,
        inputs_sha256=sha_bytes(canonical(binding)),
        report_sha256="d" * 64,
        freeze1_sha256="f" * 64,
        verification_level="EVIDENCE_REPLAYED",
        approval_assessed=False,
        operational_readiness=False,
    )
    grant = dict(
        schema="reviewer-protocol-v2-selection-authorization-v2",
        operation="SELECTION",
        inputs_sha256=assessment["inputs_sha256"],
        report_sha256=assessment["report_sha256"],
        freeze1_sha256="f" * 64,
        ledger_seal_sha256="a" * 64,
        procedure_sha256="b" * 64,
        destination_policy=dict(
            path="heldout-external/invented-policy.json", sha256="c" * 64
        ),
    )
    raw = canonical(grant)
    trusted = sha_bytes(raw)
    # Structural consistency is possible without authenticating a replay or approval.
    assert p.selection_phase_predicate(
        assessment, raw, trusted, "FREEZE_1_LEDGER_SEALED", "a" * 64, "b" * 64
    )
    if mutation == "binding":
        assessment["binding"] = {"invented": "forged mismatch"}
    elif mutation == "report":
        grant["report_sha256"] = "0" * 64
    elif mutation == "v1":
        grant["schema"] = "reviewer-protocol-v2-selection-authorization-v1"
    else:
        trusted = "0" * 64
    raw = canonical(grant)
    if mutation != "stale_trust":
        trusted = sha_bytes(raw)
    assert not p.selection_phase_predicate(
        assessment, raw, trusted, "FREEZE_1_LEDGER_SEALED", "a" * 64, "b" * 64
    )


@pytest.mark.parametrize(
    "abstained,concern", [(False, False), (True, False), (False, True), (True, True)]
)
def test_r5_note_token_matches_audit_behavior(abstained, concern):
    from experiments.reviewer_protocol_v2 import owner_audit
    from tests.test_reviewer_v2_owner_audit import fixture as owner_fixture

    assert (
        e.INTERFACE_CONTRACTS["owner_audit"]["explanatory_note"]
        == "KEY_REQUIRED_NONEMPTY_IF_ABSTAINED_OR_CONCERN"
    )
    f = owner_fixture()
    audit = json.loads(f[0])
    row = audit["records"][0]
    row.update(abstained=abstained, context_concern=concern)
    if abstained:
        row.update(label=None, components=[], certainty=None)
    if abstained or concern:
        with pytest.raises(ProtocolError) as failure:
            owner_audit.validate_audit(canonical(audit), *f[1:5])
        assert str(failure.value) == "string_type"
        row["note"] = "Invented required explanation"
    owner_audit.validate_audit(canonical(audit), *f[1:5])
    row.pop("note")
    with pytest.raises(ProtocolError) as failure:
        owner_audit.validate_audit(canonical(audit), *f[1:5])
    assert str(failure.value) == "schema_keys"
