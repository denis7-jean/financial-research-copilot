"""Benchmark metrics (design v2 §3-§5, §10). Warm-up calls are excluded everywhere.

Accuracy views (repeated calls on the same questions are not independent samples):
- majority: each case's modal final decision over repetitions (a tie counts as wrong);
  n = 31, 95% Wilson interval;
- pooled: all decisions, 95% case-cluster bootstrap interval;
- per repetition: min / median / max.
Only final decisions enter the pre-registered criteria; raw-label accuracy, stability,
policy compliance, score diagnostics and the threshold sweep are report-only.

Latency intervals: calls are clustered by question and by repetition (time), so they
are not independent. Intervals use a two-way cluster ("pigeonhole") bootstrap that
resamples questions and repetitions and takes every cell of the resampled grid. The
Haiku-vs-candidate p95 difference is paired: both routers are evaluated on the same
resampled cells in every draw. Point estimates stay nearest-rank over all calls.

Validity: the report combines the runner's execution validity with per-router checks
(infrastructure errors above 1%, decision mismatches, harness errors). The follow-up
criteria can pass only for a valid benchmark.
"""
from collections import Counter
from statistics import median

import numpy as np

from eval.metrics import percentile
from eval.routing_datasets import UNCLEAR_DEFAULTS_TO_QA, score_routing, wilson_interval
from experiments.router_bench.config import (
    BOOTSTRAP_DRAWS,
    FALLBACK_ROUTE,
    INFRA_ERROR_RATE_LIMIT,
)

CRITERIA = {
    "strict_majority_min_correct": 29,  # of 31
    "strict_pooled_min_rate": 29 / 31,
    "summarize_recall_majority_min_correct": 6,  # of 7
    "infra_error_rate_max": INFRA_ERROR_RATE_LIMIT,
    "fallback_rate_max": 0.05,
    "p95_improvement_min_ms": 300.0,
}
SWEEP_THRESHOLDS = tuple(round(0.50 + 0.05 * i, 2) for i in range(10))


def _mode(labels: list) -> str | None:
    counts = Counter(labels).most_common()
    if not counts or (len(counts) > 1 and counts[0][1] == counts[1][1]):
        return None
    return counts[0][0]


def _cluster_bootstrap(correct: np.ndarray, totals: np.ndarray, seed: int) -> tuple[float, float] | None:
    if totals.sum() == 0:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(totals), size=(BOOTSTRAP_DRAWS, len(totals)))
    rates = correct[idx].sum(axis=1) / np.maximum(totals[idx].sum(axis=1), 1)
    return float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))


LATENCY_CI_METHOD = ("two-way cluster bootstrap over questions and repetitions (all cells of the resampled "
                     "grid), 95% percentile interval; the Haiku comparison is paired on the same resampled cells")


def latency_matrix(records: list[dict], case_ids: list[str], repetitions: list[int]) -> np.ndarray:
    """Latency per (question, repetition) cell; NaN where a router made no call."""
    rows = {cid: i for i, cid in enumerate(case_ids)}
    cols = {rep: j for j, rep in enumerate(repetitions)}
    matrix = np.full((len(case_ids), len(repetitions)), np.nan)
    for r in records:
        matrix[rows[r["case_id"]], cols[r["repetition"]]] = r["latency_ms"]
    return matrix


