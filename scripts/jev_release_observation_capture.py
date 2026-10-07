"""Bounded, read-only capture of NEW AWS observations for the release preflight.

One explicit capture plan drives at most five reads: an STS
GetCallerIdentity account check first, then only the planned Lambda
GetFunctionConfiguration and GetAlias reads. Each accepted Lambda read becomes
a `jev-saved-aws-response-v2` record for the unchanged release checker. Its
capture provenance (request, host-clock timing, retry metadata, request id and
response binding) lives in a separately hashed observation file, because the
strict record envelope cannot carry it.

Without --live this only validates the plan and makes no client. --live is an
operator opt-in for a separately authorized capture; it is not owner
authorization. Responses are preserved exactly as returned: nothing is
fabricated, defaulted or repaired. Output goes to a new private directory
outside any Git worktree, created exclusively; console output is a sanitized
status of fixed codes and counts only.
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
import time

PLAN_SCHEMA = "jev-release-observation-capture-plan-v1"
# The accepted checker's record contract; this helper never changes it.
RECORD_SCHEMA = "jev-saved-aws-response-v2"
OBSERVATION_SCHEMA = "jev-release-observation-v1"
INDEX_SCHEMA = "jev-release-observation-capture-index-v1"
STATUS_SCHEMA = "jev-release-observation-capture-status-v1"

ROLES = ("production_baseline", "candidate", "alias", "rollback_target")
# Narrower than the checker: GetFunction (and its presigned code URL) is excluded.
REQUEST_KEYS = {
    "GetFunctionConfiguration": ({"FunctionName"}, {"Qualifier"}),
    "GetAlias": ({"FunctionName", "Name"}, set()),
}
CALLS = {
    "GetCallerIdentity": ("sts", "get_caller_identity"),
    "GetFunctionConfiguration": ("lambda", "get_function_configuration"),
    "GetAlias": ("lambda", "get_alias"),
}
ACCOUNT_LABEL = "account_verification"
MAX_CALLS = 1 + len(ROLES)
MAX_CONNECT_SECONDS = 10
MAX_READ_SECONDS = 30
MAX_INT_DIGITS = 64
MAX_PLAN_BYTES = 64 * 1024
MAX_RESPONSE_NODES = 100_000
# Far deeper than any Lambda/STS response, far below the json recursion limit.
MAX_JSON_DEPTH = 64

# Same patterns as the accepted checker (a test asserts they stay identical).
ACCOUNT = re.compile(r"[0-9]{12}")
REGION = re.compile(r"[a-z]{2}(-[a-z]+)+-[0-9]")
FUNCTION_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")
VERSION = re.compile(r"[1-9][0-9]{0,9}")
ALIAS_NAME = re.compile(r"(?![0-9]+$)[A-Za-z0-9_-]{1,128}")
SAFE_TOKEN = re.compile(r"[A-Za-z0-9._:-]{1,128}")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
FUNCTION_ARN = re.compile(
    r"arn:aws:lambda:(?P<region>[a-z0-9-]+):(?P<account>[0-9]{12}):function:"
    r"(?P<name>[A-Za-z0-9_-]{1,64})(?::(?P<qualifier>\$LATEST|[A-Za-z0-9_-]{1,128}))?"
)
OUTPUT_NAME = re.compile(r"(?!\.{1,2}$)[A-Za-z0-9._-]{1,128}")

INPUT_CODES = frozenset(
    {
        "LIVE_OPT_IN_REQUIRED",
        "OUTPUT_EXISTS",
        "OUTPUT_INSIDE_REPOSITORY",
        "OUTPUT_NAME_INVALID",
        "OUTPUT_PARENT_MISSING",
        "OUTPUT_UNAVAILABLE",
        "PLAN_CALL_LIMIT_INVALID",
        "PLAN_INVALID",
        "PLAN_OPERATION_UNSUPPORTED",
        "PLAN_REQUEST_INVALID",
        "PLAN_REQUEST_UNSUPPORTED",
        "PLAN_TARGET_NOT_EXPLICIT",
        "PLAN_UNREADABLE",
    }
)
STOP_CODES = frozenset(
    {
        "ACCOUNT_MISMATCH",
        "CALL_LIMIT_REACHED",
        "CLIENT_UNAVAILABLE",
        "CLOCK_INVALID",
        "CLOCK_READ_FAILED",
        "READ_FAILED",
        "RESPONSE_BINDING_MISMATCH",
        "RESPONSE_FIELD_INVALID",
        "RESPONSE_FIELD_MISSING",
        "RESPONSE_NOT_JSON_REPRESENTABLE",
        "RESPONSE_SERIALIZATION_FAILED",
        "RETRY_METADATA_MISSING",
        "UNEXPECTED_RETRY",
    }
)
# Publication failures interrupt the capture; they are never a COMPLETE result.
PUBLICATION_CODES = frozenset(
    {
        "PUBLICATION_COLLISION",
        "PUBLICATION_FAILED",
        "PUBLICATION_SERIALIZATION_FAILED",
    }
)
TIMING_SEMANTICS = {
    "clock": "HOST_UTC_CLOCK_NOT_AWS_AUTHENTICATED",
    "request_started_utc": "host clock read immediately before the SDK call",
    "response_received_utc": "host clock read immediately after the SDK call returned or raised",
    "record_observed_utc": "request_started_utc",
    "elapsed_ms": "host monotonic clock around the SDK call",
}
LIMITATIONS = [
    "HOST_CLOCK_TIMESTAMPS_NOT_AWS_AUTHENTICATED",
    "CLI_OPT_IN_IS_NOT_OWNER_AUTHORIZATION",
    "AUTHORIZATION_REFERENCE_NOT_AUTHENTICATED",
    "CAPTURE_CANNOT_PROVE_RESPONSE_AUTHENTICITY_TO_A_LATER_READER",
    "NO_DISCOVERY_ALIASES_VERSIONS_AND_STRATEGY_ARE_PLAN_SUPPLIED",
]


class InputError(ValueError):
    """Fixed input-contract code; raised before any client exists."""


class Stop(Exception):
    """Fixed stop code ending the capture; completed observations are kept."""

    def __init__(self, code, field=None):
        super().__init__(code)
        self.code, self.field = code, field


class PublicationError(Exception):
    """A private output file could not be published; carries fixed fields only."""

    def __init__(self, code, stage, file, incomplete_file_possible):
        super().__init__(code)
        self.code, self.stage, self.file = code, stage, file
        self.incomplete_file_possible = incomplete_file_possible
        self.pending_stop = None

    def summary(self):
        return {
            "code": self.code,
            "stage": self.stage,
            "file": self.file,
            "incomplete_file_possible": self.incomplete_file_possible,
            "pending_stop": self.pending_stop,
        }


# Strict JSON, matching the accepted checker's parser.


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError("non-finite number")


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("non-finite number")
    return value


def _bounded_int(text):
    if len(text.lstrip("-")) > MAX_INT_DIGITS:
        raise ValueError("integer out of range")
    return int(text)


def _has_surrogate(text):
    # A decoded str holds a valid pair as one code point, so any surrogate is unpaired.
    return any(0xD800 <= ord(char) <= 0xDFFF for char in text)


def representable(value):
    """True only for finite, bounded, surrogate-free JSON-native data.

    Nesting is bounded too, so the recursive json encoder and decoder that
    later serialize accepted data cannot hit RecursionError.
    """
    stack, nodes = [(value, 1)], 0
    while stack:
        nodes += 1
        if nodes > MAX_RESPONSE_NODES:
            return False
        item, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            return False
        kind = type(item)
        if item is None or kind is bool:
            continue
        if kind is int:
            if abs(item) >= 10**MAX_INT_DIGITS:
                return False
        elif kind is float:
            if not math.isfinite(item):
                return False
        elif kind is str:
            if _has_surrogate(item):
                return False
        elif kind is list:
            stack.extend((child, depth + 1) for child in item)
        elif kind is dict:
            for key, child in item.items():
                if type(key) is not str or _has_surrogate(key):
                    return False
                stack.append((child, depth + 1))
        else:
            return False
    return True


def parse_strict_json(raw):
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_nonfinite,
            parse_float=_finite_float,
            parse_int=_bounded_int,
        )
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise InputError("PLAN_UNREADABLE") from error
    if not representable(value):
        raise InputError("PLAN_UNREADABLE")
    return value


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    )


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


# Strict capture-plan validation.


def _require(condition, code="PLAN_INVALID"):
    if not condition:
        raise InputError(code)


def _exact_keys(value, required, optional=()):
    _require(type(value) is dict)
    _require(set(required) <= set(value) <= set(required) | set(optional))


def _bounded(value, maximum):
    return type(value) is int and 1 <= value <= maximum


def _validate_observation(entry):
    _exact_keys(entry, ("role", "operation", "request"))
    role, operation, request = entry["role"], entry["operation"], entry["request"]
    _require(role in ROLES)
    expected = "GetAlias" if role == "alias" else "GetFunctionConfiguration"
    _require(operation == expected, "PLAN_OPERATION_UNSUPPORTED")
    required, permitted = REQUEST_KEYS[operation]
    _require(
        type(request) is dict
        and required <= set(request) <= required | permitted
        and all(type(value) is str for value in request.values()),
        "PLAN_REQUEST_INVALID",
    )
    qualifier = request.get("Qualifier")
    # Plain names and checker-supported qualifiers only; no ARNs or alias qualifiers.
    _require(
        FUNCTION_NAME.fullmatch(request["FunctionName"])
        and (
            qualifier is None or qualifier == "$LATEST" or VERSION.fullmatch(qualifier)
        )
        and ("Name" not in request or ALIAS_NAME.fullmatch(request["Name"])),
        "PLAN_REQUEST_UNSUPPORTED",
    )
    # A rollback target is an explicit immutable version, never inferred.
    if role == "rollback_target":
        _require(
            qualifier is not None and VERSION.fullmatch(qualifier),
            "PLAN_TARGET_NOT_EXPLICIT",
        )


def validate_plan(plan):
    _exact_keys(
        plan,
        (
            "schema",
            "capture_id",
            "account_id",
            "region",
            "max_calls",
            "timeouts",
            "observations",
        ),
        ("authorization_reference",),
    )
    _require(plan["schema"] == PLAN_SCHEMA)
    _require(
        type(plan["capture_id"]) is str and SAFE_TOKEN.fullmatch(plan["capture_id"])
    )
    _require(type(plan["account_id"]) is str and ACCOUNT.fullmatch(plan["account_id"]))
    _require(type(plan["region"]) is str and REGION.fullmatch(plan["region"]))
    timeouts = plan["timeouts"]
    _exact_keys(timeouts, ("connect_seconds", "read_seconds"))
    _require(_bounded(timeouts["connect_seconds"], MAX_CONNECT_SECONDS))
    _require(_bounded(timeouts["read_seconds"], MAX_READ_SECONDS))
    observations = plan["observations"]
    _require(type(observations) is list and 1 <= len(observations) <= len(ROLES))
    for entry in observations:
        _validate_observation(entry)
    roles = [entry["role"] for entry in observations]
    _require(len(set(roles)) == len(roles))
    # The limit must equal the planned reads: no silent headroom.
    _require(
        type(plan["max_calls"]) is int
        and plan["max_calls"] == 1 + len(observations) <= MAX_CALLS,
        "PLAN_CALL_LIMIT_INVALID",
    )
    reference = plan.get("authorization_reference")
    if reference is not None:
        _exact_keys(reference, ("label", "sha256"))
        _require(
            type(reference["label"]) is str and SAFE_TOKEN.fullmatch(reference["label"])
        )
        _require(
            type(reference["sha256"]) is str
            and SHA256_HEX.fullmatch(reference["sha256"])
        )
    return plan


def load_plan(raw):
    _require(type(raw) is bytes and len(raw) <= MAX_PLAN_BYTES, "PLAN_UNREADABLE")
    return validate_plan(parse_strict_json(raw))


# Response checks: binding fields only. Every other field is preserved as
# returned and judged later by the unchanged checker.


def _fields(response, kinds):
    for field, kind in kinds:
        if field not in response:
            raise Stop("RESPONSE_FIELD_MISSING", field)
        if type(response[field]) is not kind:
            raise Stop("RESPONSE_FIELD_INVALID", field)


def check_caller_identity(response, plan):
    _fields(response, (("Account", str), ("Arn", str), ("UserId", str)))
    if not ACCOUNT.fullmatch(response["Account"]):
        raise Stop("RESPONSE_FIELD_INVALID", "Account")
    if response["Account"] != plan["account_id"]:
        raise Stop("ACCOUNT_MISMATCH", "Account")


def check_function_configuration(response, request, plan):
    _fields(
        response,
        (
            ("FunctionName", str),
            ("FunctionArn", str),
            ("Version", str),
            ("CodeSha256", str),
        ),
    )
    version = response["Version"]
    if version != "$LATEST" and not VERSION.fullmatch(version):
        raise Stop("RESPONSE_FIELD_INVALID", "Version")
    if not canonical_code_sha256(response["CodeSha256"]):
        raise Stop("RESPONSE_FIELD_INVALID", "CodeSha256")
    arn = FUNCTION_ARN.fullmatch(response["FunctionArn"])
    if arn is None:
        raise Stop("RESPONSE_FIELD_INVALID", "FunctionArn")
    if (
        arn["account"] != plan["account_id"]
        or arn["region"] != plan["region"]
        or arn["name"] != request["FunctionName"]
        or response["FunctionName"] != request["FunctionName"]
    ):
        raise Stop("RESPONSE_BINDING_MISMATCH", "FunctionArn")
    expected = request.get("Qualifier", "$LATEST")
    if (arn["qualifier"] or "$LATEST") != expected or version != expected:
        raise Stop("RESPONSE_BINDING_MISMATCH", "Version")


def check_alias(response, request, plan):
    _fields(response, (("AliasArn", str), ("Name", str), ("FunctionVersion", str)))
    target = response["FunctionVersion"]
    if target != "$LATEST" and not VERSION.fullmatch(target):
        raise Stop("RESPONSE_FIELD_INVALID", "FunctionVersion")
    arn = FUNCTION_ARN.fullmatch(response["AliasArn"])
    if (
        arn is None
        or arn["qualifier"] in (None, "$LATEST")
        or VERSION.fullmatch(arn["qualifier"])
    ):
        raise Stop("RESPONSE_FIELD_INVALID", "AliasArn")
    if (
        arn["account"] != plan["account_id"]
        or arn["region"] != plan["region"]
        or arn["name"] != request["FunctionName"]
        or arn["qualifier"] != request["Name"]
        or response["Name"] != request["Name"]
    ):
        raise Stop("RESPONSE_BINDING_MISMATCH", "AliasArn")


def canonical_code_sha256(value):
    """Only the canonical 44-character base64 of 32 bytes, as the checker requires."""
    try:
        digest = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return False
    return len(digest) == 32 and base64.b64encode(digest).decode("ascii") == value


def _metadata_value(metadata, key, kind):
    value = metadata.get(key) if type(metadata) is dict else None
    if type(value) is not kind:
        return None
    if kind is str and not SAFE_TOKEN.fullmatch(value):
        return None
    return value


def response_metadata(container):
    metadata = container.get("ResponseMetadata") if type(container) is dict else None
    return {
        "retry_attempts": _metadata_value(metadata, "RetryAttempts", int),
        "http_status_code": _metadata_value(metadata, "HTTPStatusCode", int),
        "request_id": _metadata_value(metadata, "RequestId", str),
    }


def failure_details(error):
    """Fixed fields of a failed read; never the exception or provider message."""
    name = type(error).__name__
    container = getattr(error, "response", None)
    code = None
    if type(container) is dict and type(container.get("Error")) is dict:
        candidate = container["Error"].get("Code")
        if type(candidate) is str and SAFE_TOKEN.fullmatch(candidate):
            code = candidate
    return {
        "type": name if SAFE_TOKEN.fullmatch(name) else "UNPRINTABLE_TYPE",
        "aws_error_code": code,
    }, response_metadata(container)


# Private output publication.


def claim_output(out_dir):
    """Create a new task-owned directory exclusively, outside any Git worktree."""
    out = Path(out_dir)
    _require(OUTPUT_NAME.fullmatch(out.name), "OUTPUT_NAME_INVALID")
    try:
        parent = out.parent.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError) as error:
        raise InputError("OUTPUT_PARENT_MISSING") from error
    except OSError as error:
        raise InputError("OUTPUT_UNAVAILABLE") from error
    try:
        _require(parent.is_dir(), "OUTPUT_PARENT_MISSING")
        for ancestor in (parent, *parent.parents):
            _require(not (ancestor / ".git").exists(), "OUTPUT_INSIDE_REPOSITORY")
        target = parent / out.name
        target.mkdir()
    except FileExistsError as error:
        raise InputError("OUTPUT_EXISTS") from error
    except OSError as error:
        # For example a permission error; never echoed, nothing was created.
        raise InputError("OUTPUT_UNAVAILABLE") from error
    return target


class Publisher:
    """Exclusive-create writes into the claimed directory; never overwrites.

    A failure raises PublicationError with fixed fields. Nothing is retried,
    renamed or deleted: a partly written file stays where it is, is never
    listed in `files`, and is disclosed as possibly incomplete.
    """

    def __init__(self, directory):
        self.directory, self.files = directory, {}

    def write_bytes(self, name, data, stage):
        if name in self.files:
            raise PublicationError("PUBLICATION_COLLISION", stage, name, False)
        opened = False
        try:
            with (self.directory / name).open("xb") as handle:
                opened = True
                handle.write(data)
        except FileExistsError:
            raise PublicationError(
                "PUBLICATION_COLLISION", stage, name, False
            ) from None
        except OSError:
            raise PublicationError("PUBLICATION_FAILED", stage, name, opened) from None
        self.files[name] = sha256_hex(data)
        return self.files[name]

    def write_json(self, name, value, stage):
        try:
            data = canonical(value).encode("utf-8")
        except (RecursionError, TypeError, ValueError):
            raise PublicationError(
                "PUBLICATION_SERIALIZATION_FAILED", stage, name, False
            ) from None
        return self.write_bytes(name, data, stage)


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def utc_text(moment):
    return moment.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _utc(moment):
    if type(moment) is not datetime.datetime or moment.utcoffset() is None:
        raise Stop("CLOCK_INVALID", "clock")
    return moment.astimezone(datetime.timezone.utc)


def _read_clock(read, field):
    """Call an injectable clock; any exception it raises is a fixed stop code."""
    try:
        return read()
    except Exception as error:
        # Injectable clocks raise arbitrary types; the message is never kept.
        raise Stop("CLOCK_READ_FAILED", field) from error


def _read_monotonic(read, field):
    value = _read_clock(read, field)
    if type(value) not in (int, float) or not math.isfinite(value):
        raise Stop("CLOCK_INVALID", field)
    return value


# Bounded reads.


def sdk_settings(timeouts):
    """botocore Config arguments: bounded timeouts and exactly one attempt."""
    return {
        "connect_timeout": timeouts["connect_seconds"],
        "read_timeout": timeouts["read_seconds"],
        "retries": {"total_max_attempts": 1, "mode": "standard"},
    }


def boto3_client_factory(service, region, settings):
    """Live capture only; imported lazily so plan validation never loads boto3."""
    import boto3
    from botocore.config import Config

    config = Config(region_name=region, **settings)
    return boto3.session.Session().client(service, region_name=region, config=config)


class Capture:
    def __init__(self, plan, plan_sha256, publisher, client_factory, clock, monotonic):
        self.plan, self.plan_sha256 = plan, plan_sha256
        self.publisher, self.client_factory = publisher, client_factory
        self.clock, self.monotonic = clock, monotonic
        self.settings = sdk_settings(plan["timeouts"])
        self.clients, self.attempted, self.sequence = {}, 0, 0
        self.previous_start, self.records = None, []
        self.account_verified = False

    def client(self, service):
        if service not in self.clients:
            try:
                self.clients[service] = self.client_factory(
                    service, self.plan["region"], self.settings
                )
            except Exception as error:
                # Injectable factories raise arbitrary types; keep the fixed code only.
                raise Stop("CLIENT_UNAVAILABLE", service) from error
        return self.clients[service]

    def observe(self, label, operation, request):
        """One separately timed read.

        Once a call has been made, its observation file is attempted for every
        outcome. It can be missing only when publication itself fails, which
        raises PublicationError and interrupts the capture.
        """
        service, method = CALLS[operation]
        client = self.client(service)
        if self.attempted >= self.plan["max_calls"]:
            raise Stop("CALL_LIMIT_REACHED", operation)
        # Both clocks are read before the call: a failure here makes no call.
        started = _utc(_read_clock(self.clock, "request_started_utc"))
        if self.previous_start is not None and started <= self.previous_start:
            raise Stop("CLOCK_INVALID", "request_started_utc")
        before = _read_monotonic(self.monotonic, "elapsed_ms")
        self.previous_start = started
        self.sequence += 1
        self.attempted += 1
        response = error = None
        try:
            response = getattr(client, method)(**request)
        except Exception as caught:
            # Any client failure is a failed read; only fixed fields are kept.
            error = caught
        # Post-response clock failures are recorded, never filled in.
        clock_stop = None
        try:
            after = _read_monotonic(self.monotonic, "elapsed_ms")
            if after < before:
                raise Stop("CLOCK_INVALID", "elapsed_ms")
            elapsed_ms = round((after - before) * 1000, 3)
        except Stop as caught:
            elapsed_ms, clock_stop = None, caught
        observation = {
            "schema": OBSERVATION_SCHEMA,
            "kind": "NEW_OBSERVATION",
            "capture_id": self.plan["capture_id"],
            "plan_sha256": self.plan_sha256,
            "sequence": self.sequence,
            "label": label,
            "service": service,
            "operation": operation,
            "request": dict(request),
            "timing": {
                "request_started_utc": utc_text(started),
                "response_received_utc": None,
                "elapsed_ms": elapsed_ms,
                "semantics": TIMING_SEMANTICS,
            },
            "sdk": {
                "connect_timeout_seconds": self.settings["connect_timeout"],
                "read_timeout_seconds": self.settings["read_timeout"],
                "total_max_attempts": 1,
            },
            "outcome": "ACCEPTED",
            "reason": None,
            "error": None,
            "response_metadata": None,
            "response": None,
            "response_sha256": None,
            "record": None,
        }
        try:
            received = _utc(_read_clock(self.clock, "response_received_utc"))
        except Stop as caught:
            received = None
            if caught.code == "CLOCK_READ_FAILED":
                clock_stop = clock_stop or caught
        clock_valid = received is not None and received >= started
        if received is not None:
            observation["timing"]["response_received_utc"] = utc_text(received)
        stop = None
        try:
            if error is not None:
                observation["error"], observation["response_metadata"] = (
                    failure_details(error)
                )
                raise Stop("READ_FAILED", operation)
            if type(response) is not dict or not representable(response):
                raise Stop("RESPONSE_NOT_JSON_REPRESENTABLE", operation)
            # A JSON round trip of JSON-native data is the identity: faithful copy.
            try:
                response = json.loads(canonical(response))
            except (RecursionError, TypeError, ValueError):
                raise Stop("RESPONSE_SERIALIZATION_FAILED", operation) from None
            observation["response"] = response
            observation["response_sha256"] = sha256_hex(
                canonical(response).encode("utf-8")
            )
            metadata = response_metadata(response)
            observation["response_metadata"] = metadata
            if metadata["retry_attempts"] is None:
                raise Stop("RETRY_METADATA_MISSING", "ResponseMetadata")
            if metadata["retry_attempts"] != 0:
                raise Stop("UNEXPECTED_RETRY", "ResponseMetadata")
            # Checked after the response is preserved, so a bad clock loses nothing.
            if clock_stop is not None:
                raise clock_stop
            if not clock_valid:
                raise Stop("CLOCK_INVALID", "response_received_utc")
            if operation == "GetCallerIdentity":
                check_caller_identity(response, self.plan)
            elif operation == "GetFunctionConfiguration":
                check_function_configuration(response, request, self.plan)
            else:
                check_alias(response, request, self.plan)
        except Stop as caught:
            stop = caught
            observation["outcome"] = (
                "READ_FAILED" if caught.code == "READ_FAILED" else "REJECTED"
            )
            observation["reason"] = {"code": caught.code, "field": caught.field}
        publication = None
        if stop is None and label in ROLES:
            record = {
                "schema": RECORD_SCHEMA,
                "role": label,
                "operation": operation,
                "request": dict(request),
                "observed_utc": utc_text(started),
                "response": response,
            }
            name = f"{self.sequence:02d}-{label}.record.json"
            try:
                observation["record"] = {
                    "file": name,
                    "sha256": self.publisher.write_json(name, record, "record"),
                }
            except PublicationError as caught:
                # Still try to preserve the response in its own observation file.
                publication = caught
                observation["outcome"] = "PUBLICATION_FAILED"
                observation["reason"] = {"code": caught.code, "field": "record"}
        observation_name = f"{self.sequence:02d}-{label}.observation.json"
        try:
            observation_sha256 = self.publisher.write_json(
                observation_name, observation, "observation"
            )
        except PublicationError as caught:
            publication = publication or caught
        if publication is not None:
            if stop is not None:
                publication.pending_stop = {"code": stop.code, "field": stop.field}
            raise publication
        if stop is not None:
            raise stop
        if observation["record"] is not None:
            self.records.append(
                {
                    "role": label,
                    "file": observation["record"]["file"],
                    "sha256": observation["record"]["sha256"],
                    "observation_file": observation_name,
                    "observation_sha256": observation_sha256,
                }
            )
        return response

    def run(self):
        self.observe(ACCOUNT_LABEL, "GetCallerIdentity", {})
        self.account_verified = True
        for entry in self.plan["observations"]:
            self.observe(entry["role"], entry["operation"], entry["request"])


def capture(plan_bytes, out_dir, client_factory, clock=_utc_now, monotonic=None):
    """Validate, claim, then read. Returns the sanitized status dict.

    Raises InputError before any client exists or any directory is created
    when the plan is invalid, and before any client exists when the output
    claim fails.
    """
    plan = load_plan(plan_bytes)
    plan_sha256 = sha256_hex(plan_bytes)
    publisher = Publisher(claim_output(out_dir))
    run = Capture(
        plan,
        plan_sha256,
        publisher,
        client_factory,
        clock,
        monotonic or time.monotonic,
    )
    stop = interruption = None
    try:
        publisher.write_bytes("capture-plan.json", plan_bytes, "plan")
        run.run()
    except Stop as caught:
        stop = caught
    except PublicationError as caught:
        interruption = caught
    if interruption is not None:
        status = "INTERRUPTED"
    else:
        status = "COMPLETE" if stop is None else "STOPPED"
    reference = plan.get("authorization_reference")
    index = {
        "schema": INDEX_SCHEMA,
        "capture_id": plan["capture_id"],
        "plan_file": "capture-plan.json",
        "plan_sha256": plan_sha256,
        "status": status,
        "stop": None if stop is None else {"code": stop.code, "field": stop.field},
        "interruption": None if interruption is None else interruption.summary(),
        "calls": {"planned": plan["max_calls"], "attempted": run.attempted},
        "account_verified": run.account_verified,
        "records": run.records,
        "files": dict(sorted(publisher.files.items())),
        "authorization": {
            "status": "NOT_SUPPLIED"
            if reference is None
            else "REFERENCED_NOT_AUTHENTICATED",
            "reference": reference,
        },
        "live_opt_in": "CLI_FLAG_IS_NOT_OWNER_AUTHORIZATION",
        "timing_semantics": TIMING_SEMANTICS,
        "limitations": LIMITATIONS,
    }
    # One attempt at the index; it is a different file, not a retry. On a
    # failed filesystem the capture is honestly reported as unindexed.
    try:
        index_sha256 = publisher.write_json("capture-index.json", index, "index")
    except PublicationError as caught:
        index_sha256 = None
        status = "INTERRUPTED_UNINDEXED"
        interruption = interruption or caught
    if interruption is not None:
        code = interruption.code
    else:
        code = None if stop is None else stop.code
    return {
        "schema": STATUS_SCHEMA,
        "status": status,
        "stop_code": code,
        "interruption_stage": None if interruption is None else interruption.stage,
        "calls_planned": plan["max_calls"],
        "calls_attempted": run.attempted,
        "accepted_records": len(run.records),
        "index_sha256": index_sha256,
    }


def main(argv=None, client_factory=boto3_client_factory, clock=_utc_now):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--out", help="new private directory outside any Git worktree")
    parser.add_argument(
        "--live",
        action="store_true",
        help="opt in to the planned read-only AWS calls; not owner authorization",
    )
    args = parser.parse_args(argv)
    try:
        try:
            raw = Path(args.plan).read_bytes()
        except OSError as error:
            raise InputError("PLAN_UNREADABLE") from error
        if not args.live:
            if args.out is not None:
                raise InputError("LIVE_OPT_IN_REQUIRED")
            plan = load_plan(raw)
            sys.stdout.write(
                canonical(
                    {
                        "schema": STATUS_SCHEMA,
                        "status": "PLAN_VALID_NO_CALLS_MADE",
                        "calls_planned": plan["max_calls"],
                        "plan_sha256": sha256_hex(raw),
                    }
                )
            )
            return 0
        if args.out is None:
            raise InputError("LIVE_OPT_IN_REQUIRED")
        status = capture(raw, args.out, client_factory, clock)
    except InputError as error:
        code = str(error) if str(error) in INPUT_CODES else "PLAN_INVALID"
        sys.stderr.write(canonical({"status": "INPUT_REJECTED", "code": code}))
        return 2
    sys.stdout.write(canonical(status))
    return 0 if status["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
