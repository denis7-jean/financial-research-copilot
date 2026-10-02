"""Complete adoption compatibility evidence is invented; no real API inputs."""

import json
import subprocess
from pathlib import Path

import pytest

from experiments.reviewer_protocol_v2 import ledger_adoption as a
from experiments.reviewer_protocol_v2 import production_preparation as p
from experiments.reviewer_protocol_v2 import selection as s
from experiments.reviewer_protocol_v2.common import canonical, sha_bytes
from tests.test_reviewer_v2_preparation import adoption, fixture


def complete_fixture(root):
    f = fixture(root)

    def put(name, value, raw=False):
        path = "heldout-external/invented-procedure/" + name
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        data = value if raw else canonical(value)
        target.write_bytes(data)
        return dict(path=path, sha256=sha_bytes(data))

    roles = {
        role: put(
            role + ".txt", ("Invented evidence for " + role + "\n").encode(), raw=True
        )
        for role in a.FREEZE_ROLES
    }
    roles.update(
        population=f["artifacts"]["population"],
        exposure_inventory=f["artifacts"]["exposure_inventory"],
        selection_specification=f["artifacts"]["selection_specification"],
        historical_similarity_source=f["code_bindings"]["historical_similarity_source"],
    )
    sources = {
        name: put("generating/" + name, raw, raw=True)
        for name, raw in f["generating_sources"].items()
    }
    generating = dict(
        schema="reviewer-protocol-v2-historical-generating-bundle-v1",
        recipe=a.HASH_RECIPE,
        sources=sources,
        implementation_sha256=f["code_bindings"]["ledger_audit_implementation_sha256"],
    )
    roles["eligibility_exposure_code_bundle"] = put(
        "generating-bundle.json", generating
    )
    rules = {}
    for role, name in zip(
        a.RULE_ROLES,
        (
            "original-design-evidence.md",
            "revised-design-evidence.md",
            "document-quotes.json",
        ),
        strict=True,
    ):
        path = "heldout-external/reviewer-protocol-v2-offline/" + name
        fb = dict(path=path, sha256=sha_bytes((root / path).read_bytes()))
        roles[role] = fb
        witness = dict(
            schema="reviewer-protocol-v2-historical-rule-relationship-v1",
            role=role,
            original_evidence=fb,
            generating_source=dict(
                filename=a.RULE_ROLES[role],
                sha256=sources[a.RULE_ROLES[role]]["sha256"],
            ),
            specification=fb,
            relation="IDENTICAL_EVIDENCE_BYTES",
        )
        rules[role] = dict(
            original_evidence=fb,
            specification=fb,
            relationship_evidence=put(role + "-relationship.json", witness),
        )
    roles["selection_code_bundle"] = put("selection-bundle.json", s.selection_bundle())
    interfaces = dict(
        schema="reviewer-protocol-v2-adoption-interface-binding-v1",
        specification=put(
            "interfaces-specification.txt",
            b"Invented interface specification.\n",
            raw=True,
        ),
        verification_bundle=p.verification_bundle(f["executing_sources"]),
    )
    roles["remaining_interfaces_specification"] = put("interfaces.json", interfaces)
    lock = dict(
        schema="reviewer-protocol-v2-adoption-runtime-lock-v1",
        scope="OFFLINE_PREPARATION_SELECTION",
        runtime=s.runtime_binding(),
        stdlib_modules=a.dependency_modules(f["executing_sources"]),
        third_party_distributions=[],
    )
    roles["runtime_dependency_lock"] = put("runtime.json", lock)
    inputs_raw, report = p.prepare(**f)
    assert inputs_raw is not None, report
    inputs_fb = put("inputs.json", inputs_raw, raw=True)
    history = a._history(
        root,
        f["historical_manifest"],
        f["expected_historical_manifest_sha256"],
        f["generating_sources"],
    )
    parent = f["historical_manifest"]["path"].rsplit("/", 1)[0]
    procedure = dict(
        schema="reviewer-protocol-v2-historical-adoption-v1",
        audit=dict(
            manifest=f["historical_manifest"],
            payloads={
                name: dict(
                    path=parent + "/" + name, sha256=history["manifest"]["files"][name]
                )
                for name in a.PAYLOADS
            },
        ),
        generating_bundle=roles["eligibility_exposure_code_bundle"],
        recorded_runtime=a.RECORDED_RUNTIME,
        pin_map=sources["input_hashes.json"],
        additional_inputs={path: history["inputs"][path] for path in a.EXTRA_INPUTS},
        input_closure=history["inputs"],
        input_closure_sha256=sha_bytes(canonical(history["inputs"])),
        rules=rules,
        proposed_runtime_dependency_lock=roles["runtime_dependency_lock"],
        current_bindings=dict(
            selection_bundle=roles["selection_code_bundle"],
            remaining_interfaces=roles["remaining_interfaces_specification"],
        ),
        selection_inputs=inputs_fb,
    )
    roles["historical_integrity_manifest"] = put("adoption.json", procedure)
    freeze = dict(
        schema="reviewer-protocol-v2-freeze-manifest-v1",
        phase="FREEZE_1",
        artifacts=roles,
    )
    return f, freeze


