"""The three routers under test, behind one interface: route(case) -> RouteRecord.

Every record keeps the raw prediction (the router's own label and score, before any
threshold) apart from the final decision (the production-equivalent rule of
RouterAgent). Haiku's self-reported confidence and Jev's choice probability are
recorded as raw scores; they are not assumed calibrated or equivalent.
"""
import hashlib
import json
import logging
import math
import os
import re
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from unittest import mock

import httpx

from experiments.router_bench.config import (
    DEFAULT_HAIKU_RESERVATION,
    FALLBACK_ROUTE,
    FINAL_DECISION_THRESHOLD,
    HAIKU_MAX_INPUT_TOKENS,
    HAIKU_MAX_OUTPUT_TOKENS,
    HAIKU_MODEL_ID,
    HAIKU_NOT_SENT_CODES,
    HAIKU_REJECTED_CODES,
    HAIKU_RESERVATIONS,
    JEV_CONNECT_TIMEOUT_S,
    JEV_ENDPOINT,
    JEV_MAX_TOKENS_PER_REQUEST,
    JEV_MODEL,
    JEV_PRICE_PER_MTOK_INPUT,
    JEV_READ_TIMEOUT_S,
)
from experiments.router_bench.payload import LABELS, ApprovedQuestions, build_jev_payload
from experiments.router_bench.safety import (
    LiveAuthorization,
    LiveCallNotAuthorized,
    SecretValue,
    contains_registered_secret,
    require_live,
    require_offline_fake,
)

