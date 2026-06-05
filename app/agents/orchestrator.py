import json
import time
import uuid

from dotenv import load_dotenv

from app.agents.qa_agent import QAAgent, QAResponse
from app.agents.router import RouterAgent
from app.agents.summarizer_agent import SummarizerAgent, SummaryResponse

load_dotenv()


def _log(event: str, payload: dict) -> None:
    print(json.dumps({"event": event, **payload}))


class CopilotOrchestrator:
    def __init__(self):
        self._router = RouterAgent()
        self._qa = QAAgent()
        self._summarizer = SummarizerAgent()

    def process(self, query: str, trace_id: str | None = None) -> dict:
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        try:
            start = time.monotonic()
            decision = self._router.route(query, trace_id=trace_id)
            router_latency_ms = (time.monotonic() - start) * 1000
            _log("orchestrator.routed", {
                "trace_id": trace_id,
                "intent": decision.task_type,
                "confidence": decision.confidence,
            })

            agent_response = self._dispatch(query, decision.task_type, trace_id=trace_id)
            if agent_response is None:
                return {"error": f"unknown task_type: {decision.task_type}", "task_type": decision.task_type, "result": {}}

            _log("orchestrator.completed", {
                "trace_id": trace_id,
                "intent": decision.task_type,
            })
            return {
                "task_type": decision.task_type,
                "router_confidence": decision.confidence,
                "result": agent_response.model_dump(),
                "agent_used": agent_response.agent,
                "total_latency_ms": router_latency_ms + agent_response.latency_ms,
            }
        except Exception as e:
            return {"error": str(e), "task_type": "unknown", "result": {}}

    def process_direct(self, query: str, task_type: str, trace_id: str | None = None) -> dict:
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        try:
            _log("orchestrator.routed", {
                "trace_id": trace_id,
                "intent": task_type,
                "confidence": None,
            })
            agent_response = self._dispatch(query, task_type, trace_id=trace_id)
            if agent_response is None:
                return {"error": "unknown task_type", "result": {}}

            _log("orchestrator.completed", {
                "trace_id": trace_id,
                "intent": task_type,
            })
            return {
                "task_type": task_type,
                "router_confidence": None,
                "result": agent_response.model_dump(),
                "agent_used": agent_response.agent,
                "total_latency_ms": agent_response.latency_ms,
            }
        except Exception as e:
            return {"error": str(e), "task_type": task_type, "result": {}}

    def _dispatch(self, query: str, task_type: str, trace_id: str | None = None) -> QAResponse | SummaryResponse | None:
        if task_type == "qa":
            return self._qa.run(query, trace_id=trace_id)
        if task_type == "summarize":
            return self._summarizer.run(query, trace_id=trace_id)
        return None


if __name__ == "__main__":
    load_dotenv()
    orch = CopilotOrchestrator()

    r1 = orch.process("What was JPMorgan Chase's net revenue for fiscal year 2025?")
    print("process() qa route:")
    print(r1)

    r2 = orch.process_direct("Summarize the key risks in Goldman Sachs 2025 annual report", "summarize")
    print("process_direct() summarize:")
    print(r2)
