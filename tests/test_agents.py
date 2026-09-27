"""Unit tests for QA/summarizer agents, RAG services and the orchestrator (all mocked)."""
import json

import faiss
import numpy as np
import pytest

from app.agents.orchestrator import CopilotOrchestrator
from app.agents.qa_agent import QAAgent, QAResponse
from app.agents.router import RouterDecision
from app.agents.summarizer_agent import SummarizerAgent, SummaryResponse
from app.observability import request_trace
from app.services import bedrock_client, retriever
from tests.conftest import FakeBedrock, converse_text

DIM = 1024


def _unit(vec_seed: int) -> list[float]:
    rng = np.random.default_rng(vec_seed)
    v = rng.random(DIM).astype(np.float32)
    return (v / np.linalg.norm(v)).tolist()


@pytest.fixture
def tiny_index(monkeypatch):
    """Install a 3-vector in-memory FAISS index and metadata in the retriever."""
    vectors = np.array([_unit(1), _unit(2), _unit(3)], dtype=np.float32)
    index = faiss.IndexFlatIP(DIM)
    index.add(vectors)
    metadata = [
        {"chunk_id": i, "source": f"s3://bucket/docs/{name}", "text": f"chunk {i} text"}
        for i, name in enumerate([
            "jpmorgan-chase-10k-fy2025.pdf", "goldman-sachs-10k-fy2025.pdf", "blackrock-10k-fy2025.pdf",
        ])
    ]
    monkeypatch.setattr(retriever, "_index", index)
    monkeypatch.setattr(retriever, "_metadata", metadata)
    return vectors


def _titan(vector, tokens=12) -> dict:
    return {"embedding": vector, "inputTextTokenCount": tokens}


# --- retriever ---------------------------------------------------------------

def test_retrieve_chunks_returns_ranked_chunks_and_traces_stages(monkeypatch, tiny_index):
    fake = FakeBedrock(invoke_responses=[_titan(_unit(2), tokens=9)])
    monkeypatch.setattr(retriever, "bedrock", fake)
    with request_trace("/ask", "q") as trace:
        chunks = retriever.retrieve_chunks("q", n_results=2)
    assert len(chunks) == 2
    assert chunks[0]["source"].endswith("goldman-sachs-10k-fy2025.pdf")
    assert set(chunks[0]) == {"content", "source", "score"}
    assert chunks[0]["score"] >= chunks[1]["score"]
    assert {"retrieval.embed", "retrieval.search"} <= set(trace.stages_ms)
    assert "retrieval.index_load" not in trace.stages_ms
    assert trace.attrs["index_loaded_this_request"] is False
    assert trace.model_calls[0]["name"] == "embed_query"
    assert trace.model_calls[0]["input_tokens"] == 9
    assert json.loads(fake.invoke_calls[0]["body"])["dimensions"] == 1024


def test_retrieve_chunks_error_returns_empty_and_is_traced(monkeypatch, tiny_index, capsys):
    monkeypatch.setattr(retriever, "bedrock", FakeBedrock(invoke_responses=[RuntimeError("AccessDenied")]))
    with request_trace("/ask", "q") as trace:
        assert retriever.retrieve_chunks("q") == []
    assert trace.errors[0]["stage"] == "retrieval"
    assert trace.errors[0]["type"] == "RuntimeError"
    logged = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    assert logged[-1]["event"] == "retrieval.error"
    assert logged[-1]["trace_id"] == trace.trace_id


def test_index_is_loaded_from_s3_once_and_timed(monkeypatch, tmp_path):
    vectors = np.array([_unit(5)], dtype=np.float32)
    built = faiss.IndexFlatIP(DIM)
    built.add(vectors)
    src_index = tmp_path / "src.faiss"
    faiss.write_index(built, str(src_index))
    meta = [{"chunk_id": 0, "source": "s3://b/docs/x.pdf", "text": "t"}]

    downloads = []

    class FakeS3:
        def download_file(self, bucket, key, path):
            downloads.append(key)
            if key.endswith(".faiss"):
                with open(src_index, "rb") as fsrc, open(path, "wb") as fdst:
                    fdst.write(fsrc.read())
            else:
                with open(path, "w") as f:
                    json.dump(meta, f)

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(retriever.tempfile, "gettempdir", lambda: str(cache_dir))
    monkeypatch.setattr(retriever, "s3", FakeS3())
    monkeypatch.setattr(retriever, "_index", None)
    monkeypatch.setattr(retriever, "_metadata", None)
    monkeypatch.setattr(retriever, "bedrock", FakeBedrock(invoke_responses=[_titan(_unit(5)), _titan(_unit(5))]))

    with request_trace("/ask", "q") as first:
        assert len(retriever.retrieve_chunks("q", n_results=1)) == 1
    with request_trace("/ask", "q") as second:
        retriever.retrieve_chunks("q", n_results=1)

    assert len(downloads) == 2  # index + metadata, first request only
    assert "retrieval.index_load" in first.stages_ms
    assert first.attrs["index_loaded_this_request"] is True
    assert "retrieval.index_load" not in second.stages_ms


