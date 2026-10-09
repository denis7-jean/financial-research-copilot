"""Invented injected clients only, including real installed SDK exception types."""

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import botocore.exceptions as e
import pytest

from scripts import jev_rag_smoke_live_adapter as adapter
from scripts import jev_rag_smoke_operator as operator
from tests import offline_guard

PAYLOAD = b'{"invented":"only"}\n'
TARGET = {
    "account": "123456789012",
    "region": "us-east-1",
    "function_name": "invented-smoke",
    "qualifier": "7",
}
SETTINGS = {"max_attempts": 1, "connect_seconds": 2, "read_seconds": 10}
SECRET = "invented-private-query-or-error"


class Events:
    def __init__(self):
        self.handlers = {}

    def register(self, name, fn):
        self.handlers.setdefault(name, []).append(fn)

    def emit(self, name, **kwargs):
        for fn in self.handlers.get(name, []):
            fn(**kwargs)


class Stream:
    def __init__(self, parts, error=None, close_error=None):
        self.parts = list(parts)
        self.error = error
        self.close_error = close_error
        self.reads = self.closes = 0
        self.sizes = []

    def read(self, size):
        self.reads += 1
        self.sizes.append(size)
        if self.parts:
            return self.parts.pop(0)
        if self.error:
            raise self.error
        return b""

    def close(self):
        self.closes += 1
        if self.close_error:
            raise self.close_error


class Client:
    def __init__(self):
        self.meta = SimpleNamespace(
            endpoint_url=adapter.ENDPOINT,
            events=Events(),
            config=SimpleNamespace(
                region_name="us-east-1",
                connect_timeout=2,
                read_timeout=10,
                retries={"total_max_attempts": 1, "mode": "standard"},
            ),
        )
        self.stream = Stream([b'{"invented":true}'])
        self.response = {
            "Payload": self.stream,
            "StatusCode": 200,
            "ExecutedVersion": "7",
            "ResponseMetadata": {
                "RequestId": "invented-sdk-id",
                "RetryAttempts": 0,
                "HTTPStatusCode": 200,
            },
        }
        self.calls = self.delivered = self.closes = 0
        self.error = self.close_error = None
        self.sends = 1
        self.skip_hooks = False
        self.mutate_params = lambda p: p
        self.mutate_send = lambda r: r

    def invoke(self, **params):
        self.calls += 1
        if not self.skip_hooks:
            self.meta.events.emit(
                "before-parameter-build.*.*",
                model=SimpleNamespace(name="Invoke"),
                params=self.mutate_params(dict(params)),
            )
            url = (
                adapter.ENDPOINT
                + "/2015-03-31/functions/"
                + adapter.quote(params["FunctionName"], safe="")
                + "/invocations?Qualifier="
                + adapter.quote(params["Qualifier"], safe="")
            )
            for _ in range(self.sends):
                self.meta.events.emit(
                    "before-send.*.*",
                    request=self.mutate_send(
                        SimpleNamespace(
                            method="POST",
                            url=url,
                            body=params["Payload"],
                            headers={
                                "X-Amz-Invocation-Type": b"RequestResponse",
                                "X-Amz-Log-Type": b"None",
                            },
                        )
                    ),
                )
                self.delivered += (
                    1  # Invented observation; not inferred from a callback.
                )
        if self.error:
            raise self.error
        return self.response

    def close(self):
        self.closes += 1
        if self.close_error:
            raise self.close_error


def bound(client=None, **kwargs):
    client = client or Client()
    return client, adapter.ParentTransport(
        client,
        kwargs.get("target", TARGET),
        kwargs.get("settings", SETTINGS),
        kwargs.get("payload", PAYLOAD),
    )


def assert_stopped(result, code):
    assert code in result.failures
    summary = result.summary()
    assert summary["delivery"] == "UNESTABLISHED"
    assert summary["reservation_release"] == "NONE"
    assert summary["authenticated_observation"] is False
    assert SECRET not in json.dumps(summary) + repr(result)


