"""Plan and execute a benchmark schedule under budgets and the downstream tripwire."""
import random
import time
from dataclasses import asdict, dataclass, field

from eval.routing_datasets import PINNED_SHA256, routing_dataset
from experiments.router_bench.config import (
    CONSECUTIVE_INFRA_ERROR_LIMIT,
    DATASET_VERSION,
    DEFAULT_COST_CAPS,
    HAIKU_EXPECTED_TOKENS,
    JEV_EXPECTED_INPUT_TOKENS,
    JEV_MIN_SECONDS_BETWEEN_CALLS,
    ROUTER_PROVIDERS,
    VERIFICATION_CASE_IDS,
    VERIFICATION_COST_CAP,
)
from experiments.router_bench.payload import PAYLOAD_TEMPLATE_SHA256, payload_fingerprint
from experiments.router_bench.routers import (
    FALLBACK_ROUTE,
    HAIKU_WORST_CASE_USD,
    JEV_WORST_CASE_USD,
    RULES_SHA256,
    RouteRecord,
    haiku_cost,
    jev_cost,
    rules_fingerprint,
)
from experiments.router_bench.safety import BudgetExhausted, DownstreamTripwire, Ledger

EXPECTED_COST_PER_CALL = {"bedrock": haiku_cost(*HAIKU_EXPECTED_TOKENS), "typesafe": jev_cost(JEV_EXPECTED_INPUT_TOKENS)}
WORST_CASE_PER_CALL = {"bedrock": HAIKU_WORST_CASE_USD, "typesafe": JEV_WORST_CASE_USD}


@dataclass(frozen=True)
class Call:
    router: str
    case_id: str
    repetition: int  # 0 = warm-up
    warmup: bool = False


@dataclass
class Plan:
    kind: str  # benchmark | jev_verification
    routers: tuple[str, ...]
    allowed_ids: tuple[str, ...]
    categories: dict
    repetitions: int
    warmup_calls: int
    seed: int
    schedule: list[Call]
    request_caps: dict[str, int]
    cost_caps: dict[str, float]
    dataset_version: str = DATASET_VERSION
    fingerprints: dict = field(default_factory=dict)
    planned_calls: dict = field(default_factory=dict)
    cost: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict:
        data = asdict(self)
        data["schedule_length"] = len(self.schedule)
        data["schedule"] = [asdict(c) for c in self.schedule]
        data["feasible"] = self.feasible
        return data


def _categories(cases, allowed_ids) -> dict:
    allowed = [c for c in cases if c.id in set(allowed_ids)]
    groups = {
        "strict_qa": [c.id for c in allowed if c.status == "clear" and c.expected_route == "qa"],
        "strict_summarize": [c.id for c in allowed if c.status == "clear" and c.expected_route == "summarize"],
        "policy": [c.id for c in allowed if c.status == "policy"],
        "exploratory": [c.id for c in allowed if c.status == "excluded"],
    }
    return {name: {"count": len(ids), "ids": ids} for name, ids in groups.items()}


