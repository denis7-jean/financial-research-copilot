import json
import os
import time

import boto3
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from app.agents.orchestrator import CopilotOrchestrator
from app.observability import RequestTrace, emit, request_trace, stage

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


@app.post("/ask")
def ask(request: QueryRequest):
    with request_trace("/ask", request.query) as trace:
        start = time.monotonic()
        result = orchestrator.process(request.query, trace_id=trace.trace_id)
        latency_ms = (time.monotonic() - start) * 1000
        _log("/ask", latency_ms, trace)
    emit(trace)
    return {**result, "trace_id": trace.trace_id}


@app.post("/summarize")
def summarize(request: QueryRequest):
    with request_trace("/summarize", request.query) as trace:
        start = time.monotonic()
        result = orchestrator.process_direct(request.query, "summarize", trace_id=trace.trace_id)
        latency_ms = (time.monotonic() - start) * 1000
        _log("/summarize", latency_ms, trace)
    emit(trace)
    return {**result, "trace_id": trace.trace_id}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "region": os.getenv("AWS_DEFAULT_REGION"),
        "timestamp": time.time(),
    }


@app.post("/evaluate")
def evaluate(payload: dict):
    results = []
    for case in payload.get("test_cases", []):
        result = orchestrator.process(case["query"])
        results.append(result)
    return results
