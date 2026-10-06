"""Synthetic contract checks for the read-only release preflight.

Invented accounts, functions, ZIPs and AWS responses only. Nothing here proves
live AWS permissions, atomic deployment or a successful rollback.
"""

import ast
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from scripts import jev_release_preflight as rp
from tests import offline_guard

ACCOUNT = "123456789012"
REGION = "us-east-1"
PROD = "invented-copilot"
TEST_FN = "invented-copilot-check"
AS_OF = "2026-10-06T12:00:00+00:00"
FRESH = "2026-10-06T11:50:00+00:00"
LAYER = f"arn:aws:lambda:{REGION}:{ACCOUNT}:layer:invented-deps:2"
SECRET = "invented-secret-token-value-never-printed"
LOCATION = "https://invented.example/presigned?X-Amz-Signature=never-printed"
REASON = "invented provider message never printed"
OLD_CODE = base64.b64encode(hashlib.sha256(b"invented previous code").digest()).decode()
MANIFEST = {
    "schema": "lambda-build-manifest-v1",
    "target": {
        "runtime": "python3.11",
        "platform": "manylinux2014_x86_64",
        "architecture": "x86_64",
        "handler": "lambda_handler.handler",
    },
    "packaging_policy": {
        "delivery_mode": "s3",
        "dependency_allocation": "complete-function-no-layers",
        "compressed_zip_limit_bytes": None,
        "aggregate_uncompressed_limit_bytes": 262144000,
        "network_operation": "NONE",
    },
    "layer_evidence": {"layers": []},
}


def make_zip(path, manifest=MANIFEST, extra=b"# invented, never executed\n"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("lambda_handler.py", extra)
        if manifest is not None:
            archive.writestr(rp.MANIFEST_NAME, rp.canonical(manifest).encode())
    path.write_bytes(buffer.getvalue())
    return path


def describe(path):
    raw = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        manifest = archive.read(rp.MANIFEST_NAME)
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "zip_bytes": len(raw),
    }


def base_plan(artifact, strategy="alias", candidate_function=PROD):
    plan = {
        "schema": rp.PLAN_SCHEMA,
        "plan_id": "invented-plan-01",
        "account_id": ACCOUNT,
        "region": REGION,
        "production_function": PROD,
        "candidate_function": candidate_function,
        "max_fact_age_seconds": 3600,
        "artifact": artifact,
        "intended_configuration": {
            "runtime": "python3.11",
            "architectures": ["x86_64"],
            "handler": "lambda_handler.handler",
            "package_type": "Zip",
            "layers": [],
            "memory_size": 512,
            "timeout": 30,
            "ephemeral_storage": 512,
            "environment": {
                "variables": {
                    "BEDROCK_MODEL_ID": {
                        "expect": "equals",
                        "value": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
                    },
                    "COPILOT_ROUTER_PROVIDER": {"expect": "absent"},
                    "EVALUATE_ENDPOINT_TOKEN": {
                        "expect": "sha256",
                        "sha256": hashlib.sha256(SECRET.encode()).hexdigest(),
                    },
                },
                "allow_unlisted": False,
            },
        },
        "release_strategy": {"type": "unresolved"},
        "rollback": None,
    }
    if strategy == "alias":
        plan["release_strategy"] = {
            "type": "alias",
            "alias_name": "live",
            "phase": "pre_release",
            "candidate_version": "8",
            "expected_alias_revision_id": "alias-rev-1",
            "expected_candidate_revision_id": "cand-rev-1",
            "additional_version_weights": {},
        }
        plan["rollback"] = {
            "function_version": "7",
            "code_sha256": OLD_CODE,
            "expected_revision_id": "roll-rev-1",
        }
    return plan


def configuration(
    code_sha256,
    zip_bytes,
    version="$LATEST",
    function=PROD,
    layers=(),
    revision="cand-rev-1",
    environment=None,
):
    arn = f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{function}"
    if version != "$LATEST":
        arn += ":" + version
    if environment is None:
        environment = {
            "BEDROCK_MODEL_ID": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
            "EVALUATE_ENDPOINT_TOKEN": SECRET,
        }
    value = {
        "FunctionName": function,
        "FunctionArn": arn,
        "Runtime": "python3.11",
        "Role": f"arn:aws:iam::{ACCOUNT}:role/invented",
        "Handler": "lambda_handler.handler",
        "CodeSize": zip_bytes,
        "CodeSha256": code_sha256,
        "Version": version,
        "MemorySize": 512,
        "Timeout": 30,
        "PackageType": "Zip",
        "Architectures": ["x86_64"],
        "State": "Active",
        "StateReason": REASON,
        "LastUpdateStatus": "Successful",
        "LastUpdateStatusReason": REASON,
        "EphemeralStorage": {"Size": 512},
        "Environment": {"Variables": environment},
        "RevisionId": revision,
        "Layers": [{"Arn": arn, "CodeSize": 1} for arn in layers],
    }
    return value


def record(role, response, operation=None, request=None, observed=FRESH):
    if operation is None:
        operation = "GetAlias" if role == "alias" else "GetFunctionConfiguration"
    return {
        "schema": rp.RECORD_SCHEMA,
        "role": role,
        "operation": operation,
        "request": request or {},
        "observed_utc": observed,
        "response": response,
    }


def alias_response(version="7", weights=None, revision="alias-rev-1", name="live"):
    value = {
        "AliasArn": f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{PROD}:{name}",
        "Name": name,
        "FunctionVersion": version,
        "Description": REASON,
        "RevisionId": revision,
    }
    if weights is not None:
        value["RoutingConfig"] = {"AdditionalVersionWeights": weights}
    return value


