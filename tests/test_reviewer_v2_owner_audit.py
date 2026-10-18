"""Invented annotations, rubric, votes and seal evidence only."""

import copy
import json
import socket
import subprocess
import sys

import pytest

from experiments.reviewer_protocol_v2 import owner_audit as a
from experiments.reviewer_protocol_v2.analysis import analyze_external
from experiments.reviewer_protocol_v2.common import ProtocolError, canonical, sha_bytes
from experiments.reviewer_protocol_v2.control_serialization import records_bytes, schema
from experiments.reviewer_protocol_v2.packet_serialization import build_external_outputs
from experiments.reviewer_protocol_v2.selection import repository_source_path
from tests.offline_guard import NetworkBlockedError
from tests.test_reviewer_v2_selection import synthetic_rows


def fixture():
    packet, mapping = build_external_outputs(synthetic_rows(), "a" * 64)
    rubric = b"Invented owner fixture rubric, not approved production wording.\n"
    records = [
        dict(
            item_id=r["item_id"],
            label="qa",
            components=[],
            certainty="sure",
            abstained=False,
            context_concern=False,
            note="",
        )
        for r in records_bytes(packet, 24)
    ]
    raw = canonical(
        dict(
            schema=schema("owner-audit"),
            packet_sha256=sha_bytes(packet),
            rubric_sha256=sha_bytes(rubric),
            records=records,
        )
    )
    return raw, packet, sha_bytes(packet), rubric, sha_bytes(rubric), mapping


def seal_fixture(f):
    raw, packet, packet_hash, rubric, rubric_hash, mapping = f
    value = dict(
        schema=schema("owner-audit-seal"),
        freeze1_sha256="f" * 64,
        audit_sha256=sha_bytes(raw),
        packet_sha256=packet_hash,
        rubric_sha256=rubric_hash,
        external_mapping_sha256=sha_bytes(mapping),
        owner_attestation=dict(no_ai_assistance=True, no_reviewer_votes_seen=True),
        sealed_utc="2026-10-01T12:34:56.123456Z",
    )
    args = (*f[:5], mapping, sha_bytes(mapping), "a" * 64, "f" * 64)
    return value, args


def votes(raw):
    vote = canonical(
        dict(
            label="qa",
            components=[],
            certainty="sure",
            rationale="Invented fixture vote.",
        )
    ).decode()
    return {
        (r["item_id"], reviewer): vote
        for r in json.loads(raw)["records"]
        for reviewer in ["R1", "R2", "R3"]
    }


def test_complete_roundtrip_and_seal():
    f = fixture()
    audit = a.validate_audit(*f[:5])
    assert a.serialize_audit(audit, *f[1:5]) == f[0]
    seal, args = seal_fixture(f)
    assert a.validate_seal(canonical(seal), *args) == seal
    assert all(set(r) == {"item_id", "question"} for r in records_bytes(f[1], 24))


@pytest.mark.parametrize(
    "abstained,concern", [(False, False), (False, True), (True, False), (True, True)]
)
def test_independent_booleans(abstained, concern):
    f = fixture()
    value = json.loads(f[0])
    value["records"][0].update(
        abstained=abstained,
        context_concern=concern,
        note="Invented explanation é\nverbatim." if abstained or concern else "",
    )
    if abstained:
        value["records"][0].update(label=None, components=[], certainty=None)
    result = a.validate_audit(canonical(value), *f[1:5])
    assert result["records"][0]["context_concern"] is concern


