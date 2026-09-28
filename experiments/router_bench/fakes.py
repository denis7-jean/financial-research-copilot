"""Offline stand-ins for Bedrock and TypeSafe, used by the dry run (and tests).

They produce seeded, plausible responses so the dry run exercises every code path
(valid answers, low scores, parse/schema errors, HTTP errors) and the accounting.
Their outputs are SIMULATED and say nothing about any router's quality.
"""
import json
import random

import httpx

from experiments.router_bench.config import JEV_ENDPOINT, JEV_MODEL
from experiments.router_bench.safety import OfflineFakeClient


class FakeBedrock(OfflineFakeClient):
    """A bedrock-runtime client whose converse() answers like the Haiku router prompt."""

    def __init__(self, labels: dict[str, str], seed: int, *, accuracy=0.9, parse_error_rate=0.01,
                 throttle_rate=0.003):
        self._labels = labels  # query -> label to favour
        self._rng = random.Random(seed)
        self.accuracy, self.parse_error_rate, self.throttle_rate = accuracy, parse_error_rate, throttle_rate
        self.calls = 0

    def converse(self, **kwargs):
        from botocore.exceptions import ClientError

        self.calls += 1
        text = kwargs["messages"][0]["content"][0]["text"]
        query = text.split("Query: ", 1)[-1]
        roll = self._rng.random()
        if roll < self.throttle_rate:
            raise ClientError({"Error": {"Code": "ThrottlingException", "Message": "simulated"},
                               "ResponseMetadata": {"HTTPStatusCode": 429}}, "Converse")
        if roll < self.throttle_rate + self.parse_error_rate:
            body = "simulated unparseable output"
        else:
            label = self._labels.get(query, "qa")
            if self._rng.random() > self.accuracy:
                label = "summarize" if label == "qa" else "qa"
            body = json.dumps({"task_type": label, "confidence": round(self._rng.uniform(0.55, 0.99), 2),
                               "reasoning": "simulated"})
        return {"output": {"message": {"role": "assistant", "content": [{"text": body}]}},
                "usage": {"inputTokens": 200 + len(query) // 4, "outputTokens": 45 + self._rng.randint(0, 15)},
                "metrics": {"latencyMs": 0}, "stopReason": "end_turn"}


class FakeTypeSafe:
    """An httpx.MockTransport handler for POST /v1/systemone. Records what it received."""

    def __init__(self, labels: dict[str, str], seed: int, *, accuracy=0.9, error_rate=0.003, schema_error_rate=0.003):
        self._labels = labels
        self._rng = random.Random(seed)
        self.accuracy, self.error_rate, self.schema_error_rate = accuracy, error_rate, schema_error_rate
        self.requests: list[dict] = []  # {"url", "header_names", "body"}

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append({"url": str(request.url), "header_names": sorted(k.lower() for k in request.headers),
                              "body": body})
        if str(request.url) != JEV_ENDPOINT or request.method != "POST":
            return httpx.Response(404)
        roll = self._rng.random()
        if roll < self.error_rate:
            return httpx.Response(529, json={"error": "simulated overload"})
        label = self._labels.get(body["state"], "qa")
        if self._rng.random() > self.accuracy:
            label = "summarize" if label == "qa" else "qa"
        p = round(self._rng.uniform(0.52, 0.99), 4)
        probabilities = {label: p, ("summarize" if label == "qa" else "qa"): round(1 - p, 4)}
        if roll < self.error_rate + self.schema_error_rate:
            probabilities = {"qa": 0.9, "summarize": 0.9}  # invalid: does not sum to 1
        return httpx.Response(200, headers={"x-request-id": f"sim-{len(self.requests)}"}, json={
            "model": JEV_MODEL,
            "answers": {"route": {"choice": label, "probabilities": probabilities, "confidence": round(2 * p - 1, 4)}},
            "usage": {"input_tokens": max(1, len(request.content) // 4), "output_tokens": 1},
        })
