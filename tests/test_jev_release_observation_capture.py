"""Synthetic contract checks for the bounded release observation capture helper.

Invented accounts, functions and AWS responses, injected fake clients and an
injected clock only. No test constructs a real SDK client, reads credentials
or reaches the network; the repository offline guard stays installed.
"""

import ast
import base64
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re

import pytest

from scripts import jev_release_observation_capture as cap
from scripts import jev_release_preflight as rp
from tests import offline_guard

ACCOUNT = "123456789012"
OTHER_ACCOUNT = "210987654321"
REGION = "us-east-1"
PROD = "invented-copilot"
ALIAS = "live"
ZIP_BYTES = 4096
ARTIFACT_HEX = hashlib.sha256(b"invented candidate zip").hexdigest()
ARTIFACT_CODE = rp.hex_to_code_sha256(ARTIFACT_HEX)
_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
NONCANONICAL_CODE = (
    ARTIFACT_CODE[:42]
    + _ALPHABET[_ALPHABET.index(ARTIFACT_CODE[42]) ^ 1]
    + ARTIFACT_CODE[43:]
)
OLD_CODE = base64.b64encode(hashlib.sha256(b"invented old code").digest()).decode()
SECRET = "invented-secret-env-value-never-printed"
ROLE_ARN = "arn:aws:iam::123456789012:role/invented-private-role"
CALLER_ARN = "arn:aws:sts::123456789012:assumed-role/invented-reader/session"
MESSAGE = "invented provider message never printed"
T0 = datetime.datetime(2026, 10, 7, 12, 0, tzinfo=datetime.timezone.utc)
AS_OF = "2026-10-07T12:10:00+00:00"

BASELINE = {
    "role": "production_baseline",
    "operation": "GetFunctionConfiguration",
    "request": {"FunctionName": PROD},
}
CANDIDATE = {
    "role": "candidate",
    "operation": "GetFunctionConfiguration",
    "request": {"FunctionName": PROD, "Qualifier": "8"},
}
ROLLBACK = {
    "role": "rollback_target",
    "operation": "GetFunctionConfiguration",
    "request": {"FunctionName": PROD, "Qualifier": "7"},
}
ALIAS_READ = {
    "role": "alias",
    "operation": "GetAlias",
    "request": {"FunctionName": PROD, "Name": ALIAS},
}
METHODS = {
    "GetFunctionConfiguration": "get_function_configuration",
    "GetAlias": "get_alias",
}


@pytest.fixture(autouse=True)
def no_outbound_attempts():
    assert offline_guard.is_installed()
    before = len(offline_guard.blocked_requests)
    yield
    assert len(offline_guard.blocked_requests) == before


def metadata(retries=0, request_id="invented-request-0001"):
    return {
        "RequestId": request_id,
        "HTTPStatusCode": 200,
        "HTTPHeaders": {"x-amzn-requestid": request_id},
        "RetryAttempts": retries,
    }


def caller(account=ACCOUNT):
    return {
        "UserId": "AROAINVENTED:session",
        "Account": account,
        "Arn": CALLER_ARN,
        "ResponseMetadata": metadata(request_id="invented-sts-0001"),
    }


def fn_config(qualifier=None, code=ARTIFACT_CODE, revision="rev-latest", env=None):
    version = qualifier or "$LATEST"
    arn = f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{PROD}"
    if qualifier is not None:
        arn += f":{qualifier}"
    return {
        "FunctionName": PROD,
        "FunctionArn": arn,
        "Runtime": "python3.11",
        "Role": ROLE_ARN,
        "Handler": "lambda_handler.handler",
        "CodeSize": ZIP_BYTES,
        "Description": "",
        "Timeout": 30,
        "MemorySize": 512,
        "LastModified": "2026-10-06T10:00:00.000+0000",
        "CodeSha256": code,
        "Version": version,
        "Environment": {"Variables": {} if env is None else env},
        "TracingConfig": {"Mode": "PassThrough"},
        "RevisionId": revision,
        "State": "Active",
        "LastUpdateStatus": "Successful",
        "PackageType": "Zip",
        "Architectures": ["x86_64"],
        "EphemeralStorage": {"Size": 512},
        "ResponseMetadata": metadata(request_id=f"invented-fn-{version}"),
    }


def alias_config(target="8", revision="alias-rev-1"):
    return {
        "AliasArn": f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{PROD}:{ALIAS}",
        "Name": ALIAS,
        "FunctionVersion": target,
        "Description": "",
        "RevisionId": revision,
        "ResponseMetadata": metadata(request_id="invented-alias-0001"),
    }


def standard_responses():
    return {
        "production_baseline": fn_config(
            code=OLD_CODE, env={"EVALUATE_ENDPOINT_TOKEN": SECRET}
        ),
        "candidate": fn_config("8", revision="rev-8"),
        "rollback_target": fn_config("7", code=OLD_CODE, revision="rev-7"),
        "alias": alias_config(),
    }


def capture_plan(observations=(BASELINE, CANDIDATE, ROLLBACK, ALIAS_READ), **overrides):
    plan = {
        "schema": cap.PLAN_SCHEMA,
        "capture_id": "invented-capture-01",
        "account_id": ACCOUNT,
        "region": REGION,
        "max_calls": 1 + len(observations),
        "timeouts": {"connect_seconds": 5, "read_seconds": 10},
        "observations": copy.deepcopy(list(observations)),
    }
    plan.update(overrides)
    return plan


def encode(plan):
    return json.dumps(plan).encode("utf-8")


class InventedClientError(Exception):
    """Shaped like botocore's ClientError; the message must never be kept."""

    def __init__(self, code="AccessDeniedException", retries=0):
        super().__init__(MESSAGE)
        self.response = {
            "Error": {"Code": code, "Message": MESSAGE},
            "ResponseMetadata": metadata(retries, "invented-failed-0001"),
        }


class FakeAWS:
    """Injected client factory: scripted results in call order, every call logged."""

    def __init__(self, results):
        self.results = list(results)
        self.calls, self.factory_calls = [], []

    def __call__(self, service, region, settings):
        self.factory_calls.append((service, region, copy.deepcopy(settings)))
        return FakeClient(self, service)


