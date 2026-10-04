"""One owner-authorized, isolated routing smoke; never application enablement.

The fixed run claim cannot be resumed or resent. Synthetic callers inject only
fakes. The dedicated CLI refuses pytest/its guard and never lifts that guard.
"""

import argparse
import contextlib
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import unquote, urlsplit

import httpx

from experiments.router_bench.persistence import RunJournal
from experiments.router_bench.safety import (
    DownstreamTripwire,
    Ledger,
    LiveAuthorization,
    SecretValue,
    contains_registered_secret,
)

RUN_ID = "2026-10-03-owner-routing-smoke-01"
MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
REGION = "us-east-1"
AWS_ENDPOINT = "https://bedrock-runtime.us-east-1.amazonaws.com"
MAX_OUTPUT = 256
CAPS = {"typesafe": 0.02, "bedrock": 0.03, "total": 0.05}
PRICES = {"typesafe": [0.042, 0.0], "bedrock": [1.10, 5.50]}
PRICE_RETRIEVED_UTC = "2026-10-04T00:41:03Z"
PRICE_SOURCES = [
    "https://docs.typesafe.ai/models",
    "https://aws.amazon.com/bedrock/pricing/",
    "https://aws.amazon.com/jp/blogs/news/amazon-bedrock-now-supports-japan-cross-region-inference/",
    "https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html",
    "https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html",
    "https://docs.aws.amazon.com/bedrock/latest/userguide/count-tokens.html",
]
CASES = (
    ("Q1", "What was the fictional Maple Bank's net revenue in 2025?", "qa"),
    (
        "Q2",
        "How much total debt did the fictional Cedar Fund report at year-end?",
        "qa",
    ),
    ("Q3", "What was the fictional Birch Company's diluted earnings per share?", "qa"),
    (
        "S1",
        "Summarize the main business risks in the fictional Maple Bank's annual report.",
        "summarize",
    ),
    (
        "S2",
        "Give a high-level overview of the fictional Cedar Fund's investment strategy.",
        "summarize",
    ),
    (
        "S3",
        "Summarize the major financial performance trends for the fictional Birch Company.",
        "summarize",
    ),
)


class SmokeError(RuntimeError):
    """Internal fixed codes only."""


def require(ok, code):
    if not ok:
        raise SmokeError(code)


def canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    raw = canonical(value)
    require(not contains_registered_secret(raw.decode()), "artifact_secret")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return digest(raw)


def prompts():
    # Normal .env loading occurs only in the CLI factory, before this import.
    from app.agents.router import _SYSTEM_PROMPT, _USER_PROMPT_TEMPLATE
    from app.agents.jev_router import payload

    return {
        cid: {
            "jev": payload(query),
            "haiku": {
                "system": [{"text": _SYSTEM_PROMPT}],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": _USER_PROMPT_TEMPLATE.format(query=query)}
                        ],
                    }
                ],
            },
        }
        for cid, query, _ in CASES
    }


class Permit:
    """One dispatch and one wire attempt, issued only after durable reservation."""

    def __init__(self):
        self.active = None
        self.dispatches = self.wires = 0

    def arm(self, provider, request):
        self.active = (provider, digest(canonical(request)))
        self.dispatches = self.wires = 0

    def consume(self, provider, request):
        require(
            self.active == (provider, digest(canonical(request)))
            and self.dispatches == 0,
            "dispatch_not_reserved",
        )
        self.dispatches += 1

    def wire(self):
        require(
            self.active is not None and self.dispatches == 1 and self.wires == 0,
            "extra_wire_attempt",
        )
        self.wires += 1

    def clear(self):
        self.active = None


