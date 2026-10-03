"""Invented HTTP and agent fixtures only; no heldout content or provider calls."""

import copy
import json
import os
import subprocess
import sys

import httpx
import pytest

from app.agents import jev_router as j
from app.agents.router_configuration import RouterConfiguration, build_router
from app.agents.routing_contract import RouterDecision
from app.errors import ServiceFailure
from app.observability import request_trace
from experiments.router_bench.payload import payload_template
from experiments.router_bench.routers import JevSchemaError, validate_jev_response


def body(choice="summarize", score=0.9):
    return {
        "model": j.MODEL,
        "answers": {
            "route": {
                "choice": choice,
                "confidence": 0.7,
                "probabilities": {
                    choice: score,
                    ("qa" if choice == "summarize" else "summarize"): 1 - score,
                },
            }
        },
        "usage": {"input_tokens": 410, "output_tokens": 35},
    }


def call(response=None, *, failure=None, status=200):
    requests = []

    def handler(request):
        requests.append(request)
        if failure:
            raise failure
        return httpx.Response(status, json=response)

    agent = j.JevRouterAgent(transport=httpx.MockTransport(handler))
    with request_trace("synthetic", "invented confidential query") as trace:
        decision = agent.route("invented confidential query")
    agent.close()
    return decision, trace.to_record(), requests


@pytest.mark.parametrize("choice", ["qa", "summarize"])
def test_valid_route_payload_usage_and_privacy(choice):
    decision, trace, requests = call(body(choice))
    assert decision.task_type == choice
    assert decision.confidence == 0.9
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == j.ENDPOINT
    assert "authorization" not in request.headers
    expected = payload_template()
    expected["state"] = "invented confidential query"
    assert json.loads(request.content) == expected
    assert request.extensions["timeout"] == {
        "connect": 2.0,
        "read": 5.0,
        "write": 5.0,
        "pool": 5.0,
    }
    assert trace["route"]["router_cost_usd"] == pytest.approx(0.00001722)
    assert trace["model_calls"][0]["input_tokens"] == 410
    assert trace["route"]["router_attempts"] == 1
    assert trace["route"]["router_live"] is False
    assert "confidential" not in json.dumps(trace)


@pytest.mark.parametrize(
    "score,expected", [(0.5, "qa"), (0.59, "qa"), (0.6, "summarize")]
)
def test_threshold_uses_choice_probability_not_confidence(score, expected):
    value = body(score=score)
    value["answers"]["route"]["confidence"] = 1.0
    decision, trace, requests = call(value)
    assert decision.task_type == expected and len(requests) == 1
    assert trace["route"]["model_confidence"] == score
    assert trace["route"]["router_outcome"] == (
        "model" if score >= 0.6 else "fallback_low_confidence"
    )


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("object", "not_object"),
        ("model", "model_mismatch"),
        ("answers", "answers_missing"),
        ("choice", "bad_choice"),
        ("keys", "bad_probability_keys"),
        ("value", "bad_probability_values"),
        ("sum", "probabilities_do_not_sum_to_1"),
        ("argmax", "choice_not_argmax"),
        ("confidence", "bad_confidence"),
        ("usage", "usage_missing"),
        ("input", "bad_input_tokens"),
        ("output", "bad_output_tokens"),
    ],
)
def test_schema_parity_and_sanitized_fallback(mutation, code):
    value = body()
    answer = value["answers"]["route"]
    if mutation == "object":
        value = []
    elif mutation == "model":
        value["model"] = "private-provider-text"
    elif mutation == "answers":
        value["answers"] = {}
    elif mutation == "choice":
        answer["choice"] = "private-provider-text"
    elif mutation == "keys":
        answer["probabilities"]["private-provider-text"] = 0
    elif mutation == "value":
        answer["probabilities"]["qa"] = True
    elif mutation == "sum":
        answer["probabilities"]["qa"] = 0.2
    elif mutation == "argmax":
        answer["choice"] = "qa"
    elif mutation == "confidence":
        answer["confidence"] = True
    elif mutation == "usage":
        value["usage"] = None
    elif mutation == "input":
        value["usage"]["input_tokens"] = False
    else:
        value["usage"]["output_tokens"] = -1
    with pytest.raises(JevSchemaError) as historical:
        validate_jev_response(copy.deepcopy(value))
    assert historical.value.code == code
    decision, trace, requests = call(value)
    assert decision.task_type == "qa" and decision.reasoning == "fallback"
    assert trace["route"]["router_error_type"] == code
    assert trace["route"]["router_cost_usd"] is None
    assert len(requests) == 1
    assert "private-provider-text" not in json.dumps(trace)


@pytest.mark.parametrize(
    "status,kind",
    [
        (301, "configuration"),
        (401, "access_denied"),
        (403, "access_denied"),
        (422, "configuration"),
        (429, "throttled"),
        (500, "unavailable"),
        (529, "unavailable"),
    ],
)
def test_http_failures_no_redirect_retry_or_secondary_call(status, kind):
    decision, trace, requests = call({"private-body": "never logged"}, status=status)
    assert decision.task_type == "qa" and len(requests) == 1
    assert trace["errors"][0]["kind"] == kind
    assert trace["errors"][0]["fatal"] is False
    assert "never logged" not in json.dumps(trace)


@pytest.mark.parametrize(
    "error,code",
    [
        (httpx.ReadTimeout("secret"), "timeout"),
        (httpx.ConnectTimeout("secret"), "timeout"),
        (httpx.ConnectError("secret"), "transport_failure"),
        (RuntimeError("secret"), "transport_failure"),
    ],
)
def test_transport_failures_are_single_attempt_and_sanitized(error, code):
    decision, trace, requests = call(failure=error)
    assert decision.task_type == "qa" and len(requests) == 1
    assert trace["route"]["router_error_type"] == code
    assert "secret" not in json.dumps(trace)


