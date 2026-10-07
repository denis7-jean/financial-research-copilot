"""Read-only adapter for the reviewed startup final-readiness projection.

Default stdout is metadata only. --emit-record explicitly includes captured
values for private storage; errors never echo values. No capture/approval
authenticity, current AWS state or release authorization is inferred.
"""

import argparse
import hashlib
from pathlib import Path
import re
import stat
import sys

from scripts import jev_release_preflight as checker

SCHEMA = "jev-saved-record-adapter-result-v1"
PROVENANCE_SCHEMA = "jev-startup-projection-provenance-v1"
RECIPE = "startup-final-readiness-config-get-v1"
INDEX_SCHEMA = "jev-lambda-startup-continuation-index-v1"
# Exact inspected raw source bytes, never imported or executed by the adapter.
RECIPE_SOURCES = {
    "runtime.py": "5de6bf0643143902994f6d580577ddf8aa9df7d1ca24c69f9e5019be384c228e",
    "common.py": "b55047150fa0f49ee68079bd5e50cadf332b208813ad51d0d8cb6187c3c52feb",
}
PROJECTED_FIELDS = (
    "FunctionName",
    "FunctionArn",
    "Runtime",
    "Role",
    "Handler",
    "CodeSize",
    "CodeSha256",
    "Version",
    "MemorySize",
    "Timeout",
    "EphemeralStorage",
    "Architectures",
    "PackageType",
    "Layers",
    "Environment",
    "VpcConfig",
    "KMSKeyArn",
    "DeadLetterConfig",
    "TracingConfig",
    "LoggingConfig",
    "State",
    "StateReasonCode",
    "LastUpdateStatus",
    "RevisionId",
    "RuntimeVersionConfig",
    "SnapStart",
    "LastModified",
)
MAX_BYTES = 8 * 1024 * 1024
REQUEST_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
INCOMPLETE_CODES = {"INDEX_BINDING_MISSING", "CAPTURE_PROVENANCE_MISSING"}
UNSUPPORTED_CODES = {"SOURCE_UNSUPPORTED", "CAPTURE_RECIPE_UNSUPPORTED"}
ERROR_CODES = (
    INCOMPLETE_CODES
    | UNSUPPORTED_CODES
    | {
        "HASH_INPUT_INVALID",
        "INPUT_UNREADABLE",
        "INPUT_UNSAFE",
        "INPUT_TOO_LARGE",
        "HASH_MISMATCH",
        "INDEX_INVALID",
        "SOURCE_BINDING_MISMATCH",
        "SOURCE_INVALID",
        "CONTEXT_INVALID",
        "JOURNAL_INVALID",
        "CAPTURE_PROVENANCE_CONTRADICTORY",
        "CHECKER_RECORD_INVALID",
    }
)


class AdapterError(ValueError):
    """Registered fixed code, never source or provider text."""


def require(condition, code):
    if not condition:
        raise AdapterError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value):
    return checker.canonical(value).encode("utf-8")


def read_bound(root, name, expected):
    require(
        type(expected) is str and checker.SHA256_HEX.fullmatch(expected),
        "HASH_INPUT_INVALID",
    )
    path = root / name
    try:
        require(path.resolve().is_relative_to(root), "INPUT_UNSAFE")
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and not path.is_symlink(), "INPUT_UNSAFE")
        require(info.st_size <= MAX_BYTES, "INPUT_TOO_LARGE")
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except (OSError, ValueError) as error:
        if isinstance(error, AdapterError):
            raise
        raise AdapterError("INPUT_UNREADABLE") from None
    require(len(raw) <= MAX_BYTES, "INPUT_TOO_LARGE")
    require(digest(raw) == expected, "HASH_MISMATCH")
    return raw


def parse(raw, code):
    try:
        return checker.parse_strict_json(raw)
    except (checker.InputError, RecursionError):
        raise AdapterError(code) from None


def journal_pairs(rows):
    """Pair the sequential helper's BEFORE/terminal rows without executing it."""
    pairs = []
    i = 0
    while i < len(rows):
        row = rows[i]
        require(type(row) is dict, "JOURNAL_INVALID")
        if row.get("phase") == "BEFORE":
            require(i + 1 < len(rows), "CAPTURE_PROVENANCE_MISSING")
            end = rows[i + 1]
            require(
                type(end) is dict
                and end.get("phase") in ("AFTER", "REJECTED", "AMBIGUOUS_STOP")
                and type(row.get("operation")) is str
                and end.get("operation") == row["operation"],
                "JOURNAL_INVALID",
            )
            try:
                before_time = checker.parse_time(row.get("utc"))
                end_time = checker.parse_time(end.get("utc"))
            except ValueError:
                raise AdapterError("CAPTURE_PROVENANCE_MISSING") from None
            require(before_time <= end_time, "CAPTURE_PROVENANCE_CONTRADICTORY")
            if pairs:
                require(
                    checker.parse_time(pairs[-1][3]["utc"]) <= before_time,
                    "CAPTURE_PROVENANCE_CONTRADICTORY",
                )
            pairs.append((i + 1, i + 2, row, end))
            i += 2
        else:
            require(
                row.get("phase") not in ("AFTER", "REJECTED", "AMBIGUOUS_STOP"),
                "JOURNAL_INVALID",
            )
            i += 1
    return pairs


