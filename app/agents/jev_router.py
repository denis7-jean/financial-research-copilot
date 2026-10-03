"""Binary Jev deployment candidate. Only invented HTTP transports are enabled.

No credentials are read and no real transport, retry, redirect or secondary
model exists here. Production enablement needs later review and authorization.
"""

import json
import math
import time

import httpx

from app.agents.routing_contract import RouterDecision
from app.errors import ServiceFailure
from app.observability import record_failure, record_model_call, set_route

MODEL = "jev-1.13.0"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
THRESHOLD = 0.6
CONNECT_TIMEOUT_S = 2.0
READ_TIMEOUT_S = 5.0
# Historical benchmark price assumptions, not a verified bill/current quotation.
INPUT_USD_PER_MTOK = 0.042
MAX_INPUT_TOKENS = 64_000
LABELS = ("qa", "summarize")
INSTRUCTIONS = "Classify this financial research query into exactly one category."
CRITERIA = {
    "qa": "The user wants a specific fact, figure, or answer retrieved from financial documents.\n"
    "Examples: revenue numbers, earnings per share, debt levels, headcount, specific dates, "
    "comparisons between two figures.",
    "summarize": "The user wants a high-level overview, narrative summary, or analysis of risks, themes, or trends.\n"
    "Examples: summarize annual report, explain key risks, describe business strategy, overview of performance.",
}


class JevOutputError(ValueError):
    """Fixed internal codes only; never include provider payloads."""


def payload(query: str) -> dict:
    if type(query) is not str or not query.strip() or len(query) > 300:
        raise JevOutputError("invalid_query")
    return {
        "state": query,
        "model": MODEL,
        "questions": {
            "route": {
                "type": "choice",
                "instructions": INSTRUCTIONS,
                "criteria": dict(CRITERIA),
            }
        },
    }


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_response(body):
    """Same pinned binary checks as the accepted benchmark; no score calibration."""
    if type(body) is not dict:
        raise JevOutputError("not_object")
    if body.get("model") != MODEL:
        raise JevOutputError("model_mismatch")
    answers = body.get("answers")
    answer = answers.get("route") if type(answers) is dict else None
    if type(answer) is not dict:
        raise JevOutputError("answers_missing")
    choice, probabilities = answer.get("choice"), answer.get("probabilities")
    if type(choice) is not str or choice not in LABELS:
        raise JevOutputError("bad_choice")
    if type(probabilities) is not dict or set(probabilities) != set(LABELS):
        raise JevOutputError("bad_probability_keys")
    if not all(_number(p) and 0 <= p <= 1 for p in probabilities.values()):
        raise JevOutputError("bad_probability_values")
    if abs(sum(probabilities.values()) - 1) > 1e-3:
        raise JevOutputError("probabilities_do_not_sum_to_1")
    if probabilities[choice] < max(probabilities.values()):
        raise JevOutputError("choice_not_argmax")
    confidence = answer.get("confidence")
    if not _number(confidence) or not 0 <= confidence <= 1:
        raise JevOutputError("bad_confidence")
    usage = body.get("usage")
    if type(usage) is not dict:
        raise JevOutputError("usage_missing")
    incoming, outgoing = usage.get("input_tokens"), usage.get("output_tokens")
    if type(incoming) is not int or incoming <= 0:
        raise JevOutputError("bad_input_tokens")
    if type(outgoing) is not int or outgoing < 0:
        raise JevOutputError("bad_output_tokens")
    return choice, float(probabilities[choice]), incoming, outgoing


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise JevOutputError("duplicate_json_key")
        result[key] = value
    return result


def _nonfinite(value):
    raise JevOutputError("nonfinite_json")


class JevRouterAgent:
    def __init__(self, *, transport):
        if type(transport) is not httpx.MockTransport:
            raise ServiceFailure("router", "configuration", "jev_live_disabled")
        self._http = httpx.Client(
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(READ_TIMEOUT_S, connect=CONNECT_TIMEOUT_S),
        )
        self.latency_ms = 0.0

    def close(self):
        self._http.close()

    def route(self, query: str, trace_id: str = "") -> RouterDecision:
        start = time.monotonic()
        fields = None
        code = None
        status = None
        kind = "invalid_model_output"
        attempted = False
        try:
            request = payload(query)
            attempted = True
            response = self._http.post(ENDPOINT, json=request)
            status = response.status_code
            if status != 200:
                kind = {
                    401: "access_denied",
                    403: "access_denied",
                    429: "throttled",
                    529: "unavailable",
                }.get(status, "unavailable" if status >= 500 else "configuration")
                code = "http_failure"
            elif len(response.content) > 65_536:
                code = "response_too_large"
            else:
                body = json.loads(
                    response.content.decode("utf-8"),
                    object_pairs_hook=_unique_object,
                    parse_constant=_nonfinite,
                )
                fields = validate_response(body)
        except httpx.TimeoutException:
            code, kind = "timeout", "timeout"
        except httpx.HTTPError:
            code, kind = "transport_failure", "unavailable"
        except JevOutputError as error:
            code = str(error)
        except (ValueError, UnicodeError):
            code = "not_json"
        except Exception:
            # Transport/mock defects carry no exception message or provider content.
            code, kind = "transport_failure", "unavailable"
        finally:
            self.latency_ms = (time.monotonic() - start) * 1000

        incoming, outgoing = fields[2:] if fields else (None, None)
        if attempted:
            record_model_call("router_jev", MODEL, incoming, outgoing, self.latency_ms)
        estimated = incoming * INPUT_USD_PER_MTOK / 1e6 if incoming else None
        set_route(
            router_provider="jev",
            router_live=False,
            router_attempts=int(attempted),
            router_latency_ms=round(self.latency_ms, 3),
            router_http_status=status,
            router_cost_usd=estimated,
            router_cost_basis="usage_estimate" if fields else "unknown",
            router_reservation_usd=MAX_INPUT_TOKENS * INPUT_USD_PER_MTOK / 1e6
            if attempted
            else 0,
        )
        if code:
            record_failure(ServiceFailure("router", kind, code), fatal=False)
            set_route(
                router_outcome="fallback_invoke_error"
                if kind != "invalid_model_output"
                else "fallback_schema_error",
                router_error_type=code,
            )
            return RouterDecision(task_type="qa", confidence=0.5, reasoning="fallback")
        choice, score = fields[:2]
        set_route(
            model_task_type=choice,
            model_confidence=score,
            router_outcome="fallback_low_confidence" if score < THRESHOLD else "model",
        )
        return RouterDecision(
            task_type="qa" if score < THRESHOLD else choice,
            confidence=0.5 if score < THRESHOLD else score,
            reasoning="fallback" if score < THRESHOLD else "jev_choice_probability",
        )
