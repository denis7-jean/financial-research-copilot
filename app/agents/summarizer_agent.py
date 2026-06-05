import json
import os
import time

import boto3
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


def _log(event: str, payload: dict) -> None:
    print(json.dumps({"event": event, **payload}))


class SummaryResponse(BaseModel):
    summary: str
    key_points: list[str]
    risk_flags: list[str]
    agent: str = "summarize"
    latency_ms: float


class SummarizerAgent:
    def __init__(self):
        self._client = boto3.client("bedrock-runtime", region_name="us-east-1")
        self._model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

    def run(self, query: str, trace_id: str = "") -> SummaryResponse:
        start = time.monotonic()
        try:
            response = self._client.converse(
                modelId=self._model_id,
                system=[{"text": "You are a financial document analyst. Always respond in valid JSON only."}],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": (
                                    "Analyze the following and return JSON with keys: "
                                    "summary (str), key_points (list[str]), risk_flags (list[str])."
                                    f"\n\n{query}"
                                )
                            }
                        ],
                    }
                ],
            )
            raw = response["output"]["message"]["content"][0]["text"]
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            parsed = json.loads(text)
            parsed["summary"] = parsed.get("summary") or "No summary returned"
            parsed["key_points"] = parsed.get("key_points") or []
            parsed["risk_flags"] = parsed.get("risk_flags") or []
            latency_ms = (time.monotonic() - start) * 1000
            _log("summarizer.completed", {"trace_id": trace_id})
            return SummaryResponse.model_validate({**parsed, "latency_ms": latency_ms})
        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            _log("summarizer.error", {"trace_id": trace_id, "error": str(e)})
            return SummaryResponse(
                summary="Parse error",
                key_points=[],
                risk_flags=[],
                latency_ms=latency_ms,
            )


if __name__ == "__main__":
    load_dotenv()
    agent = SummarizerAgent()
    result = agent.run("Summarize the key risks in Goldman Sachs 2025 annual report")
    print(result.model_dump())
