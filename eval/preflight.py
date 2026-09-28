"""Offline preflight for a paid baseline evaluation run. Makes no AWS or model calls.

Checks the dataset, labels, contamination rules, gates, results path, code under
test, configuration and cost ceiling, and estimates paid requests and cost.
Exits 1 if anything blocks a trustworthy baseline run.

Usage:
  python -m eval.preflight [--results-path PATH] [--json]
"""
import argparse
import json
import os
import sys
from collections import Counter

EXPECTED_SYSTEM_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
EXPECTED_JUDGE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
CORPUS_FILES = {
    "jpmorgan-chase-10k-fy2025.pdf": "JPM",
    "goldman-sachs-10k-fy2025.pdf": "GS",
    "bank-of-america-10k-fy2025.pdf": "BAC",
    "blackrock-10k-fy2025.pdf": "BLK",
    "visa-10k-fy2025.pdf": "V",
}

# Per-call token ASSUMPTIONS (input, output) for the estimate. Replace with
# measured values from the first run's results (tokens section).
TOKEN_ASSUMPTIONS = {
    "router": (240, 50),
    "embed_query": (25, 0),
    "qa_generate": (4_100, 350),
    "summarize": (100, 600),
    "judge_context_relevance": (4_700, 80),
    "judge_faithfulness": (4_900, 80),
    "judge_summary_grounding": (4_700, 80),
    "judge_answer_assessment": (700, 80),
}
CALL_MODELS = {
    "router": "system", "qa_generate": "system", "summarize": "system", "embed_query": "embedding",
    "judge_context_relevance": "judge", "judge_faithfulness": "judge",
    "judge_summary_grounding": "judge", "judge_answer_assessment": "judge",
}
ESTIMATE_LOW, ESTIMATE_HIGH, GEO_PREMIUM = 0.75, 1.5, 1.10


def _check(name: str, ok: bool, detail, severity: str = "block") -> dict:
    return {"check": name, "status": "pass" if ok else severity, "detail": detail}


def check_dataset(cases) -> list[dict]:
    ids = [c.id for c in cases]
    duplicates = sorted(i for i, n in Counter(ids).items() if n > 1)
    gated = [c.id for c in cases if c.gated_for_retrieval]
    bad_labels = [c.id for c in cases if c.expected_route not in ("qa", "summarize")
                  or c.route_label_status not in ("clear", "needs_review")
                  or c.expected_behavior not in ("answer", "abstain", "either")]
    unknown_tickers = sorted({t for c in cases for t in c.companies} - set(CORPUS_FILES.values()))
    bad_refs = [c.id for c in cases if c.reference_source
                and not {part.strip().split(" ")[0] for part in c.reference_source.split(";")} <= set(CORPUS_FILES)]
    gated_incomplete = [c.id for c in cases if c.gated_for_retrieval
                        and not (c.reference_answer and c.reference_source and c.companies and c.evidence)]
    abstain_with_ref = [c.id for c in cases if c.expected_behavior == "abstain" and c.reference_answer]
    mastercard = [c for c in cases if "mastercard" in c.query.lower()]
    mastercard_bad = [c.id for c in mastercard if c.category != "out_of_corpus" or c.expected_behavior != "abstain"
                      or c.companies or not c.forbidden_facts]
    visa = [c for c in cases if "V" in c.companies]
    visa_bad = [c.id for c in visa if c.reference_source and not c.reference_source.startswith("visa-10k-fy2025.pdf")]
    return [
        _check("dataset.size", len(cases) == 34, f"{len(cases)} cases"),
        _check("dataset.unique_ids", not duplicates, duplicates or "all unique"),
        _check("dataset.labels_valid", not bad_labels, bad_labels or "all valid"),
        _check("dataset.gated_population", len(gated) == 19, {"n": len(gated), "ids": gated}),
        _check("dataset.gated_cases_complete", not gated_incomplete,
               gated_incomplete or "every gated case has reference, source, companies and evidence markers"),
        _check("dataset.known_companies_only", not unknown_tickers, unknown_tickers or sorted(CORPUS_FILES.values())),
        _check("dataset.references_cite_corpus_files", not bad_refs, bad_refs or "ok"),
        _check("dataset.abstain_cases_have_no_reference", not abstain_with_ref, abstain_with_ref or "ok"),
        _check("dataset.mastercard_out_of_corpus", bool(mastercard) and not mastercard_bad,
               {"ids": [c.id for c in mastercard], "problems": mastercard_bad}),
        _check("dataset.visa_references", bool(visa) and not visa_bad,
               {"ids": [c.id for c in visa], "problems": visa_bad}),
        _check("dataset.needs_review_not_gated", True,
               {"needs_review": [c.id for c in cases if c.route_label_status == "needs_review"],
                "note": "reported, not gated, until a human adjudicates the labels"}, "warn"),
    ]


