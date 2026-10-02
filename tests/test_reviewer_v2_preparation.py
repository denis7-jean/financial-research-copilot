"""Invented workspace evidence only; no production data enters either API."""

import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.reviewer_protocol_v2 import ledger_adoption as a
from experiments.reviewer_protocol_v2 import production_preparation as p
from experiments.reviewer_protocol_v2 import selection as s
from experiments.reviewer_protocol_v2.common import ProtocolError, canonical, sha_bytes
from experiments.reviewer_protocol_v2.exposure import InventoryBuilder
from tests.test_reviewer_v2_selection import bound_fixture, synthetic_rows


def fixture(root, mutate=None):
    rows = synthetic_rows()
    if mutate:
        mutate(rows)
    binding, _ = bound_fixture(root, rows)
    selection_spec = dict(
        schema="reviewer-protocol-v2-selection-specification-v1",
        seed=20261001,
        strata=list(s.STRATUM_ENTRIES),
        rank_domain="reviewer-protocol-v2-rank-v1",
        external_id_domain="reviewer-protocol-v2-external-id-v1",
        tie_breakers=["digest", "candidate_id_utf8", "source_utf8"],
        threshold_hex=(0.9).hex(),
        comparison="<",
        shortfall="NO_PACKET",
    )
    spec_fb = binding["artifacts"]["selection_specification"]
    (root / spec_fb["path"]).write_bytes(canonical(selection_spec))
    spec_fb["sha256"] = sha_bytes(canonical(selection_spec))
    sources = {name: b"# Invented historical source.\n" for name in a.GENERATING_FILES}

    def put(path, raw):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return dict(path=path, sha256=sha_bytes(raw))

    design = {}
    extra = {}
    for name in (
        "original-design-evidence.md",
        "revised-design-evidence.md",
        "document-quotes.json",
        "recovered-references.json",
    ):
        fb = put(
            "heldout-external/reviewer-protocol-v2-offline/" + name,
            canonical({"invented": name}),
        )
        extra[name] = fb["sha256"]
        if name.endswith(".md"):
            design[name] = fb["sha256"]
    sources["integrity.py"] = (
        f"DESIGN_HASHES = {design!r}\n"
        f"RECOVERY_SHA256 = {extra['recovered-references.json']!r}\n"
    ).encode()
    sources["known_inventory.py"] = (
        f"DOC_QUOTES_SHA256 = {extra['document-quotes.json']!r}\n".encode()
    )
    sources["audit.py"] = a.RECIPE.encode()
    pop = binding["artifacts"]["population"]
    pins = {pop["path"]: pop["sha256"]}
    sources["input_hashes.json"] = canonical(pins)
    _, historical_digest = a.generating_bundle(sources)
    for row in rows:
        row["implementation_sha256"] = historical_digest
    inventory = InventoryBuilder(rows).finish()
    inventory["supporting_files"] = {}
    payloads = {
        "inventory.json": canonical(inventory),
        "population_ledger.jsonl": b"".join(canonical(r) for r in rows),
        "aggregate.json": canonical(
            dict(implementation_sha256=historical_digest, runtime=a.RECORDED_RUNTIME)
        ),
        "integrity.json": canonical(
            dict(
                protected_files=len(pins),
                frozen_bindings=0,
                pins_sha256=sha_bytes(sources["input_hashes.json"]),
                files=pins,
                verified=True,
            )
        ),
    }
    directory = "heldout-external/invented-audit/"
    for name, raw in payloads.items():
        put(directory + name, raw)
    manifest = dict(
        artifact_type="offline_unselected_audit",
        byte_contract="UTF-8; escaped Unicode; sorted keys; compact JSON; finite numbers; LF terminator",
        files={name: sha_bytes(raw) for name, raw in payloads.items()},
        frozen=False,
        implementation_sha256=historical_digest,
        runtime=a.RECORDED_RUNTIME,
        schema="offline_audit_manifest_v2",
        self_hash_rule="manifest excluded from files; receipt holds exact manifest-byte hash",
    )
    mf = put(directory + "manifest.json", canonical(manifest))
    binding["artifacts"]["eligibility_ledger"] = put(
        directory + "population_ledger.jsonl", payloads["population_ledger.jsonl"]
    )
    binding["artifacts"]["exposure_inventory"] = put(
        directory + "inventory.json", payloads["inventory.json"]
    )
    binding["code"]["ledger_audit_implementation_sha256"] = historical_digest
    executing = {}
    for path in p.VERIFICATION_BUNDLE_PATHS:
        raw = (s.SOURCE_ROOT / path).read_bytes()
        put(path, raw)
        executing[path] = raw
    return dict(
        root=root,
        artifacts=binding["artifacts"],
        code_bindings=binding["code"],
        generating_sources=sources,
        historical_manifest=mf,
        expected_historical_manifest_sha256=mf["sha256"],
        executing_sources=executing,
    )