# Never log request details (headers) from the HTTP stack.
for _name in ("httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)

HAIKU_PRICE = (1.00, 5.00)  # USD per 1M tokens (eval/metrics.py PRICES_PER_MTOK, Haiku 4.5)


def haiku_cost(input_tokens: int, output_tokens: int) -> float:
    return input_tokens * HAIKU_PRICE[0] / 1e6 + output_tokens * HAIKU_PRICE[1] / 1e6


def jev_cost(input_tokens: int) -> float:
    return input_tokens * JEV_PRICE_PER_MTOK_INPUT / 1e6


def haiku_reservation_usd(mode: str) -> float:
    return haiku_cost(*HAIKU_RESERVATIONS[mode])


HAIKU_MAX_CALL_USD = haiku_cost(HAIKU_MAX_INPUT_TOKENS, HAIKU_MAX_OUTPUT_TOKENS)  # $0.322 under the assumptions
JEV_WORST_CASE_USD = jev_cost(JEV_MAX_TOKENS_PER_REQUEST)


class ModelNotPinned(RuntimeError):
    """The Bedrock model is not the pinned Haiku 4.5: pricing and caps would be wrong, so refuse."""


@dataclass
class RouteRecord:
    router: str
    case_id: str
    raw_label: str | None  # the router's own label; None when there is none (error, unparseable)
    raw_score: float | None  # Haiku: self-reported confidence; Jev: probabilities[choice]; rules: None
    final_label: str  # production-equivalent decision
    outcome: str  # model | rules | fallback_low_score | fallback_invoke_error | fallback_parse_error |
    #               fallback_schema_error | fallback_harness_error
    latency_ms: float
    infra_error: bool = False
    error_class: str | None = None
    http_status: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None  # from recorded usage; None when unknown (runner charges worst case)
    cost_basis: str = "none"  # usage | worst_case_reservation | none
    repetition: int = 0  # 0 = warm-up
    warmup: bool = False
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def final_decision(raw_label: str | None, raw_score: float | None, outcome_if_missing: str) -> tuple[str, str]:
    """RouterAgent's rule: no raw label -> qa; score below 0.6 -> qa; else the raw label."""
    if raw_label is None:
        return FALLBACK_ROUTE, outcome_if_missing
    if raw_score is not None and raw_score < FINAL_DECISION_THRESHOLD:
        return FALLBACK_ROUTE, "fallback_low_score"
    return raw_label, "model"


# --- Haiku 4.5: the existing RouterAgent, unchanged --------------------------------------------------

@contextmanager
def _dotenv_disabled():
    """app.agents.router calls load_dotenv() when first imported; keep it from reading .env."""
    previous = os.environ.get("PYTHON_DOTENV_DISABLED")
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("PYTHON_DOTENV_DISABLED", None)
        else:
            os.environ["PYTHON_DOTENV_DISABLED"] = previous


def _import_router_agent():
    with _dotenv_disabled():
        from app.agents.router import RouterAgent
    return RouterAgent


@contextmanager
def _patched_boto3_client(fake):
    """Build RouterAgent around an injected fake, without creating (or resolving credentials for) a real client."""
    import app.agents.router as router_module

    with mock.patch.object(router_module.boto3, "client", lambda *args, **kwargs: fake):
        yield


def _check_pinned_model(model_id) -> None:
    if model_id != HAIKU_MODEL_ID:
        raise ModelNotPinned("the configured Bedrock model is not the pinned Haiku 4.5 model "
                             f"({HAIKU_MODEL_ID}); refusing, because pricing and caps assume it")


class HaikuRouter:
    name = "haiku"
    provider = "bedrock"

    def __init__(self, *, bedrock_client=None, authorization: LiveAuthorization | None = None,
                 reservation: str = DEFAULT_HAIKU_RESERVATION):
        if reservation not in HAIKU_RESERVATIONS:
            raise ValueError(f"reservation must be one of {sorted(HAIKU_RESERVATIONS)}")
        # Authorization first: nothing below may import app code (and so .env) or build a client before it.
        if bedrock_client is not None:
            require_offline_fake(bedrock_client, "bedrock")
        else:
            require_live(authorization, "bedrock")
        # RouterAgent reads BEDROCK_MODEL_ID (default: the pinned model). Fail closed before any client exists.
        _check_pinned_model(os.environ.get("BEDROCK_MODEL_ID", HAIKU_MODEL_ID))
        RouterAgent = _import_router_agent()
        if bedrock_client is not None:
            with _patched_boto3_client(bedrock_client):
                self.agent = RouterAgent()
            self.live = False
        else:
            os.environ["AWS_MAX_ATTEMPTS"] = "1"  # one billed request per routed call: no silent SDK retries
            self.agent = RouterAgent()
            if self.agent._client.meta.config.retries.get("total_max_attempts") != 1:
                raise RuntimeError("the Bedrock client would retry; refusing a live run")
            self.live = True
        _check_pinned_model(self.agent._model_id)
        self.model_id = self.agent._model_id
        self.reservation = reservation
        self.worst_case_usd = haiku_reservation_usd(reservation)

    def route(self, case) -> RouteRecord:
        from app.observability import request_trace

        with request_trace("router_bench", case.query) as trace:
            start = time.perf_counter()
            decision = self.agent.route(case.query, trace_id=trace.trace_id)
            latency_ms = (time.perf_counter() - start) * 1000
        record = trace.to_record()
        route = record["route"]
        outcome = route.get("router_outcome")
        errors = record["errors"]
        calls = record["model_calls"]
        for call in calls:  # every recorded call must have used the pinned model (the run stops otherwise)
            _check_pinned_model(call.get("model_id"))
        input_tokens = sum(c.get("input_tokens") or 0 for c in calls) if calls else None
        output_tokens = sum(c.get("output_tokens") or 0 for c in calls) if calls else None
        server_latency = next((c.get("latency_ms") for c in calls if c.get("latency_ms") is not None), None)

        if outcome == "model":
            raw_label, raw_score = decision.task_type, decision.confidence
        elif outcome == "fallback_low_confidence":
            raw_label, raw_score = route.get("model_task_type"), route.get("model_confidence")
        else:
            raw_label, raw_score = None, None
        missing_outcome = "fallback_invoke_error" if outcome == "fallback_invoke_error" else "fallback_parse_error"
        final_label, final_outcome = final_decision(raw_label, raw_score, missing_outcome)
        extra = {"router_outcome": outcome, "server_latency_ms": server_latency}
        if final_label != decision.task_type:  # our rule must reproduce RouterAgent's own decision
            extra["decision_mismatch"] = decision.task_type
        last_error = errors[-1] if errors else {}
        code = last_error.get("code")
        if calls:
            cost_usd, cost_basis = haiku_cost(input_tokens, output_tokens), "usage"
        elif outcome == "fallback_invoke_error" and code in HAIKU_NOT_SENT_CODES:
            cost_usd, cost_basis = 0.0, "not_sent"
        elif outcome == "fallback_invoke_error" and code in HAIKU_REJECTED_CODES:
            cost_usd, cost_basis = 0.0, "rejected_assumed_unbilled"
        else:
            cost_usd, cost_basis = None, "none"  # unknown: the runner charges the full reservation
        return RouteRecord(
            router=self.name, case_id=case.id, raw_label=raw_label, raw_score=raw_score,
            final_label=final_label, outcome=final_outcome, latency_ms=round(latency_ms, 3),
            infra_error=outcome == "fallback_invoke_error",
            error_class=code or last_error.get("kind"),
            input_tokens=input_tokens, output_tokens=output_tokens,
            cost_usd=cost_usd, cost_basis=cost_basis, extra=extra,
        )


# --- Deterministic rules (experiment-only) -----------------------------------------------------------

# Written only from RouterAgent's taxonomy text ("summarize": overview, narrative summary,
# analysis of risks, themes or trends; examples: summarize, explain key risks, describe
# strategy, overview). Anything else is "qa". Frozen: see RULES_SHA256.
SUMMARIZE_PATTERNS = (
    r"\bsummar", r"\boverview\b", r"\bexplain", r"\bdescrib", r"\banaly[sz]",
    r"\brisks?\b", r"\bthemes?\b", r"\btrends?\b", r"\bstrateg",
)


def rules_fingerprint() -> str:
    spec = {"summarize_patterns": list(SUMMARIZE_PATTERNS), "default": "qa", "flags": "IGNORECASE"}
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()


RULES_SHA256 = "86cea35d458a75af6456803eec068b288dab748d0d001ef89a1f43ec8b352ab9"


class RulesRouter:
    name = "rules"
    provider = None
    worst_case_usd = 0.0

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE) for p in SUMMARIZE_PATTERNS]

    def route(self, case) -> RouteRecord:
        start = time.perf_counter()
        label = "summarize" if any(p.search(case.query) for p in self._patterns) else "qa"
        latency_ms = (time.perf_counter() - start) * 1000
        return RouteRecord(router=self.name, case_id=case.id, raw_label=label, raw_score=None,
                           final_label=label, outcome="rules", latency_ms=round(latency_ms, 4),
                           cost_usd=0.0, cost_basis="usage")


