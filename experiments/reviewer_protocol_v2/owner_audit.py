"""Pure completed-audit/seal validation and explicit primary population views."""

import re
from collections import Counter
from datetime import datetime
from itertools import combinations

from experiments.reviewer_protocol_v2.analysis import analyze_external, ratio
from experiments.reviewer_protocol_v2.common import canonical, require, sha_bytes
from experiments.reviewer_protocol_v2.control_serialization import (
    object_header,
    ordered,
    records_bytes,
    schema,
    text,
)
from experiments.reviewer_protocol_v2.selection import exact_keys, hex256
from experiments.reviewer_protocol_v2.trial_interfaces import (
    INTERFACE_BUNDLE_PATHS,
    validate_external,
)
from experiments.reviewer_protocol_v2.validation import (
    CERTAINTIES,
    LABELS,
    validate_text,
)

REASONS = (
    "OWNER_ABSTAINED",
    "OWNER_CONTEXT_CONCERN",
    "REVIEWER_MISSING",
    "REVIEWER_INVALID",
)
OWNER_BUNDLE_PATHS = (
    *INTERFACE_BUNDLE_PATHS,
    "main/experiments/reviewer_protocol_v2/analysis.py",
    "main/experiments/reviewer_protocol_v2/owner_audit.py",
)


def owner_bundle(code_bytes):
    exact_keys(code_bytes, OWNER_BUNDLE_PATHS)
    require(all(type(raw) is bytes for raw in code_bytes.values()), "bundle_bytes")
    files = {path: sha_bytes(raw) for path, raw in code_bytes.items()}
    return dict(files=files, sha256=sha_bytes(canonical(files)))


def validate_audit(raw, packet, expected_packet_sha256, rubric, expected_rubric_sha256):
    """Completed annotations only; no unfinished template or label repair mode."""
    hex256(expected_packet_sha256)
    hex256(expected_rubric_sha256)
    require(
        type(rubric) is bytes and sha_bytes(rubric) == expected_rubric_sha256,
        "rubric_binding",
    )
    questions = records_bytes(packet, 24)
    require(sha_bytes(packet) == expected_packet_sha256, "packet_binding")
    audit = object_header(
        raw, "owner-audit", ("packet_sha256", "rubric_sha256", "records")
    )
    require(
        audit["packet_sha256"] == expected_packet_sha256
        and audit["rubric_sha256"] == expected_rubric_sha256,
        "audit_binding",
    )
    ordered(audit["records"], "item_id")
    require(
        len(audit["records"]) == 24
        and [r["item_id"] for r in audit["records"]]
        == [r["item_id"] for r in questions],
        "audit_id_binding",
    )
    for row in audit["records"]:
        exact_keys(
            row,
            (
                "item_id",
                "label",
                "components",
                "certainty",
                "abstained",
                "context_concern",
                "note",
            ),
        )
        require(
            type(row["abstained"]) is bool and type(row["context_concern"]) is bool,
            "audit_boolean",
        )
        text(row["note"], row["abstained"] or row["context_concern"])
        require(type(row["components"]) is list, "audit_components")
        if row["abstained"]:
            require(
                row["label"] is None
                and row["components"] == []
                and row["certainty"] is None,
                "audit_abstention",
            )
        else:
            require(
                type(row["label"]) is str
                and row["label"] in LABELS
                and type(row["certainty"]) is str
                and row["certainty"] in CERTAINTIES,
                "audit_label_certainty",
            )
            require(
                row["components"]
                == (["qa", "summarize"] if row["label"] == "multi_intent" else []),
                "audit_components",
            )
    return audit


def serialize_audit(
    value, packet, expected_packet_sha256, rubric, expected_rubric_sha256
):
    raw = canonical(value)
    validate_audit(raw, packet, expected_packet_sha256, rubric, expected_rubric_sha256)
    return raw


