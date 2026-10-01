"""Pure control contracts. Inputs are bytes; no IO, approval manager or sealing."""

import re

from experiments.reviewer_protocol_v2.common import (
    ProtocolError,
    canonical,
    decode,
    question_hash,
    require,
    sha_bytes,
)
from experiments.reviewer_protocol_v2.packet_serialization import (
    serialize_blind_records,
)
from experiments.reviewer_protocol_v2.selection import B, exact_keys, hex256
from experiments.reviewer_protocol_v2.validation import LABELS

CONTROL_SEED = 20261003
CATEGORIES = (
    "OMITTED_COMPANY_OR_PERIOD",
    "ESSENTIAL_UNSEEN_MATERIAL",
    "BOUNDARY_INTERPRETATION",
)


def schema(name):
    return "reviewer-protocol-v2-" + name + "-v1"


def text(value, nonempty=False):
    require(type(value) is str and (not nonempty or bool(value.strip())), "string_type")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ProtocolError("string_utf8") from None


def identifier(value, prefix="x_"):
    require(
        type(value) is str and re.fullmatch(prefix + r"[0-9a-f]{64}", value),
        "opaque_id",
    )


def relative_path(value):
    text(value, True)
    parts = value.split("/")
    require(
        "\\" not in value
        and ":" not in value
        and len(parts) > 1
        and parts[0] in {"main", "heldout-external"}
        and all(p not in {"", ".", ".."} for p in parts),
        "relative_path",
    )


def binding_bytes(binding, artifacts):
    """Resolve only caller-supplied bytes, never a filesystem path."""
    exact_keys(binding, ("path", "sha256"))
    relative_path(binding["path"])
    hex256(binding["sha256"])
    require(
        type(artifacts) is dict and binding["path"] in artifacts, "missing_bound_bytes"
    )
    raw = artifacts[binding["path"]]
    require(
        type(raw) is bytes and sha_bytes(raw) == binding["sha256"], "bound_bytes_hash"
    )
    return raw


def object_bytes(raw):
    require(type(raw) is bytes, "canonical_bytes")
    try:
        value = decode(raw.decode("utf-8", errors="strict"))
        require(canonical(value) == raw, "noncanonical_json")
    except UnicodeError:
        raise ProtocolError("json_utf8") from None
    require(type(value) is dict, "json_object")
    return value


def object_header(raw, name, keys):
    value = object_bytes(raw)
    exact_keys(value, ("schema", *keys))
    require(value["schema"] == schema(name), "schema_version")
    return value


def serialize_catalog(value, source_wording_approvals):
    raw = canonical(value)
    validate_catalog(raw, source_wording_approvals)
    return raw


def serialize_keys(value, catalog_raw, source_wording_approvals, rubric_sha256):
    raw = canonical(value)
    validate_keys(raw, catalog_raw, source_wording_approvals, rubric_sha256)
    return raw


def ordered(items, field):
    require(type(items) is list and all(type(r) is dict for r in items), "record_array")
    require(all(type(r.get(field)) is str for r in items), "order_key")
    keys = [r[field].encode("utf-8", errors="strict") for r in items]
    require(
        keys == sorted(keys) and len(set(keys)) == len(keys),
        "record_order_or_duplicate",
    )


def records_bytes(raw, count, sorted_ids=True):
    require(
        type(raw) is bytes
        and raw.endswith(b"\n")
        and not raw.startswith(b"\xef\xbb\xbf"),
        "packet_bytes",
    )
    try:
        lines = raw.decode("utf-8", errors="strict").split("\n")[:-1]
        rows = [object_bytes(line.encode("utf-8") + b"\n") for line in lines]
    except UnicodeError:
        raise ProtocolError("packet_utf8") from None
    require(len(rows) == count, "packet_size")
    ids = []
    for row in rows:
        exact_keys(row, ("item_id", "question"))
        identifier(row["item_id"])
        text(row["question"])
        ids.append(row["item_id"])
    require(len(set(ids)) == count, "duplicate_visible_id")
    if sorted_ids:
        ordered(rows, "item_id")
    return rows


