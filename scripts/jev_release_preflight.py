"""Read-only Lambda release preflight over explicitly supplied local records.

Consumes one release plan, saved AWS Lambda responses (each wrapped with its
role, request and observation time) and, optionally, the local artifact ZIP.
It never calls AWS, uploads, installs, runs subprocesses or writes files; the
only output is a sanitized JSON result on stdout (input errors on stderr).

Technical consistency is reported separately from qualification evidence,
independent review and owner authorization. Hash agreement never
authenticates an approval, and a saved response is never a current
observation: every fact carries its own timestamp and age.
"""

import argparse
import base64
import binascii
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import zipfile

PLAN_SCHEMA = "jev-release-plan-v1"
RECORD_SCHEMA = "jev-saved-aws-response-v1"
RESULT_SCHEMA = "jev-release-preflight-result-v1"
MANIFEST_NAME = "lambda-build-manifest.json"
MANIFEST_MAX_BYTES = 4 * 1024 * 1024
COMPLETE_FUNCTION_ALLOCATION = "complete-function-no-layers"
FUTURE_SKEW_SECONDS = 300
ROLES = ("production_baseline", "candidate", "alias", "rollback_target")
FUNCTION_OPERATIONS = ("GetFunction", "GetFunctionConfiguration")
HAIKU_PROVIDER = "haiku"

# Environment names the application actually reads (app/, excluding the
# offline indexing script). Values are never printed.
APP_ENVIRONMENT = {
    "BEDROCK_MODEL_ID": "plain",
    "S3_BUCKET_NAME": "plain",
    "FAISS_INDEX_S3_KEY": "plain",
    "FAISS_META_S3_KEY": "plain",
    "COPILOT_ROUTER_PROVIDER": "plain",
    "COPILOT_CW_REQUEST_LOG": "plain",
    "ENABLE_EVALUATE_ENDPOINT": "plain",
    "EVALUATE_ENDPOINT_TOKEN": "secret",
}
CREDENTIAL_ENVIRONMENT = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
)

ERROR_CODES = frozenset(
    {
        "ALIAS_ARN_INVALID",
        "ALIAS_IDENTITY_MISMATCH",
        "ALIAS_NAME_MISMATCH",
        "ALIAS_REVISION_ID_MISSING",
        "ALIAS_REVISION_MISMATCH",
        "ALIAS_TARGETS_UNPUBLISHED_VERSION",
        "ALIAS_TARGET_VERSION_MISMATCH",
        "ARTIFACT_SHA256_MISMATCH",
        "ARTIFACT_SIZE_MISMATCH",
        "ARTIFACT_UNREADABLE",
        "CANDIDATE_NOT_ACTIVE",
        "CANDIDATE_UPDATE_NOT_SUCCESSFUL",
        "CANDIDATE_VERSION_MISMATCH",
        "CODE_SHA256_INVALID",
        "CODE_SHA256_MISMATCH",
        "CODE_SIZE_MISMATCH",
        "CONFIGURATION_MISMATCH",
        "CREDENTIAL_IN_ENVIRONMENT",
        "ENVIRONMENT_ERROR_REPORTED",
        "ENVIRONMENT_EXPECTATION_FAILED",
        "ENVIRONMENT_UNEXPECTED_NAME",
        "FACT_TIMESTAMP_IN_FUTURE",
        "FUNCTION_ARN_INVALID",
        "FUNCTION_IDENTITY_MISMATCH",
        "LAYER_ALLOCATION_CONTRADICTION",
        "LAYER_MISMATCH",
        "MANIFEST_INVALID",
        "MANIFEST_MISSING",
        "MANIFEST_SHA256_MISMATCH",
        "MANIFEST_TARGET_MISMATCH",
        "PLAN_ALIAS_REVISION_ID_MISSING",
        "RECORD_REQUEST_RESPONSE_MISMATCH",
        "RESPONSE_FIELD_INVALID",
        "RESPONSE_FIELD_MISSING",
        "RESPONSE_MALFORMED",
        "REVISION_ID_MISSING",
        "REVISION_MISMATCH",
        "ROLLBACK_CODE_EQUALS_CANDIDATE",
        "ROLLBACK_CODE_SHA256_MISMATCH",
        "ROLLBACK_EQUALS_CANDIDATE",
        "ROLLBACK_RECORD_MISSING",
        "ROLLBACK_TARGET_MISSING",
        "ROLLBACK_TARGET_NOT_ACTIVE",
        "ROLLBACK_TARGET_NOT_IMMUTABLE",
        "ROLLBACK_VERSION_MISMATCH",
        "ROUTER_PROVIDER_NOT_HAIKU",
        "ROUTING_WEIGHTS_INVALID",
        "ROUTING_WEIGHTS_MISMATCH",
        "UNEXPECTED_WEIGHTED_ROUTING",
    }
)
MISSING_CODES = frozenset(
    {
        "ALIAS_RECORD_MISSING",
        "ARTIFACT_FILE_NOT_VERIFIED",
        "CANDIDATE_RECORD_MISSING",
        "FACT_STALE",
        "PRODUCTION_BASELINE_MISSING",
    }
)
DECISION_CODES = frozenset(
    {
        "RELEASE_STRATEGY_UNRESOLVED",
        "ROLLBACK_TARGET_UNRESOLVED",
    }
)
NOTICE_CODES = frozenset(
    {
        "ALIAS_RECORD_NOT_EVALUATED_STRATEGY_UNRESOLVED",
        "BASELINE_DIFFERS_FROM_INTENDED",
        "BASELINE_LAYERS_REMOVED_BY_PLAN",
        "CANDIDATE_IS_UNPUBLISHED_LATEST",
        "ROLLBACK_DEPENDS_ON_LAYERS",
        "ROLLBACK_RECORD_NOT_EVALUATED",
    }
)
INPUT_CODES = frozenset(
    {
        "INPUT_DUPLICATE_KEY",
        "INPUT_NONFINITE_NUMBER",
        "INPUT_NOT_JSON",
        "INPUT_UNREADABLE",
        "AS_OF_INVALID",
        "PLAN_INVALID",
        "RECORD_DUPLICATE_ROLE",
        "RECORD_INVALID",
    }
)