def test_pure_import_source_and_fresh_execution(monkeypatch):
    import builtins
    import os
    import boto3
    import dotenv

    path = Path(adapter.__file__)
    raw = path.read_text()
    tree = ast.parse(raw)
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert all(
        (n.module if isinstance(n, ast.ImportFrom) else n.names[0].name).split(".")[0]
        in {"dataclasses", "hashlib", "json", "re", "threading", "urllib"}
        for n in imports
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("side effect")

    monkeypatch.setattr(boto3, "client", forbidden)
    monkeypatch.setattr(boto3, "Session", forbidden)
    monkeypatch.setattr(dotenv, "load_dotenv", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)

    class NoEnvironment(dict):
        __getitem__ = get = __contains__ = forbidden

    monkeypatch.setattr(os, "environ", NoEnvironment())
    original = builtins.__import__

    def checked(name, *args, **kwargs):
        assert not name.startswith(("boto3", "botocore", "app", "dotenv"))
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", checked)
    exec(compile(raw, str(path), "exec"), {"__name__": "invented_import"})


def test_positive_and_exact_request():
    client, transport = bound()
    result = transport.invoke_once()
    assert result.code == "RETURNED" and not result.failures
    assert result.body == b'{"invented":true}'
    assert result.body_eof and result.body_closed and result.client_closed
    assert (
        result.dispatch_entries
        == result.parameter_checks
        == result.approved_send_callbacks
        == 1
    )
    assert (
        client.calls == client.delivered == client.closes == client.stream.closes == 1
    )
    assert transport.request == {
        "FunctionName": "arn:aws:lambda:us-east-1:123456789012:function:invented-smoke",
        "Qualifier": "7",
        "Payload": PAYLOAD,
        "InvocationType": "RequestResponse",
        "LogType": "None",
    }
    assert result.metadata["ResponseMetadata"]["RequestId"] == "invented-sdk-id"
    assert result.summary()["sdk_request_id_is_execution_id"] is False
    assert result.summary()["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"


def test_not_simulation_and_existing_operator_rejects():
    client, transport = bound()
    assert not hasattr(transport, "simulation_only")
    assert not hasattr(client, "simulation_only")
    with pytest.raises(operator.OperatorError, match="SIMULATED_CLIENT_REQUIRED"):
        operator.bind(client, TARGET, SETTINGS, transport.request)
    assert client.calls == 0


@pytest.mark.parametrize(
    "payload",
    [
        b"{}",
        b"{}\r\n",
        b'{"x":1,"x":1}\n',
        b'{"x":NaN}\n',
        b'{"x":1e999}\n',
        b"[]\n",
        b"\xff",
        b"{}\n" + b" " * adapter.EVENT_LIMIT,
    ],
    ids=[
        "no-lf",
        "crlf",
        "duplicate",
        "nan",
        "overflow",
        "array",
        "unicode",
        "oversize",
    ],
)
def test_invalid_payload_before_hooks_or_dispatch(payload):
    c = Client()
    with pytest.raises(adapter.AdapterError, match="INPUT_INVALID"):
        bound(c, payload=payload)
    assert not c.meta.events.handlers and c.calls == 0


@pytest.mark.parametrize(
    "key,value",
    [
        ("region", "us-west-2"),
        ("account", "123"),
        ("function_name", "other:alias"),
        ("qualifier", "alias"),
        ("qualifier", "0"),
        ("qualifier", 7),
    ],
)
def test_invalid_targets(key, value):
    target = dict(TARGET, **{key: value})
    with pytest.raises(adapter.AdapterError, match="INPUT_INVALID"):
        bound(target=target)


@pytest.mark.parametrize(
    "key,value",
    [
        ("max_attempts", 2),
        ("max_attempts", True),
        ("connect_seconds", 0),
        ("read_seconds", 121),
    ],
)
def test_invalid_settings(key, value):
    with pytest.raises(adapter.AdapterError, match="INPUT_INVALID"):
        bound(settings=dict(SETTINGS, **{key: value}))


@pytest.mark.parametrize(
    "key,value",
    [
        ("endpoint_url", "https://example.invalid"),
        ("region_name", "us-west-2"),
        ("connect_timeout", 3),
        ("read_timeout", 9),
        ("retries", {"max_attempts": 0}),
        ("retries", {"total_max_attempts": True, "mode": "standard"}),
    ],
)
def test_client_configuration(key, value):
    c = Client()
    setattr(c.meta if key == "endpoint_url" else c.meta.config, key, value)
    with pytest.raises(adapter.AdapterError, match="CLIENT_CONFIG_INVALID"):
        bound(c)
    assert c.calls == 0 and not c.meta.events.handlers


@pytest.mark.parametrize(
    "key,value",
    [
        ("FunctionName", "substitution"),
        ("Qualifier", "8"),
        ("Payload", b"{}\n"),
        ("LogType", "Tail"),
        ("InvocationType", "Event"),
    ],
)
def test_parameter_substitutions(key, value):
    c = Client()
    c.mutate_params = lambda p: dict(p, **{key: value})
    _, t = bound(c)
    assert_stopped(t.invoke_once(), "PARENT_REQUEST_INVALID")
    assert c.delivered == 0 and c.closes == 1


@pytest.mark.parametrize(
    "key,value",
    [
        ("method", "GET"),
        ("url", "https://example.invalid"),
        ("body", b"{}\n"),
        ("headers", {}),
    ],
)
def test_send_substitutions(key, value):
    c = Client()

    def mutation(r):
        setattr(r, key, value)
        return r

    c.mutate_send = mutation
    _, t = bound(c)
    assert_stopped(t.invoke_once(), "PARENT_SEND_BLOCKED")
    assert c.delivered == 0


def test_blocked_second_send_and_no_reentry():
    c = Client()
    c.sends = 2
    _, t = bound(c)
    result = t.invoke_once()
    assert_stopped(result, "PARENT_SEND_BLOCKED")
    assert (
        result.approved_send_callbacks
        == result.blocked_send_callbacks
        == c.delivered
        == 1
    )
    with pytest.raises(adapter.AdapterError, match="PARENT_ALREADY_ATTEMPTED"):
        t.invoke_once()
    assert c.calls == 1


@pytest.mark.parametrize(
    "error",
    [
        e.ConnectTimeoutError(endpoint_url=SECRET),
        e.ReadTimeoutError(endpoint_url=SECRET),
        e.EndpointConnectionError(endpoint_url=SECRET),
        e.ConnectionClosedError(endpoint_url=SECRET),
        e.ProxyConnectionError(proxy_url=SECRET),
        e.SSLError(endpoint_url=SECRET, error=SECRET),
        e.HTTPClientError(error=SECRET),
        e.ResponseStreamingError(error=SECRET),
        e.IncompleteReadError(actual_bytes=1, expected_bytes=8),
        OSError(SECRET),
        KeyboardInterrupt(),
        e.ParamValidationError(report=SECRET),
        e.NoCredentialsError(),
        e.PartialCredentialsError(provider="invented", cred_var=SECRET),
        e.CredentialRetrievalError(provider="invented", error_msg=SECRET),
    ],
)
def test_transport_failures_uncertain_and_not_retried(error):
    c = Client()
    c.error = error
    _, t = bound(c)
    result = t.invoke_once()
    assert_stopped(result, "PARENT_OUTCOME_UNKNOWN")
    assert c.calls == c.closes == 1
    with pytest.raises(adapter.AdapterError, match="PARENT_ALREADY_ATTEMPTED"):
        t.invoke_once()


def test_service_exception_projection_not_provider_message():
    c = Client()
    c.error = e.ClientError(
        {
            "Error": {"Code": "AccessDeniedException", "Message": SECRET},
            "ResponseMetadata": {
                "RequestId": "invented-service-id",
                "RetryAttempts": 0,
                "HTTPStatusCode": 403,
                "HTTPHeaders": {"secret": SECRET},
            },
        },
        "Invoke",
    )
    _, t = bound(c)
    result = t.invoke_once()
    assert_stopped(result, "PARENT_SERVICE_ERROR")
    assert result.metadata == {
        "ResponseMetadata": {
            "RequestId": "invented-service-id",
            "RetryAttempts": 0,
            "HTTPStatusCode": 403,
        }
    }
    assert c.calls == 1


@pytest.mark.parametrize(
    "error",
    [
        e.ReadTimeoutError(endpoint_url=SECRET),
        e.ResponseStreamingError(error=SECRET),
        e.IncompleteReadError(actual_bytes=3, expected_bytes=9),
        OSError(SECRET),
    ],
)
def test_partial_read_preserved(error):
    c = Client()
    c.response["Payload"] = c.stream = Stream([b"first", b"\xe2\x82"], error=error)
    _, t = bound(c)
    result = t.invoke_once()
    assert_stopped(result, "PARENT_OUTCOME_UNKNOWN")
    assert result.body == b"first\xe2\x82"
    assert not result.body_eof and result.body_closed and c.stream.closes == 1


@pytest.mark.parametrize("where", ["body", "client", "both"])
def test_close_failures_keep_complete_bytes(where):
    c = Client()
    if where in ("body", "both"):
        c.stream.close_error = e.ResponseStreamingError(error=SECRET)
    if where in ("client", "both"):
        c.close_error = OSError(SECRET)
    _, t = bound(c)
    result = t.invoke_once()
    assert result.body == b'{"invented":true}' and result.body_eof
    assert_stopped(
        result, "PARENT_CLOSE_FAILED" if where != "client" else "CLIENT_CLOSE_FAILED"
    )
    assert c.calls == c.closes == c.stream.closes == 1
    if where == "both":
        assert result.failures == ["PARENT_CLOSE_FAILED", "CLIENT_CLOSE_FAILED"]


def test_split_utf8_and_exact_limit():
    raw = b'"' + b"a" * (adapter.RESPONSE_LIMIT - 5) + b'\xe2\x82\xac"'
    assert len(raw) == adapter.RESPONSE_LIMIT
    c = Client()
    c.response["Payload"] = c.stream = Stream([raw[:-3], raw[-3:-2], raw[-2:]])
    _, t = bound(c)
    r = t.invoke_once()
    assert r.body == raw and r.body_eof and r.code == "RETURNED"
    assert json.loads(r.body).endswith("€")


@pytest.mark.parametrize(
    "parts",
    [
        [b"x" * adapter.RESPONSE_LIMIT, b"y", b"never"],
        [b"x" * (adapter.RESPONSE_LIMIT + 900), b"never"],
    ],
)
def test_oversize_prefix_retained_and_no_further_read(parts):
    c = Client()
    c.response["Payload"] = c.stream = Stream(parts)
    _, t = bound(c)
    r = t.invoke_once()
    assert_stopped(r, "PARENT_BODY_TOO_LARGE")
    assert len(r.body) == adapter.RESPONSE_LIMIT and c.stream.parts == [b"never"]
    assert c.stream.closes == 1 and not r.body_eof


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "null",
        "retry",
        "retry_bool",
        "long_id",
        "bad_status",
        "version",
        "log",
    ],
)
def test_invalid_metadata_keeps_bytes(change):
    c = Client()
    if change == "missing":
        del c.response["ResponseMetadata"]
    elif change == "null":
        c.response["ResponseMetadata"] = None
    elif change in ("retry", "retry_bool"):
        c.response["ResponseMetadata"]["RetryAttempts"] = (
            1 if change == "retry" else True
        )
    elif change == "long_id":
        c.response["ResponseMetadata"]["RequestId"] = SECRET * 100
    elif change == "bad_status":
        c.response["ResponseMetadata"]["HTTPStatusCode"] = 201
    elif change == "version":
        c.response["ExecutedVersion"] = "8"
    else:
        c.response["LogResult"] = SECRET
    _, t = bound(c)
    r = t.invoke_once()
    assert r.body == b'{"invented":true}' and r.failures
    assert SECRET not in json.dumps(r.metadata)
    assert r.summary()["delivery"] == "UNESTABLISHED"
    assert c.calls == 1


