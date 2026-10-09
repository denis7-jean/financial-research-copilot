"""Injected Lambda parent transport; no client factory, CLI, credentials or approval.

Import is standard-library-only. A future reviewed operator must claim and retain
reservations before construction/dispatch. This cannot enter simulate().
"""

from dataclasses import dataclass, field
import hashlib
import json
import re
from threading import Lock
from urllib.parse import quote

ENDPOINT = "https://lambda.us-east-1.amazonaws.com"
REGION = "us-east-1"
SDK_PIN = "1.42.96"
RESPONSE_LIMIT = 131_072  # Accepted handler/operator MAX_RESULT_BYTES.
EVENT_LIMIT = 131_072
ID = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")
CODES = frozenset(
    "INPUT_INVALID CLIENT_CONFIG_INVALID PARENT_ALREADY_ATTEMPTED "
    "PARENT_REQUEST_INVALID PARENT_SEND_BLOCKED PARENT_SERVICE_ERROR "
    "PARENT_OUTCOME_UNKNOWN PARENT_RESPONSE_INVALID PARENT_BODY_INVALID "
    "PARENT_BODY_TOO_LARGE PARENT_CLOSE_FAILED CLIENT_CLOSE_FAILED "
    "PARENT_HOOKS_INVALID PARENT_RETRY_INVALID PARENT_VERSION_MISMATCH "
    "PARENT_DEFECT_PROPAGATED".split()
)


class AdapterError(ValueError):
    def __init__(self, code):
        super().__init__(code if code in CODES else "INPUT_INVALID")


def require(condition, code):
    if not condition:
        raise AdapterError(code) from None


def sdk_errors():
    """Load exception definitions only, on explicit construction; no SDK client."""
    from botocore import exceptions as e

    return (
        (e.ClientError,),
        (
            e.ConnectTimeoutError,
            e.ReadTimeoutError,
            e.EndpointConnectionError,
            e.ConnectionClosedError,
            e.ProxyConnectionError,
            e.SSLError,
            e.HTTPClientError,
            e.ResponseStreamingError,
            e.IncompleteReadError,
            e.ParamValidationError,
            e.NoCredentialsError,
            e.PartialCredentialsError,
            e.CredentialRetrievalError,
        ),
    )