def adoption(f, **kwargs):
    return a.verify_adoption(
        f["root"],
        f["historical_manifest"],
        f["expected_historical_manifest_sha256"],
        f["generating_sources"],
        f["artifacts"]["population"],
        f["artifacts"]["eligibility_ledger"],
        f["code_bindings"]["selection_bundle"],
        **kwargs,
    )


def rebind_invented_history(f):
    """Mutate only invented evidence to reach checks after exact hash verification."""
    root = f["root"]
    digest = sha_bytes(
        canonical(
            {name: sha_bytes(raw) for name, raw in f["generating_sources"].items()}
        )
    )
    mf = f["historical_manifest"]
    manifest = json.loads((root / mf["path"]).read_bytes())
    parent = (root / mf["path"]).parent
    ledger = s.jsonl_records((parent / "population_ledger.jsonl").read_bytes())
    for row in ledger:
        row["implementation_sha256"] = digest
    (parent / "population_ledger.jsonl").write_bytes(
        b"".join(canonical(row) for row in ledger)
    )
    aggregate = json.loads((parent / "aggregate.json").read_bytes())
    aggregate["implementation_sha256"] = digest
    (parent / "aggregate.json").write_bytes(canonical(aggregate))
    manifest["implementation_sha256"] = digest
    manifest["files"] = {
        name: sha_bytes((parent / name).read_bytes()) for name in a.PAYLOADS
    }
    raw = canonical(manifest)
    (root / mf["path"]).write_bytes(raw)
    mf["sha256"] = sha_bytes(raw)
    f["expected_historical_manifest_sha256"] = sha_bytes(raw)
    f["code_bindings"]["ledger_audit_implementation_sha256"] = digest
    for role, name in (
        ("eligibility_ledger", "population_ledger.jsonl"),
        ("exposure_inventory", "inventory.json"),
    ):
        f["artifacts"][role]["sha256"] = manifest["files"][name]


def test_valid_deterministic_preparation_and_provenance(tmp_path):
    results = []
    for name in ("one", "two"):
        f = fixture(tmp_path / name)
        raw, report = p.prepare(**f)
        assert raw is not None, report
        value = json.loads(report)
        assert value["status"] == "PREPARED" and value["freeze1_sha256"] is None
        assert p.prepare(**f, trusted_expected_inputs_sha256=sha_bytes(raw)) == (
            raw,
            report,
        )
        p.validate_preparation(f["root"], raw, report, sha_bytes(raw))
        technical = adoption(f)
        assert technical["historical_provenance_verified"] is True
        assert technical["proposed_freeze_compatible"] is None
        assert technical["operational_adoption_performed"] is False
        results.append((raw, report, canonical(technical)))
    assert results[0] == results[1]
    print(
        json.dumps(
            dict(
                inputs=sha_bytes(results[0][0]),
                report=sha_bytes(results[0][1]),
                provenance=sha_bytes(results[0][2]),
            ),
            sort_keys=True,
        )
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r[0].update(question_sha256="0" * 64),
        lambda r: r[0].update(final_unexposed_screen_pass=False),
        lambda r: r[0]["exposure"].update(direct=1),
        lambda r: r[0]["eligibility"].update(disposition="unknown"),
        lambda r: r[1].update(cand_id=r[0]["cand_id"]),
    ],
)
def test_identity_question_flags(tmp_path, mutate):
    f = fixture(tmp_path, mutate)
    raw, report = p.prepare(**f)
    assert raw is None and json.loads(report)["status"] == "FAILED"