@pytest.fixture
def scenario(tmp_path):
    artifact_path = make_zip(tmp_path / "candidate.zip")
    artifact = describe(artifact_path)
    code = rp.hex_to_code_sha256(artifact["sha256"])
    plan = base_plan(artifact)
    records = {
        "production_baseline": record(
            "production_baseline",
            {
                "Configuration": configuration(
                    OLD_CODE, 1234, layers=[LAYER], revision="prod-rev-1"
                ),
                "Code": {"RepositoryType": "S3", "Location": LOCATION},
            },
            operation="GetFunction",
            request={"FunctionName": PROD},
        ),
        "candidate": record(
            "candidate",
            configuration(code, artifact["zip_bytes"], version="8"),
            request={"FunctionName": PROD, "Qualifier": "8"},
        ),
        "alias": record(
            "alias", alias_response(), request={"FunctionName": PROD, "Name": "live"}
        ),
        "rollback_target": record(
            "rollback_target",
            configuration(
                OLD_CODE, 1234, version="7", layers=[LAYER], revision="roll-rev-1"
            ),
            request={"FunctionName": PROD, "Qualifier": "7"},
        ),
    }
    return {
        "path": artifact_path,
        "plan": plan,
        "records": records,
        "code": code,
        "dir": tmp_path,
    }


def run(scenario, artifact=True, as_of=AS_OF):
    plan = rp.validate_plan(copy.deepcopy(scenario["plan"]))
    records = [
        rp.validate_record(copy.deepcopy(value), "0" * 64)
        for value in scenario["records"].values()
    ]
    return rp.evaluate(
        plan,
        records,
        scenario["path"] if artifact else None,
        rp.parse_time(as_of) if as_of else None,
    )


def codes(result, bucket="errors"):
    return {
        (entry["code"], entry["role"], entry.get("field")) for entry in result[bucket]
    }


def error_codes(result):
    return {entry["code"] for entry in result["errors"]}


def test_offline_guard_installed():
    assert offline_guard.is_installed()


def test_code_sha256_conversion_is_exact():
    empty = hashlib.sha256(b"").hexdigest()
    assert (
        rp.hex_to_code_sha256(empty) == "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="
    )
    assert (
        rp.code_sha256_to_hex("47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=") == empty
    )
    accepted = "46ace5c38c4cf24e131c01437419aa56244280e2e570a777ae2a0d5ff7cabed7"
    assert rp.code_sha256_to_hex(rp.hex_to_code_sha256(accepted)) == accepted
    for bad in (
        empty.upper(),
        empty[:-1],
        "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU",
        "47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU=",
        base64.b64encode(b"x" * 31).decode(),
        None,
    ):
        with pytest.raises(ValueError):
            if bad is not None and len(bad) == 64:
                rp.hex_to_code_sha256(bad)
            else:
                rp.code_sha256_to_hex(bad)


def test_complete_alias_pre_release_join_is_consistent(scenario):
    result = run(scenario)
    assert result["errors"] == [] and result["missing_or_stale_facts"] == []
    assert result["unresolved_decisions"] == []
    assert result["technical_status"] == "CONSISTENT_PENDING_EXTERNAL_GATES"
    assert result["release_authorized"] is False
    assert result["artifact"]["verification"] == "FILE_HASHED_MANIFEST_READ"
    assert result["artifact"]["expected_code_sha256"] == scenario["code"]
    assert result["alias"]["function_version"] == "7"
    assert result["rollback_target"]["version"] == "7"
    # The production layer is a planned removal, not an inconsistency.
    assert (
        "BASELINE_LAYERS_REMOVED_BY_PLAN",
        "production_baseline",
        "layers",
    ) in codes(result, "notices")
    assert result["production_baseline"]["planned_changes"]["layers"] == {
        "baseline": [LAYER],
        "intended": [],
    }
    assert ("ROLLBACK_DEPENDS_ON_LAYERS", "rollback_target", "layers") in codes(
        result, "notices"
    )
    assert all(fact["kind"] == "SAVED_RESPONSE" for fact in result["facts"])
    assert {fact["freshness"] for fact in result["facts"]} == {"WITHIN_MAX_AGE"}
    assert {fact["observed_utc"] for fact in result["facts"]} == {FRESH}
    assert set(result["separate_gates"]) == {
        "qualification",
        "independent_review",
        "owner_authorization",
    }


def test_post_release_alias_must_point_to_candidate(scenario):
    scenario["plan"]["release_strategy"]["phase"] = "post_release"
    assert error_codes(run(scenario)) == {"ALIAS_TARGET_VERSION_MISMATCH"}
    scenario["records"]["alias"]["response"]["FunctionVersion"] = "8"
    assert run(scenario)["errors"] == []


def test_unresolved_strategy_reports_decisions_not_acceptance(scenario):
    scenario["plan"] = base_plan(scenario["plan"]["artifact"], "unresolved", TEST_FN)
    candidate = configuration(
        scenario["code"], scenario["plan"]["artifact"]["zip_bytes"], function=TEST_FN
    )
    scenario["records"]["candidate"] = record(
        "candidate", candidate, request={"FunctionName": TEST_FN}
    )
    result = run(scenario)
    assert result["errors"] == []
    assert result["technical_status"] == "INCOMPLETE"
    assert {entry["code"] for entry in result["unresolved_decisions"]} == {
        "RELEASE_STRATEGY_UNRESOLVED",
        "ROLLBACK_TARGET_UNRESOLVED",
    }
    assert {entry["code"] for entry in result["notices"]} >= {
        "ALIAS_RECORD_NOT_EVALUATED_STRATEGY_UNRESOLVED",
        "ROLLBACK_RECORD_NOT_EVALUATED",
        "CANDIDATE_IS_UNPUBLISHED_LATEST",
        "BASELINE_LAYERS_REMOVED_BY_PLAN",
    }
    assert result["alias"] is None and result["rollback_target"] is None


