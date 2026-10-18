"""Invented controls/keys only; these fixtures have no approved production content."""

import copy
import json

import pytest

from experiments.reviewer_protocol_v2 import control_serialization as c
from experiments.reviewer_protocol_v2.common import (
    ProtocolError,
    canonical,
    question_hash,
    sha_bytes,
)


def control_fixture(questions=None):
    approval_path = "heldout-external/synthetic/wording-approval.txt"
    approval = b"Invented source-wording approval; predates catalog and keys.\n"
    artifacts = {approval_path: approval}
    provenance = dict(
        author="invented-fixture-author",
        source_revision="invented-revision",
        approval_evidence=dict(path=approval_path, sha256=sha_bytes(approval)),
    )
    items = [
        dict(
            local_key=f"fixture_{i:02}",
            kind="ANCHOR" if i < 15 else "DIAGNOSTIC",
            question=(
                questions[i]
                if questions
                else f"Invented control {i}: É e\u0301 “quote” \\ line\n𝄞"
            ),
            provenance=copy.deepcopy(provenance),
        )
        for i in range(21)
    ]
    catalog = canonical(dict(schema=c.schema("control-catalog"), items=items))
    binding = dict(
        path="heldout-external/synthetic/catalog.json", sha256=sha_bytes(catalog)
    )
    rubric = sha_bytes(b"Invented fixture rubric, not production.\n")
    entries = []
    for i, item in enumerate(items):
        key = dict(
            reference_key=c.reference_id(sha_bytes(catalog), item["local_key"]),
            kind=item["kind"],
            original_question_sha256=question_hash(item["question"]),
        )
        if i < 15:
            label = c.LABELS[i // 3]
            key.update(
                expected_label=label,
                expected_components=["qa", "summarize"]
                if label == "multi_intent"
                else [],
                generic_rationale="Invented fixture key only.",
            )
        else:
            key.update(
                category=c.CATEGORIES[(i - 15) // 2],
                policy_expectation="Invented unscored observation.",
                scoring_permitted=False,
            )
        entries.append(key)
    keys = canonical(
        dict(
            schema=c.schema("control-keys"),
            catalog_sha256=sha_bytes(catalog),
            rubric_sha256=rubric,
            entries=sorted(entries, key=lambda r: r["reference_key"]),
        )
    )
    return catalog, binding, keys, artifacts, rubric


def test_control_reconstruction_counts_and_visible_allowlist():
    fixture = control_fixture()
    packet, mapping = c.build_controls(*fixture)
    c.validate_controls(packet, mapping, *fixture)
    records = c.records_bytes(packet, 21)
    assert all(set(r) == {"item_id", "question"} for r in records)
    assert all(
        r["item_id"].startswith("x_") and len(r["item_id"]) == 66 for r in records
    )
    private = json.loads(mapping)
    assert len({r["reference_key"] for r in private["items"]}) == 21
    keys = json.loads(fixture[2])["entries"]
    assert [
        sum(r.get("expected_label") == label for r in keys) for label in c.LABELS
    ] == [3] * 5
    assert [
        sum(r.get("category") == category for r in keys) for category in c.CATEGORIES
    ] == [2] * 3
    assert all(
        r["scoring_permitted"] is False for r in keys if r["kind"] == "DIAGNOSTIC"
    )
    originals = {r["question"] for r in json.loads(fixture[0])["items"]}
    assert {r["question"] for r in records} == originals
    assert all(b < 128 for b in packet) and packet.endswith(b"\n")
    assert (
        b"provenance" not in packet
        and b"expected_label" not in packet
        and b"kind" not in packet
    )


def test_exact_preimages_and_references():
    fixture = control_fixture()
    catalog_hash = sha_bytes(fixture[0])
    ref_raw = c.reference_preimage(catalog_hash, "fixture_00")
    assert (
        ref_raw
        == (
            '["reviewer-protocol-v2-control-reference-v1","'
            + catalog_hash
            + '","fixture_00"]'
        ).encode()
    )
    ref = c.reference_id(catalog_hash, "fixture_00")
    qhash = question_hash(json.loads(fixture[0])["items"][0]["question"])
    visible_raw = c.visible_preimage(ref, qhash)
    assert (
        visible_raw
        == (
            '["reviewer-protocol-v2-control-id-v1",20261003,"'
            + ref
            + '","'
            + qhash
            + '"]'
        ).encode()
    )
    assert ref == "r_" + sha_bytes(ref_raw)
    assert c.visible_id(ref, qhash) == "x_" + sha_bytes(visible_raw)
    assert not ref_raw.endswith(b"\n") and not visible_raw.endswith(b"\n")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v.update(extra=0),
        lambda v: v.update(schema="wrong"),
        lambda v: v["items"].pop(),
        lambda v: v["items"].reverse(),
        lambda v: v["items"][0].update(kind=True),
        lambda v: v["items"][0].update(kind="EXTERNAL"),
        lambda v: v["items"][0].update(question=1),
        lambda v: v["items"][0].update(question="\ud800"),
        lambda v: v["items"][0].update(local_key=v["items"][1]["local_key"]),
        lambda v: v["items"][0].update(local_key="../key"),
        lambda v: v["items"][0]["provenance"].update(author=""),
        lambda v: v["items"][0]["provenance"].update(extra=True),
        lambda v: v["items"][0]["provenance"]["approval_evidence"].update(
            sha256="0" * 64
        ),
        lambda v: v["items"][0]["provenance"]["approval_evidence"].update(
            path="heldout-external/../main/a"
        ),
    ],
)
def test_catalog_failures(mutate):
    raw, _, _, artifacts, _ = control_fixture()
    value = json.loads(raw)
    mutate(value)
    with pytest.raises(ProtocolError):
        c.validate_catalog(canonical(value), artifacts)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v.update(catalog_sha256="0" * 64),
        lambda v: v.update(rubric_sha256="0" * 64),
        lambda v: v.update(extra=True),
        lambda v: v["entries"].pop(),
        lambda v: v["entries"].reverse(),
        lambda v: v["entries"][0].update(reference_key="r_" + "0" * 64),
        lambda v: v["entries"][0].update(original_question_sha256="0" * 64),
        lambda v: next(r for r in v["entries"] if r["kind"] == "ANCHOR").update(
            expected_label=True
        ),
        lambda v: next(
            r
            for r in v["entries"]
            if r["kind"] == "ANCHOR" and r["expected_label"] != "unclear"
        ).update(expected_label="unclear", expected_components=[]),
        lambda v: next(r for r in v["entries"] if r["kind"] == "ANCHOR").update(
            expected_components=["qa", "qa"]
        ),
        lambda v: next(r for r in v["entries"] if r["kind"] == "ANCHOR").update(
            generic_rationale=""
        ),
        lambda v: next(r for r in v["entries"] if r["kind"] == "DIAGNOSTIC").update(
            scoring_permitted=0
        ),
        lambda v: next(r for r in v["entries"] if r["kind"] == "DIAGNOSTIC").update(
            category="wrong"
        ),
        lambda v: next(r for r in v["entries"] if r["kind"] == "DIAGNOSTIC").update(
            policy_expectation=""
        ),
        lambda v: next(r for r in v["entries"] if r["kind"] == "DIAGNOSTIC").update(
            expected_label="qa"
        ),
    ],
)
def test_key_failures(mutate):
    catalog, _, keys, artifacts, rubric = control_fixture()
    value = json.loads(keys)
    mutate(value)
    with pytest.raises(ProtocolError):
        c.validate_keys(canonical(value), catalog, artifacts, rubric)