class FakeClient:
    def __init__(self, aws, service):
        self.aws, self.service = aws, service

    def __getattr__(self, method):
        def call(**kwargs):
            self.aws.calls.append((self.service, method, kwargs))
            result = self.aws.results.pop(0)
            if isinstance(result, Exception):
                raise result
            return copy.deepcopy(result)

        return call


class Clock:
    def __init__(self, values=None, step=1.5):
        self.values = list(values) if values is not None else None
        self.now, self.step = T0, step

    def __call__(self):
        if self.values is not None:
            return self.values.pop(0)
        value = self.now
        self.now += datetime.timedelta(seconds=self.step)
        return value


def scripted(plan, responses):
    return [caller()] + [responses[entry["role"]] for entry in plan["observations"]]


def expected_calls(plan):
    return [("sts", "get_caller_identity", {})] + [
        ("lambda", METHODS[entry["operation"]], entry["request"])
        for entry in plan["observations"]
    ]


def run(tmp_path, plan, results, clock=None, name="capture"):
    aws = FakeAWS(results)
    out = tmp_path / name
    status = cap.capture(encode(plan), out, aws, clock or Clock())
    return status, aws, out


def load(path):
    return json.loads(path.read_bytes())


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checker_plan(strategy="alias"):
    plan = {
        "schema": rp.PLAN_SCHEMA,
        "plan_id": "invented-plan",
        "account_id": ACCOUNT,
        "region": REGION,
        "production_function": PROD,
        "candidate_function": PROD,
        "max_fact_age_seconds": 3600,
        "artifact": {
            "sha256": ARTIFACT_HEX,
            "manifest_sha256": "a" * 64,
            "zip_bytes": ZIP_BYTES,
        },
        "intended_configuration": {
            "runtime": "python3.11",
            "architectures": ["x86_64"],
            "handler": "lambda_handler.handler",
            "package_type": "Zip",
            "layers": [],
            "memory_size": 512,
            "timeout": 30,
            "ephemeral_storage": 512,
            "environment": {"variables": {}, "allow_unlisted": True},
        },
        "release_strategy": {"type": "unresolved"},
        "rollback": None,
    }
    if strategy == "alias":
        plan["release_strategy"] = {
            "type": "alias",
            "alias_name": ALIAS,
            "phase": "post_release",
            "candidate_version": "8",
            "expected_alias_revision_id": "alias-rev-1",
            "additional_version_weights": {},
        }
        plan["rollback"] = {
            "function_version": "7",
            "code_sha256": OLD_CODE,
            "expected_revision_id": "rev-7",
        }
    return plan


def check_with_checker(tmp_path, out, plan):
    plan_path = tmp_path / "checker-plan.json"
    plan_path.write_bytes(encode(plan))
    index = load(out / "capture-index.json")
    paths = [str(out / record["file"]) for record in index["records"]]
    loaded, _, records = rp.load_inputs(plan_path, paths)
    return rp.evaluate(loaded, records, None, rp.parse_time(AS_OF))


# Contract alignment with the accepted checker.


def test_patterns_and_record_contract_match_the_unchanged_checker():
    for name in (
        "ACCOUNT",
        "REGION",
        "FUNCTION_NAME",
        "VERSION",
        "ALIAS_NAME",
        "SAFE_TOKEN",
        "SHA256_HEX",
        "FUNCTION_ARN",
    ):
        assert getattr(cap, name).pattern == getattr(rp, name).pattern
    assert cap.RECORD_SCHEMA == rp.RECORD_SCHEMA == "jev-saved-aws-response-v2"
    assert cap.ROLES == rp.ROLES
    assert cap.MAX_INT_DIGITS == rp.MAX_INT_DIGITS
    for operation, keys in cap.REQUEST_KEYS.items():
        assert rp.REQUEST_KEYS[operation] == keys
    assert "GetFunction" not in cap.REQUEST_KEYS
    assert set(cap.CALLS) == {
        "GetCallerIdentity",
        "GetFunctionConfiguration",
        "GetAlias",
    }