def check_contamination_rules() -> list[dict]:
    from eval.metrics import company_for_source

    expected = {f"s3://financial-copilot-hl/docs/{name}": t for name, t in CORPUS_FILES.items()}
    expected["s3://financial-copilot-hl/docs/mastercard-10k-fy2025.pdf"] = "V"  # legacy object name
    expected["s3://financial-copilot-hl/docs/mastercard-10k-fy2026.pdf"] = "MA"
    wrong = {src: (company_for_source(src), t) for src, t in expected.items() if company_for_source(src) != t}
    return [_check("contamination.source_mapping", not wrong, wrong or "all corpus files map to the right ticker; "
                   "legacy Mastercard-named object maps to Visa; other Mastercard names map to MA")]


def check_gates() -> list[dict]:
    from eval.metrics import GATES

    enforced = {g.metric: g.threshold for g in GATES if g.enforced}
    return [_check("gates.enforced_unchanged",
                   enforced == {"context_relevance_pass_rate": 0.8, "faithfulness_pass_rate": 0.8},
                   {"enforced": enforced, "report_only": [g.metric for g in GATES if not g.enforced]})]


def check_results_path(results_path: str) -> list[dict]:
    legacy_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "legacy"))
    target = os.path.normpath(os.path.abspath(results_path))
    in_legacy = target == legacy_dir or target.startswith(legacy_dir + os.sep)
    legacy_file = os.path.join(legacy_dir, "2026-06-04_pre_phase0_harness.json")
    legacy_schema = None
    if os.path.exists(legacy_file):
        with open(legacy_file, encoding="utf-8") as f:
            legacy_schema = json.load(f).get("summary", {}).get("schema_version")
    return [
        _check("results.not_in_legacy_dir", not in_legacy, results_path),
        _check("results.will_not_overwrite", not os.path.exists(results_path),
               f"{results_path} {'exists and would be overwritten' if os.path.exists(results_path) else 'is new'}",
               "warn"),
        _check("results.legacy_distinguishable", os.path.exists(legacy_file) and legacy_schema is None,
               "legacy file has no schema_version; new results are schema 2 with run_id, provenance, run_validity",
               "warn"),
    ]


def check_code_under_test(code_version: dict | None = None) -> list[dict]:
    import app.agents.orchestrator as orchestrator_module
    import app.errors  # noqa: F401  (reliability code must be importable)
    from eval.llm_judge import _code_version

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    module_path = os.path.abspath(orchestrator_module.__file__)
    code = code_version if code_version is not None else _code_version()
    return [
        _check("code.local_in_process", module_path.startswith(repo),
               {"orchestrator": os.path.relpath(module_path, repo),
                "note": "the harness imports the local code; the deployed Lambda (June build) is never called"}),
        _check("code.reliability_fix_present", True, "app.errors importable (ServiceFailure, 5xx mapping)"),
        _check("code.committed", code.get("tracked_changes_uncommitted") is False,
               {**code, "why": "provenance records the git SHA; uncommitted edits would make it misleading"}),
    ]


def check_configuration(env=os.environ) -> list[dict]:
    system_model = env.get("BEDROCK_MODEL_ID")
    judge_model = env.get("JUDGE_MODEL_ID")
    missing = [k for k in ("S3_BUCKET_NAME", "FAISS_INDEX_S3_KEY", "FAISS_META_S3_KEY") if not env.get(k)]
    has_creds = bool(env.get("AWS_ACCESS_KEY_ID") and env.get("AWS_SECRET_ACCESS_KEY")) or bool(env.get("AWS_PROFILE"))
    return [
        _check("config.system_model", system_model == EXPECTED_SYSTEM_MODEL_ID, system_model),
        _check("config.judge_model", judge_model == EXPECTED_JUDGE_MODEL_ID, judge_model),
        _check("config.index_location", not missing, missing or "S3 bucket and index keys set"),
        _check("config.aws_credentials_present", has_creds, "present" if has_creds else "missing (values never shown)"),
    ]


