"""Invented projections/journals only. Capture code is never executed.

Unit fixtures replace the recipe's two source digest pins with invented bytes;
no production bypass is exposed. The separate permitted real read-only check
validates the unmodified production pins and closure.
"""

import ast
import copy
import json
from pathlib import Path
import sys

import pytest

from scripts import jev_saved_record_adapter as adapter
from tests import offline_guard
from tests import test_jev_release_preflight as fixtures


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    projection = {field: None for field in adapter.PROJECTED_FIELDS}
    projection.update(fixtures.configuration(fixtures.OLD_CODE, 1234))
    projection.pop("StateReason", None)
    projection.pop("LastUpdateStatusReason", None)
    projection["Role"] = "arn:aws:iam::123456789012:role/invented"
    pending = copy.deepcopy(projection)
    pending["State"] = "Pending"
    source_bytes = {
        "runtime.py": b"# invented runtime fixture, never executed\n",
        "common.py": b"# invented journal fixture, never executed\n",
    }
    source_hashes = {k: adapter.digest(v) for k, v in source_bytes.items()}
    monkeypatch.setattr(adapter, "RECIPE_SOURCES", source_hashes)
    context = {
        "function": fixtures.PROD,
        "account": fixtures.ACCOUNT,
        "region": fixtures.REGION,
    }
    context_raw = adapter.canonical_bytes(context)
    bundle = {**source_hashes, "context.json": adapter.digest(context_raw)}
    rows = []
    for n, operation in enumerate(
        (
            "create_function",
            "get_function_configuration",
            "get_function_configuration",
            "get_policy",
        )
    ):
        rows += [
            {
                "phase": "BEFORE",
                "service": "lambda",
                "operation": operation,
                "utc": f"2026-10-06T11:50:{n * 2:02d}+00:00",
            },
            {
                "phase": "AFTER",
                "operation": operation,
                "utc": f"2026-10-06T11:50:{n * 2 + 1:02d}+00:00",
                "http_status": 201 if n == 0 else 200,
                "retry_attempts": 0,
                "request_id": f"00000000-0000-0000-0000-{n:012d}",
            },
        ]
    contents = {
        **source_bytes,
        "context.json": context_raw,
        "runtime-source-bindings.json": adapter.canonical_bytes(bundle),
        "function-readiness-01.json": adapter.canonical_bytes(pending),
        "function-readiness-02.json": adapter.canonical_bytes(projection),
        "function-ready.json": adapter.canonical_bytes(projection),
        "api-journal.jsonl": b"".join(adapter.canonical_bytes(r) for r in rows),
    }
    for name, raw in contents.items():
        (tmp_path / name).write_bytes(raw)
    value = {
        "root": tmp_path,
        "rows": rows,
        "projection": projection,
        "source_sha256": adapter.digest(contents["function-ready.json"]),
    }
    refresh(value)
    return value


def refresh(value):
    root = value["root"]
    index = {
        "schema": adapter.INDEX_SCHEMA,
        "files": {
            p.name: adapter.digest(p.read_bytes())
            for p in root.iterdir()
            if p.is_file() and p.name != "completion-index.json"
        },
    }
    (root / "completion-index.json").write_bytes(adapter.canonical_bytes(index))
    value["index_sha256"] = adapter.digest(
        (root / "completion-index.json").read_bytes()
    )
    value["source_sha256"] = adapter.digest((root / "function-ready.json").read_bytes())


def write_json(value, name, data):
    (value["root"] / name).write_bytes(adapter.canonical_bytes(data))
    refresh(value)


def journal(value):
    (value["root"] / "api-journal.jsonl").write_bytes(
        b"".join(adapter.canonical_bytes(r) for r in value["rows"])
    )
    refresh(value)


def run(value):
    return adapter.adapt(value["root"], value["index_sha256"], value["source_sha256"])


def args(value):
    return [
        "--evidence-dir",
        str(value["root"]),
        "--index-sha256",
        value["index_sha256"],
        "--source-sha256",
        value["source_sha256"],
    ]