def validate_seal(
    seal_raw,
    audit_raw,
    packet,
    expected_packet_sha256,
    rubric,
    expected_rubric_sha256,
    external_mapping,
    expected_mapping_sha256,
    inputs_sha256,
    expected_freeze1_sha256,
):
    """Validate supplied evidence only; does not create a seal or durable claim."""
    validate_audit(
        audit_raw, packet, expected_packet_sha256, rubric, expected_rubric_sha256
    )
    hex256(expected_mapping_sha256)
    hex256(expected_freeze1_sha256)
    require(
        type(external_mapping) is bytes
        and sha_bytes(external_mapping) == expected_mapping_sha256,
        "mapping_binding",
    )
    validate_external(packet, external_mapping, inputs_sha256)
    seal = object_header(
        seal_raw,
        "owner-audit-seal",
        (
            "freeze1_sha256",
            "audit_sha256",
            "packet_sha256",
            "rubric_sha256",
            "external_mapping_sha256",
            "owner_attestation",
            "sealed_utc",
        ),
    )
    expected = dict(
        freeze1_sha256=expected_freeze1_sha256,
        audit_sha256=sha_bytes(audit_raw),
        packet_sha256=expected_packet_sha256,
        rubric_sha256=expected_rubric_sha256,
        external_mapping_sha256=expected_mapping_sha256,
    )
    require(all(seal[k] == v for k, v in expected.items()), "seal_binding")
    exact_keys(
        seal["owner_attestation"], ("no_ai_assistance", "no_reviewer_votes_seen")
    )
    require(
        all(v is True for v in seal["owner_attestation"].values()), "seal_attestation"
    )
    text(seal["sealed_utc"])
    require(
        re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
            seal["sealed_utc"],
        ),
        "seal_utc_format",
    )
    try:
        datetime.strptime(seal["sealed_utc"], "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        require(False, "seal_utc_calendar")
    return seal


def analyze_owner(
    audit_raw,
    packet,
    expected_packet_sha256,
    rubric,
    expected_rubric_sha256,
    reviewers,
    answer_texts,
):
    """Immutable-input population view. Already-extracted local JSON votes only."""
    audit = validate_audit(
        audit_raw, packet, expected_packet_sha256, rubric, expected_rubric_sha256
    )
    require(
        type(reviewers) is list
        and len(reviewers) == 3
        and all(type(r) is str and bool(r) for r in reviewers)
        and len(set(reviewers)) == 3,
        "analysis_reviewers",
    )
    require(type(answer_texts) is dict, "answer_texts")
    ids = [r["item_id"] for r in audit["records"]]
    require(
        all(
            type(k) is tuple and len(k) == 2 and k[0] in ids and k[1] in reviewers
            for k in answer_texts
        ),
        "unplanned_answer",
    )
    owner = {r["item_id"]: r for r in audit["records"]}
    votes = {
        (item, reviewer): validate_text(answer_texts.get((item, reviewer)))
        for item in ids
        for reviewer in reviewers
    }
    # A separate local projection; never rewrite the sealed records.
    eligible_labels = {
        item: (
            row["label"]
            if not row["abstained"] and not row["context_concern"]
            else None
        )
        for item, row in owner.items()
    }
    primary = analyze_external(ids, reviewers, answer_texts, eligible_labels)
    # Preserve actual raw owner-label availability; concerns are not abstentions.
    abstentions = sum(r["abstained"] for r in owner.values())
    primary["owner_label_availability"] = ratio(24 - abstentions, 24)
    primary["owner_abstentions_or_missing"] = abstentions
    reviewer_only = {}
    for left, right in combinations(reviewers, 2):
        included = [
            item
            for item in ids
            if votes[(item, left)]["valid"] and votes[(item, right)]["valid"]
        ]
        reviewer_only[left + "&" + right] = dict(
            included_ids=included, coverage=ratio(len(included), 24)
        )
    panels = [item for item in ids if all(votes[(item, r)]["valid"] for r in reviewers)]
    populations = {}
    for reviewer in reviewers:
        included, excluded = [], []
        masks = Counter()
        totals = dict.fromkeys(REASONS, 0)
        for item in ids:
            row = owner[item]
            reasons = []
            if row["abstained"]:
                reasons.append("OWNER_ABSTAINED")
            if row["context_concern"]:
                reasons.append("OWNER_CONTEXT_CONCERN")
            if (item, reviewer) not in answer_texts:
                reasons.append("REVIEWER_MISSING")
            elif not votes[(item, reviewer)]["valid"]:
                reasons.append("REVIEWER_INVALID")
            if reasons:
                excluded.append(dict(item_id=item, reasons=reasons))
                masks["+".join(reasons)] += 1
                for reason in reasons:
                    totals[reason] += 1
            else:
                included.append(item)
        populations[reviewer] = dict(
            included_ids=included,
            coverage=ratio(len(included), 24),
            excluded=excluded,
            reason_counts=totals,
            exact_reason_combinations=dict(sorted(masks.items())),
        )
    return dict(
        schema=schema("owner-comparison-populations"),
        primary=primary,
        owner_counts=dict(
            abstentions=abstentions,
            context_concerns=sum(r["context_concern"] for r in owner.values()),
            abstention_and_context_concern=sum(
                r["abstained"] and r["context_concern"] for r in owner.values()
            ),
        ),
        reviewer_only=dict(
            pairs=reviewer_only,
            fleiss=dict(included_ids=panels, coverage=ratio(len(panels), 24)),
        ),
        owner_comparison=populations,
    )
