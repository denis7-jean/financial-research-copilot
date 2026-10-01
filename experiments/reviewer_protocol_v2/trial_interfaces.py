"""Pure membership, presentation and logical schedule. No runtime or publication."""

import hashlib

from experiments.reviewer_protocol_v2.common import (
    canonical,
    question_hash,
    require,
    sha_bytes,
)
from experiments.reviewer_protocol_v2.control_serialization import (
    object_bytes,
    object_header,
    ordered,
    records_bytes,
    relative_path,
    schema,
    text,
    validate_controls,
)
from experiments.reviewer_protocol_v2.packet_serialization import (
    build_external_outputs,
    serialize_blind_records,
)
from experiments.reviewer_protocol_v2.selection import (
    B,
    BUNDLE_PATHS,
    exact_keys,
    hex256,
)

PRESENTATION_SEED = 20261002
PRESENTATION_DOMAIN = "reviewer-protocol-v2-presentation-order-v1"
REVIEWERS = ("R1", "R2", "R3")
INTERFACE_BUNDLE_PATHS = (
    *BUNDLE_PATHS,
    "main/experiments/reviewer_protocol_v2/validation.py",
    "main/experiments/reviewer_protocol_v2/control_serialization.py",
    "main/experiments/reviewer_protocol_v2/trial_interfaces.py",
)


def interface_bundle(code_bytes):
    """Hash caller-supplied executable sources; performs no filesystem access."""
    exact_keys(code_bytes, INTERFACE_BUNDLE_PATHS)
    require(all(type(raw) is bytes for raw in code_bytes.values()), "bundle_bytes")
    files = {path: sha_bytes(raw) for path, raw in code_bytes.items()}
    return dict(files=files, sha256=sha_bytes(canonical(files)))


def validate_external(packet, mapping_raw, inputs_sha256):
    """Consistency check only; upstream accepted receipt replay remains required."""
    hex256(inputs_sha256)
    records = records_bytes(packet, 24)
    mapping = object_header(
        mapping_raw, "external-map", ("inputs_sha256", "packet_sha256", "items")
    )
    require(
        mapping["inputs_sha256"] == inputs_sha256
        and mapping["packet_sha256"] == sha_bytes(packet),
        "external_binding",
    )
    ordered(mapping["items"], "item_id")
    require(len(mapping["items"]) == 24, "external_mapping_size")
    questions = {row["item_id"]: row["question"] for row in records}
    accepted = []
    for item in mapping["items"]:
        exact_keys(
            item,
            (
                "item_id",
                "source",
                "candidate_id",
                "stratum",
                "native_sampling_stratum",
                "original_question_sha256",
                "source_revision",
                "context_group",
            ),
        )
        for key in (
            "source",
            "candidate_id",
            "stratum",
            "native_sampling_stratum",
            "source_revision",
            "context_group",
        ):
            text(item[key])
        hex256(item["original_question_sha256"])
        require(item["item_id"] in questions, "external_bijection")
        accepted.append(
            dict(
                cand_id=item["candidate_id"],
                source=item["source"],
                sampling_stratum=item["native_sampling_stratum"],
                question=questions[item["item_id"]],
                question_sha256=item["original_question_sha256"],
                source_revision=item["source_revision"],
                context_group=item["context_group"],
            )
        )
    expected = build_external_outputs(accepted, inputs_sha256)
    require((packet, mapping_raw) == expected, "external_reconstruction")
    return records, mapping["items"]


