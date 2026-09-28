"""Request-scoped observability: stage latency, Bedrock token usage, cold starts.

One RequestTrace is active per request (held in a ContextVar). Instrumented code
calls the module-level helpers below; every helper is a no-op when no trace is
active, so services keep working from __main__ blocks and ad-hoc scripts.

Privacy: a trace never stores the user query. It keeps the query length and a
truncated SHA-256 digest (pseudonymous, not anonymous) for correlating repeats.
"""
import contextvars
import hashlib
import json
import time
import uuid
from contextlib import contextmanager

SCHEMA_VERSION = 1
_ERROR_MESSAGE_MAX_CHARS = 200

_PROCESS_START = time.monotonic()
_cold_start_pending = True

_current: contextvars.ContextVar["RequestTrace | None"] = contextvars.ContextVar(
    "copilot_request_trace", default=None
)


def consume_cold_start() -> bool:
    """Return True exactly once per process: for the first request it serves."""
    global _cold_start_pending
    was_pending = _cold_start_pending
    _cold_start_pending = False
    return was_pending


def reset_cold_start() -> None:
    """Test hook: make the next trace look like the first one in the process."""
    global _cold_start_pending
    _cold_start_pending = True


def query_digest(query: str) -> str | None:
    if not query:
        return None
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]


class RequestTrace:
    def __init__(self, endpoint: str, query: str = "", trace_id: str | None = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.endpoint = endpoint
        self.cold_start = consume_cold_start()
        self.process_age_ms = round((time.monotonic() - _PROCESS_START) * 1000, 1)
        self.query_chars = len(query)
        self.query_sha256_12 = query_digest(query)
        self.stages_ms: dict[str, float] = {}
        self.model_calls: list[dict] = []
        self.errors: list[dict] = []
        self.route: dict = {}
        self.attrs: dict = {}
        self.total_ms: float | None = None
        self._start = time.monotonic()

    def elapsed_ms(self) -> float:
        return (time.monotonic() - self._start) * 1000

    def add_stage(self, name: str, ms: float) -> None:
        # Accumulate so a stage entered twice (e.g. two retrieval calls) is not lost.
        self.stages_ms[name] = round(self.stages_ms.get(name, 0.0) + ms, 1)

    def add_model_call(
        self,
        name: str,
        model_id: str,
        input_tokens: int | None,
        output_tokens: int | None,
        latency_ms: float | None,
    ) -> None:
        self.model_calls.append({
            "name": name,
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
        })

    def add_error(self, stage: str, exc: BaseException) -> None:
        self.errors.append({
            "stage": stage,
            "type": type(exc).__name__,
            "message": str(exc)[:_ERROR_MESSAGE_MAX_CHARS],
        })

    def set_route(self, **fields) -> None:
        self.route.update(fields)

    def annotate(self, key: str, value) -> None:
        self.attrs[key] = value

    def finish(self) -> None:
        if self.total_ms is None:
            self.total_ms = round(self.elapsed_ms(), 1)

    def token_totals(self) -> dict:
        totals = {"input_tokens": 0, "output_tokens": 0}
        for call in self.model_calls:
            totals["input_tokens"] += call["input_tokens"] or 0
            totals["output_tokens"] += call["output_tokens"] or 0
        return totals

    def to_record(self) -> dict:
        return {
            "event": "request.timing",
            "schema_version": SCHEMA_VERSION,
            "trace_id": self.trace_id,
            "endpoint": self.endpoint,
            "cold_start": self.cold_start,
            "process_age_ms": self.process_age_ms,
            "query_chars": self.query_chars,
            "query_sha256_12": self.query_sha256_12,
            "total_ms": self.total_ms,
            "stages_ms": dict(self.stages_ms),
            "route": dict(self.route),
            "model_calls": list(self.model_calls),
            "tokens": self.token_totals(),
            "errors": list(self.errors),
            "attrs": dict(self.attrs),
        }


def current_trace() -> RequestTrace | None:
    return _current.get()


def current_trace_id() -> str:
    trace = _current.get()
    return trace.trace_id if trace else ""


@contextmanager
def request_trace(endpoint: str, query: str = "", trace_id: str | None = None):
    trace = RequestTrace(endpoint, query=query, trace_id=trace_id)
    token = _current.set(trace)
    try:
        yield trace
    finally:
        trace.finish()
        _current.reset(token)


@contextmanager
def stage(name: str):
    start = time.monotonic()
    try:
        yield
    finally:
        trace = _current.get()
        if trace is not None:
            trace.add_stage(name, (time.monotonic() - start) * 1000)


def record_converse_usage(name: str, model_id: str, response: dict) -> None:
    """Record token usage and server-side latency from a Bedrock Converse response."""
    trace = _current.get()
    if trace is None or not isinstance(response, dict):
        return
    usage = response.get("usage") or {}
    metrics = response.get("metrics") or {}
    trace.add_model_call(
        name,
        model_id,
        usage.get("inputTokens"),
        usage.get("outputTokens"),
        metrics.get("latencyMs"),
    )


def record_model_call(
    name: str,
    model_id: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    latency_ms: float | None = None,
) -> None:
    trace = _current.get()
    if trace is not None:
        trace.add_model_call(name, model_id, input_tokens, output_tokens, latency_ms)


def record_error(stage_name: str, exc: BaseException) -> None:
    trace = _current.get()
    if trace is not None:
        trace.add_error(stage_name, exc)


def record_failure(failure, fatal: bool = True) -> None:
    """Record an app.errors.ServiceFailure (already sanitized) on the active trace."""
    trace = _current.get()
    if trace is not None:
        trace.errors.append({**failure.to_log(), "type": failure.code or failure.kind, "fatal": fatal})


def set_route(**fields) -> None:
    trace = _current.get()
    if trace is not None:
        trace.set_route(**fields)


def annotate(key: str, value) -> None:
    trace = _current.get()
    if trace is not None:
        trace.annotate(key, value)


def emit(trace: RequestTrace) -> None:
    """Write the trace as one JSON line to stdout (Lambda ships stdout to CloudWatch)."""
    trace.finish()
    print(json.dumps(trace.to_record()))
