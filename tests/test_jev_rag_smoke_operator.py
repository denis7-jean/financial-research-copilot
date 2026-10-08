"""Fresh invented parent calls and real accepted P0/handler seams, offline only."""

import ast
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import jev_rag_smoke_operator as operator
from tests import offline_guard
from tests import test_jev_rag_smoke_handler as inner
from tests import test_jev_rag_smoke_preinvoke as pre
from tests import test_jev_rag_smoke_accounting as accounting_tests
from tests.test_jev_rag_smoke import Events, QUERY, SENTINEL


class Parent:
    simulation_only = True

    def __init__(self, bundle):
        self.bundle = bundle
        self.account = "123456789012"
        self.calls, self.sent, self.closed = [], 0, 0
        self.send_events, self.skip_hooks = 1, False
        self.error, self.transform = None, lambda value: value
        self.metadata = {"RequestId": "invented-parent-id", "RetryAttempts": 0}
        self.meta = SimpleNamespace(
            config=SimpleNamespace(
                region_name="us-east-1",
                connect_timeout=2,
                read_timeout=10,
                retries={"total_max_attempts": 1, "mode": "standard"},
            ),
            endpoint_url="https://lambda.us-east-1.amazonaws.com",
            events=Events(),
        )

    def invoke(self, **kwargs):
        directory = self.bundle["root"] / self.bundle["execution_id"]
        assert (directory / "claim.json").is_file()
        assert (directory / "invocation-attempt.json").is_file()
        self.calls.append(kwargs)
        assert kwargs == self.bundle["request"]
        if not self.skip_hooks:
            self.meta.events.emit(
                "before-parameter-build.*.*",
                model=SimpleNamespace(name="Invoke"),
                params=kwargs,
            )
            for _ in range(self.send_events):
                url = operator.SendGate(kwargs, self.meta.endpoint_url).url
                self.meta.events.emit(
                    "before-send.*.*",
                    request=SimpleNamespace(
                        method="POST",
                        url=url,
                        body=kwargs["Payload"],
                        headers={
                            "X-Amz-Invocation-Type": "RequestResponse",
                            "X-Amz-Log-Type": "None",
                        },
                    ),
                )
                self.sent += 1
        if self.error:
            raise self.error
        result = inner.invoke(self.bundle["inner"])
        raw = operator.canonical(self.transform(result))
        self.body = io.BytesIO(raw)
        return {
            "StatusCode": 200,
            "ExecutedVersion": "$LATEST",
            "Payload": self.body,
            "ResponseMetadata": self.metadata,
        }

    def close(self):
        self.closed += 1


@pytest.fixture
def bundle(tmp_path):
    original = pre.bundle.__wrapped__(tmp_path)
    child = tmp_path / "inner-root"
    child.mkdir()
    inner_run = inner.run.__wrapped__(child)
    inner_run.f.config = original["policy"]
    inner_run.f.evidence = {
        key: operator.canonical(value) for key, value in original["evidence"].items()
    }
    inner_run.f.hashes = {
        key: operator.digest(value) for key, value in inner_run.f.evidence.items()
    }
    inner_run.event["policy_utf8"] = operator.canonical(original["policy"]).decode()
    inner_run.event["evidence_utf8"] = {
        key: value.decode() for key, value in inner_run.f.evidence.items()
    }
    inner_run.event["bindings"] = {
        "policy_sha256": operator.digest(operator.canonical(original["policy"])),
        "price_evidence_sha256": inner_run.f.hashes,
    }
    invocation = operator.canonical(inner_run.event)
    original["plan"]["references"]["event_sha256"] = operator.digest(invocation)
    (p0_raw, policy_raw), options = pre.inputs(original)
    plan = {
        "schema": operator.PLAN_SCHEMA,
        "mode": "SIMULATED_OFFLINE",
        "p0_plan_sha256": operator.digest(p0_raw),
        "invocation_sha256": operator.digest(invocation),
        "target": {
            "account": "123456789012",
            "region": "us-east-1",
            "function_name": "invented-isolated-smoke",
            "qualifier": "$LATEST",
        },
    }
    log = {
        "schema": "jev-rag-smoke-supplied-logs-v1",
        "request_id": "invented-parent-id",
        "report": {
            "request_id": "invented-parent-id",
            "duration_ms": 1.5,
            "billed_duration_ms": 2,
            "memory_size_mib": 512,
            "max_memory_used_mib": 100,
        },
    }
    result = {
        "args": [operator.canonical(plan), p0_raw, invocation, policy_raw],
        "kwargs": {
            "evidence": options["evidence"],
            "hashes": {
                **options["expected_hashes"],
                "operator": operator.digest(operator.canonical(plan)),
                "invocation": operator.digest(invocation),
            },
            "root": original["root"],
        },
        "root": original["root"],
        "inner": inner_run,
        "log": log,
        "execution_id": pre.validate(original)["execution_id"],
        "request": {
            "FunctionName": plan["target"]["function_name"],
            "Qualifier": "$LATEST",
            "InvocationType": "RequestResponse",
            "LogType": "None",
            "Payload": invocation,
        },
        "factories": 0,
    }
    result["parent"] = Parent(result)

    def factory():
        directory = result["root"] / result["execution_id"]
        assert (directory / "claim.json").is_file() and (
            directory / "invocation-attempt.json"
        ).is_file()
        result["factories"] += 1
        return result["parent"]

    result["kwargs"]["client_factory"] = factory
    return result