def build_trial(
    external_packet,
    external_mapping,
    inputs_sha256,
    control_packet,
    control_mapping,
    catalog_raw,
    catalog_binding,
    keys_raw,
    source_wording_approvals,
    rubric_sha256,
):
    external, external_items = validate_external(
        external_packet, external_mapping, inputs_sha256
    )
    validate_controls(
        control_packet,
        control_mapping,
        catalog_raw,
        catalog_binding,
        keys_raw,
        source_wording_approvals,
        rubric_sha256,
    )
    controls = records_bytes(control_packet, 21)
    records = external + controls
    require(len({r["item_id"] for r in records}) == 45, "combined_id_collision")
    require(
        len({question_hash(r["question"]) for r in records}) == 45,
        "duplicate_question_assembly",
    )
    items = [
        dict(
            item_id=r["item_id"],
            kind="EXTERNAL",
            reference_key=r["item_id"],
            original_question_sha256=r["original_question_sha256"],
        )
        for r in external_items
    ]
    items.extend(
        dict(
            item_id=r["item_id"],
            kind=r["kind"],
            reference_key=r["reference_key"],
            original_question_sha256=r["original_question_sha256"],
        )
        for r in object_bytes(control_mapping)["items"]
    )
    packet = serialize_blind_records(records)
    membership = canonical(
        dict(
            schema=schema("trial-membership"),
            external_packet_sha256=sha_bytes(external_packet),
            external_mapping_sha256=sha_bytes(external_mapping),
            control_packet_sha256=sha_bytes(control_packet),
            control_mapping_sha256=sha_bytes(control_mapping),
            control_keys_sha256=sha_bytes(keys_raw),
            rubric_sha256=rubric_sha256,
            combined_packet_sha256=sha_bytes(packet),
            items=sorted(items, key=lambda r: r["item_id"].encode()),
        )
    )
    return packet, membership


def validate_trial(packet, membership, *inputs):
    records_bytes(packet, 45)
    object_header(
        membership,
        "trial-membership",
        (
            "external_packet_sha256",
            "external_mapping_sha256",
            "control_packet_sha256",
            "control_mapping_sha256",
            "control_keys_sha256",
            "rubric_sha256",
            "combined_packet_sha256",
            "items",
        ),
    )
    require((packet, membership) == build_trial(*inputs), "membership_reconstruction")


def presentation_preimage(reviewer_slot, item_id):
    from experiments.reviewer_protocol_v2.control_serialization import identifier

    require(type(reviewer_slot) is str and reviewer_slot in REVIEWERS, "reviewer_slot")
    identifier(item_id)
    return B([PRESENTATION_DOMAIN, PRESENTATION_SEED, reviewer_slot, item_id])


def presentation_digest(reviewer_slot, item_id):
    return hashlib.sha256(presentation_preimage(reviewer_slot, item_id)).digest()


def presentation_key(reviewer_slot, item_id):
    return presentation_digest(reviewer_slot, item_id), item_id.encode(
        "utf-8", errors="strict"
    )


def check_membership(packet, membership_raw):
    """Structural/hash check; full validate_trial joins must precede presentation."""
    records = records_bytes(packet, 45)
    membership = object_header(
        membership_raw,
        "trial-membership",
        (
            "external_packet_sha256",
            "external_mapping_sha256",
            "control_packet_sha256",
            "control_mapping_sha256",
            "control_keys_sha256",
            "rubric_sha256",
            "combined_packet_sha256",
            "items",
        ),
    )
    for key in membership:
        if key.endswith("sha256"):
            hex256(membership[key])
    require(
        membership["combined_packet_sha256"] == sha_bytes(packet),
        "combined_packet_hash",
    )
    ordered(membership["items"], "item_id")
    require(len(membership["items"]) == 45, "membership_size")
    counts = dict(EXTERNAL=0, ANCHOR=0, DIAGNOSTIC=0)
    from experiments.reviewer_protocol_v2.control_serialization import identifier

    for row, item in zip(records, membership["items"], strict=True):
        exact_keys(
            item, ("item_id", "kind", "reference_key", "original_question_sha256")
        )
        require(type(item["kind"]) is str and item["kind"] in counts, "membership_kind")
        counts[item["kind"]] += 1
        require(
            item["item_id"] == row["item_id"]
            and item["original_question_sha256"] == question_hash(row["question"]),
            "membership_question",
        )
        if item["kind"] == "EXTERNAL":
            require(item["reference_key"] == item["item_id"], "external_reference")
        else:
            identifier(item["reference_key"], "r_")
    require(counts == dict(EXTERNAL=24, ANCHOR=15, DIAGNOSTIC=6), "membership_counts")
    require(
        len({question_hash(r["question"]) for r in records}) == 45,
        "duplicate_question_assembly",
    )
    return records