def test_module_is_stdlib_only_and_loads_the_sdk_lazily():
    tree = ast.parse(Path(cap.__file__).read_text(encoding="utf-8"))
    top_level = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            top_level.add(node.module.split(".")[0])
    assert top_level == {
        "argparse",
        "base64",
        "binascii",
        "datetime",
        "hashlib",
        "json",
        "math",
        "pathlib",
        "re",
        "sys",
        "time",
    }
    factory = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "boto3_client_factory"
    )
    sdk_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom)) and node not in tree.body
    ]
    assert sdk_imports and all(
        any(node is inner for inner in ast.walk(factory)) for node in sdk_imports
    )
    calls = {
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else getattr(node.func, "id", "")
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    # No discovery, pagination, invocation, mutation, presigned URL or file reads
    # other than the plan.
    assert not calls & {
        "get_paginator",
        "list_aliases",
        "list_versions_by_function",
        "get_function",
        "invoke",
        "generate_presigned_url",
        "read_text",
        "iterdir",
        "glob",
        "unlink",
        "rmdir",
        "rename",
        "subprocess",
        "load_dotenv",
    }
    assert "environ" not in Path(cap.__file__).read_text(encoding="utf-8")


def test_sdk_settings_are_bounded_with_exactly_one_attempt():
    assert cap.sdk_settings({"connect_seconds": 5, "read_seconds": 10}) == {
        "connect_timeout": 5,
        "read_timeout": 10,
        "retries": {"total_max_attempts": 1, "mode": "standard"},
    }


# Complete capture and checker compatibility.


def test_complete_capture_produces_records_the_unchanged_checker_accepts(tmp_path):
    plan = capture_plan()
    status, aws, out = run(tmp_path, plan, scripted(plan, standard_responses()))
    assert status == {
        "schema": cap.STATUS_SCHEMA,
        "status": "COMPLETE",
        "stop_code": None,
        "calls_planned": 5,
        "calls_attempted": 5,
        "accepted_records": 4,
        "index_sha256": file_sha256(out / "capture-index.json"),
    }
    assert aws.calls == expected_calls(plan)
    # STS first; the Lambda client exists only after the account is verified.
    assert [call[0] for call in aws.factory_calls] == ["sts", "lambda"]
    assert all(call[1] == REGION for call in aws.factory_calls)
    assert all(
        call[2]["retries"] == {"total_max_attempts": 1, "mode": "standard"}
        for call in aws.factory_calls
    )
    result = check_with_checker(tmp_path, out, checker_plan("alias"))
    assert result["errors"] == []
    assert result["missing_or_stale_facts"] == [
        {"code": "ARTIFACT_FILE_NOT_VERIFIED", "role": "artifact"}
    ]
    assert result["technical_status"] == "INCOMPLETE"
    assert result["release_authorized"] is False
    assert {fact["freshness"] for fact in result["facts"]} == {"WITHIN_MAX_AGE"}


def test_checker_cli_reads_the_written_record_files(tmp_path, capsys):
    plan = capture_plan()
    _, _, out = run(tmp_path, plan, scripted(plan, standard_responses()))
    capsys.readouterr()
    plan_path = tmp_path / "checker-plan.json"
    plan_path.write_bytes(encode(checker_plan("alias")))
    index = load(out / "capture-index.json")
    argv = ["--plan", str(plan_path), "--as-of", AS_OF]
    for record in index["records"]:
        argv += ["--record", str(out / record["file"])]
    assert rp.main(argv) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["technical_status"] == "INCOMPLETE"
    assert result["errors"] == []


def test_unresolved_strategy_and_missing_roles_stay_honestly_incomplete(tmp_path):
    plan = capture_plan((BASELINE,))
    status, aws, out = run(tmp_path, plan, scripted(plan, standard_responses()))
    assert status["status"] == "COMPLETE" and status["calls_attempted"] == 2
    # Only the planned read: nothing discovered, inferred or filled in.
    assert aws.calls == expected_calls(plan)
    result = check_with_checker(tmp_path, out, checker_plan("unresolved"))
    assert result["technical_status"] == "INCOMPLETE"
    assert result["errors"] == []
    assert {"code": "CANDIDATE_RECORD_MISSING", "role": "candidate"} in result[
        "missing_or_stale_facts"
    ]
    assert {entry["code"] for entry in result["unresolved_decisions"]} == {
        "RELEASE_STRATEGY_UNRESOLVED",
        "ROLLBACK_TARGET_UNRESOLVED",
    }


def test_alias_strategy_without_captured_alias_or_rollback_is_not_invented(tmp_path):
    plan = capture_plan((BASELINE, CANDIDATE))
    _, aws, out = run(tmp_path, plan, scripted(plan, standard_responses()))
    assert len(aws.calls) == 3
    result = check_with_checker(tmp_path, out, checker_plan("alias"))
    assert {"code": "ALIAS_RECORD_MISSING", "role": "alias"} in result[
        "missing_or_stale_facts"
    ]
    assert {"code": "ROLLBACK_RECORD_MISSING", "role": "rollback_target"} in result[
        "errors"
    ]


# Exact bindings and faithful preservation.


def test_operation_request_and_response_bindings_are_exact(tmp_path):
    plan = capture_plan()
    responses = standard_responses()
    _, aws, out = run(tmp_path, plan, scripted(plan, responses))
    index = load(out / "capture-index.json")
    assert index["files"] == {
        path.name: file_sha256(path)
        for path in out.iterdir()
        if path.name != "capture-index.json"
    }
    assert (out / "capture-plan.json").read_bytes() == encode(plan)
    assert index["plan_sha256"] == hashlib.sha256(encode(plan)).hexdigest()
    by_role = {entry["role"]: entry for entry in plan["observations"]}
    for entry in index["records"]:
        record = load(out / entry["file"])
        observation = load(out / entry["observation_file"])
        assert set(record) == {
            "schema",
            "role",
            "operation",
            "request",
            "observed_utc",
            "response",
        }
        planned = by_role[entry["role"]]
        assert record["operation"] == observation["operation"] == planned["operation"]
        assert record["request"] == observation["request"] == planned["request"]
        # Preserved exactly as returned, ResponseMetadata and unknown fields included.
        assert record["response"] == observation["response"] == responses[entry["role"]]
        assert (
            observation["response_sha256"]
            == hashlib.sha256(cap.canonical(record["response"]).encode()).hexdigest()
        )
        assert entry["sha256"] == observation["record"]["sha256"]
        assert entry["sha256"] == file_sha256(out / entry["file"])
        assert entry["observation_sha256"] == file_sha256(
            out / entry["observation_file"]
        )
        assert observation["kind"] == "NEW_OBSERVATION"
        assert observation["outcome"] == "ACCEPTED"
        assert observation["response_metadata"]["retry_attempts"] == 0
        assert observation["sdk"]["total_max_attempts"] == 1
    sts = load(out / "01-account_verification.observation.json")
    assert sts["operation"] == "GetCallerIdentity" and sts["request"] == {}
    assert sts["record"] is None and sts["response"] == caller()
    assert index["authorization"] == {"status": "NOT_SUPPLIED", "reference": None}
    assert index["live_opt_in"] == "CLI_FLAG_IS_NOT_OWNER_AUTHORIZATION"


def test_authorization_reference_is_recorded_but_never_authenticated(tmp_path):
    reference = {"label": "invented-owner-approval", "sha256": "b" * 64}
    plan = capture_plan((BASELINE,), authorization_reference=reference)
    _, _, out = run(tmp_path, plan, scripted(plan, standard_responses()))
    assert load(out / "capture-index.json")["authorization"] == {
        "status": "REFERENCED_NOT_AUTHENTICATED",
        "reference": reference,
    }


def test_malformed_nonbinding_field_is_preserved_not_repaired(tmp_path):
    plan = capture_plan((BASELINE,))
    responses = standard_responses()
    responses["production_baseline"]["MemorySize"] = "512"
    del responses["production_baseline"]["EphemeralStorage"]
    status, _, out = run(tmp_path, plan, scripted(plan, responses))
    assert status["status"] == "COMPLETE"
    record = load(out / "02-production_baseline.record.json")
    assert record["response"]["MemorySize"] == "512"
    assert "EphemeralStorage" not in record["response"]
    result = check_with_checker(tmp_path, out, checker_plan("unresolved"))
    assert result["technical_status"] == "BLOCKED"
    assert {(error["code"], error.get("field")) for error in result["errors"]} >= {
        ("RESPONSE_FIELD_INVALID", "MemorySize"),
        ("RESPONSE_FIELD_MISSING", "EphemeralStorage"),
    }


# Account verification.


def test_account_mismatch_stops_every_later_call(tmp_path):
    plan = capture_plan()
    results = [caller(OTHER_ACCOUNT)] + scripted(plan, standard_responses())[1:]
    status, aws, out = run(tmp_path, plan, results)
    assert status["status"] == "STOPPED"
    assert status["stop_code"] == "ACCOUNT_MISMATCH"
    assert status["calls_attempted"] == 1 and status["accepted_records"] == 0
    assert aws.calls == [("sts", "get_caller_identity", {})]
    assert [call[0] for call in aws.factory_calls] == ["sts"]
    index = load(out / "capture-index.json")
    assert index["account_verified"] is False and index["records"] == []
    observation = load(out / "01-account_verification.observation.json")
    assert observation["outcome"] == "REJECTED"
    assert observation["reason"] == {"code": "ACCOUNT_MISMATCH", "field": "Account"}
    assert observation["response"] == caller(OTHER_ACCOUNT)
    assert not list(out.glob("*.record.json"))


@pytest.mark.parametrize(
    "mutate, code, field",
    [
        (lambda r: r.pop("Account"), "RESPONSE_FIELD_MISSING", "Account"),
        (lambda r: r.update(Account=123456789012), "RESPONSE_FIELD_INVALID", "Account"),
        (lambda r: r.update(Account="12345"), "RESPONSE_FIELD_INVALID", "Account"),
        (lambda r: r.pop("Arn"), "RESPONSE_FIELD_MISSING", "Arn"),
    ],
)
def test_malformed_caller_identity_stops_before_lambda(tmp_path, mutate, code, field):
    plan = capture_plan((BASELINE,))
    identity = caller()
    mutate(identity)
    status, aws, out = run(
        tmp_path, plan, [identity, standard_responses()["production_baseline"]]
    )
    assert (status["stop_code"], status["calls_attempted"]) == (code, 1)
    assert len(aws.calls) == 1
    observation = load(out / "01-account_verification.observation.json")
    assert observation["reason"] == {"code": code, "field": field}
    assert observation["response"] == identity


# Plan validation happens before any client, call or directory.

INVALID_PLANS = [
    (
        "operation GetFunction",
        lambda p: p["observations"][0].update(operation="GetFunction"),
        "PLAN_OPERATION_UNSUPPORTED",
    ),
    (
        "operation Invoke",
        lambda p: p["observations"][0].update(operation="Invoke"),
        "PLAN_OPERATION_UNSUPPORTED",
    ),
    (
        "operation ListVersionsByFunction",
        lambda p: p["observations"][0].update(operation="ListVersionsByFunction"),
        "PLAN_OPERATION_UNSUPPORTED",
    ),
    (
        "operation GetCallerIdentity as role",
        lambda p: p["observations"][0].update(operation="GetCallerIdentity"),
        "PLAN_OPERATION_UNSUPPORTED",
    ),
    (
        "alias via function read",
        lambda p: p["observations"][3].update(operation="GetFunctionConfiguration"),
        "PLAN_OPERATION_UNSUPPORTED",
    ),
    (
        "function via GetAlias",
        lambda p: p["observations"][0].update(operation="GetAlias"),
        "PLAN_OPERATION_UNSUPPORTED",
    ),
    (
        "ARN FunctionName",
        lambda p: p["observations"][0]["request"].update(
            FunctionName=f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{PROD}"
        ),
        "PLAN_REQUEST_UNSUPPORTED",
    ),
    (
        "partial ARN",
        lambda p: p["observations"][0]["request"].update(
            FunctionName=f"{ACCOUNT}:function:{PROD}"
        ),
        "PLAN_REQUEST_UNSUPPORTED",
    ),
    (
        "alias qualifier",
        lambda p: p["observations"][1]["request"].update(Qualifier=ALIAS),
        "PLAN_REQUEST_UNSUPPORTED",
    ),
    (
        "leading-zero version",
        lambda p: p["observations"][1]["request"].update(Qualifier="08"),
        "PLAN_REQUEST_UNSUPPORTED",
    ),
    (
        "numeric alias name",
        lambda p: p["observations"][3]["request"].update(Name="8"),
        "PLAN_REQUEST_UNSUPPORTED",
    ),
    (
        "non-string qualifier",
        lambda p: p["observations"][1]["request"].update(Qualifier=8),
        "PLAN_REQUEST_INVALID",
    ),
    (
        "extra Marker argument",
        lambda p: p["observations"][0]["request"].update(Marker="x"),
        "PLAN_REQUEST_INVALID",
    ),
    (
        "Name on a function read",
        lambda p: p["observations"][0]["request"].update(Name=ALIAS),
        "PLAN_REQUEST_INVALID",
    ),
    (
        "Qualifier on GetAlias",
        lambda p: p["observations"][3]["request"].update(Qualifier="8"),
        "PLAN_REQUEST_INVALID",
    ),
    (
        "alias without Name",
        lambda p: p["observations"][3]["request"].pop("Name"),
        "PLAN_REQUEST_INVALID",
    ),
    (
        "rollback without version",
        lambda p: p["observations"][2]["request"].pop("Qualifier"),
        "PLAN_TARGET_NOT_EXPLICIT",
    ),
    (
        "rollback at $LATEST",
        lambda p: p["observations"][2]["request"].update(Qualifier="$LATEST"),
        "PLAN_TARGET_NOT_EXPLICIT",
    ),
    ("call limit headroom", lambda p: p.update(max_calls=6), "PLAN_CALL_LIMIT_INVALID"),
    (
        "call limit too small",
        lambda p: p.update(max_calls=4),
        "PLAN_CALL_LIMIT_INVALID",
    ),
    (
        "call limit boolean",
        lambda p: p.update(max_calls=True),
        "PLAN_CALL_LIMIT_INVALID",
    ),
    (
        "duplicate role",
        lambda p: p["observations"].__setitem__(1, copy.deepcopy(BASELINE)),
        "PLAN_INVALID",
    ),
    (
        "unknown role",
        lambda p: p["observations"][0].update(role="production"),
        "PLAN_INVALID",
    ),
    (
        "embedded saved response",
        lambda p: p["observations"][0].update(response={}),
        "PLAN_INVALID",
    ),
    ("embedded records", lambda p: p.update(records=[]), "PLAN_INVALID"),
    (
        "empty observations",
        lambda p: p.update(observations=[], max_calls=1),
        "PLAN_INVALID",
    ),
    (
        "five observations",
        lambda p: p["observations"].append(copy.deepcopy(BASELINE)),
        "PLAN_INVALID",
    ),
    (
        "zero connect timeout",
        lambda p: p["timeouts"].update(connect_seconds=0),
        "PLAN_INVALID",
    ),
    (
        "long read timeout",
        lambda p: p["timeouts"].update(read_seconds=31),
        "PLAN_INVALID",
    ),
    ("float timeout", lambda p: p["timeouts"].update(read_seconds=1.5), "PLAN_INVALID"),
    (
        "boolean timeout",
        lambda p: p["timeouts"].update(connect_seconds=True),
        "PLAN_INVALID",
    ),
    ("retry setting", lambda p: p["timeouts"].update(max_attempts=3), "PLAN_INVALID"),
    ("bad account", lambda p: p.update(account_id="12345"), "PLAN_INVALID"),
    ("bad region", lambda p: p.update(region="US-EAST-1"), "PLAN_INVALID"),
    ("bad capture id", lambda p: p.update(capture_id="a b"), "PLAN_INVALID"),
    (
        "wrong schema",
        lambda p: p.update(schema="jev-saved-aws-response-v2"),
        "PLAN_INVALID",
    ),
    (
        "bad authorization hash",
        lambda p: p.update(authorization_reference={"label": "x", "sha256": "B" * 64}),
        "PLAN_INVALID",
    ),
]


@pytest.mark.parametrize(
    "mutate, code",
    [case[1:] for case in INVALID_PLANS],
    ids=[case[0] for case in INVALID_PLANS],
)
def test_invalid_plans_are_rejected_before_any_client_or_output(tmp_path, mutate, code):
    plan = capture_plan()
    mutate(plan)
    aws = FakeAWS([])
    with pytest.raises(cap.InputError) as raised:
        cap.capture(encode(plan), tmp_path / "capture", aws, Clock())
    assert str(raised.value) == code
    assert aws.factory_calls == [] and aws.calls == []
    assert not (tmp_path / "capture").exists()


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema": NaN}',
        b'{"schema": 1e400}',
        b'{"schema": ' + b"9" * 80 + b"}",
        b'{"schema": "\\ud800"}',
        b'{"schema": "a", "schema": "b"}',
        b"\xff\xfe",
        b"[" * 100000,
        b" " * (cap.MAX_PLAN_BYTES + 1),
    ],
    ids=[
        "nan",
        "overflow",
        "huge-int",
        "surrogate",
        "duplicate-key",
        "not-utf8",
        "deep",
        "oversize",
    ],
)
def test_unreadable_plans_are_rejected_before_any_client(tmp_path, raw):
    aws = FakeAWS([])
    with pytest.raises(cap.InputError) as raised:
        cap.capture(raw, tmp_path / "capture", aws, Clock())
    assert str(raised.value) == "PLAN_UNREADABLE"
    assert aws.factory_calls == [] and not (tmp_path / "capture").exists()


