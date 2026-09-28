"""Router benchmark CLI. A dry run is the default; nothing billable happens without --live.

    python -m experiments.router_bench                      # benchmark dry run (offline)
    python -m experiments.router_bench verify-jev           # Jev verification dry run (offline)
    python -m experiments.router_bench --live bedrock --live typesafe   # LIVE, billable: needs approval

A dry run installs the offline network guard and disables .env loading before any
application module is imported, uses fake Bedrock and TypeSafe clients, reads no
credentials, and prints the plan, the frozen fingerprints and a SIMULATED execution.
"""
import argparse
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

LIVE_PROVIDERS = ("bedrock", "typesafe")

# Live runs read only these names from .env, per authorized provider; nothing else is loaded.
PROVIDER_ENV_NAMES = {
    "bedrock": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_DEFAULT_REGION",
                "BEDROCK_MODEL_ID"),
    "typesafe": ("TYPESAFE_API_KEY",),
}
DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")


def read_env_file(names, path: str = DOTENV_PATH) -> dict:
    """Only the named keys from .env (other entries are parsed and discarded, never exported)."""
    wanted = set(names)
    if not wanted or not os.path.exists(path):
        return {}
    from dotenv import dotenv_values

    return {k: v for k, v in dotenv_values(path).items() if k in wanted and v}


def export_bedrock_env(file_values: dict) -> None:
    """Bedrock credentials for botocore; existing environment values win. The TypeSafe key is never exported."""
    for name in PROVIDER_ENV_NAMES["bedrock"]:
        if name not in os.environ and file_values.get(name):
            os.environ[name] = file_values[name]


def load_typesafe_key(file_values: dict):
    from experiments.router_bench.safety import SecretValue

    value = os.environ.get("TYPESAFE_API_KEY") or file_values.get("TYPESAFE_API_KEY")
    return SecretValue(value) if value else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m experiments.router_bench", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", nargs="?", default="benchmark", choices=("benchmark", "verify-jev"))
    parser.add_argument("--live", action="append", choices=LIVE_PROVIDERS, default=[],
                        help="authorize billable calls to this provider (repeat per provider); omit for a dry run")
    parser.add_argument("--routers", default="haiku,rules,jev", help="comma-separated subset of haiku,rules,jev")
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--ids", default=None, help="comma-separated approved case IDs (default: all 34 v2 cases)")
    parser.add_argument("--repeat-first", action="store_true", help="verify-jev: repeat L01 as a third call")
    parser.add_argument("--max-cost-bedrock", type=float, default=None)
    parser.add_argument("--max-cost-typesafe", type=float, default=None)
    parser.add_argument("--max-cost-total", type=float, default=None)
    parser.add_argument("--haiku-reservation", choices=("strict", "practical"), default="strict",
                        help="strict: reserve the largest possible Haiku call (hard cap); practical: reserve "
                             "~19x the mean output (one call may overshoot a cap; disclosed in the plan)")
    parser.add_argument("--output", default=None, help="write the artifact here (dry run: optional)")
    return parser