class JevBridge:
    """Preserves the candidate's exact MockTransport constructor and streamed parser.

    Only the isolated smoke creates the external client. Its response remains
    streaming and is closed by the unchanged candidate response context manager.
    """

    def __init__(self, client, key, permit):
        self.client, self.key, self.permit = client, key, permit

    def __call__(self, request):
        from app.agents.jev_router import ENDPOINT

        require(
            request.method == "POST" and str(request.url) == ENDPOINT, "jev_endpoint"
        )
        value = json.loads(request.content)
        self.permit.consume("typesafe", value)
        self.permit.wire()
        outgoing = self.client.build_request(
            "POST",
            ENDPOINT,
            json=value,
            headers={"Authorization": "Bearer " + self.key.reveal()},
        )
        return self.client.send(outgoing, stream=True)


class HaikuBridge:
    def __init__(self, client, permit):
        self.client, self.permit = client, permit

    def converse(self, **request):
        require(request.pop("modelId") == MODEL, "haiku_model")
        self.permit.consume("bedrock", request)
        response = self.client.converse(
            modelId=MODEL,
            **request,
            inferenceConfig={"maxTokens": MAX_OUTPUT},
            performanceConfig={"latency": "standard"},
            serviceTier={"type": "default"},
        )
        require(
            response.get("serviceTier", {"type": "default"}).get("type") == "default",
            "served_tier_mismatch",
        )
        return response


def agents(client, jev_client, key, permit):
    from app.agents.router import RouterAgent
    from app.agents.jev_router import JevRouterAgent

    # Only constructor wiring differs: route() is the existing pinned control.
    class SmokeHaiku(RouterAgent):
        def __init__(self):
            self._client = HaikuBridge(client, permit)
            self._model_id = MODEL
            self.latency_ms = 0.0

    return {
        "typesafe": JevRouterAgent(
            transport=httpx.MockTransport(JevBridge(jev_client, key, permit))
        ),
        "bedrock": SmokeHaiku(),
    }


class AwsWireGuard:
    def __init__(self, permit):
        self.permit = permit
        self.count_calls = 0

    def __call__(self, request, **kwargs):
        url = urlsplit(request.url)
        require(
            url.scheme == "https"
            and url.netloc == "bedrock-runtime.us-east-1.amazonaws.com"
            and not url.query
            and request.method == "POST",
            "aws_endpoint",
        )
        path = unquote(url.path)
        if path == "/model/" + MODEL + "/count-tokens":
            require(
                self.permit.active is None and self.count_calls < 6, "extra_token_count"
            )
            self.count_calls += 1
        else:
            require(path == "/model/" + MODEL + "/converse", "aws_operation")
            self.permit.wire()


def validate_settings(settings):
    require(
        settings.get("BEDROCK_MODEL_ID", MODEL) == MODEL
        and settings.get("AWS_DEFAULT_REGION", REGION) == REGION
        and settings.get("AWS_REGION", REGION) == REGION,
        "configuration_model_region",
    )
    require(bool(settings.get("TYPESAFE_API_KEY")), "typesafe_credentials_missing")
    require(
        bool(settings.get("AWS_ACCESS_KEY_ID"))
        and bool(settings.get("AWS_SECRET_ACCESS_KEY"))
        and not settings.get("AWS_BEARER_TOKEN_BEDROCK"),
        "aws_credentials_missing_or_tier",
    )


