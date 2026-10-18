"""Fresh invented clients; accepted adapter, P0 and handler seams under guard."""

import ast
import base64
import io
from pathlib import Path

import botocore.exceptions as sdk
import pytest

from scripts import jev_rag_smoke_operator as op
from scripts import jev_rag_smoke_live_adapter as adapter
from tests import offline_guard
from tests import test_jev_rag_smoke_live_adapter as fake
from tests import test_jev_rag_smoke_operator as old
from tests import test_jev_rag_smoke_handler as inner


class Client(fake.Client):
    def __init__(self, bundle):
        super().__init__()
        self.bundle = bundle
        self.response["ExecutedVersion"] = "$LATEST"
        self.auto_body = True
        self.transform = lambda value: value

    def invoke(self, **params):
        directory = self.bundle["root"] / self.bundle["execution_id"]
        assert (directory / "claim.json").is_file()
        assert (directory / "invocation-attempt.json").is_file()
        response = super().invoke(**params)
        if self.auto_body:
            response["Payload"] = self.stream = io.BytesIO(
                op.canonical(self.transform(inner.invoke(self.bundle["inner"])))
            )
        return response


@pytest.fixture
def bundle(tmp_path):
    value = old.bundle.__wrapped__(tmp_path)
    plan = op.strict_json(value["args"][0])
    plan.update(schema=op.ADAPTER_PLAN_SCHEMA, mode=op.ADAPTER_MODE)
    old.rehash(value, 0, "operator", plan)
    value["client"] = Client(value)
    value["factories"] = 0

    def factory():
        directory = value["root"] / value["execution_id"]
        for name in ("claim.json", "invocation-attempt.json"):
            # A closed successful exclusive publication is readable now.
            assert op.strict_json((directory / name).read_bytes())
        value["factories"] += 1
        return value["client"]

    value["kwargs"]["client_factory"] = factory
    return value


def invoke(bundle, **kwargs):
    return op.consume_adapter(*bundle["args"], **bundle["kwargs"], **kwargs)


def directory(bundle):
    return bundle["root"] / bundle["execution_id"]


def index(bundle, result):
    return old.index(bundle, result)


def transport_result(bundle):
    return op.strict_json((directory(bundle) / "transport-result.json").read_bytes())