# Response binding and field checks.

FUNCTION_DEFECTS = [
    (
        "missing FunctionArn",
        lambda r: r.pop("FunctionArn"),
        "RESPONSE_FIELD_MISSING",
        "FunctionArn",
    ),
    (
        "missing Version",
        lambda r: r.pop("Version"),
        "RESPONSE_FIELD_MISSING",
        "Version",
    ),
    (
        "missing CodeSha256",
        lambda r: r.pop("CodeSha256"),
        "RESPONSE_FIELD_MISSING",
        "CodeSha256",
    ),
    (
        "missing FunctionName",
        lambda r: r.pop("FunctionName"),
        "RESPONSE_FIELD_MISSING",
        "FunctionName",
    ),
    (
        "integer Version",
        lambda r: r.update(Version=8),
        "RESPONSE_FIELD_INVALID",
        "Version",
    ),
    (
        "alias Version",
        lambda r: r.update(Version="live"),
        "RESPONSE_FIELD_INVALID",
        "Version",
    ),
    (
        "hex CodeSha256",
        lambda r: r.update(CodeSha256=ARTIFACT_HEX),
        "RESPONSE_FIELD_INVALID",
        "CodeSha256",
    ),
    (
        "non-canonical CodeSha256",
        lambda r: r.update(CodeSha256=NONCANONICAL_CODE),
        "RESPONSE_FIELD_INVALID",
        "CodeSha256",
    ),
    (
        "null CodeSha256",
        lambda r: r.update(CodeSha256=None),
        "RESPONSE_FIELD_INVALID",
        "CodeSha256",
    ),
    (
        "unparseable FunctionArn",
        lambda r: r.update(FunctionArn="not-an-arn"),
        "RESPONSE_FIELD_INVALID",
        "FunctionArn",
    ),
    (
        "other account",
        lambda r: r.update(
            FunctionArn=r["FunctionArn"].replace(ACCOUNT, OTHER_ACCOUNT)
        ),
        "RESPONSE_BINDING_MISMATCH",
        "FunctionArn",
    ),
    (
        "other region",
        lambda r: r.update(FunctionArn=r["FunctionArn"].replace(REGION, "eu-west-1")),
        "RESPONSE_BINDING_MISMATCH",
        "FunctionArn",
    ),
    (
        "other function",
        lambda r: r.update(FunctionName="invented-other"),
        "RESPONSE_BINDING_MISMATCH",
        "FunctionArn",
    ),
    (
        "other version",
        lambda r: r.update(Version="9", FunctionArn=r["FunctionArn"][:-1] + "9"),
        "RESPONSE_BINDING_MISMATCH",
        "Version",
    ),
    (
        "unqualified ARN for a version read",
        lambda r: r.update(FunctionArn=r["FunctionArn"].rsplit(":", 1)[0]),
        "RESPONSE_BINDING_MISMATCH",
        "Version",
    ),
    (
        "$LATEST for a version read",
        lambda r: r.update(Version="$LATEST"),
        "RESPONSE_BINDING_MISMATCH",
        "Version",
    ),
]


