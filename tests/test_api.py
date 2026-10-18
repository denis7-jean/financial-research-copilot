"""FastAPI contract tests. The orchestrator and Bedrock are mocked; no network."""
import json

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.agents.orchestrator import CopilotOrchestrator
from app.services import bedrock_client
from tests.conftest import ACCESS_DENIED_MESSAGE, FakeBedrock, aws_error, converse_text

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


@pytest.mark.parametrize("kind, status", [
    ("access_denied", 503), ("throttled", 503), ("unavailable", 503), ("timeout", 504),
    ("model_error", 502), ("invalid_model_output", 502), ("configuration", 500), ("internal", 500),
])
def test_failure_results_map_to_http_status(client, monkeypatch, kind, status):
    detail = {"stage": "retrieval.embed", "kind": kind, "code": "X", "retryable": False}
    orch = RecordingOrchestrator({"error": "msg", "error_detail": detail, "task_type": "unknown", "result": {}})
    monkeypatch.setattr(main_module, "orchestrator", orch)
    response = client.post("/ask", json={"query": QUERY})
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error", "error_detail", "task_type", "result", "trace_id"}
    assert body["error_detail"] == detail
    assert body["trace_id"] == orch.calls[0][2]


def test_error_without_detail_is_500(client, monkeypatch):
    monkeypatch.setattr(main_module, "orchestrator", RecordingOrchestrator({"error": "boom", "result": {}}))
    assert client.post("/summarize", json={"query": "q"}).status_code == 500


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


# --- Reliability regressions: infrastructure failures vs legitimate outcomes ---------------

DIM = 1024
VISA_SRC = "s3://financial-copilot-hl/docs/visa-10k-fy2025.pdf"
JPM_SRC = "s3://financial-copilot-hl/docs/jpmorgan-chase-10k-fy2025.pdf"


