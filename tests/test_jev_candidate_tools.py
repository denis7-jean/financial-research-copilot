"""Invented filesystem fixtures and mock comparisons only."""

import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from experiments.jev_candidate.smoke import report_bytes
from scripts.candidate_package import (
    CandidateError,
    DEFAULT_MODEL,
    build_candidate,
    safe_read,
    validate_config,
)


def config():
    return {
        "router_provider": "haiku",
        "shadow_enabled": False,
        "live_eval_enabled": False,
        "bedrock_model_id": DEFAULT_MODEL,
        "region": "us-east-1",
        "target_python": "3.11",
        "handler": "app.lambda_handler.handler",
    }


def workspace(tmp_path):
    for name in (
        "app/lambda_handler.py",
        "app/main.py",
        "app/agents/router.py",
        "app/agents/router_configuration.py",
        "eval/__init__.py",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# Invented\nx = 1\n")
    (tmp_path / "requirements.txt").write_bytes(b"invented==1\n")
    for name in (
        ".env",
        "eval/results/private.py",
        "eval/test_private.py",
        "app/private.json",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"invented secret never packaged")
    return tmp_path


def test_synthetic_comparison_reproducible_and_safe():
    first = report_bytes()
    assert first == report_bytes()
    report = json.loads(first)
    assert report["provider_calls"] == 0 and not report["performance_measured"]
    assert len(report["cases"]) == 6
    assert all(r["mock_attempts"] == {"haiku": 1, "jev": 1} for r in report["cases"])
    assert b"Invented practice query" not in first and b"latency_ms" not in first


def test_cli_has_no_live_or_publication_mode():
    for module in ("experiments.jev_candidate.smoke", "scripts.candidate_package"):
        result = subprocess.run(
            [sys.executable, "-B", "-m", module, "--live"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2


def test_archive_deterministic_source_only_no_writes(tmp_path):
    root = workspace(tmp_path)
    before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    first = build_candidate(root, config())
    assert first == build_candidate(root, config())
    assert before == {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    raw, receipt = first
    assert json.loads(receipt)["manifest"]["status"].startswith("NOT_DEPLOYABLE")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert ".env" not in archive.namelist()
        assert not any("private" in name for name in archive.namelist())
        assert not any(name.startswith("eval/") for name in archive.namelist())
        assert archive.read("app/main.py") == b"# Invented\nx = 1\n"
    (root / "app/main.py").write_bytes(b"x = 2\n")
    assert first != build_candidate(root, config())


@pytest.mark.parametrize(
    "key,value",
    [
        ("router_provider", "jev"),
        ("shadow_enabled", True),
        ("live_eval_enabled", True),
        ("bedrock_model_id", "unreviewed"),
        ("target_python", "3.13"),
        ("region", "wrong"),
        ("shadow_enabled", 0),
    ],
)
def test_reject_changed_defaults(key, value):
    value_config = config()
    value_config[key] = value
    with pytest.raises(CandidateError, match="^configuration_not_safe_default$"):
        validate_config(value_config)


def test_reject_missing_schema_source_and_syntax(tmp_path):
    root = workspace(tmp_path)
    with pytest.raises(CandidateError, match="^configuration_schema$"):
        validate_config({})
    (root / "app/main.py").write_bytes(b"type NewAlias = int\n")
    with pytest.raises(CandidateError, match="^python311_syntax$"):
        build_candidate(root, config())
    (root / "app/main.py").unlink()
    with pytest.raises(CandidateError, match="^source_incomplete$"):
        build_candidate(root, config())


def test_path_escape(tmp_path):
    root = workspace(tmp_path / "root")
    (tmp_path / "outside.py").write_bytes(b"invented")
    with pytest.raises(CandidateError, match="^source_binding$"):
        safe_read(root, "../outside.py")


def test_symlink_escape(tmp_path):
    root = workspace(tmp_path / "root")
    target = tmp_path / "outside.py"
    target.write_bytes(b"invented")
    try:
        (root / "app/escape.py").symlink_to(target)
    except OSError:
        pytest.skip("OS does not permit symlink creation")
    with pytest.raises(CandidateError, match="^source_symlink$"):
        build_candidate(root, config())


def test_symlink_rejection_without_os_privilege(tmp_path, monkeypatch):
    root = workspace(tmp_path)
    original = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path == root / "app/main.py" or original(path)
    )
    with pytest.raises(CandidateError, match="^source_symlink$"):
        build_candidate(root, config())


def test_cli_filesystem_failure_sanitized(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps(config()), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "scripts.candidate_package",
            "--root",
            str(tmp_path / "invented-private-name"),
            "--config",
            str(cfg),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stderr == "candidate_check_failed:input_read_or_schema\n"
    assert "invented-private-name" not in result.stderr


def test_automatic_workflow_is_offline_only():
    # Guard the demonstrated automatic billing path, rather than testing names.
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/eval-ci.yml"
    ).read_text(encoding="utf-8")
    assert "--run-live-eval" not in workflow
    assert "secrets." not in workflow
    assert "scripts.smoke_check" not in workflow
    assert "not test_accepted_population_regression" in workflow
