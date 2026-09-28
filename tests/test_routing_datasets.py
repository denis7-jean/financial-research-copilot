"""Versioned routing-label datasets (approved 2026-09-28) and routing scores."""
import json
from collections import Counter
from pathlib import Path

import pytest

from eval import routing_datasets as rd
from eval.eval_queries import CASES_BY_ID, EVAL_CASES
from eval.llm_judge import dataset_fingerprint

BASELINE = Path(__file__).resolve().parents[1] / "eval/results/baselines/2026-09-phase0-baseline.json"


def _counts(cases):
    return Counter((c.status, c.expected_route) for c in cases)


def test_v1_reproduces_the_baseline_labels_exactly():
    """v1 is the historical labelling: read back from the archived baseline (read-only)."""
    rows = json.loads(BASELINE.read_text(encoding="utf-8"))["results"]
    v1 = rd.routing_dataset("v1")
    assert [(c.id, c.query, c.expected_route, c.status == "clear") for c in v1] == [
        (r["id"], r["query"], r["expected_route"], r["route_label_status"] == "clear") for r in rows
    ]
    assert _counts(v1) == {("clear", "qa"): 23, ("clear", "summarize"): 7,
                           ("excluded", "qa"): 3, ("excluded", "summarize"): 1}


def test_v2_has_31_clear_cases_one_policy_case_and_two_exclusions():
    v2 = rd.routing_dataset("v2")
    assert _counts(v2) == {("clear", "qa"): 24, ("clear", "summarize"): 7,
                           ("policy", "qa"): 1, ("excluded", "qa"): 2}
    by_id = {c.id: c for c in v2}
    assert (by_id["L13"].status, by_id["L13"].expected_route) == ("clear", "qa")
    assert (by_id["L19"].status, by_id["L19"].policy) == ("policy", rd.UNCLEAR_DEFAULTS_TO_QA)
    assert by_id["L17"].status == by_id["L20"].status == "excluded"


def test_v2_differs_from_v1_only_in_the_approved_cases():
    v1 = {c.id: c for c in rd.routing_dataset("v1")}
    v2 = {c.id: c for c in rd.routing_dataset("v2")}
    assert list(v1) == list(v2)
    changed = {i for i in v1 if (v1[i].status, v1[i].expected_route, v1[i].policy)
               != (v2[i].status, v2[i].expected_route, v2[i].policy)}
    assert changed == {"L13", "L19"}
    assert all(v1[i].query == v2[i].query for i in v1)


def test_the_harness_dataset_and_gate_population_are_unchanged():
    """v2 is routing-only: L13 stays summarize/needs_review in the harness and is not gated."""
    assert dataset_fingerprint(EVAL_CASES) == "734f6e1c9ad6da4b9bea84eed3a57fb1f385253eb73b30f3f87500b5d867a6e8"
    assert (CASES_BY_ID["L13"].expected_route, CASES_BY_ID["L13"].route_label_status) == ("summarize", "needs_review")
    assert sum(c.gated_for_retrieval for c in EVAL_CASES) == 19


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_frozen_versions_detect_drift(version, monkeypatch):
    assert rd.fingerprint(rd.routing_dataset(version)) == rd.PINNED_SHA256[version]
    monkeypatch.setitem(rd.PINNED_SHA256, version, "0" * 64)
    with pytest.raises(rd.DatasetDriftError, match="new version"):
        rd.routing_dataset(version)


@pytest.mark.parametrize("successes, n, low, high", [
    (31, 31, 0.8897, 1.0), (29, 31, 0.7928, 0.9821), (6, 7, 0.4869, 0.9743), (30, 30, 0.8865, 1.0),
])
def test_wilson_interval(successes, n, low, high):
    lo, hi = rd.wilson_interval(successes, n)
    assert lo == pytest.approx(low, abs=1e-4) and hi == pytest.approx(high, abs=1e-4)
    assert rd.wilson_interval(0, 0) is None


def test_score_routing_separates_accuracy_policy_and_exclusions():
    v2 = rd.routing_dataset("v2")
    decisions = {c.id: c.expected_route for c in v2}
    decisions.update(L13="summarize", L19="summarize", L17="summarize")
    score = rd.score_routing(decisions, v2)
    assert (score["strict_accuracy"]["passed"], score["strict_accuracy"]["n"]) == (30, 31)
    assert score["errors"] == ["L13"]
    assert (score["recall"]["qa"]["passed"], score["recall"]["qa"]["n"]) == (23, 24)
    assert (score["recall"]["summarize"]["passed"], score["recall"]["summarize"]["n"]) == (7, 7)
    assert score["confusion"]["qa->summarize"] == 1
    policy = score["policy_compliance"][rd.UNCLEAR_DEFAULTS_TO_QA]
    assert (policy["complied"], policy["n"]) == (0, 1)
    assert score["excluded_predictions"] == {"L17": "summarize", "L20": "qa"}


def test_missing_decisions_count_as_errors():
    v2 = rd.routing_dataset("v2")
    score = rd.score_routing({}, v2)
    assert score["strict_accuracy"]["passed"] == 0
    assert score["confusion"]["qa->missing"] == 24