def test_retry_metadata_never_fabricates_sends_or_releases():
    c = Client()
    c.response["ResponseMetadata"]["RetryAttempts"] = 3
    _, t = bound(c)
    r = t.invoke_once()
    assert_stopped(r, "PARENT_RETRY_INVALID")
    assert r.approved_send_callbacks == 1 and c.delivered == 1
    assert r.metadata["ResponseMetadata"]["RetryAttempts"] == 3


def test_skipped_hooks_and_unrelated_defect():
    c = Client()
    c.skip_hooks = True
    _, t = bound(c)
    assert_stopped(t.invoke_once(), "PARENT_HOOKS_INVALID")
    c = Client()
    c.response["Payload"] = c.stream = Stream([b"private"], error=RuntimeError(SECRET))
    _, t = bound(c)
    with pytest.raises(RuntimeError, match=SECRET):
        t.invoke_once()
    assert t.result.body == b"private" and c.stream.closes == c.closes == 1
    with pytest.raises(adapter.AdapterError, match="PARENT_ALREADY_ATTEMPTED"):
        t.invoke_once()


def test_ordinary_function_error_still_preserves_response():
    c = Client()
    c.response["FunctionError"] = "Unhandled"
    _, t = bound(c)
    r = t.invoke_once()
    assert r.code == "RETURNED" and r.metadata["FunctionError"] == "Unhandled"
    # Returned transport is not success of the handler or experiment.
    assert r.summary()["report_evidence"].startswith("INCOMPLETE")


