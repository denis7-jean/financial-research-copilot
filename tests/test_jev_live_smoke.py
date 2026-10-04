"""Invented clients, streams and workspaces only; root offline guard stays active."""

import json
from types import SimpleNamespace

import httpx
import pytest

from experiments.jev_candidate import live_smoke as s
from experiments.router_bench.safety import BudgetExhausted, SecretValue


class FakeBedrock:
    def __init__(self, permit, failure=None, count=300):
        self.permit, self.failure, self.count = permit, failure, count
        self.requests = []
        self.counts = []
        self.closed = False

    def count_tokens(self, **request):
        self.counts.append(request)
        if self.failure == "count":
            raise RuntimeError("invented-private-secret")
        return {"inputTokens": self.count}

    def converse(self, **request):
        self.permit.wire()
        self.requests.append(request)
        if self.failure == "timeout":
            raise TimeoutError("invented-private-secret")
        text = request["messages"][0]["content"][0]["text"]
        choice = (
            "summarize"
            if any(word in text.lower() for word in ("summarize", "overview"))
            else "qa"
        )
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": json.dumps(
                                {
                                    "task_type": choice,
                                    "confidence": 0.9,
                                    "reasoning": "invented",
                                }
                            )
                        }
                    ]
                }
            },
            "usage": {"inputTokens": self.count, "outputTokens": 20},
            "serviceTier": {"type": "default"},
        }

    def close(self):
        self.closed = True