def verify(f, freeze, expected=None):
    raw = canonical(freeze)
    return adoption(
        f,
        proposed_freeze1=raw,
        expected_freeze1_sha256=sha_bytes(raw) if expected is None else expected,
        executing_sources=f["executing_sources"],
    )


def artifact(f, freeze, role):
    return json.loads((f["root"] / freeze["artifacts"][role]["path"]).read_bytes())


def replace_artifact(f, freeze, role, value):
    fb = freeze["artifacts"][role]
    raw = canonical(value)
    (f["root"] / fb["path"]).write_bytes(raw)
    fb["sha256"] = sha_bytes(raw)
    # Update the procedure's same-role FB joins, never any real history.
    if role != "historical_integrity_manifest":
        procedure = artifact(f, freeze, "historical_integrity_manifest")
        if role == "eligibility_exposure_code_bundle":
            procedure["generating_bundle"] = fb
        elif role == "runtime_dependency_lock":
            procedure["proposed_runtime_dependency_lock"] = fb
        elif role == "selection_code_bundle":
            procedure["current_bindings"]["selection_bundle"] = fb
        elif role == "remaining_interfaces_specification":
            procedure["current_bindings"]["remaining_interfaces"] = fb
        replace_artifact(f, freeze, "historical_integrity_manifest", procedure)


def test_complete_positive_and_deterministic_bytes(tmp_path):
    outputs = []
    for name in ("first", "second"):
        f, freeze = complete_fixture(tmp_path / name)
        result = verify(f, freeze)
        assert result["code"] == "BINDINGS_VERIFIED_NOT_ADOPTED", result
        assert (
            result["historical_provenance_verified"]
            and result["proposed_freeze_compatible"]
        )
        assert result["operational_adoption_performed"] is False
        raw = canonical(freeze)
        inputs, report = p.prepare(
            **f, proposed_freeze1=raw, trusted_expected_freeze1_sha256=sha_bytes(raw)
        )
        assert inputs is not None, report
        p.validate_preparation(
            f["root"], inputs, report, sha_bytes(inputs), sha_bytes(raw)
        )
        assert json.loads(report)["freeze1_sha256"] == sha_bytes(raw)
        outputs.append(
            dict(
                freeze=raw,
                procedure=canonical(
                    artifact(f, freeze, "historical_integrity_manifest")
                ),
                report=report,
                result=canonical(result),
            )
        )
    assert outputs[0] == outputs[1]
    print(
        json.dumps(
            {name: sha_bytes(raw) for name, raw in outputs[0].items()}, sort_keys=True
        )
    )


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("recorded_runtime", {}, "ADOPTION_RECORDED_RUNTIME"),
        ("additional_inputs", {}, "ADOPTION_INPUT_CLOSURE"),
        ("input_closure", {}, "ADOPTION_INPUT_CLOSURE"),
        ("input_closure_sha256", "0" * 64, "ADOPTION_INPUT_CLOSURE"),
        ("rules", {}, "RULE_EVIDENCE_SET"),
        (
            "pin_map",
            {"path": "heldout-external/missing", "sha256": "0" * 64},
            "ADOPTION_PIN_MAP_BINDING",
        ),
    ],
)
def test_procedure_mismatch(tmp_path, field, value, code):
    f, freeze = complete_fixture(tmp_path)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    procedure[field] = value
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    assert verify(f, freeze)["code"] == code