@pytest.mark.parametrize("label", a.LABELS)
@pytest.mark.parametrize("certainty", ["sure", "unsure"])
def test_accepted_labels_components_certainty(label, certainty):
    f = fixture()
    value = json.loads(f[0])
    value["records"][0].update(
        label=label,
        certainty=certainty,
        components=["qa", "summarize"] if label == "multi_intent" else [],
    )
    a.validate_audit(canonical(value), *f[1:5])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v.update(extra=True),
        lambda v: v.update(schema="unfinished-owner-template"),
        lambda v: v.update(packet_sha256="0" * 64),
        lambda v: v.update(rubric_sha256="0" * 64),
        lambda v: v["records"].pop(),
        lambda v: v["records"].reverse(),
        lambda v: v["records"][0].update(item_id=v["records"][1]["item_id"]),
        lambda v: v["records"][0].update(item_id="x_" + "0" * 64),
        lambda v: v["records"][0].update(item_id="r_" + "0" * 64),
        lambda v: v["records"][0].update(source="tatqa"),
        lambda v: v["records"][0].update(label=None, certainty=None),
        lambda v: v["records"][0].update(label=True),
        lambda v: v["records"][0].update(label="other"),
        lambda v: v["records"][0].update(components=["qa", "qa"]),
        lambda v: v["records"][0].update(components=False),
        lambda v: v["records"][0].update(certainty="certain"),
        lambda v: v["records"][0].update(abstained=1),
        lambda v: v["records"][0].update(context_concern=0),
        lambda v: v["records"][0].update(context_concern=True, note=" "),
        lambda v: v["records"][0].update(
            abstained=True, label=None, certainty=None, note=""
        ),
        lambda v: v["records"][0].update(abstained=True, note="explanation"),
        lambda v: v["records"][0].update(note=True),
        lambda v: v["records"][0].update(note="\ud800"),
    ],
)
def test_audit_failures(mutation):
    f = fixture()
    value = json.loads(f[0])
    mutation(value)
    with pytest.raises(ProtocolError):
        a.validate_audit(canonical(value), *f[1:5])


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: b"\xef\xbb\xbf" + raw,
        lambda raw: raw + b"\n",
        lambda raw: raw.replace(b'"schema":', b'"schema":"wrong","schema":'),
        lambda raw: raw.replace(b'"records":', b'"extra":NaN,"records":'),
    ],
)
def test_noncanonical_audit(mutate):
    f = fixture()
    with pytest.raises(ProtocolError):
        a.validate_audit(mutate(f[0]), *f[1:5])


@pytest.mark.parametrize(
    "mutation",
    [
        lambda v: v.update(extra=0),
        lambda v: v.update(audit_sha256="0" * 64),
        lambda v: v.update(packet_sha256="0" * 64),
        lambda v: v.update(rubric_sha256="0" * 64),
        lambda v: v.update(external_mapping_sha256="0" * 64),
        lambda v: v.update(freeze1_sha256="0" * 64),
        lambda v: v["owner_attestation"].update(no_ai_assistance=1),
        lambda v: v["owner_attestation"].update(no_reviewer_votes_seen=False),
        lambda v: v["owner_attestation"].update(extra=True),
        lambda v: v.update(sealed_utc="2026-10-01T12:34:56Z"),
        lambda v: v.update(sealed_utc="2026-10-01T12:34:56.123456+00:00"),
        lambda v: v.update(sealed_utc="2026-02-30T12:34:56.123456Z"),
        lambda v: v.update(sealed_utc=True),
    ],
)
def test_seal_failures(mutation):
    seal, args = seal_fixture(fixture())
    mutation(seal)
    with pytest.raises(ProtocolError):
        a.validate_seal(canonical(seal), *args)


def test_supplied_hash_failures_and_control_ids():
    f = fixture()
    for index, replacement in (
        (2, "0" * 64),
        (3, b"other invented rubric"),
        (4, "0" * 64),
    ):
        args = list(f[:5])
        args[index] = replacement
        with pytest.raises(ProtocolError):
            a.validate_audit(*args)
    from tests.test_reviewer_v2_controls import control_fixture
    from experiments.reviewer_protocol_v2.control_serialization import build_controls

    controls, _ = build_controls(*control_fixture())
    value = json.loads(f[0])
    value["records"][0]["item_id"] = records_bytes(controls, 21)[0]["item_id"]
    value["records"].sort(key=lambda r: r["item_id"])
    with pytest.raises(ProtocolError):
        a.validate_audit(canonical(value), *f[1:5])
    seal, args = seal_fixture(f)
    args = list(args)
    args[6] = "0" * 64
    with pytest.raises(ProtocolError):
        a.validate_seal(canonical(seal), *args)


