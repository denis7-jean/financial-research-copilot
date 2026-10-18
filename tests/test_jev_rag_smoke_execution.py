"""Invented signing/SDK/native fixtures through unchanged accepted seams."""

import ast
import io
from pathlib import Path

import pytest

from scripts import jev_rag_smoke_execution as execution
from scripts import jev_rag_smoke_client_factory as factory
from scripts import jev_rag_smoke_operator as op
from tests import offline_guard
from tests import test_jev_rag_smoke_adapter_consumer as consumer
from tests import test_jev_rag_smoke_client_factory as constructors
from tests import test_jev_rag_smoke_live_adapter as fake


@pytest.fixture
def run(tmp_path, monkeypatch):
    b = consumer.bundle.__wrapped__(tmp_path)
    consumer.tail_bundle.__wrapped__(b)
    sdk = constructors.RecordingSDK(b["client"])

    def before():
        for name in ("claim.json", "invocation-attempt.json"):
            assert op.strict_json((consumer.directory(b) / name).read_bytes())

    sdk.before = before
    monkeypatch.setattr(factory, "_load_sdk", lambda: sdk)
    settings = dict(constructors.SETTINGS)
    authority = {
        "schema": execution.AUTH_SCHEMA,
        "operational_authorized": True,
        "dedicated_process_confirmed": True,
        "execution_scope": execution.SCOPE,
        "target": op.strict_json(b["args"][0])["target"],
        "inputs_sha256": dict(b["kwargs"]["hashes"]),
        "client_settings": settings,
        "persistent_root": str(b["root"]),
    }
    b.update(sdk=sdk, authority=authority, stdout=io.StringIO(), stderr=io.StringIO())
    b["prepare"] = {
        **{k: b["kwargs"][k] for k in ("evidence", "hashes", "root")},
        "client_settings": settings,
        "access_key_id": constructors.KEY,
        "secret_access_key": constructors.SECRET,
        "session_token": constructors.TOKEN,
    }
    authorize(b)
    return b


def authorize(b):
    raw = op.canonical(b["authority"])
    b["prepare"].update(
        authorization_raw=raw, expected_authorization_sha256=op.digest(raw)
    )


def prepared(b):
    return execution.prepare(*b["args"], **b["prepare"])


def invoke(b, value=None):
    return (prepared(b) if value is None else value).run(
        stdout=b["stdout"], stderr=b["stderr"]
    )


def retained(b):
    directory = consumer.directory(b)
    claim = op.strict_json((directory / "claim.json").read_bytes())
    assert claim["preflight"]["initial_reservations_usd"]["whole_run"] == "9.1"
    assert (directory / "invocation-attempt.json").is_file()
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    calls = b["client"].calls
    with pytest.raises(op.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
        invoke(b)
    assert calls == b["client"].calls
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}


