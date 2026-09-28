"""Model pinning, Haiku reservation modes, failure costing and the budget guarantee. Offline only."""
import random
import sys

import pytest
from botocore.exceptions import EndpointConnectionError, ReadTimeoutError

from eval.routing_datasets import routing_dataset
from experiments.router_bench import safety
from experiments.router_bench.config import HAIKU_MODEL_ID
from experiments.router_bench.fakes import FakeBedrock as SimulatedBedrock
from experiments.router_bench.routers import (
    HAIKU_MAX_CALL_USD,
    HaikuRouter,
    ModelNotPinned,
    RulesRouter,
    haiku_reservation_usd,
)
from experiments.router_bench.runner import build_plan, run
from tests.conftest import FakeBedrock, aws_error, converse_text

V2 = routing_dataset("v2")
LABELS = {c.query: c.expected_route for c in V2}
OTHER_MODEL = "us.anthropic.claude-sonnet-4-6"


class Scripted(safety.OfflineFakeClient, FakeBedrock):
    pass


# --- Model pinning (audit finding 2) -------------------------------------------------------------------

def test_a_different_configured_model_is_refused_before_any_client_or_import(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", OTHER_MODEL)
    monkeypatch.delitem(sys.modules, "app.agents.router")
    with pytest.raises(ModelNotPinned, match="pinned Haiku 4.5"):
        HaikuRouter(bedrock_client=SimulatedBedrock(LABELS, 1))
    auth = safety.LiveAuthorization({"bedrock"}, allow_under_pytest=True)
    with pytest.raises(ModelNotPinned):
        HaikuRouter(authorization=auth)
    assert "app.agents.router" not in sys.modules


def test_a_call_that_used_another_model_stops_the_run():
    router = HaikuRouter(bedrock_client=SimulatedBedrock(LABELS, 1))
    router.agent._model_id = OTHER_MODEL  # e.g. something changed the agent after construction
    with pytest.raises(ModelNotPinned):
        router.route(V2[0])
    plan = build_plan(("haiku",), 1, 0, 1)
    result = run(plan, {"haiku": router}, pace=False)
    assert result["executed_calls"] == 1 and not result["valid"]
    assert result["records"][0]["error_class"] == "ModelNotPinned"
    assert result["records"][0]["cost_basis"] == "worst_case_reservation"  # the call happened; charge it all


def test_the_cli_refuses_a_mismatched_model(monkeypatch, capsys):
    from experiments.router_bench import cli
    from experiments.router_bench.payload import ApprovedQuestions

    monkeypatch.setenv("BEDROCK_MODEL_ID", OTHER_MODEL)
    plan = build_plan(("haiku",), 1, 0, 1)
    impl, _ = cli._build_routers(plan, V2, ApprovedQuestions(V2, plan.allowed_ids), frozenset(),
                                 safety.LiveAuthorization)
    assert impl is None and "Refusing" in capsys.readouterr().err


def test_live_haiku_client_never_retries(monkeypatch):
    monkeypatch.setenv("AWS_MAX_ATTEMPTS", "5")
    router = HaikuRouter(authorization=safety.LiveAuthorization({"bedrock"}, allow_under_pytest=True))
    assert router.agent._client.meta.config.retries["total_max_attempts"] == 1
    assert router.model_id == HAIKU_MODEL_ID


# --- Failed calls: charged only when they could have been billed ---------------------------------------

@pytest.mark.parametrize("error, basis", [
    (aws_error("ThrottlingException", status=429), "rejected_assumed_unbilled"),
    (aws_error("AccessDeniedException", status=403), "rejected_assumed_unbilled"),
    (EndpointConnectionError(endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com"), "not_sent"),
    (ReadTimeoutError(endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com"), "worst_case_reservation"),
    (aws_error("ModelErrorException", status=424), "worst_case_reservation"),
    (aws_error("InternalServerException", status=500), "worst_case_reservation"),
])
def test_failed_haiku_calls_are_costed_by_whether_they_could_have_been_billed(error, basis):
    plan = build_plan(("haiku",), 1, 0, 1, allowed_ids=["L01"])
    result = run(plan, {"haiku": HaikuRouter(bedrock_client=Scripted(converse_responses=[error]))}, pace=False)
    record = result["records"][0]
    assert record["cost_basis"] == basis
    expected = haiku_reservation_usd("strict") if basis == "worst_case_reservation" else 0.0
    assert record["cost_usd"] == pytest.approx(expected)


# --- Budget guarantee (audit finding 3) ----------------------------------------------------------------

def test_strict_reservation_is_a_hard_cap():
    rng = random.Random(0)
    ledger = safety.Ledger({"bedrock": 10_000, "typesafe": 0}, {"bedrock": 0.5, "typesafe": 0.0, "total": 1.0})
    reserve = haiku_reservation_usd("strict")
    assert reserve == pytest.approx(HAIKU_MAX_CALL_USD)
    with pytest.raises(safety.BudgetExhausted):
        while True:  # any actual cost up to the largest possible call, including the largest itself
            actual = rng.choice([HAIKU_MAX_CALL_USD, rng.uniform(0, HAIKU_MAX_CALL_USD), 0.0005])
            ledger.settle(ledger.reserve("bedrock", reserve), actual)
            assert ledger.accounts["bedrock"].committed_usd <= 0.5 + 1e-12


def test_practical_reservation_overshoot_is_bounded_and_disclosed():
    plan = build_plan(("haiku",), 10, 3, 1, haiku_reservation="practical")
    guarantee = plan.cost["budget_guarantee"]["bedrock"]
    assert guarantee["hard_cap"] is False
    assert guarantee["max_overshoot_usd"] == pytest.approx(HAIKU_MAX_CALL_USD - haiku_reservation_usd("practical"),
                                                           abs=1e-6)
    ledger = safety.Ledger({"bedrock": 10, "typesafe": 0}, {"bedrock": 0.5, "typesafe": 0.0, "total": 1.0})
    ledger.settle(ledger.reserve("bedrock", 0.007), 0.49)
    _, exceeded = ledger.settle(ledger.reserve("bedrock", 0.007), HAIKU_MAX_CALL_USD)  # a runaway call
    overshoot = ledger.accounts["bedrock"].committed_usd - 0.5
    assert exceeded and 0 < overshoot <= guarantee["max_overshoot_usd"] + 1e-9


def test_default_plan_is_a_hard_cap_and_reports_its_headroom():
    plan = build_plan(("haiku", "rules", "jev"), 10, 3, 1)
    assert plan.haiku_reservation == "strict" and plan.feasible, plan.problems
    for provider in ("bedrock", "typesafe"):
        g = plan.cost["budget_guarantee"][provider]
        assert g["hard_cap"] is True and g["max_overshoot_usd"] == 0.0
    assert plan.cost["budget_guarantee"]["bedrock"]["headroom_usd"] == pytest.approx(0.5 - 0.162582 - 0.322, abs=1e-5)


def test_a_cap_too_tight_to_finish_is_refused_up_front():
    plan = build_plan(("haiku",), 10, 3, 1, cost_caps={"bedrock": 0.45, "typesafe": 0.05, "total": 1.0})
    assert any("stop early" in p for p in plan.problems)


def test_router_and_plan_must_agree_on_the_reservation():
    plan = build_plan(("haiku",), 1, 0, 1, haiku_reservation="strict")
    practical = HaikuRouter(bedrock_client=SimulatedBedrock(LABELS, 1), reservation="practical")
    with pytest.raises(ValueError, match="different worst case"):
        run(plan, {"haiku": practical}, pace=False)

    class Disguised(RulesRouter):
        provider = None

    jev_plan = build_plan(("jev",), 1, 0, 1)
    with pytest.raises(ValueError, match="provider"):
        run(jev_plan, {"jev": Disguised()}, pace=False)  # a paid router cannot skip the ledger


def test_dry_run_prints_the_budget_guarantee(tmp_path, capsys):
    from experiments.router_bench import cli

    assert cli.main(["--repetitions", "1"]) == 0
    out = capsys.readouterr().out
    assert "Budget guarantee, bedrock: hard cap" in out and "Budget guarantee, typesafe: hard cap" in out
    assert cli.main(["--repetitions", "1", "--haiku-reservation", "practical"]) == 0
    assert "NOT a hard cap: one call may overshoot the ceiling by up to $0.315" in capsys.readouterr().out


def test_a_runaway_call_under_strict_reservation_is_still_detected():
    plan = build_plan(("haiku",), 1, 0, 1)
    runaway = Scripted(converse_responses=[
        converse_text('{"task_type": "qa", "confidence": 0.9, "reasoning": "r"}', 200, 70_000)])
    result = run(plan, {"haiku": HaikuRouter(bedrock_client=runaway)}, pace=False)
    assert "cost more than its worst-case reservation" in result["invalid_reasons"][0]