def _git() -> dict:
    def run(*cmd):
        try:
            return subprocess.run(["git", *cmd], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None
    status = run("status", "--porcelain", "--untracked-files=no")
    return {"sha": run("rev-parse", "HEAD"), "tracked_changes_uncommitted": bool(status) if status is not None else None}


def _fmt_ids(ids) -> str:
    return " ".join(ids) if ids else "-"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    live = frozenset(args.live)

    if not live:
        # Before any app import: block all outbound network, force fake credentials, disable .env.
        from tests import offline_guard

        offline_guard.install()
    elif "PYTEST_CURRENT_TEST" in os.environ:
        print("Refusing: live calls are never made from inside pytest.", file=sys.stderr)
        return 2

    from eval.routing_datasets import routing_dataset
    from experiments.router_bench import metrics as bench_metrics
    from experiments.router_bench.config import (
        ALL_ROUTERS,
        DATASET_VERSION,
        DEFAULT_COST_CAPS,
        DEFAULT_REPETITIONS,
        DEFAULT_SEED,
        HAIKU_MODEL_ID,
        JEV_MODEL,
        MIN_REPETITIONS,
        ROUTER_PROVIDERS,
        WARMUP_CALLS,
    )
    from experiments.router_bench.payload import ApprovedQuestions
    from experiments.router_bench.runner import build_plan, build_verification_plan, run
    from experiments.router_bench.persistence import JOURNAL_SUFFIX, RunJournal
    from experiments.router_bench.safety import ArtifactSafetyError, LiveAuthorization, assert_safe_for_output

    cases = routing_dataset(DATASET_VERSION)
    if args.command == "verify-jev":
        plan = build_verification_plan(repeat_first=args.repeat_first)
    else:
        routers = tuple(r.strip() for r in args.routers.split(",") if r.strip())
        if not routers or set(routers) - set(ALL_ROUTERS):
            print(f"--routers must be a subset of {','.join(ALL_ROUTERS)}", file=sys.stderr)
            return 2
        repetitions = args.repetitions if args.repetitions is not None else DEFAULT_REPETITIONS
        if live and repetitions < MIN_REPETITIONS:
            print(f"A live benchmark needs at least {MIN_REPETITIONS} repetitions.", file=sys.stderr)
            return 2
        caps = dict(DEFAULT_COST_CAPS)
        for provider, value in (("bedrock", args.max_cost_bedrock), ("typesafe", args.max_cost_typesafe),
                                ("total", args.max_cost_total)):
            if value is not None:
                caps[provider] = value
        ids = [i.strip() for i in args.ids.split(",")] if args.ids else None
        plan = build_plan(routers, repetitions, args.warmup if args.warmup is not None else WARMUP_CALLS,
                          args.seed if args.seed is not None else DEFAULT_SEED, ids, caps,
                          haiku_reservation=args.haiku_reservation)

    needed = {ROUTER_PROVIDERS[r] for r in plan.routers} - {None}
    if live:
        if needed - live:
            print(f"A live run must authorize every provider it calls; missing: {sorted(needed - live)}",
                  file=sys.stderr)
            return 2
        if live - needed:
            print(f"--live given for unused provider(s): {sorted(live - needed)}", file=sys.stderr)
            return 2

    approved = ApprovedQuestions(cases, plan.allowed_ids)
    impl, real_clients = _build_routers(plan, cases, approved, live, LiveAuthorization)
    if impl is None:
        return 2

    mode = "live" if live else "dry_run_simulated"
    _print_plan(plan, mode)
    if not plan.feasible:
        print("\nPLAN NOT FEASIBLE:\n  " + "\n  ".join(plan.problems))
        return 2

    created_at = datetime.now(timezone.utc)
    provenance = {
        "created_at": created_at.isoformat(), "mode": mode, "git": _git(),
        "python": platform.python_version(), "platform": platform.platform(),
        "live_authorization": sorted(live), "real_clients_constructed": real_clients,
        "jev_model_pinned": JEV_MODEL, "bedrock_router_model": impl["haiku"].model_id if "haiku" in impl else None,
        "bedrock_router_model_expected": HAIKU_MODEL_ID,
        "aws_max_attempts": os.environ.get("AWS_MAX_ATTEMPTS"),
    }
    output = args.output
    if live and not output:
        output = f"eval/results/experiments/{plan.kind.replace('_', '-')}-{created_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    # Live runs always journal; each completed call is persisted (sanitized, fsynced) before the next one.
    journal = RunJournal(output + JOURNAL_SUFFIX) if output else None
    if journal is not None:
        journal.event("provenance", **provenance)
        print(f"Journal (per-call, crash-resistant): {journal.path}")
    try:
        result = run(plan, impl, pace=bool(live), journal=journal)
    finally:
        if journal is not None:
            journal.close()

    exit_code = 0 if result["complete"] else 1
    try:
        metrics = (bench_metrics.compute(result["records"], cases, plan.routers, seed=plan.seed)
                   if plan.kind == "benchmark" else _verification_checks(result["records"], plan))
    except Exception as exc:  # the journal already holds every record; keep going to write an artifact
        metrics = {"error": f"metrics failed: {type(exc).__name__}"}
        exit_code = 3
    artifact = {"kind": plan.kind, "provenance": provenance, "plan": plan.to_dict(),
                "execution": {k: v for k, v in result.items() if k != "records"},
                "records": result["records"], "metrics": metrics}
    try:
        text = assert_safe_for_output(artifact, what="benchmark artifact")
    except ArtifactSafetyError as exc:
        text = assert_safe_for_output(_minimal_artifact(plan, provenance, result, exc.category, journal),
                                      what="minimal artifact")
        print(f"\nFull artifact REFUSED by the safety check ({exc.category}); writing a minimal diagnostic "
              "artifact instead. Sanitized per-call records are in the journal.")
        metrics = None
        exit_code = 3

    _print_result(plan, result, metrics, mode, real_clients)
    if output:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "x" if live else "w", encoding="utf-8") as f:  # live evidence is never overwritten
            f.write(text)
        print(f"\nArtifact written: {output}")
    if not live:
        from tests import offline_guard

        print(f"Outbound network attempts intercepted by the offline guard: {len(offline_guard.blocked_requests)}")
    return exit_code