def _finish(plan: Plan) -> Plan:
    per_provider = {"bedrock": 0, "typesafe": 0, "local": 0}
    for call in plan.schedule:
        per_provider[ROUTER_PROVIDERS[call.router] or "local"] += 1
    plan.planned_calls = {**per_provider, "warmup": sum(c.warmup for c in plan.schedule), "total": len(plan.schedule)}
    plan.request_caps = {p: per_provider[p] for p in ("bedrock", "typesafe")}
    expected = {p: round(per_provider[p] * EXPECTED_COST_PER_CALL[p], 6) for p in ("bedrock", "typesafe")}
    theoretical = {p: round(per_provider[p] * WORST_CASE_PER_CALL[p], 6) for p in ("bedrock", "typesafe")}
    plan.cost = {
        "expected_usd": {**expected, "total": round(sum(expected.values()), 6)},
        "worst_case_reservation_per_call_usd": {p: round(v, 6) for p, v in WORST_CASE_PER_CALL.items()},
        "theoretical_all_worst_case_usd": {**theoretical, "total": round(sum(theoretical.values()), 6),
                                           "note": "informational only: each call reserves its worst case "
                                                   "temporarily and is reconciled to recorded usage"},
        "hard_caps_usd": dict(plan.cost_caps),
        "basis": "Haiku 214 in / 52 out tokens per call (measured, baseline 6a13ffb1) at $1/$5 per 1M; "
                 f"Jev {JEV_EXPECTED_INPUT_TOKENS} input tokens per call (assumed) at $0.042 per 1M",
    }
    for provider in ("bedrock", "typesafe"):
        if per_provider[provider] == 0:
            continue
        if expected[provider] > plan.cost_caps[provider]:
            plan.problems.append(f"{provider}: expected ${expected[provider]:.4f} exceeds cap ${plan.cost_caps[provider]:.4f}")
        if WORST_CASE_PER_CALL[provider] > plan.cost_caps[provider]:
            plan.problems.append(f"{provider}: one worst-case call exceeds the cap; nothing could run")
    if plan.cost["expected_usd"]["total"] > plan.cost_caps["total"]:
        plan.problems.append("expected total exceeds the total cap")
    if payload_fingerprint() != PAYLOAD_TEMPLATE_SHA256:
        plan.problems.append("Jev payload template changed since it was frozen (fingerprint mismatch)")
    if rules_fingerprint() != RULES_SHA256:
        plan.problems.append("rules router changed since it was frozen (fingerprint mismatch)")
    plan.fingerprints = {
        "routing_dataset": {"version": plan.dataset_version, "sha256": PINNED_SHA256[plan.dataset_version]},
        "jev_payload_template_sha256": PAYLOAD_TEMPLATE_SHA256,
        "rules_sha256": RULES_SHA256,
    }
    return plan


def build_plan(routers, repetitions: int, warmup_calls: int, seed: int, allowed_ids=None,
               cost_caps: dict | None = None) -> Plan:
    cases = routing_dataset(DATASET_VERSION)  # raises DatasetDriftError if the frozen labels changed
    allowed_ids = tuple(allowed_ids) if allowed_ids is not None else tuple(c.id for c in cases)
    unknown = sorted(set(allowed_ids) - {c.id for c in cases})
    if unknown:
        raise ValueError(f"unknown case IDs: {unknown}")
    allowed = [c.id for c in cases if c.id in set(allowed_ids)]  # dataset order
    routers = tuple(routers)
    rng = random.Random(seed)
    schedule = [Call(r, cid, 0, True) for r in routers if ROUTER_PROVIDERS[r] for cid in allowed[:warmup_calls]]
    for repetition in range(1, repetitions + 1):
        order = list(allowed)
        rng.shuffle(order)
        for cid in order:
            router_order = list(routers)
            rng.shuffle(router_order)
            schedule.extend(Call(r, cid, repetition) for r in router_order)
    plan = Plan("benchmark", routers, tuple(allowed), _categories(cases, allowed), repetitions, warmup_calls, seed,
                schedule, {}, dict(cost_caps or DEFAULT_COST_CAPS))
    return _finish(plan)


def build_verification_plan(repeat_first: bool = False) -> Plan:
    """Design §7: jev only, L01 then L12 (then L01 again if repeat_first). No warm-up."""
    cases = routing_dataset(DATASET_VERSION)
    ids = list(VERIFICATION_CASE_IDS) + ([VERIFICATION_CASE_IDS[0]] if repeat_first else [])
    schedule = [Call("jev", cid, i + 1) for i, cid in enumerate(ids)]
    caps = {"bedrock": 0.0, "typesafe": VERIFICATION_COST_CAP, "total": VERIFICATION_COST_CAP}
    plan = Plan("jev_verification", ("jev",), tuple(VERIFICATION_CASE_IDS), _categories(cases, VERIFICATION_CASE_IDS),
                len(ids), 0, 0, schedule, {}, caps)
    return _finish(plan)