@pytest.mark.parametrize(
    "role",
    [
        "population",
        "eligibility_ledger",
        "exposure_inventory",
        "selection_specification",
    ],
)
@pytest.mark.parametrize("action", ["alter", "remove"])
def test_missing_or_altered_artifacts(tmp_path, role, action):
    f = fixture(tmp_path)
    path = tmp_path / f["artifacts"][role]["path"]
    if action == "alter":
        path.write_bytes(b"invented altered bytes")
    else:
        path.unlink()
    assert p.prepare(**f)[0] is None
    if role != "selection_specification":
        assert adoption(f)["code"] != "BINDINGS_VERIFIED_NOT_ADOPTED"


@pytest.mark.parametrize(
    "path",
    ["../main/a", "main/../a", "C:/a", "main\\a", "/main/a", "main//a", "other/a"],
)
def test_path_protection(tmp_path, path):
    f = fixture(tmp_path)
    f["artifacts"]["population"]["path"] = path
    assert p.prepare(**f)[0] is None


def test_symlink_escape(tmp_path):
    root = tmp_path / "workspace"
    f = fixture(root)
    path = root / f["artifacts"]["population"]["path"]
    outside = tmp_path / "outside.jsonl"
    shutil.copyfile(path, outside)
    link = root / "heldout-external" / "escape"
    try:
        link.symlink_to(outside.parent, target_is_directory=True)
    except OSError:
        # Windows directory junctions need no symlink privilege. Both endpoints
        # are invented, resolved test-owned directories inside workspace basetemp.
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
                + quote(outside.parent),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Synthetic junction creation failed"
    f["artifacts"]["population"]["path"] = "heldout-external/escape/outside.jsonl"
    assert p.prepare(**f)[0] is None
    assert adoption(f)["historical_provenance_verified"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda f: f["executing_sources"].pop(p.VERIFICATION_BUNDLE_PATHS[-1]),
        lambda f: f["executing_sources"].update(
            {p.VERIFICATION_BUNDLE_PATHS[-1]: b"# Wrong executing source\n"}
        ),
        lambda f: f["code_bindings"]["selection_bundle"].update(sha256="0" * 64),
        lambda f: f["code_bindings"].update(
            ledger_audit_implementation_sha256=s.selection_bundle()["sha256"]
        ),
        lambda f: f["generating_sources"].pop("analysis.py"),
        lambda f: f["generating_sources"].update(
            {"audit.py": b"def implementation_hash(): return 'wrong'\n"}
        ),
        lambda f: f["generating_sources"].update(
            {"integrity.py": b"# Missing inputs\n"}
        ),
        lambda f: f.update(expected_historical_manifest_sha256="0" * 64),
    ],
)
def test_wrong_source_dependency_and_trust_bindings(tmp_path, mutation):
    f = fixture(tmp_path)
    mutation(f)
    assert p.prepare(**f)[0] is None


def test_runtime_binding_and_untrusted_report(tmp_path, monkeypatch):
    f = fixture(tmp_path)
    raw, report = p.prepare(**f)
    with pytest.raises(ProtocolError):
        p.validate_preparation(tmp_path, raw, report, "0" * 64)
    assert p.prepare(**f, trusted_expected_inputs_sha256="0" * 64)[0] is None
    value = json.loads(raw)
    value["approval_sha256"] = sha_bytes(raw)
    with pytest.raises(ProtocolError):
        p.validate_preparation(
            tmp_path, canonical(value), report, sha_bytes(canonical(value))
        )
    monkeypatch.setattr(
        p, "runtime_binding", lambda: dict(s.runtime_binding(), python_version="wrong")
    )
    assert p.prepare(**f)[0] is None