def invoke(bundle, *, logs=True, **kwargs):
    raw = operator.canonical(bundle["log"]) if logs else None
    return operator.simulate(
        *bundle["args"],
        **bundle["kwargs"],
        supplied_logs=raw,
        logs_sha256=operator.digest(raw) if raw else None,
        **kwargs,
    )


def index(bundle, result):
    directory = bundle["root"] / result["execution_id"]
    raw = (directory / "index.json").read_bytes()
    assert operator.digest(raw) == result["index_sha256"]
    value = operator.strict_json(raw)
    for name, binding in value["files"].items():
        received = (directory / name).read_bytes()
        assert (
            operator.digest(received) == binding["sha256"]
            and len(received) == binding["size_bytes"]
        )
    return value


def rehash(bundle, position, field, value):
    raw = operator.canonical(value)
    bundle["args"][position] = raw
    bundle["kwargs"]["hashes"][field] = operator.digest(raw)


def test_real_p0_handler_chain_and_hash_confirmation(bundle, capsys):
    result = invoke(bundle)
    assert result["status"] == "COMPLETE" and result["dispatches"] == 1
    record = index(bundle, result)
    assert operator.confirm(result, bundle["root"] / result["execution_id"]) == record
    assert record["assessment"]["parent_transport"] == "RETURNED"
    assert record["assessment"]["handler_structure"] == "STRUCTURAL_SUCCESS"
    assert record["assessment"]["evidence_complete"]
    assert record["assessment"]["semantic_assessment"] == "UNASSESSED"
    assert (
        not record["assessment"]["experiment_success"]
        and not record["assessment"]["task_cost_established"]
    )
    assert record["initial_reservations_usd"]["whole_run"] == "9.1"
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"
    assert record["assessment"]["log_evidence"]["warm_reuse"] == "UNESTABLISHED"
    assert "init_duration_ms" not in record["assessment"]["log_evidence"]["report"]
    assert bundle["parent"].closed == bundle["parent"].sent == bundle["factories"] == 1
    assert bundle["parent"].body.closed
    assert bundle["inner"].order == [
        "Converse",
        "GetObject",
        "GetObject",
        "InvokeModel",
        "Converse",
    ]
    logs = capsys.readouterr()
    assert QUERY not in logs.out and SENTINEL not in logs.out
    assert "An invented answer." not in logs.out and logs.err == ""
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("hash", "INPUT_HASH_MISMATCH"),
        ("self_declared", "HASH_BINDINGS_REQUIRED"),
        ("extra", "PLAN_INVALID"),
        ("live", "PLAN_INVALID"),
        ("account", "TARGET_INVALID"),
        ("alias", "TARGET_INVALID"),
        ("p0", "PLAN_BINDING_MISMATCH"),
        ("event", "PLAN_BINDING_MISMATCH"),
        ("noncanonical", "PLAN_NOT_CANONICAL"),
        ("invocation", "INVOCATION_INVALID"),
    ],
)
def test_validation_before_claim_and_factory(bundle, mutation, code):
    plan = operator.strict_json(bundle["args"][0])
    if mutation == "hash":
        bundle["kwargs"]["hashes"]["operator"] = "0" * 64
    elif mutation == "self_declared":
        bundle["kwargs"]["hashes"] = {}
    elif mutation == "extra":
        plan["owner_authorized"] = True
    elif mutation == "live":
        plan["mode"] = "LIVE"
    elif mutation in ("account", "alias"):
        plan["target"]["account" if mutation == "account" else "qualifier"] = "invalid"
    elif mutation in ("p0", "event"):
        plan["p0_plan_sha256" if mutation == "p0" else "invocation_sha256"] = "0" * 64
    elif mutation == "invocation":
        event = operator.strict_json(bundle["args"][2])
        event["query"] = "different invented query"
        rehash(bundle, 2, "invocation", event)
        plan["invocation_sha256"] = bundle["kwargs"]["hashes"]["invocation"]
    if mutation not in ("hash", "self_declared"):
        rehash(bundle, 0, "operator", plan)
    if mutation == "noncanonical":
        bundle["args"][0] += b" "
        bundle["kwargs"]["hashes"]["operator"] = operator.digest(bundle["args"][0])
    with pytest.raises(operator.OperatorError, match="^" + code + "$"):
        invoke(bundle)
    assert not list(bundle["root"].iterdir()) and bundle["factories"] == 0


