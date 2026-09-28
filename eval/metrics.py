"""Pure evaluation metrics: no AWS, no I/O. Everything here is unit-tested.

Gate populations are fixed by dataset labels (eval_queries.EvalCase), never by
what the router did at run time. A case in a gated population that produced no
judgeable output (misrouted, errored, judge failure) counts as a FAILURE; it is
never dropped from the denominator.
"""
import math
import os
import re
from dataclasses import asdict, dataclass

# Exact legacy object names, checked before the patterns. Visa's 10-K was
# originally uploaded and indexed as docs/mastercard-10k-fy2025.pdf. Until the S3
# metadata migration (scripts/migrate_visa_source.py) is complete and the old
# object is deleted, retrieved chunks may still carry that source. Remove this
# entry afterwards.
LEGACY_SOURCE_NAMES: dict[str, str] = {
    "mastercard-10k-fy2025.pdf": "V",
}

# Source file name fragment -> company ticker.
SOURCE_COMPANY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("jpmorgan", "JPM"),
    ("goldman", "GS"),
    ("bank-of-america", "BAC"),
    ("blackrock", "BLK"),
    ("visa-10k", "V"),
    # Mastercard is not in the corpus; any other Mastercard file must not count as Visa.
    ("mastercard", "MA"),
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
    if name in LEGACY_SOURCE_NAMES:
        return LEGACY_SOURCE_NAMES[name]
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


_PAGE_REFERENCE = re.compile(r"\b(?:pages?|pp?\.)\s*\d+(?:\s*[-–]\s*\d+)?", re.IGNORECASE)


def marker_alternatives(markers) -> list[tuple[str, ...]]:
    """Normalize ("a", "b") -> [("a", "b")] and (("a",), ("b", "c")) -> [("a",), ("b", "c")]."""
    if markers and isinstance(markers[0], (tuple, list)):
        return [tuple(alt) for alt in markers]
    return [tuple(markers)]


def evidence_ranks(retrieved: list[dict], evidence) -> dict | None:
    """Report-only: where does the answer-bearing chunk rank in the retrieved list?

    For each (ticker, markers) group, the 1-based rank of the first retrieved
    chunk from that company's filing whose text contains every marker of at
    least one alternative, or None if no retrieved chunk matches. `markers` is
    either one tuple of strings (all required) or a tuple of such tuples
    (alternative phrasings of the same fact). Chunks from other companies never
    match.
    """
    if not evidence:
        return None
    groups = []
    for ticker, markers in evidence:
        alternatives = marker_alternatives(markers)
        rank = next((i + 1 for i, chunk in enumerate(retrieved)
                     if company_for_source(chunk.get("source", "")) == ticker
                     and any(all(m in chunk.get("text", "") for m in alt) for alt in alternatives)), None)
        groups.append({"company": ticker, "markers": [list(alt) for alt in alternatives], "rank": rank})
    ranks = [g["rank"] for g in groups]
    return {
        "groups": groups,
        "all_found": all(r is not None for r in ranks),
        "worst_rank": None if any(r is None for r in ranks) else max(ranks),
        "reciprocal_rank": sum(0.0 if r is None else 1.0 / r for r in ranks) / len(ranks),
    }


def page_references(answer: str) -> list[str]:
    """Page numbers cited in an answer. Chunk metadata has no page numbers, so none can be verified."""
    return [m.group(0) for m in _PAGE_REFERENCE.finditer(answer or "")]


def _answer_evidence(gated: list[dict]) -> dict:
    """Report-only: did retrieval return the answer-bearing chunk (deterministic markers)?"""
    found = [(r.get("evidence") or {}).get("all_found") for r in gated]
    cr_direct = {r["id"] for r in gated if (r["context_relevance"] or {}).get("score") == 5}
    evidence_found = {r["id"] for r, f in zip(gated, found) if f}
    return {
        "measures": "Answer-bearing coverage: a retrieved chunk from the expected company contains the "
                    "evidence markers for the answer. Report-only; not gated.",
        **pass_rate(found),
        "missing": sorted(r["id"] for r, f in zip(gated, found) if not f),
        "agreement_with_context_relevance_score_5": {
            "both": len(cr_direct & evidence_found),
            "judge_direct_only": sorted(cr_direct - evidence_found),
            "markers_only": sorted(evidence_found - cr_direct),
        },
    }


def _retrieval_quality_tracking(rows: list[dict]) -> dict:
    tracked = [r for r in rows if r.get("evidence") is not None]
    return {
        "note": "Report-only; not gated. See eval/README.md, Tracked retrieval-quality issues.",
        "evidence_rank": {
            "cases": len(tracked),
            "found_rate": (sum(1 for r in tracked if r["evidence"]["all_found"]) / len(tracked)) if tracked else None,
            "mean_reciprocal_rank": _mean([r["evidence"]["reciprocal_rank"] for r in tracked]),
            "evidence_not_top_ranked": {r["id"]: r["evidence"]["worst_rank"] for r in tracked
                                        if r["evidence"]["all_found"] and r["evidence"]["worst_rank"] > 1},
            "evidence_not_retrieved": sorted(r["id"] for r in tracked if not r["evidence"]["all_found"]),
        },
        "unverified_page_references": {r["id"]: r["page_references"] for r in rows if r.get("page_references")},
    }


