import copy
import json
import socket
import subprocess
import sys

import pytest

from experiments.reviewer_protocol_v2 import (
    control_serialization as c,
    trial_interfaces as t,
)
from experiments.reviewer_protocol_v2.common import ProtocolError, canonical, sha_bytes
from experiments.reviewer_protocol_v2.packet_serialization import build_external_outputs
from experiments.reviewer_protocol_v2.selection import SOURCE_ROOT
from tests.offline_guard import NetworkBlockedError
from tests.test_reviewer_v2_controls import control_fixture
from tests.test_reviewer_v2_selection import synthetic_rows

DESTINATIONS = {r: f"heldout-external/synthetic/{r}.jsonl" for r in t.REVIEWERS}


def trial_fixture(questions=None):
    controls = control_fixture(questions)
    control_packet, control_mapping = c.build_controls(*controls)
    external_packet, external_mapping = build_external_outputs(
        synthetic_rows(), "a" * 64
    )
    inputs = (
        external_packet,
        external_mapping,
        "a" * 64,
        control_packet,
        control_mapping,
        *controls,
    )
    packet, membership = t.build_trial(*inputs)
    return inputs, packet, membership


def test_complete_membership_and_reproductions():
    outputs = []
    for _ in range(2):
        inputs, packet, membership = trial_fixture()
        t.validate_trial(packet, membership, *inputs)
        payloads, manifest = t.build_presentations(packet, membership, DESTINATIONS)
        t.validate_presentations(packet, membership, payloads, manifest)
        schedule = t.build_schedule(packet, membership, payloads, manifest)
        t.validate_schedule(schedule, packet, membership, payloads, manifest)
        outputs.append(
            dict(
                control_packet=inputs[3],
                control_mapping=inputs[4],
                combined_packet=packet,
                membership=membership,
                presentation_manifest=manifest,
                schedule=schedule,
                **payloads,
            )
        )
    assert outputs[0] == outputs[1]
    print(
        json.dumps(
            {name: sha_bytes(raw) for name, raw in outputs[0].items()}, sort_keys=True
        )
    )
    assert [
        sum(r["kind"] == kind for r in json.loads(membership)["items"])
        for kind in ("EXTERNAL", "ANCHOR", "DIAGNOSTIC")
    ] == [24, 15, 6]


def test_permutations_and_zero_retry_schedule():
    _, packet, membership = trial_fixture()
    payloads, manifest = t.build_presentations(packet, membership, DESTINATIONS)
    expected = {r["item_id"]: r["question"] for r in c.records_bytes(packet, 45)}
    permutations = []
    for raw in payloads.values():
        rows = c.records_bytes(raw, 45, sorted_ids=False)
        assert {r["item_id"]: r["question"] for r in rows} == expected
        assert all(set(r) == {"item_id", "question"} for r in rows)
        permutations.append(tuple(r["item_id"] for r in rows))
    assert len(set(permutations)) == 3
    schedule = json.loads(t.build_schedule(packet, membership, payloads, manifest))
    assert type(schedule["retry_limit"]) is int and schedule["retry_limit"] == 0
    rows = schedule["items"]
    assert len(rows) == len({(r["reviewer_slot"], r["item_id"]) for r in rows}) == 135
    assert [r["schedule_index"] for r in rows] == list(range(1, 136))
    assert [r["reviewer_slot"] for r in rows] == list(t.REVIEWERS) * 45
    for r in rows:
        assert r["record_sha256"] == sha_bytes(
            canonical(dict(item_id=r["item_id"], question=expected[r["item_id"]]))
        )


def test_presentation_preimage_tie_and_input_order(monkeypatch):
    _, packet, membership = trial_fixture()
    rows = c.records_bytes(packet, 45)
    item_id = rows[0]["item_id"]
    assert (
        t.presentation_preimage("R1", item_id)
        == (
            '["reviewer-protocol-v2-presentation-order-v1",20261002,"R1","'
            + item_id
            + '"]'
        ).encode()
    )
    monkeypatch.setattr(t, "presentation_digest", lambda *a: b"\x80" * 32)
    assert t.presentation_key("R1", item_id)[0] == b"\x80" * 32
    assert (
        sorted(rows[::-1], key=lambda r: t.presentation_key("R1", r["item_id"])) == rows
    )
    payloads, manifest = t.build_presentations(
        packet, membership, dict(reversed(list(DESTINATIONS.items())))
    )
    assert all(raw == packet for raw in payloads.values())
    t.validate_presentations(packet, membership, payloads, manifest)


