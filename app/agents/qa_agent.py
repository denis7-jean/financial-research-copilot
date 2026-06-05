import json
import time

from dotenv import load_dotenv
from pydantic import BaseModel

from app.services.bedrock_client import retrieve_and_generate

load_dotenv()


def _log(event: str, payload: dict) -> None:
    print(json.dumps({"event": event, **payload}))


class QAResponse(BaseModel):
    answer: str
    citations: list[str]
    confidence: float
    agent: str = "qa"
    latency_ms: float
    retrieved_context: list[dict] = []


class QAAgent:
    def __init__(self):
        pass

    def run(self, query: str, trace_id: str = "") -> QAResponse:
        start = time.monotonic()
        try:
            result = retrieve_and_generate(query)
            latency_ms = (time.monotonic() - start) * 1000
            citations = result.get("citations", [])
            retrieved_context = result.get("retrieved_context", [])
            _log("qa.completed", {
                "trace_id": trace_id,
                "chunks_retrieved": len(retrieved_context),
            })
            return QAResponse(
                answer=result.get("answer", ""),
                citations=citations,
                confidence=1.0 if citations else 0.5,
                latency_ms=latency_ms,
                retrieved_context=retrieved_context,
            )
        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            _log("qa.error", {"trace_id": trace_id, "error": str(e)})
            return QAResponse(
                answer="",
                citations=[],
                confidence=0.0,
                latency_ms=latency_ms,
            )


if __name__ == "__main__":
    load_dotenv()
    agent = QAAgent()
    result = agent.run("What was JPMorgan Chase's net revenue for fiscal year 2025?")
    print(result.model_dump())
