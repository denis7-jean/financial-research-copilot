"""Real input regression compares aggregates only; assertion locals never include a ledger."""

from pathlib import Path
from experiments.reviewer_protocol_v2.audit import compute
from experiments.reviewer_protocol_v2.common import check_runtime
from experiments.reviewer_protocol_v2.integrity import verify_historical
from experiments.reviewer_protocol_v2.known_inventory import (
    load_population,
    reconstruct,
)
from experiments.reviewer_protocol_v2.similarity import verify_isolation


def aggregate_only():
    root = Path(__file__).resolve().parents[2]
    before = verify_historical(root)
    check_runtime()
    verify_isolation(root / "heldout-external/pilot-v1/select_pilot.py")
    population = load_population(root)
    inventory = reconstruct(root, population)
    _, summary = compute(population, inventory)
    assert verify_historical(root) == before
    return summary


def test_accepted_population_regression():
    summary = aggregate_only()
    assert [s["original"] for s in summary["strata"]] == [13, 13, 14, 50, 10, 4]
    assert [s["final_screen_pass"] for s in summary["strata"]] == [10, 11, 10, 46, 9, 3]
    assert summary["final_unexposed_screen_pass"] == 89
    assert summary["dispositions"] == {
        "SCREEN_PASS": 104,
        "DEPENDENCE_EXCLUDED": 0,
        "DIAGNOSTIC_ONLY": 0,
        "INPUT_INVALID": 0,
    }
    assert summary["rule_counts"] == {
        "E01": 1,
        **{"E0" + str(k): 0 for k in range(2, 8)},
    }
    assert summary["strata"][0]["rules"]["E01"] == 1
    assert summary["exposure_counts"] == {
        "direct": 15,
        "native_group": 15,
        "near_duplicate": 15,
    }
    assert set(summary["exposure_pair_overlaps"].values()) == {15}
    assert summary["exposure_membership_counts"] == {"0": 89, "1": 0, "2": 0, "3": 15}
    assert summary["outside_reference_threshold_matches"] == 0
    assert summary["inventory"]["evidence_records"] == 1480
    assert summary["inventory"]["outside_complete"] == 48
    assert summary["inventory"]["complete_computational_texts"] == 63
    assert summary["inventory"]["unresolved"] == 0
    assert summary["constraints"]["retained_pair_comparisons"] == 3916
    assert summary["constraints"]["native_group_conflicts"] == 1
    assert summary["constraints"]["native_conflicts_by_strata"] == {
        "finlfqa/interp|finlfqa/mixed": 1
    }
    assert summary["constraints"]["similarity_conflicts"] == 0
    assert summary["constraints"]["simultaneous_quota_feasible"]
    assert [s["quota"] for s in summary["constraints"]["strata"]] == [4, 4, 4, 6, 4, 2]