def _minimal_artifact(plan, provenance, result, category: str, journal) -> dict:
    """What remains safe to store when the full artifact is refused: counts, ledger, fingerprints."""
    return {
        "kind": plan.kind, "artifact_rejected": True, "rejection_category": category,
        "provenance": {k: provenance[k] for k in ("created_at", "mode", "git", "live_authorization", "jev_model_pinned")},
        "fingerprints": plan.fingerprints,
        "execution": {k: result[k] for k in ("complete", "valid", "executed_calls", "scheduled_calls", "ledger")},
        "journal": None if journal is None else {"path": journal.path, "lines": journal.lines,
                                                 "redacted_records": journal.redacted_records},
    }


def _build_routers(plan, cases, approved, live, LiveAuthorization):
    """Dry run: fakes only. Live: real clients, each behind its provider's LiveAuthorization."""
    from experiments.router_bench.routers import ModelNotPinned

    try:
        return _build_routers_unchecked(plan, cases, approved, live, LiveAuthorization)
    except ModelNotPinned as exc:
        print(f"Refusing: {exc}", file=sys.stderr)
        return None, []


def _build_routers_unchecked(plan, cases, approved, live, LiveAuthorization):
    from experiments.router_bench.routers import HaikuRouter, JevClient, JevRouter, RulesRouter

    impl, real = {}, []
    if not live:
        from experiments.router_bench.fakes import FakeBedrock, FakeTypeSafe

        labels = {c.query: c.expected_route for c in cases}
        if "haiku" in plan.routers:
            impl["haiku"] = HaikuRouter(bedrock_client=FakeBedrock(labels, plan.seed + 1),
                                        reservation=plan.haiku_reservation)
        if "jev" in plan.routers:
            fake = FakeTypeSafe(labels, plan.seed + 2)
            impl["jev"] = JevRouter(JevClient(transport=fake.transport()), approved)
    else:
        authorization = LiveAuthorization(live)
        # Only the names each authorized provider needs; a TypeSafe-only run reads no AWS values.
        file_values = read_env_file(name for provider in live for name in PROVIDER_ENV_NAMES[provider])
        if "haiku" in plan.routers:
            export_bedrock_env(file_values)
            impl["haiku"] = HaikuRouter(authorization=authorization, reservation=plan.haiku_reservation)
            real.append("bedrock-runtime")
        if "jev" in plan.routers:
            api_key = load_typesafe_key(file_values)
            if api_key is None:
                print("TYPESAFE_API_KEY is not set (value never printed).", file=sys.stderr)
                return None, real
            impl["jev"] = JevRouter(JevClient(authorization=authorization, api_key=api_key), approved)
            real.append("typesafe")
        file_values.clear()
    if "rules" in plan.routers:
        impl["rules"] = RulesRouter()
    return impl, real