@pytest.mark.parametrize(
    "name,raw,code",
    [
        (
            "audit.py",
            b"def implementation_hash(): return 'wrong'\n",
            "GENERATING_HASH_RECIPE",
        ),
        (
            "integrity.py",
            b"# No generating input contract\n",
            "GENERATING_INPUT_CONTRACT_MISSING",
        ),
        (
            "known_inventory.py",
            b"DOC_QUOTES_SHA256 = call()\n",
            "GENERATING_INPUT_CONTRACT_INVALID",
        ),
    ],
)
def test_specific_generating_contract_failures(tmp_path, name, raw, code):
    f = fixture(tmp_path)
    f["generating_sources"][name] = raw
    rebind_invented_history(f)
    result = adoption(f)
    assert result["code"] == code
    assert result["historical_provenance_verified"] is False


@pytest.mark.parametrize(
    "which,code",
    [
        ("runtime", "HISTORICAL_RUNTIME"),
        ("inventory", "INVENTORY_SOURCE_BINDING"),
        ("aggregate", "AGGREGATE_GENERATING_BINDING"),
        ("pins", "HISTORICAL_INPUT_PINS"),
    ],
)
def test_specific_historical_failures(tmp_path, which, code):
    f = fixture(tmp_path)
    parent = (tmp_path / f["historical_manifest"]["path"]).parent
    if which == "runtime":
        mf = f["historical_manifest"]
        manifest = json.loads((tmp_path / mf["path"]).read_bytes())
        manifest["runtime"]["python"] = "wrong"
        raw = canonical(manifest)
        (tmp_path / mf["path"]).write_bytes(raw)
        mf["sha256"] = f["expected_historical_manifest_sha256"] = sha_bytes(raw)
    else:
        name = {
            "inventory": "inventory.json",
            "aggregate": "aggregate.json",
            "pins": "integrity.json",
        }[which]
        value = json.loads((parent / name).read_bytes())
        if which == "inventory":
            value["supporting_files"] = {
                "heldout-external/invented-unbound.json": "0" * 64
            }
        elif which == "aggregate":
            value["runtime"] = {}
        else:
            value["pins_sha256"] = "0" * 64
        (parent / name).write_bytes(canonical(value))
        rebind_invented_history(f)
    assert adoption(f)["code"] == code


def test_inventory_flags_and_executing_disk_source(tmp_path):
    f = fixture(tmp_path)
    ledger_path = tmp_path / f["artifacts"]["eligibility_ledger"]["path"]
    rows = s.jsonl_records(ledger_path.read_bytes())
    rows[0]["exposure"]["direct"] = True
    rows[0]["final_unexposed_screen_pass"] = False
    raw = b"".join(canonical(row) for row in rows)
    ledger_path.write_bytes(raw)
    rebind_invented_history(f)
    assert p.prepare(**f)[0] is None
    (tmp_path / p.VERIFICATION_BUNDLE_PATHS[-1]).write_bytes(
        b"# stale fixture source\n"
    )
    assert json.loads(p.prepare(**f)[1])["findings"][0]["code"] == "CODE_BINDING"


def test_metadata_join_without_rescreening(tmp_path):
    f = fixture(tmp_path)
    path = tmp_path / f["artifacts"]["population"]["path"]
    rows = s.jsonl_records(path.read_bytes())
    rows[0]["context_group"] = "invented different metadata"
    raw = b"".join(canonical(r) for r in rows)
    path.write_bytes(raw)
    f["artifacts"]["population"]["sha256"] = sha_bytes(raw)
    assert p.prepare(**f)[0] is None


