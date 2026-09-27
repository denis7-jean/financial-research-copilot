"""Pure evaluation metrics: no AWS, no I/O. Everything here is unit-tested.

Gate populations are fixed by dataset labels (eval_queries.EvalCase), never by
what the router did at run time. A case in a gated population that produced no
judgeable output (misrouted, errored, judge failure) counts as a FAILURE; it is
never dropped from the denominator.
"""
import math
import os
from dataclasses import asdict, dataclass

# Source file name fragment -> company ticker. The file named "mastercard..."
# contains Visa Inc.'s 10-K (see eval_queries module docstring), so it maps to V.
SOURCE_COMPANY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("jpmorgan", "JPM"),
    ("goldman", "GS"),
    ("bank-of-america", "BAC"),
    ("blackrock", "BLK"),
    ("mastercard", "V"),
)

BOUNDARY_LEGACY_IDS = frozenset({"L17", "L18", "L19", "L20"})

# Assumed on-demand prices, USD per million tokens (input, output). These are
# ESTIMATES for budgeting: Anthropic list prices for Claude and the published
# Titan V2 rate. Bedrock geographic (us.*) inference profiles may cost ~10% more;
# that premium was not verified. Real spend must come from AWS billing.
PRICES_PER_MTOK: tuple[tuple[str, float, float], ...] = (
    ("claude-haiku-4-5", 1.00, 5.00),
    ("claude-sonnet-4-6", 3.00, 15.00),
    ("titan-embed-text-v2", 0.02, 0.00),
)


@dataclass(frozen=True)
class Gate:
    metric: str
    threshold: float
    enforced: bool
    population: str


GATED_QA_POPULATION = "cases with expected_route=qa, expected_behavior=answer, clear route label"

# Single source of truth for thresholds, used by the harness and by CI.
# Enforced thresholds match the pre-Phase-0 CI gate (0.80). Report-only
# thresholds are proposals pending a measured baseline; they do not fail CI.
GATES: tuple[Gate, ...] = (
    Gate("context_relevance_pass_rate", 0.80, True, GATED_QA_POPULATION),
    Gate("faithfulness_pass_rate", 0.80, True, GATED_QA_POPULATION),
    Gate("routing_accuracy_clear", 0.90, False, "cases with a clear route label"),
    Gate("answer_correctness_pass_rate", 0.80, False, "cases with a reference answer"),
    Gate("abstention_appropriate_rate", 0.80, False, "cases with expected_behavior answer or abstain"),
    Gate("summary_grounding_pass_rate", 0.80, False, "cases answered by the summarize path"),
)


def company_for_source(source: str) -> str:
    name = os.path.basename(source or "").lower()
    for fragment, ticker in SOURCE_COMPANY_PATTERNS:
        if fragment in name:
            return ticker
    return "UNKNOWN"


def company_precision(sources: list[str], expected: tuple[str, ...] | list[str]) -> float | None:
    """Share of retrieved chunks that come from an expected company's filing."""
    if not sources or not expected:
        return None
    companies = [company_for_source(s) for s in sources]
    return sum(1 for c in companies if c in expected) / len(companies)


