"""RouterAgent unit tests: Bedrock is replaced by FakeBedrock, no network."""
import json

import pytest

from app.agents.router import RouterAgent, RouterDecision
from app.observability import request_trace
from tests.conftest import FakeBedrock, converse_text


def _router(*responses) -> tuple[RouterAgent, FakeBedrock]:
    agent = RouterAgent()
    fake = FakeBedrock(converse_responses=list(responses))
    agent._client = fake
    return agent, fake


def _decision_json(task_type="qa", confidence=0.95, reasoning="numeric lookup") -> str:
    return json.dumps({"task_type": task_type, "confidence": confidence, "reasoning": reasoning})


@pytest.mark.parametrize("task_type", ["qa", "summarize"])
def test_valid_model_decision_is_returned(task_type):
    agent, _ = _router(converse_text(_decision_json(task_type, 0.9)))
    decision = agent.route("some query")
    assert isinstance(decision, RouterDecision)
    assert decision.task_type == task_type
    assert decision.confidence == 0.9


def test_markdown_fenced_json_is_parsed():
    agent, _ = _router(converse_text("```json\n" + _decision_json("summarize", 0.8) + "\n```"))
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


@pytest.mark.parametrize("text", [
    "not json at all",
    json.dumps({"task_type": "compare", "confidence": 0.9, "reasoning": "x"}),
    json.dumps({"task_type": "qa"}),
    "",
])
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
    agent, _ = _router(converse_text(_decision_json("qa", 0.9), input_tokens=241, output_tokens=38, latency_ms=700))
    with request_trace("/ask", "q") as trace:
        agent.route("q", trace_id=trace.trace_id)
    assert trace.route["router_outcome"] == "model"
    assert trace.model_calls == [{
        "name": "router", "model_id": agent._model_id,
        "input_tokens": 241, "output_tokens": 38, "latency_ms": 700,
    }]


@pytest.mark.parametrize("response, outcome", [
    (RuntimeError("boom"), "fallback_invoke_error"),
    (converse_text("garbage"), "fallback_parse_error"),
    (converse_text(_decision_json("summarize", 0.2)), "fallback_low_confidence"),
])
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
