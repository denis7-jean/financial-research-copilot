"""Invented plans/prices and local claim roots only; no invocation or native code."""

import ast
import copy
import io
import json
from pathlib import Path
import subprocess

import boto3
import pytest

from scripts import jev_rag_smoke_preinvoke as pre
from tests import offline_guard
from tests.test_jev_rag_smoke import invented


@pytest.fixture
def bundle(tmp_path):
    original = invented(tmp_path)
    policy = copy.deepcopy(original.config)
    policy["output_tokens"] = {"router": 64, "generation": 128}
    policy["ceilings_usd"] = {"haiku": "8", "titan": "1", "total": "9.1"}
    evidence = {k: pre.strict_json(v) for k, v in original.evidence.items()}
    # Independently inspectable units: ROUTE=1+2=3, GENERATE=1+4=5, EMBED=1.
    evidence["haiku"].update(
        input_token_bound=10000,
        input_usd_per_million="100",
        output_usd_per_million="31250",
    )
    evidence["titan"].update(input_token_bound=100, input_usd_per_million="10000")
    plan = {
        "schema": pre.PLAN_SCHEMA,
        "plan_id": "invented-plan",
        "run_id": policy["run_id"],
        "policy_sha256": "",
        "price_evidence_sha256": {},
        "references": {key: "a" * 64 for key in pre.REFERENCE_FIELDS},
        "owner_limits": {
            "ceilings_usd": copy.deepcopy(policy["ceilings_usd"]),
            "infrastructure_allowance_usd": "0.1",
            "memory_mib": 512,
            "timeout_seconds": 30,
            "ephemeral_storage_mib": 512,
        },
        "parent_invocation": {
            "max_attempts": 1,
            "connect_seconds": 2,
            "read_seconds": 10,
        },
    }
    root = tmp_path / "persistent-root"
    root.mkdir()
    return {"plan": plan, "policy": policy, "evidence": evidence, "root": root}


def inputs(bundle):
    policy = pre.canonical(bundle["policy"])
    evidence = {k: pre.canonical(v) for k, v in bundle["evidence"].items()}
    plan = copy.deepcopy(bundle["plan"])
    plan["policy_sha256"] = pre.digest(policy)
    plan["price_evidence_sha256"] = {k: pre.digest(v) for k, v in evidence.items()}
    plan_raw = pre.canonical(plan)
    hashes = {
        "plan": pre.digest(plan_raw),
        "policy": pre.digest(policy),
        **plan["price_evidence_sha256"],
    }
    return (plan_raw, policy), {"evidence": evidence, "expected_hashes": hashes}


def validate(bundle):
    args, kwargs = inputs(bundle)
    return pre.validate(*args, **kwargs)


def claim(bundle):
    args, kwargs = inputs(bundle)
    return pre.publish_claim(*args, root=bundle["root"], **kwargs)


def assert_code(call, code):
    with pytest.raises(pre.PreinvokeError, match="^" + code + "$"):
        call()


def test_exact_fit_counts_both_haiku_stages_and_infrastructure(bundle):
    result = validate(bundle)
    assert result["initial_reservations_usd"] == {
        "ROUTE": "3",
        "EMBED": "1",
        "GENERATE": "5",
        "haiku": "8",
        "titan": "1",
        "models": "9",
        "infrastructure": "0.1",
        "whole_run": "9.1",
    }
    assert result == validate(bundle)
    assert not list(bundle["root"].iterdir())
    assert (
        result["owner_authorized"]
        is result["invoke_authorized"]
        is result["artifact_ready"]
        is False
    )
    assert (
        "AUTHORITATIVE_CURRENT_PRICE_AND_TOKEN_BOUND_EVIDENCE"
        in result["external_gates"]
    )


@pytest.mark.parametrize(
    "provider,value,code",
    [
        ("haiku", "7.999999", "HAIKU_CEILING_INSUFFICIENT"),
        ("titan", "0.999999", "TITAN_CEILING_INSUFFICIENT"),
        ("total", "9", "TOTAL_CEILING_INSUFFICIENT"),
        ("total", "9.099999", "TOTAL_CEILING_INSUFFICIENT"),
    ],
)
def test_insufficient_ceiling_rejects_before_claim(bundle, provider, value, code):
    bundle["plan"]["owner_limits"]["ceilings_usd"][provider] = value
    bundle["policy"]["ceilings_usd"][provider] = value
    assert_code(lambda: claim(bundle), code)
    assert not list(bundle["root"].iterdir())


