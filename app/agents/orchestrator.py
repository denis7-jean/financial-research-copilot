from __future__ import annotations

import json
import time
import uuid
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from app.agents.router_configuration import RouterConfiguration, build_router
from app.errors import ServiceFailure, failure_from
from app.services.rag_smoke_policy import SmokePolicy, SmokeStop
from app.observability import (
    annotate,
    current_trace_id,
    record_failure,
    set_route,
    stage,
)

if TYPE_CHECKING:
    from app.agents.qa_agent import QAResponse
    from app.agents.summarizer_agent import SummaryResponse


def _log(event: str, payload: dict) -> None:
    print(json.dumps({"event": event, **payload}))


def _resolve_trace_id(trace_id: str | None) -> str:
    return trace_id or current_trace_id() or str(uuid.uuid4())


def _failure_result(failure: ServiceFailure, task_type: str, trace_id: str) -> dict:
    """Existing error shape plus sanitized structured detail. Raw messages never leave the logs."""
    record_failure(failure, fatal=True)
    annotate("outcome", "failed")
    _log("orchestrator.failed", {"trace_id": trace_id, **failure.to_log()})
    return {
        "error": failure.public_message(),
        "error_detail": failure.to_public(),
        "task_type": task_type,
        "result": {},
    }


class CopilotOrchestrator:
    @staticmethod
    def process_smoke(query: str, *, policy: SmokePolicy) -> dict:
        """Explicit injected single-run entry; never enabled by environment alone.

        No ordinary orchestrator, summarizer or Jev client is constructed here.
        The QAAgent calls the same retriever and generation application seams.
        Returned financial content requires separately authorized private handling.
        """
        if type(policy) is not SmokePolicy:
            raise SmokeStop("POLICY_REQUIRED")
        with policy.activate(query):
            # Import under the active policy: no ordinary service client/cache.
            from app.agents.qa_agent import QAAgent
            from app.agents.router import RouterAgent

            decision = RouterAgent(smoke_policy=policy).route(query)
            if decision.task_type != "qa":
                policy.fail("ROUTER_MISROUTE")
            response = QAAgent().run(query)
            if not response.answer.strip() or not response.retrieved_context:
                policy.fail("RAG_RESULT_INVALID")
            return {
                "scope": "STRUCTURAL_SMOKE_NOT_QUALIFICATION",
                "task_type": "qa",
                "router_confidence": decision.confidence,
                "result": response.model_dump(),
            }

    def __init__(self, *, router_configuration=None, jev_transport=None):
        load_dotenv()
        from app.agents.qa_agent import QAAgent
        from app.agents.router import RouterAgent
        from app.agents.summarizer_agent import SummarizerAgent

        # Preserve legacy construction/fixtures on the default Haiku path.
        configuration = router_configuration or RouterConfiguration.from_environment()
        self._router = (
            RouterAgent()
            if configuration.provider == "haiku" and jev_transport is None
            else build_router(configuration, jev_transport=jev_transport)
        )
        self._qa = QAAgent()
        self._summarizer = SummarizerAgent()

    def process(self, query: str, trace_id: str | None = None) -> dict:
        trace_id = _resolve_trace_id(trace_id)
        try:
            start = time.monotonic()
            with stage("route"):
                decision = self._router.route(query, trace_id=trace_id)
            router_latency_ms = (time.monotonic() - start) * 1000
            set_route(task_type=decision.task_type, confidence=decision.confidence)
            _log(
                "orchestrator.routed",
                {
                    "trace_id": trace_id,
                    "intent": decision.task_type,
                    "confidence": decision.confidence,
                    "router_latency_ms": round(router_latency_ms, 1),
                },
            )

            with stage("agent"):
                agent_response = self._dispatch(
                    query, decision.task_type, trace_id=trace_id
                )
            if agent_response is None:
                failure = ServiceFailure(
                    "orchestrator", "internal", "UnknownTaskType", decision.task_type
                )
                return {
                    **_failure_result(failure, decision.task_type, trace_id),
                    "error": f"unknown task_type: {decision.task_type}",
                }

            _log(
                "orchestrator.completed",
                {
                    "trace_id": trace_id,
                    "intent": decision.task_type,
                },
            )
            return {
                "task_type": decision.task_type,
                "router_confidence": decision.confidence,
                "result": agent_response.model_dump(),
                "agent_used": agent_response.agent,
                "total_latency_ms": router_latency_ms + agent_response.latency_ms,
            }
        except Exception as e:
            return _failure_result(failure_from("orchestrator", e), "unknown", trace_id)

    def process_direct(
        self, query: str, task_type: str, trace_id: str | None = None
    ) -> dict:
        trace_id = _resolve_trace_id(trace_id)
        try:
            set_route(task_type=task_type, confidence=None, router_outcome="direct")
            _log(
                "orchestrator.routed",
                {
                    "trace_id": trace_id,
                    "intent": task_type,
                    "confidence": None,
                },
            )
            with stage("agent"):
                agent_response = self._dispatch(query, task_type, trace_id=trace_id)
            if agent_response is None:
                failure = ServiceFailure(
                    "orchestrator", "internal", "UnknownTaskType", task_type
                )
                result = _failure_result(failure, task_type, trace_id)
                return {
                    "error": "unknown task_type",
                    "error_detail": result["error_detail"],
                    "result": {},
                }

            _log(
                "orchestrator.completed",
                {
                    "trace_id": trace_id,
                    "intent": task_type,
                },
            )
            return {
                "task_type": task_type,
                "router_confidence": None,
                "result": agent_response.model_dump(),
                "agent_used": agent_response.agent,
                "total_latency_ms": agent_response.latency_ms,
            }
        except Exception as e:
            return _failure_result(failure_from("orchestrator", e), task_type, trace_id)

    def _dispatch(
        self, query: str, task_type: str, trace_id: str | None = None
    ) -> QAResponse | SummaryResponse | None:
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

    r2 = orch.process_direct(
        "Summarize the key risks in Goldman Sachs 2025 annual report", "summarize"
    )
    print("process_direct() summarize:")
    print(r2)