# Failure kinds (app/errors.py) that describe the environment rather than the
# system's quality. Any of these makes a run invalid as a baseline.
INFRASTRUCTURE_KINDS = frozenset({"access_denied", "throttled", "unavailable", "timeout", "configuration"})
# Model-output failures are genuine system findings: they count against the
# metrics but do not invalidate the run.
MODEL_OUTPUT_KINDS = frozenset({"model_error", "invalid_model_output"})
# Failure codes raised by an offline network guard (tests/offline_guard.py). The
# app classifies them as "internal", but the request never reached AWS, so the
# case measured nothing about the system. Any of these makes a run invalid.
NETWORK_BLOCKED_CODES = frozenset({"NetworkBlockedError"})
# Unexpected application errors (kind "internal") are quality findings while they
# are sporadic. Above this share of evaluated cases the run is treated as broken
# (an application or harness fault), not as a measurement of quality.
MAX_APPLICATION_ERROR_SHARE = 0.2
# Version of the run-validity rules, recorded in every run_validity block. Archived
# results keep the verdict recorded under the rules in force when they ran (they carry
# no version field: rules 1). See eval/README.md "Measurement definition history".
#   1: Phase 0 (baseline 6a13ffb1).
#   2: 2026-09-28 (a9f105c): no-usable-results, network-blocked, systemic
#      application-error and harness-exception rules.
VALIDITY_RULES_VERSION = 2


def classify_system_failure(row: dict) -> str | None:
    """'network_blocked', 'infrastructure', 'model_output', 'application' or None."""
    detail = row.get("system_error_detail") or {}
    if not row.get("system_error") and not detail:
        return None
    if detail.get("code") in NETWORK_BLOCKED_CODES:
        return "network_blocked"
    kind = detail.get("kind")
    if kind in INFRASTRUCTURE_KINDS:
        return "infrastructure"
    if kind in MODEL_OUTPUT_KINDS:
        return "model_output"
    return "application"


def _environment_failure_label(error: dict) -> str | None:
    """'network_blocked' or the infrastructure kind for a trace error, else None."""
    if error.get("code") in NETWORK_BLOCKED_CODES:
        return "network_blocked"
    if error.get("kind") in INFRASTRUCTURE_KINDS:
        return error.get("kind")
    return None


