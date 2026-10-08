"""Offline injected parent seam. No SDK, credentials, live CLI or approval grant.

Only invented simulated transports belong here. Hooks are reviewed checks, not
a sandbox or authenticated observer. An operational adapter remains unbuilt.
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
    "CLAIM_PUBLICATION_FAILED_RETAINED CLAIM_INTERRUPTED_RETAINED CLAIM_READ_FAILED_RETAINED".split()
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


def validate(plan_raw, p0_raw, invocation_raw, policy_raw, *, evidence, hashes, root):
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
        {"schema", "mode", "p0_plan_sha256", "invocation_sha256", "target"},
        "PLAN_INVALID",
    )
    require(
        plan["schema"] == PLAN_SCHEMA and plan["mode"] == "SIMULATED_OFFLINE",
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
    try:
        require(type(value) is str and len(value) <= 512, "HANDLER_RESULT_INVALID")
        amount = Decimal(value)
        require(amount.is_finite() and amount >= 0, "HANDLER_RESULT_INVALID")
        return amount
    except InvalidOperation:
        raise OperatorError("HANDLER_RESULT_INVALID") from None


def text_size(value):
    try:
        require(type(value) is str, "HANDLER_RESULT_INVALID")
        return len(value.encode("utf-8"))
    except UnicodeError:
        raise OperatorError("HANDLER_RESULT_INVALID") from None


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
                and extra.get("approved") is False,
                "HANDLER_RESULT_INVALID",
            )
            if extra.get("charge_usd") is not None:
                decimal_value(extra["charge_usd"])
            if extra["delivery"] != "NO":
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
