"""Exact external bytes and private mapping validation; never writes artifacts."""

import re

from experiments.reviewer_protocol_v2.common import canonical, decode, question_hash, require, sha_bytes
from experiments.reviewer_protocol_v2.selection import (
    B, STRATUM_ENTRIES, exact_keys, hex256, prepare_inputs, replay_receipt,
    stratum_label, validate_identity,
)


def original_hash(row):
    require(type(row.get("question")) is str, "question_type")
    hex256(row.get("question_sha256"))
    require(question_hash(row["question"]) == row["question_sha256"], "question_hash")
    return row["question_sha256"]


def external_id_preimage(row):
    validate_identity(row.get("source"), row.get("cand_id"))
    return B(["reviewer-protocol-v2-external-id-v1", 20261001, row["source"],
              row["cand_id"], original_hash(row)])


def external_id(row):
    return "x_" + sha_bytes(external_id_preimage(row))


def serialize_blind_records(records):
    """Byte primitive; production validity additionally requires 24 mapped items."""
    require(type(records) is list, "blind_records")
    seen = set()
    for row in records:
        exact_keys(row, ("item_id", "question"))
        require(type(row["item_id"]) is str and re.fullmatch(r"x_[0-9a-f]{64}", row["item_id"]), "item_id")
        require(type(row["question"]) is str, "question_type")
        row["question"].encode("utf-8", errors="strict")
        require(row["item_id"] not in seen, "duplicate_external_id")
        seen.add(row["item_id"])
    return b"".join(canonical(r) for r in sorted(records, key=lambda r: r["item_id"].encode("utf-8")))


def build_external_outputs(accepted, inputs_sha256):
    hex256(inputs_sha256)
    require(type(accepted) is list and len(accepted) == 24, "production_size")
    identities = [(r["source"], r["cand_id"]) for r in accepted]
    require(len(set(identities)) == 24 and len({r["cand_id"] for r in accepted}) == 24, "duplicate_identity")
    for entry in STRATUM_ENTRIES:
        require(sum(stratum_label(r) == entry["stratum"] for r in accepted) == entry["quota"], "production_quota")
    records, items = [], []
    for row in accepted:
        require(type(row.get("source_revision")) is str and type(row.get("context_group")) is str, "mapping_metadata")
        item_id = external_id(row)
        records.append(dict(item_id=item_id, question=row["question"]))
        items.append(dict(item_id=item_id, source=row["source"], candidate_id=row["cand_id"],
                          stratum=stratum_label(row), native_sampling_stratum=row["sampling_stratum"],
                          original_question_sha256=original_hash(row), source_revision=row["source_revision"],
                          context_group=row["context_group"]))
    packet = serialize_blind_records(records)
    mapping = dict(schema="reviewer-protocol-v2-external-map-v1", inputs_sha256=inputs_sha256,
                   packet_sha256=sha_bytes(packet), items=sorted(items, key=lambda r: r["item_id"].encode("utf-8")))
    return packet, canonical(mapping)


def canonical_object(raw):
    require(type(raw) is bytes, "private_bytes")
    value = decode(raw.decode("utf-8", errors="strict"))
    require(canonical(value) == raw, "private_canonical")
    return value


def validate_result(root, binding, expected_sha256, payloads):
    require(type(payloads) is dict and "selection_receipt.json" in payloads, "result_files")
    receipt = canonical_object(payloads["selection_receipt.json"])
    accepted = replay_receipt(prepare_inputs(root, binding, expected_sha256), receipt, expected_sha256)
    if receipt["status"] == "SHORTFALL":
        exact_keys(payloads, ("selection_receipt.json",))
        return
    exact_keys(payloads, ("selection_receipt.json", "external_blind.jsonl", "private_mapping.json"))
    mapping = canonical_object(payloads["private_mapping.json"])
    exact_keys(mapping, ("schema", "inputs_sha256", "packet_sha256", "items"))
    packet, expected_mapping = build_external_outputs(accepted, expected_sha256)
    require(payloads["external_blind.jsonl"] == packet and payloads["private_mapping.json"] == expected_mapping,
            "packet_mapping_replay")
    require(receipt["packet_sha256"] == sha_bytes(packet)
            and receipt["mapping_sha256"] == sha_bytes(expected_mapping), "output_binding")