def canonical_payload(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def constant(_):
        raise ValueError

    require(type(raw) is bytes and 0 < len(raw) <= EVENT_LIMIT, "INPUT_INVALID")
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
        )
        require(type(value) is dict, "INPUT_INVALID")
        encoded = (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode()
        require(encoded == raw, "INPUT_INVALID")
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise AdapterError("INPUT_INVALID") from None


@dataclass(repr=False)
class Attempt:
    """Private bytes are never included in repr or sanitized summary."""

    code: str = "NOT_RETURNED"
    failures: list[str] = field(default_factory=list)
    dispatch_entries: int = 0
    parameter_checks: int = 0
    approved_send_callbacks: int = 0
    blocked_send_callbacks: int = 0
    body: bytes = b""
    body_eof: bool = False
    body_closed: bool = False
    client_closed: bool = False
    metadata: dict = field(default_factory=dict)
    metadata_state: str = "NOT_RECEIVED"

    def fail(self, code):
        self.failures.append(code)
        if self.code in ("NOT_RETURNED", "RETURNED"):
            self.code = code

    def summary(self):
        return {
            "schema": "jev-rag-smoke-parent-transport-result-v1",
            "code": self.code,
            "failures": list(self.failures),
            "dispatch_entries": self.dispatch_entries,
            "parameter_checks": self.parameter_checks,
            "approved_send_callbacks": self.approved_send_callbacks,
            "blocked_send_callbacks": self.blocked_send_callbacks,
            "delivery": "UNESTABLISHED",
            "body_bytes": len(self.body),
            "body_sha256": hashlib.sha256(self.body).hexdigest(),
            "body_eof": self.body_eof,
            "body_closed": self.body_closed,
            "client_closed": self.client_closed,
            "metadata_sha256": hashlib.sha256(
                json.dumps(
                    self.metadata,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                ).encode()
                + b"\n"
            ).hexdigest(),
            "metadata_provenance": "SELECTED_FIELDS_OF_INJECTED_SDK_RESPONSE",
            "metadata_state": self.metadata_state,
            "sdk_request_id_is_execution_id": False,
            "report_evidence": "INCOMPLETE_NOT_CAPTURED",
            "authenticated_observation": False,
            "reservation_release": "NONE",
        }

    def __repr__(self):
        return f"Attempt(code={self.code!r}, body_bytes={len(self.body)})"


class ParentTransport:
    """One-use injected client. Never labelled simulation_only, never builds clients.

    target/settings use the accepted operator/P0 field sets. The qualified full
    ARN additionally binds the account; the simulation operator uses a bare name.
    No claim, price, semantic validation, durable publication or REPORT capture.
    """

    def __init__(self, client, target, settings, payload, *, errors=None):
        require(
            type(target) is dict
            and set(target) == {"account", "region", "function_name", "qualifier"},
            "INPUT_INVALID",
        )
        require(
            type(target["account"]) is str
            and re.fullmatch(r"[0-9]{12}", target["account"])
            and target["region"] == REGION
            and type(target["function_name"]) is str
            and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", target["function_name"])
            and type(target["qualifier"]) is str
            and (
                target["qualifier"] == "$LATEST"
                or re.fullmatch(r"[1-9][0-9]{0,19}", target["qualifier"])
            ),
            "INPUT_INVALID",
        )
        require(
            type(settings) is dict
            and set(settings) == {"max_attempts", "connect_seconds", "read_seconds"}
            and type(settings["max_attempts"]) is int
            and settings["max_attempts"] == 1
            and all(
                type(settings[k]) is int and 1 <= settings[k] <= 120
                for k in ("connect_seconds", "read_seconds")
            ),
            "INPUT_INVALID",
        )
        canonical_payload(payload)
        meta = getattr(client, "meta", None)
        config = getattr(meta, "config", None)
        retries = getattr(config, "retries", None)
        require(
            getattr(meta, "endpoint_url", None) == ENDPOINT
            and getattr(config, "region_name", None) == REGION
            and getattr(config, "connect_timeout", None) == settings["connect_seconds"]
            and getattr(config, "read_timeout", None) == settings["read_seconds"]
            and type(retries) is dict
            and type(retries.get("total_max_attempts")) is int
            and retries == {"total_max_attempts": 1, "mode": "standard"}
            and callable(getattr(client, "invoke", None))
            and callable(getattr(client, "close", None))
            and callable(getattr(getattr(meta, "events", None), "register", None)),
            "CLIENT_CONFIG_INVALID",
        )
        self.client = client
        self.service_errors, self.transport_errors = (
            errors if errors is not None else sdk_errors()
        )
        self._request = {
            "FunctionName": f"arn:aws:lambda:{REGION}:{target['account']}:function:{target['function_name']}",
            "Qualifier": target["qualifier"],
            "InvocationType": "RequestResponse",
            "LogType": "None",
            "Payload": payload,
        }
        self.url = (
            ENDPOINT
            + "/2015-03-31/functions/"
            + quote(self.request["FunctionName"], safe="")
            + "/invocations?Qualifier="
            + quote(target["qualifier"], safe="")
        )
        self.result = Attempt()
        self.lock = Lock()
        self.used = False
        self.failed = False
        meta.events.register("before-parameter-build.*.*", self.parameters_hook)
        meta.events.register("before-send.*.*", self.send_hook)

    @property
    def request(self):
        """Expose a copy; caller mutation cannot change the pinned dispatch."""
        return dict(self._request)

    def parameters_hook(self, model, params, **_):
        with self.lock:
            self.result.parameter_checks += 1
            if (
                self.failed
                or self.result.dispatch_entries != 1
                or self.result.parameter_checks != 1
                or getattr(model, "name", None) != "Invoke"
                or params != self.request
            ):
                self.failed = True
                raise AdapterError("PARENT_REQUEST_INVALID")

    def send_hook(self, request, **_):
        with self.lock:
            headers = getattr(request, "headers", {})
            if (
                self.failed
                or self.result.dispatch_entries != 1
                or self.result.parameter_checks != 1
                or self.result.approved_send_callbacks
                or getattr(request, "method", None) != "POST"
                or getattr(request, "url", None) != self.url
                or getattr(request, "body", None) != self.request["Payload"]
                or not callable(getattr(headers, "get", None))
                or headers.get("X-Amz-Invocation-Type")
                not in ("RequestResponse", b"RequestResponse")
                or headers.get("X-Amz-Log-Type") not in ("None", b"None")
            ):
                self.result.blocked_send_callbacks += 1
                self.failed = True
                raise AdapterError("PARENT_SEND_BLOCKED")
            self.result.approved_send_callbacks += 1

    def _metadata(self, response, *, service_error=False):
        """Bounded projection only; no HTTP headers, Error.Message or LogResult."""
        metadata = response.get("ResponseMetadata")
        invalid = False
        fields = {}
        for key, pattern in (("RequestId", ID),):
            value = metadata.get(key) if type(metadata) is dict else None
            if type(value) is str and pattern.fullmatch(value):
                fields[key] = value
            else:
                invalid = True
        for key in ("HTTPStatusCode", "RetryAttempts"):
            value = metadata.get(key) if type(metadata) is dict else None
            lower, upper = (100, 599) if key == "HTTPStatusCode" else (0, 999)
            if type(value) is int and lower <= value <= upper:
                fields[key] = value
            else:
                invalid = True
        if type(metadata) is dict:
            self.result.metadata["ResponseMetadata"] = fields
            self.result.metadata_state = "OBJECT_PROJECTION"
        elif "ResponseMetadata" not in response:
            self.result.metadata_state = "MISSING"
        elif metadata is None:
            self.result.metadata["ResponseMetadata"] = None
            self.result.metadata_state = "NULL"
        else:
            self.result.metadata_state = "INVALID"
        if fields.get("RetryAttempts") != 0:
            self.result.fail("PARENT_RETRY_INVALID")
        if not service_error:
            status = response.get("StatusCode")
            version = response.get("ExecutedVersion")
            error = response.get("FunctionError")
            if type(status) is int and 0 <= status <= 999:
                self.result.metadata["StatusCode"] = status
            if type(version) is str and (
                version == "$LATEST" or re.fullmatch(r"[1-9][0-9]{0,19}", version)
            ):
                self.result.metadata["ExecutedVersion"] = version
            if error in (None, "Handled", "Unhandled"):
                if "FunctionError" in response:
                    self.result.metadata["FunctionError"] = error
            else:
                invalid = True
            if (
                type(status) is not int
                or status != 200
                or fields.get("HTTPStatusCode") != 200
                or "ExecutedVersion" not in self.result.metadata
                or "LogResult" in response
            ):
                invalid = True
            if (
                "ExecutedVersion" in self.result.metadata
                and self.request["Qualifier"] != "$LATEST"
                and version != self.request["Qualifier"]
            ):
                self.result.fail("PARENT_VERSION_MISMATCH")
        if invalid:
            self.result.fail("PARENT_RESPONSE_INVALID")

    def _propagated_defect(self):
        if "PARENT_DEFECT_PROPAGATED" not in self.result.failures:
            self.result.fail("PARENT_DEFECT_PROPAGATED")

    def _close(self, close, flag, code, *, propagating=False):
        """Preserve a primary defect; re-raise a lone unexpected close defect."""
        try:
            close()
            setattr(self.result, flag, True)
        except (*self.transport_errors, OSError, ValueError, KeyboardInterrupt):
            self.result.fail(code)
        except BaseException:
            # Only this resource-close boundary intercepts unrelated errors.
            # A secondary error must not replace an already-propagating defect.
            if not propagating:
                self._propagated_defect()
            self.result.fail(code)
            if not propagating:
                raise

    def _read(self, response):
        body = response.get("Payload")
        if not callable(getattr(body, "read", None)) or not callable(
            getattr(body, "close", None)
        ):
            self.result.fail("PARENT_RESPONSE_INVALID")
            if callable(getattr(body, "close", None)):
                self._close(body.close, "body_closed", "PARENT_CLOSE_FAILED")
            return
        parts, size = [], 0
        normal_exit = False
        try:
            while True:
                part = body.read(min(8192, RESPONSE_LIMIT + 1 - size))
                if type(part) is not bytes:
                    self.result.fail("PARENT_BODY_INVALID")
                    break
                if not part:
                    self.result.body_eof = True
                    break
                remaining = RESPONSE_LIMIT - size
                parts.append(part[:remaining])
                if len(part) > remaining:
                    self.result.fail("PARENT_BODY_TOO_LARGE")
                    break
                size += len(part)
            normal_exit = True
        except (*self.transport_errors, OSError, ValueError, KeyboardInterrupt):
            self.result.fail("PARENT_OUTCOME_UNKNOWN")
            normal_exit = True
        finally:
            if not normal_exit:
                self._propagated_defect()
            # Preserve bytes even if close fails or an unrelated defect propagates.
            self.result.body = b"".join(parts)
            self._close(
                body.close,
                "body_closed",
                "PARENT_CLOSE_FAILED",
                propagating=not normal_exit,
            )

    def invoke_once(self):
        with self.lock:
            require(not self.used, "PARENT_ALREADY_ATTEMPTED")
            self.used = True
            self.result.dispatch_entries = 1
        normal_exit = False
        try:
            response = self.client.invoke(**self.request)
            if type(response) is not dict:
                self.result.fail("PARENT_RESPONSE_INVALID")
            else:
                self._metadata(response)
                self._read(response)
            normal_exit = True
        except AdapterError as error:
            self.result.fail(str(error))
            normal_exit = True
        except self.service_errors as error:
            self.result.fail("PARENT_SERVICE_ERROR")
            response = getattr(error, "response", None)
            if type(response) is dict:
                self._metadata(response, service_error=True)
            normal_exit = True
        except (*self.transport_errors, OSError, KeyboardInterrupt):
            self.result.fail("PARENT_OUTCOME_UNKNOWN")
            normal_exit = True
        finally:
            if not normal_exit:
                self._propagated_defect()
            self._close(
                self.client.close,
                "client_closed",
                "CLIENT_CLOSE_FAILED",
                propagating=not normal_exit,
            )
        if (
            self.result.parameter_checks != 1
            or self.result.approved_send_callbacks != 1
            or self.failed
        ):
            self.result.fail("PARENT_HOOKS_INVALID")
        if not self.result.failures:
            self.result.code = "RETURNED"
        return self.result