def _verification_checks(records: list[dict], plan) -> dict:
    """Design §7 checks, per call and across calls. Report-only; nothing here is retried."""
    import json

    from eval.routing_datasets import routing_dataset
    from experiments.router_bench.payload import ApprovedQuestions, build_jev_payload

    cases = {c.id: c for c in routing_dataset(plan.dataset_version)}
    approved = ApprovedQuestions(list(cases.values()), plan.allowed_ids)
    calls = []
    for r in records:
        payload_bytes = len(json.dumps(build_jev_payload(cases[r["case_id"]], approved)).encode("utf-8"))
        p = r["raw_score"]
        conf = (r["extra"] or {}).get("jev_confidence")
        calls.append({
            "case_id": r["case_id"], "outcome": r["outcome"], "http_status": r["http_status"],
            "error_class": r["error_class"], "schema_valid": r["raw_label"] is not None,
            "choice": r["raw_label"], "p_choice": p, "confidence": conf,
            "confidence_equals_2p_minus_1": (abs(conf - (2 * p - 1)) <= 1e-3) if p is not None and conf is not None
            else None,
            "would_fall_back_at_0_6": (p < 0.6) if p is not None else None,
            "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"],
            "local_estimate_tokens": payload_bytes // 4, "cost_usd": r["cost_usd"], "cost_basis": r["cost_basis"],
            "latency_ms": r["latency_ms"], "response_headers": (r["extra"] or {}).get("response_headers"),
            "extra_fields": (r["extra"] or {}).get("extra_fields"),
        })
    repeated = sorted((r for r in records if r["case_id"] == plan.allowed_ids[0]), key=lambda r: r["repetition"])
    determinism = None
    if len(repeated) >= 2:
        first, second = ((r["extra"] or {}).get("jev_probabilities") for r in repeated[:2])
        determinism = {"identical_probabilities": first is not None and first == second}
    return {"calls": calls, "determinism": determinism,
            "all_schema_valid": all(c["schema_valid"] for c in calls) and len(calls) == len(plan.schedule)}


def _print_plan(plan, mode: str) -> None:
    banner = ("DRY RUN: offline, simulated clients, no credentials read, no network"
              if mode != "live" else "LIVE RUN: billable calls to " + ", ".join(sorted(
                  {p for p in ("bedrock", "typesafe") if plan.planned_calls.get(p)})))
    title = "ROUTER BENCHMARK" if plan.kind == "benchmark" else "JEV API VERIFICATION"
    print(f"{title} - {banner}")
    fp = plan.fingerprints
    print(f"\nFrozen fingerprints\n  routing dataset {fp['routing_dataset']['version']}: {fp['routing_dataset']['sha256']}"
          f"\n  Jev payload template: {fp['jev_payload_template_sha256']}\n  rules router: {fp['rules_sha256']}")
    print(f"\nApproved questions ({len(plan.allowed_ids)} IDs)")
    labels = {"strict_qa": "strict, qa", "strict_summarize": "strict, summarize",
              "policy": "policy 'unclear -> qa' (report-only)", "exploratory": "exploratory (report-only)"}
    for key, label in labels.items():
        group = plan.categories[key]
        print(f"  {label} ({group['count']}): {_fmt_ids(group['ids'])}")
    print(f"\nRouters: {', '.join(plan.routers)}; repetitions {plan.repetitions}; "
          f"warm-up {plan.warmup_calls} per paid router; seed {plan.seed}")
    pc = plan.planned_calls
    print(f"Planned calls: Bedrock {pc['bedrock']}, TypeSafe {pc['typesafe']}, local rules {pc['local']} "
          f"(warm-up {pc['warmup']}; total {pc['total']})")
    cost = plan.cost
    exp, caps = cost["expected_usd"], cost["hard_caps_usd"]
    print(f"Estimated cost: Bedrock ${exp['bedrock']:.4f}, TypeSafe ${exp['typesafe']:.4f}, total ${exp['total']:.4f}")
    print(f"Hard ceilings: Bedrock ${caps['bedrock']:.2f} and {plan.request_caps['bedrock']} requests; "
          f"TypeSafe ${caps['typesafe']:.2f} and {plan.request_caps['typesafe']} requests; total ${caps['total']:.2f}")
    wc, th = cost["worst_case_reservation_per_call_usd"], cost["theoretical_all_worst_case_usd"]
    print(f"Worst-case reservation per call: Bedrock ${wc['bedrock']:.6f}, TypeSafe ${wc['typesafe']:.6f} "
          f"(if every call hit it: ${th['bedrock']:.2f} / ${th['typesafe']:.2f}; informational only, "
          "reservations are reconciled to recorded usage after each call)")
    print(f"Cost basis: {cost['basis']}")
    for provider in ("bedrock", "typesafe"):
        if not plan.planned_calls.get(provider):
            continue
        g = cost["budget_guarantee"][provider]
        guarantee = ("hard cap: committed spend cannot exceed the ceiling" if g["hard_cap"] else
                     f"NOT a hard cap: one call may overshoot the ceiling by up to ${g['max_overshoot_usd']:.4f}, "
                     "then the run stops")
        print(f"Budget guarantee, {provider}: {guarantee}; headroom at expected cost ${g['headroom_usd']:.4f}")
    print("  (assumptions: " + "; ".join(cost["budget_guarantee"]["assumptions"]) + ")")
    print(f"Plan feasible: {plan.feasible}")