def _unit(seed: int):
    import numpy as np

    v = np.random.default_rng(seed).random(DIM).astype(np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def live_path(monkeypatch):
    """Real orchestrator -> router -> QA -> retriever -> generation; only AWS clients are fake."""
    import faiss
    import numpy as np

    from app.services import retriever

    index = faiss.IndexFlatIP(DIM)
    index.add(np.stack([_unit(1), _unit(2)]))
    monkeypatch.setattr(retriever, "_index", index)
    monkeypatch.setattr(retriever, "_metadata", [
        {"chunk_id": 0, "source": JPM_SRC, "text": "Total net revenue $182,447 million"},
        {"chunk_id": 1, "source": VISA_SRC, "text": "Net revenue $40,000 million"},
    ])

    def configure(router=None, embed=None, generate=None):
        orch = CopilotOrchestrator()
        orch._router._client = FakeBedrock(converse_responses=router or [converse_text(
            json.dumps({"task_type": "qa", "confidence": 0.95, "reasoning": "figure"}))])
        monkeypatch.setattr(retriever, "bedrock", FakeBedrock(invoke_responses=embed or []))
        monkeypatch.setattr(bedrock_client, "bedrock", FakeBedrock(converse_responses=generate or []))
        monkeypatch.setattr(main_module, "orchestrator", orch)
        return orch

    return configure


def _titan(seed: int) -> dict:
    return {"embedding": _unit(seed).tolist(), "inputTextTokenCount": 9}


def test_production_access_denied_incident_returns_503_not_empty_200(client, live_path, capsys):
    """Replays the 2026-09-28 smoke-test failure: every Bedrock call denied."""
    denied = aws_error("AccessDeniedException", ACCESS_DENIED_MESSAGE)
    live_path(router=[denied], embed=[aws_error("AccessDeniedException", ACCESS_DENIED_MESSAGE, "InvokeModel")])

    response = client.post("/ask", json={"query": "What was Visa's net revenue for fiscal year 2025?"})

    assert response.status_code == 503
    body = response.json()
    assert body["error_detail"] == {"stage": "retrieval.embed", "kind": "access_denied",
                                    "code": "AccessDeniedException", "retryable": False}
    assert body["result"] == {}
    assert "No relevant documents found." not in response.text
    for secret in ("123456789012", "arn:aws", "verified"):
        assert secret not in response.text
    out = capsys.readouterr().out
    assert "123456789012" not in out and "arn:aws" not in out
    record = _timing_records(out)[0]
    assert record["attrs"]["http_status"] == 503 and record["attrs"]["outcome"] == "failed"
    stages = [(e["stage"], e["fatal"]) for e in record["errors"]]
    assert stages == [("router", False), ("retrieval.embed", True)]
    assert record["route"]["router_outcome"] == "fallback_invoke_error"


@pytest.mark.parametrize("make_error, status, kind, retryable", [
    (lambda: __import__("botocore.exceptions").exceptions.EndpointConnectionError(
        endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com"), 503, "unavailable", True),
    (lambda: __import__("botocore.exceptions").exceptions.ReadTimeoutError(
        endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com"), 504, "timeout", True),
    (lambda: aws_error("ThrottlingException", "Too many requests", "InvokeModel"), 503, "throttled", True),
])
def test_embedding_service_failures_surface_with_status(client, live_path, make_error, status, kind, retryable):
    live_path(embed=[make_error()])
    response = client.post("/ask", json={"query": QUERY})
    assert response.status_code == status
    detail = response.json()["error_detail"]
    assert (detail["stage"], detail["kind"], detail["retryable"]) == ("retrieval.embed", kind, retryable)


def test_generation_access_denied_after_successful_retrieval(client, live_path):
    live_path(embed=[_titan(1)], generate=[aws_error("AccessDeniedException", ACCESS_DENIED_MESSAGE)])
    response = client.post("/ask", json={"query": QUERY})
    assert response.status_code == 503
    assert response.json()["error_detail"]["stage"] == "qa_generate"


def test_genuinely_empty_retrieval_stays_200(client, monkeypatch, live_path, capsys):
    import faiss

    from app.services import retriever

    live_path(embed=[_titan(1)])
    monkeypatch.setattr(retriever, "_index", faiss.IndexFlatIP(DIM))
    monkeypatch.setattr(retriever, "_metadata", [])
    response = client.post("/ask", json={"query": QUERY})
    assert response.status_code == 200
    body = response.json()
    assert "error" not in body
    assert body["result"]["answer"] == "No relevant documents found."
    assert body["result"]["citations"] == [] and body["result"]["confidence"] == 0.5
    record = _timing_records(capsys.readouterr().out)[0]
    assert record["attrs"]["outcome"] == "no_evidence" and record["errors"] == []


def test_successful_grounded_qa_cites_its_source(client, live_path, capsys):
    live_path(embed=[_titan(1)], generate=[converse_text("JPMorgan Chase total net revenue was $182,447 million.")])
    response = client.post("/ask", json={"query": QUERY})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == ASK_KEYS and set(body["result"]) == QA_RESULT_KEYS
    assert "182,447" in body["result"]["answer"]
    assert JPM_SRC in body["result"]["citations"]
    assert body["result"]["retrieved_context"][0]["source"] == JPM_SRC
    record = _timing_records(capsys.readouterr().out)[0]
    assert record["attrs"]["outcome"] == "generated" and record["attrs"]["http_status"] == 200


def test_out_of_corpus_abstention_is_a_normal_200(client, live_path):
    abstention = "The provided documents do not contain Mastercard's net revenue; they cover Visa."
    live_path(embed=[_titan(2)], generate=[converse_text(abstention)])
    response = client.post("/ask", json={"query": "What is Mastercard's total net revenue for fiscal year 2025?"})
    assert response.status_code == 200
    body = response.json()
    assert "error" not in body
    assert body["result"]["answer"] == abstention
    assert VISA_SRC in body["result"]["citations"]


def test_router_failure_alone_degrades_gracefully(client, live_path):
    live_path(router=[aws_error("ThrottlingException", "slow down")], embed=[_titan(1)],
              generate=[converse_text("$182,447 million")])
    response = client.post("/ask", json={"query": QUERY})
    assert response.status_code == 200
    assert response.json()["router_confidence"] == 0.5


def test_summarize_invalid_model_output_returns_502(client, monkeypatch):
    orch = CopilotOrchestrator()
    orch._summarizer._client = FakeBedrock(converse_responses=[converse_text("not json")])
    monkeypatch.setattr(main_module, "orchestrator", orch)
    response = client.post("/summarize", json={"query": "Summarize"})
    assert response.status_code == 502
    body = response.json()
    assert body["task_type"] == "summarize"
    assert body["error_detail"]["kind"] == "invalid_model_output"
    assert "Parse error" not in response.text


def test_summarize_access_denied_returns_503(client, monkeypatch):
    orch = CopilotOrchestrator()
    orch._summarizer._client = FakeBedrock(converse_responses=[aws_error("AccessDeniedException", ACCESS_DENIED_MESSAGE)])
    monkeypatch.setattr(main_module, "orchestrator", orch)
    response = client.post("/summarize", json={"query": "Summarize"})
    assert response.status_code == 503
    assert "123456789012" not in response.text


def test_cloudwatch_request_log_records_failure_status(client, monkeypatch, live_path):
    sent = []

    class FakeLogs:
        def put_log_events(self, **kwargs):
            sent.append(json.loads(kwargs["logEvents"][0]["message"]))

    monkeypatch.setenv("COPILOT_CW_REQUEST_LOG", "true")
    monkeypatch.setattr(main_module, "_get_cw_client", lambda: FakeLogs())
    live_path(embed=[aws_error("AccessDeniedException", ACCESS_DENIED_MESSAGE, "InvokeModel")])
    client.post("/ask", json={"query": QUERY})
    assert sent[0]["http_status"] == 503


def test_evaluate_batch_reports_per_case_failures_with_200(client, monkeypatch, live_path):
    monkeypatch.setenv("ENABLE_EVALUATE_ENDPOINT", "true")
    monkeypatch.setenv("EVALUATE_ENDPOINT_TOKEN", "tok")
    live_path(embed=[aws_error("AccessDeniedException", ACCESS_DENIED_MESSAGE, "InvokeModel")])
    response = client.post("/evaluate", json={"test_cases": [{"query": QUERY}]}, headers={"X-Evaluate-Token": "tok"})
    assert response.status_code == 200
    assert response.json()[0]["error_detail"]["kind"] == "access_denied"