@pytest.mark.parametrize("inside", [False, True])
def test_clean_actual_seams_return_receipt_confirmation_and_no_authority(run, inside):
    b = run
    original = list(b["args"])
    value = prepared(b)
    assert b["sdk"].sessions == b["client"].calls == 0
    assert not list(b["root"].iterdir())
    assert repr(value) == "RagSmokeExecution(single_use=True)"
    result = consumer.caller_context(lambda: invoke(b, value), inside)
    assert result["status"] == "COMPLETE" and result["publication_confirmed"]
    assert result["console_exit_code"] == 0 and not result["release_authorized"]
    actual = result["consumer_return"]
    index = op.confirm(actual, consumer.directory(b))
    for key in ("evidence_complete", "experiment_success", "task_cost_established"):
        assert index["assessment"][key] is False
    assert not index["owner_authorized"] and not index["invocation_authorized"]
    raw = (consumer.directory(b) / execution.RECEIPT_FILE).read_bytes()
    assert len(raw) <= execution.MAX_RECEIPT_BYTES
    assert op.digest(raw) == result["returned_status_sha256"]
    receipt = op.strict_json(raw)
    assert receipt["consumer_return"] == actual
    assert (
        receipt["authorization_sha256"] == b["prepare"]["expected_authorization_sha256"]
    )
    assert op.strict_json(b["stdout"].getvalue().encode()) == actual
    assert b["sdk"].sessions == b["client"].calls == b["client"].delivered == 1
    request = op.strict_json((consumer.directory(b) / "request.json").read_bytes())
    assert request["request"]["LogType"] == "Tail"
    assert request["payload_sha256"] == b["kwargs"]["hashes"]["invocation"]
    assert b["args"] == original
    all_raw = b"".join(p.read_bytes() for p in consumer.directory(b).iterdir())
    for secret in (constructors.KEY, constructors.SECRET, constructors.TOKEN):
        assert secret.encode() not in all_raw and secret not in repr(value)
        assert secret not in b["stdout"].getvalue() + b["stderr"].getvalue()
    with pytest.raises(execution.ExecutionError, match="^EXECUTION_ALREADY_ATTEMPTED$"):
        invoke(b, value)
    retained(b)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("operational_authorized", False),
        ("operational_authorized", 1),
        ("dedicated_process_confirmed", False),
        ("execution_scope", "ALL_CALLS"),
        ("schema", "unapproved"),
        ("target", {}),
        ("inputs_sha256", {}),
        ("persistent_root", "private-unrelated-path"),
        ("client_settings", {}),
    ],
)
def test_bad_authority_no_claim_or_factory(run, field, bad):
    b = run
    b["authority"][field] = bad
    authorize(b)
    with pytest.raises(execution.ExecutionError, match="^AUTHORIZATION_INVALID$"):
        prepared(b)
    assert not list(b["root"].iterdir())
    assert b["sdk"].sessions == b["client"].calls == 0


@pytest.mark.parametrize(
    "kind", ["absent", "hash", "duplicate", "noncanonical", "extra", "large"]
)
def test_authority_encoding_and_separate_hash(run, kind):
    b = run
    if kind == "absent":
        b["prepare"]["authorization_raw"] = None
    elif kind == "hash":
        b["prepare"]["expected_authorization_sha256"] = "0" * 64
    else:
        raw = b["prepare"]["authorization_raw"]
        if kind == "duplicate":
            raw = b'{"schema":"first",' + raw[1:]
        elif kind == "noncanonical":
            raw += b" "
        elif kind == "extra":
            b["authority"]["extra"] = True
            raw = op.canonical(b["authority"])
        else:
            raw = b" " * (execution.MAX_AUTH_BYTES + 1)
        b["prepare"].update(
            authorization_raw=raw, expected_authorization_sha256=op.digest(raw)
        )
    with pytest.raises(
        execution.ExecutionError, match="^AUTHORIZATION_(BINDING_)?INVALID$"
    ):
        prepared(b)
    assert not list(b["root"].iterdir()) and b["sdk"].sessions == 0


@pytest.mark.parametrize(
    "key", ["operator", "plan", "invocation", "policy", "haiku", "titan"]
)
def test_wrong_trusted_input_hashes_before_claim(run, key):
    b = run
    b["prepare"]["hashes"] = {**b["prepare"]["hashes"], key: "0" * 64}
    with pytest.raises(op.OperatorError):
        prepared(b)
    assert not list(b["root"].iterdir()) and b["sdk"].sessions == 0


@pytest.mark.parametrize("kind", ["relative", "missing", "git"])
def test_invalid_roots(run, kind, tmp_path):
    b = run
    root = "relative" if kind == "relative" else tmp_path / kind
    if kind == "git":
        root.mkdir()
        (root / ".git").mkdir()
    b["prepare"]["root"] = root
    with pytest.raises(op.OperatorError, match="^CLAIM_ROOT_INVALID$"):
        prepared(b)
    assert b["sdk"].sessions == 0


def test_settings_join_and_invalid_signing_before_claim(run):
    b = run
    b["prepare"]["client_settings"] = {**constructors.SETTINGS, "read_seconds": 11}
    b["authority"]["client_settings"] = b["prepare"]["client_settings"]
    authorize(b)
    with pytest.raises(execution.ExecutionError, match="^CLIENT_SETTINGS_MISMATCH$"):
        prepared(b)
    b["prepare"]["client_settings"] = dict(constructors.SETTINGS)
    b["authority"]["client_settings"] = b["prepare"]["client_settings"]
    authorize(b)
    b["prepare"]["access_key_id"] = ""
    with pytest.raises(factory.FactoryError, match="^CLIENT_CONFIG_INVALID$"):
        prepared(b)
    assert not list(b["root"].iterdir()) and b["sdk"].sessions == 0