@pytest.mark.parametrize(
    "raw,code",
    [
        (b'{"model": "one", "model": "two"}', "duplicate_json_key"),
        (b'{"private":NaN}', "nonfinite_json"),
        (b"invalid", "not_json"),
        (b"\xff", "not_json"),
        (b"x" * 65_537, "response_too_large"),
    ],
    ids=["duplicate", "nonfinite", "not-json", "utf8", "oversized"],
)
def test_raw_invalid_responses(raw, code):
    agent = j.JevRouterAgent(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))
    )
    with request_trace("synthetic") as trace:
        assert agent.route("invented").task_type == "qa"
    assert trace.route["router_error_type"] == code
    agent.close()


@pytest.mark.parametrize(
    "query", ["", " ", None, "x" * 301], ids=["empty", "space", "null", "long"]
)
def test_invalid_input_does_not_reach_transport(query):
    def forbidden(_):
        raise AssertionError("transport reached")

    agent = j.JevRouterAgent(transport=httpx.MockTransport(forbidden))
    with request_trace("synthetic") as trace:
        assert agent.route(query).task_type == "qa"
    assert trace.route["router_attempts"] == 0 and trace.model_calls == []
    agent.close()


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf"), True, "0.9"])
def test_binary_contract_rejects_invalid_confidence(value):
    with pytest.raises(ValueError):
        RouterDecision(task_type="summarize", confidence=value, reasoning="invented")


def test_configuration_default_invalid_and_disabled_modes(monkeypatch):
    monkeypatch.delenv("COPILOT_ROUTER_PROVIDER", raising=False)
    assert RouterConfiguration.from_environment().provider == "haiku"
    for provider, code in [
        ("jev", "jev_live_disabled"),
        ("shadow", "router_shadow_disabled"),
        ("unknown", "invalid_router_provider"),
    ]:
        monkeypatch.setenv("COPILOT_ROUTER_PROVIDER", provider)
        with pytest.raises(ServiceFailure) as error:
            build_router()
        assert error.value.code == code
    with pytest.raises(ServiceFailure) as error:
        j.JevRouterAgent(transport=None)
    assert error.value.code == "jev_live_disabled"


def test_mock_only_factory_and_real_transport_refusal():
    with pytest.raises(ServiceFailure):
        j.JevRouterAgent(transport=object())
    agent = build_router(
        RouterConfiguration("jev"),
        jev_transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body())),
    )
    assert agent.route("invented").task_type == "summarize"
    agent.close()


def test_new_modules_import_without_reading_env_or_constructing_clients():
    code = """
from tests.offline_guard import install
install()
from unittest.mock import patch
with patch('httpx.Client',side_effect=AssertionError('client')), patch('boto3.client',side_effect=AssertionError('aws')), patch('dotenv.load_dotenv',side_effect=AssertionError('dotenv')):
    import app.agents.jev_router
    import app.agents.router_configuration
    import app.agents.routing_contract
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHON_DOTENV_DISABLED": "1"},
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "choice,score,expected",
    [
        ("qa", 0.9, "qa"),
        ("summarize", 0.9, "summarize"),
        ("summarize", 0.5, "qa"),
    ],
)
def test_orchestrator_dispatch_contract_unchanged(monkeypatch, choice, score, expected):
    from app.agents.orchestrator import CopilotOrchestrator
    from app.agents.qa_agent import QAAgent, QAResponse
    from app.agents.summarizer_agent import SummarizerAgent, SummaryResponse

    calls = []

    def qa(self, query, trace_id=""):
        calls.append(("qa", query))
        return QAResponse(
            answer="invented", citations=["invented"], confidence=1, latency_ms=1
        )

    def summary(self, query, trace_id=""):
        calls.append(("summarize", query))
        return SummaryResponse(
            summary="invented", key_points=[], risk_flags=[], latency_ms=1
        )

    monkeypatch.setattr(QAAgent, "run", qa)
    monkeypatch.setattr(SummarizerAgent, "run", summary)
    orch = CopilotOrchestrator(
        router_configuration=RouterConfiguration("jev"),
        jev_transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=body(choice, score))
        ),
    )
    with request_trace("synthetic", "invented dispatch") as trace:
        result = orch.process("invented dispatch")
    assert result["task_type"] == expected and result["agent_used"] == expected
    assert calls == [(expected, "invented dispatch")]
    assert set(result) == {
        "task_type",
        "router_confidence",
        "result",
        "agent_used",
        "total_latency_ms",
    }
    assert trace.route["router_attempts"] == 1
    orch._router.close()


@pytest.mark.parametrize("score", [-1, 2, float("nan"), float("inf"), True, "0.8"])
def test_haiku_invalid_confidence_falls_back_without_provider_text(monkeypatch, score):
    from app.agents.router import RouterAgent
    from tests.conftest import FakeBedrock, converse_text

    fake = FakeBedrock(
        converse_responses=[
            converse_text(
                json.dumps(
                    {
                        "task_type": "summarize",
                        "confidence": score,
                        "reasoning": "private-output",
                    }
                )
            )
        ]
    )
    monkeypatch.setattr("app.agents.router.boto3.client", lambda *a, **kw: fake)
    router = RouterAgent()
    with request_trace("synthetic") as trace:
        assert router.route("invented").task_type == "qa"
    assert len(fake.converse_calls) == 1
    assert "private-output" not in json.dumps(trace.to_record())
