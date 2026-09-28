"""Router benchmark safety: authorization, budgets, network, artifacts, isolation, CLI. Offline only.

No test here can reach Bedrock or TypeSafe: the offline guard blocks all non-loopback
network, fakes and httpx.MockTransport stand in for the providers, LiveAuthorization
refuses inside pytest, and child processes get an unreachable proxy as a second barrier.
"""
import os

import httpx
import pytest

from eval.routing_datasets import routing_dataset
from experiments.router_bench import safety
from experiments.router_bench.config import JEV_ENDPOINT, JEV_MODEL
from experiments.router_bench.fakes import FakeBedrock as SimulatedBedrock
from experiments.router_bench.fakes import FakeTypeSafe
from experiments.router_bench.payload import ApprovedQuestions
from experiments.router_bench.routers import (
    HaikuRouter,
    JevClient,
    JevRouter,
    RulesRouter,
)
from experiments.router_bench.runner import build_plan, run
from tests import offline_guard

V2 = routing_dataset("v2")
LABELS = {c.query: c.expected_route for c in V2}
CANARY = "ts-canary-5e1d-not-a-real-key"


def _routers(plan, jev_handler=None, bedrock=None):
    approved = ApprovedQuestions(V2, plan.allowed_ids)
    transport = httpx.MockTransport(jev_handler) if jev_handler else FakeTypeSafe(LABELS, 7).transport()
    return {"haiku": HaikuRouter(bedrock_client=bedrock or SimulatedBedrock(LABELS, 5)),
            "rules": RulesRouter(),
            "jev": JevRouter(JevClient(transport=transport), approved)}


def _ok_body(input_tokens=180):
    return {"model": JEV_MODEL, "answers": {"route": {"choice": "qa", "probabilities": {"qa": 0.9, "summarize": 0.1},
                                                      "confidence": 0.8}},
            "usage": {"input_tokens": input_tokens, "output_tokens": 1}}


# --- Live authorization ---------------------------------------------------------------------------

def test_live_authorization_is_refused_inside_pytest():
    with pytest.raises(safety.LiveCallNotAuthorized, match="inside pytest"):
        safety.LiveAuthorization({"typesafe"})


def test_real_clients_need_a_provider_specific_authorization():
    with pytest.raises(safety.LiveCallNotAuthorized, match="dry run is the default"):
        JevClient()
    bedrock_only = safety.LiveAuthorization({"bedrock"}, allow_under_pytest=True)
    with pytest.raises(safety.LiveCallNotAuthorized, match="typesafe"):
        JevClient(authorization=bedrock_only, api_key=safety.SecretValue(CANARY))
    with pytest.raises(safety.LiveCallNotAuthorized):
        HaikuRouter()


def test_even_an_authorized_jev_client_cannot_reach_typesafe_under_pytest():
    auth = safety.LiveAuthorization({"typesafe"}, allow_under_pytest=True)
    router = JevRouter(JevClient(authorization=auth, api_key=safety.SecretValue(CANARY)), ApprovedQuestions(V2, ["L01"]))
    before = len(offline_guard.blocked_requests)
    record = router.route(next(c for c in V2 if c.id == "L01"))
    assert (record.outcome, record.error_class) == ("fallback_invoke_error", "transport:NetworkBlockedError")
    assert offline_guard.blocked_requests[before:] == [JEV_ENDPOINT]
    assert all(CANARY not in entry for entry in offline_guard.blocked_requests)


def test_even_an_authorized_haiku_router_cannot_reach_bedrock_under_pytest():
    router = HaikuRouter(authorization=safety.LiveAuthorization({"bedrock"}, allow_under_pytest=True))
    record = router.route(V2[0])
    assert (record.outcome, record.error_class) == ("fallback_invoke_error", "NetworkBlockedError")


def test_fake_clients_resolve_no_credentials(monkeypatch):
    import botocore.session

    def forbidden(*args, **kwargs):
        raise AssertionError("credentials resolved")

    monkeypatch.setattr(botocore.session.Session, "get_credentials", forbidden)
    HaikuRouter(bedrock_client=SimulatedBedrock(LABELS, 1)).route(V2[0])


# --- Budgets: reservation, reconciliation, failure, exhaustion ------------------------------------

def _ledger(requests=10, bedrock=0.05, typesafe=0.01, total=1.0):
    return safety.Ledger({"bedrock": requests, "typesafe": requests},
                         {"bedrock": bedrock, "typesafe": typesafe, "total": total})