@pytest.mark.parametrize("kind", ["function", "parser", "partial"])
def test_received_failure_evidence_never_promoted(run, kind):
    b = run
    if kind == "function":
        b["client"].response["FunctionError"] = "Unhandled"
    elif kind == "parser":
        b["client"].response["LogResult"] = "%%%"
    else:
        b["client"].auto_body = False
        b["client"].response["Payload"] = b["client"].stream = fake.Stream(
            [b"partial-invented"], error=OSError("private invented transport message")
        )
    result = invoke(b)
    if kind == "function":
        # Complete publication of a FunctionError is not a successful experiment.
        assert result["publication_confirmed"]
        index = op.confirm(result["consumer_return"], consumer.directory(b))
        assert index["assessment"]["experiment_success"] is False
        metadata = op.strict_json(
            (consumer.directory(b) / "response-metadata.json").read_bytes()
        )
        assert metadata["FunctionError"] == "Unhandled"
    else:
        assert not result["publication_confirmed"] and result["status"] == "UNCONFIRMED"
    assert b["client"].calls == 1
    retained(b)


@pytest.mark.parametrize("inside", [False, True])
@pytest.mark.parametrize("stage", ["invoke", "read"])
@pytest.mark.parametrize("secondary", [False, True])
def test_programming_defect_original_partial_evidence_no_return_receipt(
    run, inside, stage, secondary, monkeypatch
):
    b = run
    primary = RuntimeError("invented private primary")
    if stage == "invoke":
        b["client"].error = primary
    else:
        b["client"].auto_body = False
        b["client"].response["Payload"] = b["client"].stream = fake.Stream(
            [b"received-exact-prefix"], error=primary
        )
    if secondary:
        b["client"].close_error = RuntimeError("invented private secondary")
        real_write = op._write

        def write(path, raw):
            if path.name == "index.json":
                raise RuntimeError("invented private index")
            real_write(path, raw)

        monkeypatch.setattr(op, "_write", write)
    value = prepared(b)
    with pytest.raises(RuntimeError) as caught:
        consumer.caller_context(lambda: invoke(b, value), inside)
    assert caught.value is primary
    names = []
    tb = caught.value.__traceback__
    while tb:
        names.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    assert ("invoke" if stage == "invoke" else "read") in names
    assert not (consumer.directory(b) / execution.RECEIPT_FILE).exists()
    if stage == "read":
        assert (
            consumer.directory(b) / "response.bin"
        ).read_bytes() == b"received-exact-prefix"
        assert b["client"].stream.closes == 1
    assert b["client"].closes == 1 and not b["stdout"].getvalue()
    retained(b)


@pytest.mark.parametrize("kind", ["collision", "write", "close", "partial"])
def test_receipt_failure_retains_actual_consumer_files_never_confirms(
    run, kind, monkeypatch
):
    b = run
    real_open = Path.open

    class Fault:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def write(self, raw):
            if kind == "write":
                raise OSError("private disk message")
            if kind == "partial":
                self.stream.write(raw[:7])
                return 7
            return self.stream.write(raw)

        def flush(self):
            self.stream.flush()

        def fileno(self):
            return self.stream.fileno()

        def __exit__(self, *args):
            self.stream.close()
            if kind == "close":
                raise OSError("private close message")

    def open_file(path, mode="r", *args, **kwargs):
        if path.name == execution.RECEIPT_FILE and mode == "xb":
            if kind == "collision":
                with real_open(path, "xb") as stream:
                    stream.write(b"retained-collision")
            return Fault(real_open(path, mode, *args, **kwargs))
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_file)
    with pytest.raises(
        execution.ExecutionError, match="^RETURNED_STATUS_PUBLICATION_FAILED$"
    ):
        invoke(b)
    assert not b["stdout"].getvalue()
    assert (
        op.strict_json((consumer.directory(b) / "index.json").read_bytes())["status"]
        == "COMPLETE"
    )
    retained(b)