def successful(pair, status):
    end = pair[3]
    require(
        end.get("phase") == "AFTER"
        and type(end.get("http_status")) is int
        and end["http_status"] == status
        and type(end.get("retry_attempts")) is int
        and end["retry_attempts"] == 0
        and type(end.get("request_id")) is str
        and REQUEST_ID.fullmatch(end["request_id"]),
        "CAPTURE_PROVENANCE_CONTRADICTORY",
    )


def readiness_calls(rows):
    pairs = journal_pairs(rows)
    creates = [
        i
        for i, p in enumerate(pairs)
        if p[2].get("service") == "lambda" and p[2]["operation"] == "create_function"
    ]
    require(len(creates) == 1, "CAPTURE_PROVENANCE_MISSING")
    successful(pairs[creates[0]], 201)
    calls = []
    for pair in pairs[creates[0] + 1 :]:
        if pair[2].get("service") == "lambda" and pair[2]["operation"] == "get_policy":
            break
        require(
            pair[2].get("service") == "lambda"
            and pair[2]["operation"] == "get_function_configuration",
            "CAPTURE_PROVENANCE_CONTRADICTORY",
        )
        successful(pair, 200)
        if calls:
            require(
                checker.parse_time(calls[-1][3]["utc"])
                <= checker.parse_time(pair[2]["utc"]),
                "CAPTURE_PROVENANCE_CONTRADICTORY",
            )
        calls.append(pair)
    else:
        raise AdapterError("CAPTURE_PROVENANCE_MISSING")
    require(1 <= len(calls) <= 15, "CAPTURE_PROVENANCE_MISSING")
    require(
        len({p[3]["request_id"] for p in calls}) == len(calls),
        "CAPTURE_PROVENANCE_CONTRADICTORY",
    )
    return calls


