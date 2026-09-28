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
import re
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from unittest import mock

import httpx

from experiments.router_bench.config import (
    FALLBACK_ROUTE,
    FINAL_DECISION_THRESHOLD,
    HAIKU_WORST_CASE_TOKENS,
    JEV_CONNECT_TIMEOUT_S,
    JEV_ENDPOINT,
    JEV_MAX_TOKENS_PER_REQUEST,
    JEV_MODEL,
    JEV_PRICE_PER_MTOK_INPUT,
    JEV_READ_TIMEOUT_S,
)
from experiments.router_bench.payload import LABELS, ApprovedQuestions, build_jev_payload
from experiments.router_bench.safety import LiveAuthorization, SecretValue, require_live

# Never log request details (headers) from the HTTP stack.
for _name in ("httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)

HAIKU_PRICE = (1.00, 5.00)  # USD per 1M tokens (eval/metrics.py PRICES_PER_MTOK, Haiku 4.5)


def haiku_cost(input_tokens: int, output_tokens: int) -> float:
    return input_tokens * HAIKU_PRICE[0] / 1e6 + output_tokens * HAIKU_PRICE[1] / 1e6


def jev_cost(input_tokens: int) -> float:
    return input_tokens * JEV_PRICE_PER_MTOK_INPUT / 1e6


HAIKU_WORST_CASE_USD = haiku_cost(*HAIKU_WORST_CASE_TOKENS)
JEV_WORST_CASE_USD = jev_cost(JEV_MAX_TOKENS_PER_REQUEST)


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
def _patched_boto3_client(fake):
    """Build RouterAgent around an injected client, without creating (or resolving credentials for) a real one."""
    import app.agents.router as router_module

    with mock.patch.object(router_module.boto3, "client", lambda *args, **kwargs: fake):
        yield


class HaikuRouter:
    name = "haiku"
    provider = "bedrock"
    worst_case_usd = HAIKU_WORST_CASE_USD

    def __init__(self, *, bedrock_client=None, authorization: LiveAuthorization | None = None):
        from app.agents.router import RouterAgent

        if bedrock_client is not None:
            with _patched_boto3_client(bedrock_client):
                self.agent = RouterAgent()
            self.live = False
        else:
            require_live(authorization, "bedrock")
            self.agent = RouterAgent()
            self.live = True
        self.model_id = self.agent._model_id

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
        return RouteRecord(
            router=self.name, case_id=case.id, raw_label=raw_label, raw_score=raw_score,
            final_label=final_label, outcome=final_outcome, latency_ms=round(latency_ms, 3),
            infra_error=outcome == "fallback_invoke_error",
            error_class=last_error.get("code") or last_error.get("kind"),
            input_tokens=input_tokens, output_tokens=output_tokens,
            cost_usd=haiku_cost(input_tokens, output_tokens) if calls else None,
            cost_basis="usage" if calls else "none", extra=extra,
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
    """A 200 response that does not match the documented contract."""


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


def validate_jev_response(body) -> dict:
    """The design §7 schema checks. Returns the parsed fields; raises JevSchemaError."""
    if not isinstance(body, dict):
        raise JevSchemaError("body is not a JSON object")
    if body.get("model") != JEV_MODEL:
        raise JevSchemaError(f"model is {body.get('model')!r}, expected the pinned {JEV_MODEL}")
    try:
        answer = body["answers"]["route"]
    except (KeyError, TypeError):
        raise JevSchemaError("answers.route missing") from None
    choice, probabilities, confidence = answer.get("choice"), answer.get("probabilities"), answer.get("confidence")
    if choice not in LABELS:
        raise JevSchemaError(f"choice {choice!r} is not one of {LABELS}")
    if not isinstance(probabilities, dict) or set(probabilities) != set(LABELS):
        raise JevSchemaError("probabilities must have exactly the keys qa and summarize")
    if not all(_is_number(p) and 0.0 <= p <= 1.0 for p in probabilities.values()):
        raise JevSchemaError("probabilities must be numbers in [0, 1]")
    if abs(sum(probabilities.values()) - 1.0) > 1e-3:
        raise JevSchemaError("probabilities do not sum to 1")
    if probabilities[choice] < max(probabilities.values()):
        raise JevSchemaError("choice is not the most probable option")
    if not _is_number(confidence) or not 0.0 <= confidence <= 1.0:
        raise JevSchemaError("confidence must be a number in [0, 1]")
    usage = body.get("usage")
    if not isinstance(usage, dict):
        raise JevSchemaError("usage missing")
    input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
    if not (isinstance(input_tokens, int) and not isinstance(input_tokens, bool) and input_tokens > 0):
        raise JevSchemaError("usage.input_tokens must be a positive integer")
    if not (isinstance(output_tokens, int) and not isinstance(output_tokens, bool) and output_tokens >= 0):
        raise JevSchemaError("usage.output_tokens must be a non-negative integer")
    return {
        "choice": choice, "probabilities": dict(probabilities), "confidence": confidence, "model": body["model"],
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "extra_fields": sorted(set(body) - {"model", "answers", "usage"}),
        "extra_answer_fields": sorted(set(answer) - {"choice", "probabilities", "confidence"}),
    }


class JevClient:
    """HTTP client for jev-1.13.0. No retries, no redirects, no environment proxies or .netrc.

    A real network transport requires a LiveAuthorization for typesafe and an API key;
    tests and dry runs inject an httpx.MockTransport instead.
    """

    def __init__(self, *, transport: httpx.BaseTransport | None = None,
                 authorization: LiveAuthorization | None = None, api_key: SecretValue | None = None):
        if transport is None:
            require_live(authorization, "typesafe")
            if api_key is None:
                raise ValueError("a live Jev client needs TYPESAFE_API_KEY")
            transport = httpx.HTTPTransport(retries=0)
            self.live = True
        else:
            self.live = False
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
        kept = {k.lower(): v for k, v in response.headers.items()
                if k.lower() in ALLOWED_RESPONSE_HEADERS or k.lower().startswith(ALLOWED_RESPONSE_HEADER_PREFIXES)}
        if response.status_code != 200:
            status = response.status_code
            raise JevCallError(_STATUS_CLASSES.get(status, "unavailable" if status >= 500 else "http_error"), status)
        try:
            body = response.json()
        except ValueError:
            raise JevSchemaError("response is not JSON") from None
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
                               latency_ms=round(latency_ms, 3), error_class=f"schema:{exc}")
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
