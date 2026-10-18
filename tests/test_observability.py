import json

from app import observability
from app.observability import request_trace, stage
from tests.conftest import converse_text


def test_helpers_are_noops_without_active_trace():
    assert observability.current_trace() is None
    with stage("anything"):
        pass
    observability.record_converse_usage("x", "m", converse_text("hi"))
    observability.record_error("x", ValueError("boom"))
    observability.set_route(task_type="qa")
    assert observability.current_trace_id() == ""


def test_trace_is_active_only_inside_context():
    with request_trace("/ask", "q") as trace:
        assert observability.current_trace() is trace
        assert observability.current_trace_id() == trace.trace_id
    assert observability.current_trace() is None
    assert trace.total_ms is not None


def test_explicit_trace_id_is_kept():
    with request_trace("/ask", "q", trace_id="fixed-id") as trace:
        pass
    assert trace.trace_id == "fixed-id"


def test_cold_start_is_reported_once_per_process():
    with request_trace("/ask", "q") as first:
        pass
    with request_trace("/ask", "q") as second:
        pass
    assert first.cold_start is True
    assert second.cold_start is False


def test_stage_timings_accumulate():
    with request_trace("/ask", "q") as trace:
        with stage("retrieval.embed"):
            pass
        with stage("retrieval.embed"):
            pass
    assert "retrieval.embed" in trace.stages_ms
    assert trace.stages_ms["retrieval.embed"] >= 0


def test_stage_recorded_even_when_body_raises():
    with request_trace("/ask", "q") as trace:
        try:
            with stage("llm.qa_generate"):
                raise RuntimeError("fail")
        except RuntimeError:
            pass
    assert "llm.qa_generate" in trace.stages_ms


def test_converse_usage_is_recorded():
    with request_trace("/ask", "q") as trace:
        observability.record_converse_usage("router", "model-x", converse_text("{}", 240, 45, 812))
    assert trace.model_calls == [
        {"name": "router", "model_id": "model-x", "input_tokens": 240, "output_tokens": 45, "latency_ms": 812}
    ]
    assert trace.token_totals() == {"input_tokens": 240, "output_tokens": 45}


def test_converse_usage_tolerates_missing_fields():
    with request_trace("/ask", "q") as trace:
        observability.record_converse_usage("router", "m", {"output": {}})
    assert trace.model_calls[0]["input_tokens"] is None
    assert trace.token_totals() == {"input_tokens": 0, "output_tokens": 0}


def test_errors_are_truncated():
    with request_trace("/ask", "q") as trace:
        observability.record_error("retrieval", ValueError("x" * 1000))
    assert trace.errors[0]["type"] == "ValueError"
    assert len(trace.errors[0]["message"]) == 200


def test_record_never_contains_query_text(capsys):
    query = "What was JPMorgan Chase's total net revenue for fiscal year 2025?"
    with request_trace("/ask", query) as trace:
        pass
    observability.emit(trace)
    line = capsys.readouterr().out.strip()
    record = json.loads(line)
    assert query not in line
    assert "JPMorgan" not in line
    assert record["event"] == "request.timing"
    assert record["query_chars"] == len(query)
    assert len(record["query_sha256_12"]) == 12


def test_record_schema_keys():
    with request_trace("/summarize", "q") as trace:
        pass
    record = trace.to_record()
    assert set(record) == {
        "event", "schema_version", "trace_id", "endpoint", "cold_start", "process_age_ms",
        "query_chars", "query_sha256_12", "total_ms", "stages_ms", "route", "model_calls",
        "tokens", "errors", "attrs",
    }


def test_empty_query_has_no_digest():
    assert observability.query_digest("") is None