def test_p0_event_join_rejects_before_claim(bundle):
    p0_plan = operator.strict_json(bundle["args"][1])
    p0_plan["references"]["event_sha256"] = "0" * 64
    rehash(bundle, 1, "plan", p0_plan)
    plan = operator.strict_json(bundle["args"][0])
    plan["p0_plan_sha256"] = bundle["kwargs"]["hashes"]["plan"]
    rehash(bundle, 0, "operator", plan)
    with pytest.raises(operator.OperatorError, match="^EVENT_BINDING_MISMATCH$"):
        invoke(bundle)
    assert not list(bundle["root"].iterdir())


@pytest.mark.parametrize(
    "error", [TimeoutError(SENTINEL), OSError(SENTINEL), KeyboardInterrupt()]
)
def test_unknown_outcome_and_duplicate_never_resend_or_release(bundle, error):
    bundle["parent"].error = error
    result = invoke(bundle)
    record = index(bundle, result)
    assert (
        result["status"] == "INTERRUPTED" and result["code"] == "PARENT_OUTCOME_UNKNOWN"
    )
    assert (
        record["assessment"]["parent_transport"] == "UNKNOWN"
        and not record["assessment"]["evidence_complete"]
    )
    directory = bundle["root"] / bundle["execution_id"]
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(operator.OperatorError, match="^EXECUTION_ALREADY_CLAIMED$"):
        invoke(bundle)
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}
    assert len(bundle["parent"].calls) == bundle["factories"] == 1
    assert record["initial_reservations_usd"]["ROUTE"] == "3"
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"


@pytest.mark.parametrize(
    "setting,code",
    [
        ("retries", "CLIENT_CONFIG_INVALID"),
        ("account", "CLIENT_CONFIG_INVALID"),
        ("not_fake", "SIMULATED_CLIENT_REQUIRED"),
        ("second_send", "PARENT_SEND_BLOCKED"),
        ("skip", "PARENT_HOOKS_INVALID"),
    ],
)
def test_parent_settings_and_no_second_send(bundle, setting, code):
    parent = bundle["parent"]
    if setting == "retries":
        parent.meta.config.retries["total_max_attempts"] = 2
    elif setting == "account":
        parent.account = "999999999999"
    elif setting == "not_fake":
        parent.simulation_only = False
    elif setting == "second_send":
        parent.send_events = 2
    else:
        parent.skip_hooks = True
    result = invoke(bundle)
    assert result["code"] == code and result["status"] == "INTERRUPTED"
    assert parent.sent <= 1 and len(parent.calls) <= 1
    if setting == "second_send":
        assert not bundle["inner"].order


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("schema", "HANDLER_SCHEMA_UNSUPPORTED"),
        ("policy", "HANDLER_RESULT_INVALID"),
        ("run", "HANDLER_RESULT_INVALID"),
        ("flag", "HANDLER_RESULT_INVALID"),
        ("accounting", "HANDLER_RESULT_INVALID"),
        ("status", "HANDLER_RESULT_INVALID"),
        ("extra", "HANDLER_RESULT_INVALID"),
        ("success_hold", "HANDLER_RESULT_CONTRADICTORY"),
    ],
)
def test_malformed_results_preserved_before_rejection(bundle, mutation, code):
    def transform(value):
        if mutation == "schema":
            value["schema"] = "rag-smoke-handler-result-v1"
        elif mutation in ("policy", "run"):
            value["policy_sha256" if mutation == "policy" else "run_id"] = "different"
        elif mutation == "flag":
            value["release_authorized"] = True
        elif mutation == "accounting":
            value["accounting"]["known_charges_usd"]["haiku"] = "NaN"
        elif mutation == "status":
            value["status"] = "SUCCESS"
        elif mutation == "extra":
            value["private_unexpected_field"] = SENTINEL
        else:
            value["accounting"]["exposure_bound_established"] = False
        return value

    bundle["parent"].transform = transform
    result = invoke(bundle)
    record = index(bundle, result)
    assert result["code"] == code
    assert (
        "response.bin" in record["files"]
        and "response-metadata.json" in record["files"]
    )
    assert not record["assessment"]["evidence_complete"]


