import socket
import subprocess
import sys
import pytest
from experiments.reviewer_protocol_v2.__main__ import main
from experiments.reviewer_protocol_v2.common import ProtocolError, canonical, sha_bytes
from experiments.reviewer_protocol_v2.constraints import (
    constraint_summary,
    validate_diversity,
)
from experiments.reviewer_protocol_v2.eligibility import STRATA
from experiments.reviewer_protocol_v2.fixtures import synthetic_record
from experiments.reviewer_protocol_v2.integrity import verify_output_manifest
from experiments.reviewer_protocol_v2.selection import select
from experiments.reviewer_protocol_v2.packet_validation import validate_packet
from experiments.reviewer_protocol_v2.exposure import InventoryBuilder
from tests.offline_guard import NetworkBlockedError


def test_imports_do_not_load_cloud_clients_credentials_or_network():
    program = """
import os, sys, socket
before = dict(os.environ)
def fail(*args, **kwargs): raise AssertionError("import network activity")
socket.socket.connect = fail
socket.getaddrinfo = fail
import experiments.reviewer_protocol_v2.audit
import experiments.reviewer_protocol_v2.analysis
import experiments.reviewer_protocol_v2.validation
assert dict(os.environ) == before
assert not any(name.split(".")[0] in {"boto3", "botocore", "dotenv", "httpx"} for name in sys.modules)
print("clean imports")
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", program], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "argument", ["--rank", "--select", "--seed", "--live", "--freeze"]
)
def test_audit_command_rejects_ranking_selection_and_live(argument, tmp_path):
    with pytest.raises(SystemExit) as result:
        main(["audit", "--output", str(tmp_path / "out"), argument])
    assert result.value.code == 2
    assert not (tmp_path / "out").exists()


def test_future_selection_is_disabled_even_for_synthetic_inputs():
    with pytest.raises(ProtocolError, match="selection_disabled"):
        select([synthetic_record()], seed=20261001, synthetic=True)


def test_audit_refuses_tracked_or_existing_output(tmp_path):
    from experiments.reviewer_protocol_v2.audit import run_audit

    for path in (
        tmp_path / "main/out",
        tmp_path / "heldout-external/reviewer-protocol-v2-offline",
    ):
        path.mkdir(parents=True)
        with pytest.raises(ProtocolError, match="new_private_directory"):
            run_audit(tmp_path, path)


def test_network_is_blocked_without_a_request():
    with pytest.raises(NetworkBlockedError):
        socket.getaddrinfo("synthetic.invalid", 443)


def test_quota_shortfall_and_cross_stratum_group_conflict():
    rows = [
        synthetic_record("aaaaaaa")
        | {
            "source": "finlfqa",
            "sampling_stratum": "interp",
            "context_group": "shared",
        },
        synthetic_record("zzzzzzz")
        | {
            "cand_id": "c_0000000002",
            "source": "finlfqa",
            "sampling_stratum": "mixed",
            "context_group": "shared",
        },
    ]
    quotas = {
        s: int(s in (("finlfqa", "interp"), ("finlfqa", "mixed"))) for s in STRATA
    }
    result = constraint_summary(rows, quotas)
    assert result["native_group_conflicts"] == 1
    assert not result["simultaneous_quota_feasible"]
    with pytest.raises(ProtocolError, match="native_group_conflict"):
        validate_diversity(rows)
    rows[1]["context_group"] = "separate"
    assert constraint_summary(rows, quotas)["simultaneous_quota_feasible"]
    quotas[("finlfqa", "mixed")] = 2
    assert not constraint_summary(rows, quotas)["simultaneous_quota_feasible"]


def test_packet_direct_pair_diversity_rejected():
    rows = [
        synthetic_record("synthetic identical question"),
        synthetic_record("synthetic identical question") | {"context_group": "other"},
    ]
    with pytest.raises(ProtocolError, match="similarity_conflict"):
        validate_diversity(rows)


def test_synthetic_packet_validation_verbatim_binding_and_exposure():
    first = synthetic_record("aaaaaaa")
    second = synthetic_record("zzzzzzz") | {
        "cand_id": "c_0000000002",
        "context_group": "other",
    }
    population = [first, second]
    builder = InventoryBuilder(population)
    builder.add(
        "work_history_disclosure",
        "synthetic",
        None,
        "fixture:1",
        cid=second["cand_id"],
        stage="synthetic",
        completeness="canonical_id_binding",
    )
    inventory = builder.finish()
    quotas = {s: int(s == ("tatqa", "T1_qa")) for s in STRATA}
    assert validate_packet([first], population, inventory, quotas)
    with pytest.raises(ProtocolError, match="binding_or_eligibility"):
        validate_packet(
            [first | {"question": "changed"}], population, inventory, quotas
        )
    with pytest.raises(ProtocolError, match="exposure_exclusion"):
        validate_packet([second], population, inventory, quotas)
    with pytest.raises(ProtocolError, match="quota_mismatch"):
        validate_packet([], population, inventory, quotas)


def test_manifest_verification_detects_mutation_and_traversal(tmp_path):
    filenames = (
        "inventory.json",
        "population_ledger.jsonl",
        "aggregate.json",
        "integrity.json",
    )
    payload = b"{}\n"
    for filename in filenames:
        (tmp_path / filename).write_bytes(payload)
    manifest = {
        "artifact_type": "offline_unselected_audit",
        "frozen": False,
        "files": {name: sha_bytes(payload) for name in filenames},
    }
    (tmp_path / "manifest.json").write_bytes(canonical(manifest))
    assert verify_output_manifest(tmp_path) == sha_bytes(canonical(manifest))
    (tmp_path / filenames[0]).write_bytes(b"changed")
    with pytest.raises(ProtocolError, match="hash_mismatch"):
        verify_output_manifest(tmp_path)
    manifest["files"]["../outside.json"] = sha_bytes(payload)
    (tmp_path / "manifest.json").write_bytes(canonical(manifest))
    with pytest.raises(ProtocolError, match="file_set"):
        verify_output_manifest(tmp_path)
