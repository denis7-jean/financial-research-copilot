import json
import os
import time
from typing import Literal

import boto3
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


def _log(event: str, payload: dict) -> None:
    print(json.dumps({"event": event, **payload}))


class RouterDecision(BaseModel):
    task_type: Literal["qa", "summarize"]
    confidence: float
    reasoning: str


_FALLBACK = RouterDecision(task_type="qa", confidence=0.5, reasoning="fallback")

_SYSTEM_PROMPT = """You are a query classifier for a financial research assistant. Your job is to classify user queries into exactly one of two categories:

"qa" — The user wants a specific fact, figure, or answer retrieved from financial documents.
Examples: revenue numbers, earnings per share, debt levels, headcount, specific dates, comparisons between two figures.

"summarize" — The user wants a high-level overview, narrative summary, or analysis of risks, themes, or trends.
Examples: summarize annual report, explain key risks, describe business strategy, overview of performance.

Respond only with a JSON object. No explanation, no markdown, no preamble.
Format: {"task_type": "qa" or "summarize", "confidence": float between 0.0 and 1.0, "reasoning": "one sentence"}"""

_USER_PROMPT_TEMPLATE = "Classify this financial research query and respond with JSON only. Query: {query}"


class RouterAgent:
    def __init__(self):
        self._client = boto3.client("bedrock-runtime", region_name="us-east-1")
        self._model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
        self.latency_ms: float = 0.0

    def route(self, query: str, trace_id: str = "") -> RouterDecision:
        prompt = _USER_PROMPT_TEMPLATE.format(query=query)

        start = time.monotonic()
        try:
            response = self._client.converse(
                modelId=self._model_id,
                system=[{"text": _SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
            )
        except Exception as e:
            _log("router.error", {"trace_id": trace_id, "error": str(e)})
            self.latency_ms = (time.monotonic() - start) * 1000
            return _FALLBACK
        finally:
            self.latency_ms = (time.monotonic() - start) * 1000

        try:
            raw = response["output"]["message"]["content"][0]["text"]
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            data = json.loads(text)
            decision = RouterDecision.model_validate(data)
        except Exception as e:
            _log("router.error", {"trace_id": trace_id, "error": str(e)})
            return _FALLBACK

        if decision.confidence < 0.6:
            return _FALLBACK

        return decision


if __name__ == "__main__":
    load_dotenv()
    agent = RouterAgent()
    queries = [
        "What was JPMorgan Chase's net revenue for fiscal year 2025?",
        "Summarize the key risks in Goldman Sachs 2023 annual report",
    ]
    for q in queries:
        decision = agent.route(q)
        print(f"Query     : {q}")
        print(f"task_type : {decision.task_type}")
        print(f"confidence: {decision.confidence}")
        print(f"reasoning : {decision.reasoning}")
        print("---")