def test_handler_stop_is_confirmed_failure_evidence_not_success(bundle):
    bundle["inner"].f.native.index.search = lambda values, k: ([[1.0] * 5], [[0] * 5])
    result = invoke(bundle)
    record = index(bundle, result)
    assert result["status"] == "COMPLETE"
    assert record["assessment"]["handler_structure"] == "STOPPED"
    assert (
        record["assessment"]["evidence_complete"]
        and not record["assessment"]["experiment_success"]
    )
    assert bundle["inner"].order == [
        "Converse",
        "GetObject",
        "GetObject",
        "InvokeModel",
    ]


def test_function_error_has_complete_failure_evidence_without_fake_handler_result(
    bundle,
):
    original = bundle["parent"].invoke

    def failed(**kwargs):
        value = original(**kwargs)
        value["FunctionError"] = "Unhandled"
        return value

    bundle["parent"].invoke = failed
    result = invoke(bundle)
    value = index(bundle, result)["assessment"]
    assert value["handler_structure"] == "FUNCTION_ERROR" and value["evidence_complete"]
    assert value["model_accounting"] is None and not value["experiment_success"]


@pytest.mark.parametrize("case", ["missing", "mismatch", "no_report"])
def test_logs_absent_or_mismatched_cannot_establish_evidence(bundle, case):
    if case == "mismatch":
        bundle["log"]["report"]["request_id"] = "different-request"
    if case == "no_report":
        bundle["log"]["report"] = None
    result = invoke(bundle, logs=case != "missing")
    record = index(bundle, result)
    assert not record["assessment"]["evidence_complete"]
    assert record["assessment"]["handler_structure"] == "STRUCTURAL_SUCCESS"
    assert (
        result["code"]
        == {
            "missing": None,
            "mismatch": "LOG_REQUEST_MISMATCH",
            "no_report": "REPORT_INVALID",
        }[case]
    )
    assert result["dispatches"] == 1


@pytest.mark.parametrize(
    "which",
    [
        "operator-plan.json",
        "request.json",
        "invocation-attempt.json",
        "response.bin",
        "response-metadata.json",
        "index.json",
    ],
)
@pytest.mark.parametrize("kind", ["collision", "permission", "partial", "close"])
def test_exclusive_publication_failure_no_resend_and_disclosed_files(
    bundle, monkeypatch, which, kind
):
    real = operator._write

    def fail(path, raw):
        if path.name != which:
            return real(path, raw)
        if kind == "collision":
            with path.open("xb") as stream:
                stream.write(b"PREEXISTING INVENTED COLLISION")
            return real(path, raw)
        if kind == "permission":
            raise PermissionError(SENTINEL)
        with path.open("xb") as stream:
            stream.write(raw if kind == "close" else raw[:7])
        raise OSError(SENTINEL)

    monkeypatch.setattr(operator, "_write", fail)
    result = invoke(bundle)
    assert result["status"] == (
        "INTERRUPTED_UNINDEXED" if which == "index.json" else "INTERRUPTED"
    )
    assert result["code"] == "PUBLICATION_FAILED"
    assert len(bundle["parent"].calls) <= 1
    if which in ("operator-plan.json", "request.json", "invocation-attempt.json"):
        assert bundle["factories"] == 0
    if which != "index.json":
        record = index(bundle, result)
        assert which not in record["files"]
        assert any(
            item["filename"] == which and item["may_be_incomplete"]
            for item in record["failures"]
        )
    else:
        assert (
            result["index_sha256"] is None
            and result["index_failure_code"] == "PUBLICATION_FAILED"
        )
        with pytest.raises(operator.OperatorError, match="PUBLICATION_UNCONFIRMED"):
            operator.confirm(result, bundle["root"] / bundle["execution_id"])
    prior_calls = len(bundle["parent"].calls)
    with pytest.raises(operator.OperatorError, match="EXECUTION_ALREADY_CLAIMED"):
        invoke(bundle)
    assert len(bundle["parent"].calls) == prior_calls


