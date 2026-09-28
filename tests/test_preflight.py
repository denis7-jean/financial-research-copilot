"""Offline tests for eval/preflight.py (network is blocked by conftest)."""
import pytest

from eval import preflight
from eval.eval_queries import EVAL_CASES, EvalCase

CLEAN_CODE = {"git_sha": "a" * 40, "tracked_changes_uncommitted": False}
ENV = {
    "BEDROCK_MODEL_ID": preflight.EXPECTED_SYSTEM_MODEL_ID,
    "JUDGE_MODEL_ID": preflight.EXPECTED_JUDGE_MODEL_ID,
    "S3_BUCKET_NAME": "b", "FAISS_INDEX_S3_KEY": "i", "FAISS_META_S3_KEY": "m",
    "AWS_ACCESS_KEY_ID": "x", "AWS_SECRET_ACCESS_KEY": "y",
}


def _status(report, name):
    return next(c for c in report["checks"] if c["check"] == name)["status"]


def test_current_dataset_and_config_are_ready(tmp_path):
    report = preflight.run_preflight(str(tmp_path / "baseline.json"), CLEAN_CODE, ENV)
    assert report["blockers"] == []
    assert report["ready"] is True
    gated = next(c for c in report["checks"] if c["check"] == "dataset.gated_population")["detail"]
    assert gated["n"] == 19


def test_estimate_counts_paid_requests_from_labels():
    estimate = preflight.estimate_run(EVAL_CASES)
    assert estimate["cases"] == {"qa": 26, "summarize": 8}
    assert estimate["paid_requests"] == {"haiku": 68, "titan": 34, "sonnet_judge": 94, "total": 196}
    assert 1.0 <= estimate["total_usd"] <= 1.6
    low, high = estimate["range_usd"]
    assert low < estimate["total_usd"] < high


@pytest.mark.parametrize("path", ["eval/results/legacy/x.json", "eval/results/legacy"])
def test_legacy_results_path_blocks(path):
    report = preflight.run_preflight(path, CLEAN_CODE, ENV)
    assert "results.not_in_legacy_dir" in report["blockers"]


def test_existing_results_file_only_warns(tmp_path):
    path = tmp_path / "exists.json"
    path.write_text("{}")
    report = preflight.run_preflight(str(path), CLEAN_CODE, ENV)
    assert _status(report, "results.will_not_overwrite") == "warn"
    assert report["ready"] is True


def test_uncommitted_code_blocks(tmp_path):
    report = preflight.run_preflight(str(tmp_path / "r.json"), {**CLEAN_CODE, "tracked_changes_uncommitted": True}, ENV)
    assert "code.committed" in report["blockers"]


@pytest.mark.parametrize("key, value, blocker", [
    ("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0", "config.system_model"),
    ("JUDGE_MODEL_ID", "us.anthropic.claude-sonnet-4-5", "config.judge_model"),
    ("S3_BUCKET_NAME", "", "config.index_location"),
    ("EVAL_MAX_COST_USD", "0.5", "cost.ceiling_above_estimate"),
])
def test_configuration_blockers(tmp_path, key, value, blocker):
    report = preflight.run_preflight(str(tmp_path / "r.json"), CLEAN_CODE, {**ENV, key: value})
    assert blocker in report["blockers"]


def test_missing_credentials_block_without_revealing_values(tmp_path):
    env = {k: v for k, v in ENV.items() if not k.startswith("AWS_")}
    report = preflight.run_preflight(str(tmp_path / "r.json"), CLEAN_CODE, env)
    assert "config.aws_credentials_present" in report["blockers"]


def test_dataset_problems_block():
    broken = list(EVAL_CASES) + [EvalCase("L01", "dup", "numeric_qa", "qa", "clear", "answer", ("MA",))]
    checks = {c["check"]: c for c in preflight.check_dataset(broken)}
    assert checks["dataset.unique_ids"]["status"] == "block"
    assert checks["dataset.size"]["status"] == "block"
    assert checks["dataset.known_companies_only"]["detail"] == ["MA"]


def test_contamination_mapping_passes():
    assert preflight.check_contamination_rules()[0]["status"] == "pass"


def test_code_under_test_is_the_local_package(tmp_path):
    report = preflight.run_preflight(str(tmp_path / "r.json"), CLEAN_CODE, ENV)
    detail = next(c for c in report["checks"] if c["check"] == "code.local_in_process")["detail"]
    assert detail["orchestrator"].replace("\\", "/") == "app/agents/orchestrator.py"


def test_cli_blocks_network_and_reports(monkeypatch, capsys, tmp_path):
    import botocore.httpsession

    original = botocore.httpsession.URLLib3Session.send
    monkeypatch.setattr(botocore.httpsession.URLLib3Session, "send", original)  # restored after the test
    real_run_preflight = preflight.run_preflight
    monkeypatch.setattr(preflight, "run_preflight",
                        lambda results_path=None: real_run_preflight(str(tmp_path / "r.json"), CLEAN_CODE, ENV))
    assert preflight.main([]) == 0
    out = capsys.readouterr().out
    assert "Network attempts during preflight: 0" in out and "READY: True" in out
