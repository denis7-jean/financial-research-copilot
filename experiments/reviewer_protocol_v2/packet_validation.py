"""Future packet integrity validation as a pure function; never creates a packet."""

from collections import Counter
from experiments.reviewer_protocol_v2.common import require
from experiments.reviewer_protocol_v2.constraints import validate_diversity
from experiments.reviewer_protocol_v2.eligibility import (
    QUOTAS,
    classify,
    reference_index,
)
from experiments.reviewer_protocol_v2.exposure import exposure_ledger


def validate_packet(rows, population, inventory, quotas=None):
    quotas = QUOTAS if quotas is None else quotas
    require(
        all(
            isinstance(row, dict) and isinstance(row.get("cand_id"), str)
            for row in rows
        ),
        "packet_invalid_record",
    )
    require(
        len({row.get("cand_id") for row in rows}) == len(rows),
        "packet_duplicate_identity",
    )
    refs = reference_index(population)
    for row in rows:
        require(
            classify(row, refs)["disposition"] == "SCREEN_PASS",
            "packet_binding_or_eligibility",
        )
    require(
        Counter((row["source"], row["sampling_stratum"]) for row in rows)
        == Counter(quotas),
        "packet_quota_mismatch",
    )
    flags = {row["cand_id"]: row for row in exposure_ledger(population, inventory)}
    require(
        all(
            not any(
                flags[row["cand_id"]][key]
                for key in ("direct", "native_group", "near_duplicate")
            )
            for row in rows
        ),
        "packet_exposure_exclusion",
    )
    validate_diversity(rows)
    return True
