from dotenv import load_dotenv

load_dotenv()

import json
import os
import time

import boto3

from app.agents.orchestrator import CopilotOrchestrator
from eval.eval_queries import EVAL_QUERIES, BOUNDARY_QUERIES

JUDGE_MODEL_ID = os.getenv("JUDGE_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

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


def _parse_judge_response(text: str) -> dict:
    try:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        return json.loads(text)
    except Exception:
        return {"score": 0, "pass": False, "reasoning": "parse_error"}


def judge_response(
    query: str,
    retrieved_context: list[dict],
    answer: str,
    client,
) -> dict:
    if not retrieved_context:
        return {
            "context_relevance": {"score": 0, "pass": False, "reasoning": "no_context_retrieved"},
            "faithfulness": {"score": 0, "pass": False, "reasoning": "no_context_retrieved"},
        }

    context_string = "".join(
        f"[Source: {chunk['source']}]\n{chunk['text']}\n\n"
        for chunk in retrieved_context
    )

    try:
        cr_response = client.converse(
            modelId=JUDGE_MODEL_ID,
            system=[{"text": CONTEXT_RELEVANCE_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": f"User Query: {query}\n\nRetrieved Chunks:\n{context_string}"}],
                }
            ],
        )
        cr_text = cr_response["output"]["message"]["content"][0]["text"]
        context_relevance = _parse_judge_response(cr_text)

        faith_response = client.converse(
            modelId=JUDGE_MODEL_ID,
            system=[{"text": FAITHFULNESS_PROMPT}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": f"Retrieved Context:\n{context_string}\n\nGenerated Answer:\n{answer}"}],
                }
            ],
        )
        faith_text = faith_response["output"]["message"]["content"][0]["text"]
        faithfulness = _parse_judge_response(faith_text)

        return {
            "context_relevance": {
                "score": context_relevance.get("score", 0),
                "pass": context_relevance.get("pass", False),
                "reasoning": context_relevance.get("reasoning", ""),
            },
            "faithfulness": {
                "score": faithfulness.get("score", 0),
                "pass": faithfulness.get("pass", False),
                "reasoning": faithfulness.get("reasoning", ""),
            },
        }

    except Exception as e:
        return {
            "context_relevance": {"score": 0, "pass": False, "reasoning": str(e)},
            "faithfulness": {"score": 0, "pass": False, "reasoning": str(e)},
        }


def run_evaluation(queries: list[str] | None = None) -> dict:
    if queries is None:
        from eval.eval_queries import EVAL_QUERIES
        queries = EVAL_QUERIES
    orchestrator = CopilotOrchestrator()
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    results = []

    for i, query in enumerate(queries):
        print(f"[{i+1}/{len(queries)}] Evaluating: {query[:60]}...")

        result = orchestrator.process(query)
        answer = result["result"].get("answer", "")
        retrieved_context = result["result"].get("retrieved_context", [])
        agent_used = result.get("agent_used", "unknown")
        task_type = result.get("task_type", "unknown")

        if agent_used == "summarize":
            scores = {
                "context_relevance": {"score": None, "pass": None, "reasoning": "skipped_summarize"},
                "faithfulness": {"score": None, "pass": None, "reasoning": "skipped_summarize"},
            }
        else:
            scores = judge_response(query, retrieved_context, answer, client)

        results.append({
            "query": query,
            "task_type": task_type,
            "agent_used": agent_used,
            "answer_preview": answer[:200],
            "context_relevance": scores["context_relevance"],
            "faithfulness": scores["faithfulness"],
        })

        if i < len(queries) - 1:
            time.sleep(2)

    judged = [r for r in results
              if r["context_relevance"]["score"] is not None
              and r["query"] not in BOUNDARY_QUERIES]
    total_queries = len(results)
    judged_queries = len(judged)
    context_relevance_pass_rate = sum(1 for r in judged if r["context_relevance"]["pass"]) / len(judged) if judged else 0.0
    faithfulness_pass_rate = sum(1 for r in judged if r["faithfulness"]["pass"]) / len(judged) if judged else 0.0
    mean_context_relevance = sum(r["context_relevance"]["score"] for r in judged) / len(judged) if judged else 0.0
    mean_faithfulness = sum(r["faithfulness"]["score"] for r in judged) / len(judged) if judged else 0.0
    overall_pass = context_relevance_pass_rate >= 0.75 and faithfulness_pass_rate >= 0.75

    summary = {
        "total_queries": total_queries,
        "judged_queries": judged_queries,
        "boundary_queries_excluded": len([r for r in results if r["query"] in BOUNDARY_QUERIES]),
        "context_relevance_pass_rate": context_relevance_pass_rate,
        "faithfulness_pass_rate": faithfulness_pass_rate,
        "mean_context_relevance": mean_context_relevance,
        "mean_faithfulness": mean_faithfulness,
        "overall_pass": overall_pass,
    }

    with open("eval/results/latest.json", "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print("\n--- Evaluation Summary ---")
    print(f"Total queries    : {total_queries}")
    print(f"Judged queries   : {judged_queries}")
    print(f"Context relevance: pass_rate={context_relevance_pass_rate:.2%}  mean={mean_context_relevance:.2f}")
    print(f"Faithfulness     : pass_rate={faithfulness_pass_rate:.2%}  mean={mean_faithfulness:.2f}")
    print(f"Overall pass     : {overall_pass}")

    return summary


if __name__ == "__main__":
    load_dotenv()
    os.makedirs("eval/results", exist_ok=True)
    summary = run_evaluation(EVAL_QUERIES)
    print("\nOverall pass:", summary["overall_pass"])