def test_missing_encoding_evidence_and_freeze_mismatch(tmp_path):
    f = fixture(tmp_path)
    fb = f["artifacts"]["selection_specification"]
    roles = {role: fb for role in a.FREEZE_ROLES}
    roles.update(
        population=f["artifacts"]["population"],
        exposure_inventory=f["artifacts"]["exposure_inventory"],
    )
    raw = canonical(
        dict(
            schema="reviewer-protocol-v2-freeze-manifest-v1",
            phase="FREEZE_1",
            artifacts=roles,
        )
    )
    result = adoption(f, proposed_freeze1=raw, expected_freeze1_sha256=sha_bytes(raw))
    assert result["historical_provenance_verified"] is True
    assert result["code"] == "schema_keys"
    assert result["proposed_freeze_compatible"] is False
    assert (
        p.prepare(
            **f, proposed_freeze1=raw, trusted_expected_freeze1_sha256=sha_bytes(raw)
        )[0]
        is None
    )
    assert (
        adoption(f, proposed_freeze1=raw, expected_freeze1_sha256="0" * 64)["code"]
        == "FREEZE_TRUSTED_HASH"
    )
    roles["population"] = fb
    raw = canonical(
        dict(
            schema="reviewer-protocol-v2-freeze-manifest-v1",
            phase="FREEZE_1",
            artifacts=roles,
        )
    )
    assert (
        adoption(f, proposed_freeze1=raw, expected_freeze1_sha256=sha_bytes(raw))[
            "code"
        ]
        == "FREEZE_POPULATION_BINDING"
    )


def test_no_hooks_or_mutation(tmp_path, monkeypatch):
    from experiments.reviewer_protocol_v2 import packet_serialization, trial_interfaces

    f = fixture(tmp_path)
    before = {
        x.relative_to(tmp_path): x.read_bytes()
        for x in tmp_path.rglob("*")
        if x.is_file()
    }

    def fail(*args, **kwargs):
        pytest.fail("Forbidden operation")

    for name in (
        "ranking_digest",
        "ranked_stratum",
        "scan",
        "select_bound_inputs",
        "external_id",
    ):
        if hasattr(s, name):
            monkeypatch.setattr(s, name, fail)
    for name in ("external_id", "build_external_outputs", "serialize_blind_records"):
        monkeypatch.setattr(packet_serialization, name, fail)
    for name in ("build_trial", "build_presentations", "build_schedule"):
        monkeypatch.setattr(trial_interfaces, name, fail)
    monkeypatch.setattr(Path, "write_bytes", fail)
    assert p.prepare(**f)[0] is not None
    assert adoption(f)["historical_provenance_verified"] is True
    assert before == {
        x.relative_to(tmp_path): x.read_bytes()
        for x in tmp_path.rglob("*")
        if x.is_file()
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", "wrong"),
        ("status", "FAILED"),
        ("inputs_sha256", "0" * 64),
        ("freeze1_sha256", "0" * 64),
        ("findings", [{"code": "INPUT_SCHEMA", "artifact": None}]),
    ],
)
def test_stale_or_self_declared_report(tmp_path, field, value):
    f = fixture(tmp_path)
    raw, report = p.prepare(**f)
    changed = json.loads(report)
    changed[field] = value
    with pytest.raises(ProtocolError):
        p.validate_preparation(tmp_path, raw, canonical(changed), sha_bytes(raw))


def test_sanitized_malformed_evidence(tmp_path):
    f = fixture(tmp_path)
    f["historical_manifest"] = {
        "question": "invented sensitive sentinel",
        "secret": "invented secret sentinel",
    }
    result = canonical(adoption(f))
    report = p.prepare(**f)[1]
    assert b"sentinel" not in result + report
    assert b"c_000" not in result + report


def test_import_purity_and_dependency_closure():
    program = """
import os, sys, socket, builtins
from pathlib import Path
before = dict(os.environ)
def fail(*a, **k): raise AssertionError("side effect")
socket.socket.connect = fail
socket.getaddrinfo = fail
builtins.open = fail
Path.read_bytes = fail
Path.write_bytes = fail
from experiments.reviewer_protocol_v2 import production_preparation as p
from experiments.reviewer_protocol_v2.selection import SOURCE_ROOT
assert os.environ == before
loaded = {m.__file__ for n,m in sys.modules.items() if n == "experiments" or n.startswith("experiments.")}
assert loaded == {str(SOURCE_ROOT/x) for x in p.VERIFICATION_BUNDLE_PATHS}
assert not any(n.split(".")[0] in {"boto3","botocore","dotenv","httpx"} for n in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", program], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    with pytest.raises(Exception) as error:
        socket.getaddrinfo("invented-preparation.invalid", 443)
    assert "NetworkBlocked" in type(error.value).__name__
