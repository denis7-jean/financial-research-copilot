import hmac
import json
import os
import time

import boto3
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from app.agents.orchestrator import CopilotOrchestrator
from app.errors import http_status_for
from app.observability import RequestTrace, annotate, emit, request_trace, stage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = CopilotOrchestrator()

_LOG_GROUP = "/financial-copilot/requests"
_LOG_STREAM = "financial-copilot-stream"

_cw_client = None


def _cloudwatch_request_log_enabled() -> bool:
    # On by default to preserve the deployed behaviour; tests and local runs can opt out.
    return os.getenv("COPILOT_CW_REQUEST_LOG", "true").strip().lower() not in {"false", "0", "no"}


def _get_cw_client():
    """Create the CloudWatch Logs client and ensure the group/stream exist, once.

    Previously this ran at import time, which made every import of app.main
    perform two AWS calls. Deferring it keeps imports side-effect free.
    """
    global _cw_client
    if _cw_client is None:
        client = boto3.client("logs", region_name="us-east-1")
        try:
            client.create_log_group(logGroupName=_LOG_GROUP)
        except Exception:
            pass
        try:
            client.create_log_stream(logGroupName=_LOG_GROUP, logStreamName=_LOG_STREAM)
        except Exception:
            pass
        _cw_client = client
    return _cw_client


class QueryRequest(BaseModel):
    query: str


def _log(endpoint: str, latency_ms: float, trace: RequestTrace) -> None:
    """Write the per-request summary to the custom CloudWatch log group.

    The query text is deliberately not logged (only its length).
    """
    if not _cloudwatch_request_log_enabled():
        return
    entry = json.dumps({
        "timestamp": time.time(),
        "endpoint": endpoint,
        "query_chars": trace.query_chars,
        "latency_ms": latency_ms,
        "trace_id": trace.trace_id,
        "cold_start": trace.cold_start,
        "http_status": trace.attrs.get("http_status"),
    })
    try:
        with stage("request_log"):
            _get_cw_client().put_log_events(
                logGroupName=_LOG_GROUP,
                logStreamName=_LOG_STREAM,
                logEvents=[{"timestamp": int(time.time() * 1000), "message": entry}],
            )
    except Exception:
        pass


def _respond(result: dict, trace: RequestTrace):
    """Successful results keep the plain 200 contract. Failures carry the same body
    (with sanitized error and error_detail) under a 5xx status."""
    body = {**result, "trace_id": trace.trace_id}
    status = trace.attrs["http_status"]
    if status == 200:
        return body
    return JSONResponse(status_code=status, content=body)


@app.post("/ask")
def ask(request: QueryRequest):
    with request_trace("/ask", request.query) as trace:
        start = time.monotonic()
        result = orchestrator.process(request.query, trace_id=trace.trace_id)
        latency_ms = (time.monotonic() - start) * 1000
        annotate("http_status", http_status_for(result))
        _log("/ask", latency_ms, trace)
    emit(trace)
    return _respond(result, trace)


@app.post("/summarize")
def summarize(request: QueryRequest):
    with request_trace("/summarize", request.query) as trace:
        start = time.monotonic()
        result = orchestrator.process_direct(request.query, "summarize", trace_id=trace.trace_id)
        latency_ms = (time.monotonic() - start) * 1000
        annotate("http_status", http_status_for(result))
        _log("/summarize", latency_ms, trace)
    emit(trace)
    return _respond(result, trace)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "region": os.getenv("AWS_DEFAULT_REGION"),
        "timestamp": time.time(),
    }


EVALUATE_MAX_CASES = 25
EVALUATE_MAX_QUERY_CHARS = 2000


def _evaluate_token() -> str | None:
    """The configured /evaluate token, or None when the endpoint is disabled.

    Fails closed: the endpoint is off unless ENABLE_EVALUATE_ENDPOINT=true AND a
    non-empty EVALUATE_ENDPOINT_TOKEN is set. Nothing in this repo calls it; the
    eval harness drives the orchestrator directly.
    """
    if os.getenv("ENABLE_EVALUATE_ENDPOINT", "false").strip().lower() != "true":
        return None
    token = os.getenv("EVALUATE_ENDPOINT_TOKEN", "")
    return token or None


@app.post("/evaluate")
def evaluate(payload: dict, x_evaluate_token: str | None = Header(default=None)):
    expected = _evaluate_token()
    if expected is None:
        # Indistinguishable from a route that does not exist.
        raise HTTPException(status_code=404, detail="Not Found")
    if not x_evaluate_token or not hmac.compare_digest(x_evaluate_token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Evaluate-Token")

    cases = payload.get("test_cases", [])
    if not isinstance(cases, list):
        raise HTTPException(status_code=422, detail="test_cases must be a list")
    if len(cases) > EVALUATE_MAX_CASES:
        raise HTTPException(status_code=413, detail=f"At most {EVALUATE_MAX_CASES} test_cases per request")
    for case in cases:
        query = case.get("query") if isinstance(case, dict) else None
        if not isinstance(query, str) or not query.strip():
            raise HTTPException(status_code=422, detail="Each test case needs a non-empty string 'query'")
        if len(query) > EVALUATE_MAX_QUERY_CHARS:
            raise HTTPException(status_code=413, detail=f"query exceeds {EVALUATE_MAX_QUERY_CHARS} characters")

    results = []
    for case in cases:
        # Batch endpoint: stays 200 overall; failed cases carry error/error_detail in the list.
        with request_trace("/evaluate", case["query"]) as trace:
            result = orchestrator.process(case["query"], trace_id=trace.trace_id)
            annotate("http_status", http_status_for(result))
        emit(trace)
        results.append(result)
    return results