class Stream(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False
        self.reads = 0

    def __iter__(self):
        for v in self.chunks:
            self.reads += 1
            yield v

    def close(self):
        self.closed = True


def factory(failure=None, count=300):
    state = SimpleNamespace(streams=[], jev_requests=[])

    def configure(permit):
        state.aws = FakeBedrock(permit, failure, count)

        def handler(request):
            state.jev_requests.append(request)
            assert str(request.url) == "https://api.typesafe.ai/v1/systemone"
            body = json.loads(request.content)
            choice = (
                "summarize"
                if any(
                    word in body["state"].lower() for word in ("summarize", "overview")
                )
                else "qa"
            )
            value = {
                "model": "jev-1.13.0",
                "answers": {
                    "route": {
                        "choice": choice,
                        "confidence": 0.8,
                        "probabilities": {
                            choice: 0.9,
                            ("qa" if choice == "summarize" else "summarize"): 0.1,
                        },
                    }
                },
                "usage": {"input_tokens": 400, "output_tokens": 30},
            }
            if failure == "version":
                value["model"] = "wrong"
            if failure == "usage":
                del value["usage"]
            if failure == "jev-timeout":
                raise httpx.ReadTimeout("invented-private-secret")
            raw = json.dumps(value).encode()
            stream = Stream(
                [b" " * 65537, b"never-read"]
                if failure == "oversize"
                else [raw[:13], raw[13:]]
            )
            state.streams.append(stream)
            return httpx.Response(401 if failure == "auth" else 200, stream=stream)

        state.external = httpx.Client(
            transport=httpx.MockTransport(handler),
            follow_redirects=False,
            trust_env=False,
        )
        return state.aws, state.external, SecretValue("invented-test-key")

    return configure, state


INVENTORY = {"head": "invented-commit", "sha256": "a" * 64, "files": {}}


def run(tmp_path, failure=None, count=300):
    configure, state = factory(failure, count)
    directory = tmp_path / "invented-run"
    result = s.execute(directory, configure, INVENTORY)
    return result, state, directory


def test_complete_fixed_six_by_two_schedule_and_prompt_limits(tmp_path):
    result, state, directory = run(tmp_path)
    assert result["status"] == "COMPLETED" and len(result["results"]) == 12
    assert (
        len(state.jev_requests) == len(state.aws.requests) == len(state.aws.counts) == 6
    )
    assert all(r["chosen_route"] == r["expected_route"] for r in result["results"])
    assert all(len(q) <= 300 for _, q, _ in s.CASES)
    assert all(stream.closed for stream in state.streams) and state.aws.closed
    for request in state.aws.requests:
        assert set(request) == {
            "modelId",
            "system",
            "messages",
            "inferenceConfig",
            "performanceConfig",
            "serviceTier",
        }
        assert request["modelId"] == s.MODEL and request["inferenceConfig"] == {
            "maxTokens": 256
        }
        assert request["serviceTier"] == {"type": "default"}
        assert request["performanceConfig"] == {"latency": "standard"}
    entries = [
        json.loads(v)
        for v in (directory / "run.journal.jsonl").read_text().splitlines()
    ]
    calls = [v for v in entries if v["type"].startswith("call_")]
    assert [v["type"] for v in calls] == ["call_started", "call_completed"] * 12
    assert all(v["reserved_usd"] > 0 for v in calls if v["type"] == "call_started")
    assert "invented-test-key" not in "".join(
        p.read_text() for p in directory.iterdir()
    )
    before = len(state.jev_requests), len(state.aws.requests)
    with pytest.raises(FileExistsError):
        s.execute(directory, lambda _: pytest.fail("re-entry factory"), INVENTORY)
    assert before == (6, 6)


@pytest.mark.parametrize(
    "failure,attempts",
    [
        ("auth", (1, 0)),
        ("version", (1, 0)),
        ("usage", (1, 0)),
        ("oversize", (1, 0)),
        ("jev-timeout", (1, 0)),
        ("timeout", (1, 1)),
        ("count", (0, 0)),
    ],
)
def test_failure_stops_every_provider_without_replacement(tmp_path, failure, attempts):
    result, state, directory = run(tmp_path, failure)
    assert result["status"] == "STOPPED"
    assert (len(state.jev_requests), len(state.aws.requests)) == attempts
    accounts = result["accounting"]["providers"]
    assert (
        accounts["typesafe"]["requests"],
        accounts["bedrock"]["requests"],
    ) == attempts
    if attempts[0] and failure != "timeout":
        assert accounts["typesafe"]["charged_at_worst_case"] == 1
        assert accounts["typesafe"]["committed_usd"] == pytest.approx(0.002688)
    if failure == "timeout":
        assert accounts["bedrock"]["charged_at_worst_case"] == 1
    if failure == "oversize":
        assert state.streams[0].closed and state.streams[0].reads == 1
    assert all(v.closed for v in state.streams)
    assert "invented-private-secret" not in "".join(
        p.read_text() for p in directory.iterdir()
    )


@pytest.mark.parametrize(
    "caps",
    [
        {"bedrock": 0.03, "typesafe": 0, "total": 0.05},
        {"bedrock": 0.03, "typesafe": 0.02, "total": 0.0001},
    ],
)
def test_monetary_cap_blocks_before_dispatch(tmp_path, monkeypatch, caps):
    monkeypatch.setattr(s, "CAPS", caps)
    result, state, _ = run(tmp_path)
    assert (
        result["status"] == "STOPPED" and state.jev_requests == state.aws.requests == []
    )


def test_seventh_request_and_duplicate_dispatch_are_blocked():
    ledger = s.Ledger({"bedrock": 6, "typesafe": 6}, dict(s.CAPS))
    for _ in range(6):
        ledger.settle(ledger.reserve("typesafe", 0.002688), None)
    with pytest.raises(BudgetExhausted):
        ledger.reserve("typesafe", 0.002688)
    permit = s.Permit()
    with pytest.raises(s.SmokeError, match="dispatch_not_reserved"):
        permit.consume("typesafe", {})
    permit.arm("typesafe", {})
    permit.consume("typesafe", {})
    permit.wire()
    with pytest.raises(s.SmokeError, match="extra_wire_attempt"):
        permit.wire()
    with pytest.raises(s.SmokeError, match="dispatch_not_reserved"):
        permit.consume("typesafe", {})


def test_configuration_failure_has_no_token_or_inference_calls(tmp_path):
    result = s.execute(
        tmp_path / "invented",
        lambda _: (_ for _ in ()).throw(s.SmokeError("typesafe_credentials_missing")),
        INVENTORY,
    )
    assert result["stop_code"] == "typesafe_credentials_missing"
    assert not result["results"] and not result["token_counts"]
    with pytest.raises(s.SmokeError, match="offline_guard_active"):
        s.configure_live(s.Permit())


@pytest.mark.parametrize(
    "url",
    [
        "https://unexpected.invalid/x",
        s.AWS_ENDPOINT + "/model/wrong/converse",
        s.AWS_ENDPOINT + "/model/" + s.MODEL + "/invoke",
    ],
)
def test_wire_allowlist_rejects_other_hosts_models_operations(url):
    with pytest.raises(s.SmokeError):
        s.AwsWireGuard(s.Permit())(SimpleNamespace(url=url, method="POST"))


def test_counted_prompt_is_exact_control_prompt(tmp_path):
    result, state, _ = run(tmp_path)
    assert result["status"] == "COMPLETED"
    assert [r["input"]["converse"] for r in state.aws.counts] == [
        {k: r[k] for k in ("system", "messages")} for r in state.aws.requests
    ]


@pytest.mark.parametrize(
    "key,value,code",
    [
        ("TYPESAFE_API_KEY", "", "typesafe_credentials_missing"),
        ("AWS_ACCESS_KEY_ID", "", "aws_credentials_missing_or_tier"),
        ("BEDROCK_MODEL_ID", "wrong", "configuration_model_region"),
        ("AWS_DEFAULT_REGION", "wrong", "configuration_model_region"),
    ],
)
def test_missing_or_wrong_settings_reject_before_clients(key, value, code):
    settings = {
        "TYPESAFE_API_KEY": "invented",
        "AWS_ACCESS_KEY_ID": "invented",
        "AWS_SECRET_ACCESS_KEY": "invented",
    }
    settings[key] = value
    with pytest.raises(s.SmokeError, match=code):
        s.validate_settings(settings)


def test_downstream_call_is_blocked_and_stops_run(tmp_path):
    configure, state = factory()

    def downstream(permit):
        values = configure(permit)
        original = state.aws.converse

        def attempted(**kwargs):
            original(**kwargs)
            from app.agents.qa_agent import QAAgent

            QAAgent.run(None, "invented")

        state.aws.converse = attempted
        return values

    result = s.execute(tmp_path / "invented", downstream, INVENTORY)
    assert (
        result["status"] == "STOPPED"
        and len(state.jev_requests) == len(state.aws.requests) == 1
    )


def test_import_is_pure_in_fresh_guarded_process():
    import subprocess
    import sys

    source = "from tests.offline_guard import install; install(); import sys; import experiments.jev_candidate.live_smoke; assert not any(x.startswith('app.') for x in sys.modules)"
    result = subprocess.run([sys.executable, "-B", "-c", source], capture_output=True)
    assert result.returncode == 0