def test_guard_active():
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


def test_public_request_copy_and_latest():
    c, t = bound(target=dict(TARGET, qualifier="$LATEST"))
    edited = t.request
    edited["FunctionName"] = "substituted"
    c.response["ExecutedVersion"] = "$LATEST"
    assert t.invoke_once().code == "RETURNED"
    assert t.request["FunctionName"].endswith(":function:invented-smoke")


@pytest.mark.parametrize("value", [None, 1, "not-bytes"])
def test_malformed_body_retains_prefix_and_closes(value):
    c = Client()
    c.response["Payload"] = c.stream = Stream([b"prefix", value])
    _, t = bound(c)
    r = t.invoke_once()
    assert_stopped(r, "PARENT_BODY_INVALID")
    assert r.body == b"prefix" and c.stream.closes == 1


def test_payload_without_read_is_closed():
    c = Client()
    c.response["Payload"] = SimpleNamespace(
        close=lambda: setattr(c, "body_closed", True)
    )
    _, t = bound(c)
    assert_stopped(t.invoke_once(), "PARENT_RESPONSE_INVALID")
    assert c.body_closed


def test_injected_exception_definitions_and_no_factories():
    c = Client()
    t = adapter.ParentTransport(
        c, TARGET, SETTINGS, PAYLOAD, errors=((e.ClientError,), (e.ReadTimeoutError,))
    )
    assert t.invoke_once().code == "RETURNED"


