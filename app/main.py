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

cw = boto3.client("logs", region_name="us-east-1")

try:
    cw.create_log_group(logGroupName=_LOG_GROUP)
except Exception:
    pass

try:
    cw.create_log_stream(logGroupName=_LOG_GROUP, logStreamName=_LOG_STREAM)
except Exception:
    pass


class QueryRequest(BaseModel):
    query: str


def _log(endpoint: str, query: str, latency_ms: float):
    entry = json.dumps({
        "timestamp": time.time(),
        "endpoint": endpoint,
        "query_preview": query[:100],
        "latency_ms": latency_ms,
    })
    try:
        cw.put_log_events(
            logGroupName=_LOG_GROUP,
            logStreamName=_LOG_STREAM,
            logEvents=[{"timestamp": int(time.time() * 1000), "message": entry}],
        )
    except Exception:
        pass


@app.post("/ask")
def ask(request: QueryRequest):
    start = time.monotonic()
    result = orchestrator.process(request.query)
    latency_ms = (time.monotonic() - start) * 1000
    _log("ask", request.query, latency_ms)
    return result


@app.post("/summarize")
def summarize(request: QueryRequest):
    start = time.monotonic()
    result = orchestrator.process_direct(request.query, "summarize")
    latency_ms = (time.monotonic() - start) * 1000
    _log("summarize", request.query, latency_ms)
    return result


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