@pytest.mark.parametrize(
    "role,field,value",
    [
        (
            "eligibility_exposure_code_bundle",
            "implementation_sha256",
            s.selection_bundle()["sha256"],
        ),
        ("eligibility_exposure_code_bundle", "sources", {}),
        ("eligibility_exposure_code_bundle", "recipe", "semantic_equivalence"),
        ("runtime_dependency_lock", "runtime", {}),
        ("runtime_dependency_lock", "stdlib_modules", []),
        ("runtime_dependency_lock", "third_party_distributions", ["invented-sdk"]),
        ("runtime_dependency_lock", "scope", "LIVE"),
        (
            "remaining_interfaces_specification",
            "verification_bundle",
            s.selection_bundle(),
        ),
    ],
)
def test_source_runtime_dependency_failures(tmp_path, role, field, value):
    f, freeze = complete_fixture(tmp_path)
    changed = artifact(f, freeze, role)
    changed[field] = value
    replace_artifact(f, freeze, role, changed)
    result = verify(f, freeze)
    assert (
        result["proposed_freeze_compatible"] is False
        and result["code"] != "BINDINGS_VERIFIED_NOT_ADOPTED"
    )


@pytest.mark.parametrize("target", ["source", "input", "rule", "lock"])
def test_missing_applicable_evidence(tmp_path, target):
    f, freeze = complete_fixture(tmp_path)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    paths = {
        "source": artifact(f, freeze, "eligibility_exposure_code_bundle")["sources"][
            "analysis.py"
        ]["path"],
        "input": next(iter(procedure["additional_inputs"])),
        "rule": procedure["rules"]["eligibility_specification"][
            "relationship_evidence"
        ]["path"],
        "lock": freeze["artifacts"]["runtime_dependency_lock"]["path"],
    }
    (tmp_path / paths[target]).unlink()
    result = verify(f, freeze)
    assert result["code"] == "missing_input"
    assert result["proposed_freeze_compatible"] is not True


def test_altered_rule_witness_and_source_is_not_specification(tmp_path):
    f, freeze = complete_fixture(tmp_path)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    rule = procedure["rules"]["eligibility_specification"]
    fb = rule["relationship_evidence"]
    witness = json.loads((tmp_path / fb["path"]).read_bytes())
    witness["generating_source"]["sha256"] = s.selection_bundle()["sha256"]
    raw = canonical(witness)
    (tmp_path / fb["path"]).write_bytes(raw)
    fb["sha256"] = sha_bytes(raw)
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    assert verify(f, freeze)["code"] == "RULE_RELATIONSHIP_BINDING"
    rule["original_evidence"] = artifact(f, freeze, "eligibility_exposure_code_bundle")[
        "sources"
    ]["eligibility.py"]
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    assert verify(f, freeze)["code"] in {
        "RULE_ORIGINAL_EVIDENCE_BINDING",
        "RULE_SOURCE_IS_NOT_SPECIFICATION",
    }


@pytest.mark.parametrize(
    "role",
    [
        "historical_integrity_manifest",
        "runtime_dependency_lock",
        "remaining_interfaces_specification",
        "eligibility_exposure_code_bundle",
    ],
)
def test_self_declared_approval_rejected(tmp_path, role):
    f, freeze = complete_fixture(tmp_path)
    changed = artifact(f, freeze, role)
    changed["approval_sha256"] = sha_bytes(canonical(changed))
    replace_artifact(f, freeze, role, changed)
    assert verify(f, freeze)["code"] == "schema_keys"


def test_separate_trust_and_preparation_inputs(tmp_path):
    f, freeze = complete_fixture(tmp_path)
    assert verify(f, freeze, "0" * 64)["code"] == "FREEZE_TRUSTED_HASH"
    raw = canonical(freeze)
    result = adoption(
        f,
        proposed_freeze1=raw,
        expected_freeze1_sha256=sha_bytes(raw),
        executing_sources=f["executing_sources"],
        input_binding_raw=b"invented different binding",
    )
    assert result["code"] == "ADOPTION_PREPARATION_INPUT_BINDING"
    assert (
        adoption(f, proposed_freeze1=raw, expected_freeze1_sha256=sha_bytes(raw))[
            "code"
        ]
        == "CURRENT_VERIFICATION_EVIDENCE_MISSING"
    )