def test_populations_overlaps_and_raw_immutability():
    f = fixture()
    value = json.loads(f[0])
    rows = value["records"]
    rows[0].update(
        abstained=True, label=None, certainty=None, note="Invented abstention."
    )
    rows[1].update(context_concern=True, note="Invented labeled concern.")
    rows[2].update(
        abstained=True, label=None, certainty=None, context_concern=True, note="Both."
    )
    raw = canonical(value)
    snapshot = copy.deepcopy(value)
    answers = votes(raw)
    answers.pop((rows[0]["item_id"], "R1"))
    answers[(rows[1]["item_id"], "R1")] = "{{"
    report = a.analyze_owner(raw, *f[1:5], ["R1", "R2", "R3"], answers)
    assert value == snapshot and raw == canonical(snapshot)
    assert report["owner_counts"] == dict(
        abstentions=2, context_concerns=2, abstention_and_context_concern=1
    )
    pop = report["owner_comparison"]["R1"]
    assert pop["coverage"]["numerator"] == 21 and pop["coverage"]["denominator"] == 24
    assert pop["reason_counts"] == dict(
        OWNER_ABSTAINED=2,
        OWNER_CONTEXT_CONCERN=2,
        REVIEWER_MISSING=1,
        REVIEWER_INVALID=1,
    )
    assert pop["exact_reason_combinations"] == {
        "OWNER_ABSTAINED+REVIEWER_MISSING": 1,
        "OWNER_CONTEXT_CONCERN+REVIEWER_INVALID": 1,
        "OWNER_ABSTAINED+OWNER_CONTEXT_CONCERN": 1,
    }
    assert report["primary"]["reviewers"]["R1"]["owner_cohen_kappa"]["n"] == 21
    assert report["primary"]["owner_label_availability"]["numerator"] == 22
    assert report["primary"]["owner_abstentions_or_missing"] == 2
    ids = [r["item_id"] for r in rows]
    baseline = analyze_external(ids, ["R1", "R2", "R3"], answers, {})
    for key in (
        "pairwise",
        "fleiss_kappa",
        "complete_coverage",
        "unconditional_unanimity",
        "majority_availability",
    ):
        assert report["primary"][key] == baseline[key]
    assert report["reviewer_only"]["fleiss"]["coverage"]["numerator"] == 22
    for reviewer in ["R1", "R2", "R3"]:
        assert (
            report["primary"]["reviewers"][reviewer]["owner_agreement_planned"][
                "denominator"
            ]
            == 24
        )


@pytest.mark.parametrize("all_concern", [False, True])
def test_empty_owner_population_without_scores(all_concern):
    f = fixture()
    value = json.loads(f[0])
    for row in value["records"]:
        row.update(context_concern=all_concern, note="Invented exclusion explanation.")
        if not all_concern:
            row.update(abstained=True, label=None, certainty=None)
    raw = canonical(value)
    report = a.analyze_owner(raw, *f[1:5], ["R1", "R2", "R3"], votes(raw))
    for reviewer in ["R1", "R2", "R3"]:
        assert report["owner_comparison"][reviewer]["coverage"]["numerator"] == 0
        stats = report["primary"]["reviewers"][reviewer]
        assert stats["owner_cohen_kappa"]["value"] is None
        assert stats["owner_agreement_available"]["value"] is None
    assert report["primary"]["fleiss_kappa"]["n"] == 24


def test_deterministic_reproduction():
    results = []
    for _ in range(2):
        f = fixture()
        seal, args = seal_fixture(f)
        a.validate_seal(canonical(seal), *args)
        report = a.analyze_owner(*f[:5], ["R1", "R2", "R3"], votes(f[0]))
        results.append(
            dict(
                audit=f[0],
                synthetic_seal=canonical(seal),
                population_view=canonical(report),
            )
        )
    assert results[0] == results[1]
    print(json.dumps({k: sha_bytes(v) for k, v in results[0].items()}, sort_keys=True))


def test_excluded_concern_is_not_a_kappa_disagreement():
    f = fixture()
    value = json.loads(f[0])
    answers = {}
    for i, row in enumerate(value["records"]):
        row["label"] = "qa" if i % 2 else "summarize"
        for reviewer in ["R1", "R2", "R3"]:
            answers[(row["item_id"], reviewer)] = canonical(
                dict(
                    label=row["label"],
                    components=[],
                    certainty="sure",
                    rationale="Invented vote.",
                )
            ).decode()
    row = value["records"][0]
    row.update(context_concern=True, note="Retain this labeled concern.", label="qa")
    report = a.analyze_owner(canonical(value), *f[1:5], ["R1", "R2", "R3"], answers)
    for reviewer in ["R1", "R2", "R3"]:
        stats = report["primary"]["reviewers"][reviewer]
        assert stats["owner_cohen_kappa"] == dict(n=23, value=1.0, reason=None)
        assert stats["owner_agreement_available"]["numerator"] == 23
        assert stats["owner_agreement_planned"]["denominator"] == 24
    assert value["records"][0]["label"] == "qa"


def test_import_purity_dependency_coverage_and_network_guard():
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
from experiments.reviewer_protocol_v2 import owner_audit as a
from experiments.reviewer_protocol_v2.selection import repository_source_path
assert os.environ == before
loaded = {m.__file__ for n,m in sys.modules.items() if n == "experiments" or n.startswith("experiments.")}
assert loaded == {str(repository_source_path(p)) for p in a.OWNER_BUNDLE_PATHS}
assert not any(n.split(".")[0] in {"boto3","botocore","dotenv","httpx"} for n in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", program], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (
        len(
            a.owner_bundle(
                {p: (repository_source_path(p)).read_bytes() for p in a.OWNER_BUNDLE_PATHS}
            )["files"]
        )
        == 12
    )
    with pytest.raises(NetworkBlockedError):
        socket.getaddrinfo("invented-owner-audit.invalid", 443)
