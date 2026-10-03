"""Deterministic invented comparisons; no provider, live or publication mode."""

import argparse
import contextlib
import hashlib
import io
import json
from types import SimpleNamespace


def report_bytes():
    from tests.offline_guard import install

    install()  # Before app imports; never lift the guard.
    import httpx
    from app.agents.jev_router import JevRouterAgent, MODEL
    from app.observability import request_trace
    from experiments.router_bench.routers import HaikuRouter
    from experiments.router_bench.safety import OfflineFakeClient

    rows = []
    for scenario in ("qa", "summarize", "low", "malformed", "timeout", "throttled"):
        choice = "qa" if scenario == "qa" else "summarize"
        score = 0.55 if scenario == "low" else 0.9
        expected = choice if scenario in ("qa", "summarize") else "qa"
        calls = {"haiku": 0, "jev": 0}

        class Fake(OfflineFakeClient):
            def converse(self, **kwargs):
                calls["haiku"] += 1
                if scenario in ("timeout", "throttled"):
                    raise TimeoutError("invented service failure")
                return {
                    "output": {
                        "message": {
                            "content": [
                                {
                                    "text": "{}"
                                    if scenario == "malformed"
                                    else json.dumps(
                                        {
                                            "task_type": choice,
                                            "confidence": score,
                                            "reasoning": "invented",
                                        }
                                    )
                                }
                            ]
                        }
                    },
                    "usage": {"inputTokens": 100, "outputTokens": 10},
                }

        def handler(request):
            calls["jev"] += 1
            if scenario == "timeout":
                raise httpx.ReadTimeout("invented", request=request)
            if scenario == "throttled":
                return httpx.Response(429, json={})
            return httpx.Response(
                200,
                json={
                    "model": "wrong" if scenario == "malformed" else MODEL,
                    "answers": {
                        "route": {
                            "choice": choice,
                            "confidence": 0.8,
                            "probabilities": {
                                choice: score,
                                ("qa" if choice == "summarize" else "summarize"): 1
                                - score,
                            },
                        }
                    },
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                },
            )

        # Existing benchmark suppresses .env before importing the Haiku control.
        control = HaikuRouter(bedrock_client=Fake())
        with contextlib.redirect_stdout(io.StringIO()):
            baseline = control.route(
                SimpleNamespace(id=scenario, query="Invented practice query")
            )
        agent = JevRouterAgent(transport=httpx.MockTransport(handler))
        try:
            with request_trace("synthetic_candidate") as trace:
                candidate = agent.route("Invented practice query")
        finally:
            agent.close()
        if (
            baseline.final_label != expected
            or candidate.task_type != expected
            or calls != {"haiku": 1, "jev": 1}
        ):
            raise RuntimeError("synthetic_contract_mismatch")
        rows.append(
            {
                "scenario": scenario,
                "expected_route": expected,
                "haiku_route": baseline.final_label,
                "jev_route": candidate.task_type,
                "haiku_outcome": baseline.extra["router_outcome"],
                "jev_outcome": trace.route["router_outcome"],
                "mock_attempts": calls,
            }
        )
    return (
        json.dumps(
            {
                "schema": "jev-candidate-synthetic-smoke-v1",
                "evidence_class": "SIMULATED_NOT_QUALIFICATION",
                "provider_calls": 0,
                "performance_measured": False,
                "cases": rows,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    raw = report_bytes()
    print(raw.decode("utf-8"), end="")
    print("report_sha256=" + hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    main()