def test_worst_case_is_reserved_then_reconciled_to_actual_usage():
    ledger = _ledger()
    reservation = ledger.reserve("bedrock", 0.007)
    assert ledger.accounts["bedrock"].reserved_usd == pytest.approx(0.007)
    charged, exceeded = ledger.settle(reservation, 0.0005)
    account = ledger.accounts["bedrock"]
    assert (charged, exceeded) == (0.0005, False)
    assert (account.reserved_usd, account.committed_usd, account.requests) == (pytest.approx(0), 0.0005, 1)


def test_failed_calls_are_charged_at_worst_case():
    ledger = _ledger()
    charged, _ = ledger.settle(ledger.reserve("typesafe", 0.002688), None)
    assert charged == 0.002688
    assert ledger.accounts["typesafe"].worst_case_charges == 1


def test_request_cap_and_cost_cap_are_independent():
    by_count = _ledger(requests=2)
    for _ in range(2):
        by_count.settle(by_count.reserve("bedrock", 0.001), 0.0001)
    with pytest.raises(safety.BudgetExhausted, match="request cap 2"):
        by_count.reserve("bedrock", 0.001)
    by_cost = _ledger(requests=100, typesafe=0.005)
    by_cost.settle(by_cost.reserve("typesafe", 0.002688), 0.003)
    with pytest.raises(safety.BudgetExhausted, match="cost cap"):  # 0.003 + worst case 0.002688 > 0.005
        by_cost.reserve("typesafe", 0.002688)
    total = _ledger(requests=100, bedrock=1, typesafe=1, total=0.01)
    total.settle(total.reserve("bedrock", 0.007), 0.007)
    with pytest.raises(safety.BudgetExhausted, match="total cost cap"):
        total.reserve("typesafe", 0.004)


def test_theoretical_worst_case_total_does_not_block_a_plan_or_a_run():
    plan = build_plan(("haiku", "rules", "jev"), repetitions=10, warmup_calls=3, seed=3)
    theoretical = plan.cost["theoretical_all_worst_case_usd"]
    assert theoretical["typesafe"] > plan.cost_caps["typesafe"]  # 343 x $0.002688 = $0.92 > $0.05
    assert theoretical["bedrock"] > plan.cost_caps["bedrock"]  # 343 x $0.322 = $110 > $0.60
    assert plan.feasible, plan.problems
    result = run(plan, _routers(plan), pace=False)
    assert result["complete"] and result["executed_calls"] == 1026
    assert result["ledger"]["providers"]["typesafe"]["committed_usd"] < plan.cost_caps["typesafe"]


def test_plans_that_cannot_fit_are_refused():
    too_expensive = build_plan(("haiku",), 10, 3, 1, cost_caps={"bedrock": 0.05, "typesafe": 0.05, "total": 1.0})
    assert not too_expensive.feasible and "expected" in too_expensive.problems[0]
    one_call_too_big = build_plan(("jev",), 1, 0, 1, cost_caps={"bedrock": 0.5, "typesafe": 0.001, "total": 1.0})
    assert any("one worst-case call" in p for p in one_call_too_big.problems)
    with pytest.raises(ValueError, match="not feasible"):
        run(one_call_too_big, _routers(one_call_too_big))


def test_budget_exhaustion_stops_the_run_and_keeps_partial_results(tmp_path):
    plan = build_plan(("jev",), 1, 0, 1, cost_caps={"bedrock": 0.5, "typesafe": 0.01, "total": 1.0})
    result = run(plan, _routers(plan, jev_handler=lambda req: httpx.Response(200, json=_ok_body(60_000))), pace=False)
    assert not result["complete"] and not result["valid"]
    assert result["executed_calls"] == 3  # 3 x $0.00252 committed; a 4th worst-case reservation would exceed $0.01
    assert any(r.startswith("budget exhausted: typesafe: cost cap") for r in result["invalid_reasons"])
    assert result["ledger"]["providers"]["typesafe"]["committed_usd"] <= 0.01
    assert len(result["records"]) == 3


def test_a_call_costing_more_than_its_reservation_stops_the_run():
    from tests.conftest import FakeBedrock, converse_text

    class Scripted(safety.OfflineFakeClient, FakeBedrock):
        pass

    plan = build_plan(("haiku",), 1, 0, 1)
    runaway = Scripted(converse_responses=[
        converse_text('{"task_type": "qa", "confidence": 0.9, "reasoning": "r"}', 200, 70_000)])  # > 64k max
    result = run(plan, _routers(plan, bedrock=runaway), pace=False)
    assert result["executed_calls"] == 1 and not result["valid"]
    assert "cost more than its worst-case reservation" in result["invalid_reasons"][0]
    assert result["ledger"]["providers"]["bedrock"]["reservations_exceeded"] == 1