def test_duplicate_questions_preserve_external_bytes():
    external_packet, external_mapping = build_external_outputs(
        synthetic_rows(), "a" * 64
    )
    original = external_packet, external_mapping
    questions = [f"Invented duplicate fixture {i}" for i in range(21)]
    questions[0] = c.records_bytes(external_packet, 24)[0]["question"]
    controls = control_fixture(questions)
    control_packet, control_mapping = c.build_controls(*controls)
    with pytest.raises(ProtocolError, match="duplicate_question_assembly"):
        t.build_trial(
            external_packet,
            external_mapping,
            "a" * 64,
            control_packet,
            control_mapping,
            *controls,
        )
    assert original == (external_packet, external_mapping)
    questions[0] = questions[1]
    controls = control_fixture(questions)
    control_packet, control_mapping = c.build_controls(*controls)
    with pytest.raises(ProtocolError, match="duplicate_question_assembly"):
        t.build_trial(
            external_packet,
            external_mapping,
            "a" * 64,
            control_packet,
            control_mapping,
            *controls,
        )


def test_cross_packet_id_collision(monkeypatch):
    external_packet, external_mapping = build_external_outputs(
        synthetic_rows(), "a" * 64
    )
    external_ids = [r["item_id"] for r in c.records_bytes(external_packet, 24)]
    fixture = control_fixture()
    refs = [
        c.reference_id(sha_bytes(fixture[0]), r["local_key"])
        for r in json.loads(fixture[0])["items"]
    ]
    monkeypatch.setattr(
        c, "visible_id", lambda ref, digest: external_ids[refs.index(ref)]
    )
    control_packet, control_mapping = c.build_controls(*fixture)
    with pytest.raises(ProtocolError, match="combined_id_collision"):
        t.build_trial(
            external_packet,
            external_mapping,
            "a" * 64,
            control_packet,
            control_mapping,
            *fixture,
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v.update(extra=True),
        lambda v: v.update(control_keys_sha256="0" * 64),
        lambda v: v["items"].reverse(),
        lambda v: v["items"].pop(),
        lambda v: v["items"][0].update(reference_key="r_" + "0" * 64),
        lambda v: v["items"][0].update(
            kind="ANCHOR" if v["items"][0]["kind"] == "DIAGNOSTIC" else "DIAGNOSTIC"
        ),
        lambda v: v["items"][0].update(original_question_sha256="0" * 64),
    ],
)
def test_membership_failures(mutate):
    inputs, packet, membership = trial_fixture()
    value = json.loads(membership)
    mutate(value)
    with pytest.raises(ProtocolError):
        t.validate_trial(packet, canonical(value), *inputs)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v.update(seed=True),
        lambda v: v.update(seed="20261002"),
        lambda v: v.update(domain="wrong"),
        lambda v: v.update(membership_sha256="0" * 64),
        lambda v: v.update(extra=True),
        lambda v: v["reviewers"].reverse(),
        lambda v: v["reviewers"][0]["item_ids"].reverse(),
        lambda v: v["reviewers"][0]["item_ids"].pop(),
        lambda v: v["reviewers"][0]["packet"].update(sha256="0" * 64),
        lambda v: v["reviewers"][0]["packet"].update(path="../R1.jsonl"),
        lambda v: v["reviewers"][0]["packet"].update(path="main/R1.jsonl"),
        lambda v: v["reviewers"][0].update(extra=True),
    ],
)
def test_presentation_failures(mutate):
    _, packet, membership = trial_fixture()
    payloads, raw = t.build_presentations(packet, membership, DESTINATIONS)
    value = json.loads(raw)
    mutate(value)
    with pytest.raises(ProtocolError):
        t.validate_presentations(packet, membership, payloads, canonical(value))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v.update(retry_limit=True),
        lambda v: v.update(retry_limit=1),
        lambda v: v.update(retry_limit="0"),
        lambda v: v.update(extra=True),
        lambda v: v.update(presentation_manifest_sha256="0" * 64),
        lambda v: v["items"].pop(),
        lambda v: v["items"].reverse(),
        lambda v: v["items"][0].update(schedule_index=True),
        lambda v: v["items"][0].update(presentation_index=True),
        lambda v: v["items"][0].update(reviewer_slot="R2"),
        lambda v: v["items"][0].update(record_sha256="0" * 64),
        lambda v: v["items"].__setitem__(0, copy.deepcopy(v["items"][1])),
    ],
)
def test_schedule_failures(mutate):
    _, packet, membership = trial_fixture()
    payloads, manifest = t.build_presentations(packet, membership, DESTINATIONS)
    value = json.loads(t.build_schedule(packet, membership, payloads, manifest))
    mutate(value)
    with pytest.raises(ProtocolError):
        t.validate_schedule(canonical(value), packet, membership, payloads, manifest)