def estimate_run(cases) -> dict:
    """Paid requests and cost for one run, from expected routes and TOKEN_ASSUMPTIONS."""
    from eval.metrics import price_for

    n_qa = sum(1 for c in cases if c.expected_route == "qa")
    n_sum = len(cases) - n_qa
    calls = {
        "router": len(cases), "embed_query": n_qa + n_sum,  # QA retrieval + harness evidence for summaries
        "qa_generate": n_qa, "summarize": n_sum,
        "judge_context_relevance": n_qa, "judge_faithfulness": n_qa,
        "judge_summary_grounding": n_sum, "judge_answer_assessment": len(cases),
    }
    models = {"system": EXPECTED_SYSTEM_MODEL_ID, "judge": EXPECTED_JUDGE_MODEL_ID,
              "embedding": "amazon.titan-embed-text-v2:0"}
    cost = {"system": 0.0, "judge": 0.0, "embedding": 0.0}
    for name, n in calls.items():
        tokens_in, tokens_out = TOKEN_ASSUMPTIONS[name]
        price_in, price_out = price_for(models[CALL_MODELS[name]])
        cost[CALL_MODELS[name]] += n * (tokens_in * price_in + tokens_out * price_out) / 1e6
    total = sum(cost.values())
    requests = {
        "haiku": calls["router"] + calls["qa_generate"] + calls["summarize"],
        "titan": calls["embed_query"],
        "sonnet_judge": sum(n for k, n in calls.items() if k.startswith("judge_")),
    }
    return {
        "basis": "expected routes from labels; misroutes shift judge calls. Token counts are assumptions.",
        "cases": {"qa": n_qa, "summarize": n_sum},
        "calls": calls,
        "paid_requests": {**requests, "total": sum(requests.values())},
        "cost_usd": {k: round(v, 4) for k, v in cost.items()},
        "total_usd": round(total, 2),
        "range_usd": [round(total * ESTIMATE_LOW, 2), round(total * ESTIMATE_HIGH * GEO_PREMIUM, 2)],
    }


def check_cost_ceiling(estimate: dict, env=os.environ) -> list[dict]:
    from eval.llm_judge import DEFAULT_MAX_COST_USD

    ceiling = float(env.get("EVAL_MAX_COST_USD", DEFAULT_MAX_COST_USD))
    high = estimate["range_usd"][1]
    return [_check("cost.ceiling_above_estimate", ceiling >= high,
                   {"ceiling_usd": ceiling, "estimate_high_usd": high})]


def run_preflight(results_path: str | None = None, code_version: dict | None = None, env=None) -> dict:
    from eval.eval_queries import EVAL_CASES
    from eval.llm_judge import DEFAULT_RESULTS_PATH

    env = os.environ if env is None else env
    results_path = results_path or env.get("EVAL_RESULTS_PATH", DEFAULT_RESULTS_PATH)
    estimate = estimate_run(EVAL_CASES)
    checks = (check_dataset(EVAL_CASES) + check_contamination_rules() + check_gates()
              + check_results_path(results_path) + check_code_under_test(code_version)
              + check_configuration(env) + check_cost_ceiling(estimate, env))
    blockers = [c["check"] for c in checks if c["status"] == "block"]
    return {"results_path": results_path, "checks": checks, "estimate": estimate,
            "blockers": blockers, "ready": not blockers}


class _NetworkAttempted(RuntimeError):
    pass


def _block_network() -> list[str]:
    """Make any botocore HTTP request fail loudly; returns the list of attempted URLs."""
    import botocore.httpsession

    attempts: list[str] = []

    def blocked(self, request):
        attempts.append(request.url.split("?")[0])
        raise _NetworkAttempted(f"preflight attempted a network call: {request.url}")

    botocore.httpsession.URLLib3Session.send = blocked
    return attempts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results-path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    attempts = _block_network()
    from dotenv import load_dotenv

    load_dotenv()
    report = run_preflight(args.results_path)
    report["network_attempts"] = attempts
    if attempts:
        report["blockers"].append("offline_guarantee")
        report["ready"] = False

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        for c in report["checks"]:
            print(f"[{c['status'].upper():5}] {c['check']:42} {json.dumps(c['detail'], default=str)[:150]}")
        e = report["estimate"]
        print(f"\nEstimated paid requests: {e['paid_requests']}")
        print(f"Estimated cost: ${e['total_usd']:.2f} (range ${e['range_usd'][0]:.2f}-${e['range_usd'][1]:.2f})")
        print(f"Network attempts during preflight: {len(attempts)}")
        print(f"READY: {report['ready']}  blockers: {report['blockers'] or 'none'}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