@pytest.mark.parametrize(
    "mutate, code, field",
    [case[1:] for case in FUNCTION_DEFECTS],
    ids=[case[0] for case in FUNCTION_DEFECTS],
)
def test_function_response_defects_reject_and_preserve(tmp_path, mutate, code, field):
    plan = capture_plan((CANDIDATE, ALIAS_READ))
    responses = standard_responses()
    mutate(responses["candidate"])
    status, aws, out = run(tmp_path, plan, scripted(plan, responses))
    assert (status["status"], status["stop_code"]) == ("STOPPED", code)
    assert len(aws.calls) == 2  # the alias read after the defect never happens
    observation = load(out / "02-candidate.observation.json")
    assert observation["outcome"] == "REJECTED"
    assert observation["reason"] == {"code": code, "field": field}
    assert observation["response"] == responses["candidate"]  # not repaired
    assert observation["record"] is None
    assert not list(out.glob("*.record.json"))


ALIAS_DEFECTS = [
    (
        "missing AliasArn",
        lambda r: r.pop("AliasArn"),
        "RESPONSE_FIELD_MISSING",
        "AliasArn",
    ),
    (
        "missing FunctionVersion",
        lambda r: r.pop("FunctionVersion"),
        "RESPONSE_FIELD_MISSING",
        "FunctionVersion",
    ),
    (
        "integer FunctionVersion",
        lambda r: r.update(FunctionVersion=8),
        "RESPONSE_FIELD_INVALID",
        "FunctionVersion",
    ),
    (
        "alias FunctionVersion",
        lambda r: r.update(FunctionVersion="other"),
        "RESPONSE_FIELD_INVALID",
        "FunctionVersion",
    ),
    (
        "version-qualified AliasArn",
        lambda r: r.update(AliasArn=r["AliasArn"].replace(f":{ALIAS}", ":8")),
        "RESPONSE_FIELD_INVALID",
        "AliasArn",
    ),
    (
        "other alias name",
        lambda r: r.update(Name="other"),
        "RESPONSE_BINDING_MISMATCH",
        "AliasArn",
    ),
    (
        "other account",
        lambda r: r.update(AliasArn=r["AliasArn"].replace(ACCOUNT, OTHER_ACCOUNT)),
        "RESPONSE_BINDING_MISMATCH",
        "AliasArn",
    ),
]