def test_missing_records_and_artifact_are_reported(scenario):
    scenario["records"] = {"alias": scenario["records"]["alias"]}
    result = run(scenario, artifact=False)
    assert {entry["code"] for entry in result["missing_or_stale_facts"]} == {
        "ARTIFACT_FILE_NOT_VERIFIED",
        "PRODUCTION_BASELINE_MISSING",
        "CANDIDATE_RECORD_MISSING",
    }
    assert ("ROLLBACK_RECORD_MISSING", "rollback_target", None) in codes(result)
    assert result["artifact"]["verification"] == "NOT_SUPPLIED"
    assert result["technical_status"] == "BLOCKED"
    del scenario["records"]["alias"]
    scenario["plan"]["rollback"] = None
    result = run(scenario, artifact=False)
    assert ("ALIAS_RECORD_MISSING", "alias", None) in codes(
        result, "missing_or_stale_facts"
    )
    assert ("ROLLBACK_TARGET_MISSING", "rollback_target", "rollback") in codes(result)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("content", "ARTIFACT_SHA256_MISMATCH"),
        ("manifest", "MANIFEST_SHA256_MISMATCH"),
        ("no_manifest", "MANIFEST_MISSING"),
        ("target", "MANIFEST_TARGET_MISMATCH"),
        ("invalid_manifest", "MANIFEST_INVALID"),
        ("unreadable", "ARTIFACT_UNREADABLE"),
    ],
)
def test_artifact_identity_failures(scenario, mutation, code):
    path = scenario["path"]
    if mutation == "content":
        make_zip(path, extra=b"# changed\n")
    elif mutation == "manifest":
        make_zip(path, {**MANIFEST, "schema": "changed"})
    elif mutation == "no_manifest":
        make_zip(path, None)
    elif mutation == "target":
        make_zip(
            path,
            {**MANIFEST, "target": {**MANIFEST["target"], "architecture": "arm64"}},
        )
    elif mutation == "invalid_manifest":
        make_zip(path, {"schema": "invented"})
    else:
        path.write_bytes(b"not a zip")
    assert code in error_codes(run(scenario))


def test_duplicate_manifest_entry_is_not_trusted(scenario):
    with zipfile.ZipFile(scenario["path"], "a") as archive:
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr(rp.MANIFEST_NAME, b"{}")
    assert ("MANIFEST_INVALID", "artifact", None) in codes(run(scenario))


def test_artifact_size_mismatch(scenario):
    scenario["plan"]["artifact"]["zip_bytes"] += 1
    assert {"ARTIFACT_SIZE_MISMATCH", "CODE_SIZE_MISMATCH"} <= error_codes(
        run(scenario)
    )


def test_layer_contradictions(scenario):
    scenario["plan"]["intended_configuration"]["layers"] = [LAYER]
    result = run(scenario)
    assert ("LAYER_ALLOCATION_CONTRADICTION", "artifact", "layers") in codes(result)
    assert ("LAYER_MISMATCH", "candidate", "layers") in codes(result)
    scenario["plan"]["intended_configuration"]["layers"] = []
    scenario["records"]["candidate"]["response"]["Layers"] = [{"Arn": LAYER}]
    assert error_codes(run(scenario)) == {"LAYER_MISMATCH"}
    scenario["records"]["candidate"]["response"]["Layers"] = []
    make_zip(
        scenario["path"], {**MANIFEST, "layer_evidence": {"layers": [{"arn": LAYER}]}}
    )
    scenario["plan"]["artifact"] = describe(scenario["path"])
    candidate = scenario["records"]["candidate"]["response"]
    candidate["CodeSha256"] = rp.hex_to_code_sha256(
        scenario["plan"]["artifact"]["sha256"]
    )
    candidate["CodeSize"] = scenario["plan"]["artifact"]["zip_bytes"]
    assert error_codes(run(scenario)) == {"LAYER_ALLOCATION_CONTRADICTION"}


@pytest.mark.parametrize(
    "field,value,code,reported",
    [
        ("CodeSha256", OLD_CODE, "CODE_SHA256_MISMATCH", "CodeSha256"),
        ("CodeSha256", "not-base64", "CODE_SHA256_INVALID", "CodeSha256"),
        ("CodeSize", 1, "CODE_SIZE_MISMATCH", "CodeSize"),
        ("Architectures", ["arm64"], "CONFIGURATION_MISMATCH", "architectures"),
        ("Runtime", "python3.12", "CONFIGURATION_MISMATCH", "runtime"),
        ("Handler", "app.lambda_handler.handler", "CONFIGURATION_MISMATCH", "handler"),
        ("MemorySize", 1024, "CONFIGURATION_MISMATCH", "memory_size"),
        ("Timeout", 60, "CONFIGURATION_MISMATCH", "timeout"),
        (
            "EphemeralStorage",
            {"Size": 1024},
            "CONFIGURATION_MISMATCH",
            "ephemeral_storage",
        ),
        ("State", "Pending", "CANDIDATE_NOT_ACTIVE", "State"),
        (
            "LastUpdateStatus",
            "InProgress",
            "CANDIDATE_UPDATE_NOT_SUCCESSFUL",
            "LastUpdateStatus",
        ),
        ("RevisionId", None, "REVISION_ID_MISSING", "RevisionId"),
        ("RevisionId", "other-rev", "REVISION_MISMATCH", "RevisionId"),
    ],
)
def test_candidate_configuration_failures(scenario, field, value, code, reported):
    candidate = scenario["records"]["candidate"]["response"]
    if value is None:
        del candidate[field]
    else:
        candidate[field] = value
    result = run(scenario)
    assert (code, "candidate", reported) in codes(result)
    assert result["technical_status"] == "BLOCKED"


@pytest.mark.parametrize(
    "arn,code",
    [
        (
            f"arn:aws:lambda:{REGION}:210987654321:function:{PROD}:8",
            "FUNCTION_IDENTITY_MISMATCH",
        ),
        (
            f"arn:aws:lambda:us-west-2:{ACCOUNT}:function:{PROD}:8",
            "FUNCTION_IDENTITY_MISMATCH",
        ),
        (
            f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:other:8",
            "FUNCTION_IDENTITY_MISMATCH",
        ),
        (
            f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{PROD}:9",
            "RECORD_REQUEST_RESPONSE_MISMATCH",
        ),
        ("not-an-arn", "FUNCTION_ARN_INVALID"),
    ],
)
def test_identity_joins(scenario, arn, code):
    scenario["records"]["candidate"]["response"]["FunctionArn"] = arn
    assert code in error_codes(run(scenario))


def test_candidate_version_must_match_strategy(scenario):
    candidate = scenario["records"]["candidate"]
    candidate["response"]["Version"] = "9"
    candidate["response"]["FunctionArn"] = (
        candidate["response"]["FunctionArn"][:-1] + "9"
    )
    candidate["request"]["Qualifier"] = "9"
    assert error_codes(run(scenario)) == {"CANDIDATE_VERSION_MISMATCH"}


