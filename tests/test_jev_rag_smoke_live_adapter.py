"""Invented injected clients only, including real installed SDK exception types."""

import ast
import base64
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
                                "X-Amz-Log-Type": getattr(
                                    self, "log_type", "None"
                                ).encode("ascii"),
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
        in {
            "dataclasses",
            "base64",
            "binascii",
            "decimal",
            "hashlib",
            "json",
            "re",
            "threading",
            "urllib",
        }
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
    assert_stopped(t.result, "PARENT_DEFECT_PROPAGATED")


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


@pytest.mark.parametrize(
    "stage,exception_type",
    [
        ("invoke", RuntimeError),
        ("read", RuntimeError),
        ("before-hooks", RuntimeError),
        ("invoke", ValueError),
        ("before-hooks", ValueError),
    ],
)
def test_ad1_original_defect_truthful_state_and_reentry(stage, exception_type):
    from botocore.response import StreamingBody

    error = exception_type(SECRET)

    class BeforeHooks(Client):
        def invoke(self, **params):
            self.calls += 1
            raise error

    c = BeforeHooks() if stage == "before-hooks" else Client()
    if stage == "read":
        raw_stream = Stream([b"prefix-", b"more"], error=error)
        c.response["Payload"] = StreamingBody(raw_stream, 4096)
    else:
        c.error = error
    _, t = bound(c)
    assert t.result.code == "NOT_RETURNED"
    with pytest.raises(exception_type) as caught:
        t.invoke_once()
    assert caught.value is error
    names = []
    trace = caught.value.__traceback__
    while trace:
        names.append(trace.tb_frame.f_code.co_name)
        trace = trace.tb_next
    assert names[-1] == ("read" if stage == "read" else "invoke")
    assert t.result.failures == ["PARENT_DEFECT_PROPAGATED"]
    assert_stopped(t.result, "PARENT_DEFECT_PROPAGATED")
    assert t.result.summary()["code"] == "PARENT_DEFECT_PROPAGATED"
    assert t.result.dispatch_entries == c.calls == c.closes == 1
    assert t.result.client_closed and not t.result.body_eof
    expected_hooks = 0 if stage == "before-hooks" else 1
    assert (
        t.result.parameter_checks
        == t.result.approved_send_callbacks
        == c.delivered
        == expected_hooks
    )
    assert t.result.blocked_send_callbacks == 0
    if stage == "read":
        assert t.result.body == b"prefix-more" and raw_stream.closes == 1
        assert t.result.body_closed
        assert t.result.metadata_state == "OBJECT_PROJECTION"
        assert t.result.metadata == {
            "ResponseMetadata": {
                "RequestId": "invented-sdk-id",
                "RetryAttempts": 0,
                "HTTPStatusCode": 200,
            },
            "StatusCode": 200,
            "ExecutedVersion": "7",
        }
    else:
        assert t.result.body == b"" and t.result.metadata_state == "NOT_RECEIVED"
    before = t.result.summary()
    with pytest.raises(adapter.AdapterError, match="PARENT_ALREADY_ATTEMPTED"):
        t.invoke_once()
    assert t.result.summary() == before and c.calls == 1


@pytest.mark.parametrize("where", ["body", "client", "both"])
@pytest.mark.parametrize("secondary", [RuntimeError, OSError])
def test_ad1_cleanup_cannot_replace_read_defect(where, secondary):
    primary = RuntimeError(SECRET)
    c = Client()
    c.response["Payload"] = c.stream = Stream([b"received"], error=primary)
    if where in ("body", "both"):
        c.stream.close_error = secondary("invented secondary body failure")
    if where in ("client", "both"):
        c.close_error = secondary("invented secondary client failure")
    _, t = bound(c)
    with pytest.raises(RuntimeError) as caught:
        t.invoke_once()
    assert caught.value is primary and caught.value.__context__ is None
    assert t.result.body == b"received" and not t.result.body_eof
    expected = ["PARENT_DEFECT_PROPAGATED"]
    if where in ("body", "both"):
        expected.append("PARENT_CLOSE_FAILED")
    if where in ("client", "both"):
        expected.append("CLIENT_CLOSE_FAILED")
    assert t.result.code == "PARENT_DEFECT_PROPAGATED" and t.result.failures == expected
    assert t.result.metadata["ResponseMetadata"]["RequestId"] == "invented-sdk-id"
    assert c.stream.closes == c.closes == 1
    assert t.result.body_closed == (where == "client")
    assert t.result.client_closed == (where == "body")
    assert_stopped(t.result, "PARENT_DEFECT_PROPAGATED")