# --- retrieve_and_generate -------------------------------------------------------

def test_retrieve_and_generate_contract_and_usage(monkeypatch):
    chunks = [
        {"content": "Total net revenue 182,447", "source": "s3://b/docs/jpmorgan-chase-10k-fy2025.pdf", "score": 0.61},
        {"content": "more", "source": "s3://b/docs/jpmorgan-chase-10k-fy2025.pdf", "score": 0.55},
    ]
    monkeypatch.setattr(bedrock_client, "retrieve_chunks", lambda q, n_results=5: chunks)
    fake = FakeBedrock(converse_responses=[converse_text("It was $182.4B.", 4100, 180, 2100)])
    monkeypatch.setattr(bedrock_client, "bedrock", fake)

    with request_trace("/ask", "q") as trace:
        result = bedrock_client.retrieve_and_generate("q")

    assert set(result) == {"answer", "citations", "retrieved_context"}
    assert result["answer"] == "It was $182.4B."
    assert result["citations"] == ["s3://b/docs/jpmorgan-chase-10k-fy2025.pdf"]
    assert result["retrieved_context"][0] == {"text": chunks[0]["content"], "source": chunks[0]["source"], "score": 0.61}
    assert "llm.qa_generate" in trace.stages_ms
    assert trace.attrs["retrieved_chunks"] == 2
    assert trace.model_calls[0] == {
        "name": "qa_generate", "model_id": bedrock_client.BEDROCK_MODEL_ID,
        "input_tokens": 4100, "output_tokens": 180, "latency_ms": 2100,
    }
    prompt = fake.converse_calls[0]["messages"][0]["content"][0]["text"]
    assert "Source: s3://b/docs/jpmorgan-chase-10k-fy2025.pdf" in prompt


def test_retrieve_and_generate_empty_retrieval(monkeypatch):
    monkeypatch.setattr(bedrock_client, "retrieve_chunks", lambda q, n_results=5: [])
    result = bedrock_client.retrieve_and_generate("q")
    assert result["answer"] == "No relevant documents found."
    assert result["error"] == "empty_retrieval"


def test_retrieve_and_generate_generation_error(monkeypatch):
    monkeypatch.setattr(
        bedrock_client, "retrieve_chunks",
        lambda q, n_results=5: [{"content": "c", "source": "s", "score": 0.1}],
    )
    monkeypatch.setattr(bedrock_client, "bedrock", FakeBedrock(converse_responses=[RuntimeError("ModelTimeout")]))
    with request_trace("/ask", "q") as trace:
        result = bedrock_client.retrieve_and_generate("q")
    assert result["answer"] == ""
    assert "ModelTimeout" in result["error"]
    assert trace.errors[0]["stage"] == "qa_generate"


# --- QAAgent ----------------------------------------------------------------------

def test_qa_agent_success_contract(monkeypatch):
    monkeypatch.setattr("app.agents.qa_agent.retrieve_and_generate", lambda q: {
        "answer": "A", "citations": ["s3://x"], "retrieved_context": [{"text": "t", "source": "s3://x", "score": 0.5}],
    })
    response = QAAgent().run("q", trace_id="t1")
    assert isinstance(response, QAResponse)
    assert response.model_dump().keys() == {"answer", "citations", "confidence", "agent", "latency_ms", "retrieved_context"}
    assert response.agent == "qa"
    assert response.confidence == 1.0