def test_consecutive_infrastructure_errors_stop_only_that_router():
    plan = build_plan(("rules", "jev"), 1, 0, 1)
    result = run(plan, _routers(plan, jev_handler=lambda req: httpx.Response(529)), pace=False)
    jev = [r for r in result["records"] if r["router"] == "jev"]
    rules = [r for r in result["records"] if r["router"] == "rules"]
    assert len(jev) == 3 and all(r["cost_basis"] == "worst_case_reservation" for r in jev)
    assert len(rules) == 34
    assert result["router_state"]["jev"]["stopped"] == "3 consecutive infrastructure errors"
    assert not result["valid"]


def test_a_harness_error_stops_the_run_with_a_record():
    class Broken(RulesRouter):
        def route(self, case):
            raise KeyError("bug")

    plan = build_plan(("rules",), 1, 0, 1)
    result = run(plan, {"rules": Broken()}, pace=False)
    assert result["executed_calls"] == 1
    assert result["records"][0]["outcome"] == "fallback_harness_error"
    assert "harness error" in result["invalid_reasons"][0]


def test_jev_calls_are_paced_in_live_runs():
    plan = build_plan(("jev",), 1, 0, 1, allowed_ids=["L01", "L12", "N01"])
    sleeps, now = [], [0.0]
    result = run(plan, _routers(plan), sleep=sleeps.append, clock=lambda: now[0], pace=True)
    assert result["complete"] and sleeps == [pytest.approx(1.0), pytest.approx(1.0)]


# --- Downstream isolation ---------------------------------------------------------------------------

def test_tripwire_catches_downstream_calls_even_for_preloaded_modules():
    import app.agents.qa_agent as qa_agent

    class Sneaky(RulesRouter):
        def route(self, case):
            qa_agent.QAAgent.run(None, case.query)

    plan = build_plan(("rules",), 1, 0, 1)
    result = run(plan, {"rules": Sneaky()}, pace=False)
    assert not result["downstream"]["clean"]
    assert result["downstream"]["downstream_calls"] == ["app.agents.qa_agent.QAAgent.run"]
    assert "downstream" in " ".join(result["invalid_reasons"])
    assert qa_agent.QAAgent.run.__name__ == "run"  # restored after the run


def test_a_normal_run_touches_no_downstream_code():
    plan = build_plan(("haiku", "rules", "jev"), 1, 1, 2)
    result = run(plan, _routers(plan), pace=False)
    assert result["downstream"]["clean"] and result["downstream"]["downstream_calls"] == []


# --- Artifacts: no keys, headers, documents or chunks ------------------------------------------------

@pytest.mark.parametrize("artifact, reason", [
    ({"records": [{"headers": {"x": "y"}}]}, "forbidden key"),
    ({"row": {"retrieved_chunks": []}}, "forbidden key"),
    ({"note": "JPMorgan Chase ... " * 60}, "document text"),
    ({"note": f"key={CANARY}"}, "secret"),
    ({"note": "Bearer abc"}, "authorization header"),
])
def test_artifact_safety_check_refuses_sensitive_content(artifact, reason):
    safety.SecretValue(CANARY)
    with pytest.raises(safety.ArtifactSafetyError, match=reason):
        safety.assert_safe_for_output(artifact, what="test")


def test_secret_values_cannot_be_serialized():
    import pickle

    with pytest.raises(TypeError):
        pickle.dumps(safety.SecretValue(CANARY))


# --- Injected clients cannot bypass live authorization (audit finding 1) -----------------------------

def test_an_injected_real_bedrock_client_is_refused():
    import boto3
    from unittest import mock

    real = boto3.client("bedrock-runtime", region_name="us-east-1")  # built offline; never called
    for injected in (real, mock.MagicMock(), object()):
        with pytest.raises(safety.LiveCallNotAuthorized, match="OfflineFakeClient"):
            HaikuRouter(bedrock_client=injected)