def test_ad1_invoke_defect_survives_unrelated_client_close_defect():
    primary = RuntimeError(SECRET)
    c = Client()
    c.error = primary
    c.close_error = RuntimeError("invented close defect")
    _, t = bound(c)
    with pytest.raises(RuntimeError) as caught:
        t.invoke_once()
    assert caught.value is primary and caught.value.__context__ is None
    assert t.result.failures == ["PARENT_DEFECT_PROPAGATED", "CLIENT_CLOSE_FAILED"]
    assert t.result.approved_send_callbacks == c.delivered == c.calls == c.closes == 1
    assert not t.result.client_closed


@pytest.mark.parametrize("where", ["body", "client"])
def test_ad1_lone_unrelated_close_defect_still_propagates(where):
    error = RuntimeError(SECRET)
    c = Client()
    if where == "body":
        c.stream.close_error = error
    else:
        c.close_error = error
    _, t = bound(c)
    with pytest.raises(RuntimeError) as caught:
        t.invoke_once()
    assert caught.value is error
    assert t.result.body == b'{"invented":true}' and t.result.body_eof
    assert t.result.failures == [
        "PARENT_DEFECT_PROPAGATED",
        "PARENT_CLOSE_FAILED" if where == "body" else "CLIENT_CLOSE_FAILED",
    ]
    assert t.result.metadata_state == "OBJECT_PROJECTION"
    assert_stopped(t.result, "PARENT_DEFECT_PROPAGATED")


def test_ad1_invalid_metadata_and_read_defect_preserve_primary_fixed_failure():
    c = Client()
    c.response["FunctionError"] = SECRET
    c.response["Payload"] = c.stream = Stream([b"prefix"], error=RuntimeError(SECRET))
    _, t = bound(c)
    with pytest.raises(RuntimeError):
        t.invoke_once()
    assert t.result.code == "PARENT_RESPONSE_INVALID"
    assert t.result.failures == ["PARENT_RESPONSE_INVALID", "PARENT_DEFECT_PROPAGATED"]
    assert t.result.body == b"prefix" and c.stream.closes == c.closes == 1
    assert "FunctionError" not in t.result.metadata
    assert SECRET not in json.dumps(t.result.summary()) + json.dumps(t.result.metadata)


# Tail-specific cases. The inherited None assertions above are unchanged.
EXECUTION_ID = "invented-execution-id"
TEXT_REPORT = (
    "REPORT RequestId: invented-execution-id\tDuration: 1.25 ms\t"
    "Billed Duration: 2 ms\tMemory Size: 512 MB\tMax Memory Used: 160 MB\n"
).encode()


def tail_bound(client=None, raw=TEXT_REPORT, target=TARGET):
    client = client or Client()
    client.log_type = "Tail"
    client.response["LogResult"] = base64.b64encode(raw).decode()
    return client, adapter.ParentTransport(
        client,
        target,
        SETTINGS,
        PAYLOAD,
        log_type="Tail",
        parser_contract=adapter.REPORT_CONTRACT,
    )


def json_report(**changes):
    metrics = dict(
        durationMs=1.25, billedDurationMs=2, memorySizeMB=512, maxMemoryUsedMB=160
    )
    metrics.update(changes)
    return (
        json.dumps(
            dict(
                type="platform.report",
                record=dict(requestId=EXECUTION_ID, metrics=metrics),
            )
        )
        + "\n"
    ).encode()