def configure_live(permit):
    require(
        "PYTEST_CURRENT_TEST" not in os.environ
        and "tests.offline_guard" not in sys.modules
        and os.getenv("PYTHON_DOTENV_DISABLED") != "1",
        "offline_guard_active",
    )
    from dotenv import load_dotenv
    import boto3
    from botocore.config import Config
    from app.agents.jev_router import ENDPOINT

    main_root = Path(__file__).resolve().parents[2]
    load_dotenv(main_root / ".env", override=False)
    validate_settings(os.environ)
    # This task's existing credentials are environment/.env AWS signing keys.
    # No discovery of unrelated credential files, metadata or new auth flows.
    LiveAuthorization({"bedrock", "typesafe"})
    key = SecretValue(os.environ["TYPESAFE_API_KEY"])
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        if os.getenv(name):
            SecretValue(os.environ[name])
    client = boto3.client(
        "bedrock-runtime",
        region_name=REGION,
        endpoint_url=AWS_ENDPOINT,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        config=Config(
            retries={"mode": "standard", "total_max_attempts": 1},
            connect_timeout=2,
            read_timeout=10,
            proxies={},
            signature_version="v4",
        ),
    )
    require(
        client.meta.config.retries.get("total_max_attempts") == 1
        and client.meta.region_name == REGION,
        "aws_retry_configuration",
    )
    client.meta.events.register("before-send.bedrock-runtime", AwsWireGuard(permit))
    for name in ("httpx", "httpcore", "botocore", "boto3"):
        logging.getLogger(name).setLevel(logging.WARNING)

    def endpoint(request):
        require(
            request.method == "POST" and str(request.url) == ENDPOINT, "jev_endpoint"
        )

    external = httpx.Client(
        transport=httpx.HTTPTransport(retries=0),
        trust_env=False,
        follow_redirects=False,
        timeout=httpx.Timeout(5, connect=2),
        event_hooks={"request": [endpoint]},
    )
    return client, external, key


def source_inventory():
    root = Path(__file__).resolve().parents[2]
    previous = json.loads(
        (
            root.parent
            / "heldout-external/jev-upgrade-streaming/2026-10-03-f73914f/candidate-checkpoint.json"
        ).read_bytes()
    )
    names = (
        set(previous["source_files"])
        | set(previous["test_files"])
        | {
            str(root / "experiments/jev_candidate/live_smoke.py"),
            str(root / "tests/test_jev_live_smoke.py"),
        }
    )
    result = {}
    head = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    )
    for name in sorted(names):
        path = Path(name)
        relative = path.resolve().relative_to(root).as_posix()
        raw = path.read_bytes()
        require(
            subprocess.check_output(["git", "show", head + ":" + relative], cwd=root)
            == raw.replace(b"\r\n", b"\n"),
            "uncommitted_source",
        )
        result[relative] = digest(raw)
    return {"head": head, "files": result, "sha256": digest(canonical(result))}