@pytest.mark.parametrize("inside", [False, True])
def test_console_failure_explicit_no_confirmed_completion(run, inside):
    b = run

    class Broken:
        def write(self, _):
            raise OSError("invented private console")

    b["stdout"] = Broken()
    result = consumer.caller_context(lambda: invoke(b), inside)
    assert result["status"] == "UNCONFIRMED" and not result["publication_confirmed"]
    assert result["code"] == "CONSOLE_CONFIRMATION_UNAVAILABLE"
    assert result["console_exit_code"] == 3
    assert b["stderr"].getvalue() == "CONSOLE_CONFIRMATION_UNAVAILABLE\n"
    retained(b)


def test_pure_import_lazy_factory_and_immutable_supplied_maps(run, monkeypatch):
    assert offline_guard.is_installed()
    tree = ast.parse(Path(execution.__file__).read_bytes())
    assert all(not isinstance(node, ast.Import) for node in tree.body)
    assert all(
        node.module == "threading"
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    )
    b = run
    monkeypatch.setattr(
        factory, "_load_sdk", lambda: pytest.fail("SDK_DURING_PREPARATION")
    )
    value = prepared(b)
    assert not list(b["root"].iterdir())
    assert b["sdk"].sessions == 0
    # Caller mutation after preparation cannot replace already bound byte inputs.
    b["prepare"]["hashes"]["invocation"] = "0" * 64
    b["prepare"]["evidence"]["haiku"] = b"changed"
    assert value._hashes["invocation"] != "0" * 64
    assert value._evidence["haiku"] != b"changed"


def test_import_exec_never_reads_environment_or_loads_sdk(monkeypatch):
    import builtins
    import os

    raw = Path(execution.__file__).read_bytes()
    real_import = builtins.__import__

    def allowed(name, *args, **kwargs):
        assert name == "threading"
        return real_import(name, *args, **kwargs)

    def refuse(*args, **kwargs):
        pytest.fail("IMPORT_SIDE_EFFECT")

    with monkeypatch.context() as m:
        m.setattr(builtins, "open", refuse)
        m.setattr(os, "getenv", refuse)
        m.setattr(os, "environ", {})
        m.setattr(builtins, "__import__", allowed)
        namespace = {"__name__": "invented_pure_launcher"}
        exec(compile(raw, "invented_launcher", "exec"), namespace)
        assert namespace["SCOPE"] == execution.SCOPE


def test_confirm_actual_return_after_closed_receipt_and_exact_inputs_unchanged(
    run, monkeypatch
):
    b = run
    files = []
    for i, raw in enumerate(b["args"]):
        path = b["root"].parent / ("invented-input-" + str(i) + ".json")
        with path.open("xb") as stream:
            stream.write(raw)
        files.append((path, raw))
    received = []
    original_consume, original_confirm = op.consume_adapter, op.confirm

    def consume(*args, **kwargs):
        actual = original_consume(*args, **kwargs)
        received.append(actual)
        return actual

    def confirm(actual, directory):
        assert actual is received[0]
        assert (
            op.strict_json((directory / execution.RECEIPT_FILE).read_bytes())[
                "consumer_return"
            ]
            == actual
        )
        return original_confirm(actual, directory)

    monkeypatch.setattr(op, "consume_adapter", consume)
    monkeypatch.setattr(op, "confirm", confirm)
    result = invoke(b)
    assert result["publication_confirmed"] and result["consumer_return"] is received[0]
    assert all(path.read_bytes() == raw for path, raw in files)