def run(plan: Plan, routers: dict, *, sleep=time.sleep, clock=time.monotonic, pace: bool = True) -> dict:
    """Execute the schedule. Stops the whole run on budget exhaustion, a harness error or a
    call that cost more than its reservation; stops one router after consecutive infra errors."""
    if not plan.feasible:
        raise ValueError(f"plan is not feasible: {plan.problems}")
    cases = {c.id: c for c in routing_dataset(plan.dataset_version)}
    ledger = Ledger(plan.request_caps, plan.cost_caps)
    records: list[RouteRecord] = []
    stop_reason = None
    state = {r: {"consecutive_infra_errors": 0, "stopped": None} for r in plan.routers}
    last_typesafe = None
    with DownstreamTripwire() as tripwire:
        for call in plan.schedule:
            if state[call.router]["stopped"]:
                continue
            router = routers[call.router]
            provider = router.provider
            reservation = None
            if provider:
                try:
                    reservation = ledger.reserve(provider, router.worst_case_usd)
                except BudgetExhausted as exc:
                    stop_reason = f"budget exhausted: {exc}"
                    break
            if provider == "typesafe" and pace and last_typesafe is not None:
                wait = JEV_MIN_SECONDS_BETWEEN_CALLS - (clock() - last_typesafe)
                if wait > 0:
                    sleep(wait)
            harness_error = None
            try:
                record = router.route(cases[call.case_id])
            except Exception as exc:  # a harness defect (or a downstream tripwire): record it, then stop
                harness_error = type(exc).__name__
                record = RouteRecord(router=call.router, case_id=call.case_id, raw_label=None, raw_score=None,
                                     final_label=FALLBACK_ROUTE, outcome="fallback_harness_error", latency_ms=0.0,
                                     error_class=harness_error)
            if provider == "typesafe":
                last_typesafe = clock()
            record.repetition, record.warmup = call.repetition, call.warmup
            if reservation is not None:
                usage_known = record.cost_basis == "usage"
                charged, exceeded = ledger.settle(reservation, record.cost_usd if usage_known else None)
                record.cost_usd = round(charged, 8)
                record.cost_basis = "usage" if usage_known else "worst_case_reservation"
                if exceeded:
                    stop_reason = f"{call.router}: a call cost more than its worst-case reservation"
            records.append(record)
            if harness_error:
                stop_reason = f"harness error in {call.router} on {call.case_id}: {harness_error}"
            if stop_reason:
                break
            if record.infra_error:
                state[call.router]["consecutive_infra_errors"] += 1
                if state[call.router]["consecutive_infra_errors"] >= CONSECUTIVE_INFRA_ERROR_LIMIT:
                    state[call.router]["stopped"] = f"{CONSECUTIVE_INFRA_ERROR_LIMIT} consecutive infrastructure errors"
            else:
                state[call.router]["consecutive_infra_errors"] = 0
    downstream = tripwire.report()
    complete = stop_reason is None and len(records) == len(plan.schedule)
    reasons = []
    if stop_reason:
        reasons.append(stop_reason)
    if len(records) < len(plan.schedule):
        reasons.append(f"incomplete: {len(records)}/{len(plan.schedule)} scheduled calls executed")
    if not downstream["clean"]:
        reasons.append("downstream QA/summarization/retrieval code was touched")
    reasons += [f"{r} stopped: {s['stopped']}" for r, s in state.items() if s["stopped"]]
    return {
        "records": [r.to_dict() for r in records],
        "complete": complete,
        "valid": complete and downstream["clean"] and not any(s["stopped"] for s in state.values()),
        "invalid_reasons": reasons,
        "router_state": state,
        "ledger": ledger.summary(),
        "downstream": downstream,
        "executed_calls": len(records),
        "scheduled_calls": len(plan.schedule),
    }