@pytest.mark.parametrize(
    "mutation,code,field",
    [
        ("not_dict", "RESPONSE_MALFORMED", None),
        ("no_configuration", "RESPONSE_MALFORMED", "Configuration"),
        ("missing_field", "RESPONSE_FIELD_MISSING", "Handler"),
        ("bool_memory", "RESPONSE_FIELD_INVALID", "MemorySize"),
        ("bad_version", "RESPONSE_FIELD_INVALID", "Version"),
        ("bad_layers", "RESPONSE_FIELD_INVALID", "Layers"),
        ("bad_environment", "RESPONSE_FIELD_INVALID", "Environment"),
    ],
)
def test_malformed_responses(scenario, mutation, code, field):
    baseline = scenario["records"]["production_baseline"]
    configuration_value = baseline["response"]["Configuration"]
    if mutation == "not_dict":
        baseline["response"] = ["invented"]
    elif mutation == "no_configuration":
        del baseline["response"]["Configuration"]
    elif mutation == "missing_field":
        del configuration_value["Handler"]
    elif mutation == "bool_memory":
        configuration_value["MemorySize"] = True
    elif mutation == "bad_version":
        configuration_value["Version"] = "v1"
    elif mutation == "bad_layers":
        configuration_value["Layers"] = ["arn"]
    else:
        configuration_value["Environment"] = {"Variables": {"A": 1}}
    result = run(scenario)
    assert (code, "production_baseline", field) in codes(result)
    assert result["production_baseline"] is None


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("version", "ALIAS_TARGET_VERSION_MISMATCH"),
        ("latest", "ALIAS_TARGETS_UNPUBLISHED_VERSION"),
        ("weights", "UNEXPECTED_WEIGHTED_ROUTING"),
        ("bad_weights", "ROUTING_WEIGHTS_INVALID"),
        ("primary_weight", "ROUTING_WEIGHTS_INVALID"),
        ("name", "ALIAS_NAME_MISMATCH"),
        ("account", "ALIAS_IDENTITY_MISMATCH"),
        ("numeric_arn", "ALIAS_ARN_INVALID"),
        ("no_revision", "ALIAS_REVISION_ID_MISSING"),
        ("revision", "ALIAS_REVISION_MISMATCH"),
        ("plan_revision", "PLAN_ALIAS_REVISION_ID_MISSING"),
        ("missing", "RESPONSE_FIELD_MISSING"),
    ],
)
def test_alias_failures(scenario, mutation, code):
    alias = scenario["records"]["alias"]["response"]
    if mutation == "version":
        alias["FunctionVersion"] = "6"
    elif mutation == "latest":
        alias["FunctionVersion"] = "$LATEST"
    elif mutation == "weights":
        alias["RoutingConfig"] = {"AdditionalVersionWeights": {"8": 0.1}}
    elif mutation == "bad_weights":
        alias["RoutingConfig"] = {"AdditionalVersionWeights": {"8": 1.5}}
    elif mutation == "primary_weight":
        alias["RoutingConfig"] = {"AdditionalVersionWeights": {"7": 0.1}}
    elif mutation == "name":
        scenario["plan"]["release_strategy"]["alias_name"] = "other"
    elif mutation == "account":
        alias["AliasArn"] = alias["AliasArn"].replace(ACCOUNT, "210987654321")
    elif mutation == "numeric_arn":
        alias["AliasArn"] = alias["AliasArn"].rsplit(":", 1)[0] + ":7"
    elif mutation == "no_revision":
        del alias["RevisionId"]
    elif mutation == "revision":
        alias["RevisionId"] = "alias-rev-2"
    elif mutation == "plan_revision":
        scenario["plan"]["release_strategy"]["expected_alias_revision_id"] = None
    else:
        del alias["FunctionVersion"]
    result = run(scenario)
    assert code in error_codes(result)
    assert result["technical_status"] == "BLOCKED"


def test_planned_weighted_routing_must_match_exactly(scenario):
    scenario["plan"]["release_strategy"]["additional_version_weights"] = {"8": 0.1}
    assert error_codes(run(scenario)) == {"ROUTING_WEIGHTS_MISMATCH"}
    alias = scenario["records"]["alias"]["response"]
    alias["RoutingConfig"] = {"AdditionalVersionWeights": {"8": 0.2}}
    assert error_codes(run(scenario)) == {"ROUTING_WEIGHTS_MISMATCH"}
    alias["RoutingConfig"] = {"AdditionalVersionWeights": {"8": 0.1}}
    assert run(scenario)["errors"] == []


def test_stale_and_future_snapshots(scenario):
    scenario["records"]["alias"]["observed_utc"] = "2026-10-05T11:00:00+00:00"
    result = run(scenario)
    assert ("FACT_STALE", "alias", "observed_utc") in codes(
        result, "missing_or_stale_facts"
    )
    assert result["errors"] == [] and result["technical_status"] == "INCOMPLETE"
    stale = [fact for fact in result["facts"] if fact["role"] == "alias"][0]
    assert stale["freshness"] == "STALE" and stale["observed_utc"].startswith(
        "2026-10-05"
    )
    scenario["records"]["alias"]["observed_utc"] = "2026-10-06T13:00:00Z"
    assert ("FACT_TIMESTAMP_IN_FUTURE", "alias", "observed_utc") in codes(run(scenario))
    clocked = run(scenario, as_of=None)
    assert clocked["evaluated_at_source"] == "HOST_CLOCK"


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("latest", "ROLLBACK_TARGET_NOT_IMMUTABLE"),
        ("alias_name", "ROLLBACK_TARGET_NOT_IMMUTABLE"),
        ("record_missing", "ROLLBACK_RECORD_MISSING"),
        ("version", "ROLLBACK_VERSION_MISMATCH"),
        ("code", "ROLLBACK_CODE_SHA256_MISMATCH"),
        ("candidate_version", "ROLLBACK_EQUALS_CANDIDATE"),
        ("inactive", "ROLLBACK_TARGET_NOT_ACTIVE"),
        ("revision", "REVISION_MISMATCH"),
        ("bad_code", "CODE_SHA256_INVALID"),
        ("other_function", "FUNCTION_IDENTITY_MISMATCH"),
    ],
)
def test_rollback_bindings(scenario, mutation, code):
    rollback = scenario["plan"]["rollback"]
    response = scenario["records"]["rollback_target"]["response"]
    if mutation == "latest":
        rollback["function_version"] = "$LATEST"
    elif mutation == "alias_name":
        rollback["function_version"] = "live"
    elif mutation == "record_missing":
        del scenario["records"]["rollback_target"]
    elif mutation == "version":
        response["Version"] = "6"
        response["FunctionArn"] = response["FunctionArn"][:-1] + "6"
        scenario["records"]["rollback_target"]["request"]["Qualifier"] = "6"
    elif mutation == "code":
        response["CodeSha256"] = scenario["code"].replace(scenario["code"][0], "A", 1)
    elif mutation == "candidate_version":
        rollback["function_version"] = "8"
    elif mutation == "inactive":
        response["State"] = "Inactive"
    elif mutation == "revision":
        response["RevisionId"] = "roll-rev-2"
    elif mutation == "bad_code":
        rollback["code_sha256"] = "abc"
    else:
        response["FunctionArn"] = response["FunctionArn"].replace(PROD, TEST_FN)
    result = run(scenario)
    assert (code, "rollback_target") in {
        (e["code"], e["role"]) for e in result["errors"]
    }
    assert result["technical_status"] == "BLOCKED"


