"""FastAPI contract tests. The orchestrator and Bedrock are mocked; no network."""
import json

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.agents.orchestrator import CopilotOrchestrator
from app.services import bedrock_client
from tests.conftest import FakeBedrock, converse_text

ASK_KEYS = {"task_type", "router_confidence", "result", "agent_used", "total_latency_ms", "trace_id"}
QA_RESULT_KEYS = {"answer", "citations", "confidence", "agent", "latency_ms", "retrieved_context"}
SUMMARY_RESULT_KEYS = {"summary", "key_points", "risk_flags", "agent", "latency_ms"}
QUERY = "What was JPMorgan Chase's total net revenue for fiscal year 2025?"


class RecordingOrchestrator:
    def __init__(self, result=None):
        self.result = result or {
            "task_type": "qa", "router_confidence": 0.95,
            "result": {"answer": "A", "citations": [], "confidence": 1.0, "agent": "qa",
                       "latency_ms": 10.0, "retrieved_context": []},
            "agent_used": "qa", "total_latency_ms": 12.0,
        }
        self.calls = []

    def process(self, query, trace_id=None):
        self.calls.append(("process", query, trace_id))
        return dict(self.result)

    def process_direct(self, query, task_type, trace_id=None):
        self.calls.append(("process_direct", query, task_type, trace_id))
        return dict(self.result)


@pytest.fixture
def client():
    return TestClient(main_module.app)


def _timing_records(captured: str) -> list[dict]:
    records = []
    for line in captured.splitlines():
        if line.startswith("{"):
            record = json.loads(line)
            if record.get("event") == "request.timing":
                records.append(record)
    return records


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["region"] == "us-east-1"


def test_ask_passes_trace_id_through_and_returns_it(client, monkeypatch, capsys):
    orch = RecordingOrchestrator()
    monkeypatch.setattr(main_module, "orchestrator", orch)
    body = client.post("/ask", json={"query": QUERY}).json()
    assert set(body) == ASK_KEYS
    _, query, trace_id = orch.calls[0]
    assert query == QUERY
    assert body["trace_id"] == trace_id
    records = _timing_records(capsys.readouterr().out)
    assert len(records) == 1
    assert records[0]["trace_id"] == trace_id
    assert records[0]["endpoint"] == "/ask"


def test_summarize_bypasses_router(client, monkeypatch):
    orch = RecordingOrchestrator()
    monkeypatch.setattr(main_module, "orchestrator", orch)
    body = client.post("/summarize", json={"query": "Summarize GS risks"}).json()
    assert orch.calls[0][0] == "process_direct"
    assert orch.calls[0][2] == "summarize"
    assert body["trace_id"] == orch.calls[0][3]


def test_error_result_is_passed_through_with_trace_id(client, monkeypatch):
    orch = RecordingOrchestrator({"error": "boom", "task_type": "unknown", "result": {}})
    monkeypatch.setattr(main_module, "orchestrator", orch)
    response = client.post("/ask", json={"query": QUERY})
    # Existing contract: errors are reported in the body with HTTP 200.
    assert response.status_code == 200
    assert set(response.json()) == {"error", "task_type", "result", "trace_id"}


def test_missing_query_is_rejected(client):
    assert client.post("/ask", json={}).status_code == 422


def test_timing_record_never_contains_query(client, monkeypatch, capsys):
    monkeypatch.setattr(main_module, "orchestrator", RecordingOrchestrator())
    client.post("/ask", json={"query": QUERY})
    out = capsys.readouterr().out
    assert QUERY not in out
    record = _timing_records(out)[0]
    assert record["query_chars"] == len(QUERY)


def test_cold_start_flag_only_on_first_request(client, monkeypatch, capsys):
    monkeypatch.setattr(main_module, "orchestrator", RecordingOrchestrator())
    client.post("/ask", json={"query": "a"})
    client.post("/ask", json={"query": "b"})
    records = _timing_records(capsys.readouterr().out)
    assert [r["cold_start"] for r in records] == [True, False]


def test_cloudwatch_request_log_omits_query_text(client, monkeypatch):
    sent = []

    class FakeLogs:
        def put_log_events(self, **kwargs):
            sent.append(kwargs)

    monkeypatch.setenv("COPILOT_CW_REQUEST_LOG", "true")
    monkeypatch.setattr(main_module, "_get_cw_client", lambda: FakeLogs())
    monkeypatch.setattr(main_module, "orchestrator", RecordingOrchestrator())
    body = client.post("/ask", json={"query": QUERY}).json()
    message = json.loads(sent[0]["logEvents"][0]["message"])
    assert QUERY not in sent[0]["logEvents"][0]["message"]
    assert "query_preview" not in message
    assert message["query_chars"] == len(QUERY)
    assert message["trace_id"] == body["trace_id"]
    assert message["endpoint"] == "/ask"


def test_cloudwatch_request_log_disabled_makes_no_client(client, monkeypatch):
    def must_not_be_called():
        raise AssertionError("CloudWatch client created while disabled")

    monkeypatch.setattr(main_module, "_get_cw_client", must_not_be_called)
    monkeypatch.setattr(main_module, "orchestrator", RecordingOrchestrator())
    assert client.post("/ask", json={"query": "q"}).status_code == 200


def test_cloudwatch_failure_does_not_break_request(client, monkeypatch):
    class BrokenLogs:
        def put_log_events(self, **kwargs):
            raise RuntimeError("throttled")

    monkeypatch.setenv("COPILOT_CW_REQUEST_LOG", "true")
    monkeypatch.setattr(main_module, "_get_cw_client", lambda: BrokenLogs())
    monkeypatch.setattr(main_module, "orchestrator", RecordingOrchestrator())
    assert client.post("/ask", json={"query": "q"}).status_code == 200