def is_contaminated(sources: list[str], expected: tuple[str, ...] | list[str]) -> bool | None:
    """True if any retrieved chunk comes from a company the question is not about."""
    if not sources or not expected:
        return None
    return any(company_for_source(s) not in expected for s in sources)


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile. With small n, P95 is effectively the max."""
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return None
    rank = max(1, math.ceil(pct / 100 * len(clean)))
    return clean[rank - 1]


def pass_rate(flags: list[bool | None]) -> dict:
    """Pass rate where None (not judged) counts as a failure, not an exclusion."""
    n = len(flags)
    passed = sum(1 for f in flags if f is True)
    return {"pass_rate": (passed / n) if n else None, "passed": passed, "n": n}


def price_for(model_id: str) -> tuple[float, float] | None:
    model_id = (model_id or "").lower()
    for fragment, price_in, price_out in PRICES_PER_MTOK:
        if fragment in model_id:
            return price_in, price_out
    return None


def estimate_cost_usd(model_calls: list[dict]) -> dict:
    total = 0.0
    unpriced = 0
    for call in model_calls:
        price = price_for(call.get("model_id", ""))
        if price is None:
            unpriced += 1
            continue
        total += (call.get("input_tokens") or 0) * price[0] / 1e6
        total += (call.get("output_tokens") or 0) * price[1] / 1e6
    return {"usd": round(total, 6), "unpriced_calls": unpriced}


def evaluate_gates(values: dict[str, float | None], gates: tuple[Gate, ...] = GATES) -> tuple[list[dict], bool]:
    """Apply gates. A missing value (empty population) fails an enforced gate."""
    results = []
    for gate in gates:
        value = values.get(gate.metric)
        passed = value is not None and value >= gate.threshold
        results.append({**asdict(gate), "value": value, "passed": passed})
    overall = all(r["passed"] for r in results if r["enforced"])
    return results, overall


def _score_or_zero(judgement: dict | None) -> float:
    if not judgement or not isinstance(judgement.get("score"), (int, float)):
        return 0.0
    return float(judgement["score"])


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _latency_summary(rows: list[dict]) -> dict:
    totals = [r["latency"]["total_ms"] for r in rows]
    stage_names = sorted({name for r in rows for name in r["latency"]["stages_ms"]})
    by_path = {}
    for path in ("qa", "summarize"):
        subset = [r["latency"]["total_ms"] for r in rows if r["agent_used"] == path]
        by_path[path] = {"p50": percentile(subset, 50), "p95": percentile(subset, 95), "n": len(subset)}
    return {
        "note": "Measured in-process by the harness (orchestrator.process); excludes Lambda, "
                "network to the Function URL and response serialization.",
        "total_ms": {"p50": percentile(totals, 50), "p95": percentile(totals, 95), "n": len(totals)},
        "by_path": by_path,
        "stages_ms": {
            name: {
                "p50": percentile([r["latency"]["stages_ms"][name] for r in rows if name in r["latency"]["stages_ms"]], 50),
                "p95": percentile([r["latency"]["stages_ms"][name] for r in rows if name in r["latency"]["stages_ms"]], 95),
                "n": sum(1 for r in rows if name in r["latency"]["stages_ms"]),
            }
            for name in stage_names
        },
        "cold_start_cases": [r["id"] for r in rows if r["latency"].get("cold_start")],
    }


def _token_summary(rows: list[dict], judge_calls: list[dict]) -> dict:
    by_call: dict[str, dict] = {}
    system_calls = [c for r in rows for c in r["model_calls"]]
    for call in system_calls:
        agg = by_call.setdefault(call["name"], {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        agg["calls"] += 1
        agg["input_tokens"] += call.get("input_tokens") or 0
        agg["output_tokens"] += call.get("output_tokens") or 0
    judge_in = sum(c.get("input_tokens") or 0 for c in judge_calls)
    judge_out = sum(c.get("output_tokens") or 0 for c in judge_calls)
    return {
        "system_under_test_by_call": by_call,
        "judge": {"calls": len(judge_calls), "input_tokens": judge_in, "output_tokens": judge_out},
        "estimated_cost_usd": {
            "note": "Estimate from recorded tokens and assumed list prices (eval/metrics.py "
                    "PRICES_PER_MTOK); not a bill.",
            "system_under_test": estimate_cost_usd(system_calls),
            "judge": estimate_cost_usd(judge_calls),
        },
    }


def _compact(row: dict) -> dict:
    return {
        "id": row["id"],
        "category": row["category"],
        "expected_route": row["expected_route"],
        "predicted_route": row["predicted_route"],
        "expected_behavior": row["expected_behavior"],
        "abstained": row["abstained"],
        "abstention_appropriate": row["abstention_appropriate"],
        "answer_preview": row["answer_preview"][:160],
        "notes": row["notes"],
    }


def summarize_results(rows: list[dict], judge_calls: list[dict]) -> dict:
    # Routing (deterministic, no judge).
    clear = [r for r in rows if r["route_label_status"] == "clear"]
    confusion: dict[str, int] = {}
    for r in rows:
        key = f"{r['expected_route']}->{r['predicted_route']}"
        confusion[key] = confusion.get(key, 0) + 1
    outcomes: dict[str, int] = {}
    for r in rows:
        outcome = r.get("router_outcome") or "none"
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    routing = {
        "accuracy_clear": pass_rate([r["route_correct"] for r in clear]),
        "accuracy_all": pass_rate([r["route_correct"] for r in rows]),
        "confusion_expected_to_predicted": confusion,
        "router_outcomes": outcomes,
        "mismatches": [r["id"] for r in rows if not r["route_correct"]],
        "needs_review_labels": [r["id"] for r in rows if r["route_label_status"] == "needs_review"],
    }

    gated = [r for r in rows if r["gated_for_retrieval"]]
    context_relevance = {
        **pass_rate([(r["context_relevance"] or {}).get("pass") for r in gated]),
        "mean_score": _mean([_score_or_zero(r["context_relevance"]) for r in gated]),
        "failures": [r["id"] for r in gated if not (r["context_relevance"] or {}).get("pass")],
        "population": GATED_QA_POPULATION,
    }
    faithfulness = {
        **pass_rate([(r["faithfulness"] or {}).get("pass") for r in gated]),
        "mean_score": _mean([_score_or_zero(r["faithfulness"]) for r in gated]),
        "failures": [r["id"] for r in gated if not (r["faithfulness"] or {}).get("pass")],
        "population": GATED_QA_POPULATION,
    }

    precision_rows = [r for r in rows if r["retrieval"]["company_precision"] is not None]
    retrieval_companies = {
        "mean_company_precision": _mean([r["retrieval"]["company_precision"] for r in precision_rows]),
        "n": len(precision_rows),
        "contaminated_cases": [r["id"] for r in rows if r["retrieval"]["contaminated"]],
        "unknown_source_chunks": sum(r["retrieval"]["sources"].count("UNKNOWN") for r in rows),
    }

    grounding_rows = [r for r in rows if r["agent_used"] == "summarize"]
    summary_grounding = {
        **pass_rate([(r["summary_grounding"] or {}).get("pass") for r in grounding_rows]),
        "mean_score": _mean([_score_or_zero(r["summary_grounding"]) for r in grounding_rows]),
        "failures": [r["id"] for r in grounding_rows if not (r["summary_grounding"] or {}).get("pass")],
        "caveat": "Summaries are generated without documents; they are judged against evidence the "
                  "harness retrieves afterwards (top-5 chunks), so true claims absent from those "
                  "chunks count as unsupported.",
    }

    reference_rows = [r for r in rows if r["has_reference"]]
    answer_correctness = {
        **pass_rate([(r["answer_correctness"] or {}).get("pass") for r in reference_rows]),
        "mean_score": _mean([_score_or_zero(r["answer_correctness"]) for r in reference_rows]),
        "failures": [r["id"] for r in reference_rows if not (r["answer_correctness"] or {}).get("pass")],
    }

    abstention_rows = [r for r in rows if r["expected_behavior"] in ("answer", "abstain")]
    abstention = {
        **pass_rate([r["abstention_appropriate"] for r in abstention_rows]),
        "false_abstentions": [r["id"] for r in abstention_rows
                              if r["expected_behavior"] == "answer" and r["abstained"] is True],
        "missed_abstentions": [r["id"] for r in abstention_rows
                               if r["expected_behavior"] == "abstain" and r["abstained"] is False],
        "undetermined": [r["id"] for r in abstention_rows if r["abstention_appropriate"] is None],
    }

    # Same population rule as the pre-Phase-0 harness, for continuity only.
    legacy_rows = [r for r in rows if r["legacy"] and r["agent_used"] == "qa"
                   and r["id"] not in BOUNDARY_LEGACY_IDS and r["context_relevance"] is not None]
    legacy_comparable = {
        "note": "Pre-Phase-0 population: legacy queries routed to qa, boundary excluded. "
                "Depends on router output; for continuity only, not gated.",
        "context_relevance_pass_rate": pass_rate([r["context_relevance"]["pass"] for r in legacy_rows])["pass_rate"],
        "faithfulness_pass_rate": pass_rate([(r["faithfulness"] or {}).get("pass") for r in legacy_rows])["pass_rate"],
        "n": len(legacy_rows),
    }

    gate_values = {
        "context_relevance_pass_rate": context_relevance["pass_rate"],
        "faithfulness_pass_rate": faithfulness["pass_rate"],
        "routing_accuracy_clear": routing["accuracy_clear"]["pass_rate"],
        "answer_correctness_pass_rate": answer_correctness["pass_rate"],
        "abstention_appropriate_rate": abstention["pass_rate"],
        "summary_grounding_pass_rate": summary_grounding["pass_rate"],
    }
    gates, overall = evaluate_gates(gate_values)

    return {
        # Flat keys kept for backward compatibility (definitions documented in eval/README.md).
        "total_queries": len(rows),
        "judged_queries": len(gated),
        "context_relevance_pass_rate": context_relevance["pass_rate"],
        "faithfulness_pass_rate": faithfulness["pass_rate"],
        "mean_context_relevance": context_relevance["mean_score"],
        "mean_faithfulness": faithfulness["mean_score"],
        "overall_pass": overall,
        "gates": gates,
        "routing": routing,
        "retrieval": {"context_relevance": context_relevance, "companies": retrieval_companies},
        "faithfulness": faithfulness,
        "summary_grounding": summary_grounding,
        "answer_correctness": answer_correctness,
        "abstention": abstention,
        "boundary_and_out_of_corpus": [_compact(r) for r in rows
                                       if r["category"] in ("boundary", "out_of_corpus")],
        "corpus_defects": [_compact(r) for r in rows if r["category"] == "corpus_defect"],
        "errors": {
            "cases_with_system_errors": [r["id"] for r in rows if r["system_error"] or r["trace_errors"]],
            "judge_errors": sum(r["judge_errors"] for r in rows),
        },
        "latency_ms": _latency_summary(rows),
        "tokens": _token_summary(rows, judge_calls),
        "legacy_comparable": legacy_comparable,
    }
