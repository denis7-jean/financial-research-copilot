"""Approved descriptive agreement definitions; no new gates or correctness claims."""

from collections import Counter
from itertools import combinations
from experiments.reviewer_protocol_v2.common import require
from experiments.reviewer_protocol_v2.validation import LABELS, validate_text


def ratio(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def cohen(pairs):
    n = len(pairs)
    if not n:
        return {"n": 0, "value": None, "reason": "no_shared_valid_labels"}
    left, right = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    agreement = sum(x == y for x, y in pairs) / n
    expected = sum(left[label] * right[label] for label in LABELS) / (n * n)
    return {
        "n": n,
        "value": (agreement - expected) / (1 - expected) if expected != 1 else None,
        "reason": "degenerate_marginals" if expected == 1 else None,
    }


def fleiss(panels):
    n = len(panels)
    require(all(len(panel) == 3 for panel in panels), "fleiss_requires_three_raters")
    if not n:
        return {"n": 0, "value": None, "reason": "no_complete_panels"}
    counts = [Counter(panel) for panel in panels]
    observed = (
        sum(
            sum(value * (value - 1) for value in count.values()) / 6 for count in counts
        )
        / n
    )
    totals = Counter(label for panel in panels for label in panel)
    expected = sum((totals[label] / (3 * n)) ** 2 for label in LABELS)
    return {
        "n": n,
        "value": (observed - expected) / (1 - expected) if expected != 1 else None,
        "reason": "degenerate_marginals" if expected == 1 else None,
    }


def analyze_external(planned_ids, reviewers, answer_texts, owner_labels):
    """Already-extracted JSON texts only; service-envelope admission remains blocked.

    Missing or invalid texts remain in planned denominators. Owner None is abstention.
    Item classes/keys, provider envelope and any future gates need separately bound inputs.
    """
    require(
        len(reviewers) == 3 and len(set(reviewers)) == 3,
        "analysis_requires_three_reviewers",
    )
    require(len(set(planned_ids)) == len(planned_ids), "duplicate_planned_item")
    require(
        all(
            key in planned_ids and value in (*LABELS, None)
            for key, value in owner_labels.items()
        ),
        "invalid_owner_label",
    )
    require(
        all(key[0] in planned_ids and key[1] in reviewers for key in answer_texts),
        "unplanned_answer",
    )
    votes = {
        (item, reviewer): validate_text(answer_texts.get((item, reviewer)))
        for item in planned_ids
        for reviewer in reviewers
    }

    def label(item, reviewer):
        vote = votes[(item, reviewer)]
        return vote["vote"]["label"] if vote["valid"] else None

    complete = [
        item
        for item in planned_ids
        if all(label(item, reviewer) is not None for reviewer in reviewers)
    ]
    unanimous = sum(
        len({label(item, reviewer) for reviewer in reviewers}) == 1 for item in complete
    )
    majorities = {}
    for item in complete:
        counts = Counter(label(item, reviewer) for reviewer in reviewers)
        winner, count = counts.most_common(1)[0]
        if count >= 2:
            majorities[item] = winner
    owner_present = {item for item in planned_ids if owner_labels.get(item) is not None}
    aligned = sum(
        majorities[item] == owner_labels[item]
        for item in majorities
        if item in owner_present
    )
    result = {
        "planned": len(planned_ids),
        "complete_coverage": ratio(len(complete), len(planned_ids)),
        "unconditional_unanimity": ratio(unanimous, len(planned_ids)),
        "conditional_unanimity": ratio(unanimous, len(complete)),
        "majority_availability": ratio(len(majorities), len(planned_ids)),
        "owner_label_availability": ratio(len(owner_present), len(planned_ids)),
        "owner_abstentions_or_missing": len(planned_ids) - len(owner_present),
        "owner_majority_planned_alignment": ratio(aligned, len(planned_ids)),
        "owner_majority_conditional_alignment": ratio(
            aligned, len(set(majorities) & owner_present)
        ),
        "fleiss_kappa": fleiss(
            [[label(item, reviewer) for reviewer in reviewers] for item in complete]
        ),
        "pairwise": {},
        "reviewers": {},
        "status": "descriptive_only_not_a_trial_acceptance_report",
    }
    for left, right in combinations(reviewers, 2):
        pairs = [
            (label(item, left), label(item, right))
            for item in planned_ids
            if label(item, left) is not None and label(item, right) is not None
        ]
        result["pairwise"][left + "&" + right] = {
            "agreement": ratio(sum(x == y for x, y in pairs), len(pairs)),
            "coverage": ratio(len(pairs), len(planned_ids)),
            "cohen_kappa": cohen(pairs),
        }
    for reviewer in reviewers:
        valid = [item for item in planned_ids if label(item, reviewer) is not None]
        distribution = Counter(label(item, reviewer) for item in valid)
        owner_pairs = [
            (label(item, reviewer), owner_labels[item])
            for item in valid
            if item in owner_present
        ]
        matched = sum(x == y for x, y in owner_pairs)
        result["reviewers"][reviewer] = {
            "validity": ratio(len(valid), len(planned_ids)),
            "invalid_or_unattempted": len(planned_ids) - len(valid),
            "label_distribution": dict(sorted(distribution.items())),
            "certainty_distribution": dict(
                sorted(
                    Counter(
                        votes[(item, reviewer)]["vote"]["certainty"] for item in valid
                    ).items()
                )
            ),
            "unsure": ratio(
                sum(
                    votes[(item, reviewer)]["vote"]["certainty"] == "unsure"
                    for item in valid
                ),
                len(valid),
            ),
            "owner_agreement_available": ratio(matched, len(owner_pairs)),
            "owner_agreement_planned": ratio(matched, len(planned_ids)),
            "owner_cohen_kappa": cohen(owner_pairs),
        }
    return result


def analyze_packets(
    item_classes, reviewers, answer_texts, owner_labels, anchor_key, external_sources
):
    """Separate planned packet classes, reviewed anchor keys and source-family diagnostics.

    This pure function accepts already validated local inputs; it neither builds a packet
    nor admits service responses. It makes no GO/NO-GO decision.
    """
    require(
        all(
            value in ("external", "anchor", "diagnostic")
            for value in item_classes.values()
        ),
        "invalid_item_class",
    )
    require(
        all(
            item in item_classes and reviewer in reviewers
            for item, reviewer in answer_texts
        ),
        "unplanned_answer",
    )
    external = [item for item, kind in item_classes.items() if kind == "external"]
    anchors = {item for item, kind in item_classes.items() if kind == "anchor"}
    require(set(anchor_key) == anchors, "anchor_key_binding")
    require(
        set(external_sources) == set(external)
        and all(
            source in ("tatqa", "finqa", "finlfqa")
            for source in external_sources.values()
        ),
        "external_source_binding",
    )
    for key in anchor_key.values():
        require(
            key.get("label") in LABELS
            and key.get("components")
            == (["qa", "summarize"] if key["label"] == "multi_intent" else []),
            "anchor_key_contract",
        )
    external_answers = {
        key: value for key, value in answer_texts.items() if key[0] in external
    }
    result = {
        "external": analyze_external(
            external, reviewers, external_answers, owner_labels
        ),
        "packet_classes": {},
    }
    family = [item for item in external if external_sources[item] == "finlfqa"]
    validations = {
        (item, reviewer): validate_text(answer_texts.get((item, reviewer)))
        for item in item_classes
        for reviewer in reviewers
    }
    unanimous_family = sum(
        all(validations[(item, reviewer)]["valid"] for reviewer in reviewers)
        and len(
            {validations[(item, reviewer)]["vote"]["label"] for reviewer in reviewers}
        )
        == 1
        for item in family
    )
    result["external"]["finlfqa_unconditional_unanimity"] = ratio(
        unanimous_family, len(family)
    )
    for kind in ("external", "anchor", "diagnostic"):
        ids = [item for item, value in item_classes.items() if value == kind]
        per_reviewer = {}
        for reviewer in reviewers:
            valid = [item for item in ids if validations[(item, reviewer)]["valid"]]
            missing = sum((item, reviewer) not in answer_texts for item in ids)
            stats = {
                "validity": ratio(len(valid), len(ids)),
                "not_attempted": missing,
                "invalid_attempted": len(ids) - len(valid) - missing,
                "failure_codes": dict(
                    sorted(
                        Counter(
                            validations[(item, reviewer)]["primary"]
                            for item in ids
                            if not validations[(item, reviewer)]["valid"]
                            and (item, reviewer) in answer_texts
                        ).items()
                    )
                ),
                "labels": dict(
                    sorted(
                        Counter(
                            validations[(item, reviewer)]["vote"]["label"]
                            for item in valid
                        ).items()
                    )
                ),
                "certainty": dict(
                    sorted(
                        Counter(
                            validations[(item, reviewer)]["vote"]["certainty"]
                            for item in valid
                        ).items()
                    )
                ),
                "unsure": ratio(
                    sum(
                        validations[(item, reviewer)]["vote"]["certainty"] == "unsure"
                        for item in valid
                    ),
                    len(valid),
                ),
            }
            if kind == "anchor":
                correct = {
                    item
                    for item in valid
                    if all(
                        validations[(item, reviewer)]["vote"][field]
                        == anchor_key[item][field]
                        for field in ("label", "components")
                    )
                }
                stats["correctness"] = ratio(len(correct), len(ids))
                stats["by_expected_label"] = {
                    label: ratio(
                        sum(
                            item in correct
                            for item in ids
                            if anchor_key[item]["label"] == label
                        ),
                        sum(anchor_key[item]["label"] == label for item in ids),
                    )
                    for label in LABELS
                }
            per_reviewer[reviewer] = stats
        result["packet_classes"][kind] = {
            "planned": len(ids),
            "reviewers": per_reviewer,
        }
    return result
