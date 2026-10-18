"""Router tests: fake responses or real SDK retries with an in-process send stub."""

import json
import socket

import boto3
import botocore.session
import botocore.httpsession
from botocore.exceptions import ClientError, ReadTimeoutError
from botocore.awsrequest import AWSResponse
from botocore.config import Config
import pytest

from app.agents import router as router_module
from app.agents.router import RouterAgent, RouterDecision
from app.observability import request_trace
from tests.conftest import FakeBedrock, converse_text
from tests import offline_guard


def _router(*responses) -> tuple[RouterAgent, FakeBedrock]:
    agent = RouterAgent()
    fake = FakeBedrock(converse_responses=list(responses))
    agent._client = fake
    return agent, fake


def _decision_json(task_type="qa", confidence=0.95, reasoning="numeric lookup") -> str:
    return json.dumps(
        {"task_type": task_type, "confidence": confidence, "reasoning": reasoning}
    )


@pytest.mark.parametrize("task_type", ["qa", "summarize"])
def test_valid_model_decision_is_returned(task_type):
    agent, _ = _router(converse_text(_decision_json(task_type, 0.9)))
    decision = agent.route("some query")
    assert isinstance(decision, RouterDecision)
    assert decision.task_type == task_type
    assert decision.confidence == 0.9


def test_markdown_fenced_json_is_parsed():
    agent, _ = _router(
        converse_text("```json\n" + _decision_json("summarize", 0.8) + "\n```")
    )
    assert agent.route("q").task_type == "summarize"


def test_request_uses_configured_model_and_includes_query():
    agent, fake = _router(converse_text(_decision_json()))
    agent.route("What was JPM revenue?")
    call = fake.converse_calls[0]
    assert call["modelId"] == agent._model_id
    assert "What was JPM revenue?" in call["messages"][0]["content"][0]["text"]
    # Phase 0 must not change inference parameters.
    assert "inferenceConfig" not in call


@pytest.mark.parametrize("confidence", [0.0, 0.3, 0.59])
def test_low_confidence_falls_back_to_qa(confidence):
    agent, _ = _router(converse_text(_decision_json("summarize", confidence)))
    decision = agent.route("q")
    assert decision.task_type == "qa"
    assert decision.confidence == 0.5
    assert decision.reasoning == "fallback"


def test_threshold_is_inclusive_at_0_6():
    agent, _ = _router(converse_text(_decision_json("summarize", 0.6)))
    assert agent.route("q").task_type == "summarize"


@pytest.mark.parametrize(
    "text",
    [
        "not json at all",
        json.dumps({"task_type": "compare", "confidence": 0.9, "reasoning": "x"}),
        json.dumps({"task_type": "qa"}),
        "",
    ],
)
def test_unparseable_or_invalid_output_falls_back_to_qa(text):
    agent, _ = _router(converse_text(text))
    decision = agent.route("q")
    assert decision.task_type == "qa"
    assert decision.reasoning == "fallback"


def test_missing_content_falls_back_to_qa():
    agent, _ = _router({"output": {"message": {"content": []}}})
    assert agent.route("q").task_type == "qa"


def test_bedrock_exception_falls_back_to_qa_and_sets_latency():
    agent, _ = _router(RuntimeError("ThrottlingException"))
    decision = agent.route("q")
    assert decision.task_type == "qa"
    assert agent.latency_ms >= 0


def test_trace_records_usage_and_model_outcome():
    agent, _ = _router(
        converse_text(
            _decision_json("qa", 0.9),
            input_tokens=241,
            output_tokens=38,
            latency_ms=700,
        )
    )
    with request_trace("/ask", "q") as trace:
        agent.route("q", trace_id=trace.trace_id)
    assert trace.route["router_outcome"] == "model"
    assert trace.model_calls == [
        {
            "name": "router",
            "model_id": agent._model_id,
            "input_tokens": 241,
            "output_tokens": 38,
            "latency_ms": 700,
        }
    ]


@pytest.mark.parametrize(
    "response, outcome",
    [
        (RuntimeError("boom"), "fallback_invoke_error"),
        (converse_text("garbage"), "fallback_parse_error"),
        (converse_text(_decision_json("summarize", 0.2)), "fallback_low_confidence"),
    ],
)
def test_trace_records_fallback_reason(response, outcome):
    agent, _ = _router(response)
    with request_trace("/ask", "q") as trace:
        agent.route("q")
    assert trace.route["router_outcome"] == outcome


