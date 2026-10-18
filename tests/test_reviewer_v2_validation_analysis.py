import json
import pytest
from experiments.reviewer_protocol_v2.analysis import (
    analyze_external,
    analyze_packets,
    cohen,
    fleiss,
)
from experiments.reviewer_protocol_v2.common import ProtocolError
from experiments.reviewer_protocol_v2.validation import (
    validate_service_response,
    validate_text,
)

BASE = {
    "label": "qa",
    "components": [],
    "certainty": "sure",
    "rationale": "A factual task.",
}


@pytest.mark.parametrize(
    "text,code",
    [
        ('{{"label":"qa"}', "F_JSON"),
        ('{"label":"qa","label":"qa"}', "F_DUP_KEY"),
        ("```json\n{}\n```", "F_JSON"),
        ("[]", "F_JSON"),
        ("{}", "F_KEYS"),
        (json.dumps(BASE | {"label": 1}), "F_TYPE"),
        (json.dumps(BASE | {"certainty": "certain"}), "F_ENUM"),
        (
            json.dumps(BASE | {"label": "multi_intent", "components": ["qa", "qa"]}),
            "F_COMPONENTS",
        ),
        (json.dumps(BASE | {"rationale": "line\nline"}), "F_RATIONALE"),
        (json.dumps(BASE | {"rationale": "x " * 26}), "F_RATIONALE"),
        (json.dumps(BASE | {"rationale": "x" * 301}), "F_RATIONALE"),
        (json.dumps(BASE | {"rationale": " "}), "F_RATIONALE"),
        (None, "F_NO_TEXT"),
    ],
)
def test_strict_failures_no_repair(text, code):
    result = validate_text(text)
    assert not result["valid"] and result["primary"] == code and result["vote"] is None


def test_valid_contract_and_all_findings():
    assert validate_text(" \n" + json.dumps(BASE) + "\n ")["valid"]
    assert validate_text(
        json.dumps(BASE | {"label": "multi_intent", "components": ["qa", "summarize"]})
    )["valid"]
    result = validate_text(
        json.dumps(
            BASE
            | {"extra": 1, "certainty": 1, "components": ["qa", "qa"], "rationale": ""}
        )
    )
    assert result["findings"] == ["F_KEYS", "F_TYPE", "F_COMPONENTS", "F_RATIONALE"]


def test_service_envelope_stays_blocked():
    with pytest.raises(ProtocolError, match="approved_stop"):
        validate_service_response({})


def test_missing_votes_owner_abstention_and_denominators():
    ids, reviewers = ["synthetic-a", "synthetic-b", "synthetic-c"], ["R1", "R2", "R3"]
    texts = {
        (item, reviewer): json.dumps(BASE) for item in ids for reviewer in reviewers
    }
    texts.pop((ids[1], "R3"))
    texts[(ids[2], "R2")] = "{{"
    report = analyze_external(
        ids, reviewers, texts, {ids[0]: "qa", ids[1]: None, ids[2]: "qa"}
    )
    assert report["complete_coverage"]["numerator"] == 1
    assert report["unconditional_unanimity"] == {
        "numerator": 1,
        "denominator": 3,
        "value": 1 / 3,
    }
    assert report["conditional_unanimity"]["denominator"] == 1
    assert report["owner_majority_conditional_alignment"]["denominator"] == 1
    assert report["pairwise"]["R1&R2"]["cohen_kappa"]["n"] == 2
    assert report["reviewers"]["R1"]["owner_cohen_kappa"]["n"] == 2
    assert report["reviewers"]["R3"]["validity"]["denominator"] == 3
    assert report["fleiss_kappa"]["n"] == 1
    assert report["fleiss_kappa"]["reason"] == "degenerate_marginals"


def test_kappa_known_synthetic_example_and_undefined_populations():
    assert (
        cohen(
            [
                ("qa", "qa"),
                ("qa", "summarize"),
                ("summarize", "summarize"),
                ("summarize", "qa"),
            ]
        )["value"]
        == 0
    )
    assert cohen([])["value"] is None
    assert fleiss([])["value"] is None
    assert (
        fleiss([["qa", "qa", "qa"], ["summarize", "summarize", "summarize"]])["value"]
        == 1
    )


def test_anchors_and_diagnostics_do_not_enter_external_agreement():
    classes = {
        "synthetic-external": "external",
        "synthetic-anchor": "anchor",
        "synthetic-diagnostic": "diagnostic",
    }
    reviewers = ["R1", "R2", "R3"]
    texts = {
        (item, reviewer): json.dumps(BASE) for item in classes for reviewer in reviewers
    }
    texts[("synthetic-anchor", "R1")] = "{{"
    texts.pop(("synthetic-diagnostic", "R2"))
    result = analyze_packets(
        classes,
        reviewers,
        texts,
        {"synthetic-external": "qa"},
        {"synthetic-anchor": {"label": "qa", "components": []}},
        {"synthetic-external": "finlfqa"},
    )
    assert result["external"]["complete_coverage"]["denominator"] == 1
    assert result["external"]["fleiss_kappa"]["n"] == 1
    assert result["external"]["finlfqa_unconditional_unanimity"]["numerator"] == 1
    assert (
        result["packet_classes"]["anchor"]["reviewers"]["R1"]["correctness"][
            "numerator"
        ]
        == 0
    )
    assert (
        result["packet_classes"]["diagnostic"]["reviewers"]["R2"]["not_attempted"] == 1
    )