def run_validity(rows: list[dict], judge_calls: list[dict], complete: bool = True,
                 harness_failure: dict | None = None) -> dict:
    """Is this run usable as a quality baseline?

    Invalid when the numbers cannot describe the system's quality:
    - no case was evaluated, or none produced a usable result (every case failed
      with a system error);
    - an offline network guard blocked any system, judge or harness call (the run
      never reached AWS);
    - infrastructure problems in the system under test, the judge or the harness,
      including non-fatal ones such as a throttled router falling back;
    - unexpected application errors in more than MAX_APPLICATION_ERROR_SHARE of
      cases (systemic breakage);
    - an unexpected harness exception, or any other reason the run is incomplete.

    Model-output failures and sporadic application errors stay quality findings:
    they count against the metrics without invalidating the run. An outage or a
    broken harness is therefore never mistaken for a quality regression.
    """
    classes = {r["id"]: classify_system_failure(r) for r in rows}
    network_blocked = sorted(i for i, c in classes.items() if c == "network_blocked")
    system_infra = {r["id"]: r["system_error_detail"]["kind"] for r in rows if classes[r["id"]] == "infrastructure"}
    application = sorted(i for i, c in classes.items() if c == "application")
    usable = sum(1 for c in classes.values() if c is None)
    degraded = {r["id"]: [label for e in r.get("trace_errors", []) if not e.get("fatal", True)
                          for label in [_environment_failure_label(e)] if label]
                for r in rows}
    degraded = {k: v for k, v in degraded.items() if v}
    failed_judge_calls = [c for c in judge_calls if not c.get("invoked", True)]
    judge_infra = [c.get("error_kind") for c in failed_judge_calls]
    judge_blocked = sum(1 for c in failed_judge_calls if c.get("error_code") in NETWORK_BLOCKED_CODES)
    harness_infra = sum(r.get("harness_infra_errors", 0) for r in rows)
    application_share = len(application) / len(rows) if rows else None
    reasons = []
    if not rows:
        reasons.append("no cases evaluated")
    elif not usable:
        reasons.append(f"no usable results: all {len(rows)} evaluated cases failed with system errors")
    if harness_failure:
        reasons.append(f"unexpected harness failure at {harness_failure.get('case')} "
                       f"({harness_failure.get('error_type')})")
    if not complete:
        reasons.append("run incomplete")
    if network_blocked:
        reasons.append(f"network blocked by an offline guard in {network_blocked} (the run never reached AWS)")
    if system_infra:
        reasons.append(f"system infrastructure failures in {sorted(system_infra)}")
    if degraded:
        reasons.append(f"degraded by non-fatal infrastructure or network-blocked failures in {sorted(degraded)}")
    if judge_infra:
        blocked = f", {judge_blocked} blocked by an offline guard" if judge_blocked else ""
        reasons.append(f"{len(judge_infra)} judge call(s) failed to invoke{blocked}")
    if harness_infra:
        reasons.append(f"{harness_infra} harness evidence retrieval failure(s)")
    if application_share is not None and application_share > MAX_APPLICATION_ERROR_SHARE:
        reasons.append(f"systemic application failure: {len(application)}/{len(rows)} cases failed with "
                       f"unexpected application errors (limit {MAX_APPLICATION_ERROR_SHARE:.0%})")
    return {
        "valid_for_baseline": not reasons,
        "rules_version": VALIDITY_RULES_VERSION,
        "reasons": reasons,
        "evaluated_cases": len(rows),
        "usable_cases": usable,
        "network_blocked_cases": network_blocked,
        "system_infrastructure_failures": system_infra,
        "system_model_output_failures": sorted(i for i, c in classes.items() if c == "model_output"),
        "application_errors": application,
        "application_error_share": application_share,
        "degraded_cases": degraded,
        "judge_infrastructure_errors": len(judge_infra),
        "judge_infrastructure_error_kinds": sorted(set(k for k in judge_infra if k)),
        "judge_network_blocked_calls": judge_blocked,
        "harness_infrastructure_errors": harness_infra,
        "harness_failure": harness_failure,
    }


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
    judge_by_kind: dict[str, dict] = {}
    for call in judge_calls:
        agg = judge_by_kind.setdefault(call.get("kind", "unknown"), {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        agg["calls"] += 1
        agg["input_tokens"] += call.get("input_tokens") or 0
        agg["output_tokens"] += call.get("output_tokens") or 0
    return {
        "system_under_test_by_call": by_call,
        "judge": {"calls": len(judge_calls),
                  "invoked": sum(1 for c in judge_calls if c.get("invoked", True)),
                  "input_tokens": judge_in, "output_tokens": judge_out, "by_kind": judge_by_kind},
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
    cr_scores = [(r["context_relevance"] or {}).get("score") for r in gated]
    context_relevance = {
        **pass_rate([(r["context_relevance"] or {}).get("pass") for r in gated]),
        "mean_score": _mean([_score_or_zero(r["context_relevance"]) for r in gated]),
        "failures": [r["id"] for r in gated if not (r["context_relevance"] or {}).get("pass")],
        "population": GATED_QA_POPULATION,
        "measures": "Topical relevance: pass is score >= 3 ('topically related but require inference'). "
                    "It does not require the answer to be in the retrieved chunks; see answer_evidence.",
        "score_distribution": {str(k): cr_scores.count(k) for k in sorted({s for s in cr_scores if s is not None})},
        "direct_answer_rate": (sum(1 for s in cr_scores if s == 5) / len(gated)) if gated else None,
    }
    answer_evidence = _answer_evidence(gated)
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
    refusals = [r["id"] for r in grounding_rows if (r["summary_grounding"] or {}).get("refusal")]
    substantive = [r for r in grounding_rows if r["id"] not in refusals]
    summary_grounding = {
        **pass_rate([(r["summary_grounding"] or {}).get("pass") for r in grounding_rows]),
        "mean_score": _mean([_score_or_zero(r["summary_grounding"]) for r in grounding_rows]),
        "failures": [r["id"] for r in grounding_rows if not (r["summary_grounding"] or {}).get("pass")],
        "refusals": refusals,
        "substantive": {
            "n": len(substantive),
            "grounded_rate": pass_rate([(r["summary_grounding"] or {}).get("pass") for r in substantive])["pass_rate"],
        },
        "rule": "Refusals (answer assessment abstained=True) count as failures, never as grounded summaries.",
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
        "retrieval": {"context_relevance": context_relevance, "answer_evidence": answer_evidence,
                      "companies": retrieval_companies},
        "faithfulness": faithfulness,
        "summary_grounding": summary_grounding,
        "answer_correctness": answer_correctness,
        "abstention": abstention,
        "boundary_and_out_of_corpus": [_compact(r) for r in rows
                                       if r["category"] in ("boundary", "out_of_corpus")],
        "forbidden_fact_leaks": {
            "note": "Deterministic: answers containing a fact that belongs to a different "
                    "company (e.g. Visa figures in a Mastercard answer).",
            "cases_checked": [r["id"] for r in rows if r.get("forbidden_facts_checked")],
            "leaks": {r["id"]: r["forbidden_fact_hits"] for r in rows if r.get("forbidden_fact_hits")},
        },
        "errors": {
            "cases_with_system_errors": [r["id"] for r in rows if r["system_error"] or r["trace_errors"]],
            "judge_errors": sum(r["judge_errors"] for r in rows),
            "judge_infra_errors": sum(r.get("judge_infra_errors", 0) for r in rows),
        },
        "latency_ms": _latency_summary(rows),
        "tokens": _token_summary(rows, judge_calls),
        "legacy_comparable": legacy_comparable,
        "retrieval_quality_tracking": _retrieval_quality_tracking(rows),
    }