def test_reviewer_extra_metadata_rejected():
    _, packet, membership = trial_fixture()
    payloads, manifest = t.build_presentations(packet, membership, DESTINATIONS)
    rows = c.records_bytes(payloads[DESTINATIONS["R1"]], 45, sorted_ids=False)
    rows[0]["kind"] = "ANCHOR"
    payloads[DESTINATIONS["R1"]] = b"".join(canonical(r) for r in rows)
    with pytest.raises(ProtocolError):
        t.validate_presentations(packet, membership, payloads, manifest)


def test_network_guard():
    with pytest.raises(NetworkBlockedError):
        socket.getaddrinfo("invented-interface-fixture.invalid", 443)


def test_imports_are_pure_and_bundle_covers_dependencies():
    program = """
import os, sys, socket, builtins
from pathlib import Path
before = dict(os.environ)
def fail(*a, **k): raise AssertionError("operational side effect")
socket.socket.connect = fail
socket.getaddrinfo = fail
builtins.open = fail
Path.read_bytes = fail
Path.write_bytes = fail
from experiments.reviewer_protocol_v2 import trial_interfaces as t
assert dict(os.environ) == before
loaded = {m.__file__ for name,m in sys.modules.items()
          if name == "experiments" or name.startswith("experiments.")}
from experiments.reviewer_protocol_v2.selection import SOURCE_ROOT
assert loaded == {str(SOURCE_ROOT / p) for p in t.INTERFACE_BUNDLE_PATHS}
assert not any(n.split(".")[0] in {"boto3","botocore","dotenv","httpx"} for n in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", program], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    bundle = t.interface_bundle(
        {p: (SOURCE_ROOT / p).read_bytes() for p in t.INTERFACE_BUNDLE_PATHS}
    )
    assert len(bundle["files"]) == 10


@pytest.mark.parametrize(
    "change",
    [
        lambda v: v["items"][0].update(stratum="wrong"),
        lambda v: v["items"][0].update(candidate_id=True),
        lambda v: v["items"][0].update(original_question_sha256="0" * 64),
        lambda v: v["items"][0].update(source_revision="\ud800"),
        lambda v: v["items"][0].update(extra=True),
        lambda v: v.update(inputs_sha256="0" * 64),
    ],
)
def test_external_join_failures(change):
    inputs, _, _ = trial_fixture()
    value = json.loads(inputs[1])
    change(value)
    with pytest.raises(ProtocolError):
        t.validate_external(inputs[0], canonical(value), inputs[2])


def test_pure_functions_do_not_rank_or_access_files(monkeypatch):
    from pathlib import Path
    from experiments.reviewer_protocol_v2 import selection

    def fail(*a, **k):
        pytest.fail("prohibited operation reached")

    monkeypatch.setattr(selection, "ranking_digest", fail)
    monkeypatch.setattr(selection, "select_bound_inputs", fail)
    monkeypatch.setattr(Path, "read_bytes", fail)
    monkeypatch.setattr(Path, "write_bytes", fail)
    inputs, packet, membership = trial_fixture()
    t.validate_trial(packet, membership, *inputs)
    payloads, manifest = t.build_presentations(packet, membership, DESTINATIONS)
    t.validate_schedule(
        t.build_schedule(packet, membership, payloads, manifest),
        packet,
        membership,
        payloads,
        manifest,
    )