@pytest.mark.parametrize(
    "phase,value",
    [
        ("before", float("nan")),
        ("before", 10**1000),
        ("after", float("inf")),
        ("after", 10**1000),
        ("after", -1.0),
        ("overflow", 1e308),
    ],
)
def test_clock_failures_preserve_received_response_and_null_invalid_duration(
    bundle, phase, value
):
    readings = iter(
        [value]
        if phase == "before"
        else [-1e308, value]
        if phase == "overflow"
        else [1.0, value]
    )
    result = invoke(bundle, monotonic=lambda: next(readings))
    record = index(bundle, result)
    assert (
        result["code"] == "CLOCK_INVALID"
        and record["timings"]["elapsed_seconds"] is None
    )
    if phase == "before":
        assert bundle["factories"] == 0 and not bundle["parent"].calls
    else:
        assert "response.bin" in record["files"] and len(bundle["parent"].calls) == 1


def test_utc_failure_after_receipt_never_fabricates_timestamp(bundle):
    stamps = iter(["2026-10-08T00:00:00Z", "999999999999999999-99-99T99:00:00Z"])
    result = invoke(bundle, utc=lambda: next(stamps))
    record = index(bundle, result)
    assert result["code"] == "CLOCK_INVALID"
    assert (
        record["timings"]["response_received"] is None
        and "response.bin" in record["files"]
    )


def test_metadata_serialization_failure_keeps_response_and_no_private_diagnostic(
    bundle, monkeypatch
):
    bundle["parent"].metadata["RequestId"] = object()
    result = invoke(bundle)
    record = index(bundle, result)
    assert result["code"] == "SERIALIZATION_FAILED"
    assert (
        "response.bin" in record["files"]
        and "response-metadata.json" not in record["files"]
    )
    output, error = io.StringIO(), io.StringIO()
    assert operator.emit_confirmation(result, output, error) == 2
    assert (
        QUERY not in output.getvalue()
        and SENTINEL not in output.getvalue()
        and str(bundle["root"]) not in output.getvalue()
    )


@pytest.mark.parametrize("kind", ["serializer", "short", "write", "flush"])
def test_console_failure_denies_confirmation_without_repeating_publication(
    bundle, monkeypatch, kind
):
    result = invoke(bundle)
    directory = bundle["root"] / bundle["execution_id"]
    before = {path.name: path.read_bytes() for path in directory.iterdir()}

    class Console(io.StringIO):
        def write(self, text):
            if kind == "short":
                return 1
            if kind == "write":
                raise OSError(SENTINEL)
            return super().write(text)

        def flush(self):
            if kind == "flush":
                raise OSError(SENTINEL)

    if kind == "serializer":
        monkeypatch.setattr(
            operator,
            "encode",
            lambda value: (_ for _ in ()).throw(
                operator.OperatorError("SERIALIZATION_FAILED")
            ),
        )
    error = io.StringIO()
    assert operator.emit_confirmation(result, Console(), error) == 3
    assert error.getvalue() == "CONSOLE_CONFIRMATION_UNAVAILABLE\n"
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}
    assert len(bundle["parent"].calls) == 1


def test_unrelated_programming_error_propagates_and_claim_blocks_next_attempt(bundle):
    bundle["parent"].error = AssertionError("invented programming error")
    with pytest.raises(AssertionError, match="invented programming error"):
        invoke(bundle)
    assert bundle["parent"].closed == 1
    with pytest.raises(operator.OperatorError, match="EXECUTION_ALREADY_CLAIMED"):
        invoke(bundle)