# --- TypeSafe Jev --------------------------------------------------------------------------------------

class JevSchemaError(RuntimeError):
    """A 200 response that does not match the documented contract.

    Carries a fixed code only: no server-controlled text ever reaches a message,
    a record or an artifact.
    """

    CODES = frozenset({
        "not_json", "not_object", "model_mismatch", "answers_missing", "bad_choice", "bad_probability_keys",
        "bad_probability_values", "probabilities_do_not_sum_to_1", "choice_not_argmax", "bad_confidence",
        "usage_missing", "bad_input_tokens", "bad_output_tokens",
    })

    def __init__(self, code: str):
        if code not in self.CODES:
            raise ValueError(f"unknown schema error code {code!r}")
        super().__init__(code)
        self.code = code


class JevCallError(RuntimeError):
    """The call failed (HTTP error, timeout, transport). Carries a class name and status only."""

    def __init__(self, error_class: str, http_status: int | None = None):
        super().__init__(error_class if http_status is None else f"{error_class} (HTTP {http_status})")
        self.error_class = error_class
        self.http_status = http_status


_STATUS_CLASSES = {401: "auth", 403: "auth", 422: "contract", 429: "throttled", 529: "overloaded"}
ALLOWED_RESPONSE_HEADERS = ("x-request-id", "request-id", "date")
ALLOWED_RESPONSE_HEADER_PREFIXES = ("x-ratelimit-",)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


_SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")
_SAFE_HEADER_VALUE = re.compile(r"^[\x20-\x7e]{0,128}$")
MAX_REPORTED_NAMES = 20


def _safe_names(names) -> list[str]:
    """Server-controlled field names, reduced to short identifiers; anything else is redacted."""
    kept = sorted(n if isinstance(n, str) and _SAFE_NAME.match(n) else "<redacted>" for n in names)
    return kept[:MAX_REPORTED_NAMES] + ([f"<{len(kept) - MAX_REPORTED_NAMES} more>"] if len(kept) > MAX_REPORTED_NAMES else [])


def _safe_header_value(value: str) -> str:
    if not _SAFE_HEADER_VALUE.match(value) or "bearer" in value.lower() or contains_registered_secret(value):
        return "<redacted>"
    return value


def validate_jev_response(body) -> dict:
    """The design §7 schema checks. Returns the parsed fields; raises JevSchemaError(code)."""
    if not isinstance(body, dict):
        raise JevSchemaError("not_object")
    if body.get("model") != JEV_MODEL:
        raise JevSchemaError("model_mismatch")
    try:
        answer = body["answers"]["route"]
    except (KeyError, TypeError):
        raise JevSchemaError("answers_missing") from None
    if not isinstance(answer, dict):
        raise JevSchemaError("answers_missing")
    choice, probabilities, confidence = answer.get("choice"), answer.get("probabilities"), answer.get("confidence")
    if not isinstance(choice, str) or choice not in LABELS:
        raise JevSchemaError("bad_choice")
    if not isinstance(probabilities, dict) or set(probabilities) != set(LABELS):
        raise JevSchemaError("bad_probability_keys")
    if not all(_is_number(p) and 0.0 <= p <= 1.0 for p in probabilities.values()):
        raise JevSchemaError("bad_probability_values")
    if abs(sum(probabilities.values()) - 1.0) > 1e-3:
        raise JevSchemaError("probabilities_do_not_sum_to_1")
    if probabilities[choice] < max(probabilities.values()):
        raise JevSchemaError("choice_not_argmax")
    if not _is_number(confidence) or not 0.0 <= confidence <= 1.0:
        raise JevSchemaError("bad_confidence")
    usage = body.get("usage")
    if not isinstance(usage, dict):
        raise JevSchemaError("usage_missing")
    input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
    if not (isinstance(input_tokens, int) and not isinstance(input_tokens, bool) and input_tokens > 0):
        raise JevSchemaError("bad_input_tokens")
    if not (isinstance(output_tokens, int) and not isinstance(output_tokens, bool) and output_tokens >= 0):
        raise JevSchemaError("bad_output_tokens")
    return {
        "choice": choice, "probabilities": {k: float(v) for k, v in probabilities.items()},
        "confidence": float(confidence), "model": JEV_MODEL,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "extra_fields": _safe_names(set(body) - {"model", "answers", "usage"}),
        "extra_answer_fields": _safe_names(set(answer) - {"choice", "probabilities", "confidence"}),
    }