@pytest.mark.parametrize(
    "raw",
    [
        TEXT_REPORT,
        json_report(),
        b"START RequestId: invented-execution-id Version: 7\n"
        + TEXT_REPORT
        + b"END RequestId: invented-execution-id\n",
    ],
)
def test_tail_text_json_and_separate_identity(raw):
    c, t = tail_bound(raw=raw)
    r = t.invoke_once()
    assert r.code == "RETURNED" and r.log_state == "DECODED"
    assert r.log_decoded == raw and r.log_encoded == c.response["LogResult"].encode()
    assert r.log_encoded_complete and r.log_decoded_complete
    joined = adapter.parse_report(raw, "7", "7")
    assert joined["execution_request_id"] == EXECUTION_ID
    assert joined["execution_request_id"] != r.metadata["ResponseMetadata"]["RequestId"]
    assert joined["report"]["duration_ms"] == "1.25"
    assert joined["initialization_measurement"] == "UNAVAILABLE"
    assert joined["report"]["init_duration_ms"] is None
    assert (
        not joined["authenticated_observation"] and not joined["complete_execution_log"]
    )
    assert joined["warm_execution"] == "UNESTABLISHED"
    assert r.summary()["sdk_request_id_is_execution_id"] is False
    assert c.calls == c.delivered == c.closes == c.stream.closes == 1


@pytest.mark.parametrize("version", ["$LATEST", "7"])
def test_tail_latest_not_immutable(version):
    c, t = tail_bound(target=dict(TARGET, qualifier="$LATEST"))
    c.response["ExecutedVersion"] = version
    assert t.invoke_once().code == "RETURNED"
    assert (
        adapter.parse_report(TEXT_REPORT, version, "$LATEST")[
            "immutable_code_identity_established"
        ]
        is False
    )


@pytest.mark.parametrize(
    "value,state",
    [
        (None, "NULL"),
        (1, "INVALID_TYPE"),
        ({"private": SECRET}, "INVALID_TYPE"),
        ("\u00e9" + SECRET, "INVALID_ASCII"),
        ("!" + SECRET, "INVALID_BASE64"),
        ("Zh==", "INVALID_BASE64"),
        ("A" * 5465, "OVERSIZED_ENCODED"),
        (base64.b64encode(b"a" * 4097).decode(), "OVERSIZED_DECODED"),
    ],
)
def test_tail_invalid_projection_is_bounded_and_labelled(value, state):
    c, t = tail_bound()
    c.response["LogResult"] = value
    r = t.invoke_once()
    assert r.log_state == state and "PARENT_LOG_INVALID" in r.failures
    assert len(r.log_encoded) <= 5464 and len(r.log_decoded) <= 4096
    if state in {"OVERSIZED_ENCODED", "INVALID_ASCII", "INVALID_TYPE"}:
        assert not r.log_encoded_complete
    assert not r.log_decoded_complete
    assert SECRET not in json.dumps(r.summary()) and SECRET not in repr(r)
    assert r.body_eof and c.calls == c.closes == c.stream.closes == 1


def test_tail_missing_and_null_are_distinct():
    c, t = tail_bound()
    del c.response["LogResult"]
    assert t.invoke_once().log_state == "MISSING"
    assert t.result.failures == ["PARENT_LOG_MISSING"]
    assert t.result.body and t.result.client_closed


@pytest.mark.parametrize("size", [4095, 4096])
def test_tail_byte_boundaries(size):
    raw = b"x" * (size - len(TEXT_REPORT) - 1) + b"\n" + TEXT_REPORT
    c, t = tail_bound(raw=raw)
    r = t.invoke_once()
    assert (
        r.log_encoded_complete and r.log_decoded_complete and len(r.log_decoded) == size
    )
    assert len(r.log_encoded) <= 5464
    assert (
        adapter.parse_report(r.log_decoded, "7", "7")["execution_request_id"]
        == EXECUTION_ID
    )


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        TEXT_REPORT[:-20],
        TEXT_REPORT + TEXT_REPORT,
        TEXT_REPORT + TEXT_REPORT.replace(EXECUTION_ID.encode(), b"other-id"),
        b"START RequestId: other-id Version: 7\n" + TEXT_REPORT,
        b"START RequestId: invented-execution-id Version: 8\n" + TEXT_REPORT,
        TEXT_REPORT + b"END RequestId: other-id\n",
        TEXT_REPORT.replace(b"1.25", b"NaN"),
        TEXT_REPORT.replace(b"2 ms", b"2.0 ms"),
        json_report(billedDurationMs=True),
        json_report(memorySizeMB=512.0),
        json_report(durationMs=float("nan")),
        json_report(durationMs=-1.25),
        json_report(durationMs=None),
        json_report(initDurationMs=None),
        json_report().replace(b"1.25", b"1E-999999999999"),
        json_report().replace(b"1.25", b"1E999999999"),
        json_report().replace(b"1.25", b"0E-999999999"),
        json_report().replace(b"1.25", b"1" * 129),
        json_report().replace(
            b'"durationMs": 1.25', b'"durationMs": 1.25, "durationMs": 1.25'
        ),
        b'{"type":"platform.report","record":\n' + TEXT_REPORT,
        (b'{"unknown":' + b"[" * 34 + b"0" + b"]" * 34 + b"}\n") + TEXT_REPORT,
    ],
)
def test_tail_parser_rejects_ambiguous_truncated_and_numeric_forms(raw):
    with pytest.raises(adapter.AdapterError, match="^REPORT_INVALID$"):
        adapter.parse_report(raw, "7", "7")


