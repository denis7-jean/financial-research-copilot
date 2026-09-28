"""Offline tests for the smoke-check validator and runner (HTTP is mocked)."""
import httpx
import pytest

from scripts import smoke_check
from scripts.smoke_check import SMOKE_CASES, validate_response

JPM = SMOKE_CASES["jpm_net_revenue"]
VISA = SMOKE_CASES["visa_net_revenue"]
JPM_SRC = "s3://financial-copilot-hl/docs/jpmorgan-chase-10k-fy2025.pdf"
VISA_SRC = "s3://financial-copilot-hl/docs/visa-10k-fy2025.pdf"


def _ok(answer: str, citations: list[str]) -> dict:
    return {"task_type": "qa", "router_confidence": 0.9, "agent_used": "qa", "total_latency_ms": 900.0,
            "trace_id": "t-1", "result": {"answer": answer, "citations": citations, "confidence": 1.0,
                                          "agent": "qa", "latency_ms": 800.0, "retrieved_context": []}}


def test_grounded_answers_pass():
    assert validate_response(200, _ok("Total net revenue was $182,447 million.", [JPM_SRC]), JPM) == []
    assert validate_response(200, _ok("Visa's net revenue was $40.0 billion.", [VISA_SRC]), VISA) == []


def test_the_production_incident_response_fails():
    """The 2026-09-28 outage body: HTTP 200, no error key, no-evidence answer."""
    body = _ok("No relevant documents found.", [])
    body["router_confidence"] = 0.5
    problems = validate_response(200, body, VISA)
    assert any("no-evidence answer" in p for p in problems)
    assert any("no citation" in p for p in problems)


def test_http_error_status_fails_with_detail():
    body = {"error": "denied", "error_detail": {"stage": "retrieval.embed", "kind": "access_denied"},
            "task_type": "unknown", "result": {}, "trace_id": "t"}
    problems = validate_response(503, body, JPM)
    assert problems == ["HTTP 503 (error_detail={'stage': 'retrieval.embed', 'kind': 'access_denied'})"]


def test_application_error_with_200_fails():
    body = {**_ok("x", [JPM_SRC]), "error": "legacy error"}
    assert any("application error" in p for p in validate_response(200, body, JPM))


def test_wrong_company_citation_fails():
    problems = validate_response(200, _ok("Visa's net revenue was $40.0 billion.", [JPM_SRC]), VISA)
    assert problems == [f"no citation of visa-10k-fy2025.pdf (got ['{JPM_SRC}'])"]


def test_legacy_mastercard_path_is_not_accepted_as_visa_citation():
    legacy = "s3://financial-copilot-hl/docs/mastercard-10k-fy2025.pdf"
    assert validate_response(200, _ok("$40,000 million", [legacy]), VISA)


def test_missing_figure_fails():
    problems = validate_response(200, _ok("Revenue grew strongly.", [JPM_SRC]), JPM)
    assert problems == ["answer lacks expected figure ('182,447', '182.4')"]


@pytest.mark.parametrize("body", [None, [], "text"])
def test_non_object_body_fails(body):
    assert validate_response(200, body, JPM)


def test_missing_trace_id_fails():
    body = _ok("$182,447 million", [JPM_SRC])
    del body["trace_id"]
    assert validate_response(200, body, JPM) == ["missing trace_id"]


def test_runner_exit_codes(monkeypatch, capsys):
    responses = {
        JPM["query"]: httpx.Response(200, json=_ok("$182,447 million", [JPM_SRC])),
        VISA["query"]: httpx.Response(503, json={"error": "e", "error_detail": {"kind": "access_denied"},
                                                 "result": {}, "trace_id": "t-2"}),
    }
    calls = []

    def fake_post(url, json, timeout):
        calls.append(url)
        return responses[json["query"]]

    monkeypatch.setattr(httpx, "post", fake_post)
    assert smoke_check.main(["--base-url", "http://localhost:8000/", "--case", "jpm_net_revenue"]) == 0
    assert smoke_check.main(["--base-url", "http://localhost:8000"]) == 1
    assert calls[0] == "http://localhost:8000/ask"
    out = capsys.readouterr().out
    assert "ok   jpm_net_revenue" in out and "FAIL visa_net_revenue trace_id=t-2: HTTP 503" in out