class JevClient:
    """HTTP client for jev-1.13.0. No retries, no redirects, no environment proxies or .netrc.

    A real network transport requires a LiveAuthorization for typesafe and an API key;
    tests and dry runs inject an httpx.MockTransport instead. Any other injected
    transport is treated as real, so injection cannot bypass the live opt-in.
    """

    def __init__(self, *, transport: httpx.BaseTransport | None = None,
                 authorization: LiveAuthorization | None = None, api_key: SecretValue | None = None):
        if api_key is not None and not isinstance(api_key, SecretValue):
            raise TypeError("api_key must be a SecretValue")
        if transport is None:
            require_live(authorization, "typesafe")
            if api_key is None:
                raise ValueError("a live Jev client needs TYPESAFE_API_KEY")
            transport = httpx.HTTPTransport(retries=0)
            self.live = True
        elif isinstance(transport, httpx.MockTransport):
            self.live = False
        else:
            raise LiveCallNotAuthorized(
                "typesafe: only an httpx.MockTransport may be injected; real transports are built by the "
                "client itself, behind a LiveAuthorization")
        self._api_key = api_key
        self._http = httpx.Client(
            transport=transport, trust_env=False, follow_redirects=False,
            timeout=httpx.Timeout(JEV_READ_TIMEOUT_S, connect=JEV_CONNECT_TIMEOUT_S),
        )

    def post(self, payload: dict) -> tuple[dict, dict]:
        """Returns (validated fields, allowlisted response headers)."""
        headers = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key.reveal()}"
        try:
            response = self._http.post(JEV_ENDPOINT, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise JevCallError("timeout") from None
        except httpx.HTTPError as exc:
            raise JevCallError(f"transport:{type(exc).__name__}") from None
        except Exception as exc:  # e.g. the offline guard's NetworkBlockedError; never echo the message
            raise JevCallError(f"transport:{type(exc).__name__}") from None
        kept = {k.lower(): _safe_header_value(v) for k, v in response.headers.items()
                if k.lower() in ALLOWED_RESPONSE_HEADERS or k.lower().startswith(ALLOWED_RESPONSE_HEADER_PREFIXES)}
        if response.status_code != 200:
            status = response.status_code
            raise JevCallError(_STATUS_CLASSES.get(status, "unavailable" if status >= 500 else "http_error"), status)
        try:
            body = response.json()
        except ValueError:
            raise JevSchemaError("not_json") from None
        return validate_jev_response(body), kept

    def close(self) -> None:
        self._http.close()


class JevRouter:
    name = "jev"
    provider = "typesafe"
    worst_case_usd = JEV_WORST_CASE_USD

    def __init__(self, client: JevClient, approved: ApprovedQuestions):
        self.client = client
        self.approved = approved

    def route(self, case) -> RouteRecord:
        payload = build_jev_payload(case, self.approved)  # allowlist + frozen template, before any I/O
        start = time.perf_counter()
        try:
            fields, headers = self.client.post(payload)
        except JevCallError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            return RouteRecord(router=self.name, case_id=case.id, raw_label=None, raw_score=None,
                               final_label=FALLBACK_ROUTE, outcome="fallback_invoke_error",
                               latency_ms=round(latency_ms, 3), infra_error=True, error_class=exc.error_class,
                               http_status=exc.http_status)
        except JevSchemaError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            return RouteRecord(router=self.name, case_id=case.id, raw_label=None, raw_score=None,
                               final_label=FALLBACK_ROUTE, outcome="fallback_schema_error",
                               latency_ms=round(latency_ms, 3), error_class=f"schema:{exc.code}")
        latency_ms = (time.perf_counter() - start) * 1000
        raw_label, raw_score = fields["choice"], fields["probabilities"][fields["choice"]]
        final_label, outcome = final_decision(raw_label, raw_score, "fallback_schema_error")
        return RouteRecord(
            router=self.name, case_id=case.id, raw_label=raw_label, raw_score=raw_score,
            final_label=final_label, outcome=outcome, latency_ms=round(latency_ms, 3),
            input_tokens=fields["input_tokens"], output_tokens=fields["output_tokens"],
            cost_usd=jev_cost(fields["input_tokens"]), cost_basis="usage",
            extra={"jev_confidence": fields["confidence"], "jev_probabilities": fields["probabilities"],
                   "jev_model": fields["model"], "extra_fields": fields["extra_fields"],
                   "extra_answer_fields": fields["extra_answer_fields"], "response_headers": headers},
        )