def test_unknown_extra_contract_mapping_preserves_accounting_and_known_charge(bundle):
    def transform(value):
        accounting = value["accounting"]
        accounting["extra_requests"] = [
            {"delivery": "YES", "approved": False, "charge_usd": None}
        ]
        accounting["extra_request_count"] = 1
        accounting["extra_requests_sha256"] = operator.digest(
            operator.canonical(accounting["extra_requests"])
        )
        accounting["reservation_coverage"] = "UNESTABLISHED"
        accounting["exposure_bound_established"] = accounting["ceiling_established"] = (
            False
        )
        value["status"], value["code"], value["result"] = (
            "UNCERTAIN",
            "EXTRA_REQUEST_OBSERVED",
            None,
        )
        return value

    bundle["parent"].transform = transform
    result = invoke(bundle)
    record = index(bundle, result)
    assert (
        record["assessment"]["contract_exposure"]
        == "VIOLATED_RECORD_UNRESERVED_EXPOSURE"
    )
    assert record["assessment"]["model_accounting"]["known_charges_usd"]["haiku"] != "0"
    assert not record["assessment"]["experiment_success"]


def test_blocked_extra_is_not_invented_as_delivered_charge(bundle):
    bundle["inner"].f.model.send_events = 2
    result = invoke(bundle)
    record = index(bundle, result)
    accounting = record["assessment"]["model_accounting"]
    assert accounting["extra_request_count"] == 1
    assert accounting["extra_requests"][0]["delivery"] == "NO"
    assert accounting["extra_requests"][0]["charge_usd"] is None
    assert (
        record["assessment"]["contract_exposure"]
        != "VIOLATED_RECORD_UNRESERVED_EXPOSURE"
    )
    assert not bundle["inner"].f.s3.calls


def test_static_no_sdk_network_subprocess_native_or_live_entry():
    tree = ast.parse(Path(operator.__file__).read_text(encoding="utf8"))
    imports = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    imports |= {
        name.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for name in node.names
    }
    assert not imports & {
        "boto3",
        "botocore",
        "subprocess",
        "socket",
        "httpx",
        "requests",
        "numpy",
        "faiss",
        "dotenv",
    }
    assert not hasattr(operator, "main")
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


@pytest.mark.parametrize("field", ["body", "url", "method", "headers", "parameters"])
def test_prepared_request_mutations_block_before_delivery(bundle, field):
    real = bundle["parent"].meta.events.emit

    def emit(event, **kwargs):
        if field == "parameters" and event == "before-parameter-build.*.*":
            kwargs["params"] = {**kwargs["params"], "InvocationType": "Event"}
        elif event == "before-send.*.*":
            setattr(
                kwargs["request"],
                field,
                {}
                if field == "headers"
                else b"different"
                if field == "body"
                else "different",
            )
        return real(event, **kwargs)

    bundle["parent"].meta.events.emit = emit
    result = invoke(bundle)
    assert result["code"] == (
        "PARENT_REQUEST_INVALID" if field == "parameters" else "PARENT_SEND_BLOCKED"
    )
    assert bundle["parent"].sent == 0 and not bundle["inner"].order


@pytest.mark.parametrize(
    "mutation", ["empty_answer", "unicode", "confidence", "bad_score", "unknown_field"]
)
def test_success_result_structure_rejects_malformed_fields(bundle, mutation):
    def transform(value):
        result = value["result"]
        if mutation == "empty_answer":
            result["answer"] = ""
        elif mutation == "unicode":
            result["answer"] = "\ud800"
        elif mutation == "confidence":
            result["router_confidence"] = True
        elif mutation == "bad_score":
            result["retrieval"][0]["score"] = None
        else:
            result["unknown"] = SENTINEL
        return value

    bundle["parent"].transform = transform
    result = invoke(bundle)
    assert result["code"] == "HANDLER_RESULT_INVALID"
    assert "response.bin" in index(bundle, result)["files"]


