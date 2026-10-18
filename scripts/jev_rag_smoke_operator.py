"""Offline injected parent seam. No SDK, credentials, live CLI or approval grant.

Simulation and adapter-backed consumption have distinct explicit plan contracts.
Factories are injected; this module supplies no SDK or credential entry point.
Hooks and local evidence are not authenticated observers or execution authority.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math
import os
import re
import sys
import time
from urllib.parse import quote

from app import rag_smoke_handler as handler
from app.services.rag_smoke_policy import SmokeStop, canonical, digest, strict_json
from scripts import jev_rag_smoke_preinvoke as p0

PLAN_SCHEMA = "jev-rag-smoke-operator-plan-v1"
INDEX_SCHEMA = "jev-rag-smoke-operator-index-v1"
ADAPTER_PLAN_SCHEMA = "jev-rag-smoke-adapter-operator-plan-v1"
ADAPTER_INDEX_SCHEMA = "jev-rag-smoke-adapter-operator-index-v1"
ADAPTER_MODE = "ADAPTER_BACKED"
TAIL_PLAN_SCHEMA = "jev-rag-smoke-adapter-operator-plan-v2"
TAIL_INDEX_SCHEMA = "jev-rag-smoke-adapter-operator-index-v2"
TAIL_MODE = "ADAPTER_BACKED_TAIL"
TAIL_PARSER_CONTRACT = "jev-rag-smoke-platform-report-v1"
MAX_LOG_BYTES = 65_536
RESPONSE_LIMIT = handler.MAX_RESULT_BYTES
SERIAL_ERRORS = (ValueError, TypeError, UnicodeError, RecursionError, OverflowError)
ID = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")
RESULT_KEYS = set(handler.response("STOPPED", "INPUT_INVALID"))
ERROR_CODES = frozenset(
    "HASH_BINDINGS_REQUIRED INPUT_INVALID INPUT_HASH_MISMATCH PLAN_INVALID "
    "PLAN_NOT_CANONICAL PLAN_BINDING_MISMATCH TARGET_INVALID INVOCATION_INVALID "
    "INVOCATION_NOT_CANONICAL INVOCATION_INPUT_MISMATCH EVENT_BINDING_MISMATCH "
    "RUN_BINDING_MISMATCH CLOCK_INVALID PUBLICATION_FAILED SERIALIZATION_FAILED "
    "RECORD_TOO_LARGE PARENT_REQUEST_INVALID PARENT_SEND_BLOCKED SIMULATED_CLIENT_REQUIRED "
    "CLIENT_CONFIG_INVALID PARENT_RESPONSE_INVALID PARENT_BODY_INVALID PARENT_BODY_TOO_LARGE "
    "PARENT_OUTCOME_UNKNOWN PARENT_CLOSE_FAILED HANDLER_RESULT_INVALID "
    "HANDLER_SCHEMA_UNSUPPORTED HANDLER_RESULT_CONTRADICTORY LOG_BINDING_MISMATCH LOG_INVALID "
    "LOG_REQUEST_MISMATCH REPORT_INVALID PARENT_HOOKS_INVALID PARENT_RETRY_INVALID "
    "PARENT_REQUEST_ID_INVALID PARENT_STATUS_INVALID PARENT_VERSION_INVALID "
    "PARENT_VERSION_MISMATCH LOCAL_OPERATION_FAILED CLIENT_CLOSE_FAILED "
    "PUBLICATION_UNCONFIRMED CONSOLE_CONFIRMATION_UNAVAILABLE OPERATOR_FAILED "
    "TRUST_BINDINGS_REQUIRED PRICE_EVIDENCE_REQUIRED POLICY_INVALID "
    "PLAN_SERIALIZATION_FAILED POLICY_SERIALIZATION_FAILED POLICY_NOT_CANONICAL "
    "POLICY_BINDING_MISMATCH PRICE_BINDING_MISMATCH REFERENCE_INVALID LIMITS_INVALID "
    "PARENT_ATTEMPTS_INVALID PARENT_TIMEOUT_INVALID POLICY_OR_PRICE_EVIDENCE_INVALID "
    "CEILING_BINDING_MISMATCH EXPECTED_SOURCE_IMPOSSIBLE HAIKU_CEILING_INSUFFICIENT "
    "TITAN_CEILING_INSUFFICIENT TOTAL_CEILING_INSUFFICIENT CLAIM_ROOT_INVALID "
    "CLAIM_SERIALIZATION_FAILED EXECUTION_ALREADY_CLAIMED CLAIM_CREATE_FAILED "
    "CLAIM_PUBLICATION_FAILED_RETAINED CLAIM_INTERRUPTED_RETAINED CLAIM_READ_FAILED_RETAINED "
    "PARENT_SERVICE_ERROR PARENT_DEFECT_PROPAGATED OPERATOR_DEFECT_PROPAGATED "
    "PARENT_ALREADY_ATTEMPTED CLIENT_FACTORY_REQUIRED PARENT_LOG_MISSING "
    "PARENT_LOG_INVALID REPORT_INVALID".split()
)


class OperatorError(ValueError):
    """Expected errors have fixed, non-sensitive codes."""

    def __init__(self, code):
        super().__init__(
            code if type(code) is str and code in ERROR_CODES else "OPERATOR_FAILED"
        )


def require(condition, code):
    if not condition:
        raise OperatorError(code) from None


def exact(value, keys, code):
    require(type(value) is dict and set(value) == set(keys), code)


def encode(value):
    try:
        return canonical(value)
    except SERIAL_ERRORS:
        raise OperatorError("SERIALIZATION_FAILED") from None


def parse(raw, limit, code):
    require(type(raw) is bytes and 0 < len(raw) <= limit, code)
    try:
        return strict_json(raw)
    except (SmokeStop, *SERIAL_ERRORS):
        raise OperatorError(code) from None


def _validate(
    plan_raw,
    p0_raw,
    invocation_raw,
    policy_raw,
    *,
    evidence,
    hashes,
    root,
    schema,
    mode,
):
    """All joins before claims or factories. Separately supplied hashes are not authority."""
    exact(
        hashes,
        {"operator", "plan", "invocation", "policy", "haiku", "titan"},
        "HASH_BINDINGS_REQUIRED",
    )
    require(
        all(p0.hash_value(value) for value in hashes.values()), "HASH_BINDINGS_REQUIRED"
    )
    for name, raw in (("operator", plan_raw), ("invocation", invocation_raw)):
        require(
            type(raw) is bytes and 0 < len(raw) <= handler.MAX_EVENT_BYTES,
            "INPUT_INVALID",
        )
        require(digest(raw) == hashes[name], "INPUT_HASH_MISMATCH")
    try:
        preflight = p0.validate(
            p0_raw,
            policy_raw,
            evidence=evidence,
            expected_hashes={
                key: hashes[key] for key in ("plan", "policy", "haiku", "titan")
            },
        )
        parent = p0.persistent_root(root)
    except p0.PreinvokeError as error:
        raise OperatorError(str(error)) from None
    plan = parse(plan_raw, handler.MAX_EVENT_BYTES, "PLAN_INVALID")
    require(encode(plan) == plan_raw, "PLAN_NOT_CANONICAL")
    exact(
        plan,
        {"schema", "mode", "p0_plan_sha256", "invocation_sha256", "target"}
        | ({"log_type", "parser_contract"} if schema == TAIL_PLAN_SCHEMA else set()),
        "PLAN_INVALID",
    )
    require(
        plan["schema"] == schema and plan["mode"] == mode,
        "PLAN_INVALID",
    )
    if schema == TAIL_PLAN_SCHEMA:
        require(
            plan["log_type"] == "Tail"
            and plan["parser_contract"] == TAIL_PARSER_CONTRACT,
            "PLAN_INVALID",
        )
    require(
        plan["p0_plan_sha256"] == hashes["plan"]
        and plan["invocation_sha256"] == hashes["invocation"],
        "PLAN_BINDING_MISMATCH",
    )
    target = plan["target"]
    exact(target, {"account", "region", "function_name", "qualifier"}, "TARGET_INVALID")
    require(
        type(target["account"]) is str
        and re.fullmatch(r"[0-9]{12}", target["account"]),
        "TARGET_INVALID",
    )
    require(
        target["region"] == "us-east-1"
        and type(target["function_name"]) is str
        and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", target["function_name"]),
        "TARGET_INVALID",
    )
    require(
        type(target["qualifier"]) is str
        and (
            target["qualifier"] == "$LATEST"
            or re.fullmatch(r"[1-9][0-9]{0,19}", target["qualifier"])
        ),
        "TARGET_INVALID",
    )
    event = parse(invocation_raw, handler.MAX_EVENT_BYTES, "INVOCATION_INVALID")
    require(encode(event) == invocation_raw, "INVOCATION_NOT_CANONICAL")
    try:
        checked = handler.validate(event, hashes["invocation"], parent, None)
    except handler.EnvelopeError:
        raise OperatorError("INVOCATION_INVALID") from None
    # Actual handler validation above, plus byte-identical P0/event inputs.
    require(
        event["policy_utf8"].encode() == policy_raw
        and {k: v.encode() for k, v in event["evidence_utf8"].items()} == evidence,
        "INVOCATION_INPUT_MISMATCH",
    )
    original = parse(p0_raw, p0.MAX_INPUT_BYTES, "PLAN_INVALID")
    require(
        original["references"]["event_sha256"] == hashes["invocation"],
        "EVENT_BINDING_MISMATCH",
    )
    require(checked.config["run_id"] == original["run_id"], "RUN_BINDING_MISMATCH")
    return plan, original, preflight, parent


def validate(plan_raw, p0_raw, invocation_raw, policy_raw, *, evidence, hashes, root):
    """Legacy simulation validation; adapter-backed plans cannot enter simulate."""
    return _validate(
        plan_raw,
        p0_raw,
        invocation_raw,
        policy_raw,
        evidence=evidence,
        hashes=hashes,
        root=root,
        schema=PLAN_SCHEMA,
        mode="SIMULATED_OFFLINE",
    )


def validate_adapter(
    plan_raw, p0_raw, invocation_raw, policy_raw, *, evidence, hashes, root
):
    """Adapter plan validation only; a hash match confers no invocation authority."""
    candidate = parse(plan_raw, handler.MAX_EVENT_BYTES, "PLAN_INVALID")
    tail = type(candidate) is dict and candidate.get("schema") == TAIL_PLAN_SCHEMA
    return _validate(
        plan_raw,
        p0_raw,
        invocation_raw,
        policy_raw,
        evidence=evidence,
        hashes=hashes,
        root=root,
        schema=TAIL_PLAN_SCHEMA if tail else ADAPTER_PLAN_SCHEMA,
        mode=TAIL_MODE if tail else ADAPTER_MODE,
    )


def clock_sample(utc, monotonic):
    try:
        stamp, tick = utc(), monotonic()
        require(type(stamp) is str and stamp.endswith("Z"), "CLOCK_INVALID")
        parsed = datetime.fromisoformat(stamp[:-1] + "+00:00")
        require(parsed.utcoffset().total_seconds() == 0, "CLOCK_INVALID")
        require(type(tick) in (int, float) and math.isfinite(tick), "CLOCK_INVALID")
        return {"utc": stamp, "monotonic": tick}
    except (OSError, *SERIAL_ERRORS):
        raise OperatorError("CLOCK_INVALID") from None


def elapsed(start, end):
    try:
        value = end["monotonic"] - start["monotonic"]
        require(math.isfinite(value) and value >= 0, "CLOCK_INVALID")
        require(
            datetime.fromisoformat(end["utc"].replace("Z", "+00:00"))
            >= datetime.fromisoformat(start["utc"].replace("Z", "+00:00")),
            "CLOCK_INVALID",
        )
        return value
    except SERIAL_ERRORS:
        raise OperatorError("CLOCK_INVALID") from None


def _write(path, raw):
    """Exclusive publication; successful close is part of success. No cleanup/retry."""
    with path.open("xb") as stream:
        if stream.write(raw) != len(raw):
            raise OSError("short write")
        stream.flush()
        os.fsync(stream.fileno())


class Publication:
    def __init__(self, directory):
        self.directory = directory
        self.files = {}
        self.failures = []

    def failure(self, code, stage, filename=None, incomplete=False):
        self.failures.append(
            {
                "code": str(OperatorError(code)),
                "stage": stage,
                "filename": filename,
                "may_be_incomplete": incomplete,
            }
        )

    def raw(self, filename, raw):
        try:
            _write(self.directory / filename, raw)
        except (OSError, KeyboardInterrupt):
            self.failure("PUBLICATION_FAILED", "publication", filename, True)
            return False
        self.files[filename] = {"sha256": digest(raw), "size_bytes": len(raw)}
        return True

    def record(self, filename, value):
        try:
            raw = encode(value)
        except OperatorError:
            self.failure("SERIALIZATION_FAILED", "serialization", filename)
            return False
        if len(raw) > p0.MAX_INPUT_BYTES:
            self.failure("RECORD_TOO_LARGE", "serialization", filename)
            return False
        return self.raw(filename, raw)


class SendGate:
    def __init__(self, request, endpoint):
        self.request = request
        self.url = (
            endpoint
            + "/2015-03-31/functions/"
            + quote(request["FunctionName"], safe="")
            + "/invocations?Qualifier="
            + quote(request["Qualifier"], safe="")
        )
        self.parameters = self.sends = self.blocked = 0
        self.failed = False

    def parameters_hook(self, model, params, **_):
        self.parameters += 1
        if (
            getattr(model, "name", None) != "Invoke"
            or params != self.request
            or self.parameters != 1
        ):
            self.failed = True
            raise OperatorError("PARENT_REQUEST_INVALID")

    def send_hook(self, request, **_):
        headers = getattr(request, "headers", {})
        if (
            self.failed
            or self.parameters != 1
            or self.sends
            or getattr(request, "method", None) != "POST"
            or getattr(request, "url", None) != self.url
            or getattr(request, "body", None) != self.request["Payload"]
            or not callable(getattr(headers, "get", None))
            or headers.get("X-Amz-Invocation-Type")
            not in ("RequestResponse", b"RequestResponse")
            or headers.get("X-Amz-Log-Type") not in ("None", b"None")
        ):
            self.blocked += 1
            self.failed = True
            raise OperatorError("PARENT_SEND_BLOCKED")
        self.sends += 1


def bind(client, target, settings, request):
    """Reviewed simulated client protocol; no inference of delivery from a hook."""
    require(
        getattr(client, "simulation_only", None) is True, "SIMULATED_CLIENT_REQUIRED"
    )
    meta = getattr(client, "meta", None)
    config = getattr(meta, "config", None)
    endpoint = "https://lambda.us-east-1.amazonaws.com"
    retries = getattr(config, "retries", None)
    require(
        getattr(meta, "endpoint_url", None) == endpoint
        and getattr(client, "account", None) == target["account"]
        and getattr(config, "region_name", None) == "us-east-1"
        and getattr(config, "connect_timeout", None) == settings["connect_seconds"]
        and getattr(config, "read_timeout", None) == settings["read_seconds"]
        and type(retries) is dict
        and type(retries.get("total_max_attempts")) is int
        and retries == {"total_max_attempts": 1, "mode": "standard"},
        "CLIENT_CONFIG_INVALID",
    )
    require(
        callable(getattr(client, "invoke", None))
        and callable(getattr(client, "close", None))
        and callable(getattr(getattr(meta, "events", None), "register", None)),
        "CLIENT_CONFIG_INVALID",
    )
    gate = SendGate(request, endpoint)
    meta.events.register("before-parameter-build.*.*", gate.parameters_hook)
    meta.events.register("before-send.*.*", gate.send_hook)
    return gate


def read_response(response):
    """Bound bytes consumed for interpretation, not allocations inside a transport."""
    if type(response) is not dict:
        return b"", False, "PARENT_RESPONSE_INVALID"
    body = response.get("Payload")
    if not callable(getattr(body, "read", None)) or not callable(
        getattr(body, "close", None)
    ):
        return b"", False, "PARENT_RESPONSE_INVALID"
    chunks, length, complete, code = [], 0, False, None
    try:
        while True:
            part = body.read(min(8192, RESPONSE_LIMIT + 1 - length))
            if type(part) is not bytes:
                code = "PARENT_BODY_INVALID"
                break
            if not part:
                complete = True
                break
            if len(part) > RESPONSE_LIMIT - length:
                chunks.append(part[: RESPONSE_LIMIT - length])
                code = "PARENT_BODY_TOO_LARGE"
                break
            chunks.append(part)
            length += len(part)
    except (OSError, ValueError, KeyboardInterrupt):
        code = "PARENT_OUTCOME_UNKNOWN"
    finally:
        try:
            body.close()
        except (OSError, ValueError, KeyboardInterrupt):
            code = code or "PARENT_CLOSE_FAILED"
    return b"".join(chunks), complete, code


def decimal_value(value):
    """Bound exact arithmetic by metadata, never by expanding or rounding text."""
    try:
        require(type(value) is str and len(value) <= 512, "HANDLER_RESULT_INVALID")
        amount = Decimal(value)
        require(amount.is_finite() and amount >= 0, "HANDLER_RESULT_INVALID")
        parts = amount.as_tuple()
        # Preserve the existing 512-character/coefficient budget and long sums.
        # Nonzero operands then have exponent [-512, 511], adjusted <= 511.
        require(
            len(parts.digits) <= 512
            and parts.exponent >= -512
            and amount.adjusted() <= 511,
            "HANDLER_RESULT_INVALID",
        )
        # A zero exponent can widen money_total too; validate it above, then
        # return exact exponent-zero metadata without changing the raw record.
        if amount.is_zero():
            return Decimal(0)
        return amount
    except InvalidOperation:
        raise OperatorError("HANDLER_RESULT_INVALID") from None


def text_size(value):
    try:
        require(type(value) is str, "HANDLER_RESULT_INVALID")
        return len(value.encode("utf-8"))
    except UnicodeError:
        raise OperatorError("HANDLER_RESULT_INVALID") from None


def consumer_accounting(value):
    """Necessary producer invariants, not a fresh cost/authorization calculation.

    SmokePolicy.accounting gives exact bound/coverage precedence. Ceiling also
    depends on its private caps, so only the necessary implications are asserted
    here; a conservative false ceiling is not strengthened into a passing one.
    """
    from decimal import DecimalException

    from app.services.rag_smoke_policy import money_total

    accounting = value["accounting"]
    stages = accounting.get("unestablished_stages")
    vocabulary = {"router", "index", "metadata", "embedding", "generation"}
    require(
        type(stages) is list and all(type(stage) is str for stage in stages),
        "HANDLER_RESULT_INVALID",
    )
    require(
        set(stages) <= vocabulary | {"unidentified_model_request"},
        "HANDLER_RESULT_INVALID",
    )
    require(len(stages) == len(set(stages)), "HANDLER_RESULT_CONTRADICTORY")
    bound = accounting["exposure_bound_established"]
    coverage = accounting["reservation_coverage"]
    require(bound == (not stages), "HANDLER_RESULT_CONTRADICTORY")
    require(
        coverage == "VIOLATED"
        or coverage == ("UNESTABLISHED" if stages else "WITHIN_RECORDED_RESERVATIONS"),
        "HANDLER_RESULT_CONTRADICTORY",
    )
    require(
        not accounting["ceiling_established"] or (bound and coverage != "VIOLATED"),
        "HANDLER_RESULT_CONTRADICTORY",
    )
    require(
        p0.hash_value(accounting.get("extra_requests_sha256")), "HANDLER_RESULT_INVALID"
    )
    if accounting["extra_request_count"] == 0:
        require(
            accounting["extra_requests_sha256"] == digest(encode([])),
            "HANDLER_RESULT_CONTRADICTORY",
        )
    compact = "extra_requests" not in accounting
    if compact:
        require(
            value["status"] == "UNCERTAIN"
            and value["code"] == "RESULT_TOO_LARGE"
            and not value["local_events"],
            "HANDLER_RESULT_CONTRADICTORY",
        )
    else:
        require(type(accounting["extra_requests"]) is list, "HANDLER_RESULT_INVALID")
    held = False
    holds = {"haiku": [Decimal(0)], "titan": [Decimal(0)]}
    for stage, attempt in value["attempts"].items():
        require(
            stage in vocabulary
            and type(attempt) is dict
            and {"reservation_usd", "hold_usd", "settled"} <= set(attempt)
            and type(attempt["settled"]) is bool,
            "HANDLER_RESULT_INVALID",
        )
        reservation = decimal_value(attempt["reservation_usd"])
        hold = decimal_value(attempt["hold_usd"])
        require(
            hold == (Decimal(0) if attempt["settled"] else reservation),
            "HANDLER_RESULT_CONTRADICTORY",
        )
        # Exact handler branch uses the producer's reservation string != "0".
        held |= not attempt["settled"] and attempt["reservation_usd"] != "0"
        if attempt["settled"]:
            usage = attempt.get("usage")
            require(
                stage in {"router", "embedding", "generation"}
                and "charge_usd" in attempt
                and type(usage) is dict
                and set(usage) == {"inputTokens", "outputTokens"}
                and all(
                    type(tokens) is int and tokens >= 0 for tokens in usage.values()
                )
                and (stage != "embedding" or usage["outputTokens"] == 0)
                and attempt.get("usage_attribution") == "AUTHORIZED_REQUEST",
                "HANDLER_RESULT_CONTRADICTORY",
            )
        if ("charge_usd" in attempt and not attempt["settled"]) or attempt.get(
            "usage_attribution"
        ) == "UNATTRIBUTED_RESPONSE":
            require(stage in stages, "HANDLER_RESULT_CONTRADICTORY")
        # Match SmokePolicy.accounting: S3 holds are excluded from model totals.
        if stage not in {"index", "metadata"}:
            holds["titan" if stage == "embedding" else "haiku"].append(hold)
        if (
            "charge_usd" in attempt
            and decimal_value(attempt["charge_usd"]) > reservation
        ):
            require(coverage == "VIOLATED", "HANDLER_RESULT_CONTRADICTORY")
    for provider, amounts in holds.items():
        try:
            total = money_total(amounts)
        except (DecimalException, ValueError, OverflowError):
            raise OperatorError("HANDLER_RESULT_INVALID") from None
        require(
            decimal_value(accounting["retained_holds_usd"][provider]) == total,
            "HANDLER_RESULT_CONTRADICTORY",
        )
    # A recorded token overrun also violates coverage, even if dollars fit.
    for event in value["local_events"]:
        record = event["record"]
        if (
            type(record) is dict
            and record.get("kind") == "usage"
            and record.get("overrun") is True
        ):
            require(coverage == "VIOLATED", "HANDLER_RESULT_CONTRADICTORY")
    uncertain_codes = {
        "UNCERTAIN_PROVIDER_OUTCOME",
        "LOCAL_OR_UNCERTAIN_FAILURE",
        "EVIDENCE_PUBLICATION_FAILED",
    }
    uncertainty = bool(stages) or held or value["code"] in uncertain_codes
    if value["status"] in ("STOPPED", "STRUCTURAL_SUCCESS"):
        require(not uncertainty, "HANDLER_RESULT_CONTRADICTORY")
    # Footer/close and local-import failures have different rules from SmokeStop.
    if value["code"] in {"CLIENT_CLOSE_FAILED", "LOCAL_EVIDENCE_UNAVAILABLE"}:
        require(value["status"] == "UNCERTAIN", "HANDLER_RESULT_CONTRADICTORY")
    elif value["code"] == "LOCAL_EXECUTION_UNAVAILABLE":
        require(
            value["status"] == ("UNCERTAIN" if value["attempts"] else "STOPPED"),
            "HANDLER_RESULT_CONTRADICTORY",
        )
    elif value["code"] == "RESULT_TOO_LARGE":
        require(
            value["status"] == ("UNCERTAIN" if compact or uncertainty else "STOPPED"),
            "HANDLER_RESULT_CONTRADICTORY",
        )
    elif (
        value["code"] in handler.STOP_CODES | {"SMOKE_STOPPED"}
        and value["code"] != "RESULT_TOO_LARGE"
    ):
        require(
            value["status"] == ("UNCERTAIN" if uncertainty else "STOPPED"),
            "HANDLER_RESULT_CONTRADICTORY",
        )


def inspect_handler(raw, policy_hash, run_id):
    """Structural consumer, not a semantic judge or complete acceptance engine."""
    value = parse(raw, RESPONSE_LIMIT, "HANDLER_RESULT_INVALID")
    require(
        type(value) is dict and value.get("schema") == handler.RESULT_SCHEMA,
        "HANDLER_SCHEMA_UNSUPPORTED",
    )
    exact(value, RESULT_KEYS, "HANDLER_RESULT_INVALID")
    require(
        value["scope"] == "STRUCTURAL_SMOKE_NOT_QUALIFICATION"
        and value["status"] in ("STRUCTURAL_SUCCESS", "STOPPED", "UNCERTAIN")
        and (
            value["code"] is None
            if value["status"] == "STRUCTURAL_SUCCESS"
            else type(value["code"]) is str
            and re.fullmatch(r"[A-Z0-9_]{1,80}", value["code"])
        )
        and all(
            value[key] is False
            for key in (
                "parent_claim_verified",
                "publication_confirmed",
                "qualification",
                "release_authorized",
            )
        )
        and value["policy_sha256"] == policy_hash
        and value["run_id"] == run_id,
        "HANDLER_RESULT_INVALID",
    )
    require(
        type(value["attempts"]) is dict
        and type(value["local_events"]) is list
        and len(value["local_events"]) <= 32
        and type(value["exposure_usd"]) is dict,
        "HANDLER_RESULT_INVALID",
    )
    for entry in value["local_events"]:
        require(
            type(entry) is dict
            and set(entry) == {"filename", "sha256", "record"}
            and type(entry["filename"]) is str
            and re.fullmatch(r"[0-9]{2}-[a-z_-]+\.json", entry["filename"])
            and digest(encode(entry["record"])) == entry["sha256"],
            "HANDLER_RESULT_INVALID",
        )
    accounting = value["accounting"]
    require(
        type(accounting) is dict
        and accounting.get("scope") == "LOCAL_MODEL_ACCOUNTING_NOT_TASK_TOTAL",
        "HANDLER_RESULT_INVALID",
    )
    for field in ("known_charges_usd", "retained_holds_usd"):
        exact(accounting.get(field), {"haiku", "titan"}, "HANDLER_RESULT_INVALID")
        for amount in accounting[field].values():
            decimal_value(amount)
    require(
        all(
            type(accounting.get(key)) is bool
            for key in ("exposure_bound_established", "ceiling_established")
        )
        and accounting.get("reservation_coverage")
        in ("VIOLATED", "UNESTABLISHED", "WITHIN_RECORDED_RESERVATIONS")
        and type(accounting.get("extra_request_count")) is int
        and 0 <= accounting["extra_request_count"] <= 1000,
        "HANDLER_RESULT_INVALID",
    )
    consumer_accounting(value)
    extras = accounting.get("extra_requests")
    count = accounting["extra_request_count"]
    mapping = "INCOMPLETE"  # compact output cannot reconstruct omitted observations
    unauthorized = False
    if type(extras) is list:
        require(
            len(extras) == count
            and digest(encode(extras)) == accounting.get("extra_requests_sha256"),
            "HANDLER_RESULT_INVALID",
        )
        mapping = accounting["reservation_coverage"]
        for extra in extras:
            require(
                type(extra) is dict
                and extra.get("delivery") in ("NO", "YES", "UNKNOWN")
                and extra.get("approved") is False
                and {"usage", "charge_usd"} <= set(extra),
                "HANDLER_RESULT_INVALID",
            )
            if extra["delivery"] == "NO":
                require(
                    extra["usage"] is None and extra["charge_usd"] is None,
                    "HANDLER_RESULT_CONTRADICTORY",
                )
            if extra.get("charge_usd") is not None:
                actual = decimal_value(extra["charge_usd"])
                if actual > 0:
                    require(
                        accounting["reservation_coverage"] == "VIOLATED",
                        "HANDLER_RESULT_CONTRADICTORY",
                    )
            if extra["delivery"] != "NO":
                require(
                    extra.get("stage") in {"router", "embedding", "generation"},
                    "HANDLER_RESULT_INVALID",
                )
                if extra["delivery"] == "UNKNOWN" or extra["charge_usd"] is None:
                    require(
                        extra["stage"] in accounting["unestablished_stages"],
                        "HANDLER_RESULT_CONTRADICTORY",
                    )
                unauthorized = True
                mapping = "VIOLATED_RECORD_UNRESERVED_EXPOSURE"
    require(
        type(value["result"]) is dict
        if value["status"] == "STRUCTURAL_SUCCESS"
        else value["result"] is None,
        "HANDLER_RESULT_INVALID",
    )
    if value["status"] == "STRUCTURAL_SUCCESS":
        result = value["result"]
        exact(
            result,
            {"answer", "citations", "retrieval", "router_confidence"},
            "HANDLER_RESULT_INVALID",
        )
        require(
            0 < text_size(result["answer"]) <= handler.MAX_ANSWER_BYTES
            and type(result["citations"]) is list
            and len(result["citations"]) <= 100
            and all(type(source) is str for source in result["citations"])
            and result["citations"] == sorted(set(result["citations"]))
            and type(result["retrieval"]) is list
            and 0 < len(result["retrieval"]) <= 100,
            "HANDLER_RESULT_INVALID",
        )
        try:
            require(
                type(result["router_confidence"]) in (int, float)
                and math.isfinite(result["router_confidence"])
                and 0 <= result["router_confidence"] <= 1,
                "HANDLER_RESULT_INVALID",
            )
            for row in result["retrieval"]:
                exact(row, {"source", "score"}, "HANDLER_RESULT_INVALID")
                require(
                    type(row["source"]) is str
                    and bool(row["source"])
                    and type(row["score"]) in (int, float)
                    and math.isfinite(row["score"]),
                    "HANDLER_RESULT_INVALID",
                )
        except OverflowError:
            raise OperatorError("HANDLER_RESULT_INVALID") from None
        require(
            value["code"] is None
            and set(value["attempts"])
            == {"router", "index", "metadata", "embedding", "generation"}
            and accounting["exposure_bound_established"]
            and accounting["ceiling_established"]
            and mapping == "WITHIN_RECORDED_RESERVATIONS"
            and count == 0,
            "HANDLER_RESULT_CONTRADICTORY",
        )
    return {
        "status": value["status"],
        "model_accounting": accounting,
        "contract_exposure": mapping,
        "unapproved_delivered_or_uncertain": unauthorized,
    }


def inspect_logs(raw, expected_hash, request_id):
    """Supplied selected-field REPORT projection only, never fetches logs."""
    require(
        p0.hash_value(expected_hash)
        and type(raw) is bytes
        and digest(raw) == expected_hash,
        "LOG_BINDING_MISMATCH",
    )
    value = parse(raw, MAX_LOG_BYTES, "LOG_INVALID")
    exact(value, {"schema", "request_id", "report"}, "LOG_INVALID")
    require(
        value["schema"] == "jev-rag-smoke-supplied-logs-v1"
        and value["request_id"] == request_id,
        "LOG_REQUEST_MISMATCH",
    )
    report = value["report"]
    require(
        type(report) is dict
        and set(report)
        >= {
            "request_id",
            "duration_ms",
            "billed_duration_ms",
            "memory_size_mib",
            "max_memory_used_mib",
        }
        and set(report)
        <= {
            "request_id",
            "duration_ms",
            "billed_duration_ms",
            "memory_size_mib",
            "max_memory_used_mib",
            "init_duration_ms",
        },
        "REPORT_INVALID",
    )
    require(report["request_id"] == request_id, "LOG_REQUEST_MISMATCH")
    for name, number in report.items():
        if name != "request_id":
            try:
                require(
                    type(number) in (int, float)
                    and math.isfinite(number)
                    and number >= 0,
                    "REPORT_INVALID",
                )
            except OverflowError:
                raise OperatorError("REPORT_INVALID") from None
    return {
        "report": report,
        "provenance": "SUPPLIED_PROJECTION_UNAUTHENTICATED",
        "warm_reuse": "UNESTABLISHED",
        "cpu_dispatch": "UNESTABLISHED",
        "absence_of_errors": "UNESTABLISHED",
    }


def simulate(
    plan_raw,
    p0_raw,
    invocation_raw,
    policy_raw,
    *,
    evidence,
    hashes,
    root,
    client_factory,
    supplied_logs=None,
    logs_sha256=None,
    utc=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    monotonic=time.monotonic,
):
    """Claim once, simulate one Invoke, publish evidence. No operational authorization."""
    plan, original, preflight, parent = validate(
        plan_raw,
        p0_raw,
        invocation_raw,
        policy_raw,
        evidence=evidence,
        hashes=hashes,
        root=root,
    )
    require(callable(client_factory), "SIMULATED_CLIENT_REQUIRED")
    # Malformed/hash-mismatched supplied evidence rejects before any claim.
    if supplied_logs is not None:
        require(
            type(supplied_logs) is bytes
            and len(supplied_logs) <= MAX_LOG_BYTES
            and p0.hash_value(logs_sha256)
            and digest(supplied_logs) == logs_sha256,
            "LOG_BINDING_MISMATCH",
        )
    else:
        require(logs_sha256 is None, "LOG_BINDING_MISMATCH")
    try:
        claimed = p0.publish_claim(
            p0_raw,
            policy_raw,
            evidence=evidence,
            expected_hashes={
                key: hashes[key] for key in ("plan", "policy", "haiku", "titan")
            },
            root=parent,
        )
    except p0.PreinvokeError as error:
        raise OperatorError(str(error)) from None
    publication = Publication(parent / claimed["execution_id"])
    try:
        claim_size = (publication.directory / "claim.json").stat().st_size
    except OSError:
        raise OperatorError("CLAIM_READ_FAILED_RETAINED") from None
    publication.files["claim.json"] = {
        "sha256": claimed["claim_sha256"],
        "size_bytes": claim_size,
    }
    assessment = {
        "parent_transport": "NOT_DISPATCHED",
        "handler_structure": "UNESTABLISHED",
        "model_accounting": None,
        "contract_exposure": "UNESTABLISHED",
        "evidence_complete": False,
        "semantic_assessment": "UNASSESSED",
        "task_cost_established": False,
        "experiment_success": False,
    }
    request = {
        "FunctionName": plan["target"]["function_name"],
        "Qualifier": plan["target"]["qualifier"],
        "InvocationType": "RequestResponse",
        "LogType": "None",
        "Payload": invocation_raw,
    }
    request_record = {
        "schema": "jev-rag-smoke-parent-request-v1",
        "operation": "Invoke",
        "target": plan["target"],
        "invocation_type": "RequestResponse",
        "log_type": "None",
        "payload_sha256": hashes["invocation"],
        "payload_size_bytes": len(invocation_raw),
        "mode": "SIMULATED_OFFLINE",
        "hashes": hashes,
        "p0_preflight": preflight,
    }
    dispatches, client, gate = 0, None, None
    timings = {
        "request_start": None,
        "response_received": None,
        "elapsed_seconds": None,
    }
    try:
        for filename, raw in (
            ("operator-plan.json", plan_raw),
            ("p0-plan.json", p0_raw),
            ("invocation.json", invocation_raw),
            ("policy.json", policy_raw),
            ("haiku-evidence.json", evidence["haiku"]),
            ("titan-evidence.json", evidence["titan"]),
        ):
            require(publication.raw(filename, raw), "PUBLICATION_FAILED")
        require(
            publication.record("request.json", request_record), "PUBLICATION_FAILED"
        )
        start = clock_sample(utc, monotonic)
        timings["request_start"] = start["utc"]
        marker = {
            "schema": "jev-rag-smoke-parent-attempt-v1",
            "state": "FULL_P0_RESERVATIONS_RETAINED_OUTCOME_UNKNOWN",
            "request_sha256": publication.files["request.json"]["sha256"],
            "started_utc": start["utc"],
            "mode": "SIMULATED_OFFLINE",
            "maximum_dispatches": 1,
        }
        require(
            publication.record("invocation-attempt.json", marker), "PUBLICATION_FAILED"
        )
        client = client_factory()
        gate = bind(client, plan["target"], original["parent_invocation"], request)
        dispatches = 1
        assessment["parent_transport"] = "UNKNOWN"
        response = client.invoke(**request)
        # Consume/preserve before clocks, metadata serialization or interpretation.
        raw, complete, read_code = read_response(response)
        published_response = publication.raw("response.bin", raw)
        if read_code:
            publication.failure(read_code, "response")
        if not published_response:
            raise OperatorError("PUBLICATION_FAILED")
        if type(response) is not dict:
            raise OperatorError("PARENT_RESPONSE_INVALID")
        metadata = response.get("ResponseMetadata")
        receipt = {
            "status_code": response.get("StatusCode"),
            "executed_version": response.get("ExecutedVersion"),
            "function_error": response.get("FunctionError"),
            "request_id": metadata.get("RequestId") if type(metadata) is dict else None,
            "retry_attempts": metadata.get("RetryAttempts")
            if type(metadata) is dict
            else None,
            "body_complete": complete,
            "body_sha256": digest(raw),
        }
        require(
            publication.record("response-metadata.json", receipt), "PUBLICATION_FAILED"
        )
        end = clock_sample(utc, monotonic)
        timings["response_received"] = end["utc"]
        timings["elapsed_seconds"] = elapsed(start, end)
        require(not read_code and complete, read_code or "PARENT_OUTCOME_UNKNOWN")
        require(
            gate.parameters == gate.sends == 1 and not gate.failed,
            "PARENT_HOOKS_INVALID",
        )
        require(
            type(receipt["retry_attempts"]) is int and receipt["retry_attempts"] == 0,
            "PARENT_RETRY_INVALID",
        )
        require(
            type(receipt["request_id"]) is str and ID.fullmatch(receipt["request_id"]),
            "PARENT_REQUEST_ID_INVALID",
        )
        require(
            type(receipt["status_code"]) is int and receipt["status_code"] == 200,
            "PARENT_STATUS_INVALID",
        )
        require(
            type(receipt["executed_version"]) is str
            and (
                receipt["executed_version"] == "$LATEST"
                or re.fullmatch(r"[1-9][0-9]{0,19}", receipt["executed_version"])
            ),
            "PARENT_VERSION_INVALID",
        )
        require(
            plan["target"]["qualifier"] == "$LATEST"
            or receipt["executed_version"] == plan["target"]["qualifier"],
            "PARENT_VERSION_MISMATCH",
        )
        require(
            receipt["function_error"] in (None, "Handled", "Unhandled"),
            "PARENT_RESPONSE_INVALID",
        )
        assessment["parent_transport"] = "RETURNED"
        if receipt["function_error"]:
            assessment["handler_structure"] = "FUNCTION_ERROR"
        else:
            result = inspect_handler(raw, hashes["policy"], original["run_id"])
            assessment["handler_structure"] = result["status"]
            assessment["model_accounting"] = result["model_accounting"]
            assessment["contract_exposure"] = result["contract_exposure"]
        if supplied_logs is not None:
            require(
                publication.raw("supplied-logs.json", supplied_logs),
                "PUBLICATION_FAILED",
            )
            assessment["log_evidence"] = inspect_logs(
                supplied_logs, logs_sha256, receipt["request_id"]
            )
            assessment["evidence_complete"] = assessment["handler_structure"] in (
                "STRUCTURAL_SUCCESS",
                "STOPPED",
                "UNCERTAIN",
                "FUNCTION_ERROR",
            )
        # No semantic judgment, parent completion authentication, qualification or release.
    except OperatorError as error:
        if not publication.failures or publication.failures[-1]["code"] != str(error):
            publication.failure(str(error), "operation")
    except (OSError, KeyboardInterrupt):
        publication.failure(
            "PARENT_OUTCOME_UNKNOWN" if dispatches else "LOCAL_OPERATION_FAILED",
            "operation",
        )
    finally:
        if client is not None and callable(getattr(client, "close", None)):
            try:
                client.close()
            except (OSError, ValueError, KeyboardInterrupt):
                publication.failure("CLIENT_CLOSE_FAILED", "close")
    if publication.failures:
        assessment["evidence_complete"] = False
    index = {
        "schema": INDEX_SCHEMA,
        "mode": "SIMULATED_OFFLINE",
        "status": "INTERRUPTED" if publication.failures else "COMPLETE",
        "files": publication.files,
        "failures": list(publication.failures),
        "assessment": assessment,
        "initial_reservations_usd": preflight["initial_reservations_usd"],
        "reservation_release": "NONE_PARENT_HOLDS_RETAINED",
        "external_gates": preflight["external_gates"],
        "timings": timings,
        "dispatches": dispatches,
        "send_checks": {
            "parameters": gate.parameters,
            "approved_callbacks": gate.sends,
            "blocked_callbacks": gate.blocked,
        }
        if gate
        else None,
        "owner_authorized": False,
        "invoke_authorized": False,
        "release_authorized": False,
    }
    primary = publication.failures[0]["code"] if publication.failures else None
    confirmed = publication.record("index.json", index)
    return {
        "schema": INDEX_SCHEMA,
        "mode": "SIMULATED_OFFLINE",
        "status": index["status"] if confirmed else "INTERRUPTED_UNINDEXED",
        "code": primary
        or (publication.failures[0]["code"] if publication.failures else None),
        "index_failure_code": None if confirmed else publication.failures[-1]["code"],
        "failure_count": len(publication.failures),
        "failures": list(publication.failures),
        "index_sha256": publication.files["index.json"]["sha256"]
        if confirmed
        else None,
        "execution_id": preflight["execution_id"],
        "dispatches": dispatches,
        "release_authorized": False,
    }


def _publish_adapter(pub, transport):
    """Private bounded projection, published before any handler interpretation."""
    result = transport.result
    summary = result.summary()
    summary["hook_failed"] = transport.failed
    published = [
        pub.raw("response.bin", result.body),
        pub.record("response-metadata.json", result.metadata),
        pub.record("transport-result.json", summary),
    ]
    if transport.request["LogType"] == "Tail":
        published.extend(
            [
                pub.raw("log-encoded.bin", result.log_encoded),
                pub.raw("log-decoded.bin", result.log_decoded),
                pub.record("log-evidence.json", result.log_summary()),
            ]
        )
    for code in result.failures:
        pub.failure(code, "adapter")
    clean = (
        result.code == "RETURNED"
        and not result.failures
        and not transport.failed
        and result.dispatch_entries == 1
        and result.parameter_checks == 1
        and result.approved_send_callbacks == 1
        and result.blocked_send_callbacks == 0
        and result.body_eof
        and result.body_closed
        and result.client_closed
    )
    if not clean and not result.failures:
        pub.failure("PARENT_HOOKS_INVALID", "adapter-state")
    return all(published) and clean


def consume_adapter(
    plan_raw,
    p0_raw,
    invocation_raw,
    policy_raw,
    *,
    evidence,
    hashes,
    root,
    client_factory,
    utc=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    monotonic=time.monotonic,
):
    """Explicit injected adapter seam. No live CLI, factory or credential defaults.

    Programming defects propagate. Available local evidence is best-effort in
    that case, never a returned completion confirmation. Parent holds never
    settle here, even when an inner handler result is structurally acceptable.
    """
    from scripts import jev_rag_smoke_live_adapter as adapter

    plan, original, preflight, parent = validate_adapter(
        plan_raw,
        p0_raw,
        invocation_raw,
        policy_raw,
        evidence=evidence,
        hashes=hashes,
        root=root,
    )
    tail_mode = plan["schema"] == TAIL_PLAN_SCHEMA
    mode = TAIL_MODE if tail_mode else ADAPTER_MODE
    index_schema = TAIL_INDEX_SCHEMA if tail_mode else ADAPTER_INDEX_SCHEMA
    require(callable(client_factory), "CLIENT_FACTORY_REQUIRED")
    try:
        claim = p0.publish_claim(
            p0_raw,
            policy_raw,
            evidence=evidence,
            expected_hashes={
                key: hashes[key] for key in ("plan", "policy", "haiku", "titan")
            },
            root=parent,
        )
    except p0.PreinvokeError as error:
        raise OperatorError(str(error)) from None
    directory = parent / preflight["execution_id"]
    pub = Publication(directory)
    try:
        claim_size = (directory / "claim.json").stat().st_size
    except OSError:
        raise OperatorError("CLAIM_READ_FAILED_RETAINED") from None
    pub.files["claim.json"] = {
        "sha256": claim["claim_sha256"],
        "size_bytes": claim_size,
    }
    request = {
        "FunctionName": (
            f"arn:aws:lambda:{plan['target']['region']}:{plan['target']['account']}:"
            f"function:{plan['target']['function_name']}"
        ),
        "Qualifier": plan["target"]["qualifier"],
        "InvocationType": "RequestResponse",
        "LogType": "Tail" if tail_mode else "None",
        "Payload": invocation_raw,
    }
    request_record = {
        "schema": "jev-rag-smoke-parent-request-v1",
        "mode": mode,
        "request": {k: v for k, v in request.items() if k != "Payload"},
        "payload_sha256": hashes["invocation"],
        "payload_size_bytes": len(invocation_raw),
        "input_hashes": hashes,
        "preflight": preflight,
        "owner_authorized": False,
        "invocation_authorized": False,
    }
    if tail_mode:
        request_record["schema"] = "jev-rag-smoke-parent-request-v2"
        request_record["parser_contract"] = plan["parser_contract"]
    assessment = {
        "parent_transport": "NOT_DISPATCHED",
        "handler_structure": "UNESTABLISHED",
        "model_accounting": None,
        "contract_exposure": "UNESTABLISHED",
        "evidence_complete": False,
        "experiment_success": False,
        "semantic_assessment": "UNASSESSED",
        "task_cost_established": False,
        "report_evidence": "INCOMPLETE_NOT_CAPTURED",
        "sdk_request_id_is_execution_id": False,
        "authenticated_observation": False,
    }
    timings = {
        "started_utc": None,
        "received_utc": None,
        "client_elapsed_seconds": None,
    }
    client = transport = None
    index_hash = index_failure = None
    status = "INTERRUPTED_UNINDEXED"
    completed = False  # This invocation, never the caller's ambient except state.
    try:
        for name, raw in (
            ("operator-plan.json", plan_raw),
            ("p0-plan.json", p0_raw),
            ("invocation.json", invocation_raw),
            ("policy.json", policy_raw),
            ("haiku-price.json", evidence["haiku"]),
            ("titan-price.json", evidence["titan"]),
        ):
            require(pub.raw(name, raw), "PUBLICATION_FAILED")
        require(pub.record("request.json", request_record), "PUBLICATION_FAILED")
        start = clock_sample(utc, monotonic)
        timings["started_utc"] = start["utc"]
        marker = {
            "schema": "jev-rag-smoke-parent-attempt-v2"
            if tail_mode
            else "jev-rag-smoke-parent-attempt-v1",
            "mode": mode,
            "state": "FULL_P0_RESERVATIONS_RETAINED_OUTCOME_UNKNOWN",
            "request_sha256": digest(encode(request_record)),
            "started_utc": start["utc"],
            "max_dispatches": 1,
        }
        require(pub.record("invocation-attempt.json", marker), "PUBLICATION_FAILED")
        # Both durable files are closed before either injected factory or adapter.
        client = client_factory()
        options = (
            {"log_type": "Tail", "parser_contract": plan["parser_contract"]}
            if tail_mode
            else {}
        )
        transport = adapter.ParentTransport(
            client,
            plan["target"],
            original["parent_invocation"],
            invocation_raw,
            **options,
        )
        require(transport.request == request, "PARENT_REQUEST_INVALID")
        assessment["parent_transport"] = "UNKNOWN"
        normal_return = False
        try:
            transport.invoke_once()
            normal_return = True
        finally:
            # Only this evidence boundary suppresses secondary defects while a
            # primary invoke/read defect is already propagating. No conversion.
            try:
                clean = _publish_adapter(pub, transport)
            except BaseException:
                if normal_return:
                    raise
                pub.failure("OPERATOR_DEFECT_PROPAGATED", "secondary-evidence")
        if tail_mode and transport.result.log_state == "DECODED":
            # Raw bytes and labels must be successfully published before parsing.
            if all(
                name in pub.files
                for name in (
                    "log-encoded.bin",
                    "log-decoded.bin",
                    "log-evidence.json",
                    "response-metadata.json",
                    "response.bin",
                    "transport-result.json",
                )
            ):
                try:
                    joined = adapter.parse_report(
                        transport.result.log_decoded,
                        transport.result.metadata.get("ExecutedVersion"),
                        plan["target"]["qualifier"],
                    )
                    joined.update(
                        request_sha256=digest(encode(request_record)),
                        response_sha256=digest(transport.result.body),
                        response_metadata_sha256=digest(
                            encode(transport.result.metadata)
                        ),
                        log_encoded_sha256=digest(transport.result.log_encoded),
                        log_decoded_sha256=digest(transport.result.log_decoded),
                        sdk_request_id=(
                            transport.result.metadata["ResponseMetadata"].get(
                                "RequestId"
                            )
                            if type(transport.result.metadata.get("ResponseMetadata"))
                            is dict
                            else None
                        ),
                        parent_transport_complete=clean,
                    )
                    if pub.record("report-association.json", joined):
                        assessment["report_evidence"] = joined["status"]
                    else:
                        clean = False
                except adapter.AdapterError as error:
                    pub.failure(str(error), "report-parser")
                    clean = False
            else:
                clean = False
        end = clock_sample(utc, monotonic)
        timings["received_utc"] = end["utc"]
        timings["client_elapsed_seconds"] = elapsed(start, end)
        require(clean, "PARENT_RESPONSE_INVALID")
        assessment["parent_transport"] = "RETURNED"
        if transport.result.metadata.get("FunctionError") is not None:
            assessment["handler_structure"] = "FUNCTION_ERROR"
        else:
            inspected = inspect_handler(
                transport.result.body, hashes["policy"], original["run_id"]
            )
            assessment["handler_structure"] = inspected["status"]
            assessment["model_accounting"] = inspected["model_accounting"]
            assessment["contract_exposure"] = inspected["contract_exposure"]
        completed = True
    except (OperatorError, adapter.AdapterError) as error:
        code = str(error)
        if not pub.failures or pub.failures[-1]["code"] != code:
            pub.failure(code, "adapter-consumer")
        completed = True
    except (OSError, KeyboardInterrupt):
        pub.failure(
            "PARENT_OUTCOME_UNKNOWN"
            if transport is not None
            else "LOCAL_OPERATION_FAILED",
            "adapter-consumer",
        )
        completed = True
    finally:
        propagating = not completed
        if propagating:
            pub.failure("OPERATOR_DEFECT_PROPAGATED", "adapter-consumer")
        # A constructed adapter owns closure; if construction rejected, the
        # consumer closes the supplied client without masking a primary defect.
        if (
            client is not None
            and transport is None
            and callable(getattr(client, "close", None))
        ):
            try:
                client.close()
            except (OSError, ValueError, KeyboardInterrupt):
                pub.failure("CLIENT_CLOSE_FAILED", "client-close")
            except BaseException:
                pub.failure("CLIENT_CLOSE_FAILED", "client-close")
                if not propagating:
                    raise
        result = transport.result if transport is not None else None
        status = "INTERRUPTED" if pub.failures else "COMPLETE"
        index = {
            "schema": index_schema,
            "mode": mode,
            "status": status,
            "execution_id": preflight["execution_id"],
            "files": pub.files.copy(),
            "failures": pub.failures.copy(),
            "assessment": assessment,
            "initial_reservations_usd": preflight["initial_reservations_usd"],
            "reservation_release": "NONE_PARENT_HOLDS_RETAINED",
            "external_gates": preflight["external_gates"],
            "timings": timings,
            "dispatches": result.dispatch_entries if result is not None else 0,
            "owner_authorized": False,
            "invocation_authorized": False,
            "release_authorized": False,
        }
        try:
            if pub.record("index.json", index):
                index_hash = pub.files["index.json"]["sha256"]
            else:
                status = "INTERRUPTED_UNINDEXED"
                index_failure = pub.failures[-1]["code"]
        except BaseException:
            if not propagating:
                raise
            # No returned confirmation is possible on a propagating defect.
    return {
        "schema": index_schema,
        "mode": mode,
        "status": status,
        "code": pub.failures[0]["code"] if pub.failures else None,
        "index_failure_code": index_failure,
        "failure_count": len(pub.failures),
        "failures": pub.failures.copy(),
        "index_sha256": index_hash,
        "execution_id": preflight["execution_id"],
        "dispatches": transport.result.dispatch_entries if transport is not None else 0,
        "release_authorized": False,
    }


def confirm(result, directory):
    """Only a successfully returned COMPLETE plus exact index/file hashes confirms publication."""
    require(
        type(result) is dict
        and result.get("status") == "COMPLETE"
        and p0.hash_value(result.get("index_sha256")),
        "PUBLICATION_UNCONFIRMED",
    )
    parent = p0.persistent_root(directory)
    try:
        raw = (parent / "index.json").read_bytes()
        require(digest(raw) == result["index_sha256"], "PUBLICATION_UNCONFIRMED")
        index = parse(raw, p0.MAX_INPUT_BYTES, "PUBLICATION_UNCONFIRMED")
        require(index["status"] == "COMPLETE", "PUBLICATION_UNCONFIRMED")
        for name, binding in index["files"].items():
            require(
                type(name) is str
                and re.fullmatch(r"[a-z0-9-]+\.(json|bin)", name)
                and not (parent / name).is_symlink(),
                "PUBLICATION_UNCONFIRMED",
            )
            received = (parent / name).read_bytes()
            require(
                digest(received) == binding["sha256"]
                and len(received) == binding["size_bytes"],
                "PUBLICATION_UNCONFIRMED",
            )
    except (OSError, KeyError, TypeError):
        raise OperatorError("PUBLICATION_UNCONFIRMED") from None
    return index


def emit_confirmation(result, stdout=None, stderr=None):
    """No live entry point. Console failure is exit 3, never confirmation from index bytes."""
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        # Do not expose private results, request bodies, paths or provider messages.
        selected = {
            key: result[key]
            for key in (
                "schema",
                "mode",
                "status",
                "code",
                "index_failure_code",
                "failure_count",
                "failures",
                "index_sha256",
                "execution_id",
                "dispatches",
                "release_authorized",
            )
        }
        text = encode(selected).decode("ascii")
        require(stdout.write(text) == len(text), "CONSOLE_CONFIRMATION_UNAVAILABLE")
        stdout.flush()
    except (OperatorError, OSError, *SERIAL_ERRORS):
        try:
            stderr.write("CONSOLE_CONFIRMATION_UNAVAILABLE\n")
            stderr.flush()
        except (OSError, *SERIAL_ERRORS):
            pass
        return 3
    return 0 if result["status"] == "COMPLETE" else 2
