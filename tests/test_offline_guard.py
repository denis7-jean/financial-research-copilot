"""The offline guard and the live-evaluation opt-in.

Regression for the 2026-09-28 incident (docs/incidents/2026-09-28-unguarded-live-eval-test-run.md):
`pytest eval/test_llm_judge.py` ran the paid evaluation with real `.env` credentials,
because the network guard lived in tests/conftest.py and only loaded when tests/
was collected.

The subprocess tests run the real eval test file in a child pytest. As a second
barrier, the child inherits this session's fake credentials and disabled `.env`,
and gets an unreachable HTTPS proxy, so even a broken guard could not reach AWS.
"""
import asyncio
import os
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import boto3
import httpx
import pytest
from dotenv import load_dotenv

from eval import test_llm_judge
from tests import offline_guard
from tests.conftest import NetworkBlockedError, isolated_blocked_requests

REPO = Path(__file__).resolve().parents[1]
EVAL_TESTS = "eval/test_llm_judge.py"
LIVE_TESTS = 5  # llm-marked tests in eval/test_llm_judge.py


def test_attempt_logs_are_isolated_and_retained_even_on_failure(monkeypatch):
    previous = ["invented:earlier-test"]
    monkeypatch.setattr(offline_guard, "blocked_requests", previous)
    with pytest.raises(RuntimeError, match="invented failure"):
        with isolated_blocked_requests():
            assert offline_guard.is_installed()
            assert offline_guard.blocked_requests == []
            with pytest.raises(NetworkBlockedError):
                offline_guard._block("invented:current-test", "synthetic guard check")
            assert offline_guard.blocked_requests == ["invented:current-test"]
            assert previous == ["invented:earlier-test"]
            raise RuntimeError("invented failure")
    assert offline_guard.blocked_requests is previous
    assert previous == ["invented:earlier-test", "invented:current-test"]
    with isolated_blocked_requests():
        assert offline_guard.blocked_requests == []
    assert offline_guard.blocked_requests is previous
    assert previous == ["invented:earlier-test", "invented:current-test"]


def test_guard_is_installed_for_the_offline_session():
    assert offline_guard.is_installed()
    assert os.environ["AWS_ACCESS_KEY_ID"] == "unit-test-fake-key"
    assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"
    for name in ("AWS_SESSION_TOKEN", "AWS_PROFILE", "AWS_BEARER_TOKEN_BEDROCK"):
        assert name not in os.environ


def test_dotenv_files_are_never_loaded(tmp_path, monkeypatch):
    monkeypatch.delenv("OFFLINE_GUARD_PROBE", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("OFFLINE_GUARD_PROBE=loaded\n", encoding="utf-8")
    assert load_dotenv(env_file) is False
    assert "OFFLINE_GUARD_PROBE" not in os.environ


def test_boto3_resolves_only_the_fake_credentials():
    credentials = boto3.Session().get_credentials()
    assert credentials.access_key == "unit-test-fake-key"
    assert credentials.method == "env"


# --- Non-AWS network: TypeSafe (Jev) and any other host ---------------------------------------

TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
CANARY_KEY = "ts-canary-not-a-real-key"


def test_typesafe_api_key_is_removed():
    assert "TYPESAFE_API_KEY" not in os.environ


def test_httpx_cannot_reach_typesafe_and_never_records_credentials():
    before = len(offline_guard.blocked_requests)
    with httpx.Client() as client, pytest.raises(NetworkBlockedError) as excinfo:
        client.post(TYPESAFE_URL + "?probe=1", headers={"Authorization": f"Bearer {CANARY_KEY}"},
                    json={"state": "q", "model": "jev-1.13.0"})
    assert offline_guard.blocked_requests[before:] == [TYPESAFE_URL]
    assert CANARY_KEY not in str(excinfo.value)
    assert all(CANARY_KEY not in entry for entry in offline_guard.blocked_requests)


def test_async_httpx_cannot_reach_typesafe():
    async def call():
        async with httpx.AsyncClient() as client:
            await client.post(TYPESAFE_URL, headers={"Authorization": f"Bearer {CANARY_KEY}"}, json={})

    with pytest.raises(NetworkBlockedError):
        asyncio.run(call())


@pytest.mark.parametrize("attempt", [
    lambda: socket.create_connection(("api.typesafe.ai", 443), timeout=1),
    lambda: socket.getaddrinfo("api.typesafe.ai", 443),
    lambda: socket.socket().connect(("8.8.8.8", 53)),
    lambda: socket.socket().connect_ex(("2001:4860:4860::8888", 53)),
    # Bypass environment proxies: a loopback proxy is (correctly) allowed.
    lambda: urllib.request.build_opener(urllib.request.ProxyHandler({})).open(TYPESAFE_URL, timeout=1),
], ids=["create_connection", "dns", "connect", "connect_ex", "urllib"])
def test_every_other_outbound_path_is_blocked(attempt):
    with pytest.raises(NetworkBlockedError):
        attempt()


def test_loopback_connections_still_work():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    try:
        client = socket.create_connection(server.getsockname(), timeout=2)
        client.close()
    finally:
        server.close()
    assert socket.getaddrinfo("localhost", 80)


def test_blocked_requests_are_recorded():
    before = len(offline_guard.blocked_requests)
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    with pytest.raises(NetworkBlockedError):
        client.converse(modelId="m", messages=[{"role": "user", "content": [{"text": "hi"}]}])
    assert len(offline_guard.blocked_requests) == before + 1
    assert offline_guard.blocked_requests[-1].startswith("https://bedrock-runtime.us-east-1.amazonaws.com/")


# --- The live fixture's own check (independent of the root conftest hooks) ------------------

class _Config:
    def __init__(self, options: dict):
        self.options = options

    def getoption(self, name, default=None):
        return self.options.get(name, default)


def test_live_fixture_skips_without_the_option():
    with pytest.raises(pytest.skip.Exception, match="--run-live-eval"):
        test_llm_judge._authorize_live_run(_Config({}))


def test_live_fixture_refuses_while_the_guard_is_installed():
    with pytest.raises(pytest.fail.Exception, match="guard is still installed"):
        test_llm_judge._authorize_live_run(_Config({"run_live_eval": True}))


def test_live_fixture_allows_an_authorized_run(monkeypatch):
    monkeypatch.setattr(offline_guard, "is_installed", lambda: False)
    test_llm_judge._authorize_live_run(_Config({"run_live_eval": True}))


# --- Child pytest runs of the real eval test file -------------------------------------------

def _pytest(tmp_path, *args):
    env = dict(os.environ)  # fake credentials, PYTHON_DOTENV_DISABLED=1
    env.update(HTTPS_PROXY="http://127.0.0.1:9", HTTP_PROXY="http://127.0.0.1:9",
               EVAL_RESULTS_PATH=str(tmp_path / "must-not-exist.json"))
    env.pop("NO_PROXY", None)
    env.pop("PYTEST_ADDOPTS", None)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
         "-p", "no:logfire", "-p", "no:pytest_logfire", "-q", *args],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=300,
    )
    output = proc.stdout + proc.stderr
    assert not (tmp_path / "must-not-exist.json").exists(), output
    return proc.returncode, output