def assert_retained(bundle, result, *, code=None):
    if code:
        assert code in {v["code"] for v in result["failures"]}
    record = index(bundle, result)
    assert record["initial_reservations_usd"]["whole_run"] == "9.1"
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
    assert not record["assessment"]["evidence_complete"]
    assert not record["assessment"]["experiment_success"]
    before = {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    calls = bundle["client"].calls
    with pytest.raises(op.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
        invoke(bundle)
    assert before == {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    assert bundle["client"].calls == calls
    assert bundle["factories"] == 1
    return record


def test_clean_actual_handler_full_arn_and_incomplete_report(
    bundle, monkeypatch, capsys
):
    actual = op.inspect_handler
    observations = []

    def inspect(raw, *args):
        for name in ("response.bin", "response-metadata.json", "transport-result.json"):
            assert (directory(bundle) / name).is_file()
        assert raw == (directory(bundle) / "response.bin").read_bytes()
        observations.append(raw)
        return actual(raw, *args)

    monkeypatch.setattr(op, "inspect_handler", inspect)
    result = invoke(bundle)
    record = assert_retained(bundle, result)
    assert result["status"] == "COMPLETE"
    assert op.confirm(result, directory(bundle)) == record
    assert (
        observations
        and record["assessment"]["handler_structure"] == "STRUCTURAL_SUCCESS"
    )
    assert record["assessment"]["contract_exposure"] == "WITHIN_RECORDED_RESERVATIONS"
    assert record["assessment"]["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"
    assert record["assessment"]["sdk_request_id_is_execution_id"] is False
    assert not record["assessment"]["authenticated_observation"]
    request = op.strict_json((directory(bundle) / "request.json").read_bytes())
    assert request["request"]["FunctionName"] == (
        "arn:aws:lambda:us-east-1:123456789012:function:invented-isolated-smoke"
    )
    projection = transport_result(bundle)
    assert projection["parameter_checks"] == projection["approved_send_callbacks"] == 1
    assert projection["blocked_send_callbacks"] == 0
    assert (
        projection["metadata_provenance"] == "SELECTED_FIELDS_OF_INJECTED_SDK_RESPONSE"
    )
    assert bundle["client"].stream.closed and bundle["client"].closes == 1
    assert bundle["inner"].order == [
        "Converse",
        "GetObject",
        "GetObject",
        "InvokeModel",
        "Converse",
    ]
    console = capsys.readouterr()
    assert fake.SECRET not in console.out + console.err
    assert old.QUERY not in console.out and old.SENTINEL not in console.out
    assert "An invented answer." not in console.out and not console.err
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


@pytest.mark.parametrize("kind", ["hash", "mode", "schema", "factory", "target", "p0"])
def test_validation_before_claim_or_factory(bundle, kind):
    plan = op.strict_json(bundle["args"][0])
    code = "PLAN_INVALID"
    if kind == "hash":
        bundle["kwargs"]["hashes"]["operator"] = "0" * 64
        code = "INPUT_HASH_MISMATCH"
    elif kind == "factory":
        bundle["kwargs"]["client_factory"] = None
        code = "CLIENT_FACTORY_REQUIRED"
    else:
        if kind == "mode":
            plan["mode"] = "SIMULATED_OFFLINE"
        if kind == "schema":
            plan["schema"] = op.PLAN_SCHEMA
        if kind == "target":
            plan["target"]["account"] = "invalid"
            code = "TARGET_INVALID"
        if kind == "p0":
            plan["p0_plan_sha256"] = "0" * 64
            code = "PLAN_BINDING_MISMATCH"
        old.rehash(bundle, 0, "operator", plan)
    with pytest.raises(op.OperatorError, match="^" + code + "$"):
        invoke(bundle)
    assert not list(bundle["root"].iterdir()) and bundle["factories"] == 0


def test_adapter_constructed_after_closed_claim_and_marker(bundle, monkeypatch):
    original = adapter.ParentTransport
    constructed = []

    def constructor(*args, **kwargs):
        assert bundle["factories"] == 1
        assert op.strict_json((directory(bundle) / "claim.json").read_bytes())
        assert op.strict_json(
            (directory(bundle) / "invocation-attempt.json").read_bytes()
        )
        constructed.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(adapter, "ParentTransport", constructor)
    invoke(bundle)
    assert constructed == [True]


def test_claim_read_failure_is_sanitized_and_refuses_factory_and_resend(
    bundle, monkeypatch
):
    original = Path.stat

    def stat(path, *args, **kwargs):
        if path.name == "claim.json" and path.parent == directory(bundle):
            raise OSError(fake.SECRET)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    with pytest.raises(op.OperatorError, match="^CLAIM_READ_FAILED_RETAINED$"):
        invoke(bundle)
    assert (directory(bundle) / "claim.json").read_bytes()
    assert bundle["factories"] == bundle["client"].calls == 0
    with pytest.raises(op.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
        invoke(bundle)


@pytest.mark.parametrize("error", ["Handled", "Unhandled"])
def test_function_error_not_handler_or_success(bundle, monkeypatch, error):
    bundle["client"].response["FunctionError"] = error
    monkeypatch.setattr(
        op, "inspect_handler", lambda *args: pytest.fail("interpretation")
    )
    result = invoke(bundle)
    record = assert_retained(bundle, result)
    assert result["status"] == "COMPLETE"
    assert record["assessment"]["handler_structure"] == "FUNCTION_ERROR"


@pytest.mark.parametrize(
    "case,code",
    [
        ("service", "PARENT_SERVICE_ERROR"),
        ("connect", "PARENT_OUTCOME_UNKNOWN"),
        ("read", "PARENT_OUTCOME_UNKNOWN"),
        ("metadata", "PARENT_RESPONSE_INVALID"),
        ("retry", "PARENT_RETRY_INVALID"),
        ("missing-hooks", "PARENT_HOOKS_INVALID"),
        ("second-send", "PARENT_SEND_BLOCKED"),
        ("body-close", "PARENT_CLOSE_FAILED"),
        ("client-close", "CLIENT_CLOSE_FAILED"),
        ("overflow", "PARENT_BODY_TOO_LARGE"),
    ],
)
def test_nonclean_transport_never_inspected(bundle, monkeypatch, case, code):
    client = bundle["client"]
    client.auto_body = False
    if case == "service":
        client.error = sdk.ClientError(
            {
                "Error": {"Code": "Denied", "Message": fake.SECRET},
                "ResponseMetadata": client.response["ResponseMetadata"],
            },
            "Invoke",
        )
    if case == "connect":
        client.error = sdk.ConnectTimeoutError(endpoint_url=fake.SECRET)
    if case == "read":
        client.stream.error = sdk.ReadTimeoutError(endpoint_url=fake.SECRET)
    if case == "metadata":
        client.response["ResponseMetadata"]["RequestId"] = fake.SECRET + "!"
    if case == "retry":
        client.response["ResponseMetadata"]["RetryAttempts"] = 1
    if case == "missing-hooks":
        client.skip_hooks = True
    if case == "second-send":
        client.sends = 2
    if case == "body-close":
        client.stream.close_error = OSError(fake.SECRET)
    if case == "client-close":
        client.close_error = OSError(fake.SECRET)
    if case == "overflow":
        client.stream.parts = [b"a" * (adapter.RESPONSE_LIMIT + 9), b"never"]
    monkeypatch.setattr(
        op, "inspect_handler", lambda *args: pytest.fail("interpretation")
    )
    result = invoke(bundle)
    record = assert_retained(bundle, result, code=code)
    assert result["status"] == "INTERRUPTED"
    assert record["assessment"]["handler_structure"] == "UNESTABLISHED"
    if case == "second-send":
        assert client.delivered == 1
        assert transport_result(bundle)["blocked_send_callbacks"] == 1
    if case == "overflow":
        assert (
            directory(bundle) / "response.bin"
        ).read_bytes() == b"a" * adapter.RESPONSE_LIMIT
        assert client.stream.parts == [b"never"]
    assert not bundle["inner"].order
    assert fake.SECRET not in repr(result)


@pytest.mark.parametrize("kind", ["invoke", "read", "value", "before-hooks", "cleanup"])
def test_propagated_original_defect_retains_evidence_and_refuses_reentry(
    bundle, monkeypatch, kind
):
    client = bundle["client"]
    client.auto_body = False
    error = ValueError(fake.SECRET) if kind == "value" else RuntimeError(fake.SECRET)
    if kind in ("invoke", "value", "before-hooks"):
        client.error = error
        if kind == "before-hooks":
            client.skip_hooks = True
    else:
        client.stream.parts = [b"exact partial bytes"]
        client.stream.error = error
        if kind == "cleanup":
            client.stream.close_error = RuntimeError("secondary-private-defect")
            client.close_error = RuntimeError("another-private-defect")
    monkeypatch.setattr(
        op, "inspect_handler", lambda *args: pytest.fail("interpretation")
    )
    with pytest.raises(type(error)) as caught:
        invoke(bundle)
    assert caught.value is error
    assert any(
        frame.name
        == ("invoke" if kind in ("invoke", "value", "before-hooks") else "read")
        for frame in caught.traceback
    )
    summary = transport_result(bundle)
    assert (
        summary["code"] != "RETURNED"
        and "PARENT_DEFECT_PROPAGATED" in summary["failures"]
    )
    assert summary["body_eof"] is False and client.closes == 1
    if kind in ("read", "cleanup"):
        assert (
            directory(bundle) / "response.bin"
        ).read_bytes() == b"exact partial bytes"
        metadata = op.strict_json(
            (directory(bundle) / "response-metadata.json").read_bytes()
        )
        assert metadata["ResponseMetadata"]["RequestId"] == "invented-sdk-id"
        assert client.stream.closes == 1
    raw = (directory(bundle) / "index.json").read_bytes()
    record = op.strict_json(raw)
    assert record["status"] == "INTERRUPTED"
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
    before = {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    with pytest.raises(op.OperatorError, match="EXECUTION_ALREADY_CLAIMED"):
        invoke(bundle)
    assert before == {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    assert client.calls == bundle["factories"] == 1
    assert fake.SECRET not in repr(record)


def test_swallowed_blocked_hook_plus_foreign_defect_all_state_retained(
    bundle, monkeypatch
):
    client = bundle["client"]
    original = client.invoke
    client.sends = 2
    error = RuntimeError(fake.SECRET)

    def invoke_swallow(**params):
        try:
            original(**params)
        except adapter.AdapterError:
            pass
        raise error

    client.invoke = invoke_swallow
    monkeypatch.setattr(
        op, "inspect_handler", lambda *args: pytest.fail("interpretation")
    )
    with pytest.raises(RuntimeError) as caught:
        invoke(bundle)
    assert caught.value is error
    summary = transport_result(bundle)
    assert summary["hook_failed"] and summary["blocked_send_callbacks"] == 1
    assert summary["approved_send_callbacks"] == 1 and client.delivered == 1


def test_swallowed_gate_error_normal_return_cannot_be_clean(bundle, monkeypatch):
    client = bundle["client"]
    original = client.invoke
    client.sends = 2

    def invoke_swallow(**params):
        try:
            return original(**params)
        except adapter.AdapterError:
            return client.response

    client.invoke = invoke_swallow
    monkeypatch.setattr(
        op, "inspect_handler", lambda *args: pytest.fail("interpretation")
    )
    result = invoke(bundle)
    assert_retained(bundle, result, code="PARENT_HOOKS_INVALID")
    assert transport_result(bundle)["blocked_send_callbacks"] == 1


@pytest.mark.parametrize(
    "name",
    ["invocation-attempt.json", "response.bin", "transport-result.json", "index.json"],
)
@pytest.mark.parametrize("kind", ["collision", "partial-close"])
def test_publication_failures_refuse_confirmation_and_keep_claim(
    bundle, monkeypatch, name, kind
):
    original = op._write

    def write(path, raw):
        if path.name == name:
            if kind == "collision":
                with path.open("xb") as out:
                    out.write(b"existing collision")
                return original(path, raw)
            original(path, raw[:5])
            raise OSError(fake.SECRET)
        return original(path, raw)

    monkeypatch.setattr(op, "_write", write)
    result = invoke(bundle)
    assert result["status"] != "COMPLETE"
    assert result["code"] == "PUBLICATION_FAILED"
    with pytest.raises(op.OperatorError, match="PUBLICATION_UNCONFIRMED"):
        op.confirm(result, directory(bundle))
    retained = (directory(bundle) / name).read_bytes()
    assert (
        retained == b"existing collision" if kind == "collision" else len(retained) == 5
    )
    before = {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    with pytest.raises(op.OperatorError, match="EXECUTION_ALREADY_CLAIMED"):
        invoke(bundle)
    assert before == {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    if name == "invocation-attempt.json":
        assert bundle["factories"] == bundle["client"].calls == 0
    else:
        assert bundle["factories"] == bundle["client"].calls == 1
    if name != "index.json":
        record = index(bundle, result)
        assert name not in record["files"]
        assert record["initial_reservations_usd"]["whole_run"] == "9.1"
    else:
        assert result["index_sha256"] is None


def test_secondary_publication_defect_does_not_mask_primary(bundle, monkeypatch):
    client = bundle["client"]
    error = RuntimeError("primary-private-defect")
    client.error = error
    original = op._write

    def write(path, raw):
        if path.name in ("response.bin", "index.json"):
            raise RuntimeError("secondary-private-defect")
        return original(path, raw)

    monkeypatch.setattr(op, "_write", write)
    with pytest.raises(RuntimeError) as caught:
        invoke(bundle)
    assert caught.value is error
    assert client.closes == 1
    assert (directory(bundle) / "claim.json").is_file()
    assert (directory(bundle) / "invocation-attempt.json").is_file()


def test_no_default_live_factory_cli_or_environment_loader():
    tree = ast.parse(Path(op.__file__).read_text())
    consumer = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "consume_adapter"
    )
    defaults = dict(
        zip([a.arg for a in consumer.args.kwonlyargs], consumer.args.kw_defaults)
    )
    assert defaults["client_factory"] is None
    source = ast.get_source_segment(Path(op.__file__).read_text(), consumer)
    assert not any(
        x in source
        for x in ("boto3", "Session(", "getenv", "load_dotenv", "supplied_logs")
    )


@pytest.mark.parametrize(
    "mode",
    [
        "ordinary_stop",
        "retained_hold",
        "retry",
        "delivered",
        "unknown",
        "zero",
        "compact",
    ],
)
def test_actual_handler_accounting_mapping_remains_unchanged(bundle, monkeypatch, mode):
    old.op1_producer(bundle, mode, monkeypatch)
    result = invoke(bundle)
    record = assert_retained(bundle, result)
    assert result["status"] == "COMPLETE"
    raw = (directory(bundle) / "response.bin").read_bytes()
    actual = op.inspect_handler(
        raw,
        bundle["kwargs"]["hashes"]["policy"],
        op.strict_json(bundle["args"][1])["run_id"],
    )
    assert record["assessment"]["handler_structure"] == actual["status"]
    assert record["assessment"]["model_accounting"] == actual["model_accounting"]
    assert record["assessment"]["contract_exposure"] == actual["contract_exposure"]
    if mode in ("delivered", "unknown", "zero"):
        assert actual["contract_exposure"] == "VIOLATED_RECORD_UNRESERVED_EXPOSURE"
    if mode == "compact":
        assert actual["contract_exposure"] == "INCOMPLETE"


def test_handler_contradiction_rejects_after_exact_bytes_retained(bundle):
    def transform(value):
        value["accounting"]["retained_holds_usd"]["haiku"] = "1"
        return value

    bundle["client"].transform = transform
    result = invoke(bundle)
    record = assert_retained(bundle, result, code="HANDLER_RESULT_CONTRADICTORY")
    assert record["assessment"]["handler_structure"] == "UNESTABLISHED"
    assert record["assessment"]["contract_exposure"] == "UNESTABLISHED"
    raw = op.strict_json((directory(bundle) / "response.bin").read_bytes())
    assert raw["accounting"]["retained_holds_usd"]["haiku"] == "1"


def test_all_adapter_failures_preserved_not_just_primary(bundle, monkeypatch):
    client = bundle["client"]
    client.auto_body = False
    client.response["ResponseMetadata"]["RetryAttempts"] = 1
    client.stream.parts = [b"x" * (adapter.RESPONSE_LIMIT + 1)]
    client.stream.close_error = OSError(fake.SECRET)
    client.close_error = OSError(fake.SECRET)
    monkeypatch.setattr(
        op, "inspect_handler", lambda *args: pytest.fail("interpretation")
    )
    result = invoke(bundle)
    assert_retained(bundle, result)
    failures = transport_result(bundle)["failures"]
    assert failures == [
        "PARENT_RETRY_INVALID",
        "PARENT_BODY_TOO_LARGE",
        "PARENT_CLOSE_FAILED",
        "CLIENT_CLOSE_FAILED",
    ]
    assert [
        f["code"] for f in result["failures"] if f["stage"] == "adapter"
    ] == failures


@pytest.mark.parametrize("kind", ["factory-defect", "invalid-client"])
def test_pre_dispatch_defects_and_constructor_rejection_keep_marker(bundle, kind):
    error = RuntimeError(fake.SECRET)
    if kind == "factory-defect":

        def factory():
            bundle["factories"] += 1
            raise error

        bundle["kwargs"]["client_factory"] = factory
        with pytest.raises(RuntimeError) as caught:
            invoke(bundle)
        assert caught.value is error
        result = op.strict_json((directory(bundle) / "index.json").read_bytes())
        assert result["status"] == "INTERRUPTED" and result["dispatches"] == 0
    else:
        bundle["client"].meta.endpoint_url = "https://invented.invalid"
        returned = invoke(bundle)
        result = index(bundle, returned)
        assert returned["code"] == "CLIENT_CONFIG_INVALID"
        assert bundle["client"].closes == 1
    assert bundle["client"].calls == 0
    assert result["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
    assert (directory(bundle) / "invocation-attempt.json").is_file()


@pytest.mark.parametrize("when", ["before", "after"])
def test_clock_failure_retains_claim_and_no_fabricated_timing(bundle, when):
    stamps = iter(
        ["2026-10-09T00:00:00Z", "invalid"] if when == "after" else ["invalid"]
    )
    result = invoke(bundle, utc=lambda: next(stamps), monotonic=lambda: 1.0)
    record = index(bundle, result)
    assert result["code"] == "CLOCK_INVALID"
    assert bundle["client"].calls == (1 if when == "after" else 0)
    assert record["timings"]["received_utc"] is None
    assert record["timings"]["client_elapsed_seconds"] is None
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"


@pytest.mark.parametrize(
    "field",
    [
        "code",
        "hook_failed",
        "blocked",
        "parameters",
        "sends",
        "eof",
        "body-close",
        "client-close",
        "failures",
    ],
)
def test_full_state_required_even_if_foreign_layer_presents_clean_primary(
    bundle, monkeypatch, field
):
    original = adapter.ParentTransport.invoke_once

    def misleading(transport):
        result = original(transport)
        if field == "code":
            result.code = "NOT_RETURNED"
        if field == "hook_failed":
            transport.failed = True
        if field == "blocked":
            result.blocked_send_callbacks = 1
        if field == "parameters":
            result.parameter_checks = 0
        if field == "sends":
            result.approved_send_callbacks = 0
        if field == "eof":
            result.body_eof = False
        if field == "body-close":
            result.body_closed = False
        if field == "client-close":
            result.client_closed = False
        if field == "failures":
            result.failures.append("PARENT_CLOSE_FAILED")
        return result

    monkeypatch.setattr(adapter.ParentTransport, "invoke_once", misleading)
    monkeypatch.setattr(
        op, "inspect_handler", lambda *args: pytest.fail("interpretation")
    )
    result = invoke(bundle)
    assert result["status"] == "INTERRUPTED"
    assert_retained(bundle, result)


def caller_context(call, inside):
    """An unrelated handled caller exception must not affect this invocation."""
    if inside:
        try:
            raise KeyError("invented caller context")
        except KeyError:
            return call()
    return call()


@pytest.mark.parametrize("inside", [False, True], ids=["outside", "inside-except"])
def test_ac1_clean_return_is_context_independent(bundle, inside):
    result = caller_context(lambda: invoke(bundle), inside)
    assert result["status"] == "COMPLETE" and not result["failures"]
    record = assert_retained(bundle, result)
    assert op.confirm(result, directory(bundle)) == record
    assert record["assessment"]["handler_structure"] == "STRUCTURAL_SUCCESS"


@pytest.mark.parametrize("inside", [False, True], ids=["outside", "inside-except"])
@pytest.mark.parametrize("case", ["configuration", "sdk", "body", "local", "clock"])
def test_ac1_handled_failures_have_no_ambient_defect(bundle, monkeypatch, inside, case):
    client = bundle["client"]
    code = "CLIENT_CONFIG_INVALID"
    kwargs = {}
    if case == "configuration":
        client.meta.endpoint_url = "https://invented.invalid"
    if case == "sdk":
        client.error = sdk.ConnectTimeoutError(endpoint_url=fake.SECRET)
        code = "PARENT_OUTCOME_UNKNOWN"
    if case == "body":
        client.auto_body = False
        client.stream.error = sdk.ReadTimeoutError(endpoint_url=fake.SECRET)
        code = "PARENT_OUTCOME_UNKNOWN"
    if case == "local":

        def factory():
            bundle["factories"] += 1
            raise OSError(fake.SECRET)

        bundle["kwargs"]["client_factory"] = factory
        code = "LOCAL_OPERATION_FAILED"
    if case == "clock":
        kwargs = {"utc": lambda: "invalid", "monotonic": lambda: 0.0}
        code = "CLOCK_INVALID"
    result = caller_context(lambda: invoke(bundle, **kwargs), inside)
    assert result["status"] == "INTERRUPTED" and result["code"] == code
    assert "OPERATOR_DEFECT_PROPAGATED" not in [f["code"] for f in result["failures"]]
    record = index(bundle, result)
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
    assert not record["assessment"]["evidence_complete"]
    assert fake.SECRET not in repr(result) + repr(record)


@pytest.mark.parametrize("inside", [False, True], ids=["outside", "inside-except"])
@pytest.mark.parametrize("where", ["index", "client-close"])
def test_ac1_lone_finalization_defect_propagates_exactly(
    bundle, monkeypatch, inside, where
):
    error = RuntimeError(fake.SECRET)
    if where == "index":
        original = op.Publication.record

        def fail_index(pub, filename, value):
            if filename == "index.json":
                raise error
            return original(pub, filename, value)

        monkeypatch.setattr(op.Publication, "record", fail_index)
        frame = "fail_index"
    else:
        bundle["client"].meta.endpoint_url = "https://invented.invalid"
        bundle["client"].close_error = error
        frame = "close"
    with pytest.raises(RuntimeError) as caught:
        caller_context(lambda: invoke(bundle), inside)
    assert caught.value is error and any(f.name == frame for f in caught.traceback)
    assert (directory(bundle) / "claim.json").is_file()
    assert (directory(bundle) / "invocation-attempt.json").is_file()
    claim = op.strict_json((directory(bundle) / "claim.json").read_bytes())
    assert claim["preflight"]["initial_reservations_usd"]["whole_run"] == "9.1"
    before = {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    for filename, raw in before.items():
        if filename.endswith(".json"):
            assert fake.SECRET not in raw.decode()
            assert (
                "Traceback" not in raw.decode()
                and str(directory(bundle)) not in raw.decode()
            )
    with pytest.raises(op.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
        caller_context(lambda: invoke(bundle), inside)
    assert before == {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    assert bundle["factories"] == 1
    assert bundle["client"].calls == (1 if where == "index" else 0)


@pytest.mark.parametrize("inside", [False, True], ids=["outside", "inside-except"])
@pytest.mark.parametrize("primary", ["invoke", "read"])
@pytest.mark.parametrize("secondary", ["cleanup", "index", "both"])
def test_ac1_genuine_primary_survives_secondary_finalization(
    bundle,
    monkeypatch,
    inside,
    primary,
    secondary,
):
    client = bundle["client"]
    client.auto_body = False
    error = RuntimeError("invented primary private diagnostic")
    if primary == "invoke":
        client.error = error
    else:
        client.stream.parts = [b"exact retained partial response"]
        client.stream.error = error
    if secondary in ("cleanup", "both"):
        client.close_error = RuntimeError("invented secondary close diagnostic")
        if primary == "read":
            client.stream.close_error = RuntimeError(
                "invented secondary body diagnostic"
            )
    if secondary in ("index", "both"):
        original = op.Publication.record

        def fail_index(pub, filename, value):
            if filename == "index.json":
                raise RuntimeError("invented index diagnostic")
            return original(pub, filename, value)

        monkeypatch.setattr(op.Publication, "record", fail_index)
    with pytest.raises(RuntimeError) as caught:
        caller_context(lambda: invoke(bundle), inside)
    assert caught.value is error and any(f.name == primary for f in caught.traceback)
    summary = transport_result(bundle)
    assert (
        summary["code"] != "RETURNED"
        and "PARENT_DEFECT_PROPAGATED" in summary["failures"]
    )
    if primary == "read":
        assert (
            directory(bundle) / "response.bin"
        ).read_bytes() == b"exact retained partial response"
        assert summary["metadata_state"] == "OBJECT_PROJECTION"
    if secondary == "cleanup":
        record = op.strict_json((directory(bundle) / "index.json").read_bytes())
        assert record["status"] == "INTERRUPTED"
        assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
        assert "OPERATOR_DEFECT_PROPAGATED" in [f["code"] for f in record["failures"]]
    before = {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    claim = op.strict_json(before["claim.json"])
    assert claim["preflight"]["initial_reservations_usd"]["whole_run"] == "9.1"
    assert before["invocation-attempt.json"]
    for filename, raw in before.items():
        if filename.endswith(".json"):
            assert "invented primary private diagnostic" not in raw.decode()
            assert "invented secondary" not in raw.decode()
            assert "invented index diagnostic" not in raw.decode()
            assert "Traceback" not in raw.decode()
            assert str(directory(bundle)) not in raw.decode()
    with pytest.raises(op.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
        caller_context(lambda: invoke(bundle), inside)
    assert before == {p.name: p.read_bytes() for p in directory(bundle).iterdir()}
    assert client.calls == bundle["factories"] == 1


@pytest.mark.parametrize("inside", [False, True], ids=["outside", "inside-except"])
@pytest.mark.parametrize("handled", ["adapter", "os"])
def test_ac1_handled_error_bookkeeping_defect_counts_as_escaping(
    bundle, monkeypatch, inside, handled
):
    error = RuntimeError("invented bookkeeping diagnostic")
    if handled == "adapter":
        bundle["client"].meta.endpoint_url = "https://invented.invalid"
        # A secondary close failure must not replace the bookkeeping defect.
        bundle["client"].close_error = RuntimeError("invented secondary close")
    else:

        def factory():
            bundle["factories"] += 1
            raise OSError(fake.SECRET)

        bundle["kwargs"]["client_factory"] = factory
    original = op.Publication.failure
    failures = []

    def bookkeeping(pub, code, *args, **kwargs):
        failures.append(code)
        if len(failures) == 1:
            raise error
        return original(pub, code, *args, **kwargs)

    monkeypatch.setattr(op.Publication, "failure", bookkeeping)
    with pytest.raises(RuntimeError) as caught:
        caller_context(lambda: invoke(bundle), inside)
    assert caught.value is error and any(
        f.name == "bookkeeping" for f in caught.traceback
    )
    record = op.strict_json((directory(bundle) / "index.json").read_bytes())
    assert record["status"] == "INTERRUPTED" and record["dispatches"] == 0
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
    assert "OPERATOR_DEFECT_PROPAGATED" in [f["code"] for f in record["failures"]]
    assert bundle["client"].calls == 0
    assert "invented bookkeeping diagnostic" not in repr(record)


@pytest.fixture
def tail_bundle(bundle):
    plan = op.strict_json(bundle["args"][0])
    plan.update(
        schema=op.TAIL_PLAN_SCHEMA,
        mode=op.TAIL_MODE,
        log_type="Tail",
        parser_contract=adapter.REPORT_CONTRACT,
    )
    old.rehash(bundle, 0, "operator", plan)
    bundle["client"].log_type = "Tail"
    bundle["client"].response["LogResult"] = base64.b64encode(fake.TEXT_REPORT).decode()
    return bundle


@pytest.mark.parametrize("raw", [fake.TEXT_REPORT, fake.json_report()])
@pytest.mark.parametrize("inside", [False, True])
def test_tail_real_handler_join_is_not_overall_completion(
    tail_bundle, raw, inside, monkeypatch, capsys
):
    b = tail_bundle
    b["client"].response["LogResult"] = base64.b64encode(raw).decode()
    original = adapter.parse_report
    observed = []

    def parse(*args):
        for name in (
            "log-encoded.bin",
            "log-decoded.bin",
            "log-evidence.json",
            "response.bin",
            "response-metadata.json",
            "transport-result.json",
        ):
            assert (directory(b) / name).is_file()
        observed.append(args[0])
        return original(*args)

    monkeypatch.setattr(adapter, "parse_report", parse)
    result = caller_context(lambda: invoke(b), inside)
    record = assert_retained(b, result)
    assert result["status"] == "COMPLETE" and op.confirm(result, directory(b)) == record
    assert result["schema"] == op.TAIL_INDEX_SCHEMA and result["mode"] == op.TAIL_MODE
    join = op.strict_json((directory(b) / "report-association.json").read_bytes())
    assert join["execution_request_id"] == fake.EXECUTION_ID
    assert join["sdk_request_id"] == "invented-sdk-id"
    assert (
        join["executed_version"] == "$LATEST"
        and not join["immutable_code_identity_established"]
    )
    assert join["parent_transport_complete"] and observed == [raw]
    for field, file in (
        ("request_sha256", "request.json"),
        ("response_sha256", "response.bin"),
        ("response_metadata_sha256", "response-metadata.json"),
        ("log_encoded_sha256", "log-encoded.bin"),
        ("log_decoded_sha256", "log-decoded.bin"),
    ):
        assert join[field] == op.digest((directory(b) / file).read_bytes())
    assert record["assessment"]["report_evidence"] == "JOINED_SAME_INVOKE_RESPONSE"
    for flag in (
        "authenticated_observation",
        "task_cost_established",
        "evidence_complete",
        "experiment_success",
    ):
        assert record["assessment"][flag] is False
    assert (
        not record["owner_authorized"]
        and not record["invocation_authorized"]
        and not record["release_authorized"]
    )
    assert b["client"].calls == b["client"].delivered == b["factories"] == 1
    assert fake.SECRET not in capsys.readouterr().out


@pytest.mark.parametrize(
    "field,value",
    [
        ("log_type", "None"),
        ("parser_contract", "unreviewed"),
        ("schema", op.ADAPTER_PLAN_SCHEMA),
        ("mode", op.ADAPTER_MODE),
    ],
)
def test_tail_plan_hash_and_contract_before_claim(tail_bundle, field, value):
    b = tail_bundle
    plan = op.strict_json(b["args"][0])
    plan[field] = value
    old.rehash(b, 0, "operator", plan)
    with pytest.raises(op.OperatorError, match="^PLAN_INVALID$"):
        invoke(b)
    assert not list(b["root"].iterdir()) and b["factories"] == b["client"].calls == 0


def test_tail_unhashed_mutation_rejects_before_claim(tail_bundle):
    b = tail_bundle
    plan = op.strict_json(b["args"][0])
    plan["parser_contract"] = "changed"
    b["args"][0] = op.canonical(plan)
    with pytest.raises(op.OperatorError, match="^INPUT_HASH_MISMATCH$"):
        invoke(b)
    assert b["factories"] == 0 and not list(b["root"].iterdir())


@pytest.mark.parametrize(
    "name",
    [
        "log-encoded.bin",
        "log-decoded.bin",
        "log-evidence.json",
        "report-association.json",
        "index.json",
    ],
)
@pytest.mark.parametrize("fault", ["disk", "partial", "collision"])
def test_tail_publication_failure_never_confirms_or_resends(
    tail_bundle, monkeypatch, name, fault
):
    b = tail_bundle
    write = op._write

    def failing(path, raw):
        if path.name == name:
            if fault == "partial":
                with path.open("xb") as f:
                    f.write(raw[:3])
                raise OSError(fake.SECRET)
            if fault == "collision":
                with path.open("xb") as f:
                    f.write(b"prior")
                return write(path, raw)
            raise PermissionError(fake.SECRET)
        return write(path, raw)

    monkeypatch.setattr(op, "_write", failing)
    result = invoke(b)
    assert result["status"].startswith("INTERRUPTED")
    with pytest.raises(op.OperatorError, match="^PUBLICATION_UNCONFIRMED$"):
        op.confirm(result, directory(b))
    if name != "index.json":
        record = assert_retained(b, result, code="PUBLICATION_FAILED")
        assert name not in record["files"]
        failures = [item for item in result["failures"] if item["filename"] == name]
        assert failures and failures[0]["may_be_incomplete"]
        assert record["assessment"]["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"
    else:
        assert result["status"] == "INTERRUPTED_UNINDEXED"
        before = {p.name: p.read_bytes() for p in directory(b).iterdir()}
        with pytest.raises(op.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
            invoke(b)
        assert before == {p.name: p.read_bytes() for p in directory(b).iterdir()}
    assert b["client"].calls == b["factories"] == 1
    assert fake.SECRET not in repr(result)


@pytest.mark.parametrize(
    "kind", ["missing", "null", "bad", "oversized", "conflict", "no-report"]
)
def test_tail_invalid_logs_retained_without_complete_join(tail_bundle, kind):
    b = tail_bundle
    if kind == "missing":
        del b["client"].response["LogResult"]
    elif kind == "null":
        b["client"].response["LogResult"] = None
    elif kind == "bad":
        b["client"].response["LogResult"] = "!" + fake.SECRET
    elif kind == "oversized":
        b["client"].response["LogResult"] = "x" * 6000
    else:
        b["client"].response["LogResult"] = base64.b64encode(
            fake.TEXT_REPORT * 2 if kind == "conflict" else b"unknown log\n"
        ).decode()
    result = invoke(b)
    record = assert_retained(b, result)
    assert result["status"] == "INTERRUPTED"
    assert record["assessment"]["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"
    assert not (directory(b) / "report-association.json").exists()
    assert len((directory(b) / "log-encoded.bin").read_bytes()) <= 5464


@pytest.mark.parametrize("kind", ["read", "close", "function-error", "metadata-null"])
def test_tail_failure_association_preserves_outcome_boundary(tail_bundle, kind):
    b = tail_bundle
    c = b["client"]
    c.auto_body = False
    c.response["Payload"] = c.stream = fake.Stream([b"partial-body"])
    if kind == "read":
        c.stream.error = sdk.ReadTimeoutError(endpoint_url=fake.SECRET)
    if kind == "close":
        c.stream.close_error = OSError(fake.SECRET)
    if kind == "function-error":
        c.response["FunctionError"] = "Unhandled"
    if kind == "metadata-null":
        c.response["ResponseMetadata"] = None
    result = invoke(b)
    record = assert_retained(b, result)
    join = op.strict_json((directory(b) / "report-association.json").read_bytes())
    assert join["parent_transport_complete"] == (kind == "function-error")
    assert record["assessment"]["report_evidence"] == "JOINED_SAME_INVOKE_RESPONSE"
    if kind == "function-error":
        assert (
            result["status"] == "COMPLETE"
            and record["assessment"]["handler_structure"] == "FUNCTION_ERROR"
        )
    else:
        assert result["status"] == "INTERRUPTED"
    assert not record["assessment"]["experiment_success"]


@pytest.mark.parametrize("inside", [False, True])
def test_tail_programming_defect_preserves_raw_evidence_and_primary(
    tail_bundle, monkeypatch, inside
):
    b = tail_bundle
    c = b["client"]
    primary = RuntimeError(fake.SECRET)
    c.auto_body = False
    c.response["Payload"] = c.stream = fake.Stream(
        [b"exact-prefix"], error=primary, close_error=OSError(fake.SECRET)
    )
    c.close_error = RuntimeError("secondary")
    with pytest.raises(RuntimeError) as caught:
        caller_context(lambda: invoke(b), inside)
    assert caught.value is primary
    assert (directory(b) / "response.bin").read_bytes() == b"exact-prefix"
    assert (directory(b) / "log-decoded.bin").read_bytes() == fake.TEXT_REPORT
    record = op.strict_json((directory(b) / "index.json").read_bytes())
    assert (
        record["status"] == "INTERRUPTED"
        and record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
    )
    assert not record["assessment"]["evidence_complete"]
    with pytest.raises(op.OperatorError, match="^PUBLICATION_UNCONFIRMED$"):
        op.confirm(dict(status="INTERRUPTED"), directory(b))
    with pytest.raises(op.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
        invoke(b)
    assert c.calls == b["factories"] == c.closes == c.stream.closes == 1
    assert fake.SECRET not in repr(record)


def test_tail_blocked_second_send_retains_full_parent_hold(tail_bundle):
    b = tail_bundle
    b["client"].sends = 2
    result = invoke(b)
    record = assert_retained(b, result)
    assert result["status"] == "INTERRUPTED" and b["client"].delivered == 1
    assert record["initial_reservations_usd"]["whole_run"] == "9.1"
    assert record["assessment"]["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"


def test_tail_transport_metadata_retry_never_settles_parent(tail_bundle):
    b = tail_bundle
    b["client"].response["ResponseMetadata"]["RetryAttempts"] = 2
    result = invoke(b)
    record = assert_retained(b, result, code="PARENT_RETRY_INVALID")
    assert result["status"] == "INTERRUPTED" and b["client"].delivered == 1
    join = op.strict_json((directory(b) / "report-association.json").read_bytes())
    assert not join["parent_transport_complete"]
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"


def test_tail_unknown_invoke_cannot_infer_report_id(tail_bundle):
    b = tail_bundle
    b["client"].error = sdk.ReadTimeoutError(endpoint_url=fake.SECRET)
    result = invoke(b)
    record = assert_retained(b, result)
    assert (
        result["status"] == "INTERRUPTED"
        and record["assessment"]["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"
    )
    assert not (directory(b) / "report-association.json").exists()
    assert (directory(b) / "log-decoded.bin").read_bytes() == b""


def test_tail_report_publication_serializer_failure_keeps_raw(tail_bundle, monkeypatch):
    b = tail_bundle
    encode = op.encode

    def broken(value):
        if type(value) is dict and value.get("schema") == adapter.REPORT_CONTRACT:
            raise op.OperatorError("SERIALIZATION_FAILED")
        return encode(value)

    monkeypatch.setattr(op, "encode", broken)
    result = invoke(b)
    record = assert_retained(b, result, code="SERIALIZATION_FAILED")
    assert (
        result["status"] == "INTERRUPTED"
        and "report-association.json" not in record["files"]
    )
    assert (directory(b) / "log-decoded.bin").read_bytes() == fake.TEXT_REPORT
    assert record["assessment"]["report_evidence"] == "INCOMPLETE_NOT_CAPTURED"