def test_no_writes_or_operational_calls(tmp_path, monkeypatch):
    from experiments.reviewer_protocol_v2 import packet_serialization, trial_interfaces

    f, freeze = complete_fixture(tmp_path)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    def fail(*args, **kwargs):
        pytest.fail("Forbidden side effect")

    for module, names in (
        (s, ("select", "scan", "ranking_digest", "select_bound_inputs")),
        (packet_serialization, ("external_id", "build_external_outputs")),
        (trial_interfaces, ("build_trial", "build_presentations", "build_schedule")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, fail)
    monkeypatch.setattr(Path, "write_bytes", fail)
    monkeypatch.setattr(Path, "write_text", fail)
    assert verify(f, freeze)["proposed_freeze_compatible"] is True
    raw = canonical(freeze)
    assert (
        p.prepare(
            **f, proposed_freeze1=raw, trusted_expected_freeze1_sha256=sha_bytes(raw)
        )[0]
        is not None
    )
    assert before == {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }


@pytest.mark.parametrize(
    "relative",
    [
        "../outside.json",
        "main/../outside.json",
        "C:/outside.json",
        "heldout-external\\outside.json",
    ],
)
def test_nested_path_escape(tmp_path, relative):
    f, freeze = complete_fixture(tmp_path)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    procedure["rules"]["eligibility_specification"]["original_evidence"]["path"] = (
        relative
    )
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    assert verify(f, freeze)["proposed_freeze_compatible"] is False


def test_dependency_scan_rejects_nonstdlib_or_relative_imports():
    with pytest.raises(Exception, match="RUNTIME_DEPENDENCY_NONSTDLIB"):
        a.dependency_modules({"invented.py": b"import invented_missing_sdk\n"})
    with pytest.raises(Exception, match="RUNTIME_DEPENDENCY_IMPORT"):
        a.dependency_modules({"invented.py": b"from . import missing\n"})
    assert a.dependency_modules(
        {"invented.py": b"def nested():\n    import json\n"}
    ) == ["json"]


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("wrong_specification", "RULE_SPECIFICATION_BINDING"),
        ("unbound_original", "RULE_ORIGINAL_EVIDENCE_BINDING"),
        ("extra_closure", "ADOPTION_INPUT_CLOSURE"),
        ("current_historical", "ADOPTION_CURRENT_VERIFICATION_BINDING"),
        ("audit_payload", "ADOPTION_ORIGINAL_AUDIT_BINDING"),
    ],
)
def test_exact_relationship_and_closure_joins(tmp_path, mutation, code):
    f, freeze = complete_fixture(tmp_path)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    if mutation == "wrong_specification":
        procedure["rules"]["eligibility_specification"]["specification"] = freeze[
            "artifacts"
        ]["selection_specification"]
    elif mutation == "unbound_original":
        procedure["rules"]["eligibility_specification"]["original_evidence"] = freeze[
            "artifacts"
        ]["selection_specification"]
    elif mutation == "extra_closure":
        procedure["input_closure"]["heldout-external/invented-unrecorded"] = "0" * 64
        procedure["input_closure_sha256"] = sha_bytes(
            canonical(procedure["input_closure"])
        )
    elif mutation == "audit_payload":
        procedure["audit"]["payloads"]["population_ledger.jsonl"]["sha256"] = "0" * 64
    else:
        value = artifact(f, freeze, "remaining_interfaces_specification")
        value["verification_bundle"]["sha256"] = f["code_bindings"][
            "ledger_audit_implementation_sha256"
        ]
        replace_artifact(f, freeze, "remaining_interfaces_specification", value)
        assert verify(f, freeze)["code"] == code
        return
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    assert verify(f, freeze)["code"] == code


def test_nested_junction_escape(tmp_path):
    root = tmp_path / "workspace"
    f, freeze = complete_fixture(root)
    procedure = artifact(f, freeze, "historical_integrity_manifest")
    fb = procedure["rules"]["eligibility_specification"]["relationship_evidence"]
    outside = tmp_path / "invented-outside"
    outside.mkdir()
    (outside / "witness.json").write_bytes((root / fb["path"]).read_bytes())
    link = root / "heldout-external" / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:

        def quote(value):
            return "'" + str(value).replace("'", "''") + "'"

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "New-Item -ItemType Junction -Path "
                + quote(link)
                + " -Target "
                + quote(outside),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Test-owned junction creation failed"
    fb["path"] = "heldout-external/escape/witness.json"
    replace_artifact(f, freeze, "historical_integrity_manifest", procedure)
    assert verify(f, freeze)["code"] == "path_outside_root"