@pytest.mark.parametrize(
    "path", ["/main/a", "main//a", "main/./a", "main/../a", "C:/a", "main\\a", True]
)
def test_binding_path_failures(path):
    with pytest.raises(ProtocolError):
        c.binding_bytes(dict(path=path, sha256="a" * 64), {})


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: b"\xef\xbb\xbf" + raw,
        lambda raw: raw + b"\n",
        lambda raw: raw.replace(b'"schema":', b'"schema":"wrong","schema":'),
        lambda raw: raw.replace(b'"items":', b'"extra":NaN,"items":'),
    ],
)
def test_canonical_failures(mutate):
    fixture = control_fixture()
    with pytest.raises(ProtocolError):
        c.validate_catalog(mutate(fixture[0]), fixture[3])


def test_collisions(monkeypatch):
    fixture = control_fixture()
    monkeypatch.setattr(c, "visible_id", lambda *a: "x_" + "a" * 64)
    with pytest.raises(ProtocolError, match="duplicate_external_id"):
        c.build_controls(*fixture)
    monkeypatch.setattr(c, "reference_id", lambda *a: "r_" + "a" * 64)
    with pytest.raises(ProtocolError, match="reference_collision"):
        c.build_controls(*fixture)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v.update(packet_sha256="0" * 64),
        lambda v: v["items"][0].update(local_key="wrong"),
        lambda v: v["items"][0].update(reference_key="r_" + "0" * 64),
        lambda v: v["items"][0].update(kind="EXTERNAL"),
        lambda v: v["items"][0].update(extra=True),
        lambda v: v["items"].pop(),
        lambda v: v["items"].reverse(),
    ],
)
def test_mapping_reconstruction(mutate):
    fixture = control_fixture()
    packet, mapping = c.build_controls(*fixture)
    value = json.loads(mapping)
    mutate(value)
    with pytest.raises(ProtocolError):
        c.validate_controls(packet, canonical(value), *fixture)


def test_wording_approval_is_independent_input():
    fixture = control_fixture()
    with pytest.raises(ProtocolError, match="missing_bound_bytes"):
        c.validate_catalog(fixture[0], {})
    assert sha_bytes(fixture[0]) not in next(iter(fixture[3].values())).decode()
    assert sha_bytes(fixture[2]) not in next(iter(fixture[3].values())).decode()


def test_catalog_and_key_serializers():
    catalog, _, keys, approvals, rubric = control_fixture()
    assert c.serialize_catalog(json.loads(catalog), approvals) == catalog
    assert c.serialize_keys(json.loads(keys), catalog, approvals, rubric) == keys
    # A later catalog/key seal is not source-wording evidence and is not consumed.
    unrelated = dict(
        approvals,
        **{"heldout-external/synthetic/later-seal.json": b"not a wording approval"},
    )
    assert c.serialize_catalog(json.loads(catalog), unrelated) == catalog
    with pytest.raises(ProtocolError):
        c.serialize_catalog(
            {"schema": c.schema("control-catalog"), "items": []}, approvals
        )


@pytest.mark.parametrize(
    "change",
    [
        dict(path=True),
        dict(path=[]),
        dict(sha256=True),
        dict(sha256="0" * 64),
        dict(extra=True),
    ],
)
def test_catalog_binding_failures(change):
    catalog, binding, keys, approvals, rubric = control_fixture()
    binding.update(change)
    with pytest.raises(ProtocolError):
        c.build_controls(catalog, binding, keys, approvals, rubric)
