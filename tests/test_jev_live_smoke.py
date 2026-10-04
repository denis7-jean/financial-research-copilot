"""Invented clients, streams and workspaces only; root offline guard stays active."""

from decimal import Decimal
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
        raise AssertionError("CountTokens is forbidden")

    def converse(self, **request):
        self.permit.wire()
        self.requests.append(request)
        if self.failure == "timeout":
            raise TimeoutError("invented-private-secret")
        if self.failure == "interrupt":
            raise KeyboardInterrupt()
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
            "usage": {
                "inputTokens": self.count,
                "outputTokens": 257 if self.failure == "output-bound" else 20,
            },
            "serviceTier": {"type": "default"},
            "ResponseMetadata": {"RetryAttempts": 0},
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
        len(state.jev_requests) == len(state.aws.requests) == 6
        and state.aws.counts == []
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
    assert all(
        Decimal(v["reserved_usd"]) > 0 for v in calls if v["type"] == "call_started"
    )
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
        ("interrupt", (1, 1)),
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
    if attempts[0] and failure not in {"timeout", "interrupt"}:
        assert accounts["typesafe"]["charged_at_worst_case"] == 1
        assert accounts["typesafe"]["committed_usd"] == Decimal("0.002688")
    if failure in {"timeout", "interrupt"}:
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
        {"bedrock": "1.33", "typesafe": "0", "total": "1.35"},
        {"bedrock": "1.33", "typesafe": "0.02", "total": "1.344575999"},
        {"bedrock": "1.328447999", "typesafe": "0.02", "total": "1.35"},
    ],
)
def test_monetary_cap_blocks_before_dispatch(tmp_path, monkeypatch, caps):
    monkeypatch.setattr(s, "CAPS", {k: Decimal(v) for k, v in caps.items()})
    result, state, _ = run(tmp_path)
    assert (
        result["status"] == "STOPPED" and state.jev_requests == state.aws.requests == []
    )
    assert result["stop_code"] == "plan_budget"


def test_seventh_request_and_duplicate_dispatch_are_blocked():
    ledger = s.ExactLedger({"bedrock": 6, "typesafe": 6}, dict(s.CAPS))
    for _ in range(6):
        ledger.settle(ledger.reserve("typesafe", Decimal("0.002688")), None)
    with pytest.raises(BudgetExhausted):
        ledger.reserve("typesafe", Decimal("0.002688"))
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
    assert not result["results"] and result["input_bounds"] == s.MAX_INPUT
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