def test_qa_agent_degraded_result_keeps_contract_and_logs(monkeypatch, capsys):
    monkeypatch.setattr("app.agents.qa_agent.retrieve_and_generate", lambda q: {
        "answer": "", "citations": [], "retrieved_context": [], "error": "ThrottlingException",
    })
    response = QAAgent().run("q", trace_id="t2")
    assert response.answer == ""
    assert response.confidence == 0.5
    events = [json.loads(line)["event"] for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    assert "qa.degraded" in events


def test_qa_agent_unexpected_exception(monkeypatch):
    def boom(q):
        raise ValueError("bad")
    monkeypatch.setattr("app.agents.qa_agent.retrieve_and_generate", boom)
    response = QAAgent().run("q")
    assert response.answer == ""
    assert response.confidence == 0.0


# --- SummarizerAgent -------------------------------------------------------------

def _summarizer(*responses) -> SummarizerAgent:
    agent = SummarizerAgent()
    agent._client = FakeBedrock(converse_responses=list(responses))
    return agent


def test_summarizer_success_contract_and_usage():
    payload = json.dumps({"summary": "S", "key_points": ["k1"], "risk_flags": ["r1"]})
    agent = _summarizer(converse_text("```json\n" + payload + "\n```", 90, 400, 3000))
    with request_trace("/summarize", "q") as trace:
        response = agent.run("q")
    assert isinstance(response, SummaryResponse)
    assert response.model_dump().keys() == {"summary", "key_points", "risk_flags", "agent", "latency_ms"}
    assert response.summary == "S"
    assert response.agent == "summarize"
    assert "llm.summarize" in trace.stages_ms
    assert trace.model_calls[0]["output_tokens"] == 400


def test_summarizer_fills_missing_fields():
    response = _summarizer(converse_text(json.dumps({"summary": ""}))).run("q")
    assert response.summary == "No summary returned"
    assert response.key_points == [] and response.risk_flags == []


def test_summarizer_parse_error_keeps_contract():
    with request_trace("/summarize", "q") as trace:
        response = _summarizer(converse_text("Here is a summary without JSON")).run("q")
    assert response.summary == "Parse error"
    assert trace.errors[0]["stage"] == "summarize_parse"
    # Usage is still recorded: the call happened and was billed.
    assert len(trace.model_calls) == 1


def test_summarizer_invoke_error_is_distinguished_from_parse_error():
    with request_trace("/summarize", "q") as trace:
        response = _summarizer(RuntimeError("AccessDenied")).run("q")
    assert response.summary == "Parse error"
    assert trace.errors[0]["stage"] == "summarize_invoke"
    assert trace.model_calls == []


# --- CopilotOrchestrator -----------------------------------------------------------

class _StubRouter:
    def __init__(self, decision):
        self.decision = decision
        self.trace_ids = []

    def route(self, query, trace_id=""):
        self.trace_ids.append(trace_id)
        return self.decision


class _StubAgent:
    def __init__(self, response=None, exc=None):
        self.response, self.exc = response, exc
        self.trace_ids = []

    def run(self, query, trace_id=""):
        self.trace_ids.append(trace_id)
        if self.exc:
            raise self.exc
        return self.response


def _orchestrator(decision, qa=None, summarizer=None) -> CopilotOrchestrator:
    orch = CopilotOrchestrator()
    orch._router = _StubRouter(decision)
    orch._qa = qa or _StubAgent(QAResponse(answer="A", citations=["c"], confidence=1.0, latency_ms=100.0))
    orch._summarizer = summarizer or _StubAgent(
        SummaryResponse(summary="S", key_points=[], risk_flags=[], latency_ms=50.0)
    )
    return orch


def test_process_qa_contract_and_trace():
    orch = _orchestrator(RouterDecision(task_type="qa", confidence=0.9, reasoning="r"))
    with request_trace("/ask", "q") as trace:
        result = orch.process("q", trace_id=trace.trace_id)
    assert set(result) == {"task_type", "router_confidence", "result", "agent_used", "total_latency_ms"}
    assert result["task_type"] == "qa" and result["agent_used"] == "qa"
    assert result["router_confidence"] == 0.9
    assert result["total_latency_ms"] >= 100.0
    assert orch._router.trace_ids == [trace.trace_id]
    assert orch._qa.trace_ids == [trace.trace_id]
    assert {"route", "agent"} <= set(trace.stages_ms)
    assert trace.route["task_type"] == "qa"


def test_process_summarize_dispatch():
    orch = _orchestrator(RouterDecision(task_type="summarize", confidence=0.8, reasoning="r"))
    result = orch.process("q")
    assert result["agent_used"] == "summarize"
    assert result["result"]["summary"] == "S"


def test_process_uses_active_trace_id_when_none_given():
    orch = _orchestrator(RouterDecision(task_type="qa", confidence=0.9, reasoning="r"))
    with request_trace("/ask", "q", trace_id="abc") as _:
        orch.process("q")
    assert orch._router.trace_ids == ["abc"]


def test_process_generates_trace_id_outside_request():
    orch = _orchestrator(RouterDecision(task_type="qa", confidence=0.9, reasoning="r"))
    orch.process("q")
    assert len(orch._router.trace_ids[0]) == 36


def test_process_agent_exception_returns_error_contract():
    orch = _orchestrator(
        RouterDecision(task_type="qa", confidence=0.9, reasoning="r"),
        qa=_StubAgent(exc=RuntimeError("kaboom")),
    )
    with request_trace("/ask", "q") as trace:
        result = orch.process("q")
    assert result == {"error": "kaboom", "task_type": "unknown", "result": {}}
    assert trace.errors[0]["stage"] == "orchestrator"


def test_process_unknown_task_type():
    orch = _orchestrator(RouterDecision.model_construct(task_type="compare", confidence=0.9, reasoning="r"))
    result = orch.process("q")
    assert result["error"] == "unknown task_type: compare"


def test_process_direct_contract_and_trace():
    orch = _orchestrator(RouterDecision(task_type="qa", confidence=0.9, reasoning="r"))
    with request_trace("/summarize", "q") as trace:
        result = orch.process_direct("q", "summarize", trace_id=trace.trace_id)
    assert set(result) == {"task_type", "router_confidence", "result", "agent_used", "total_latency_ms"}
    assert result["router_confidence"] is None
    assert result["total_latency_ms"] == 50.0
    assert orch._router.trace_ids == []  # router is bypassed
    assert trace.route["router_outcome"] == "direct"


def test_process_direct_unknown_task_type():
    orch = _orchestrator(RouterDecision(task_type="qa", confidence=0.9, reasoning="r"))
    assert orch.process_direct("q", "nope") == {"error": "unknown task_type", "result": {}}