@pytest.mark.parametrize(
    "mutate, code, field",
    [case[1:] for case in ALIAS_DEFECTS],
    ids=[case[0] for case in ALIAS_DEFECTS],
)
def test_alias_response_defects_reject_and_preserve(tmp_path, mutate, code, field):
    plan = capture_plan((ALIAS_READ,))
    responses = standard_responses()
    mutate(responses["alias"])
    status, _, out = run(tmp_path, plan, scripted(plan, responses))
    assert status["stop_code"] == code
    observation = load(out / "02-alias.observation.json")
    assert observation["reason"] == {"code": code, "field": field}
    assert observation["response"] == responses["alias"]


def test_unqualified_and_latest_reads_bind_to_latest(tmp_path):
    latest = {
        "role": "candidate",
        "operation": "GetFunctionConfiguration",
        "request": {"FunctionName": PROD, "Qualifier": "$LATEST"},
    }
    plan = capture_plan((BASELINE, latest))
    responses = standard_responses()
    responses["candidate"] = fn_config("$LATEST")
    status, _, _ = run(tmp_path, plan, scripted(plan, responses))
    assert status["status"] == "COMPLETE"


@pytest.mark.parametrize(
    "response",
    [
        {**fn_config("8"), "MemorySize": float("nan")},
        {**fn_config("8"), "LastModified": datetime.datetime(2026, 10, 6)},
        {**fn_config("8"), "Description": "\ud800"},
        {**fn_config("8"), "CodeSize": 10**70},
        ["not", "a", "mapping"],
        None,
    ],
    ids=["nan", "datetime", "surrogate", "huge-int", "list", "none"],
)
def test_unrepresentable_responses_are_rejected_not_coerced(tmp_path, response):
    plan = capture_plan((CANDIDATE,))
    aws = FakeAWS([caller(), response])
    status = cap.capture(encode(plan), tmp_path / "capture", aws, Clock())
    assert status["stop_code"] == "RESPONSE_NOT_JSON_REPRESENTABLE"
    observation = load(tmp_path / "capture" / "02-candidate.observation.json")
    assert observation["response"] is None and observation["record"] is None


# Retries and failed reads.


@pytest.mark.parametrize(
    "response_metadata, code",
    [
        (metadata(retries=1), "UNEXPECTED_RETRY"),
        (metadata(retries=2), "UNEXPECTED_RETRY"),
        ({"RequestId": "invented"}, "RETRY_METADATA_MISSING"),
        ({**metadata(), "RetryAttempts": "0"}, "RETRY_METADATA_MISSING"),
        (None, "RETRY_METADATA_MISSING"),
    ],
    ids=["one-retry", "two-retries", "no-retry-field", "string-retry", "no-metadata"],
)
def test_retries_and_missing_retry_metadata_stop_the_capture(
    tmp_path, response_metadata, code
):
    plan = capture_plan((CANDIDATE, ALIAS_READ))
    responses = standard_responses()
    if response_metadata is None:
        del responses["candidate"]["ResponseMetadata"]
    else:
        responses["candidate"]["ResponseMetadata"] = response_metadata
    status, aws, out = run(tmp_path, plan, scripted(plan, responses))
    assert status["stop_code"] == code and len(aws.calls) == 2
    observation = load(out / "02-candidate.observation.json")
    assert observation["reason"]["code"] == code
    assert observation["response"] == responses["candidate"]