@pytest.mark.parametrize(
    "variables,code,field",
    [
        (
            {"COPILOT_ROUTER_PROVIDER": "jev"},
            "ROUTER_PROVIDER_NOT_HAIKU",
            "COPILOT_ROUTER_PROVIDER",
        ),
        (
            {"AWS_SECRET_ACCESS_KEY": "invented"},
            "CREDENTIAL_IN_ENVIRONMENT",
            "AWS_SECRET_ACCESS_KEY",
        ),
        ({"UNLISTED_NAME": "x"}, "ENVIRONMENT_UNEXPECTED_NAME", "UNLISTED_NAME"),
        ({"bad name": "x"}, "ENVIRONMENT_UNEXPECTED_NAME", "UNPRINTABLE_NAME"),
        (
            {"EVALUATE_ENDPOINT_TOKEN": "wrong"},
            "ENVIRONMENT_EXPECTATION_FAILED",
            "EVALUATE_ENDPOINT_TOKEN",
        ),
        (
            {"BEDROCK_MODEL_ID": "invented-model"},
            "ENVIRONMENT_EXPECTATION_FAILED",
            "BEDROCK_MODEL_ID",
        ),
    ],
)
def test_environment_checks_never_print_values(
    scenario, capsys, variables, code, field, tmp_path
):
    environment = scenario["records"]["candidate"]["response"]["Environment"][
        "Variables"
    ]
    environment.update(variables)
    if code == "ROUTER_PROVIDER_NOT_HAIKU":
        scenario["plan"]["intended_configuration"]["environment"]["variables"].pop(
            "COPILOT_ROUTER_PROVIDER"
        )
        scenario["plan"]["intended_configuration"]["environment"]["allow_unlisted"] = (
            True
        )
    result = run(scenario)
    assert (code, "candidate", field) in codes(result)
    assert rp.main(cli_args(scenario, tmp_path)) == 1
    output = capsys.readouterr()
    printed = output.out + output.err
    assert SECRET not in printed
    # Exact JSON strings: short values such as "jev" also occur inside schema names.
    for value in ["invented-model", "wrong", *variables.values()]:
        assert json.dumps(value) not in printed


def test_environment_error_and_missing_expectation(scenario):
    environment = scenario["records"]["candidate"]["response"]["Environment"]
    environment["Error"] = {"ErrorCode": "invented", "Message": REASON}
    del environment["Variables"]["EVALUATE_ENDPOINT_TOKEN"]
    found = codes(run(scenario))
    assert ("ENVIRONMENT_ERROR_REPORTED", "candidate", "Environment") in found
    assert (
        "ENVIRONMENT_EXPECTATION_FAILED",
        "candidate",
        "EVALUATE_ENDPOINT_TOKEN",
    ) in found


def cli_args(scenario, tmp_path, artifact=True):
    folder = tmp_path / "cli"
    folder.mkdir(exist_ok=True)
    plan = folder / "plan.json"
    plan.write_text(json.dumps(scenario["plan"]))
    args = ["--plan", str(plan), "--as-of", AS_OF]
    for role, value in scenario["records"].items():
        path = folder / (role + ".json")
        path.write_text(json.dumps(value))
        args += ["--record", str(path)]
    if artifact:
        args += ["--artifact", str(scenario["path"])]
    return args


