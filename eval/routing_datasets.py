"""Versioned routing-label datasets and routing scores for router benchmarks.

Routing labels only. The eval harness keeps using `eval/eval_queries.py`
unchanged, so its enforced-gate population (19 cases) and every archived result
keep their original labels. Each version is frozen by a pinned SHA-256; changing
a query or label means creating a new version, never editing one.

- v1: the labels used by the Phase 0 baseline (run 6a13ffb1), derived from
  eval/eval_queries.py. 30 clear (23 qa, 7 summarize); L13, L17, L19 and L20
  excluded (needs review).
- v2 (approved 2026-09-28): L13 relabelled to clear qa. L19 falls under the
  experimental policy "unclear query -> qa", scored as policy compliance and not
  as accuracy. L17 and L20 stay excluded. 31 clear (24 qa, 7 summarize).
"""
import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from typing import Literal

from eval.eval_queries import EVAL_CASES

Route = Literal["qa", "summarize"]
Status = Literal["clear", "policy", "excluded"]

# Experimental policy (v2): a query too unclear to classify should take the grounded
# QA path. It describes the desired final decision only; production routing is unchanged.
UNCLEAR_DEFAULTS_TO_QA = "unclear_defaults_to_qa"


@dataclass(frozen=True)
class RoutingCase:
    id: str
    query: str
    status: Status
    # clear: the label. policy: the route the policy requires. excluded: the
    # historical label, kept for reference and never scored.
    expected_route: Route
    policy: str | None = None
    note: str = ""


def _v1() -> tuple[RoutingCase, ...]:
    return tuple(
        RoutingCase(c.id, c.query, "clear" if c.route_label_status == "clear" else "excluded", c.expected_route,
                    note="" if c.route_label_status == "clear" else "needs review (historical label, not scored)")
        for c in EVAL_CASES
    )


_V2_CHANGES = {
    "L13": dict(status="clear", expected_route="qa",
                note="Relabelled summarize -> qa (approved 2026-09-28): the named segments are a specific, "
                     "verifiable fact."),
    "L17": dict(note="Excluded: a general definition; neither class fits the taxonomy."),
    "L19": dict(status="policy", expected_route="qa", policy=UNCLEAR_DEFAULTS_TO_QA,
                note="Unclear query; scored as compliance with the experimental policy, not as accuracy."),
    "L20": dict(note="Excluded: two intents; the two-class taxonomy cannot express both."),
}


def _v2() -> tuple[RoutingCase, ...]:
    return tuple(replace(case, **_V2_CHANGES[case.id]) if case.id in _V2_CHANGES else case for case in _v1())


def fingerprint(cases) -> str:
    """SHA-256 over every field of every case, in order."""
    payload = json.dumps([asdict(case) for case in cases], sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_BUILDERS = {"v1": _v1, "v2": _v2}
PINNED_SHA256 = {
    "v1": "f9011fd94ed18d430afd6da2f32082d1fef1a6f0fa3029b688ce55ab36a5312d",
    "v2": "9d4f2da1393b3ddd42728740d5c8c08e9ccc0051edc7ae0746260cb456cc5e5d",
}


class DatasetDriftError(RuntimeError):
    """A routing dataset no longer matches its pinned fingerprint."""


def routing_dataset(version: str) -> tuple[RoutingCase, ...]:
    """The frozen cases of a version; raises DatasetDriftError if they changed."""
    cases = _BUILDERS[version]()
    actual = fingerprint(cases)
    if actual != PINNED_SHA256[version]:
        raise DatasetDriftError(f"routing dataset {version} changed (sha256 {actual[:12]}...); "
                                "create a new version instead of editing a frozen one")
    return cases


def wilson_interval(successes: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    """95% Wilson score interval for a proportion; None when n == 0."""
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def _rate(successes: int, n: int) -> dict:
    return {"passed": successes, "n": n, "rate": successes / n if n else None, "wilson_95": wilson_interval(successes, n)}


def score_routing(decisions: dict[str, str], cases) -> dict:
    """Score one set of routing decisions (case id -> 'qa' | 'summarize') against a dataset.

    Strict accuracy uses clear cases only. Policy cases are reported as policy
    compliance, and excluded cases as raw predictions; neither enters accuracy.
    A clear case with no decision counts as wrong.
    """
    clear = [c for c in cases if c.status == "clear"]
    correct = {c.id: decisions.get(c.id) == c.expected_route for c in clear}
    confusion: dict[str, int] = {}
    for c in clear:
        key = f"{c.expected_route}->{decisions.get(c.id, 'missing')}"
        confusion[key] = confusion.get(key, 0) + 1
    recall = {}
    for route in ("qa", "summarize"):
        members = [c for c in clear if c.expected_route == route]
        recall[route] = _rate(sum(correct[c.id] for c in members), len(members))
    policies: dict[str, dict] = {}
    for c in (c for c in cases if c.status == "policy"):
        entry = policies.setdefault(c.policy, {"cases": {}, "complied": 0, "n": 0})
        complied = decisions.get(c.id) == c.expected_route
        entry["cases"][c.id] = {"decision": decisions.get(c.id), "required": c.expected_route, "complied": complied}
        entry["complied"] += complied
        entry["n"] += 1
    return {
        "strict_accuracy": _rate(sum(correct.values()), len(clear)),
        "recall": recall,
        "confusion": confusion,
        "errors": sorted(i for i, ok in correct.items() if not ok),
        "policy_compliance": policies,
        "excluded_predictions": {c.id: decisions.get(c.id) for c in cases if c.status == "excluded"},
    }