def test_recorded_prompt_is_exact_control_prompt_without_counting(tmp_path):
    result, state, directory = run(tmp_path)
    assert result["status"] == "COMPLETED" and state.aws.counts == []
    plan = json.loads((directory / "plan.json").read_bytes())
    assert [plan["complete_prompts"][cid]["haiku"] for cid, _, _ in s.CASES] == [
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


def test_exact_capacity_arithmetic_and_known_settlement(tmp_path):
    reservations = s.capacity_reservations()
    assert reservations == {
        "typesafe": Decimal("0.002688"),
        "bedrock": Decimal("0.221408"),
    }
    assert 6 * sum(reservations.values()) == Decimal("1.344576")
    result, _, directory = run(tmp_path)
    assert result["accounting"]["providers"]["bedrock"]["committed_usd"] == Decimal(
        "0.00264"
    )
    assert result["accounting"]["total_committed_usd"] == Decimal("0.0027408")
    recorded = json.loads((directory / "result.json").read_bytes())
    assert recorded["accounting"]["total_committed_usd"] == "0.0027408"
    assert json.loads((directory / "reservations.json").read_bytes())[
        "worst_case_total_usd"
    ] == {"bedrock": "1.328448", "typesafe": "0.016128"}
    ledger = s.ExactLedger({"bedrock": 6, "typesafe": 6}, s.CAPS)
    for _ in range(6):
        for provider, amount in reservations.items():
            ledger.settle(ledger.reserve(provider, amount), None)
    assert ledger.summary()["total_committed_usd"] == Decimal("1.344576")
    assert ledger.summary()["total_remaining_usd"] == Decimal("0.005424")


@pytest.mark.parametrize(
    "count,failure",
    [
        (200001, None),
        (202000, None),
        (300, "output-bound"),
        (True, None),
        (-1, None),
        (None, None),
        ("bad", None),
    ],
)
def test_usage_rejection_preserves_evidence_and_stops_next_call(
    tmp_path, count, failure
):
    result, state, directory = run(tmp_path, failure, count)
    assert result["status"] == "STOPPED"
    assert result["stop_code"] == "usage_accounting_failure"
    assert len(state.aws.requests) == len(state.jev_requests) == 1
    row = result["results"][-1]
    assert not row["usage_within_bounds"]
    account = result["accounting"]["providers"]["bedrock"]
    if type(count) is int and count >= 0:
        assert row["input_tokens"] == count
        assert row["output_tokens"] == (257 if failure else 20)
        assert account["committed_usd"] == s.charge(
            "bedrock", count, row["output_tokens"]
        )
        if (
            s.charge("bedrock", count, row["output_tokens"])
            > s.capacity_reservations()["bedrock"]
        ):
            assert account["reservations_exceeded"] == 1
    else:
        assert row["input_tokens"] is None
        assert account["committed_usd"] == Decimal("0.221408")
        assert account["charged_at_worst_case"] == 1
    assert "bad" not in (directory / "result.json").read_text()


def test_count_tokens_wire_operation_is_rejected():
    with pytest.raises(s.SmokeError, match="aws_operation"):
        s.AwsWireGuard(s.Permit())(
            SimpleNamespace(
                url=s.AWS_ENDPOINT + "/model/" + s.MODEL + "/count-tokens",
                method="POST",
            )
        )


def test_live_predecessor_identity_is_checked_before_dispatch(tmp_path, monkeypatch):
    configure, state = factory()
    old = tmp_path / s.PREDECESSOR_RUN_ID
    old.mkdir()
    raw = s.canonical({"cases": s.CASES, "complete_prompts": s.prompts()})
    (old / "plan.json").write_bytes(raw)
    monkeypatch.setattr(s, "PREDECESSOR_PLAN_SHA256", s.digest(raw))
    result = s.execute(tmp_path / "invented-successor", configure, INVENTORY, live=True)
    assert result["status"] == "COMPLETED"
    altered = json.loads(raw)
    altered["cases"][0][1] = "a changed invented question"
    (old / "plan.json").write_bytes(s.canonical(altered))
    result = s.execute(tmp_path / "invented-other", configure, INVENTORY, live=True)
    assert result["stop_code"] == "predecessor_plan_hash"
    assert state.aws.requests == [] and len(state.jev_requests) == 6


def test_missing_haiku_usage_keeps_full_reservation(tmp_path):
    configure, state = factory()

    def missing_usage(permit):
        values = configure(permit)
        original = state.aws.converse

        def response(**kwargs):
            value = original(**kwargs)
            del value["usage"]
            return value

        state.aws.converse = response
        return values

    result = s.execute(tmp_path / "invented", missing_usage, INVENTORY)
    assert result["stop_code"] == "usage_accounting_failure"
    assert len(state.aws.requests) == len(state.jev_requests) == 1
    assert result["accounting"]["providers"]["bedrock"]["committed_usd"] == Decimal(
        "0.221408"
    )


@pytest.mark.parametrize(
    "metadata", [None, {"RetryAttempts": True}, {"RetryAttempts": 1}]
)
def test_runner_stops_on_unknown_or_multiple_sdk_attempts(tmp_path, metadata):
    configure, state = factory()

    def unexpected_attempts(permit):
        values = configure(permit)
        original = state.aws.converse

        def response(**kwargs):
            value = original(**kwargs)
            if metadata is None:
                del value["ResponseMetadata"]
            else:
                value["ResponseMetadata"] = metadata
            return value

        state.aws.converse = response
        return values

    result = s.execute(tmp_path / "invented", unexpected_attempts, INVENTORY)
    assert result["status"] == "STOPPED"
    assert result["stop_code"] == "unexpected_activity"
    assert len(state.aws.requests) == len(state.jev_requests) == 1
    # Usage is known and settled before the existing attempt gate; that gate
    # must still stop the batch rather than coercing unknown metadata to one.
    assert result["accounting"]["providers"]["bedrock"]["committed_usd"] == Decimal(
        "0.00044"
    )


def test_reservation_checks_exact_provider_and_total_caps():
    for caps in (
        {"bedrock": "0.221407999", "typesafe": "0.02", "total": "1.35"},
        {"bedrock": "1.33", "typesafe": "0.02", "total": "0.221407999"},
    ):
        ledger = s.ExactLedger({"bedrock": 6, "typesafe": 6}, caps)
        with pytest.raises(BudgetExhausted):
            ledger.reserve("bedrock", Decimal("0.221408"))
        assert ledger.accounts["bedrock"].requests == 0


def test_transport_configuration_has_zero_retries():
    import ast

    tree = ast.parse(__import__("inspect").getsource(s.configure_live))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    config = next(
        n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "Config"
    )
    assert ast.literal_eval(
        next(k.value for k in config.keywords if k.arg == "retries")
    ) == {"mode": "standard", "total_max_attempts": 1}
    transport = next(
        n
        for n in calls
        if isinstance(n.func, ast.Attribute) and n.func.attr == "HTTPTransport"
    )
    assert (
        ast.literal_eval(
            next(k.value for k in transport.keywords if k.arg == "retries")
        )
        == 0
    )