def adapt(evidence_dir, index_sha256, source_sha256, source="function-ready.json"):
    """Verify and adapt one final-readiness capture; hashes are caller inputs."""
    require(source == "function-ready.json", "SOURCE_UNSUPPORTED")
    require(
        type(source_sha256) is str and checker.SHA256_HEX.fullmatch(source_sha256),
        "HASH_INPUT_INVALID",
    )
    root = Path(evidence_dir).resolve()
    index = parse(
        read_bound(root, "completion-index.json", index_sha256), "INDEX_INVALID"
    )
    require(
        type(index) is dict
        and index.get("schema") == INDEX_SCHEMA
        and type(index.get("files")) is dict,
        "INDEX_INVALID",
    )
    bindings = index["files"]
    used = {"completion-index.json": index_sha256}

    def load(name, code="SOURCE_INVALID"):
        require(name in bindings, "INDEX_BINDING_MISSING")
        raw = read_bound(root, name, bindings[name])
        used[name] = digest(raw)
        return raw, parse(raw, code) if name.endswith((".json", ".jsonl")) else None

    # Journal JSONL needs line parsing, not single-JSON parsing.
    require("api-journal.jsonl" in bindings, "INDEX_BINDING_MISSING")
    journal_raw = read_bound(root, "api-journal.jsonl", bindings["api-journal.jsonl"])
    used["api-journal.jsonl"] = digest(journal_raw)
    rows = [parse(line, "JOURNAL_INVALID") for line in journal_raw.splitlines()]
    _, bundle = load("runtime-source-bindings.json")
    require(type(bundle) is dict, "SOURCE_BINDING_MISMATCH")
    for name, expected in RECIPE_SOURCES.items():
        raw, _ = load(name)
        require(bundle.get(name) == digest(raw), "SOURCE_BINDING_MISMATCH")
        require(digest(raw) == expected, "CAPTURE_RECIPE_UNSUPPORTED")
    _, context = load("context.json", "CONTEXT_INVALID")
    require(
        bundle.get("context.json") == used["context.json"], "SOURCE_BINDING_MISMATCH"
    )
    require(
        type(context) is dict
        and type(context.get("function")) is str
        and checker.FUNCTION_NAME.fullmatch(context["function"])
        and type(context.get("account")) is str
        and checker.ACCOUNT.fullmatch(context["account"])
        and type(context.get("region")) is str
        and checker.REGION.fullmatch(context["region"]),
        "CONTEXT_INVALID",
    )
    raw, projection = load(source)
    require(digest(raw) == source_sha256, "HASH_MISMATCH")
    require(
        type(projection) is dict and set(projection) == set(PROJECTED_FIELDS),
        "SOURCE_INVALID",
    )
    calls = readiness_calls(rows)
    for n, _ in enumerate(calls, 1):
        last_name = f"function-readiness-{n:02d}.json"
        last_raw, captured = load(last_name)
        require(
            type(captured) is dict and set(captured) == set(PROJECTED_FIELDS),
            "SOURCE_INVALID",
        )
        arn = checker.parse_function_arn(captured.get("FunctionArn"))
        require(
            arn is not None
            and arn["name"] == context["function"]
            and arn["account"] == context["account"]
            and arn["region"] == context["region"]
            and arn["qualifier"] in (None, "$LATEST")
            and captured.get("FunctionName") == context["function"]
            and captured.get("Version") == "$LATEST",
            "CAPTURE_PROVENANCE_CONTRADICTORY",
        )
        ready = (
            captured.get("State") == "Active"
            and captured.get("LastUpdateStatus") == "Successful"
        )
        require(ready == (n == len(calls)), "CAPTURE_PROVENANCE_CONTRADICTORY")
    require(raw == last_raw, "CAPTURE_PROVENANCE_CONTRADICTORY")
    require(
        not any(
            re.fullmatch(r"function-readiness-\d{2}\.json", name) and name > last_name
            for name in bindings
        ),
        "CAPTURE_PROVENANCE_CONTRADICTORY",
    )
    call = calls[-1]
    record = {
        "schema": checker.RECORD_SCHEMA,
        "role": "candidate",
        "operation": "GetFunctionConfiguration",
        "request": {"FunctionName": context["function"]},
        "observed_utc": call[3]["utc"],
        "response": projection,
    }
    record_sha256 = digest(canonical_bytes(record))
    try:
        validated = checker.validate_record(record, record_sha256)
    except checker.InputError:
        raise AdapterError("CHECKER_RECORD_INVALID") from None
    findings = checker.Findings()
    config = checker.function_configuration(validated, findings)
    require(config is not None, "CHECKER_RECORD_INVALID")
    checker.check_identity(
        validated,
        config,
        {"account_id": context["account"], "region": context["region"]},
        context["function"],
        findings,
    )
    checker.check_environment_safety("candidate", config, findings)
    require(
        not findings.errors
        and config["Version"] == "$LATEST"
        and type(config.get("RevisionId")) is str
        and bool(config["RevisionId"]),
        "CHECKER_RECORD_INVALID",
    )
    companion = {
        "schema": PROVENANCE_SCHEMA,
        "record_sha256": record_sha256,
        "source_kind": "SELECTED_FIELD_PROJECTION",
        "capture_recipe": RECIPE,
        "source_file": source,
        "shared_capture_file": last_name,
        "raw_file_sha256": dict(sorted(used.items())),
        "operation": record["operation"],
        "request": record["request"],
        "request_basis": "HASH_BOUND_RUNTIME_CALLSITE_AND_CONTEXT_NOT_RAW_REQUEST_LOG",
        "capture_callsite": "runtime.py:create_function readiness loop; common.py:call/journal",
        "timestamp_basis": "API_JOURNAL_AFTER_UTC_NOT_PROVIDER_OBSERVATION_TIME",
        "journal_before_line": call[0],
        "journal_after_line": call[1],
        "journal_before_utc": call[2]["utc"],
        "journal_after_utc": call[3]["utc"],
        "request_id": call[3]["request_id"],
        "null_policy": "PRESERVED_PROJECTION_NULL_ORIGINAL_ABSENT_VS_NULL_UNKNOWN",
        "omitted_response_metadata": "NOT_RESTORED",
        "capture_authenticated": False,
        "owner_authorization_authenticated": False,
    }
    return {
        "schema": SCHEMA,
        "status": "ADAPTED_CANDIDATE_PROJECTION",
        "release_authorized": False,
        "record": record,
        "record_sha256": record_sha256,
        "provenance": companion,
        "provenance_sha256": digest(canonical_bytes(companion)),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--index-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--source", default="function-ready.json")
    parser.add_argument("--emit-record", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = adapt(
            args.evidence_dir, args.index_sha256, args.source_sha256, args.source
        )
    except AdapterError as error:
        code = str(error) if str(error) in ERROR_CODES else "SOURCE_INVALID"
        status = (
            "INCOMPLETE"
            if code in INCOMPLETE_CODES
            else "UNSUPPORTED"
            if code in UNSUPPORTED_CODES
            else "REJECTED"
        )
        sys.stderr.write(
            checker.canonical(
                {
                    "schema": SCHEMA,
                    "status": status,
                    "code": code,
                    "release_authorized": False,
                }
            )
        )
        return 1 if status in ("INCOMPLETE", "UNSUPPORTED") else 2
    if not args.emit_record:
        result = {key: value for key, value in result.items() if key != "record"}
    sys.stdout.write(checker.canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
