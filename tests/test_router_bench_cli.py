"""Router benchmark CLI: dry run output, refusals and fresh-process isolation. Offline only."""
import json
import os
import subprocess
import sys
from pathlib import Path

from eval.routing_datasets import routing_dataset
from experiments.router_bench import cli, safety
from experiments.router_bench.runner import build_verification_plan

REPO = Path(__file__).resolve().parents[1]
V2 = routing_dataset("v2")


# --- CLI dry run --------------------------------------------------------------------------------------

def test_dry_run_writes_a_safe_artifact_and_reads_no_credentials(tmp_path, monkeypatch, capsys):
    import botocore.session

    def forbidden(*args, **kwargs):
        raise AssertionError("credentials resolved during a dry run")

    monkeypatch.setattr(botocore.session.Session, "get_credentials", forbidden)
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-dryrun-canary-must-not-be-read")
    output = tmp_path / "dry.json"
    assert cli.main(["--repetitions", "2", "--output", str(output)]) == 0
    printed = capsys.readouterr().out
    text = output.read_text(encoding="utf-8")
    assert "ts-dryrun-canary-must-not-be-read" not in text + printed
    assert "ts-dryrun-canary-must-not-be-read" not in safety._REGISTERED_SECRETS
    assert not any(c.query in text for c in V2)  # records carry case IDs only
    data = json.loads(text)
    assert data["provenance"]["mode"] == "dry_run_simulated"
    assert data["provenance"]["real_clients_constructed"] == []
    assert data["execution"]["downstream"]["clean"]
    for expected in ("strict, qa (24)", "strict, summarize (7)", "(1): L19", "(2): L17 L20",
                     "Planned calls: Bedrock 71, TypeSafe 71, local rules 68",
                     "Hard ceilings: Bedrock $0.60", "9d4f2da1393b3ddd", "Downstream isolation: CLEAN"):
        assert expected in printed, expected


def test_cli_refuses_live_runs_inside_pytest(capsys):
    assert cli.main(["--live", "typesafe", "--routers", "jev"]) == 2
    assert "never made from inside pytest" in capsys.readouterr().err


def test_verification_dry_run_plans_exactly_two_approved_calls(tmp_path):
    plan = build_verification_plan()
    assert [(c.router, c.case_id) for c in plan.schedule] == [("jev", "L01"), ("jev", "L12")]
    assert plan.request_caps == {"bedrock": 0, "typesafe": 2}
    assert plan.cost_caps["typesafe"] == 0.01 and plan.feasible
    assert len(build_verification_plan(repeat_first=True).schedule) == 3
    assert cli.main(["verify-jev", "--output", str(tmp_path / "v.json")]) == 0
    checks = json.loads((tmp_path / "v.json").read_text(encoding="utf-8"))["metrics"]
    assert checks["all_schema_valid"] and [c["case_id"] for c in checks["calls"]] == ["L01", "L12"]


# --- Child processes: fresh-process isolation and individually selected tests -------------------------

def _child(args, tmp_path):
    env = dict(os.environ)  # this session's fake credentials and disabled .env
    env.update(HTTPS_PROXY="http://127.0.0.1:9", HTTP_PROXY="http://127.0.0.1:9",
               EVAL_RESULTS_PATH=str(tmp_path / "must-not-exist.json"))
    for name in ("NO_PROXY", "PYTEST_ADDOPTS", "PYTEST_CURRENT_TEST"):
        env.pop(name, None)
    proc = subprocess.run([sys.executable, *args], cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


def test_child_process_dry_run_never_imports_downstream_code(tmp_path):
    code, output = _child(["-m", "experiments.router_bench", "--repetitions", "1"], tmp_path)
    assert code == 0, output
    assert "Downstream isolation: CLEAN" in output
    assert "modules imported during the run: none; loaded in this process: none" in output
    assert "Outbound network attempts intercepted by the offline guard: 0" in output


def test_child_process_individually_selected_benchmark_test_stays_offline(tmp_path):
    test_id = "tests/test_router_bench_safety.py::test_even_an_authorized_jev_client_cannot_reach_typesafe_under_pytest"
    code, output = _child(["-m", "pytest", "-p", "no:cacheprovider", "-q", test_id], tmp_path)
    assert code == 0, output
    assert "1 passed" in output and "offline guard active" in output