def _print_result(plan, result, metrics, mode, real_clients) -> None:
    sim = " (SIMULATED - not a measurement)" if mode != "live" else ""
    print(f"\nExecution{sim}: {result['executed_calls']}/{result['scheduled_calls']} calls; "
          f"complete={result['complete']}; valid={result['valid']}")
    if result["invalid_reasons"]:
        print("  reasons: " + "; ".join(result["invalid_reasons"]))
    for provider, acct in result["ledger"]["providers"].items():
        print(f"  ledger {provider}: {acct['requests']}/{acct['request_cap']} requests, "
              f"${acct['committed_usd']:.6f} of ${acct['cost_cap_usd']:.2f}; "
              f"{acct['charged_at_worst_case']} charged at worst case")
    d = result["downstream"]
    print(f"\nDownstream isolation: {'CLEAN' if d['clean'] else 'VIOLATED'} - QA, summarization and retrieval code: "
          f"{len(d['downstream_calls'])} calls intercepted; modules imported during the run: "
          f"{d['downstream_modules_imported_during_run'] or 'none'}; loaded in this process: "
          f"{sorted(m for m in d['downstream_modules_guarded'] if m in sys.modules) or 'none'}")
    print(f"Live authorization: {'none' if mode != 'live' else 'yes'}; real clients constructed: {real_clients or 'none'}")
    if metrics is None or "error" in metrics:
        print(f"\nMetrics not available: {'artifact refused' if metrics is None else metrics['error']}")
    elif plan.kind == "benchmark":
        print(f"\nMetrics{sim}")
        if mode != "live" and "rules" in metrics["per_router"]:
            print("  (rules is deterministic and local, so its numbers are real even in a dry run; its patterns were "
                  "written from the taxonomy by an author who had seen these questions: not an unbiased estimate)")
        for name, m in metrics["per_router"].items():
            acc = m["strict_accuracy"]
            maj, pooled = acc["majority"], acc["pooled"]
            rec = m["recall"]["majority"]
            print(f"  {name:<6} strict majority {maj['passed']}/{maj['n']}, pooled {pooled['rate']:.3f}; "
                  f"recall qa {rec['qa']['passed']}/{rec['qa']['n']}, summarize {rec['summarize']['passed']}/"
                  f"{rec['summarize']['n']}; fallback {m['fallback']['rate']:.3f}; infra {m['infra_errors']['rate']:.3f}; "
                  f"p95 {m['latency']['p95_ms']:.2f} ms; cost ${m['cost']['usd']:.6f}")
    else:
        for c in metrics["calls"]:
            print(f"  {c['case_id']}: {c['outcome']}, choice {c['choice']}, p {c['p_choice']}, "
                  f"conf=2p-1: {c['confidence_equals_2p_minus_1']}, tokens {c['input_tokens']} "
                  f"(local estimate {c['local_estimate_tokens']})")