def test_cli_success_is_sanitized_and_read_only(scenario, tmp_path, capsys):
    args = cli_args(scenario, tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert rp.main(args) == 0
    output = capsys.readouterr()
    assert output.err == ""
    result = json.loads(output.out)
    assert result["technical_status"] == "CONSISTENT_PENDING_EXTERNAL_GATES"
    assert (
        result["plan_sha256"]
        == hashlib.sha256((tmp_path / "cli/plan.json").read_bytes()).hexdigest()
    )
    for secret in (SECRET, LOCATION, "presigned", REASON, "role/invented"):
        assert secret not in output.out
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_external_gate_references_are_not_authentication(scenario, tmp_path, capsys):
    digest = "a" * 64
    scenario["plan"]["external_gates"] = {
        "qualification": {"label": "invented-qualification", "sha256": digest},
        "owner_authorization": {"label": "invented-approval", "sha256": digest},
    }
    result = run(scenario)
    assert result["technical_status"] == "CONSISTENT_PENDING_EXTERNAL_GATES"
    assert result["release_authorized"] is False
    assert (
        result["separate_gates"]["owner_authorization"]["status"]
        == "REFERENCED_NOT_AUTHENTICATED"
    )
    assert result["separate_gates"]["independent_review"]["status"] == "NOT_SUPPLIED"
    assert "HASH_AGREEMENT_DOES_NOT_AUTHENTICATE_APPROVAL" in result["limitations"]


@pytest.mark.parametrize(
    "case,code",
    [
        ("duplicate_key", "INPUT_DUPLICATE_KEY"),
        ("nan", "INPUT_NONFINITE_NUMBER"),
        ("not_json", "INPUT_NOT_JSON"),
        ("missing_file", "INPUT_UNREADABLE"),
        ("plan_schema", "PLAN_INVALID"),
        ("unknown_environment_name", "PLAN_INVALID"),
        ("secret_equals", "PLAN_INVALID"),
        ("jev_provider", "PLAN_INVALID"),
        ("plan_weights", "PLAN_INVALID"),
        ("alias_other_function", "PLAN_INVALID"),
        ("record_schema", "RECORD_INVALID"),
        ("record_operation", "RECORD_INVALID"),
        ("record_time", "RECORD_INVALID"),
        ("duplicate_role", "RECORD_DUPLICATE_ROLE"),
        ("as_of", "AS_OF_INVALID"),
    ],
)
def test_input_contract_rejections(scenario, tmp_path, capsys, case, code):
    variables = scenario["plan"]["intended_configuration"]["environment"]["variables"]
    if case == "plan_schema":
        scenario["plan"]["schema"] = "other"
    elif case == "unknown_environment_name":
        variables["INVENTED_SETTING"] = {"expect": "absent"}
    elif case == "secret_equals":
        variables["EVALUATE_ENDPOINT_TOKEN"] = {"expect": "equals", "value": SECRET}
    elif case == "jev_provider":
        variables["COPILOT_ROUTER_PROVIDER"] = {"expect": "equals", "value": "jev"}
    elif case == "plan_weights":
        scenario["plan"]["release_strategy"]["additional_version_weights"] = {"6": 1.0}
    elif case == "alias_other_function":
        scenario["plan"]["candidate_function"] = TEST_FN
    elif case == "record_schema":
        scenario["records"]["alias"]["schema"] = "other"
    elif case == "record_operation":
        scenario["records"]["alias"]["operation"] = "GetFunction"
    elif case == "record_time":
        scenario["records"]["alias"]["observed_utc"] = "2026-10-06T11:50:00"
    args = cli_args(scenario, tmp_path)
    plan = tmp_path / "cli/plan.json"
    if case == "duplicate_key":
        plan.write_text('{"schema": "a", "schema": "b"}')
    elif case == "nan":
        plan.write_text('{"schema": NaN}')
    elif case == "not_json":
        plan.write_bytes(b"\xff\xfe")
    elif case == "missing_file":
        plan.unlink()
    elif case == "duplicate_role":
        args += ["--record", str(tmp_path / "cli/alias.json")]
    elif case == "as_of":
        args[args.index("--as-of") + 1] = "yesterday"
    assert rp.main(args) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err) == {"status": "INPUT_REJECTED", "code": code}
    assert SECRET not in output.err


def test_every_emitted_code_is_registered(scenario):
    registered = rp.ERROR_CODES | rp.MISSING_CODES | rp.DECISION_CODES | rp.NOTICE_CODES
    findings = rp.Findings()
    with pytest.raises(AssertionError):
        findings.error("NOT_A_REGISTERED_CODE")
    source = Path(rp.__file__).read_text()
    literals = {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.isupper()
        and "_" in node.value
    }
    assert registered <= literals
    assert not (rp.ERROR_CODES & rp.MISSING_CODES)