@pytest.mark.parametrize(
    "kind",
    [
        "read_failure",
        "oversize",
        "close_failure",
        "malformed",
        "retry",
        "request_id",
        "version",
    ],
)
def test_response_failures_preserve_bytes_and_do_not_repeat(bundle, kind):
    original = bundle["parent"].invoke
    body_closed = []

    class Body(io.BytesIO):
        def read(self, size):
            if kind == "read_failure":
                if self.tell() > 0:
                    raise OSError(SENTINEL)
                return super().read(3)
            return super().read(size)

        def close(self):
            body_closed.append(True)
            super().close()
            if kind == "close_failure":
                raise OSError(SENTINEL)

    def response(**kwargs):
        value = original(**kwargs)
        raw = value["Payload"].getvalue()
        value["Payload"].close()
        value["Payload"] = Body(
            b"x" * (operator.RESPONSE_LIMIT + 1)
            if kind == "oversize"
            else b'{"bad":true}'
            if kind == "malformed"
            else raw
        )
        if kind == "retry":
            value["ResponseMetadata"]["RetryAttempts"] = 1
        if kind == "request_id":
            value["ResponseMetadata"]["RequestId"] = None
        if kind == "version":
            value["ExecutedVersion"] = None
        return value

    bundle["parent"].invoke = response
    result = invoke(bundle)
    record = index(bundle, result)
    assert (
        result["status"] == "INTERRUPTED"
        and not record["assessment"]["evidence_complete"]
    )
    assert len(bundle["parent"].calls) == 1 and body_closed == [True]
    assert record["files"]["response.bin"]["size_bytes"] <= operator.RESPONSE_LIMIT
    if kind == "oversize":
        assert record["files"]["response.bin"]["size_bytes"] == operator.RESPONSE_LIMIT
    if kind == "read_failure":
        assert record["files"]["response.bin"]["size_bytes"] == 3
        assert (
            bundle["root"] / result["execution_id"] / "response.bin"
        ).read_bytes() == b'{"a'
    assert record["reservation_release"] == "NONE_PARENT_HOLDS_RETAINED"


def test_record_and_index_failures_both_disclosed_and_no_overwrite(bundle, monkeypatch):
    real = operator._write

    def fail(path, raw):
        if path.name in ("response-metadata.json", "index.json"):
            with path.open("xb") as stream:
                stream.write(raw[:3])
            raise OSError(SENTINEL)
        return real(path, raw)

    monkeypatch.setattr(operator, "_write", fail)
    result = invoke(bundle)
    assert result["status"] == "INTERRUPTED_UNINDEXED" and result["failure_count"] == 2
    assert result["code"] == result["index_failure_code"] == "PUBLICATION_FAILED"
    assert [
        (failure["filename"], failure["may_be_incomplete"])
        for failure in result["failures"]
    ] == [("response-metadata.json", True), ("index.json", True)]
    directory = bundle["root"] / bundle["execution_id"]
    assert (directory / "response.bin").is_file()
    assert (
        len((directory / "response-metadata.json").read_bytes())
        == len((directory / "index.json").read_bytes())
        == 3
    )


def test_clocks_accept_increasing_utc_with_different_fractional_precision(bundle):
    stamps = iter(["2026-10-08T00:00:00Z", "2026-10-08T00:00:00.000001Z"])
    ticks = iter([1.0, 2.0])
    result = invoke(bundle, utc=lambda: next(stamps), monotonic=lambda: next(ticks))
    assert (
        result["status"] == "COMPLETE"
        and index(bundle, result)["timings"]["elapsed_seconds"] == 1
    )


def test_real_accounting_counterexample_hold_plus_known_unreserved_charge(bundle):
    real_factory = bundle["inner"].factory

    def factory(policy):
        clients = real_factory(policy)
        accounting_tests.observe_extra(
            bundle["inner"].f,
            policy,
            usage={"inputTokens": 10000, "outputTokens": 0},
            lose_original_response=True,
        )
        return clients

    bundle["inner"].factory = factory
    result = invoke(bundle)
    record = index(bundle, result)
    accounting = record["assessment"]["model_accounting"]
    assert accounting["retained_holds_usd"]["haiku"] == "3"
    assert accounting["known_charges_usd"]["haiku"] == "1"
    raw = (bundle["root"] / result["execution_id"] / "response.bin").read_bytes()
    received = operator.strict_json(raw)
    assert received["exposure_usd"]["haiku"] == "4"
    assert accounting["reservation_coverage"] == "VIOLATED"
    assert (
        record["assessment"]["contract_exposure"]
        == "VIOLATED_RECORD_UNRESERVED_EXPOSURE"
    )
    assert not accounting["extra_requests"][0]["approved"]
    assert len(bundle["inner"].f.model.calls) == 1 and not bundle["inner"].f.s3.calls