def test_infrastructure_separates_model_subtotal_from_whole_run(bundle):
    bundle["plan"]["owner_limits"]["ceilings_usd"]["total"] = bundle["policy"][
        "ceilings_usd"
    ]["total"] = "9"
    assert_code(lambda: claim(bundle), "TOTAL_CEILING_INSUFFICIENT")
    bundle["plan"]["owner_limits"]["infrastructure_allowance_usd"] = "0"
    assert validate(bundle)["initial_reservations_usd"]["whole_run"] == "9"


def test_exact_small_decimal_products_are_not_rounded(bundle):
    bundle["evidence"]["haiku"].update(
        input_token_bound=1,
        input_usd_per_million="0.000000000001",
        output_usd_per_million="0.000000000001",
    )
    result = validate(bundle)["initial_reservations_usd"]
    assert result["ROUTE"] == "0.000000000000000065"
    assert result["GENERATE"] == "0.000000000000000129"
    assert result["haiku"] == "0.000000000000000194"
    assert result["whole_run"] == "1.100000000000000194"


@pytest.mark.parametrize(
    "value", ["-1", "NaN", "Infinity", "1e9", "01", "", 9, True, None]
)
def test_malformed_limits(bundle, value):
    bundle["plan"]["owner_limits"]["infrastructure_allowance_usd"] = value
    assert_code(lambda: claim(bundle), "LIMITS_INVALID")
    assert not list(bundle["root"].iterdir())


@pytest.mark.parametrize(
    "key", ["memory_mib", "timeout_seconds", "ephemeral_storage_mib"]
)
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "512"])
def test_explicit_owner_sizing_requires_bounded_integers(bundle, key, value):
    bundle["plan"]["owner_limits"][key] = value
    assert_code(lambda: validate(bundle), "LIMITS_INVALID")


def test_contradictory_owner_and_policy_ceilings(bundle):
    bundle["plan"]["owner_limits"]["ceilings_usd"]["haiku"] = "9"
    assert_code(lambda: claim(bundle), "CEILING_BINDING_MISMATCH")


@pytest.mark.parametrize("key", sorted(pre.REFERENCE_FIELDS))
def test_all_artifact_configuration_owner_and_event_references_required(bundle, key):
    del bundle["plan"]["references"][key]
    assert_code(lambda: claim(bundle), "PLAN_INVALID")


def test_reference_hash_and_run_identity_checks(bundle):
    bundle["plan"]["references"]["configuration_sha256"] = "invented-private-value"
    assert_code(lambda: validate(bundle), "REFERENCE_INVALID")
    bundle["plan"]["references"]["configuration_sha256"] = "a" * 64
    bundle["plan"]["run_id"] = "different-run"
    assert_code(lambda: validate(bundle), "RUN_BINDING_MISMATCH")


@pytest.mark.parametrize("key", ["plan", "policy", "haiku", "titan"])
def test_separate_trust_anchor_required_and_stale_hash_rejected(bundle, key):
    args, kwargs = inputs(bundle)
    del kwargs["expected_hashes"][key]
    assert_code(lambda: pre.validate(*args, **kwargs), "TRUST_BINDINGS_REQUIRED")
    args, kwargs = inputs(bundle)
    kwargs["expected_hashes"][key] = "0" * 64
    assert_code(lambda: pre.validate(*args, **kwargs), "INPUT_HASH_MISMATCH")


def test_missing_price_evidence_and_declared_hash_contradictions(bundle):
    args, kwargs = inputs(bundle)
    del kwargs["evidence"]["titan"]
    assert_code(lambda: pre.validate(*args, **kwargs), "PRICE_EVIDENCE_REQUIRED")
    args, kwargs = inputs(bundle)
    plan = pre.strict_json(args[0])
    plan["price_evidence_sha256"]["haiku"] = "0" * 64
    raw = pre.canonical(plan)
    kwargs["expected_hashes"]["plan"] = pre.digest(raw)
    assert_code(lambda: pre.validate(raw, args[1], **kwargs), "PRICE_BINDING_MISMATCH")


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_bound",
        "negative_price",
        "insufficient_output_bound",
        "wrong_model",
        "malformed_timestamp",
    ],
)
def test_hash_matching_price_record_is_not_sufficient(bundle, mutation):
    price = bundle["evidence"]["haiku"]
    if mutation == "missing_bound":
        del price["input_token_bound"]
    elif mutation == "negative_price":
        price["input_usd_per_million"] = "-1"
    elif mutation == "insufficient_output_bound":
        price["max_supported_output_tokens"] = 100
    elif mutation == "wrong_model":
        price["model_id"] = "unapproved-model"
    else:
        price["verified_utc"] = "bad-time"
    assert_code(lambda: claim(bundle), "POLICY_OR_PRICE_EVIDENCE_INVALID")
    assert not list(bundle["root"].iterdir())