def cluster_indices(n_cases: int, n_reps: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    return (rng.integers(0, n_cases, size=(BOOTSTRAP_DRAWS, n_cases)),
            rng.integers(0, n_reps, size=(BOOTSTRAP_DRAWS, n_reps)))


def resampled_percentiles(matrix: np.ndarray, q: float, case_idx: np.ndarray, rep_idx: np.ndarray) -> np.ndarray:
    """The q-th percentile of every draw's resampled grid (NaN cells ignored)."""
    cells = matrix[case_idx[:, :, None], rep_idx[:, None, :]].reshape(len(case_idx), -1)
    with np.errstate(all="ignore"):
        return np.nanpercentile(cells, q, axis=1, method="inverted_cdf")


def _interval(values: np.ndarray) -> tuple[float, float] | None:
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return None
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def _cohen_kappa(a: list, b: list) -> float | None:
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(x == y for x, y in pairs) / n
    labels = {x for pair in pairs for x in pair}
    expected = sum((sum(x == lab for x, _ in pairs) / n) * (sum(y == lab for _, y in pairs) / n) for lab in labels)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def _router_metrics(records: list[dict], cases, seed: int) -> dict:
    clear = [c for c in cases if c.status == "clear"]
    by_case: dict[str, list[dict]] = {}
    for r in records:
        by_case.setdefault(r["case_id"], []).append(r)
    reps = sorted({r["repetition"] for r in records})
    n_calls = len(records)

    majority_final = {cid: _mode([r["final_label"] for r in rs]) for cid, rs in by_case.items()}
    majority_raw = {cid: _mode([r["raw_label"] for r in rs]) for cid, rs in by_case.items()}
    majority = score_routing({k: v for k, v in majority_final.items() if v}, cases)
    raw_majority = score_routing({k: v for k, v in majority_raw.items() if v}, cases)

    correct = np.array([sum(r["final_label"] == c.expected_route for r in by_case.get(c.id, [])) for c in clear])
    totals = np.array([len(by_case.get(c.id, [])) for c in clear])
    pooled_rate = float(correct.sum() / totals.sum()) if totals.sum() else None
    raw_correct = sum(r["raw_label"] == c.expected_route for c in clear for r in by_case.get(c.id, []))
    pooled_recall = {}
    for route in ("qa", "summarize"):
        members = [i for i, c in enumerate(clear) if c.expected_route == route]
        n = int(totals[members].sum())
        pooled_recall[route] = {"correct": int(correct[members].sum()), "n": n,
                                "rate": float(correct[members].sum() / n) if n else None}
    per_rep = []
    for rep in reps:
        decided = {r["case_id"]: r["final_label"] for r in records if r["repetition"] == rep}
        per_rep.append(sum(decided.get(c.id) == c.expected_route for c in clear))

    policy = {}
    for c in (c for c in cases if c.status == "policy"):
        rs = by_case.get(c.id, [])
        policy[c.id] = {
            "policy": c.policy, "required": c.expected_route, "n": len(rs),
            "complied_with_raw_label": sum(r["final_label"] == c.expected_route and r["raw_label"] == c.expected_route
                                           for r in rs),
            "complied_via_fallback": sum(r["final_label"] == c.expected_route and r["raw_label"] != c.expected_route
                                         for r in rs),
            "not_complied": sum(r["final_label"] != c.expected_route for r in rs),
        }
    exploratory = {c.id: dict(Counter(r["final_label"] for r in by_case.get(c.id, [])))
                   for c in cases if c.status == "excluded"}

    outcomes = Counter(r["outcome"] for r in records)
    fallbacks = [r for r in records if r["outcome"].startswith("fallback")]
    expected_by_id = {c.id: c.expected_route for c in clear}
    correct_by_fallback = sum(1 for r in fallbacks if expected_by_id.get(r["case_id"]) == FALLBACK_ROUTE)
    infra = sum(bool(r["infra_error"]) for r in records)

    unstable = {}
    for cid, rs in by_case.items():
        labels = [r["raw_label"] or "none" for r in rs]
        top = Counter(labels).most_common(1)[0][1]
        share = 1 - top / len(labels)
        if share > 0:
            unstable[cid] = round(share, 4)

    latencies = [r["latency_ms"] for r in records]
    latency = {"n": n_calls, "ci_method": LATENCY_CI_METHOD}
    for q in (50, 95, 99):
        latency[f"p{q}_ms"] = percentile(latencies, q) if n_calls else None
        latency[f"p{q}_ci95_ms"] = None  # filled in by compute(), on the shared question x repetition grid
    mismatches = [r for r in records if (r.get("extra") or {}).get("decision_mismatch")]

    scored = [(r["raw_score"], r["raw_label"] == expected_by_id[r["case_id"]]) for r in records
              if r["raw_score"] is not None and r["case_id"] in expected_by_id]
    diagnostics = None
    if scored:
        bins = {"[0.5,0.7)": (0.5, 0.7), "[0.7,0.9)": (0.7, 0.9), "[0.9,1.0]": (0.9, 1.01)}
        diagnostics = {
            "note": "report-only; far too few cases for any calibration claim",
            "brier_raw": float(np.mean([(s - float(ok)) ** 2 for s, ok in scored])),
            "reliability": {name: {"n": sum(lo <= s < hi for s, _ in scored),
                                   "accuracy": (float(np.mean([ok for s, ok in scored if lo <= s < hi]))
                                                if any(lo <= s < hi for s, _ in scored) else None)}
                            for name, (lo, hi) in bins.items()},
            "score_min": min(s for s, _ in scored), "score_max": max(s for s, _ in scored),
            "threshold_sweep_exploratory": {
                str(t): float(np.mean([((r["raw_label"] if r["raw_score"] is None or r["raw_score"] >= t
                                          else FALLBACK_ROUTE) if r["raw_label"] else FALLBACK_ROUTE)
                                        == expected_by_id[r["case_id"]]
                                        for r in records if r["case_id"] in expected_by_id]))
                for t in SWEEP_THRESHOLDS},
        }

    costs = [r["cost_usd"] or 0.0 for r in records]
    return {
        "calls": n_calls,
        "repetitions": len(reps),
        "strict_accuracy": {
            "majority": majority["strict_accuracy"],
            "pooled": {"correct": int(correct.sum()), "n": int(totals.sum()), "rate": pooled_rate,
                       "cluster_bootstrap_95": _cluster_bootstrap(correct, totals, seed)},
            "per_repetition": {"n_per_repetition": len(clear), "min": min(per_rep) if per_rep else None,
                               "median": median(per_rep) if per_rep else None,
                               "max": max(per_rep) if per_rep else None},
            "errors_majority": majority["errors"],
            "confusion_majority": majority["confusion"],
        },
        "recall": {"majority": majority["recall"], "pooled": pooled_recall},
        "raw_label_accuracy_report_only": {
            "majority": raw_majority["strict_accuracy"],
            "pooled": {"correct": int(raw_correct), "n": int(totals.sum()),
                       "rate": float(raw_correct / totals.sum()) if totals.sum() else None},
        },
        "policy_compliance_report_only": policy,
        "exploratory_predictions": exploratory,
        "outcomes": dict(outcomes),
        "fallback": {"rate": len(fallbacks) / n_calls if n_calls else None, "by_reason": {
            k: v for k, v in outcomes.items() if k.startswith("fallback")},
            "correct_by_fallback_on_clear_qa": correct_by_fallback},
        "infra_errors": {"count": infra, "rate": infra / n_calls if n_calls else None,
                         "invalid": bool(n_calls) and infra / n_calls > INFRA_ERROR_RATE_LIMIT},
        "stability_report_only": {"unstable_cases": unstable,
                                  "mean_disagreement": (sum(unstable.values()) / len(by_case)) if by_case else None},
        "latency": latency,
        "cost": {"usd": round(sum(costs), 6), "per_1000_decisions_usd": round(1000 * sum(costs) / n_calls, 6)
                 if n_calls else None,
                 "input_tokens": sum(r["input_tokens"] or 0 for r in records),
                 "output_tokens": sum(r["output_tokens"] or 0 for r in records),
                 "calls_charged_at_worst_case": sum(r["cost_basis"] == "worst_case_reservation" for r in records)},
        "score_diagnostics_report_only": diagnostics,
        "decision_mismatches": {"count": len(mismatches), "case_ids": sorted({r["case_id"] for r in mismatches})},
        "harness_errors": outcomes.get("fallback_harness_error", 0),
        "_majority_final": majority_final,
    }


def _validity(per_router: dict, execution: dict | None) -> dict:
    reasons = list(execution["invalid_reasons"]) if execution else []
    metric_reasons = []
    for name, m in per_router.items():
        if m["infra_errors"]["invalid"]:
            metric_reasons.append(f"{name}: infrastructure error rate {m['infra_errors']['rate']:.1%} exceeds "
                                  f"{INFRA_ERROR_RATE_LIMIT:.0%}")
        if m["decision_mismatches"]["count"]:
            metric_reasons.append(f"{name}: {m['decision_mismatches']['count']} decision mismatch(es) between the "
                                  "benchmark's final-decision rule and RouterAgent's own decision")
        if m["harness_errors"]:
            metric_reasons.append(f"{name}: {m['harness_errors']} harness error(s)")
    execution_valid = execution["valid"] if execution else None
    return {
        "benchmark_valid": (execution_valid is not False) and not metric_reasons,
        "execution_valid": execution_valid,
        "reasons": reasons + metric_reasons,
        "note": "criteria are evaluated only for a valid benchmark",
    }


def compute(records: list[dict], cases, routers, *, seed: int = 0, execution: dict | None = None) -> dict:
    measured = [r for r in records if not r["warmup"]]
    by_router = {name: [r for r in measured if r["router"] == name] for name in routers}
    per_router = {name: _router_metrics(by_router[name], cases, seed) for name in routers}

    case_ids = sorted({r["case_id"] for r in measured})
    repetitions = sorted({r["repetition"] for r in measured})
    matrices = {name: latency_matrix(by_router[name], case_ids, repetitions) for name in routers}
    if case_ids and repetitions:
        case_idx, rep_idx = cluster_indices(len(case_ids), len(repetitions), seed + 101)
        draws = {name: {q: resampled_percentiles(matrices[name], q, case_idx, rep_idx) for q in (50, 95, 99)}
                 for name in routers if by_router[name]}
        for name, per_q in draws.items():
            for q, values in per_q.items():
                per_router[name]["latency"][f"p{q}_ci95_ms"] = _interval(values)
    else:
        draws = {}
    strict_ids = [c.id for c in cases if c.status == "clear"]
    all_ids = [c.id for c in cases]
    agreement = {}
    names = list(per_router)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ma, mb = per_router[a]["_majority_final"], per_router[b]["_majority_final"]
            agreement[f"{a}~{b}"] = {
                "kappa_strict": _cohen_kappa([ma.get(i) for i in strict_ids], [mb.get(i) for i in strict_ids]),
                "kappa_all": _cohen_kappa([ma.get(i) for i in all_ids], [mb.get(i) for i in all_ids]),
            }
    criteria = {}
    haiku = per_router.get("haiku")
    for name, m in per_router.items():
        checks = {
            "strict_majority": (m["strict_accuracy"]["majority"]["passed"] or 0) >= CRITERIA["strict_majority_min_correct"],
            "strict_pooled": (m["strict_accuracy"]["pooled"]["rate"] or 0) >= CRITERIA["strict_pooled_min_rate"] - 1e-12,
            "summarize_recall_majority": (m["recall"]["majority"]["summarize"]["passed"] or 0)
            >= CRITERIA["summarize_recall_majority_min_correct"],
            "infra_error_rate": m["infra_errors"]["rate"] is not None
            and m["infra_errors"]["rate"] <= CRITERIA["infra_error_rate_max"],
            "fallback_rate": m["fallback"]["rate"] is not None and m["fallback"]["rate"] <= CRITERIA["fallback_rate_max"],
        }
        p95 = None
        if haiku is not None and name != "haiku" and "haiku" in draws and name in draws:
            improvement = haiku["latency"]["p95_ms"] - m["latency"]["p95_ms"]
            ci = _interval(draws["haiku"][95] - draws[name][95])  # paired: same resampled cells
            p95 = {"improvement_ms": improvement, "ci95_ms": ci, "method": LATENCY_CI_METHOD,
                   "passed": improvement >= CRITERIA["p95_improvement_min_ms"] and ci is not None and ci[0] > 0}
            checks["p95_latency_vs_haiku"] = p95["passed"]
        criteria[name] = {"checks": checks, "p95_vs_haiku": p95}
    validity = _validity(per_router, execution)
    for name in criteria:
        criteria[name]["meets_follow_up_criteria"] = (
            None if name == "haiku" else all(criteria[name]["checks"].values()) and validity["benchmark_valid"])
    for m in per_router.values():
        m.pop("_majority_final")
    return {"per_router": per_router, "agreement": agreement, "criteria": criteria, "criteria_definition": CRITERIA,
            "validity": validity,
            "wilson_reference": {f"{k}/31": wilson_interval(k, 31) for k in (31, 30, 29, 28)},
            "policy": UNCLEAR_DEFAULTS_TO_QA}