@pytest.mark.parametrize("stage", ["serialization", "limit", "confirmation"])
def test_post_return_failure_never_emits_or_resends(run, monkeypatch, stage):
    b = run
    original_encode = op.encode

    def encode(value):
        if type(value) is dict and value.get("schema") == execution.RECEIPT_SCHEMA:
            if stage == "serialization":
                raise op.OperatorError("SERIALIZATION_FAILED")
            if stage == "limit":
                return b"x" * (execution.MAX_RECEIPT_BYTES + 1)
        return original_encode(value)

    def confirm(*args):
        raise op.OperatorError("PUBLICATION_UNCONFIRMED")

    monkeypatch.setattr(op, "encode", encode)
    if stage == "confirmation":
        monkeypatch.setattr(op, "confirm", confirm)
    codes = {
        "serialization": "RETURNED_STATUS_INVALID",
        "limit": "RETURNED_STATUS_TOO_LARGE",
        "confirmation": "PUBLICATION_UNCONFIRMED",
    }
    with pytest.raises(
        (execution.ExecutionError, op.OperatorError), match="^" + codes[stage] + "$"
    ):
        invoke(b)
    assert not b["stdout"].getvalue()
    retained(b)


@pytest.mark.parametrize("inside", [False, True])
def test_lone_unexpected_console_defect_propagates_after_publication(run, inside):
    b = run
    original = RuntimeError("invented console programming defect")

    class Broken:
        def write(self, _):
            raise original

    b["stdout"] = Broken()
    with pytest.raises(RuntimeError) as caught:
        consumer.caller_context(lambda: invoke(b), inside)
    assert caught.value is original
    assert (consumer.directory(b) / execution.RECEIPT_FILE).is_file()
    retained(b)


@pytest.mark.parametrize("inside", [False, True])
def test_lone_receipt_programming_defect_propagates_original(run, inside, monkeypatch):
    b = run
    original = RuntimeError("invented private receipt programming defect")
    real_write = op._write

    def write(path, raw):
        if path.name == execution.RECEIPT_FILE:
            raise original
        real_write(path, raw)

    monkeypatch.setattr(op, "_write", write)
    with pytest.raises(RuntimeError) as caught:
        consumer.caller_context(lambda: invoke(b), inside)
    assert caught.value is original
    assert not b["stdout"].getvalue()
    retained(b)


def test_non_tail_plan_cannot_prepare(run):
    b = run
    plan = op.strict_json(b["args"][0])
    plan.pop("log_type")
    plan.pop("parser_contract")
    plan.update(schema=op.ADAPTER_PLAN_SCHEMA, mode=op.ADAPTER_MODE)
    consumer.old.rehash(b, 0, "operator", plan)
    with pytest.raises(execution.ExecutionError, match="^TAIL_PLAN_REQUIRED$"):
        prepared(b)
    assert not list(b["root"].iterdir()) and b["sdk"].sessions == 0


@pytest.mark.parametrize("field", ["function_name", "qualifier", "account", "region"])
def test_authorization_target_including_qualifier_cannot_substitute(run, field):
    b = run
    b["authority"]["target"][field] = "substituted"
    authorize(b)
    with pytest.raises(execution.ExecutionError, match="^AUTHORIZATION_INVALID$"):
        prepared(b)
    assert not list(b["root"].iterdir()) and b["sdk"].sessions == 0


def test_preparation_does_not_publish_or_read_environment(run, monkeypatch):
    import os

    def refuse(*args, **kwargs):
        pytest.fail("PREPARATION_SIDE_EFFECT")

    monkeypatch.setattr(os, "getenv", refuse)
    monkeypatch.setattr(op, "_write", refuse)
    value = prepared(run)
    assert repr(value) == "RagSmokeExecution(single_use=True)"
    assert not list(run["root"].iterdir()) and run["sdk"].sessions == 0


@pytest.mark.parametrize(
    "field,value", [("max_attempts", True), ("read_seconds", 10.0)]
)
@pytest.mark.parametrize("also_settings", [False, True])
def test_authorization_settings_are_byte_exact_not_loose_numeric_equality(
    run, field, value, also_settings
):
    b = run
    b["authority"]["client_settings"] = {**constructors.SETTINGS, field: value}
    if also_settings:
        b["prepare"]["client_settings"] = b["authority"]["client_settings"]
    authorize(b)
    code = "CLIENT_SETTINGS_MISMATCH" if also_settings else "AUTHORIZATION_INVALID"
    with pytest.raises(execution.ExecutionError, match="^" + code + "$"):
        prepared(b)
    assert not list(b["root"].iterdir()) and b["sdk"].sessions == 0
