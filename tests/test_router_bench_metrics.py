"""Latency intervals (clustered, paired) and the combined validity verdict. Offline, synthetic data."""
import numpy as np
import pytest

from eval.routing_datasets import routing_dataset
from experiments.router_bench import metrics as bench_metrics
from experiments.router_bench.config import BOOTSTRAP_DRAWS

V2 = routing_dataset("v2")
REPS = 10


def _records(router, latency_of, extra_of=lambda cid, rep: {}, infra_of=lambda cid, rep: False):
    return [{"router": router, "case_id": c.id, "repetition": rep, "warmup": False, "raw_label": c.expected_route,
             "raw_score": None, "final_label": c.expected_route, "outcome": "model", "latency_ms": latency_of(i, rep),
             "infra_error": infra_of(c.id, rep), "input_tokens": 1, "output_tokens": 1, "cost_usd": 0.0,
             "cost_basis": "usage", "extra": extra_of(c.id, rep)}
            for rep in range(1, REPS + 1) for i, c in enumerate(V2)]


def _naive_call_bootstrap(latencies, q, seed=5):
    """The pre-fix method: resample calls as if independent (kept here only for comparison)."""
    rng = np.random.default_rng(seed)
    samples = np.asarray(latencies, dtype=float)
    stats = np.percentile(samples[rng.integers(0, len(samples), size=(BOOTSTRAP_DRAWS, len(samples)))], q, axis=1,
                          method="inverted_cdf")
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def test_clustered_latency_intervals_are_wider_than_the_naive_per_call_bootstrap():
    # Four questions are consistently slow: calls on the same question are strongly correlated.
    def latency(i, rep):
        return (2_000.0 if i < 4 else 300.0) + 7.0 * ((i * 13 + rep * 7) % 11)

    records = _records("jev", latency)
    m = bench_metrics.compute(records, V2, ("jev",), seed=3)["per_router"]["jev"]["latency"]
    clustered = m["p95_ci95_ms"]
    naive = _naive_call_bootstrap([r["latency_ms"] for r in records], 95)
    assert m["ci_method"] == bench_metrics.LATENCY_CI_METHOD
    assert (clustered[1] - clustered[0]) > 2 * (naive[1] - naive[0])


def test_the_haiku_comparison_is_paired_on_the_same_resampled_cells():
    def base(i, rep):
        return 200.0 + 900.0 * (i % 5) + 30.0 * rep  # large differences between questions and over time

    haiku = _records("haiku", lambda i, rep: base(i, rep) + 400.0)
    jev = _records("jev", base)
    p95 = bench_metrics.compute(haiku + jev, V2, ("haiku", "jev"), seed=3)["criteria"]["jev"]["p95_vs_haiku"]
    assert p95["improvement_ms"] == pytest.approx(400.0)
    assert p95["ci95_ms"] == pytest.approx((400.0, 400.0))  # an unpaired bootstrap would be very wide here
    assert p95["passed"] is True


def test_decision_mismatches_are_visible_and_invalidate_the_benchmark():
    haiku = _records("haiku", lambda i, rep: 900.0,
                     extra_of=lambda cid, rep: {"decision_mismatch": "summarize"} if (cid, rep) == ("L05", 3) else {})
    jev = _records("jev", lambda i, rep: 100.0)
    m = bench_metrics.compute(haiku + jev, V2, ("haiku", "jev"), seed=1)
    assert m["per_router"]["haiku"]["decision_mismatches"] == {"count": 1, "case_ids": ["L05"]}
    assert m["validity"]["benchmark_valid"] is False
    assert any("decision mismatch" in r for r in m["validity"]["reasons"])
    assert m["criteria"]["jev"]["meets_follow_up_criteria"] is False  # every check passes, but the run is invalid
    assert all(m["criteria"]["jev"]["checks"].values())


def test_execution_and_metric_validity_are_combined():
    jev = _records("jev", lambda i, rep: 100.0, infra_of=lambda cid, rep: (cid, rep) in {("L01", 1), ("L02", 2),
                                                                                           ("L03", 3), ("L04", 4)})
    execution = {"valid": True, "invalid_reasons": []}
    m = bench_metrics.compute(jev, V2, ("jev",), seed=1, execution=execution)
    assert m["validity"]["execution_valid"] is True
    assert m["validity"]["benchmark_valid"] is False  # 4/340 = 1.2% infrastructure errors
    assert any("infrastructure error rate 1.2%" in r for r in m["validity"]["reasons"])
    stopped = bench_metrics.compute(_records("jev", lambda i, rep: 100.0), V2, ("jev",), seed=1,
                                    execution={"valid": False, "invalid_reasons": ["jev stopped: 3 consecutive"]})
    assert stopped["validity"]["benchmark_valid"] is False and stopped["validity"]["reasons"] == ["jev stopped: 3 consecutive"]


def test_a_clean_benchmark_is_valid():
    m = bench_metrics.compute(_records("jev", lambda i, rep: 100.0), V2, ("jev",), seed=1,
                              execution={"valid": True, "invalid_reasons": []})
    assert m["validity"] == {"benchmark_valid": True, "execution_valid": True, "reasons": [],
                             "note": "criteria are evaluated only for a valid benchmark"}


def test_accuracy_methodology_is_unchanged():
    m = bench_metrics.compute(_records("jev", lambda i, rep: 100.0), V2, ("jev",), seed=1)["per_router"]["jev"]
    majority = m["strict_accuracy"]["majority"]
    assert (majority["passed"], majority["n"]) == (31, 31)
    assert majority["wilson_95"][0] == pytest.approx(0.8897, abs=1e-4)
    assert (m["strict_accuracy"]["pooled"]["correct"], m["strict_accuracy"]["pooled"]["n"]) == (310, 310)