def test_module_has_no_aws_network_subprocess_or_write_paths():
    tree = ast.parse(Path(rp.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    assert imported == {
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
        "zipfile",
        "zlib",
    }
    calls = {
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else getattr(node.func, "id", "")
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert not calls & {
        "write_bytes",
        "write_text",
        "unlink",
        "mkdir",
        "extractall",
        "extract",
        "system",
        "remove",
        "rename",
        "replace_file",
    }
    opens = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "open"
    ]
    assert all(
        [arg.value for arg in node.args if isinstance(arg, ast.Constant)]
        in ([], ["rb"])
        for node in opens
    )


# ---- Correction batch: Codex review RP-1 to RP-7 -------------------------------


def as_version(response, version):
    """Make a saved configuration describe one numeric version of its function."""
    response = copy.deepcopy(response)
    response["Version"] = version
    base = response["FunctionArn"].split(":function:")[0]
    response["FunctionArn"] = f"{base}:function:{response['FunctionName']}:{version}"
    return response


def baseline_as(scenario, response, version):
    scenario["records"]["production_baseline"] = record(
        "production_baseline",
        as_version(response, version),
        request={"FunctionName": PROD, "Qualifier": version},
    )


def test_rp1_conflicting_facts_about_one_immutable_version_block(scenario):
    rollback = scenario["records"]["rollback_target"]["response"]
    conflicting = copy.deepcopy(rollback)
    conflicting["CodeSha256"] = scenario["code"]
    baseline_as(scenario, conflicting, "7")
    found = codes(run(scenario))
    assert ("IMMUTABLE_VERSION_CONFLICT", "rollback_target", "CodeSha256") in found
    candidate = scenario["records"]["candidate"]["response"]
    conflicting = copy.deepcopy(candidate)
    conflicting["CodeSha256"] = OLD_CODE
    baseline_as(scenario, conflicting, "8")
    assert ("IMMUTABLE_VERSION_CONFLICT", "candidate", "CodeSha256") in codes(
        run(scenario)
    )
    conflicting = copy.deepcopy(rollback)
    conflicting["MemorySize"] = 1024
    baseline_as(scenario, conflicting, "7")
    assert ("IMMUTABLE_VERSION_CONFLICT", "rollback_target", "memory_size") in codes(
        run(scenario)
    )


def test_rp1_agreeing_version_and_mutable_latest_snapshots_do_not_conflict(scenario):
    rollback = scenario["records"]["rollback_target"]["response"]
    baseline_as(scenario, rollback, "7")
    assert run(scenario)["errors"] == []
    baseline = scenario["records"]["production_baseline"]
    baseline["request"] = {"FunctionName": PROD}
    baseline["response"] = configuration(
        rp.hex_to_code_sha256("1" * 64), 99, environment={"S3_BUCKET_NAME": "x"}
    )
    assert run(scenario)["errors"] == []


def test_rp1_baseline_code_hash_is_validated(scenario):
    configuration_value = scenario["records"]["production_baseline"]["response"]
    configuration_value["Configuration"]["CodeSha256"] = "not-base64"
    result = run(scenario)
    assert ("CODE_SHA256_INVALID", "production_baseline", "CodeSha256") in codes(result)
    assert result["technical_status"] == "BLOCKED"


@pytest.mark.parametrize(
    "observed,planned",
    [({"9": 0.1}, {"9": 0.1}), ({"8": 0.1, "9": 0.1}, {"8": 0.1})],
)
def test_rp1_weighted_targets_must_be_the_other_verified_version(
    scenario, observed, planned
):
    scenario["plan"]["release_strategy"]["additional_version_weights"] = planned
    scenario["records"]["alias"]["response"]["RoutingConfig"] = {
        "AdditionalVersionWeights": observed
    }
    result = run(scenario)
    assert ("ROUTING_TARGET_UNSUPPORTED", "alias", "RoutingConfig") in codes(result)
    assert result["technical_status"] == "BLOCKED"


def test_rp1_two_planned_targets_are_rejected(scenario):
    scenario["plan"]["release_strategy"]["additional_version_weights"] = {
        "8": 0.1,
        "9": 0.1,
    }
    with pytest.raises(rp.InputError, match="PLAN_INVALID"):
        rp.validate_plan(scenario["plan"])


def test_rp1_post_release_weight_to_verified_rollback_is_consistent(scenario):
    strategy = scenario["plan"]["release_strategy"]
    strategy["phase"] = "post_release"
    strategy["additional_version_weights"] = {"7": 0.1}
    alias = scenario["records"]["alias"]["response"]
    alias["FunctionVersion"] = "8"
    alias["RoutingConfig"] = {"AdditionalVersionWeights": {"7": 0.1}}
    result = run(scenario)
    assert result["errors"] == []
    assert result["technical_status"] == "CONSISTENT_PENDING_EXTERNAL_GATES"


@pytest.mark.parametrize("role", ["production_baseline", "rollback_target"])
@pytest.mark.parametrize(
    "mutation,code,field",
    [
        ("error", "ENVIRONMENT_ERROR_REPORTED", "Environment"),
        ("provider", "ROUTER_PROVIDER_NOT_HAIKU", "COPILOT_ROUTER_PROVIDER"),
        ("credential", "CREDENTIAL_IN_ENVIRONMENT", "AWS_SESSION_TOKEN"),
    ],
)
def test_rp2_environment_safety_applies_to_every_function_role(
    scenario, role, mutation, code, field
):
    response = scenario["records"][role]["response"]
    if role == "production_baseline":
        response = response["Configuration"]
    environment = response["Environment"]
    if mutation == "error":
        environment["Error"] = {"ErrorCode": "invented", "Message": REASON}
    elif mutation == "provider":
        environment["Variables"]["COPILOT_ROUTER_PROVIDER"] = "jev"
    else:
        environment["Variables"]["AWS_SESSION_TOKEN"] = "invented"
    result = run(scenario)
    assert (code, role, field) in codes(result)
    assert result["technical_status"] == "BLOCKED"


def test_rp2_baseline_and_rollback_may_differ_from_intended_environment(scenario):
    old = {"S3_BUCKET_NAME": "invented-bucket", "COPILOT_ROUTER_PROVIDER": "haiku"}
    scenario["records"]["rollback_target"]["response"]["Environment"]["Variables"] = old
    baseline = scenario["records"]["production_baseline"]["response"]
    baseline["Configuration"]["Environment"]["Variables"] = dict(old)
    result = run(scenario)
    assert result["errors"] == []
    assert result["technical_status"] == "CONSISTENT_PENDING_EXTERNAL_GATES"


def test_rp3_configuration_only_rollback_with_identical_code_is_permitted(scenario):
    rollback = scenario["records"]["rollback_target"]["response"]
    rollback["CodeSha256"] = scenario["code"]
    rollback["CodeSize"] = scenario["plan"]["artifact"]["zip_bytes"]
    scenario["plan"]["rollback"]["code_sha256"] = scenario["code"]
    result = run(scenario)
    assert result["errors"] == []
    notice = ("ROLLBACK_CODE_MATCHES_CANDIDATE", "rollback_target", "code_sha256")
    assert notice in codes(result, "notices")
    assert result["technical_status"] == "CONSISTENT_PENDING_EXTERNAL_GATES"


def test_rp3_distinct_function_identities_with_equal_versions(scenario):
    scenario["plan"] = base_plan(scenario["plan"]["artifact"], "unresolved", TEST_FN)
    scenario["plan"]["rollback"] = {"function_version": "7", "code_sha256": OLD_CODE}
    candidate = configuration(
        scenario["code"],
        scenario["plan"]["artifact"]["zip_bytes"],
        version="7",
        function=TEST_FN,
    )
    scenario["records"]["candidate"] = record(
        "candidate", candidate, request={"FunctionName": TEST_FN, "Qualifier": "7"}
    )
    del scenario["records"]["alias"]
    result = run(scenario)
    assert result["errors"] == []
    assert result["technical_status"] == "INCOMPLETE"
    assert {entry["code"] for entry in result["unresolved_decisions"]} == {
        "RELEASE_STRATEGY_UNRESOLVED"
    }


def test_rp3_same_qualified_candidate_version_is_still_rejected(scenario):
    scenario["plan"]["rollback"]["function_version"] = "8"
    assert "ROLLBACK_EQUALS_CANDIDATE" in error_codes(run(scenario))


def rebind_candidate_to_artifact(scenario):
    scenario["plan"]["artifact"] = describe(scenario["path"])
    candidate = scenario["records"]["candidate"]["response"]
    candidate["CodeSha256"] = rp.hex_to_code_sha256(
        scenario["plan"]["artifact"]["sha256"]
    )
    candidate["CodeSize"] = scenario["plan"]["artifact"]["zip_bytes"]


def test_rp4_manifest_allocation_evidence_is_required(scenario):
    make_zip(
        scenario["path"],
        {key: value for key, value in MANIFEST.items() if key != "packaging_policy"},
    )
    rebind_candidate_to_artifact(scenario)
    result = run(scenario)
    assert error_codes(result) == {"MANIFEST_INVALID"}
    assert result["technical_status"] == "BLOCKED"


@pytest.mark.parametrize(
    "declared,intended",
    [
        ([LAYER.replace(":2", ":3")], [LAYER]),
        ([LAYER, LAYER + "0"], [LAYER + "0", LAYER]),
    ],
)
def test_rp4_declared_layer_bindings_and_order_must_match(scenario, declared, intended):
    legacy = {
        **MANIFEST,
        "packaging_policy": {"dependency_allocation": "LEGACY_UNRESOLVED"},
        "layer_evidence": {"layers": [{"arn": arn} for arn in declared]},
    }
    make_zip(scenario["path"], legacy)
    rebind_candidate_to_artifact(scenario)
    scenario["plan"]["intended_configuration"]["layers"] = intended
    result = run(scenario)
    assert ("LAYER_ALLOCATION_CONTRADICTION", "artifact", "layers") in codes(result)
    assert ("MANIFEST_ALLOCATION_UNSUPPORTED", "artifact", "allocation") in codes(
        result
    )


@pytest.mark.parametrize(
    "role,request_value,code",
    [
        ("candidate", {}, "RECORD_REQUEST_INVALID"),
        ("alias", {"FunctionName": PROD}, "RECORD_REQUEST_INVALID"),
        (
            "candidate",
            {"FunctionName": PROD, "Qualifier": "8", "Name": "live"},
            "RECORD_REQUEST_INVALID",
        ),
        ("candidate", {"FunctionName": PROD, "Qualifier": 8}, "RECORD_REQUEST_INVALID"),
        (
            "candidate",
            {"FunctionName": f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{PROD}:8"},
            "RECORD_REQUEST_UNSUPPORTED",
        ),
        (
            "candidate",
            {"FunctionName": PROD, "Qualifier": "live"},
            "RECORD_REQUEST_UNSUPPORTED",
        ),
    ],
)
def test_rp5_operation_specific_request_contract(
    scenario, tmp_path, capsys, role, request_value, code
):
    scenario["records"][role]["request"] = request_value
    assert rp.main(cli_args(scenario, tmp_path)) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err) == {"status": "INPUT_REJECTED", "code": code}


def test_rp5_unqualified_request_must_return_latest(scenario):
    del scenario["records"]["candidate"]["request"]["Qualifier"]
    found = codes(run(scenario))
    assert ("RECORD_REQUEST_RESPONSE_MISMATCH", "candidate", "Qualifier") in found


@pytest.mark.parametrize(
    "routing",
    [
        [],
        False,
        0,
        "",
        None,
        {"AdditionalVersionWeights": []},
        {"AdditionalVersionWeights": None},
        {"AdditionalVersionWeights": "8"},
        {"AdditionalVersionWeights": False},
    ],
)
def test_rp6_present_malformed_routing_is_rejected(scenario, routing):
    scenario["records"]["alias"]["response"]["RoutingConfig"] = routing
    result = run(scenario)
    assert ("ROUTING_WEIGHTS_INVALID", "alias", "RoutingConfig") in codes(result)
    assert result["technical_status"] == "BLOCKED"


@pytest.mark.parametrize("routing", ["absent", {}, {"AdditionalVersionWeights": {}}])
def test_rp6_absent_or_empty_routing_remains_valid(scenario, routing):
    alias = scenario["records"]["alias"]["response"]
    if routing == "absent":
        alias.pop("RoutingConfig", None)
    else:
        alias["RoutingConfig"] = routing
    assert run(scenario)["errors"] == []


@pytest.mark.parametrize(
    "case,code",
    [
        ("exponent_overflow", "INPUT_NONFINITE_NUMBER"),
        ("huge_integer", "INPUT_NUMBER_OUT_OF_RANGE"),
        ("unpaired_surrogate", "INPUT_INVALID_UNICODE"),
        ("record_time_overflow", "RECORD_INVALID"),
        ("as_of_overflow", "AS_OF_INVALID"),
    ],
)
def test_rp7_boundary_inputs_are_sanitized_rejections(
    scenario, tmp_path, capsys, case, code
):
    args = cli_args(scenario, tmp_path)
    alias_path = tmp_path / "cli/alias.json"
    text = alias_path.read_text()
    if case == "exponent_overflow":
        alias_path.write_text(text[:-1] + ', "ignored": 1e400}')
    elif case == "huge_integer":
        alias_path.write_text(text[:-1] + ', "ignored": ' + "9" * 80 + "}")
    elif case == "unpaired_surrogate":
        alias_path.write_text(text[:-1] + ', "ignored": "\\ud800"}')
    elif case == "record_time_overflow":
        value = json.loads(text)
        value["observed_utc"] = "9999-12-31T23:00:00-23:00"
        alias_path.write_text(json.dumps(value))
    else:
        args[args.index("--as-of") + 1] = "9999-12-31T23:00:00-23:00"
    assert rp.main(args) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err) == {"status": "INPUT_REJECTED", "code": code}


def test_rp7_unpaired_surrogate_in_environment_value(scenario, tmp_path, capsys):
    args = cli_args(scenario, tmp_path)
    candidate_path = tmp_path / "cli/candidate.json"
    text = candidate_path.read_text()
    assert json.dumps(SECRET) in text
    candidate_path.write_text(text.replace(json.dumps(SECRET), '"\\udc80"'))
    assert rp.main(args) == 2
    assert json.loads(capsys.readouterr().err)["code"] == "INPUT_INVALID_UNICODE"


def stored_zip(path, manifest_raw, encrypted=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr(rp.MANIFEST_NAME, manifest_raw)
    data = bytearray(buffer.getvalue())
    if encrypted:
        # zipfile clears this flag on write; set it in the local (offset 6) and
        # central (offset 8) headers as an encrypted entry would carry it.
        data[6] |= 0x1
        data[data.index(b"PK\x01\x02") + 8] |= 0x1
    path.write_bytes(bytes(data))


@pytest.mark.parametrize("mode", ["encrypted", "crc"])
def test_rp7_unreadable_manifest_is_a_fixed_code(scenario, mode):
    raw = rp.canonical(MANIFEST).encode()
    stored_zip(scenario["path"], raw, encrypted=mode == "encrypted")
    if mode == "crc":
        data = scenario["path"].read_bytes()
        position = data.index(raw) + 5
        flipped = bytes([data[position] ^ 0x01])
        scenario["path"].write_bytes(data[:position] + flipped + data[position + 1 :])
    result = run(scenario)
    assert ("MANIFEST_UNREADABLE", "artifact", None) in codes(result)
    assert result["technical_status"] == "BLOCKED"