def test_impossible_expected_source_rejected_before_any_claim(bundle):
    source = bundle["policy"]["expected_source"]["source"]
    other = source.replace("public-invented", "other-invented")
    bundle["policy"]["metadata"]["source_counts"] = {source: 1, other: 4}
    bundle["policy"]["expected_source"]["minimum_hits"] = 2
    assert_code(lambda: claim(bundle), "EXPECTED_SOURCE_IMPOSSIBLE")
    assert not list(bundle["root"].iterdir())
    bundle["policy"]["expected_source"]["minimum_hits"] = 1
    assert validate(bundle)["status"] == "BUDGET_SUFFICIENT_EXTERNAL_GATES_UNRESOLVED"


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("max_attempts", 2, "PARENT_ATTEMPTS_INVALID"),
        ("max_attempts", True, "PARENT_ATTEMPTS_INVALID"),
        ("connect_seconds", 0, "PARENT_TIMEOUT_INVALID"),
        ("read_seconds", True, "PARENT_TIMEOUT_INVALID"),
    ],
)
def test_parent_declared_configuration(bundle, field, value, code):
    bundle["plan"]["parent_invocation"][field] = value
    assert_code(lambda: claim(bundle), code)


def test_strict_json_and_canonical_inputs(bundle):
    args, kwargs = inputs(bundle)
    for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b"[" * 2000):
        kwargs["expected_hashes"]["plan"] = pre.digest(raw)
        assert_code(lambda: pre.validate(raw, args[1], **kwargs), "PLAN_INVALID")
    args, kwargs = inputs(bundle)
    raw = json.dumps(pre.strict_json(args[0]), indent=2).encode()
    kwargs["expected_hashes"]["plan"] = pre.digest(raw)
    assert_code(lambda: pre.validate(raw, args[1], **kwargs), "PLAN_NOT_CANONICAL")


def test_exclusive_claim_and_duplicate_preserve_unknown_holds(bundle):
    result = claim(bundle)
    directory = bundle["root"] / result["execution_id"]
    raw = (directory / "claim.json").read_bytes()
    assert pre.digest(raw) == result["claim_sha256"]
    saved = pre.strict_json(raw)
    assert saved["preflight"]["initial_reservations_usd"]["whole_run"] == "9.1"
    assert saved["state"] == "FULL_RESERVATIONS_RETAINED_NO_DISPATCH"
    attempt = directory / "invented-uncertain-parent.json"
    attempt.write_bytes(b'{"outcome":"UNKNOWN","hold":"9.1"}\n')
    previous = {p.name: p.read_bytes() for p in directory.iterdir()}
    assert_code(lambda: claim(bundle), "EXECUTION_ALREADY_CLAIMED")
    # A revised plan label/hash with the same run identity cannot evade its claim.
    bundle["plan"]["plan_id"] = "revised-label"
    assert validate(bundle)["execution_id"] == result["execution_id"]
    assert_code(lambda: claim(bundle), "EXECUTION_ALREADY_CLAIMED")
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == previous
    assert (
        pre.strict_json(raw)["preflight"]["initial_reservations_usd"]
        == saved["preflight"]["initial_reservations_usd"]
    )


