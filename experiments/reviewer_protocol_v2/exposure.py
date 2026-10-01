"""Known exposure binding; derived exclusions never become direct exposure seeds."""

from collections import defaultdict
from experiments.reviewer_protocol_v2.common import (
    question_hash,
    read_json,
    require,
    verify_file,
)
from experiments.reviewer_protocol_v2.eligibility import normalize
from experiments.reviewer_protocol_v2.similarity import cos, conflicts, grams

CATEGORIES = {
    "historical_trial_packet",
    "removed_control",
    "planning_document_disclosure",
    "work_history_disclosure",
    "owner_audit",
    "reviewer_request",
    "other_documented_exposure",
}


class InventoryBuilder:
    def __init__(self, population):
        self.population = {row["cand_id"]: row for row in population}
        self.exact = defaultdict(list)
        self.normalized = defaultdict(list)
        for row in population:
            self.exact[row["question"]].append(row["cand_id"])
            self.normalized[normalize(row["question"])].append(row["cand_id"])
        self.evidence = []
        self.outside = {}

    def identify(self, cid=None, question=None):
        if cid is not None:
            require(cid in self.population, "exposure_unknown_id")
            require(
                question is None
                or question_hash(question)
                == question_hash(self.population[cid]["question"]),
                "exposure_identity_mismatch",
            )
            return [cid], "candidate_id"
        require(
            isinstance(question, str) and normalize(question),
            "exposure_unusable_question",
        )
        if question in self.exact:
            return self.exact[question], "exact_original_question"
        if normalize(question) in self.normalized:
            return self.normalized[
                normalize(question)
            ], "registered_normalized_equality"
        return [], "outside_pilot_full_text"

    def add(
        self,
        category,
        source,
        source_digest,
        locator,
        *,
        cid=None,
        question=None,
        stage,
        actor="unknown",
        timestamp=None,
        timestamp_basis=None,
        metadata=None,
        completeness="authoritative_complete_record",
    ):
        require(category in CATEGORIES, "unknown_exposure_category")
        require(
            completeness
            in {
                "authoritative_complete_record",
                "accepted_exact_recovery",
                "canonical_id_binding",
            },
            "incomplete_exposure_reference",
        )
        ids, resolution = self.identify(cid, question)
        if not ids:
            digest = question_hash(question)
            self.outside.setdefault(
                digest,
                {
                    "question": question,
                    "question_sha256": digest,
                    "complete": True,
                    "evidence_indices": [],
                },
            )
        for item in ids or [None]:
            digest = (
                question_hash(self.population[item]["question"])
                if item
                else question_hash(question)
            )
            evidence = {
                "category": category,
                "source": source,
                "source_sha256": source_digest,
                "locator": locator,
                "cand_id": item,
                "question_sha256": digest,
                "resolution": resolution,
                "stage": stage,
                "actor": actor,
                "timestamp": timestamp,
                "timestamp_basis": timestamp_basis,
                "completeness": completeness,
                "metadata": metadata,
            }
            if item is None:
                self.outside[digest]["evidence_indices"].append(len(self.evidence))
            self.evidence.append(evidence)

    def finish(self):
        direct = sorted(
            {e["cand_id"] for e in self.evidence if e["cand_id"] is not None}
        )
        items, by_text = [], {}
        for cid in direct:
            row = self.population[cid]
            indices = [i for i, e in enumerate(self.evidence) if e["cand_id"] == cid]
            records = [self.evidence[i] for i in indices]
            timestamps = sorted(
                e["timestamp"] for e in records if e["timestamp"] is not None
            )
            items.append(
                {
                    "cand_id": cid,
                    "question_sha256": question_hash(row["question"]),
                    "canonical_question_reference": "pilot-v1/out/candidates.jsonl#"
                    + cid,
                    "exposure_categories": sorted({e["category"] for e in records}),
                    "evidence_indices": indices,
                    "earliest_known_exposure_stage": None,
                    "stage_chronology_note": "Evidence stages retained individually; no complete chronological ordering established.",
                    "earliest_supported_timestamp": timestamps[0]
                    if timestamps
                    else None,
                }
            )
            ref = by_text.setdefault(
                row["question"],
                {
                    "question": row["question"],
                    "question_sha256": question_hash(row["question"]),
                    "pilot_ids": [],
                    "evidence_indices": [],
                    "complete": True,
                },
            )
            ref["pilot_ids"].append(cid)
            ref["evidence_indices"].extend(indices)
        for digest, outside in sorted(self.outside.items()):
            ref = by_text.setdefault(
                outside["question"],
                {
                    "question": outside["question"],
                    "question_sha256": digest,
                    "pilot_ids": [],
                    "evidence_indices": [],
                    "complete": True,
                },
            )
            ref["evidence_indices"].extend(outside["evidence_indices"])
        return {
            "schema": "known_exposure_inventory_v2",
            "scope": "accepted_known_exposure_only",
            "unresolved": [],
            "pilot_items": items,
            "outside_items": list(self.outside.values()),
            "references": sorted(by_text.values(), key=lambda x: x["question_sha256"]),
            "evidence": self.evidence,
        }