def test_valid_projection_and_provenance_are_deterministic(evidence):
    assert offline_guard.is_installed()
    before = {p.name: p.read_bytes() for p in evidence["root"].iterdir()}
    result = run(evidence)
    assert result == run(evidence)
    assert result["record"]["response"] == evidence["projection"]
    assert result["record"]["observed_utc"] == evidence["rows"][5]["utc"]
    assert result["record"]["operation"] == "GetFunctionConfiguration"
    assert result["record"]["request"] == {"FunctionName": fixtures.PROD}
    assert result["record"]["role"] == "candidate" and not result["release_authorized"]
    assert set(result["record"]) == {
        "schema",
        "role",
        "operation",
        "request",
        "observed_utc",
        "response",
    }
    provenance = result["provenance"]
    assert provenance["source_kind"] == "SELECTED_FIELD_PROJECTION"
    assert (
        provenance["journal_before_line"] == 5 and provenance["journal_after_line"] == 6
    )
    assert provenance["shared_capture_file"] == "function-readiness-02.json"
    assert (
        provenance["raw_file_sha256"]["function-ready.json"]
        == evidence["source_sha256"]
    )
    assert (
        not provenance["capture_authenticated"]
        and not provenance["owner_authorization_authenticated"]
    )
    assert "ResponseMetadata" not in result["record"]["response"]
    assert result["record"]["response"]["KMSKeyArn"] is None
    assert "StateReason" not in result["record"]["response"]
    assert result["record_sha256"] == adapter.digest(
        adapter.canonical_bytes(result["record"])
    )
    assert result["provenance_sha256"] == adapter.digest(
        adapter.canonical_bytes(provenance)
    )
    assert {p.name: p.read_bytes() for p in evidence["root"].iterdir()} == before
    validated = adapter.checker.validate_record(
        result["record"], result["record_sha256"]
    )
    assert validated["role"] == "candidate"