def validate_catalog(raw, source_wording_approvals):
    catalog = object_header(raw, "control-catalog", ("items",))
    ordered(catalog["items"], "local_key")
    require(len(catalog["items"]) == 21, "catalog_size")
    counts = dict(ANCHOR=0, DIAGNOSTIC=0)
    for row in catalog["items"]:
        exact_keys(row, ("local_key", "kind", "question", "provenance"))
        require(re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", row["local_key"]), "local_key")
        require(type(row["kind"]) is str and row["kind"] in counts, "control_kind")
        counts[row["kind"]] += 1
        text(row["question"], True)
        exact_keys(
            row["provenance"], ("author", "source_revision", "approval_evidence")
        )
        text(row["provenance"]["author"], True)
        text(row["provenance"]["source_revision"], True)
        evidence = binding_bytes(
            row["provenance"]["approval_evidence"], source_wording_approvals
        )
        # The caller supplies independent wording approvals, not a downstream catalog approval.
        require(
            evidence != raw and sha_bytes(raw).encode() not in evidence,
            "approval_hash_cycle",
        )
    require(counts == dict(ANCHOR=15, DIAGNOSTIC=6), "control_counts")
    return catalog


def reference_preimage(catalog_sha256, local_key):
    hex256(catalog_sha256)
    text(local_key, True)
    require(re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", local_key), "local_key")
    return B(["reviewer-protocol-v2-control-reference-v1", catalog_sha256, local_key])


def reference_id(catalog_sha256, local_key):
    return "r_" + sha_bytes(reference_preimage(catalog_sha256, local_key))


def visible_preimage(reference_key, original_question_sha256):
    identifier(reference_key, "r_")
    hex256(original_question_sha256)
    return B(
        [
            "reviewer-protocol-v2-control-id-v1",
            CONTROL_SEED,
            reference_key,
            original_question_sha256,
        ]
    )


def visible_id(reference_key, original_question_sha256):
    return "x_" + sha_bytes(visible_preimage(reference_key, original_question_sha256))


def validate_keys(raw, catalog_raw, source_wording_approvals, rubric_sha256):
    hex256(rubric_sha256)
    catalog = validate_catalog(catalog_raw, source_wording_approvals)
    keys = object_header(
        raw, "control-keys", ("catalog_sha256", "rubric_sha256", "entries")
    )
    require(
        keys["catalog_sha256"] == sha_bytes(catalog_raw)
        and keys["rubric_sha256"] == rubric_sha256,
        "keys_binding",
    )
    ordered(keys["entries"], "reference_key")
    expected = {
        reference_id(sha_bytes(catalog_raw), row["local_key"]): row
        for row in catalog["items"]
    }
    require(
        len(expected) == 21 and len(keys["entries"]) == 21,
        "reference_collision_or_key_size",
    )
    anchors, diagnostics = dict.fromkeys(LABELS, 0), dict.fromkeys(CATEGORIES, 0)
    for key in keys["entries"]:
        require(key["reference_key"] in expected, "unknown_reference")
        source = expected[key["reference_key"]]
        require(
            key.get("kind") == source["kind"]
            and key.get("original_question_sha256")
            == question_hash(source["question"]),
            "key_source_binding",
        )
        if source["kind"] == "ANCHOR":
            exact_keys(
                key,
                (
                    "reference_key",
                    "kind",
                    "original_question_sha256",
                    "expected_label",
                    "expected_components",
                    "generic_rationale",
                ),
            )
            require(
                type(key["expected_label"]) is str and key["expected_label"] in LABELS,
                "anchor_label",
            )
            components = (
                ["qa", "summarize"] if key["expected_label"] == "multi_intent" else []
            )
            require(
                type(key["expected_components"]) is list
                and key["expected_components"] == components,
                "anchor_components",
            )
            text(key["generic_rationale"], True)
            anchors[key["expected_label"]] += 1
        else:
            exact_keys(
                key,
                (
                    "reference_key",
                    "kind",
                    "original_question_sha256",
                    "category",
                    "policy_expectation",
                    "scoring_permitted",
                ),
            )
            require(
                type(key["category"]) is str and key["category"] in CATEGORIES,
                "diagnostic_category",
            )
            require(key["scoring_permitted"] is False, "diagnostic_scoring")
            text(key["policy_expectation"], True)
            diagnostics[key["category"]] += 1
    require(
        all(n == 3 for n in anchors.values())
        and all(n == 2 for n in diagnostics.values()),
        "key_distribution",
    )
    for row in catalog["items"]:
        evidence = binding_bytes(
            row["provenance"]["approval_evidence"], source_wording_approvals
        )
        require(
            evidence != raw and sha_bytes(raw).encode() not in evidence,
            "approval_hash_cycle",
        )
    return keys


def build_controls(
    catalog_raw, catalog_binding, keys_raw, source_wording_approvals, rubric_sha256
):
    """Return validated packet/map bytes. Does not approve content or create a seal."""
    exact_keys(catalog_binding, ("path", "sha256"))
    relative_path(catalog_binding["path"])
    binding_bytes(catalog_binding, {catalog_binding["path"]: catalog_raw})
    catalog = validate_catalog(catalog_raw, source_wording_approvals)
    validate_keys(keys_raw, catalog_raw, source_wording_approvals, rubric_sha256)
    records, items, refs = [], [], set()
    for row in catalog["items"]:
        ref = reference_id(sha_bytes(catalog_raw), row["local_key"])
        require(ref not in refs, "reference_collision")
        refs.add(ref)
        digest = question_hash(row["question"])
        item_id = visible_id(ref, digest)
        records.append(dict(item_id=item_id, question=row["question"]))
        items.append(
            dict(
                item_id=item_id,
                reference_key=ref,
                local_key=row["local_key"],
                kind=row["kind"],
                original_question_sha256=digest,
            )
        )
    packet = serialize_blind_records(records)
    mapping = canonical(
        dict(
            schema=schema("control-map"),
            catalog=catalog_binding,
            packet_sha256=sha_bytes(packet),
            items=sorted(items, key=lambda r: r["item_id"].encode()),
        )
    )
    return packet, mapping


def validate_controls(
    packet,
    mapping,
    catalog_raw,
    catalog_binding,
    keys_raw,
    source_wording_approvals,
    rubric_sha256,
):
    records_bytes(packet, 21)
    object_header(mapping, "control-map", ("catalog", "packet_sha256", "items"))
    expected = build_controls(
        catalog_raw, catalog_binding, keys_raw, source_wording_approvals, rubric_sha256
    )
    require((packet, mapping) == expected, "control_reconstruction")