def execute(directory, factory, inventory, *, live=False):
    """Fixed schedule; factory injection is for invented offline tests only."""
    directory.mkdir(parents=True, exist_ok=False)  # claim before auth/counting
    journal = RunJournal(str(directory / "run.journal.jsonl"))
    permit = Permit()
    ledger = Ledger({"bedrock": 6, "typesafe": 6}, dict(CAPS))
    results, counts = [], {}
    status = "STOPPED"
    code = None
    phase = "configuration"
    active = None
    client = external = None
    routers = {}
    try:
        journal.event(
            "run_started",
            run_id=RUN_ID,
            ceilings=CAPS,
            maximum_requests={"typesafe": 6, "bedrock": 6, "total": 12},
            prices=PRICES,
            source_hash=inventory["sha256"],
            candidate_commit=inventory["head"],
        )
        write(directory / "source-inventory.json", inventory)
        client, external, key = factory(permit)
        instructions = prompts()
        write(
            directory / "plan.json",
            {
                "schema": "isolated-routing-smoke-plan-v1",
                "run_id": RUN_ID,
                "cases": CASES,
                "complete_prompts": instructions,
                "models": {"typesafe": "jev-1.13.0", "bedrock": MODEL},
                "region": REGION,
                "tier": "default_standard",
                "haiku_max_output_tokens": MAX_OUTPUT,
                "jev_max_input_tokens": 64000,
                "ceilings_usd": CAPS,
                "prices_per_million": PRICES,
                "price_retrieved_utc": PRICE_RETRIEVED_UTC,
                "price_sources": PRICE_SOURCES,
                "source_inventory_sha256": inventory["sha256"],
                "candidate_commit": inventory["head"],
                "retries": 0,
                "provider_order_per_case": ["typesafe", "bedrock"],
                "evidence_class": "EXPLORATORY_NOT_QUALIFICATION",
                "actual_live": live,
            },
        )
        # Official CountTokens is non-inference, free, and matches billed inputs
        # for identical Converse system/messages. Failure stops before inference.
        phase = "token_count_preflight"
        for cid, _, _ in CASES:
            journal.event("token_count_started", case_id=cid)
            count = client.count_tokens(
                modelId=MODEL, input={"converse": instructions[cid]["haiku"]}
            )["inputTokens"]
            require(type(count) is int and 0 < count <= 2048, "input_token_bound")
            counts[cid] = count
            journal.event("token_count_completed", case_id=cid, input_tokens=count)
        reservations = {
            cid: {
                "typesafe": 64000 * PRICES["typesafe"][0] / 1e6,
                "bedrock": (
                    counts[cid] * PRICES["bedrock"][0]
                    + MAX_OUTPUT * PRICES["bedrock"][1]
                )
                / 1e6,
            }
            for cid, _, _ in CASES
        }
        write(
            directory / "reservations.json",
            {
                "schema": "isolated-routing-smoke-reservations-v1",
                "counts": counts,
                "per_request_usd": reservations,
                "expected_cost_usd": {
                    "typesafe": 6 * 410 * 0.042 / 1e6,
                    "bedrock": sum((v * 1.1 + 52 * 5.5) / 1e6 for v in counts.values()),
                },
                "expectation_basis": "Haiku exact CountTokens + historical 52 output; Jev historical 410 input, not guaranteed",
                "worst_case_total_usd": {
                    p: sum(r[p] for r in reservations.values())
                    for p in ("typesafe", "bedrock")
                },
            },
        )
        require(
            sum(r["bedrock"] for r in reservations.values()) <= CAPS["bedrock"]
            and sum(sum(r.values()) for r in reservations.values()) <= CAPS["total"],
            "plan_budget",
        )
        routers = agents(client, external, key, permit)
        from app.observability import request_trace

        with DownstreamTripwire() as tripwire:
            phase = "routing_inference"
            for cid, query, expected in CASES:
                for provider in ("typesafe", "bedrock"):
                    amount = reservations[cid][provider]
                    active = ledger.reserve(provider, amount)
                    journal.event(
                        "call_started",
                        case_id=cid,
                        provider=provider,
                        reserved_usd=amount,
                        request_sha256=digest(
                            canonical(
                                instructions[cid][
                                    "jev" if provider == "typesafe" else "haiku"
                                ]
                            )
                        ),
                    )
                    permit.arm(
                        provider,
                        instructions[cid]["jev" if provider == "typesafe" else "haiku"],
                    )
                    start = time.monotonic()
                    with (
                        request_trace("isolated_owner_smoke") as trace,
                        contextlib.redirect_stdout(io.StringIO()),
                    ):
                        decision = routers[provider].route(query)
                    latency = (time.monotonic() - start) * 1000
                    outcome = trace.route.get("router_outcome")
                    calls = trace.model_calls
                    usage = (
                        (calls[0].get("input_tokens"), calls[0].get("output_tokens"))
                        if len(calls) == 1
                        else (None, None)
                    )
                    valid_usage = (
                        all(type(v) is int and v >= 0 for v in usage) and usage[0] > 0
                    )
                    if valid_usage:
                        valid_usage = (
                            usage[0] <= 64000
                            if provider == "typesafe"
                            else usage[0] == counts[cid] and usage[1] <= MAX_OUTPUT
                        )
                    cost = (
                        (
                            usage[0] * PRICES[provider][0]
                            + usage[1] * PRICES[provider][1]
                        )
                        / 1e6
                        if valid_usage
                        else None
                    )
                    _, exceeded = ledger.settle(active, cost)
                    active = None
                    raw_label = trace.route.get(
                        "model_task_type",
                        decision.task_type if outcome == "model" else None,
                    )
                    score = trace.route.get(
                        "model_confidence",
                        decision.confidence if outcome == "model" else None,
                    )
                    error = trace.route.get("router_error_type")
                    # Never serialize arbitrary provider text, reasoning or exception details.
                    row = {
                        "case_id": cid,
                        "provider": provider,
                        "expected_route": expected,
                        "chosen_route": decision.task_type,
                        "raw_route": raw_label,
                        "score": score,
                        "fallback": outcome != "model",
                        "outcome": outcome,
                        "client_latency_ms": round(latency, 3),
                        "input_tokens": usage[0] if valid_usage else None,
                        "output_tokens": usage[1] if valid_usage else None,
                        "cost_usd": cost,
                        "retained_unknown_reservation_usd": amount
                        if cost is None
                        else 0,
                        "error_code": error
                        if isinstance(error, str)
                        and error.replace("_", "").isalnum()
                        and len(error) <= 64
                        else None,
                    }
                    results.append(row)
                    journal.event("call_completed", **row)
                    require(
                        permit.dispatches == permit.wires == 1
                        and trace.route.get("router_attempts") == 1
                        and not tripwire.calls
                        and not any(
                            n in sys.modules and n not in tripwire._preloaded
                            for n in tripwire.report()["downstream_modules_guarded"]
                        ),
                        "unexpected_activity",
                    )
                    permit.clear()
                    require(not exceeded and valid_usage, "usage_accounting_failure")
                    require(
                        outcome in {"model", "fallback_low_confidence"},
                        "provider_failure",
                    )
            require(tripwire.report()["clean"], "downstream_activity")
        status = "COMPLETED"
    except (Exception, KeyboardInterrupt) as failure:
        code = (
            str(failure)
            if isinstance(failure, SmokeError)
            else "configuration_or_provider_failure"
        )
        if isinstance(failure, KeyboardInterrupt):
            code = "interrupted_unknown_outcome"
        # AWS codes are allowlisted; never expose the server message/request IDs.
        if hasattr(failure, "response") and isinstance(failure.response, dict):
            aws_code = failure.response.get("Error", {}).get("Code")
            if aws_code in {
                "ValidationException",
                "AccessDeniedException",
                "UnrecognizedClientException",
                "ExpiredTokenException",
                "ThrottlingException",
                "ServiceUnavailableException",
                "ResourceNotFoundException",
            }:
                code = aws_code
        if active is not None:
            ledger.settle(active, None)
    finally:
        permit.clear()
        for resource in [routers.get("typesafe"), external, client]:
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    status, code = "STOPPED", "resource_close_failure"
        report = {
            "schema": "isolated-routing-smoke-result-v1",
            "run_id": RUN_ID,
            "status": status,
            "stop_code": code,
            "last_phase": phase,
            "results": results,
            "accounting": ledger.summary(),
            "token_counts": counts,
            "actual_live": live,
            "qualification": False,
            "deployment": False,
            "source_inventory_sha256": inventory["sha256"],
            "candidate_commit": inventory["head"],
        }
        journal.event(
            "run_finished" if status == "COMPLETED" else "run_stopped",
            status=status,
            code=code,
            accounting=ledger.summary(),
        )
        journal.close()
        write(directory / "result.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-owner-smoke", action="store_true")
    args = parser.parse_args()
    require(args.execute_owner_smoke, "explicit_opt_in_required")
    root = Path(__file__).resolve().parents[2].parent
    directory = root / "heldout-external/jev-isolated-live-smoke" / RUN_ID
    require(
        not directory.is_symlink()
        and directory.resolve().is_relative_to(root / "heldout-external"),
        "run_path",
    )
    report = execute(directory, configure_live, source_inventory(), live=True)
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0 if report["status"] == "COMPLETED" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeError, OSError):
        print("smoke_stopped:configuration_or_existing_run", file=sys.stderr)
        raise SystemExit(2) from None