def test_repeat_parameter_hook_unsupported_operation_and_send_before_dispatch():
    for action in ("repeat", "operation", "early"):
        c, t = bound()
        if action == "early":
            with pytest.raises(adapter.AdapterError, match="PARENT_SEND_BLOCKED"):
                t.send_hook(SimpleNamespace())
            assert c.calls == 0
        else:
            t.result.dispatch_entries = 1
            model = SimpleNamespace(
                name="Invoke" if action == "repeat" else "ListFunctions"
            )
            if action == "repeat":
                t.parameters_hook(model, t.request)
            with pytest.raises(adapter.AdapterError, match="PARENT_REQUEST_INVALID"):
                t.parameters_hook(model, t.request)
        assert t.failed


@pytest.mark.parametrize("stage", ["read", "body-close", "client-close"])
def test_closed_stream_value_error_is_sanitized_locally(stage):
    c = Client()
    if stage == "read":
        c.stream.error = ValueError(SECRET)
    elif stage == "body-close":
        c.stream.close_error = ValueError(SECRET)
    else:
        c.close_error = ValueError(SECRET)
    _, t = bound(c)
    r = t.invoke_once()
    code = {
        "read": "PARENT_OUTCOME_UNKNOWN",
        "body-close": "PARENT_CLOSE_FAILED",
        "client-close": "CLIENT_CLOSE_FAILED",
    }[stage]
    assert_stopped(r, code)
    assert r.body == b'{"invented":true}'


def test_invoke_value_error_is_not_globally_hidden():
    c = Client()
    c.error = ValueError(SECRET)
    _, t = bound(c)
    with pytest.raises(ValueError, match=SECRET):
        t.invoke_once()
    assert c.closes == 1


def test_installed_sdk_config_and_invoke_serialization_without_client():
    import gzip
    import botocore
    from botocore.config import Config
    from botocore.model import ServiceModel
    from botocore.serialize import create_serializer

    c = Client()
    c.meta.config = Config(
        region_name="us-east-1",
        connect_timeout=2,
        read_timeout=10,
        retries={"total_max_attempts": 1, "mode": "standard"},
    )
    _, t = bound(c)
    # Read installed public service metadata only; no Session, loader or client.
    path = Path(botocore.__file__).parent / "data/lambda/2015-03-31/service-2.json.gz"
    with gzip.open(path, "rb") as source:
        model = ServiceModel(json.load(source), service_name="lambda")
    wire = create_serializer("rest-json").serialize_to_request(
        t.request, model.operation_model("Invoke")
    )
    assert wire["method"] == "POST"
    assert adapter.ENDPOINT + wire["url_path"] == t.url.split("?")[0]
    assert wire["query_string"] == {"Qualifier": "7"}
    assert wire["body"] == PAYLOAD
    assert wire["headers"]["X-Amz-Invocation-Type"] == "RequestResponse"
    assert wire["headers"]["X-Amz-Log-Type"] == "None"
    assert c.calls == 0


@pytest.mark.parametrize("state", ["MISSING", "NULL", "INVALID"])
def test_metadata_presence_is_not_fabricated(state):
    c = Client()
    if state == "MISSING":
        del c.response["ResponseMetadata"]
    else:
        c.response["ResponseMetadata"] = None if state == "NULL" else SECRET
    _, t = bound(c)
    r = t.invoke_once()
    assert_stopped(r, "PARENT_RESPONSE_INVALID")
    assert r.metadata_state == state
    assert ("ResponseMetadata" in r.metadata) == (state == "NULL")
    assert SECRET not in json.dumps(r.metadata)