def test_low_confidence_trace_keeps_the_rejected_model_label():
    agent, _ = _router(converse_text(_decision_json("summarize", 0.4)))
    with request_trace("/ask", "q") as trace:
        agent.route("q")
    assert trace.route["model_task_type"] == "summarize"
    assert trace.route["model_confidence"] == 0.4


def test_invoke_error_is_not_counted_as_model_call():
    agent, _ = _router(RuntimeError("boom"))
    with request_trace("/ask", "q") as trace:
        agent.route("q")
    assert trace.model_calls == []


@pytest.fixture
def retrying_sdk_router(monkeypatch, tmp_path):
    # Real SDK retries/parsing/signing, invented credentials and no profile or
    # config discovery. Clearing only retry environment does not lift the guard.
    guards = (
        botocore.httpsession.URLLib3Session.send,
        socket.getaddrinfo,
        socket.socket.connect,
    )
    blocked_before = list(offline_guard.blocked_requests)
    monkeypatch.delenv("AWS_MAX_ATTEMPTS", raising=False)
    monkeypatch.delenv("AWS_RETRY_MODE", raising=False)
    session = botocore.session.Session()
    session.set_config_variable("config_file", str(tmp_path / "no-config"))
    session.set_config_variable("credentials_file", str(tmp_path / "no-credentials"))
    session.set_credentials("invented-key", "invented-secret")
    isolated = boto3.session.Session(botocore_session=session)
    # Explicit synthetic policy, not a change/claim about production settings.
    config = Config(retries={"mode": "legacy", "total_max_attempts": 5}, proxies={})
    monkeypatch.setattr(
        router_module.boto3,
        "client",
        lambda *a, **kw: isolated.client(*a, **kw, config=config),
    )
    monkeypatch.setattr("botocore.endpoint.time.sleep", lambda seconds: None)
    agent = RouterAgent()
    assert agent._client.meta.config.retries == {
        "mode": "legacy",
        "total_max_attempts": 5,
    }
    outcomes, sends = [], []

    class Raw:
        def __init__(self, raw):
            self.raw = raw

        def stream(self, amt=None, decode_content=False):
            yield self.raw

    def before_send(request, **kwargs):
        sends.append("Converse")  # No signed headers/body retained or logged.
        assert outcomes, "unexpected extra SDK dispatch"
        status, body = outcomes.pop(0)
        headers = {"content-type": "application/json"}
        if status == 429:
            headers["x-amzn-errortype"] = "ThrottlingException"
        return AWSResponse(request.url, status, headers, Raw(json.dumps(body).encode()))

    event, hook_id = "before-send.bedrock-runtime.Converse", "invented-router-retries"
    agent._client.meta.events.register(event, before_send, unique_id=hook_id)
    try:
        yield agent, outcomes, sends, config.retries["total_max_attempts"]
    finally:
        agent._client.meta.events.unregister(event, unique_id=hook_id)
        agent._client.close()
        assert guards == (
            botocore.httpsession.URLLib3Session.send,
            socket.getaddrinfo,
            socket.socket.connect,
        )
        assert offline_guard.blocked_requests == blocked_before