def test_failed_read_keeps_fixed_fields_only_and_stops(tmp_path):
    plan = capture_plan((BASELINE, CANDIDATE, ALIAS_READ))
    results = scripted(plan, standard_responses())
    results[2] = InventedClientError("ResourceNotFoundException", retries=0)
    status, aws, out = run(tmp_path, plan, results)
    assert (status["status"], status["stop_code"]) == ("STOPPED", "READ_FAILED")
    assert status["calls_attempted"] == 3 and len(aws.calls) == 3
    observation = load(out / "03-candidate.observation.json")
    assert observation["outcome"] == "READ_FAILED"
    assert observation["error"] == {
        "type": "InventedClientError",
        "aws_error_code": "ResourceNotFoundException",
    }
    assert observation["response_metadata"] == {
        "retry_attempts": 0,
        "http_status_code": 200,
        "request_id": "invented-failed-0001",
    }
    assert observation["response"] is None
    assert MESSAGE not in (out / "03-candidate.observation.json").read_text()


def test_generic_client_failure_records_type_only(tmp_path):
    plan = capture_plan((BASELINE,))
    status, _, out = run(tmp_path, plan, [caller(), TimeoutError(MESSAGE)])
    assert status["stop_code"] == "READ_FAILED"
    observation = load(out / "02-production_baseline.observation.json")
    assert observation["error"] == {"type": "TimeoutError", "aws_error_code": None}
    assert observation["response_metadata"]["retry_attempts"] is None


def test_client_construction_failure_makes_no_call(tmp_path):
    def factory(service, region, settings):
        raise RuntimeError(MESSAGE)

    status = cap.capture(encode(capture_plan()), tmp_path / "capture", factory, Clock())
    assert (status["stop_code"], status["calls_attempted"]) == ("CLIENT_UNAVAILABLE", 0)
    index = load(tmp_path / "capture" / "capture-index.json")
    assert index["stop"] == {"code": "CLIENT_UNAVAILABLE", "field": "sts"}
    assert set(index["files"]) == {"capture-plan.json"}


# Partial results.


def test_completed_observations_survive_a_later_failure(tmp_path):
    plan = capture_plan()
    results = scripted(plan, standard_responses())
    results[3] = InventedClientError()
    status, _, out = run(tmp_path, plan, results)
    assert status["status"] == "STOPPED" and status["accepted_records"] == 2
    index = load(out / "capture-index.json")
    assert [entry["role"] for entry in index["records"]] == [
        "production_baseline",
        "candidate",
    ]
    for entry in index["records"]:
        assert file_sha256(out / entry["file"]) == entry["sha256"]
    assert index["calls"] == {"planned": 5, "attempted": 4}
    assert index["account_verified"] is True
    assert sorted(index["files"]) == [
        "01-account_verification.observation.json",
        "02-production_baseline.observation.json",
        "02-production_baseline.record.json",
        "03-candidate.observation.json",
        "03-candidate.record.json",
        "04-rollback_target.observation.json",
        "capture-plan.json",
    ]
    result = check_with_checker(tmp_path, out, checker_plan("alias"))
    assert {"code": "ALIAS_RECORD_MISSING", "role": "alias"} in result[
        "missing_or_stale_facts"
    ]


# Timestamps.


def test_each_observation_has_distinct_separately_read_timestamps(tmp_path):
    plan = capture_plan()
    _, _, out = run(tmp_path, plan, scripted(plan, standard_responses()))
    observations = [load(path) for path in sorted(out.glob("*.observation.json"))]
    stamps = [
        (o["timing"]["request_started_utc"], o["timing"]["response_received_utc"])
        for o in observations
    ]
    flat = [value for pair in stamps for value in pair]
    assert len(set(flat)) == len(flat) == 10
    assert flat == sorted(flat)
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z", s) for s in flat)
    for observation in observations[1:]:
        record = load(out / observation["record"]["file"])
        assert record["observed_utc"] == observation["timing"]["request_started_utc"]
        assert observation["timing"]["semantics"]["clock"] == (
            "HOST_UTC_CLOCK_NOT_AWS_AUTHENTICATED"
        )


def test_repeated_request_start_time_stops_before_the_call(tmp_path):
    plan = capture_plan((BASELINE, CANDIDATE))
    seconds = [0, 1, 2, 3, 2]  # the third read would start at the previous start
    clock = Clock([T0 + datetime.timedelta(seconds=value) for value in seconds])
    status, aws, _ = run(tmp_path, plan, scripted(plan, standard_responses()), clock)
    assert status["stop_code"] == "CLOCK_INVALID"
    assert len(aws.calls) == 2


def test_backwards_response_time_rejects_but_preserves_response(tmp_path):
    plan = capture_plan((BASELINE,))
    clock = Clock(
        [T0, T0 + datetime.timedelta(seconds=1), T0 + datetime.timedelta(seconds=5), T0]
    )
    status, _, out = run(tmp_path, plan, scripted(plan, standard_responses()), clock)
    assert status["stop_code"] == "CLOCK_INVALID"
    observation = load(out / "02-production_baseline.observation.json")
    assert observation["reason"] == {
        "code": "CLOCK_INVALID",
        "field": "response_received_utc",
    }
    assert observation["response"] == standard_responses()["production_baseline"]
    assert observation["record"] is None


def test_naive_clock_is_rejected_before_any_call(tmp_path):
    plan = capture_plan((BASELINE,))
    status, aws, _ = run(
        tmp_path,
        plan,
        scripted(plan, standard_responses()),
        Clock([T0.replace(tzinfo=None)]),
    )
    assert status["stop_code"] == "CLOCK_INVALID" and aws.calls == []


# Output claims and overwrite rejection.