def build_presentations(packet, membership_raw, destinations):
    records = check_membership(packet, membership_raw)
    exact_keys(destinations, REVIEWERS)
    for path in destinations.values():
        relative_path(path)
        require(path.startswith("heldout-external/"), "presentation_private_path")
    require(len(set(destinations.values())) == 3, "presentation_path_alias")
    payloads, entries = {}, []
    for reviewer in REVIEWERS:
        permuted = sorted(
            records, key=lambda r: presentation_key(reviewer, r["item_id"])
        )
        raw = b"".join(canonical(r) for r in permuted)
        payloads[destinations[reviewer]] = raw
        entries.append(
            dict(
                reviewer_slot=reviewer,
                item_ids=[r["item_id"] for r in permuted],
                packet=dict(path=destinations[reviewer], sha256=sha_bytes(raw)),
            )
        )
    manifest = canonical(
        dict(
            schema=schema("presentation-manifest"),
            combined_packet_sha256=sha_bytes(packet),
            membership_sha256=sha_bytes(membership_raw),
            domain=PRESENTATION_DOMAIN,
            seed=PRESENTATION_SEED,
            reviewers=entries,
        )
    )
    return payloads, manifest


def validate_presentations(packet, membership_raw, payloads, manifest_raw):
    manifest = object_header(
        manifest_raw,
        "presentation-manifest",
        ("combined_packet_sha256", "membership_sha256", "domain", "seed", "reviewers"),
    )
    require(
        type(manifest["seed"]) is int and manifest["seed"] == PRESENTATION_SEED,
        "presentation_seed",
    )
    require(
        type(manifest["reviewers"]) is list and len(manifest["reviewers"]) == 3,
        "reviewer_count",
    )
    destinations = {}
    for expected, row in zip(REVIEWERS, manifest["reviewers"], strict=True):
        exact_keys(row, ("reviewer_slot", "item_ids", "packet"))
        require(row["reviewer_slot"] == expected, "reviewer_order")
        exact_keys(row["packet"], ("path", "sha256"))
        destinations[expected] = row["packet"]["path"]
    expected_payloads, expected_manifest = build_presentations(
        packet, membership_raw, destinations
    )
    require(
        type(payloads) is dict
        and payloads == expected_payloads
        and manifest_raw == expected_manifest,
        "presentation_reconstruction",
    )
    for raw in payloads.values():
        records_bytes(raw, 45, sorted_ids=False)
    return manifest


def build_schedule(packet, membership_raw, payloads, manifest_raw):
    manifest = validate_presentations(packet, membership_raw, payloads, manifest_raw)
    records = {r["item_id"]: r for r in records_bytes(packet, 45)}
    items = []
    for position in range(45):
        for reviewer in manifest["reviewers"]:
            item_id = reviewer["item_ids"][position]
            items.append(
                dict(
                    schedule_index=len(items) + 1,
                    reviewer_slot=reviewer["reviewer_slot"],
                    presentation_index=position + 1,
                    item_id=item_id,
                    record_sha256=sha_bytes(canonical(records[item_id])),
                )
            )
    return canonical(
        dict(
            schema=schema("logical-schedule"),
            presentation_manifest_sha256=sha_bytes(manifest_raw),
            retry_limit=0,
            items=items,
        )
    )


def validate_schedule(schedule_raw, packet, membership_raw, payloads, manifest_raw):
    schedule = object_header(
        schedule_raw,
        "logical-schedule",
        ("presentation_manifest_sha256", "retry_limit", "items"),
    )
    require(
        type(schedule["retry_limit"]) is int and schedule["retry_limit"] == 0,
        "retry_limit",
    )
    expected = build_schedule(packet, membership_raw, payloads, manifest_raw)
    require(schedule_raw == expected, "schedule_reconstruction")