@pytest.mark.parametrize(
    "scenario", ["no_retry", "throttle_success", "exhaustion", "bad_output"]
)
def test_sdk_retry_sends_match_attempt_telemetry(retrying_sdk_router, scenario, capsys):
    agent, outcomes, sends, limit = retrying_sdk_router
    throttled = (429, {"message": "invented arn:aws:iam::123456789012:role/private"})
    success = (200, converse_text(_decision_json("summarize", 0.9)))
    if scenario == "exhaustion":
        outcomes.extend([throttled] * limit)
        expected, outcome = limit, "fallback_invoke_error"
    elif scenario in ("throttle_success", "bad_output"):
        outcomes.extend(
            [
                throttled,
                throttled,
                (200, converse_text("private not JSON"))
                if scenario == "bad_output"
                else success,
            ]
        )
        expected, outcome = (
            3,
            "fallback_parse_error" if scenario == "bad_output" else "model",
        )
    else:
        outcomes.append(success)
        expected, outcome = 1, "model"
    with request_trace("/ask", "invented query") as trace:
        decision = agent.route("invented query")
    assert not outcomes
    assert len(sends) == expected
    assert trace.route["router_attempts"] == len(sends)
    assert trace.route["router_outcome"] == outcome
    assert decision.task_type == ("summarize" if outcome == "model" else "qa")
    if outcome != "model":
        assert decision.confidence == 0.5 and decision.reasoning == "fallback"
        record = json.dumps(trace.to_record()) + capsys.readouterr().out
        assert "arn:aws" not in record and "123456789012" not in record
        assert "private not JSON" not in record


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        [],
        "not a mapping",
        {},
        {"RetryAttempts": None},
        {"RetryAttempts": True},
        {"RetryAttempts": False},
        {"RetryAttempts": -1},
        {"RetryAttempts": "2"},
        {"RetryAttempts": 2.0},
    ],
)
@pytest.mark.parametrize("is_error", [False, True])
def test_unusable_sdk_metadata_is_explicit_unknown(metadata, is_error):
    response = converse_text(_decision_json())
    response["ResponseMetadata"] = metadata
    if is_error:
        # Known error code keeps classification independent of malformed retry
        # metadata, which the telemetry extractor must not throw on.
        response["Error"] = {"Code": "ThrottlingException", "Message": "invented"}
        error = ClientError({"Error": response["Error"]}, "Converse")
        error.response = response  # Malformed metadata after valid construction.
        response = error
    agent, _ = _router(response)
    with request_trace("/ask") as trace:
        decision = agent.route("invented query")
    assert trace.route["router_attempts"] is None
    assert json.loads(json.dumps(trace.to_record()))["route"]["router_attempts"] is None
    assert decision.task_type == "qa"
    assert trace.route["router_outcome"] == (
        "fallback_invoke_error" if is_error else "model"
    )


@pytest.mark.parametrize("retries", [0, 2])
@pytest.mark.parametrize("is_error", [False, True])
def test_valid_sdk_metadata_counts_initial_attempt(retries, is_error):
    response = converse_text(_decision_json())
    response["ResponseMetadata"] = {"RetryAttempts": retries}
    if is_error:
        response["Error"] = {"Code": "ThrottlingException", "Message": "invented"}
        response = ClientError(response, "Converse")
    agent, _ = _router(response)
    with request_trace("/ask") as trace:
        agent.route("invented query")
    assert trace.route["router_attempts"] == retries + 1


def test_missing_metadata_and_transport_failure_do_not_retain_attempts():
    known = converse_text(_decision_json("summarize"))
    known["ResponseMetadata"] = {"RetryAttempts": 3}
    missing_error = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "invented"}}, "Converse"
    )
    agent, _ = _router(
        known,
        converse_text(_decision_json()),
        missing_error,
        ReadTimeoutError(endpoint_url="https://invented.invalid"),
    )
    with request_trace("/ask") as trace:
        for expected in (4, None, None, None):
            agent.route("invented query")
            assert trace.route["router_attempts"] == expected


def test_schema_failure_preserves_valid_attempt_metadata(capsys):
    response = converse_text(
        json.dumps({"task_type": "invented-invalid-route", "confidence": 0.9})
    )
    response["ResponseMetadata"] = {"RetryAttempts": 2}
    agent, _ = _router(response)
    with request_trace("/ask") as trace:
        decision = agent.route("invented query")
    assert trace.route["router_attempts"] == 3
    assert trace.route["router_outcome"] == "fallback_parse_error"
    assert decision.task_type == "qa" and decision.reasoning == "fallback"
    assert "invented-invalid-route" not in capsys.readouterr().out


def test_pre_dispatch_sdk_validation_is_factual_zero(retrying_sdk_router):
    agent, _, sends, _ = retrying_sdk_router
    agent._model_id = None  # Invalid SDK parameter, no dispatch possible.
    with request_trace("/ask") as trace:
        decision = agent.route("invented query")
    assert not sends
    assert trace.route["router_attempts"] == 0
    assert trace.route["router_outcome"] == "fallback_invoke_error"
    assert decision.task_type == "qa" and decision.reasoning == "fallback"


def test_strict_metadata_extraction_never_calls_overridden_mapping_methods():
    class BrokenDict(dict):
        def get(self, *args):
            raise RuntimeError("must not be invoked")

    for value in [None, [], BrokenDict(), {"ResponseMetadata": BrokenDict()}]:
        assert router_module._sdk_attempts(value) is None