@pytest.mark.parametrize(
    "failure",
    ["permission", "partial_write", "short_write", "flush", "fsync", "interrupt"],
)
def test_publication_failure_retains_claim_and_denies_reentry(
    bundle, monkeypatch, failure
):
    original_open = Path.open

    class Stream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, raw):
            if failure in {"partial_write", "short_write", "interrupt"}:
                self.stream.write(raw[:7])
                if failure == "short_write":
                    return 7
                if failure == "interrupt":
                    raise KeyboardInterrupt()
                raise OSError("invented private path and disk message")
            return self.stream.write(raw)

        def flush(self):
            if failure == "flush":
                raise OSError("invented private flush message")
            self.stream.flush()

        def fileno(self):
            return self.stream.fileno()

    def opened(path, mode="r", *args, **kwargs):
        if path.name == "claim.json" and mode == "xb":
            if failure == "permission":
                raise PermissionError("invented secret private path")
            return Stream(original_open(path, mode, *args, **kwargs))
        return original_open(path, mode, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", opened)
        if failure == "fsync":
            patch.setattr(
                pre.os,
                "fsync",
                lambda fd: (_ for _ in ()).throw(OSError("private sync failure")),
            )
        assert_code(
            lambda: claim(bundle),
            "CLAIM_INTERRUPTED_RETAINED"
            if failure == "interrupt"
            else "CLAIM_PUBLICATION_FAILED_RETAINED",
        )
    directories = list(bundle["root"].iterdir())
    assert len(directories) == 1
    before = {p.name: p.read_bytes() for p in directories[0].iterdir()}
    assert_code(lambda: claim(bundle), "EXECUTION_ALREADY_CLAIMED")
    assert {p.name: p.read_bytes() for p in directories[0].iterdir()} == before


def test_claim_serialization_failure_precedes_directory_creation(bundle, monkeypatch):
    original = pre.canonical

    def serialize(value):
        if value.get("schema") == pre.CLAIM_SCHEMA:
            raise UnicodeError("invented private serializer payload")
        return original(value)

    monkeypatch.setattr(pre, "canonical", serialize)
    assert_code(lambda: claim(bundle), "CLAIM_SERIALIZATION_FAILED")
    assert not list(bundle["root"].iterdir())


def test_unrelated_programming_failure_propagates_without_deleting_claim(
    bundle, monkeypatch
):
    monkeypatch.setattr(
        pre.os,
        "fsync",
        lambda fd: (_ for _ in ()).throw(AssertionError("programming defect")),
    )
    with pytest.raises(AssertionError, match="programming defect"):
        claim(bundle)
    assert len(list(bundle["root"].iterdir())) == 1


def test_abrupt_exit_after_creation_leaves_exclusive_marker(bundle, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(
            pre.os,
            "fsync",
            lambda fd: (_ for _ in ()).throw(SystemExit(99)),
        )
        with pytest.raises(SystemExit) as stopped:
            claim(bundle)
        assert stopped.value.code == 99
    directory = next(bundle["root"].iterdir())
    retained = (directory / "claim.json").read_bytes()
    assert_code(lambda: claim(bundle), "EXECUTION_ALREADY_CLAIMED")
    assert (directory / "claim.json").read_bytes() == retained


def test_plan_cannot_promote_hashes_to_owner_approval(bundle):
    bundle["plan"]["owner_authorized"] = True
    assert_code(lambda: claim(bundle), "PLAN_INVALID")
    assert not list(bundle["root"].iterdir())


def test_roots_missing_relative_and_git_rejected(bundle):
    args, kwargs = inputs(bundle)
    for root in (
        "relative-root",
        bundle["root"] / "missing",
        bundle["root"] / ".." / "persistent-root",
    ):
        assert_code(
            lambda: pre.publish_claim(*args, root=root, **kwargs), "CLAIM_ROOT_INVALID"
        )
    (bundle["root"] / ".git").mkdir()
    assert_code(lambda: claim(bundle), "CLAIM_ROOT_INVALID")
    assert list(bundle["root"].iterdir()) == [bundle["root"] / ".git"]


@pytest.mark.parametrize("kind", ["symlink", "reparse"])
def test_root_link_protections_without_windows_privilege(bundle, monkeypatch, kind):
    original_link, original_stat = Path.is_symlink, Path.lstat
    if kind == "symlink":
        monkeypatch.setattr(
            Path,
            "is_symlink",
            lambda path: path == bundle["root"] or original_link(path),
        )
    else:

        class Metadata:
            st_file_attributes = 0x400

            def __init__(self, original):
                self.original = original

            def __getattr__(self, name):
                return getattr(self.original, name)

        monkeypatch.setattr(
            Path,
            "lstat",
            lambda path: (
                Metadata(original_stat(path))
                if path == bundle["root"]
                else original_stat(path)
            ),
        )
    assert_code(lambda: claim(bundle), "CLAIM_ROOT_INVALID")
    assert not list(bundle["root"].iterdir())


def test_claim_creation_failure_is_sanitized(bundle, monkeypatch):
    original = Path.mkdir
    monkeypatch.setattr(
        Path,
        "mkdir",
        lambda path, *a, **kw: (
            (_ for _ in ()).throw(PermissionError("private root failure"))
            if path.parent == bundle["root"]
            else original(path, *a, **kw)
        ),
    )
    assert_code(lambda: claim(bundle), "CLAIM_CREATE_FAILED")
    assert not list(bundle["root"].iterdir())


def test_existing_file_at_execution_identity_is_never_replaced(bundle):
    result = validate(bundle)
    path = bundle["root"] / result["execution_id"]
    path.write_bytes(b"invented retained claim sentinel")
    assert_code(lambda: claim(bundle), "EXECUTION_ALREADY_CLAIMED")
    assert path.read_bytes() == b"invented retained claim sentinel"


def cli_inputs(bundle, tmp_path):
    args, kwargs = inputs(bundle)
    paths = {
        "plan": args[0],
        "policy": args[1],
        "haiku-evidence": kwargs["evidence"]["haiku"],
        "titan-evidence": kwargs["evidence"]["titan"],
        "expected-hashes": pre.canonical(kwargs["expected_hashes"]),
    }
    argv = []
    for name, raw in paths.items():
        path = tmp_path / (name + ".json")
        path.write_bytes(raw)
        argv += ["--" + name, str(path)]
    return argv


def test_validate_cli_has_no_writes_and_no_sdk_network_subprocess(
    bundle, tmp_path, monkeypatch, capsys
):
    argv = cli_inputs(bundle, tmp_path)
    original_open = Path.open

    def no_write(path, mode="r", *args, **kwargs):
        assert not any(c in mode for c in "wax+")
        return original_open(path, mode, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected side effect")

    monkeypatch.setattr(Path, "open", no_write)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(boto3, "client", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert pre.main(["validate", *argv]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["invoke_authorized"] is False
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


def test_claim_path_never_constructs_sdk_or_subprocess(bundle, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected external activity")

    for owner, name in (
        (boto3, "client"),
        (subprocess, "run"),
        (subprocess, "Popen"),
    ):
        monkeypatch.setattr(owner, name, forbidden)
    result = claim(bundle)
    assert result["invoke_authorized"] is False
    assert offline_guard.is_installed() and not offline_guard.blocked_requests


def test_cli_sanitized_failures_and_no_raw_private_paths(bundle, tmp_path, capsys):
    argv = cli_inputs(bundle, tmp_path)
    assert pre.main(["validate", *argv, "--private-provider-value"]) == 2
    output = capsys.readouterr()
    assert output.out == "" and output.err == "ARGUMENTS_INVALID\n"
    (tmp_path / "plan.json").write_bytes(b"invented private provider text")
    assert pre.main(["validate", *argv]) == 2
    output = capsys.readouterr()
    assert output.out == "" and output.err == "INPUT_HASH_MISMATCH\n"


@pytest.mark.parametrize(
    "failure", ["serialization", "output", "short_write", "flush", "closed_output"]
)
def test_console_failure_never_confirms_or_releases_published_claim(
    bundle, tmp_path, monkeypatch, capsys, failure
):
    argv = cli_inputs(bundle, tmp_path)
    original = pre.canonical
    if failure == "serialization":

        def encode(value):
            if value.get("schema") == pre.RESULT_SCHEMA:
                raise ValueError("invented private serializer text")
            return original(value)

        monkeypatch.setattr(pre, "canonical", encode)
    else:

        class Broken(io.StringIO):
            def write(self, value):
                if failure == "short_write":
                    return super().write(value[:7])
                if failure == "flush":
                    return super().write(value)
                raise OSError("invented private stdout failure")

            def flush(self):
                if failure == "flush":
                    raise OSError("invented private stdout flush failure")
                return super().flush()

        stream = io.StringIO() if failure == "closed_output" else Broken()
        if failure == "closed_output":
            stream.close()
        monkeypatch.setattr(pre.sys, "stdout", stream)
    assert pre.main(["claim", *argv, "--persistent-root", str(bundle["root"])]) == 3
    assert capsys.readouterr().err == "CONSOLE_CONFIRMATION_UNAVAILABLE\n"
    assert len(list(bundle["root"].iterdir())) == 1
    assert_code(lambda: claim(bundle), "EXECUTION_ALREADY_CLAIMED")


def test_unavailable_diagnostic_stream_preserves_denial_exit(monkeypatch):
    closed = io.StringIO()
    closed.close()
    monkeypatch.setattr(pre.sys, "stderr", closed)
    assert pre.main(["unsupported-mode"]) == 2


def test_component_import_closure_is_pure_and_fixed(bundle):
    root = Path(__file__).resolve().parents[1]
    forbidden = {"boto3", "botocore", "subprocess", "socket", "httpx", "numpy", "faiss"}
    for name in (
        "scripts/jev_rag_smoke_preinvoke.py",
        "app/services/rag_smoke_policy.py",
        "app/errors.py",
        "app/__init__.py",
        "app/services/__init__.py",
    ):
        tree = ast.parse((root / name).read_bytes())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert (
                    not {alias.name.split(".")[0] for alias in node.names} & forbidden
                )
            if isinstance(node, ast.ImportFrom):
                if name == "app/errors.py" and node.module == "botocore.exceptions":
                    # Existing lazy classify() exception types; no SDK/client path.
                    assert all(alias.name.endswith("Error") for alias in node.names)
                    continue
                assert (node.module or "").split(".")[0] not in forbidden
    assert validate(bundle)["owner_authorized"] is False
