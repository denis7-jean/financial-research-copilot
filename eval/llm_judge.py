"""LLM-as-judge evaluation harness (live: calls Bedrock for the system and the judge).

Per case it records routing (vs label), retrieval relevance, faithfulness (QA
path), summary grounding (summarize path), answer correctness (vs a verified
reference), abstention appropriateness, latency and token usage. Aggregation and
gates live in eval/metrics.py. See eval/README.md for definitions and costs.
"""
from dotenv import load_dotenv

load_dotenv()

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

import boto3

from app.agents.orchestrator import CopilotOrchestrator
from app.observability import request_trace
from eval.eval_queries import EVAL_CASES, EvalCase
from eval.metrics import GATES, company_for_source, company_precision, is_contaminated, summarize_results

JUDGE_MODEL_ID = os.getenv("JUDGE_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
# Deterministic judging; the pre-Phase-0 harness used provider defaults.
JUDGE_INFERENCE_CONFIG = {"temperature": 0.0, "maxTokens": 400}
DEFAULT_RESULTS_PATH = "eval/results/latest.json"
RESULTS_SCHEMA_VERSION = 2

# Pass thresholds per judge score (1-5). Unchanged from the original rubrics.
CONTEXT_RELEVANCE_PASS_MIN = 3
FAITHFULNESS_PASS_MIN = 4
GROUNDING_PASS_MIN = 4
CORRECTNESS_PASS_MIN = 4

CONTEXT_RELEVANCE_PROMPT = """You are an evaluation judge for a financial research AI system.

Your task: assess whether the retrieved document chunks contain sufficient
information to answer the user's query.

Scoring rubric:
5 — Chunks contain a direct, complete answer to the query
4 — Chunks contain most of the answer; minor gaps
3 — Chunks are topically related but require inference to answer the query
2 — Chunks are loosely related; answering the query requires significant inference
1 — Chunks are irrelevant to the query

You must respond with valid JSON only. No explanation outside the JSON.
Schema: {"score": int, "reasoning": "one sentence", "pass": bool}
"pass" is true if score >= 3."""

FAITHFULNESS_PROMPT = """You are an evaluation judge for a financial research AI system.

Your task: assess whether every factual claim in the generated answer
is directly supported by the retrieved context. This tests for hallucination.

Scoring rubric:
5 — Every claim in the answer is explicitly supported by the context
4 — Nearly all claims supported; one minor unsupported inference
3 — Most claims supported; one unsupported factual claim
2 — Several claims are not supported or contradict the context
1 — Answer contains fabricated numbers or facts not present in context

You must respond with valid JSON only. No explanation outside the JSON.
Schema: {"score": int, "reasoning": "one sentence", "pass": bool}
"pass" is true if score >= 4."""

SUMMARY_GROUNDING_PROMPT = """You are an evaluation judge for a financial research AI system.

The system wrote the summary below WITHOUT being given any documents. The
evidence excerpts were retrieved afterwards from the company's FY2025 10-K by
the evaluation harness. Your task: assess whether the specific factual claims in
the summary are supported by the evidence. Claims the evidence does not address
count as unsupported. Generic statements without specific facts are neutral.

Scoring rubric:
5 — Every specific claim is supported by the evidence
4 — Nearly all specific claims supported; one minor unsupported inference
3 — Most specific claims supported; one unsupported factual claim
2 — Several specific claims are unsupported or contradict the evidence
1 — Contains fabricated figures or facts, or contradicts the evidence

You must respond with valid JSON only. No explanation outside the JSON.
Schema: {"score": int, "reasoning": "one sentence"}"""

ANSWER_ASSESSMENT_PROMPT = """You are an evaluation judge for a financial research AI system that answers
questions from FY2025 SEC 10-K filings.

Given the user query, the system's answer and, when available, a reference
answer verified against the filing, return:

"abstained": true if the answer declines to answer or says the information is
not available in its documents; false if it gives a substantive answer, even a
partial or incorrect one.

"correctness_score": null when no reference answer is provided. Otherwise:
5 — States the reference facts correctly (rounding and unit conversion are fine)
4 — Correct key figure or fact with a minor imprecision or omission
3 — Partially correct: some required facts right, others missing or wrong
2 — Mostly incorrect, or the key figure is from the wrong period or entity
1 — Wrong, contradicts the reference, or abstains although a reference exists

You must respond with valid JSON only. No explanation outside the JSON.
Schema: {"abstained": bool, "correctness_score": int or null, "reasoning": "one sentence"}"""

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def _parse_judge_response(text: str) -> dict:
    """Parse judge JSON, tolerating code fences and surrounding prose."""
    try:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = _JSON_OBJECT.search(text)
            if match is None:
                raise
            return json.loads(match.group(0))
    except Exception:
        return {"score": 0, "pass": False, "reasoning": "parse_error"}


def _call_judge(client, system_prompt: str, user_text: str, judge_calls: list[dict]) -> tuple[dict, str | None]:
    """One judge call. Returns (parsed_json, error). Usage is appended to judge_calls."""
    try:
        response = client.converse(
            modelId=JUDGE_MODEL_ID,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_text}]}],
            inferenceConfig=JUDGE_INFERENCE_CONFIG,
        )
    except Exception as e:
        return {}, f"{type(e).__name__}: {str(e)[:200]}"
    usage = response.get("usage") or {}
    judge_calls.append({
        "name": "judge",
        "model_id": JUDGE_MODEL_ID,
        "input_tokens": usage.get("inputTokens"),
        "output_tokens": usage.get("outputTokens"),
    })
    try:
        text = response["output"]["message"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        return {}, f"malformed_response: {type(e).__name__}"
    parsed = _parse_judge_response(text)
    if parsed.get("reasoning") == "parse_error":
        return parsed, "parse_error"
    return parsed, None


def _scored(parsed: dict, error: str | None, pass_min: int) -> dict:
    """Normalise a 1-5 judgement. Pass is computed from the score, not trusted from the judge."""
    score = parsed.get("score")
    if error or not isinstance(score, int) or isinstance(score, bool):
        return {"score": 0, "pass": False, "reasoning": error or "invalid_score", "judge_error": True}
    return {"score": score, "pass": score >= pass_min, "reasoning": parsed.get("reasoning", ""), "judge_error": False}


def _failed(reason: str) -> dict:
    return {"score": 0, "pass": False, "reasoning": reason, "judge_error": False}


def _context_string(chunks: list[dict], text_key: str) -> str:
    return "".join(f"[Source: {chunk['source']}]\n{chunk[text_key]}\n\n" for chunk in chunks)


def judge_context_relevance(client, query: str, chunks: list[dict], judge_calls: list[dict]) -> dict:
    parsed, error = _call_judge(
        client, CONTEXT_RELEVANCE_PROMPT,
        f"User Query: {query}\n\nRetrieved Chunks:\n{_context_string(chunks, 'text')}", judge_calls)
    return _scored(parsed, error, CONTEXT_RELEVANCE_PASS_MIN)


def judge_faithfulness(client, chunks: list[dict], answer: str, judge_calls: list[dict]) -> dict:
    parsed, error = _call_judge(
        client, FAITHFULNESS_PROMPT,
        f"Retrieved Context:\n{_context_string(chunks, 'text')}\n\nGenerated Answer:\n{answer}", judge_calls)
    return _scored(parsed, error, FAITHFULNESS_PASS_MIN)


def judge_summary_grounding(client, query: str, evidence: list[dict], summary_text: str,
                            judge_calls: list[dict]) -> dict:
    parsed, error = _call_judge(
        client, SUMMARY_GROUNDING_PROMPT,
        f"User Query: {query}\n\nEvidence Excerpts:\n{_context_string(evidence, 'content')}"
        f"\n\nSummary:\n{summary_text}", judge_calls)
    return _scored(parsed, error, GROUNDING_PASS_MIN)


def assess_answer(client, case: EvalCase, answer: str, judge_calls: list[dict]) -> tuple[bool | None, dict | None, bool]:
    """Returns (abstained, correctness_or_None, judge_error)."""
    parsed, error = _call_judge(
        client, ANSWER_ASSESSMENT_PROMPT,
        f"User Query: {case.query}\n\nReference Answer: {case.reference_answer or 'None provided'}"
        f"\n\nSystem Answer:\n{answer}", judge_calls)
    abstained = parsed.get("abstained") if isinstance(parsed.get("abstained"), bool) else None
    judge_error = bool(error) or abstained is None
    if case.reference_answer is None:
        return abstained, None, judge_error
    score = parsed.get("correctness_score")
    if error or not isinstance(score, int) or isinstance(score, bool):
        return abstained, {"score": 0, "pass": False, "reasoning": error or "invalid_score", "judge_error": True}, True
    return abstained, {"score": score, "pass": score >= CORRECTNESS_PASS_MIN,
                       "reasoning": parsed.get("reasoning", ""), "judge_error": False}, judge_error


def judge_response(query: str, retrieved_context: list[dict], answer: str, client) -> dict:
    """Pre-Phase-0 entry point, kept for compatibility: context relevance + faithfulness."""
    if not retrieved_context:
        return {
            "context_relevance": {"score": 0, "pass": False, "reasoning": "no_context_retrieved"},
            "faithfulness": {"score": 0, "pass": False, "reasoning": "no_context_retrieved"},
        }
    judge_calls: list[dict] = []
    return {
        "context_relevance": judge_context_relevance(client, query, retrieved_context, judge_calls),
        "faithfulness": judge_faithfulness(client, retrieved_context, answer, judge_calls),
    }


def answer_text_from_result(result: dict) -> str:
    """Text the user actually received, for either agent's response shape."""
    if "answer" in result:
        return result.get("answer") or ""
    if "summary" in result:
        summary = result.get("summary") or ""
        key_points = result.get("key_points") or []
        risk_flags = result.get("risk_flags") or []
        if summary == "Parse error" and not key_points and not risk_flags:
            return ""
        parts = [f"Summary: {summary}"]
        if key_points:
            parts.append("Key points:\n" + "\n".join(f"- {p}" for p in key_points))
        if risk_flags:
            parts.append("Risk flags:\n" + "\n".join(f"- {r}" for r in risk_flags))
        return "\n".join(parts)
    return ""


def evaluate_case(case: EvalCase, orchestrator, client, retrieve_evidence, judge_calls: list[dict]) -> dict:
    with request_trace("eval", case.query) as trace:
        result = orchestrator.process(case.query, trace_id=trace.trace_id)
    record = trace.to_record()

    inner = result.get("result") or {}
    agent_used = result.get("agent_used", "unknown")
    predicted_route = result.get("task_type", "unknown")
    answer = answer_text_from_result(inner)
    retrieved = inner.get("retrieved_context") or []
    sources = [company_for_source(c.get("source", "")) for c in retrieved]
    raw_sources = [c.get("source", "") for c in retrieved]

    judge_errors = 0
    context_relevance = faithfulness = summary_grounding = None

    if retrieved:
        context_relevance = judge_context_relevance(client, case.query, retrieved, judge_calls)
        faithfulness = judge_faithfulness(client, retrieved, answer, judge_calls)
        judge_errors += context_relevance["judge_error"] + faithfulness["judge_error"]
    elif case.gated_for_retrieval:
        # Gated cases without production context are failures, never exclusions.
        reason = f"no_retrieved_context (routed to {predicted_route}, agent {agent_used})"
        context_relevance, faithfulness = _failed(reason), _failed(reason)

    if agent_used == "summarize":
        if not answer:
            summary_grounding = _failed("empty_or_unparseable_summary")
        else:
            # Evidence retrieval happens outside the request trace: eval overhead, not system latency.
            evidence = retrieve_evidence(case.query, n_results=5)
            if evidence:
                summary_grounding = judge_summary_grounding(client, case.query, evidence, answer, judge_calls)
                judge_errors += summary_grounding["judge_error"]
            else:
                summary_grounding = _failed("no_evidence_retrieved")

    if answer:
        abstained, correctness, assessment_error = assess_answer(client, case, answer, judge_calls)
        judge_errors += int(assessment_error)
    else:
        abstained = None
        correctness = _failed("empty_answer") if case.reference_answer else None

    if case.expected_behavior == "either":
        abstention_appropriate = None
    elif not answer:
        abstention_appropriate = False
    elif abstained is None:
        abstention_appropriate = None
    else:
        abstention_appropriate = abstained == (case.expected_behavior == "abstain")

    return {
        "id": case.id,
        "query": case.query,
        "category": case.category,
        "legacy": case.legacy,
        "notes": case.notes,
        "expected_route": case.expected_route,
        "route_label_status": case.route_label_status,
        "expected_behavior": case.expected_behavior,
        "gated_for_retrieval": case.gated_for_retrieval,
        "has_reference": case.reference_answer is not None,
        "reference_answer": case.reference_answer,
        "reference_source": case.reference_source,
        "predicted_route": predicted_route,
        "agent_used": agent_used,
        "route_correct": predicted_route == case.expected_route,
        "router_outcome": record["route"].get("router_outcome"),
        "system_error": result.get("error"),
        "trace_errors": record["errors"],
        "answer_preview": answer[:300],
        "answer_chars": len(answer),
        "retrieval": {
            "sources": sources,
            "raw_sources": raw_sources,
            "company_precision": company_precision(raw_sources, case.companies),
            "contaminated": is_contaminated(raw_sources, case.companies),
        },
        "context_relevance": context_relevance,
        "faithfulness": faithfulness,
        "summary_grounding": summary_grounding,
        "answer_correctness": correctness,
        "abstained": abstained,
        "abstention_appropriate": abstention_appropriate,
        "judge_errors": judge_errors,
        "latency": {
            "total_ms": record["total_ms"],
            "stages_ms": record["stages_ms"],
            "cold_start": record["cold_start"],
        },
        "model_calls": record["model_calls"],
        "tokens": record["tokens"],
    }


def _resolve_cases(cases) -> list[EvalCase]:
    if cases is None:
        return list(EVAL_CASES)
    resolved = []
    by_query = {c.query: c for c in EVAL_CASES}
    for i, item in enumerate(cases):
        if isinstance(item, EvalCase):
            resolved.append(item)
        elif item in by_query:
            resolved.append(by_query[item])
        else:
            resolved.append(EvalCase(f"ADHOC{i:02d}", item, "adhoc", "qa", "needs_review", "either"))
    return resolved


def run_evaluation(
    cases=None,
    *,
    orchestrator=None,
    client=None,
    retrieve_evidence=None,
    results_path: str | None = None,
    sleep_seconds: float | None = None,
) -> dict:
    """Run the labeled evaluation, write results and return the summary.

    `cases` may be EvalCase objects or, for backward compatibility, query strings.
    """
    cases = _resolve_cases(cases)
    orchestrator = orchestrator or CopilotOrchestrator()
    client = client or boto3.client("bedrock-runtime", region_name="us-east-1")
    if retrieve_evidence is None:
        from app.services.retriever import retrieve_chunks as retrieve_evidence
    results_path = results_path or os.getenv("EVAL_RESULTS_PATH", DEFAULT_RESULTS_PATH)
    if sleep_seconds is None:
        sleep_seconds = float(os.getenv("EVAL_SLEEP_SECONDS", "2"))

    run_id = uuid.uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    judge_calls: list[dict] = []
    rows = []

    for i, case in enumerate(cases):
        print(f"[{i + 1}/{len(cases)}] {case.id} {case.category}: {case.query[:60]}...")
        rows.append(evaluate_case(case, orchestrator, client, retrieve_evidence, judge_calls))
        if i < len(cases) - 1 and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    summary = {
        "schema_version": RESULTS_SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": os.getenv("GITHUB_SHA"),
        "system_model_id": os.getenv("BEDROCK_MODEL_ID"),
        "judge_model_id": JUDGE_MODEL_ID,
        "judge_inference_config": JUDGE_INFERENCE_CONFIG,
        **summarize_results(rows, judge_calls),
        "results_path": results_path,
    }

    directory = os.path.dirname(results_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": rows}, f, indent=2)

    _print_summary(summary)
    return summary


def _fmt(value) -> str:
    return "n/a" if value is None else f"{value:.2%}"


def _print_summary(summary: dict) -> None:
    print("\n--- Evaluation Summary ---")
    print(f"Run id           : {summary['run_id']}")
    print(f"Cases            : {summary['total_queries']} (gated QA population: {summary['judged_queries']})")
    for gate in summary["gates"]:
        flag = "ENFORCED" if gate["enforced"] else "report-only"
        status = "PASS" if gate["passed"] else "FAIL"
        print(f"{gate['metric']:<32} {_fmt(gate['value']):>8}  >= {gate['threshold']:.0%}  {status}  [{flag}]")
    print(f"Router mismatches: {summary['routing']['mismatches']}")
    print(f"Contaminated     : {summary['retrieval']['companies']['contaminated_cases']}")
    print(f"System errors    : {summary['errors']['cases_with_system_errors']}")
    print(f"Judge errors     : {summary['errors']['judge_errors']}")
    print(f"Overall pass     : {summary['overall_pass']}  (enforced gates only)")


if __name__ == "__main__":
    load_dotenv()
    summary = run_evaluation()
    print("\nOverall pass:", summary["overall_pass"])
    print("Gates:", [g["metric"] for g in GATES if g.enforced], "enforced")