@pytest.mark.parametrize("token", [b"1E-64", b"1E64", b"0E-64", b"1E-12"])
def test_tail_numeric_boundaries_are_exact(token):
    raw = json_report().replace(b"1.25", token)
    joined = adapter.parse_report(raw, "7", "7")
    assert joined["report"]["duration_ms"] == str(adapter.Decimal(token.decode()))


@pytest.mark.parametrize("token", [b"1E-65", b"1E65", b"0E-65"])
def test_tail_numeric_just_outside_bounds(token):
    with pytest.raises(adapter.AdapterError, match="^REPORT_INVALID$"):
        adapter.parse_report(json_report().replace(b"1.25", token), "7", "7")


@pytest.mark.parametrize(
    "prefix",
    [
        b"cut leading application fragment\n",
        b'"message": "cut"}\n',
        b'"application": "cut\n',
        b"\x80 cut utf8\n",
        b'{"application": -1.25}\n',
    ],
)
def test_tail_unknown_content_and_leading_fragments(prefix):
    joined = adapter.parse_report(prefix + TEXT_REPORT, "7", "7")
    assert joined["execution_request_id"] == EXECUTION_ID
    assert not joined["complete_execution_log"]


@pytest.mark.parametrize(
    "raw",
    [
        TEXT_REPORT.replace(b"160 MB", b"160 MB\tInit Duration: 23.45 ms"),
        json_report(initDurationMs=23.45),
    ],
)
def test_tail_optional_init_preserved(raw):
    joined = adapter.parse_report(raw, "7", "7")
    assert joined["report"]["init_duration_ms"] == "23.45"
    assert joined["initialization_measurement"] == "REPORTED"
    assert joined["warm_execution"] == "UNESTABLISHED"


@pytest.mark.parametrize(
    "stage",
    [
        "sdk-read",
        "read-defect",
        "body-close",
        "client-close",
        "close-defect",
        "function-error",
    ],
)
def test_tail_survives_payload_and_cleanup_paths(stage):
    c, t = tail_bound()
    c.stream = c.response["Payload"] = Stream([b"prefix"])
    primary = RuntimeError(SECRET)
    if stage == "sdk-read":
        c.stream.error = e.ReadTimeoutError(endpoint_url=SECRET)
    if stage == "read-defect":
        c.stream.error = primary
    if stage == "body-close":
        c.stream.close_error = OSError(SECRET)
    if stage == "client-close":
        c.close_error = OSError(SECRET)
    if stage == "close-defect":
        c.stream.close_error = primary
    if stage == "function-error":
        c.response["FunctionError"] = "Unhandled"
    if stage in {"read-defect", "close-defect"}:
        with pytest.raises(RuntimeError) as caught:
            t.invoke_once()
        assert caught.value is primary
    else:
        t.invoke_once()
    r = t.result
    assert r.log_decoded == TEXT_REPORT and r.log_state == "DECODED"
    assert r.metadata["ResponseMetadata"]["RequestId"] == "invented-sdk-id"
    assert r.body == b"prefix" and c.calls == c.closes == c.stream.closes == 1
    if stage != "function-error":
        assert r.failures
    with pytest.raises(adapter.AdapterError, match="^PARENT_ALREADY_ATTEMPTED$"):
        t.invoke_once()
    assert c.calls == 1