SHA256_HEX = re.compile(r"[0-9a-f]{64}")
ACCOUNT = re.compile(r"[0-9]{12}")
REGION = re.compile(r"[a-z]{2}(-[a-z]+)+-[0-9]")
FUNCTION_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")
VERSION = re.compile(r"[1-9][0-9]{0,9}")
ALIAS_NAME = re.compile(r"(?![0-9]+$)[A-Za-z0-9_-]{1,128}")
SAFE_TOKEN = re.compile(r"[A-Za-z0-9._:-]{1,128}")
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
FUNCTION_ARN = re.compile(
    r"arn:aws:lambda:(?P<region>[a-z0-9-]+):(?P<account>[0-9]{12}):function:"
    r"(?P<name>[A-Za-z0-9_-]{1,64})(?::(?P<qualifier>\$LATEST|[A-Za-z0-9_-]{1,128}))?"
)
LAYER_ARN = re.compile(
    r"arn:aws:lambda:[a-z0-9-]+:[0-9]{12}:layer:[A-Za-z0-9_-]{1,140}:[1-9][0-9]*"
)
CONFIG_FIELDS = (
    "runtime",
    "architectures",
    "handler",
    "package_type",
    "layers",
    "memory_size",
    "timeout",
    "ephemeral_storage",
)


class InputError(ValueError):
    """Fixed input-contract code; never a provider message or value."""


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("INPUT_DUPLICATE_KEY")
        result[key] = value
    return result


def _nonfinite(_):
    raise InputError("INPUT_NONFINITE_NUMBER")