def validate_inventory(inventory, population):
    require(
        inventory.get("schema") == "known_exposure_inventory_v2"
        and inventory.get("unresolved") == [],
        "inventory_unresolved_or_schema",
    )
    evidence = inventory["evidence"]
    require(
        all(
            e["category"] in CATEGORIES
            and e["completeness"]
            in {
                "authoritative_complete_record",
                "accepted_exact_recovery",
                "canonical_id_binding",
            }
            for e in evidence
        ),
        "inventory_incomplete_evidence",
    )
    canonical_rows = {r["cand_id"]: r for r in population}
    seen = set()
    for ref in inventory["references"]:
        require(
            ref["complete"] is True
            and isinstance(ref["question"], str)
            and normalize(ref["question"]),
            "inventory_incomplete_text",
        )
        require(
            question_hash(ref["question"]) == ref["question_sha256"]
            and ref["question"] not in seen,
            "inventory_hash_or_dedup",
        )
        seen.add(ref["question"])
        require(bool(ref["evidence_indices"]), "inventory_text_without_provenance")
        for index in ref["evidence_indices"]:
            require(
                type(index) is int and 0 <= index < len(evidence),
                "inventory_evidence_index",
            )
            require(
                evidence[index]["question_sha256"] == ref["question_sha256"],
                "inventory_evidence_binding",
            )
        for cid in ref["pilot_ids"]:
            require(
                cid in canonical_rows
                and canonical_rows[cid]["question"] == ref["question"],
                "inventory_identity_binding",
            )
    coverage = [i for ref in inventory["references"] for i in ref["evidence_indices"]]
    require(
        sorted(coverage) == list(range(len(evidence))),
        "inventory_provenance_lost_or_duplicated",
    )
    direct = {e["cand_id"] for e in evidence if e["cand_id"] is not None}
    require(
        direct == {item["cand_id"] for item in inventory["pilot_items"]},
        "inventory_direct_binding",
    )
    require(
        len(inventory["pilot_items"]) == len(direct), "inventory_duplicate_pilot_item"
    )
    for item in inventory["pilot_items"]:
        cid = item["cand_id"]
        require(
            cid in canonical_rows
            and item["question_sha256"]
            == question_hash(canonical_rows[cid]["question"]),
            "inventory_pilot_item_binding",
        )
        require(
            item["evidence_indices"]
            == [i for i, e in enumerate(evidence) if e["cand_id"] == cid],
            "inventory_pilot_provenance_binding",
        )
    outside_hashes = set()
    for item in inventory["outside_items"]:
        require(
            item["complete"] is True
            and isinstance(item["question"], str)
            and normalize(item["question"]),
            "inventory_incomplete_outside_text",
        )
        require(
            item["question_sha256"] == question_hash(item["question"])
            and item["question_sha256"] not in outside_hashes,
            "inventory_outside_hash_or_dedup",
        )
        outside_hashes.add(item["question_sha256"])
        require(
            item["evidence_indices"]
            == [
                i
                for i, e in enumerate(evidence)
                if e["cand_id"] is None
                and e["question_sha256"] == item["question_sha256"]
            ],
            "inventory_outside_provenance_binding",
        )
    require(
        outside_hashes
        == {e["question_sha256"] for e in evidence if e["cand_id"] is None},
        "inventory_outside_binding",
    )
    require(
        seen
        == {item["question"] for item in inventory["outside_items"]}
        | {canonical_rows[cid]["question"] for cid in direct},
        "inventory_reference_union",
    )
    require(
        sorted(cid for ref in inventory["references"] for cid in ref["pilot_ids"])
        == sorted(direct),
        "inventory_reference_pilot_binding",
    )
    for e in evidence:
        if e["cand_id"] is not None:
            require(
                e["cand_id"] in canonical_rows
                and question_hash(canonical_rows[e["cand_id"]]["question"])
                == e["question_sha256"],
                "inventory_evidence_identity",
            )
    return inventory


def load_inventory(path, expected_hash, population):
    # A caller must supply an independently bound digest; complete=True alone is no attestation.
    verify_file(path, expected_hash)
    return validate_inventory(read_json(path), population)


def exposure_ledger(population, inventory):
    validate_inventory(inventory, population)
    direct = {item["cand_id"] for item in inventory["pilot_items"]}
    exposed_groups = {
        (row["source"], row["context_group"])
        for row in population
        if row["cand_id"] in direct
    }
    references = [(ref, grams(ref["question"])) for ref in inventory["references"]]
    result = []
    for row in population:
        vector = grams(row["question"])
        scores = [(ref, cos(vector, other)) for ref, other in references]
        matches = [
            {
                "reference_sha256": ref["question_sha256"],
                "score": score,
                "score_hex": score.hex(),
                "pilot_ids": ref["pilot_ids"],
                "evidence_indices": ref["evidence_indices"],
            }
            for ref, score in scores
            if conflicts(score)
        ]
        maximum = max((score for _, score in scores), default=0.0)
        result.append(
            {
                "cand_id": row["cand_id"],
                "direct": row["cand_id"] in direct,
                "native_group": (row["source"], row["context_group"]) in exposed_groups,
                "near_duplicate": bool(matches),
                "similarity_matches": matches,
                "maximum_similarity": maximum,
                "maximum_similarity_hex": maximum.hex(),
                "comparisons": len(scores),
            }
        )
    return result