@pytest.mark.parametrize("stage", ["parameters", "wire", "second"])
def test_tail_hooks_exact_and_second_send_blocked(stage):
    c, t = tail_bound()
    if stage == "parameters":
        c.mutate_params = lambda p: dict(p, LogType="None")
    if stage == "wire":
        c.mutate_send = lambda r: SimpleNamespace(
            **{**r.__dict__, "headers": {**r.headers, "X-Amz-Log-Type": b"None"}}
        )
    if stage == "second":
        c.sends = 2
    r = t.invoke_once()
    assert r.failures and c.calls == 1
    assert c.delivered == (1 if stage == "second" else 0)
    assert r.summary()["reservation_release"] == "NONE"


@pytest.mark.parametrize(
    "log_type,contract",
    [
        ("Tail", None),
        ("Tail", "other"),
        ("None", adapter.REPORT_CONTRACT),
        (True, None),
    ],
)
def test_tail_contract_is_explicit_before_hooks(log_type, contract):
    c = Client()
    with pytest.raises(adapter.AdapterError, match="^INPUT_INVALID$"):
        adapter.ParentTransport(
            c, TARGET, SETTINGS, PAYLOAD, log_type=log_type, parser_contract=contract
        )
    assert not c.meta.events.handlers and c.calls == 0


def test_tail_installed_sdk_serializer_exact_headers_without_client():
    from botocore.loaders import Loader
    from botocore.model import ServiceModel
    from botocore.serialize import create_serializer

    loader = Loader(
        extra_search_paths=[Loader.BUILTIN_DATA_PATH],
        include_default_search_paths=False,
    )
    model = ServiceModel(loader.load_service_model("lambda", "service-2"))
    serializer = create_serializer(model.resolved_protocol)
    operation = model.operation_model("Invoke")
    c, t = tail_bound()

    def invoke(**params):
        c.calls += 1
        c.meta.events.emit("before-parameter-build.*.*", model=operation, params=params)
        request = serializer.serialize_to_request(params, operation)
        sent = SimpleNamespace(
            method=request["method"],
            url=adapter.ENDPOINT + request["url_path"] + "?Qualifier=7",
            headers=request["headers"],
            body=request["body"],
        )
        c.meta.events.emit("before-send.*.*", request=sent)
        c.delivered += 1
        return c.response

    c.invoke = invoke
    assert t.invoke_once().code == "RETURNED"
    assert c.calls == c.delivered == t.result.approved_send_callbacks == 1
    assert t.result.log_decoded == TEXT_REPORT


@pytest.mark.parametrize(
    "changes",
    [dict(unknownMetric=1), dict(restoreDurationMs=True), dict(restoreDurationMs=-1)],
)
def test_tail_unknown_or_invalid_optional_metrics_reject(changes):
    with pytest.raises(adapter.AdapterError, match="^REPORT_INVALID$"):
        adapter.parse_report(json_report(**changes), "7", "7")


def test_tail_json_start_runtime_done_joins():
    prefix = b'{"type":"platform.start","record":{"requestId":"invented-execution-id","version":"7"}}\n'
    suffix = b'{"type":"platform.runtimeDone","record":{"requestId":"invented-execution-id","status":"success"}}\n'
    assert (
        adapter.parse_report(prefix + json_report() + suffix, "7", "7")[
            "execution_request_id"
        ]
        == EXECUTION_ID
    )
    for raw in (
        prefix.replace(b'"7"', b'"8"') + json_report(),
        json_report() + suffix.replace(EXECUTION_ID.encode(), b"other-id"),
    ):
        with pytest.raises(adapter.AdapterError, match="^REPORT_INVALID$"):
            adapter.parse_report(raw, "7", "7")


def test_tail_unknown_invoke_has_no_execution_id():
    c, t = tail_bound()
    c.error = e.ReadTimeoutError(endpoint_url=SECRET)
    r = t.invoke_once()
    assert r.code == "PARENT_OUTCOME_UNKNOWN" and r.log_state == "NOT_RECEIVED"
    assert r.log_encoded == r.log_decoded == b"" and not r.metadata
    assert r.summary()["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"


@pytest.mark.parametrize(
    "prefix",
    [
        b"\x80 REPORT RequestId: other-id\n",
        b'{"type":"platform\\u002ereport","record":\n',
        b'{"application": "cut\n',
    ],
)
def test_tail_malformed_candidates_never_selected_away(prefix):
    with pytest.raises(adapter.AdapterError, match="^REPORT_INVALID$"):
        adapter.parse_report(prefix + TEXT_REPORT, "7", "7")