def test_duplicate_output_claim_is_rejected_and_existing_evidence_untouched(tmp_path):
    plan = capture_plan((BASELINE,))
    run(tmp_path, plan, scripted(plan, standard_responses()))
    before = {path.name: path.read_bytes() for path in (tmp_path / "capture").iterdir()}
    aws = FakeAWS(scripted(plan, standard_responses()))
    with pytest.raises(cap.InputError) as raised:
        cap.capture(encode(plan), tmp_path / "capture", aws, Clock())
    assert str(raised.value) == "OUTPUT_EXISTS"
    assert aws.factory_calls == [] and aws.calls == []
    after = {path.name: path.read_bytes() for path in (tmp_path / "capture").iterdir()}
    assert after == before


def test_existing_empty_directory_is_not_reused(tmp_path):
    (tmp_path / "capture").mkdir()
    with pytest.raises(cap.InputError, match="OUTPUT_EXISTS"):
        cap.capture(encode(capture_plan()), tmp_path / "capture", FakeAWS([]), Clock())


def test_publisher_never_overwrites(tmp_path):
    publisher = cap.Publisher(tmp_path)
    publisher.write_json("a.json", {"first": True})
    with pytest.raises(FileExistsError):
        publisher.write_json("a.json", {"second": True})
    (tmp_path / "b.json").write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        cap.Publisher(tmp_path).write_json("b.json", {})
    assert (tmp_path / "b.json").read_bytes() == b"existing"
    assert load(tmp_path / "a.json") == {"first": True}


def test_output_inside_a_git_worktree_is_refused(tmp_path):
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    (tmp_path / "repo" / "nested").mkdir()
    aws = FakeAWS([])
    with pytest.raises(cap.InputError, match="OUTPUT_INSIDE_REPOSITORY"):
        cap.capture(
            encode(capture_plan()), tmp_path / "repo" / "nested" / "out", aws, Clock()
        )
    assert not (tmp_path / "repo" / "nested" / "out").exists()
    repository = Path(cap.__file__).resolve().parents[1]
    with pytest.raises(cap.InputError, match="OUTPUT_INSIDE_REPOSITORY"):
        cap.claim_output(repository / "invented-capture-never-created")
    assert not (repository / "invented-capture-never-created").exists()
    assert aws.factory_calls == []


@pytest.mark.parametrize(
    "relative, code",
    [
        ("missing/out", "OUTPUT_PARENT_MISSING"),
        ("..", "OUTPUT_NAME_INVALID"),
        ("bad name", "OUTPUT_NAME_INVALID"),
    ],
)
def test_output_path_rules(tmp_path, relative, code):
    with pytest.raises(cap.InputError, match=code):
        cap.claim_output(tmp_path / relative)


# Live entry point (driven only with an injected fake factory).


def write_plan(tmp_path, plan):
    path = tmp_path / "capture-plan-input.json"
    path.write_bytes(encode(plan))
    return str(path)


def test_cli_without_live_only_validates_and_makes_no_client(tmp_path, capsys):
    aws = FakeAWS([])
    plan = capture_plan()
    assert cap.main(["--plan", write_plan(tmp_path, plan)], aws, Clock()) == 0
    assert json.loads(capsys.readouterr().out) == {
        "schema": cap.STATUS_SCHEMA,
        "status": "PLAN_VALID_NO_CALLS_MADE",
        "calls_planned": 5,
        "plan_sha256": hashlib.sha256(encode(plan)).hexdigest(),
    }
    assert aws.factory_calls == []


@pytest.mark.parametrize(
    "extra",
    [["--out", "OUT"], ["--live"]],
    ids=["out-without-live", "live-without-out"],
)
def test_cli_requires_both_opt_in_and_output(tmp_path, capsys, extra):
    aws = FakeAWS([])
    argv = ["--plan", write_plan(tmp_path, capture_plan())] + [
        str(tmp_path / "capture") if value == "OUT" else value for value in extra
    ]
    assert cap.main(argv, aws, Clock()) == 2
    assert json.loads(capsys.readouterr().err) == {
        "status": "INPUT_REJECTED",
        "code": "LIVE_OPT_IN_REQUIRED",
    }
    assert aws.factory_calls == [] and not (tmp_path / "capture").exists()


def test_cli_invalid_plan_with_live_never_reaches_a_client(tmp_path, capsys):
    plan = capture_plan()
    plan["observations"][0]["operation"] = "GetFunction"
    aws = FakeAWS([])
    argv = [
        "--plan",
        write_plan(tmp_path, plan),
        "--out",
        str(tmp_path / "capture"),
        "--live",
    ]
    assert cap.main(argv, aws, Clock()) == 2
    assert json.loads(capsys.readouterr().err)["code"] == "PLAN_OPERATION_UNSUPPORTED"
    assert aws.factory_calls == [] and not (tmp_path / "capture").exists()


def test_cli_missing_plan_file_is_sanitized(tmp_path, capsys):
    assert (
        cap.main(["--plan", str(tmp_path / "absent.json")], FakeAWS([]), Clock()) == 2
    )
    assert json.loads(capsys.readouterr().err)["code"] == "PLAN_UNREADABLE"


@pytest.mark.parametrize("fail", [False, True], ids=["complete", "failed-read"])
def test_console_output_is_sanitized(tmp_path, capsys, fail):
    plan = capture_plan()
    results = scripted(plan, standard_responses())
    if fail:
        results[4] = InventedClientError()
    aws = FakeAWS(results)
    argv = [
        "--plan",
        write_plan(tmp_path, plan),
        "--out",
        str(tmp_path / "capture"),
        "--live",
    ]
    assert cap.main(argv, aws, Clock()) == (1 if fail else 0)
    captured = capsys.readouterr()
    assert captured.err == ""
    status = json.loads(captured.out)
    assert set(status) == {
        "schema",
        "status",
        "stop_code",
        "calls_planned",
        "calls_attempted",
        "accepted_records",
        "index_sha256",
    }
    console = captured.out
    for forbidden in (
        SECRET,
        ROLE_ARN,
        CALLER_ARN,
        MESSAGE,
        ACCOUNT,
        PROD,
        ARTIFACT_CODE,
        "invented-request",
        str(tmp_path),
    ):
        assert forbidden not in console
    # The private capture keeps the faithful response, secrets included.
    private = (tmp_path / "capture" / "02-production_baseline.record.json").read_text()
    assert SECRET in private and ROLE_ARN in private
