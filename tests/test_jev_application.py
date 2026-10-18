"""Explicit application factory and lifetime checks; synthetic key/HTTP only."""

import json

import httpx
import pytest

from app.agents import jev_router as j
from app.agents.router_configuration import RouterConfiguration, build_router
from app.errors import ServiceFailure
from app.observability import request_trace
from tests.test_jev_candidate import body


SECRET = "invented-key-not-a-credential"


def install_http(monkeypatch, *, status=200, choice="summarize"):
    requests, options = [], []
    stream = None

    def handler(request):
        nonlocal stream
        requests.append(request)
        stream = httpx.ByteStream(json.dumps(body(choice)).encode())
        return httpx.Response(status, stream=stream)

    transport = httpx.MockTransport(handler)

    def factory(**kwargs):
        options.append(kwargs)
        return transport

    monkeypatch.setattr(j.httpx, "HTTPTransport", factory)
    return requests, options


@pytest.mark.parametrize("key", [None, "", "   ", "private\nmarker", "private\tmarker", "é"])
def test_missing_or_invalid_key_fails_before_http(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    else:
        monkeypatch.setenv("TYPESAFE_API_KEY", key)

    def forbidden(**kwargs):
        pytest.fail("HTTP constructed before key validation")

    monkeypatch.setattr(j.httpx, "HTTPTransport", forbidden)
    with pytest.raises(ServiceFailure) as error:
        build_router(RouterConfiguration("jev"))
    assert error.value.code in {"missing_jev_api_key", "invalid_jev_api_key"}
    assert "private" not in str(error.value)


@pytest.mark.parametrize("status", [200, 401, 429, 500])
def test_explicit_live_factory_request_metadata_and_privacy(monkeypatch, capsys, caplog, status):
    monkeypatch.setenv("COPILOT_ROUTER_PROVIDER", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", SECRET)
    requests, options = install_http(monkeypatch, status=status)
    agent = build_router()
    try:
        with request_trace("synthetic") as trace:
            decision = agent.route("invented query")
        assert options == [{"retries": 0, "trust_env": False}]
        assert len(requests) == 1
        request = requests[0]
        assert request.method == "POST" and str(request.url) == j.ENDPOINT
        assert request.headers["authorization"] == f"Bearer {SECRET}"
        assert json.loads(request.content) == j.payload("invented query")
        assert request.extensions["timeout"] == {"connect": 2.0, "read": 5.0, "write": 5.0, "pool": 5.0}
        assert agent._http.follow_redirects is False
        assert agent._http._trust_env is False
        assert trace.route["router_live"] is True
        assert trace.route["router_attempts"] == 1
        assert trace.route["router_http_status"] == status
        assert decision.task_type == ("summarize" if status == 200 else "qa")
        assert trace.route["router_cost_basis"] == ("usage_estimate" if status == 200 else "unknown")
        assert SECRET not in json.dumps(trace.to_record()) + capsys.readouterr().out + caplog.text
    finally:
        agent.close()
    assert agent._http.is_closed


def test_live_key_cannot_enable_arbitrary_injection():
    with pytest.raises(ServiceFailure) as error:
        j.JevRouterAgent(api_key=SECRET, transport=object())
    assert error.value.code == "jev_live_disabled"
    with pytest.raises(ServiceFailure) as error:
        j.JevRouterAgent(api_key=SECRET, transport=httpx.MockTransport(lambda _: None))
    assert error.value.code == "jev_ambiguous_configuration"


def test_default_haiku_never_reads_jev_key_or_constructs_http(monkeypatch):
    from app.agents import router

    sentinel = object()
    monkeypatch.setattr(router, "RouterAgent", lambda: sentinel)

    def forbidden(*args, **kwargs):
        pytest.fail("default Haiku touched Jev configuration")

    monkeypatch.setattr(j.httpx, "HTTPTransport", forbidden)
    monkeypatch.setattr("app.agents.router_configuration.os.getenv", forbidden)
    assert build_router(RouterConfiguration()) is sentinel


@pytest.mark.parametrize("choice", ["qa", "summarize"])
def test_live_factory_through_ask_keeps_haiku_generation(monkeypatch, choice):
    import app.main as main
    from app.agents.orchestrator import CopilotOrchestrator
    from app.services import bedrock_client
    from tests.conftest import FakeBedrock, converse_text

    monkeypatch.setenv("COPILOT_ROUTER_PROVIDER", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", SECRET)
    requests, _ = install_http(monkeypatch, choice=choice)
    text = "Invented answer" if choice == "qa" else json.dumps({
        "summary": "Invented summary", "key_points": ["invented"], "risk_flags": []})
    fake = FakeBedrock(converse_responses=[converse_text(text)])
    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: fake)
    monkeypatch.setattr(bedrock_client, "bedrock", fake)
    monkeypatch.setattr(bedrock_client, "retrieve_chunks", lambda *args, **kwargs: [
        {"source": "invented", "content": "Invented evidence", "score": 0.9}])
    orch = CopilotOrchestrator()
    monkeypatch.setattr(main, "orchestrator", orch)
    from fastapi.testclient import TestClient

    with TestClient(main.app) as client:
        response = client.post("/ask", json={"query": "invented query"})
        assert response.status_code == 200
        result = response.json()
        assert result["task_type"] == choice and result["agent_used"] == choice
        assert result["result"]["answer" if choice == "qa" else "summary"] == (
            "Invented answer" if choice == "qa" else "Invented summary")
    assert orch._router._http.is_closed
    assert len(requests) == 1 and len(fake.converse_calls) == 1
    assert fake.converse_calls[0]["modelId"] == "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def test_orchestrator_construction_failure_closes_jev(monkeypatch):
    from app.agents.orchestrator import CopilotOrchestrator
    from app.agents.summarizer_agent import SummarizerAgent

    monkeypatch.setenv("COPILOT_ROUTER_PROVIDER", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", SECRET)
    install_http(monkeypatch)
    constructed = []
    original = j.httpx.Client

    def client(**kwargs):
        result = original(**kwargs)
        constructed.append(result)
        return result

    def fail(self):
        raise RuntimeError("invented construction failure")

    monkeypatch.setattr(j.httpx, "Client", client)
    monkeypatch.setattr(SummarizerAgent, "__init__", fail)
    with pytest.raises(RuntimeError):
        CopilotOrchestrator()
    assert len(constructed) == 1 and constructed[0].is_closed