def read_json(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise InputError("INPUT_UNREADABLE") from error
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InputError("INPUT_NOT_JSON") from error
    return value, hashlib.sha256(raw).hexdigest()


def hex_to_code_sha256(hex_digest):
    """Raw lowercase SHA-256 hex → AWS CodeSha256 (base64 of the 32 bytes)."""
    if type(hex_digest) is not str or not SHA256_HEX.fullmatch(hex_digest):
        raise ValueError("CODE_SHA256_INVALID")
    return base64.b64encode(bytes.fromhex(hex_digest)).decode("ascii")


def code_sha256_to_hex(code_sha256):
    """AWS CodeSha256 → raw hex; only the canonical 44-character form is accepted."""
    if type(code_sha256) is not str:
        raise ValueError("CODE_SHA256_INVALID")
    try:
        digest = base64.b64decode(code_sha256, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("CODE_SHA256_INVALID") from error
    if len(digest) != 32 or base64.b64encode(digest).decode("ascii") != code_sha256:
        raise ValueError("CODE_SHA256_INVALID")
    return digest.hex()


def parse_time(value):
    if type(value) is not str:
        raise ValueError("timestamp")
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp")
    return parsed.astimezone(datetime.timezone.utc)


def _require(condition, code="PLAN_INVALID"):
    if not condition:
        raise InputError(code)


def _exact_keys(value, required, optional=()):
    _require(type(value) is dict)
    _require(set(required) <= set(value) <= set(required) | set(optional))


def _positive_int(value):
    return type(value) is int and value > 0


def _validate_weights(weights):
    """Return normalized {version: weight} or raise ValueError."""
    if type(weights) is not dict:
        raise ValueError("weights")
    total = 0.0
    for version, weight in weights.items():
        if not (type(version) is str and VERSION.fullmatch(version)):
            raise ValueError("weights")
        if type(weight) not in (int, float) or type(weight) is bool:
            raise ValueError("weights")
        if not math.isfinite(weight) or not 0 < weight < 1:
            raise ValueError("weights")
        total += weight
    if total >= 1:
        raise ValueError("weights")
    return {version: float(weight) for version, weight in weights.items()}


def validate_plan(plan):
    _exact_keys(
        plan,
        (
            "schema",
            "plan_id",
            "account_id",
            "region",
            "production_function",
            "candidate_function",
            "max_fact_age_seconds",
            "artifact",
            "intended_configuration",
            "release_strategy",
            "rollback",
        ),
        ("external_gates",),
    )
    _require(plan["schema"] == PLAN_SCHEMA)
    _require(type(plan["plan_id"]) is str and SAFE_TOKEN.fullmatch(plan["plan_id"]))
    _require(type(plan["account_id"]) is str and ACCOUNT.fullmatch(plan["account_id"]))
    _require(type(plan["region"]) is str and REGION.fullmatch(plan["region"]))
    for key in ("production_function", "candidate_function"):
        _require(type(plan[key]) is str and FUNCTION_NAME.fullmatch(plan[key]))
    _require(_positive_int(plan["max_fact_age_seconds"]))

    artifact = plan["artifact"]
    _exact_keys(artifact, ("sha256", "manifest_sha256", "zip_bytes"))
    for key in ("sha256", "manifest_sha256"):
        _require(type(artifact[key]) is str and SHA256_HEX.fullmatch(artifact[key]))
    _require(_positive_int(artifact["zip_bytes"]))

    config = plan["intended_configuration"]
    _exact_keys(config, (*CONFIG_FIELDS, "environment"))
    _require(type(config["runtime"]) is str and config["runtime"].startswith("python"))
    _require(
        type(config["architectures"]) is list
        and len(config["architectures"]) == 1
        and config["architectures"][0] in ("x86_64", "arm64")
    )
    _require(type(config["handler"]) is str and 0 < len(config["handler"]) <= 128)
    _require(config["package_type"] == "Zip")
    _require(
        type(config["layers"]) is list
        and all(
            type(arn) is str and LAYER_ARN.fullmatch(arn) for arn in config["layers"]
        )
        and len(set(config["layers"])) == len(config["layers"])
    )
    _require(
        type(config["memory_size"]) is int and 128 <= config["memory_size"] <= 10240
    )
    _require(type(config["timeout"]) is int and 1 <= config["timeout"] <= 900)
    _require(
        type(config["ephemeral_storage"]) is int
        and 512 <= config["ephemeral_storage"] <= 10240
    )
    environment = config["environment"]
    _exact_keys(environment, ("variables", "allow_unlisted"))
    _require(type(environment["allow_unlisted"]) is bool)
    _require(type(environment["variables"]) is dict)
    for name, expectation in environment["variables"].items():
        # Only names the application actually reads; no invented configuration.
        _require(name in APP_ENVIRONMENT)
        _require(type(expectation) is dict and "expect" in expectation)
        kind = expectation["expect"]
        if kind in ("absent", "present"):
            _exact_keys(expectation, ("expect",))
        elif kind == "sha256":
            _exact_keys(expectation, ("expect", "sha256"))
            _require(
                type(expectation["sha256"]) is str
                and SHA256_HEX.fullmatch(expectation["sha256"])
            )
        elif kind == "equals":
            # Secret values are never written into a plan; compare by hash.
            _require(APP_ENVIRONMENT[name] == "plain")
            _exact_keys(expectation, ("expect", "value"))
            _require(type(expectation["value"]) is str)
        else:
            _require(False)
    provider = environment["variables"].get("COPILOT_ROUTER_PROVIDER")
    _require(
        provider is None
        or provider["expect"] == "absent"
        or (provider["expect"] == "equals" and provider["value"] == HAIKU_PROVIDER)
    )

    strategy = plan["release_strategy"]
    _require(type(strategy) is dict and strategy.get("type") in ("unresolved", "alias"))
    if strategy["type"] == "unresolved":
        _exact_keys(strategy, ("type",))
    else:
        _exact_keys(
            strategy,
            (
                "type",
                "alias_name",
                "phase",
                "candidate_version",
                "expected_alias_revision_id",
                "additional_version_weights",
            ),
            ("expected_candidate_revision_id",),
        )
        _require(
            type(strategy["alias_name"]) is str
            and ALIAS_NAME.fullmatch(strategy["alias_name"])
        )
        _require(strategy["phase"] in ("pre_release", "post_release"))
        _require(
            type(strategy["candidate_version"]) is str
            and VERSION.fullmatch(strategy["candidate_version"])
        )
        _require(plan["candidate_function"] == plan["production_function"])
        for key in ("expected_alias_revision_id", "expected_candidate_revision_id"):
            value = strategy.get(key)
            _require(
                value is None or (type(value) is str and SAFE_TOKEN.fullmatch(value))
            )
        try:
            weights = _validate_weights(strategy["additional_version_weights"])
        except ValueError as error:
            raise InputError("PLAN_INVALID") from error
        _require(
            strategy["candidate_version"] not in weights
            or strategy["phase"] == "pre_release"
        )

    rollback = plan["rollback"]
    if rollback is not None:
        _exact_keys(
            rollback, ("function_version", "code_sha256"), ("expected_revision_id",)
        )
        # Version immutability is a finding, not an input error, so it is reported.
        _require(type(rollback["function_version"]) is str)
        _require(type(rollback["code_sha256"]) is str)
        value = rollback.get("expected_revision_id")
        _require(value is None or (type(value) is str and SAFE_TOKEN.fullmatch(value)))

    gates = plan.get("external_gates", {})
    _require(type(gates) is dict)
    _require(
        set(gates) <= {"qualification", "independent_review", "owner_authorization"}
    )
    for reference in gates.values():
        _require(reference is None or type(reference) is dict)
        if reference is not None:
            _exact_keys(reference, ("label", "sha256"))
            _require(
                type(reference["label"]) is str
                and SAFE_TOKEN.fullmatch(reference["label"])
            )
            _require(
                type(reference["sha256"]) is str
                and SHA256_HEX.fullmatch(reference["sha256"])
            )
    return plan


def validate_record(record, input_sha256):
    if not (
        type(record) is dict
        and set(record)
        == {"schema", "role", "operation", "request", "observed_utc", "response"}
        and record["schema"] == RECORD_SCHEMA
        and record["role"] in ROLES
        and type(record["request"]) is dict
        and set(record["request"]) <= {"FunctionName", "Qualifier", "Name"}
        and all(type(v) is str for v in record["request"].values())
    ):
        raise InputError("RECORD_INVALID")
    expected_operation = (
        ("GetAlias",) if record["role"] == "alias" else FUNCTION_OPERATIONS
    )
    if record["operation"] not in expected_operation:
        raise InputError("RECORD_INVALID")
    try:
        observed = parse_time(record["observed_utc"])
    except ValueError as error:
        raise InputError("RECORD_INVALID") from error
    return {**record, "observed": observed, "input_sha256": input_sha256}


class Findings:
    def __init__(self):
        self.errors, self.missing, self.decisions, self.notices = [], [], [], []

    def _add(self, bucket, allowed, code, role, field):
        if code not in allowed:
            raise AssertionError("unregistered code")
        entry = {"code": code, "role": role}
        if field is not None:
            entry["field"] = field
        if entry not in bucket:
            bucket.append(entry)

    def error(self, code, role=None, field=None):
        self._add(self.errors, ERROR_CODES, code, role, field)

    def missing_fact(self, code, role=None, field=None):
        self._add(self.missing, MISSING_CODES, code, role, field)

    def decision(self, code, role=None, field=None):
        self._add(self.decisions, DECISION_CODES, code, role, field)

    def notice(self, code, role=None, field=None):
        self._add(self.notices, NOTICE_CODES, code, role, field)


SAFE_VALUE = re.compile(r"[A-Za-z0-9._:/$-]{1,256}")


def safe_value(value):
    """Provider strings are printed only when they are plain identifiers."""
    if type(value) is str:
        return value if SAFE_VALUE.fullmatch(value) else "UNPRINTABLE_VALUE"
    if type(value) is list:
        return [safe_value(item) for item in value]
    return value if type(value) is int else "UNPRINTABLE_VALUE"


def version_label(version):
    return version if version == "$LATEST" or VERSION.fullmatch(version) else "INVALID"


def parse_function_arn(arn):
    match = FUNCTION_ARN.fullmatch(arn) if type(arn) is str else None
    return match.groupdict() if match else None


def function_configuration(record, findings):
    """Return the FunctionConfiguration dict or None (finding recorded)."""
    role, response = record["role"], record["response"]
    if type(response) is not dict:
        findings.error("RESPONSE_MALFORMED", role)
        return None
    if record["operation"] == "GetFunction":
        response = response.get("Configuration")
        if type(response) is not dict:
            findings.error("RESPONSE_MALFORMED", role, "Configuration")
            return None
    required = {
        "FunctionName": str,
        "FunctionArn": str,
        "Runtime": str,
        "Handler": str,
        "CodeSha256": str,
        "CodeSize": int,
        "Version": str,
        "MemorySize": int,
        "Timeout": int,
        "PackageType": str,
        "Architectures": list,
        "State": str,
        "LastUpdateStatus": str,
        "EphemeralStorage": dict,
    }
    valid = True
    for field, kind in required.items():
        if field not in response:
            findings.error("RESPONSE_FIELD_MISSING", role, field)
            valid = False
        elif type(response[field]) is not kind:
            findings.error("RESPONSE_FIELD_INVALID", role, field)
            valid = False
    if valid and version_label(response["Version"]) == "INVALID":
        findings.error("RESPONSE_FIELD_INVALID", role, "Version")
        valid = False
    if valid and type(response["EphemeralStorage"].get("Size")) is not int:
        findings.error("RESPONSE_FIELD_INVALID", role, "EphemeralStorage")
        valid = False
    layers = response.get("Layers", [])
    if type(layers) is not list or not all(
        type(layer) is dict and type(layer.get("Arn")) is str for layer in layers
    ):
        findings.error("RESPONSE_FIELD_INVALID", role, "Layers")
        valid = False
    environment = response.get("Environment", {})
    if (
        type(environment) is not dict
        or type(environment.get("Variables", {})) is not dict
    ):
        findings.error("RESPONSE_FIELD_INVALID", role, "Environment")
        valid = False
    elif not all(
        type(k) is str and type(v) is str
        for k, v in environment.get("Variables", {}).items()
    ):
        findings.error("RESPONSE_FIELD_INVALID", role, "Environment")
        valid = False
    return response if valid else None


def observed_configuration(response):
    return {
        "runtime": response["Runtime"],
        "architectures": list(response["Architectures"]),
        "handler": response["Handler"],
        "package_type": response["PackageType"],
        "layers": [layer["Arn"] for layer in response.get("Layers", [])],
        "memory_size": response["MemorySize"],
        "timeout": response["Timeout"],
        "ephemeral_storage": response["EphemeralStorage"]["Size"],
    }


def check_identity(record, response, plan, function_name, findings):
    """Account/region/name joins; returns the ARN qualifier."""
    role = record["role"]
    arn = parse_function_arn(response["FunctionArn"])
    if arn is None:
        findings.error("FUNCTION_ARN_INVALID", role, "FunctionArn")
        return None
    if (
        arn["account"] != plan["account_id"]
        or arn["region"] != plan["region"]
        or arn["name"] != function_name
        or response["FunctionName"] != function_name
    ):
        findings.error("FUNCTION_IDENTITY_MISMATCH", role, "FunctionArn")
    request = record["request"]
    requested = request.get("FunctionName")
    if requested is not None and requested != function_name:
        findings.error("RECORD_REQUEST_RESPONSE_MISMATCH", role, "FunctionName")
    qualifier = arn["qualifier"] or "$LATEST"
    if response["Version"] == "$LATEST":
        consistent = qualifier == "$LATEST"
    else:
        consistent = qualifier == response["Version"]
    requested_qualifier = request.get("Qualifier")
    if not consistent or (
        requested_qualifier is not None and requested_qualifier != response["Version"]
    ):
        findings.error("RECORD_REQUEST_RESPONSE_MISMATCH", role, "Qualifier")
    return qualifier


def check_environment(role, response, intended_environment, findings):
    variables = response.get("Environment", {}).get("Variables", {})
    if "Error" in response.get("Environment", {}):
        findings.error("ENVIRONMENT_ERROR_REPORTED", role, "Environment")
    for name in CREDENTIAL_ENVIRONMENT:
        if name in variables:
            findings.error("CREDENTIAL_IN_ENVIRONMENT", role, name)
    provider = variables.get("COPILOT_ROUTER_PROVIDER")
    if provider is not None and provider != HAIKU_PROVIDER:
        findings.error("ROUTER_PROVIDER_NOT_HAIKU", role, "COPILOT_ROUTER_PROVIDER")
    expected = intended_environment["variables"]
    for name, expectation in sorted(expected.items()):
        present = name in variables
        kind = expectation["expect"]
        if kind == "absent":
            ok = not present
        elif kind == "present":
            ok = present
        elif kind == "sha256":
            ok = (
                present
                and hashlib.sha256(variables[name].encode("utf-8")).hexdigest()
                == expectation["sha256"]
            )
        else:
            ok = present and variables[name] == expectation["value"]
        if not ok:
            findings.error("ENVIRONMENT_EXPECTATION_FAILED", role, name)
    if not intended_environment["allow_unlisted"]:
        for name in sorted(set(variables) - set(expected)):
            if name in CREDENTIAL_ENVIRONMENT:
                continue
            safe = name if ENV_NAME.fullmatch(name) else "UNPRINTABLE_NAME"
            findings.error("ENVIRONMENT_UNEXPECTED_NAME", role, safe)


def check_freshness(record, as_of, max_age, findings):
    age = (as_of - record["observed"]).total_seconds()
    if age < -FUTURE_SKEW_SECONDS:
        findings.error("FACT_TIMESTAMP_IN_FUTURE", record["role"], "observed_utc")
        freshness = "FUTURE_TIMESTAMP"
    elif age > max_age:
        findings.missing_fact("FACT_STALE", record["role"], "observed_utc")
        freshness = "STALE"
    else:
        freshness = "WITHIN_MAX_AGE"
    return {
        "role": record["role"],
        "operation": record["operation"],
        "kind": "SAVED_RESPONSE",
        "observed_utc": record["observed"].isoformat(),
        "age_seconds": round(age, 3),
        "freshness": freshness,
        "input_sha256": record["input_sha256"],
    }


def verify_artifact(path, plan, findings):
    """Hash the local ZIP and read (never extract or execute) its manifest."""
    expected = plan["artifact"]
    try:
        digest, size = hashlib.sha256(), 0
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        with zipfile.ZipFile(path) as archive:
            entries = [
                info for info in archive.infolist() if info.filename == MANIFEST_NAME
            ]
            manifest_raw = None
            if len(entries) == 1 and entries[0].file_size <= MANIFEST_MAX_BYTES:
                manifest_raw = archive.read(entries[0])
            manifest_state = "MANIFEST_MISSING" if not entries else "MANIFEST_INVALID"
    except (OSError, zipfile.BadZipFile):
        findings.error("ARTIFACT_UNREADABLE", "artifact")
        return {"verification": "UNREADABLE"}
    if digest.hexdigest() != expected["sha256"]:
        findings.error("ARTIFACT_SHA256_MISMATCH", "artifact")
    if size != expected["zip_bytes"]:
        findings.error("ARTIFACT_SIZE_MISMATCH", "artifact")
    if manifest_raw is None:
        # Absent, duplicated or oversized manifest entries are never trusted.
        findings.error(manifest_state, "artifact")
        return {"verification": "FILE_HASHED", "sha256": digest.hexdigest()}
    if hashlib.sha256(manifest_raw).hexdigest() != expected["manifest_sha256"]:
        findings.error("MANIFEST_SHA256_MISMATCH", "artifact")
    try:
        manifest = json.loads(
            manifest_raw.decode("utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_nonfinite,
        )
        target = manifest["target"]
        policy = manifest.get("packaging_policy")
        manifest_layers = manifest["layer_evidence"]["layers"]
        if type(target) is not dict or type(manifest_layers) is not list:
            raise TypeError("manifest")
    except (UnicodeDecodeError, json.JSONDecodeError, InputError, KeyError, TypeError):
        findings.error("MANIFEST_INVALID", "artifact")
        return {"verification": "FILE_HASHED", "sha256": digest.hexdigest()}
    config = plan["intended_configuration"]
    for field, intended in (
        ("runtime", config["runtime"]),
        ("architecture", config["architectures"][0]),
        ("handler", config["handler"]),
    ):
        if target.get(field) != intended:
            findings.error("MANIFEST_TARGET_MISMATCH", "artifact", field)
    allocation = policy.get("dependency_allocation") if type(policy) is dict else None
    if (
        config["layers"]
        and (allocation == COMPLETE_FUNCTION_ALLOCATION or not manifest_layers)
    ) or (not config["layers"] and manifest_layers):
        # The planned layers must agree with the dependency allocation the artifact was built for.
        findings.error("LAYER_ALLOCATION_CONTRADICTION", "artifact", "layers")
    return {
        "verification": "FILE_HASHED_MANIFEST_READ",
        "sha256": digest.hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "manifest_dependency_allocation": allocation
        if type(allocation) is str and SAFE_TOKEN.fullmatch(allocation)
        else None,
        "manifest_declared_layers": len(manifest_layers),
    }


def compare_configuration(role, observed, intended, findings):
    for field in CONFIG_FIELDS:
        if observed[field] != intended[field]:
            code = "LAYER_MISMATCH" if field == "layers" else "CONFIGURATION_MISMATCH"
            findings.error(code, role, field)


def check_candidate(record, plan, artifact_code_sha256, findings):
    role = "candidate"
    response = function_configuration(record, findings)
    if response is None:
        return None
    check_identity(record, response, plan, plan["candidate_function"], findings)
    observed = observed_configuration(response)
    compare_configuration(role, observed, plan["intended_configuration"], findings)
    check_environment(
        role, response, plan["intended_configuration"]["environment"], findings
    )
    try:
        code_sha256_to_hex(response["CodeSha256"])
        if response["CodeSha256"] != artifact_code_sha256:
            findings.error("CODE_SHA256_MISMATCH", role, "CodeSha256")
    except ValueError:
        findings.error("CODE_SHA256_INVALID", role, "CodeSha256")
    if response["CodeSize"] != plan["artifact"]["zip_bytes"]:
        findings.error("CODE_SIZE_MISMATCH", role, "CodeSize")
    if response["State"] != "Active":
        findings.error("CANDIDATE_NOT_ACTIVE", role, "State")
    if response["LastUpdateStatus"] != "Successful":
        findings.error("CANDIDATE_UPDATE_NOT_SUCCESSFUL", role, "LastUpdateStatus")
    revision = response.get("RevisionId")
    if type(revision) is not str or not revision:
        findings.error("REVISION_ID_MISSING", role, "RevisionId")
    strategy = plan["release_strategy"]
    if strategy["type"] == "alias":
        if response["Version"] != strategy["candidate_version"]:
            findings.error("CANDIDATE_VERSION_MISMATCH", role, "Version")
        expected = strategy.get("expected_candidate_revision_id")
        if expected is not None and revision != expected:
            findings.error("REVISION_MISMATCH", role, "RevisionId")
    elif response["Version"] == "$LATEST":
        findings.notice("CANDIDATE_IS_UNPUBLISHED_LATEST", role, "Version")
    return {
        "version": version_label(response["Version"]),
        "configuration": {
            field: safe_value(value) for field, value in observed.items()
        },
        "environment_names": sorted(
            name if ENV_NAME.fullmatch(name) else "UNPRINTABLE_NAME"
            for name in response.get("Environment", {}).get("Variables", {})
        ),
    }


def check_baseline(record, plan, findings):
    role = "production_baseline"
    response = function_configuration(record, findings)
    if response is None:
        return None
    check_identity(record, response, plan, plan["production_function"], findings)
    observed = observed_configuration(response)
    intended = plan["intended_configuration"]
    # Baseline differences are planned changes, not inconsistencies.
    changes = [field for field in CONFIG_FIELDS if observed[field] != intended[field]]
    if changes:
        findings.notice("BASELINE_DIFFERS_FROM_INTENDED", role)
    if observed["layers"] and not intended["layers"]:
        findings.notice("BASELINE_LAYERS_REMOVED_BY_PLAN", role, "layers")
    variables = response.get("Environment", {}).get("Variables", {})
    names = {
        name if ENV_NAME.fullmatch(name) else "UNPRINTABLE_NAME" for name in variables
    }
    return {
        "version": version_label(response["Version"]),
        "configuration": {
            field: safe_value(value) for field, value in observed.items()
        },
        "planned_changes": {
            field: {
                "baseline": safe_value(observed[field]),
                "intended": intended[field],
            }
            for field in changes
        },
        "environment_names": sorted(names),
        "baseline_layer_count": len(observed["layers"]),
    }


def check_rollback(record, plan, artifact_code_sha256, candidate_version, findings):
    rollback = plan["rollback"]
    role = "rollback_target"
    version = rollback["function_version"]
    if not VERSION.fullmatch(version):
        # $LATEST or an alias name can change after the fact; never acceptable.
        findings.error("ROLLBACK_TARGET_NOT_IMMUTABLE", role, "function_version")
        return None
    try:
        expected_code = code_sha256_to_hex(rollback["code_sha256"])
    except ValueError:
        findings.error("CODE_SHA256_INVALID", role, "code_sha256")
        expected_code = None
    if expected_code is not None and rollback["code_sha256"] == artifact_code_sha256:
        findings.error("ROLLBACK_CODE_EQUALS_CANDIDATE", role, "code_sha256")
    if version == candidate_version:
        findings.error("ROLLBACK_EQUALS_CANDIDATE", role, "function_version")
    if record is None:
        findings.error("ROLLBACK_RECORD_MISSING", role)
        return None
    response = function_configuration(record, findings)
    if response is None:
        return None
    qualifier = check_identity(
        record, response, plan, plan["production_function"], findings
    )
    if response["Version"] != version or qualifier != version:
        findings.error("ROLLBACK_VERSION_MISMATCH", role, "Version")
    if expected_code is not None and response["CodeSha256"] != rollback["code_sha256"]:
        findings.error("ROLLBACK_CODE_SHA256_MISMATCH", role, "CodeSha256")
    if response["State"] != "Active":
        findings.error("ROLLBACK_TARGET_NOT_ACTIVE", role, "State")
    revision = response.get("RevisionId")
    if type(revision) is not str or not revision:
        findings.error("REVISION_ID_MISSING", role, "RevisionId")
    elif rollback.get("expected_revision_id") not in (None, revision):
        findings.error("REVISION_MISMATCH", role, "RevisionId")
    observed = observed_configuration(response)
    if observed["layers"]:
        # Layer versions must still exist for a rollback; not verifiable offline.
        findings.notice("ROLLBACK_DEPENDS_ON_LAYERS", role, "layers")
    return {
        "version": version,
        "configuration": {
            field: safe_value(value) for field, value in observed.items()
        },
    }


def check_alias(record, plan, findings):
    role = "alias"
    strategy = plan["release_strategy"]
    response = record["response"]
    if type(response) is not dict:
        findings.error("RESPONSE_MALFORMED", role)
        return None
    for field in ("AliasArn", "Name", "FunctionVersion"):
        if type(response.get(field)) is not str:
            findings.error("RESPONSE_FIELD_MISSING", role, field)
            return None
    match = FUNCTION_ARN.fullmatch(response["AliasArn"])
    if (
        match is None
        or match["qualifier"] in (None, "$LATEST")
        or VERSION.fullmatch(match["qualifier"])
    ):
        findings.error("ALIAS_ARN_INVALID", role, "AliasArn")
    elif (
        match["account"] != plan["account_id"]
        or match["region"] != plan["region"]
        or match["name"] != plan["production_function"]
        or match["qualifier"] != response["Name"]
    ):
        findings.error("ALIAS_IDENTITY_MISMATCH", role, "AliasArn")
    request = record["request"]
    if request.get("FunctionName") not in (
        None,
        plan["production_function"],
    ) or request.get("Name") not in (None, response["Name"]):
        findings.error("RECORD_REQUEST_RESPONSE_MISMATCH", role, "Name")
    if response["Name"] != strategy["alias_name"]:
        findings.error("ALIAS_NAME_MISMATCH", role, "Name")
    target = response["FunctionVersion"]
    if not VERSION.fullmatch(target):
        findings.error("ALIAS_TARGETS_UNPUBLISHED_VERSION", role, "FunctionVersion")
    else:
        rollback = plan["rollback"]
        expected = (
            strategy["candidate_version"]
            if strategy["phase"] == "post_release"
            else rollback["function_version"]
            if rollback is not None
            else None
        )
        if expected is not None and target != expected:
            findings.error("ALIAS_TARGET_VERSION_MISMATCH", role, "FunctionVersion")
    routing = response.get("RoutingConfig") or {}
    weights = (
        routing.get("AdditionalVersionWeights") or {} if type(routing) is dict else None
    )
    try:
        weights = _validate_weights(weights)
        if target in weights:
            raise ValueError("weights")
    except ValueError:
        findings.error("ROUTING_WEIGHTS_INVALID", role, "RoutingConfig")
        weights = None
    planned = _validate_weights(strategy["additional_version_weights"])
    if weights is not None and weights != planned:
        findings.error(
            "UNEXPECTED_WEIGHTED_ROUTING"
            if not planned
            else "ROUTING_WEIGHTS_MISMATCH",
            role,
            "RoutingConfig",
        )
    revision = response.get("RevisionId")
    if type(revision) is not str or not revision:
        findings.error("ALIAS_REVISION_ID_MISSING", role, "RevisionId")
    if strategy.get("expected_alias_revision_id") is None:
        findings.error(
            "PLAN_ALIAS_REVISION_ID_MISSING", role, "expected_alias_revision_id"
        )
    elif type(revision) is str and revision != strategy["expected_alias_revision_id"]:
        findings.error("ALIAS_REVISION_MISMATCH", role, "RevisionId")
    return {
        "name": response["Name"] if ALIAS_NAME.fullmatch(response["Name"]) else None,
        "function_version": target if VERSION.fullmatch(target) else "UNPUBLISHED",
        "phase": strategy["phase"],
        "additional_version_weights": weights,
    }


def evaluate(plan, records, artifact_path=None, as_of=None):
    """Pure evaluation of already-loaded inputs; returns the result dict."""
    findings = Findings()
    as_of_source = "SUPPLIED"
    if as_of is None:
        as_of = datetime.datetime.now(datetime.timezone.utc)
        as_of_source = "HOST_CLOCK"
    by_role = {record["role"]: record for record in records}
    artifact_code_sha256 = hex_to_code_sha256(plan["artifact"]["sha256"])

    if artifact_path is None:
        findings.missing_fact("ARTIFACT_FILE_NOT_VERIFIED", "artifact")
        artifact = {"verification": "NOT_SUPPLIED"}
    else:
        artifact = verify_artifact(artifact_path, plan, findings)
    artifact.update(
        {
            "expected_sha256": plan["artifact"]["sha256"],
            "expected_code_sha256": artifact_code_sha256,
            "expected_zip_bytes": plan["artifact"]["zip_bytes"],
        }
    )

    facts = [
        check_freshness(by_role[role], as_of, plan["max_fact_age_seconds"], findings)
        for role in ROLES
        if role in by_role
    ]

    baseline = None
    if "production_baseline" in by_role:
        baseline = check_baseline(by_role["production_baseline"], plan, findings)
    else:
        findings.missing_fact("PRODUCTION_BASELINE_MISSING", "production_baseline")

    candidate = None
    if "candidate" in by_role:
        candidate = check_candidate(
            by_role["candidate"], plan, artifact_code_sha256, findings
        )
    else:
        findings.missing_fact("CANDIDATE_RECORD_MISSING", "candidate")

    strategy = plan["release_strategy"]
    alias = None
    if strategy["type"] == "unresolved":
        findings.decision("RELEASE_STRATEGY_UNRESOLVED", None, "release_strategy")
        if "alias" in by_role:
            findings.notice("ALIAS_RECORD_NOT_EVALUATED_STRATEGY_UNRESOLVED", "alias")
    elif "alias" in by_role:
        alias = check_alias(by_role["alias"], plan, findings)
    else:
        findings.missing_fact("ALIAS_RECORD_MISSING", "alias")

    rollback = None
    if plan["rollback"] is not None:
        candidate_version = (
            strategy["candidate_version"]
            if strategy["type"] == "alias"
            else candidate["version"]
            if candidate is not None
            else None
        )
        rollback = check_rollback(
            by_role.get("rollback_target"),
            plan,
            artifact_code_sha256,
            candidate_version,
            findings,
        )
    elif strategy["type"] == "alias":
        # Never silently acceptable: an alias release needs an explicit way back.
        findings.error("ROLLBACK_TARGET_MISSING", "rollback_target", "rollback")
    else:
        findings.decision("ROLLBACK_TARGET_UNRESOLVED", "rollback_target", "rollback")
        if "rollback_target" in by_role:
            findings.notice("ROLLBACK_RECORD_NOT_EVALUATED", "rollback_target")

    if findings.errors:
        status = "BLOCKED"
    elif findings.missing or findings.decisions:
        status = "INCOMPLETE"
    else:
        status = "CONSISTENT_PENDING_EXTERNAL_GATES"
    gates = plan.get("external_gates", {})
    return {
        "schema": RESULT_SCHEMA,
        "plan_id": plan["plan_id"],
        "evaluated_at": as_of.isoformat(),
        "evaluated_at_source": as_of_source,
        "technical_status": status,
        "release_authorized": False,
        "artifact": artifact,
        "facts": facts,
        "production_baseline": baseline,
        "intended_configuration": {
            field: plan["intended_configuration"][field] for field in CONFIG_FIELDS
        },
        "intended_environment_names": sorted(
            plan["intended_configuration"]["environment"]["variables"]
        ),
        "candidate": candidate,
        "alias": alias,
        "rollback_target": rollback,
        "errors": findings.errors,
        "missing_or_stale_facts": findings.missing,
        "unresolved_decisions": findings.decisions,
        "notices": findings.notices,
        "separate_gates": {
            name: {
                "status": "REFERENCED_NOT_AUTHENTICATED"
                if gates.get(name) is not None
                else "NOT_SUPPLIED",
                "reference": gates.get(name),
            }
            for name in ("qualification", "independent_review", "owner_authorization")
        },
        "limitations": [
            "SAVED_RESPONSES_ONLY_NO_LIVE_AWS_OBSERVATION",
            "HASH_AGREEMENT_DOES_NOT_AUTHENTICATE_APPROVAL",
            "NO_PROOF_OF_IAM_PERMISSIONS_ATOMIC_DEPLOYMENT_OR_ROLLBACK_SUCCESS",
            "LAYER_VERSION_AVAILABILITY_NOT_VERIFIED",
        ],
    }


def load_inputs(plan_path, record_paths):
    plan, plan_sha256 = read_json(plan_path)
    validate_plan(plan)
    records, roles = [], set()
    for path in record_paths:
        record, digest = read_json(path)
        record = validate_record(record, digest)
        if record["role"] in roles:
            raise InputError("RECORD_DUPLICATE_ROLE")
        roles.add(record["role"])
        records.append(record)
    return plan, plan_sha256, records


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--record", action="append", default=[])
    parser.add_argument("--artifact")
    parser.add_argument("--as-of")
    args = parser.parse_args(argv)
    try:
        if args.as_of is None:
            as_of = None
        else:
            try:
                as_of = parse_time(args.as_of)
            except ValueError as error:
                raise InputError("AS_OF_INVALID") from error
        plan, plan_sha256, records = load_inputs(args.plan, args.record)
        result = evaluate(plan, records, args.artifact, as_of)
        result["plan_sha256"] = plan_sha256
    except InputError as error:
        code = str(error) if str(error) in INPUT_CODES else "PLAN_INVALID"
        sys.stderr.write(canonical({"status": "INPUT_REJECTED", "code": code}))
        return 2
    sys.stdout.write(canonical(result))
    return 0 if result["technical_status"] == "CONSISTENT_PENDING_EXTERNAL_GATES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