@pytest.mark.parametrize("part", ["index", "source", "journal", "context", "runtime"])
def test_hash_mismatches(evidence, part):
    if part == "index":
        evidence["index_sha256"] = "0" * 64
    elif part == "source":
        evidence["source_sha256"] = "0" * 64
    else:
        name = {
            "journal": "api-journal.jsonl",
            "context": "context.json",
            "runtime": "runtime.py",
        }[part]
        with (evidence["root"] / name).open("ab") as out:
            out.write(b" ")
    with pytest.raises(adapter.AdapterError, match="^HASH_MISMATCH$"):
        run(evidence)


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing_index_binding", "INDEX_BINDING_MISSING"),
        ("missing_runtime", "INPUT_UNREADABLE"),
        ("wrong_source_bundle", "SOURCE_BINDING_MISMATCH"),
        ("unknown_recipe", "CAPTURE_RECIPE_UNSUPPORTED"),
        ("wrong_context_binding", "SOURCE_BINDING_MISMATCH"),
        ("missing_request_name", "CONTEXT_INVALID"),
        ("arn_request", "CONTEXT_INVALID"),
        ("bad_index_schema", "INDEX_INVALID"),
    ],
)
def test_input_closure_failures(evidence, case, code):
    root = evidence["root"]
    if case == "missing_runtime":
        (root / "runtime.py").unlink()
    elif case in ("missing_index_binding", "bad_index_schema"):
        index = json.loads((root / "completion-index.json").read_bytes())
        if case == "missing_index_binding":
            del index["files"]["api-journal.jsonl"]
        else:
            index["schema"] = "invented-wrong"
        (root / "completion-index.json").write_bytes(adapter.canonical_bytes(index))
        evidence["index_sha256"] = adapter.digest(
            (root / "completion-index.json").read_bytes()
        )
    elif case in ("wrong_source_bundle", "wrong_context_binding", "unknown_recipe"):
        bundle = json.loads((root / "runtime-source-bindings.json").read_bytes())
        if case == "unknown_recipe":
            (root / "runtime.py").write_bytes(b"# different invented recipe\n")
            bundle["runtime.py"] = adapter.digest((root / "runtime.py").read_bytes())
        else:
            bundle[
                "context.json" if case == "wrong_context_binding" else "runtime.py"
            ] = "0" * 64
        write_json(evidence, "runtime-source-bindings.json", bundle)
    else:
        context = json.loads((root / "context.json").read_bytes())
        if case == "missing_request_name":
            del context["function"]
        else:
            context["function"] = (
                "arn:aws:lambda:us-east-1:123456789012:function:invented"
            )
        write_json(evidence, "context.json", context)
        bundle = json.loads((root / "runtime-source-bindings.json").read_bytes())
        bundle["context.json"] = adapter.digest((root / "context.json").read_bytes())
        write_json(evidence, "runtime-source-bindings.json", bundle)
    with pytest.raises(adapter.AdapterError, match="^" + code + "$"):
        run(evidence)


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing_operation", "CAPTURE_PROVENANCE_MISSING"),
        ("other_operation", "CAPTURE_PROVENANCE_CONTRADICTORY"),
        ("missing_timestamp", "CAPTURE_PROVENANCE_MISSING"),
        ("invalid_timestamp", "CAPTURE_PROVENANCE_MISSING"),
        ("reversed_timestamp", "CAPTURE_PROVENANCE_CONTRADICTORY"),
        ("duplicate_request_id", "CAPTURE_PROVENANCE_CONTRADICTORY"),
        ("retry", "CAPTURE_PROVENANCE_CONTRADICTORY"),
        ("failed_call", "CAPTURE_PROVENANCE_CONTRADICTORY"),
        ("missing_boundary", "CAPTURE_PROVENANCE_MISSING"),
        ("missing_pair", "JOURNAL_INVALID"),
    ],
)
def test_journal_failures(evidence, case, code):
    rows = evidence["rows"]
    if case == "missing_operation":
        rows[2:6] = []
    elif case == "other_operation":
        rows[2]["operation"] = rows[3]["operation"] = "get_function"
    elif case == "missing_timestamp":
        del rows[5]["utc"]
    elif case == "invalid_timestamp":
        rows[5]["utc"] = "invented-private-message"
    elif case == "reversed_timestamp":
        rows[5]["utc"] = "2026-10-06T11:49:00+00:00"
    elif case == "duplicate_request_id":
        rows[5]["request_id"] = rows[3]["request_id"]
    elif case == "retry":
        rows[5]["retry_attempts"] = 1
    elif case == "failed_call":
        rows[5]["phase"] = "AMBIGUOUS_STOP"
    elif case == "missing_boundary":
        del rows[6:]
    else:
        del rows[5]
    journal(evidence)
    with pytest.raises(adapter.AdapterError, match="^" + code + "$"):
        run(evidence)


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing_handler", "SOURCE_INVALID"),
        ("null_handler", "CHECKER_RECORD_INVALID"),
        ("null_environment", "CHECKER_RECORD_INVALID"),
        ("bad_identity", "CAPTURE_PROVENANCE_CONTRADICTORY"),
        ("published_version", "CAPTURE_PROVENANCE_CONTRADICTORY"),
        ("unexpected_metadata", "SOURCE_INVALID"),
        ("missing_revision", "CHECKER_RECORD_INVALID"),
        ("credential", "CHECKER_RECORD_INVALID"),
        ("different_final_capture", "CAPTURE_PROVENANCE_CONTRADICTORY"),
        ("earlier_ready", "CAPTURE_PROVENANCE_CONTRADICTORY"),
    ],
)
def test_projection_failures(evidence, case, code):
    projection = copy.deepcopy(evidence["projection"])
    if case == "missing_handler":
        del projection["Handler"]
    elif case == "null_handler":
        projection["Handler"] = None
    elif case == "null_environment":
        projection["Environment"] = None
    elif case == "bad_identity":
        projection["FunctionName"] = "another-invented-function"
    elif case == "published_version":
        projection["Version"] = "7"
    elif case == "unexpected_metadata":
        projection["ResponseMetadata"] = {}
    elif case == "missing_revision":
        projection["RevisionId"] = None
    elif case == "credential":
        projection["Environment"]["Variables"]["AWS_SECRET_ACCESS_KEY"] = (
            fixtures.SECRET
        )
    elif case == "different_final_capture":
        projection["Role"] = "invented-other-role"
    else:
        write_json(evidence, "function-readiness-01.json", projection)
    write_json(evidence, "function-ready.json", projection)
    if case not in ("different_final_capture", "earlier_ready"):
        write_json(evidence, "function-readiness-02.json", projection)
    with pytest.raises(adapter.AdapterError, match="^" + code + "$"):
        run(evidence)


@pytest.mark.parametrize(
    "source",
    [
        "function-created.json",
        "invoke-1-observed.json",
        "function-readiness-01.json",
        "../private.json",
    ],
)
def test_unsupported_sources_never_relabel_create_function(evidence, source):
    with pytest.raises(adapter.AdapterError, match="^SOURCE_UNSUPPORTED$"):
        adapter.adapt(
            evidence["root"],
            evidence["index_sha256"],
            evidence["source_sha256"],
            source,
        )