def test_deterministic_invented_receipts_with_explicit_clocks(tmp_path):
    results = []
    for name in ("first", "second"):
        child = tmp_path / name
        child.mkdir()
        run = bundle.__wrapped__(child)
        ticks = iter([10.0, 11.0])
        result = invoke(
            run, utc=lambda: "2026-10-08T00:00:00Z", monotonic=lambda: next(ticks)
        )
        results.append(result)
        assert result["status"] == "COMPLETE"
    assert results[0] == results[1]


def test_injected_operational_diagnostic_never_exposes_provider_text(bundle):
    bundle["parent"].error = operator.OperatorError(SENTINEL + str(bundle["root"]))
    result = invoke(bundle)
    assert result["code"] == "OPERATOR_FAILED"
    output, error = io.StringIO(), io.StringIO()
    assert operator.emit_confirmation(result, output, error) == 2
    assert SENTINEL not in output.getvalue() and QUERY not in output.getvalue()
    assert str(bundle["root"]) not in output.getvalue()


def test_complete_return_does_not_confirm_altered_index_or_published_file(bundle):
    result = invoke(bundle)
    directory = bundle["root"] / result["execution_id"]
    # Only invented test-owned files are changed, never task/protected evidence.
    (directory / "response.bin").write_bytes(b"invented alteration")
    with pytest.raises(operator.OperatorError, match="PUBLICATION_UNCONFIRMED"):
        operator.confirm(result, directory)


def test_changed_plan_hash_cannot_repeat_same_run_or_release_old_reservations(bundle):
    bundle["parent"].error = TimeoutError(SENTINEL)
    result = invoke(bundle)
    directory = bundle["root"] / result["execution_id"]
    old_claim = (directory / "claim.json").read_bytes()
    changed = operator.strict_json(bundle["args"][1])
    changed["plan_id"] = "invented-revised-plan"
    rehash(bundle, 1, "plan", changed)
    plan = operator.strict_json(bundle["args"][0])
    plan["p0_plan_sha256"] = bundle["kwargs"]["hashes"]["plan"]
    rehash(bundle, 0, "operator", plan)
    with pytest.raises(operator.OperatorError, match="EXECUTION_ALREADY_CLAIMED"):
        invoke(bundle)
    assert (directory / "claim.json").read_bytes() == old_claim
    assert len(bundle["parent"].calls) == 1


def test_serializer_failure_at_final_index_denies_completion_without_retry(
    bundle, monkeypatch
):
    real = operator.canonical

    def encode(value):
        if type(value) is dict and value.get("schema") == operator.INDEX_SCHEMA:
            raise ValueError(SENTINEL)
        return real(value)

    monkeypatch.setattr(operator, "canonical", encode)
    result = invoke(bundle)
    assert (
        result["status"] == "INTERRUPTED_UNINDEXED" and result["index_sha256"] is None
    )
    assert result["index_failure_code"] == "SERIALIZATION_FAILED"
    assert result["failures"] == [
        {
            "code": "SERIALIZATION_FAILED",
            "stage": "serialization",
            "filename": "index.json",
            "may_be_incomplete": False,
        }
    ]
    assert len(bundle["parent"].calls) == 1
    directory = bundle["root"] / result["execution_id"]
    assert (directory / "response.bin").is_file() and not (
        directory / "index.json"
    ).exists()


def test_claim_metadata_failure_retains_claim_and_never_constructs_client(
    bundle, monkeypatch
):
    real = Path.stat

    def stat(path, *args, **kwargs):
        if path.name == "claim.json":
            raise PermissionError(SENTINEL)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    with pytest.raises(operator.OperatorError, match="^CLAIM_READ_FAILED_RETAINED$"):
        invoke(bundle)
    assert bundle["factories"] == 0 and not bundle["parent"].calls
    raw = (bundle["root"] / bundle["execution_id"] / "claim.json").read_bytes()
    assert (
        operator.strict_json(raw)["state"] == "FULL_RESERVATIONS_RETAINED_NO_DISPATCH"
    )
    with pytest.raises(operator.OperatorError, match="EXECUTION_ALREADY_CLAIMED"):
        invoke(bundle)
