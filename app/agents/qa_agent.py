import time

from dotenv import load_dotenv
from pydantic import BaseModel

from app.services.bedrock_client import retrieve_and_generate

load_dotenv()


class QAResponse(BaseModel):
    answer: str
    citations: list[str]
    confidence: float
    agent: str = "qa"
    latency_ms: float


class QAAgent:
    def __init__(self):
        pass

    def run(self, query: str) -> QAResponse:
        start = time.monotonic()
        try:
            result = retrieve_and_generate(query)
            latency_ms = (time.monotonic() - start) * 1000
            citations = result.get("citations", [])
            return QAResponse(
                answer=result.get("answer", ""),
                citations=citations,
                confidence=1.0 if citations else 0.5,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            print(f"QAAgent.run error: {e}")
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