def test_an_injected_real_transport_is_refused():
    class CustomTransport(httpx.BaseTransport):
        def handle_request(self, request):
            raise AssertionError("must never be used")

    for transport in (httpx.HTTPTransport(), CustomTransport()):
        with pytest.raises(safety.LiveCallNotAuthorized, match="MockTransport"):
            JevClient(transport=transport, api_key=safety.SecretValue(CANARY))
    with pytest.raises(TypeError, match="SecretValue"):
        JevClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)), api_key=CANARY)


def test_authorization_is_checked_before_app_code_is_imported(monkeypatch):
    import sys

    monkeypatch.delitem(sys.modules, "app.agents.router")
    with pytest.raises(safety.LiveCallNotAuthorized):
        HaikuRouter()
    with pytest.raises(safety.LiveCallNotAuthorized):
        HaikuRouter(bedrock_client=object())
    assert "app.agents.router" not in sys.modules  # not imported, so its load_dotenv() never ran


def test_router_agent_is_imported_with_dotenv_disabled(monkeypatch):
    import sys

    import dotenv

    seen = []
    monkeypatch.delitem(sys.modules, "app.agents.router")
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: seen.append(os.environ.get("PYTHON_DOTENV_DISABLED")))
    HaikuRouter(bedrock_client=SimulatedBedrock(LABELS, 1))
    assert seen == ["1"]  # the module-level load_dotenv() ran with loading disabled
    assert "PYTHON_DOTENV_DISABLED" not in os.environ  # and the setting was restored afterwards


# --- Credential exposure (audit findings 7 and 8) ---------------------------------------------------

def test_live_runs_read_only_the_keys_their_providers_need(tmp_path, monkeypatch):
    from experiments.router_bench import cli

    env_file = tmp_path / ".env"
    env_file.write_text("AWS_ACCESS_KEY_ID=file-aws-canary\nAWS_SECRET_ACCESS_KEY=file-secret-canary\n"
                        "TYPESAFE_API_KEY=file-ts-canary\nOTHER_SECRET=file-other-canary\n", encoding="utf-8")
    typesafe_only = cli.read_env_file(cli.PROVIDER_ENV_NAMES["typesafe"], path=str(env_file))
    assert typesafe_only == {"TYPESAFE_API_KEY": "file-ts-canary"}
    key = cli.load_typesafe_key(typesafe_only)
    assert key.reveal() == "file-ts-canary" and "file-ts-canary" not in repr(key)
    assert "TYPESAFE_API_KEY" not in os.environ  # never exported
    bedrock_only = cli.read_env_file(cli.PROVIDER_ENV_NAMES["bedrock"], path=str(env_file))
    assert set(bedrock_only) == {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"}
    monkeypatch.delenv("AWS_ACCESS_KEY_ID")
    cli.export_bedrock_env(bedrock_only)
    assert os.environ["AWS_ACCESS_KEY_ID"] == "file-aws-canary"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "unit-test-fake-secret"  # existing values win
    assert "OTHER_SECRET" not in os.environ and "TYPESAFE_API_KEY" not in os.environ


def test_the_cli_never_loads_the_whole_dotenv_file():
    import inspect

    from experiments.router_bench import cli

    assert "load_dotenv" not in inspect.getsource(cli)


def test_server_controlled_text_never_reaches_records_or_artifacts():
    safety.SecretValue(CANARY)
    hostile = "<script>alert(1)</script> Bearer stolen " + "x" * 700
    body = {"model": hostile, "answers": {"route": {"choice": "qa"}}, "usage": {}}
    record = JevRouter(JevClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))),
                       ApprovedQuestions(V2, ["L01"])).route(V2[0])
    assert record.error_class == "schema:model_mismatch"
    ok_body = {**_ok_body(), hostile[:30]: 1, "headers": 2, **{f"f{i}": i for i in range(30)}}
    headers = [(b"x-request-id", f"id-{CANARY}".encode()), (b"x-ratelimit-remaining", b"\xe9\xe9"), (b"date", b"Mon")]
    record_ok = JevRouter(JevClient(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, headers=headers, json=ok_body))), ApprovedQuestions(V2, ["L01"])).route(V2[0])
    assert "<redacted>" in record_ok.extra["extra_fields"] and len(record_ok.extra["extra_fields"]) <= 21
    assert record_ok.extra["response_headers"]["x-request-id"] == "<redacted>"
    assert record_ok.extra["response_headers"]["x-ratelimit-remaining"] == "<redacted>"
    for r in (record, record_ok):
        text = safety.assert_safe_for_output(r.to_dict(), what="record")
        assert "script" not in text and "stolen" not in text and CANARY not in text