def test_metadata_default_and_explicit_private_record(evidence, capsys):
    assert adapter.main(args(evidence)) == 0
    printed = capsys.readouterr()
    assert printed.err == "" and fixtures.SECRET not in printed.out
    assert "record" not in json.loads(printed.out)
    assert adapter.main(args(evidence) + ["--emit-record"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["record"]["response"] == evidence["projection"]


def test_sensitive_diagnostics_are_fixed(evidence, capsys):
    value = copy.deepcopy(evidence["projection"])
    value["Handler"] = None
    value["Environment"]["Error"] = {
        "Message": fixtures.SECRET,
        "ErrorCode": "private-provider-text",
    }
    write_json(evidence, "function-ready.json", value)
    write_json(evidence, "function-readiness-02.json", value)
    assert adapter.main(args(evidence)) == 2
    output = capsys.readouterr()
    assert (
        output.out == ""
        and fixtures.SECRET not in output.err
        and "private-provider-text" not in output.err
    )
    assert json.loads(output.err)["code"] == "CHECKER_RECORD_INVALID"


def test_incomplete_and_unsupported_cli(evidence, capsys):
    assert adapter.main(args(evidence) + ["--source", "function-created.json"]) == 1
    assert json.loads(capsys.readouterr().err)["status"] == "UNSUPPORTED"
    del evidence["rows"][6:]
    journal(evidence)
    assert adapter.main(args(evidence)) == 1
    assert json.loads(capsys.readouterr().err)["status"] == "INCOMPLETE"


def test_module_has_no_network_subprocess_or_mutation_paths():
    tree = ast.parse(Path(adapter.__file__).read_text())
    imports = {
        a.name.split(".")[0]
        for n in ast.walk(tree)
        if isinstance(n, ast.Import)
        for a in n.names
    }
    assert imports == {"argparse", "hashlib", "re", "stat", "sys"}
    assert {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} == {
        "pathlib",
        "scripts",
    }
    calls = {
        getattr(n.func, "attr", getattr(n.func, "id", ""))
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
    }
    assert not calls & {
        "write_bytes",
        "write_text",
        "mkdir",
        "unlink",
        "rename",
        "remove",
        "system",
        "extract",
        "extractall",
        "exec",
        "eval",
    }
    modes = [
        n.args[0].value
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "open"
    ]
    assert modes == ["rb"]


def test_recipe_pins_do_not_offer_a_cli_override():
    assert adapter.RECIPE_SOURCES == {
        "runtime.py": "5de6bf0643143902994f6d580577ddf8aa9df7d1ca24c69f9e5019be384c228e",
        "common.py": "b55047150fa0f49ee68079bd5e50cadf332b208813ad51d0d8cb6187c3c52feb",
    }


def test_runtime_readonly_guard(evidence):
    active = [False]
    events = []

    def audit(event, arguments):
        if not active[0]:
            return
        bad = event.startswith(("socket.", "subprocess.")) or event in {
            "os.system",
            "os.remove",
            "os.rename",
            "os.mkdir",
            "os.rmdir",
        }
        if event == "open":
            mode, flags = arguments[1:3]
            bad |= (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and bool(flags & (1 | 2 | 64 | 512 | 1024))
            )
        if bad:
            events.append(event)
            raise AssertionError("ADAPTER_SIDE_EFFECT")

    sys.addaudithook(audit)
    active[0] = True
    try:
        result = run(evidence)
    finally:
        active[0] = False
    assert result["status"] == "ADAPTED_CANDIDATE_PROJECTION" and events == []


@pytest.mark.parametrize("argument", ["source_sha256", "index_sha256"])
def test_invalid_hash_argument(evidence, argument):
    evidence[argument] = "invented-private-invalid-hash"
    with pytest.raises(adapter.AdapterError, match="^HASH_INPUT_INVALID$"):
        run(evidence)


def test_non_regular_source_is_rejected(evidence):
    path = evidence["root"] / "runtime.py"
    path.unlink()
    path.mkdir()
    with pytest.raises(adapter.AdapterError, match="^INPUT_UNSAFE$"):
        run(evidence)


def test_earlier_capture_identity_must_match_request_origin(evidence):
    path = evidence["root"] / "function-readiness-01.json"
    value = json.loads(path.read_bytes())
    value["FunctionName"] = "another-invented-function"
    write_json(evidence, path.name, value)
    with pytest.raises(
        adapter.AdapterError, match="^CAPTURE_PROVENANCE_CONTRADICTORY$"
    ):
        run(evidence)