def test_child_pytest_keeps_offline_plugin_policy(tmp_path, monkeypatch):
    from types import SimpleNamespace

    calls = []

    def captured(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout="invented stdout", stderr="")

    monkeypatch.setattr(subprocess, "run", captured)
    assert _pytest(tmp_path, EVAL_TESTS) == (0, "invented stdout")
    argv, options = calls[0]
    assert argv == [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
                    "-p", "no:logfire", "-p", "no:pytest_logfire", "-q", EVAL_TESTS]
    assert options["cwd"] == REPO
    assert options["capture_output"] is True and options["timeout"] == 300
    assert "PYTEST_ADDOPTS" not in options["env"]
    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD" not in options["env"]
    assert options["env"]["PYTHON_DOTENV_DISABLED"] == "1"
    assert options["env"]["AWS_ACCESS_KEY_ID"] == "unit-test-fake-key"


def test_selecting_the_eval_file_alone_is_a_usage_error(tmp_path):
    code, output = _pytest(tmp_path, EVAL_TESTS)
    assert code == pytest.ExitCode.USAGE_ERROR, output
    assert "live execution was not authorized" in output


def test_selecting_live_tests_by_marker_without_opt_in_is_a_usage_error(tmp_path):
    code, output = _pytest(tmp_path, EVAL_TESTS, "-m", "llm")
    assert code == pytest.ExitCode.USAGE_ERROR, output
    assert "--run-live-eval" in output


def test_live_tests_are_skipped_in_a_mixed_offline_run(tmp_path):
    code, output = _pytest(tmp_path, EVAL_TESTS, "tests/test_harness.py", "-rs")
    assert code == pytest.ExitCode.OK, output
    assert f"{LIVE_TESTS} skipped" in output
    assert "requires --run-live-eval" in output
    assert "offline guard active" in output


def test_bypassing_the_root_conftest_still_cannot_start_a_live_run(tmp_path):
    code, output = _pytest(tmp_path, "--noconftest", EVAL_TESTS, "-rs")
    assert code == pytest.ExitCode.OK, output
    assert f"{LIVE_TESTS} skipped" in output
    assert "live, billable evaluation not authorized" in output


def test_opt_in_refuses_offline_tests(tmp_path):
    code, output = _pytest(tmp_path, "--run-live-eval", "tests/test_harness.py")
    assert code == pytest.ExitCode.USAGE_ERROR, output
    assert "contains offline tests" in output


def test_opt_in_is_accepted_for_live_tests(tmp_path):
    """Collection only: proves the opt-in is honored without running anything."""
    code, output = _pytest(tmp_path, "--run-live-eval", "--collect-only", EVAL_TESTS)
    assert code == pytest.ExitCode.OK, output
    assert f"{LIVE_TESTS} tests collected" in output