def test_ask_end_to_end_with_mocked_bedrock(client, monkeypatch, capsys):
    """Real router -> QA agent -> RAG service, with Bedrock and retrieval faked."""
    orch = CopilotOrchestrator()
    orch._router._client = FakeBedrock(converse_responses=[converse_text(
        json.dumps({"task_type": "qa", "confidence": 0.95, "reasoning": "figure"}), 240, 40, 600)])
    chunks = [{"content": "Total net revenue $182,447", "source": "s3://b/docs/jpmorgan-chase-10k-fy2025.pdf",
               "score": 0.62}]
    monkeypatch.setattr(bedrock_client, "retrieve_chunks", lambda q, n_results=5: chunks)
    monkeypatch.setattr(bedrock_client, "bedrock", FakeBedrock(
        converse_responses=[converse_text("$182.447 billion", 4000, 150, 2000)]))
    monkeypatch.setattr(main_module, "orchestrator", orch)

    body = client.post("/ask", json={"query": QUERY}).json()

    assert set(body) == ASK_KEYS
    assert set(body["result"]) == QA_RESULT_KEYS
    assert body["task_type"] == "qa" and body["agent_used"] == "qa"
    assert body["result"]["answer"] == "$182.447 billion"
    record = _timing_records(capsys.readouterr().out)[0]
    assert record["trace_id"] == body["trace_id"]
    assert {"route", "agent", "llm.qa_generate"} <= set(record["stages_ms"])
    assert [c["name"] for c in record["model_calls"]] == ["router", "qa_generate"]
    assert record["tokens"] == {"input_tokens": 4240, "output_tokens": 190}
    assert record["route"]["router_outcome"] == "model"
    assert record["errors"] == []


def test_summarize_end_to_end_contract(client, monkeypatch):
    orch = CopilotOrchestrator()
    orch._summarizer._client = FakeBedrock(converse_responses=[converse_text(
        json.dumps({"summary": "S", "key_points": ["a"], "risk_flags": ["b"]}))])
    monkeypatch.setattr(main_module, "orchestrator", orch)
    body = client.post("/summarize", json={"query": "Summarize"}).json()
    assert set(body) == ASK_KEYS
    assert set(body["result"]) == SUMMARY_RESULT_KEYS
    assert body["router_confidence"] is None


# --- /evaluate: disabled by default, token-gated, bounded ---------------------------

def _enable_evaluate(monkeypatch, token="s3cr3t-test-token"):
    monkeypatch.setenv("ENABLE_EVALUATE_ENDPOINT", "true")
    monkeypatch.setenv("EVALUATE_ENDPOINT_TOKEN", token)
    return token


def test_evaluate_is_disabled_by_default(client, monkeypatch):
    orch = RecordingOrchestrator()
    monkeypatch.setattr(main_module, "orchestrator", orch)
    response = client.post("/evaluate", json={"test_cases": [{"query": "q"}]})
    assert response.status_code == 404
    assert orch.calls == []


def test_evaluate_enabled_without_token_configured_stays_closed(client, monkeypatch):
    monkeypatch.setenv("ENABLE_EVALUATE_ENDPOINT", "true")
    monkeypatch.setenv("EVALUATE_ENDPOINT_TOKEN", "")
    response = client.post("/evaluate", json={"test_cases": []}, headers={"X-Evaluate-Token": ""})
    assert response.status_code == 404


@pytest.mark.parametrize("headers", [{}, {"X-Evaluate-Token": "wrong"}])
def test_evaluate_rejects_missing_or_wrong_token(client, monkeypatch, headers):
    _enable_evaluate(monkeypatch)
    orch = RecordingOrchestrator()
    monkeypatch.setattr(main_module, "orchestrator", orch)
    response = client.post("/evaluate", json={"test_cases": [{"query": "q"}]}, headers=headers)
    assert response.status_code == 401
    assert orch.calls == []


def test_evaluate_with_valid_token_preserves_response_shape(client, monkeypatch, capsys):
    token = _enable_evaluate(monkeypatch)
    orch = RecordingOrchestrator()
    monkeypatch.setattr(main_module, "orchestrator", orch)
    response = client.post(
        "/evaluate",
        json={"test_cases": [{"query": "a"}, {"query": "b"}]},
        headers={"X-Evaluate-Token": token},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list) and len(body) == 2
    assert body[0] == orch.result
    trace_ids = [call[2] for call in orch.calls]
    assert all(trace_ids) and trace_ids[0] != trace_ids[1]
    assert len(_timing_records(capsys.readouterr().out)) == 2


def test_evaluate_rejects_too_many_cases_before_running_any(client, monkeypatch):
    token = _enable_evaluate(monkeypatch)
    orch = RecordingOrchestrator()
    monkeypatch.setattr(main_module, "orchestrator", orch)
    cases = [{"query": "q"}] * (main_module.EVALUATE_MAX_CASES + 1)
    response = client.post("/evaluate", json={"test_cases": cases}, headers={"X-Evaluate-Token": token})
    assert response.status_code == 413
    assert orch.calls == []


@pytest.mark.parametrize("cases, status", [
    ("not-a-list", 422),
    ([{"nope": 1}], 422),
    ([{"query": "   "}], 422),
    (["just a string"], 422),
    ([{"query": "x" * 2001}], 413),
])
def test_evaluate_validates_cases(client, monkeypatch, cases, status):
    token = _enable_evaluate(monkeypatch)
    orch = RecordingOrchestrator()
    monkeypatch.setattr(main_module, "orchestrator", orch)
    response = client.post("/evaluate", json={"test_cases": cases}, headers={"X-Evaluate-Token": token})
    assert response.status_code == status
    assert orch.calls == []
