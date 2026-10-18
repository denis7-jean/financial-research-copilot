import os

import boto3
from dotenv import load_dotenv

from app.errors import ServiceFailure, failure_from
from app.observability import annotate, record_converse_usage, stage
from app.services.retriever import retrieve_chunks
from app.services.rag_smoke_policy import current_policy

if current_policy() is None:
    load_dotenv()

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
NO_EVIDENCE_ANSWER = "No relevant documents found."

bedrock = (
    boto3.client("bedrock-runtime", region_name="us-east-1")
    if current_policy() is None
    else None
)


def _ordinary_client():
    # A module first imported by an isolated smoke must still work ordinarily.
    # Dedicated smoke clients never populate or replace this ordinary cache.
    global bedrock, BEDROCK_MODEL_ID
    if bedrock is None:
        load_dotenv()
        BEDROCK_MODEL_ID = os.getenv(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        )
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    return bedrock


def retrieve_and_generate(query: str, knowledge_base_id: str = None) -> dict:
    """Retrieve context and generate a grounded answer.

    A genuinely empty retrieval returns NO_EVIDENCE_ANSWER with
    outcome="empty_retrieval". Retrieval, invocation and malformed-response
    failures raise app.errors.ServiceFailure.
    """
    if current_policy() is None:
        _ordinary_client()
    chunks = retrieve_chunks(query, n_results=5)
    annotate("retrieved_chunks", len(chunks))

    if not chunks:
        annotate("outcome", "no_evidence")
        return {
            "answer": NO_EVIDENCE_ANSWER,
            "citations": [],
            "retrieved_context": [],
            "outcome": "empty_retrieval",
        }

    with stage("qa.build_context"):
        context = "".join(
            f"Source: {chunk['source']}\n{chunk['content']}\n\n"
            for chunk in chunks
        )
    annotate("context_chars", len(context))

    with stage("llm.qa_generate"):
        try:
            request = dict(
                modelId=BEDROCK_MODEL_ID,
                system=[
                    {
                        "text": (
                            "You are a financial research analyst. Answer questions "
                            "using only the provided context. If the answer is not in "
                            "the context, say so clearly. Be precise with numbers and "
                            "cite your sources."
                        )
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": f"Context:\n{context}\n\nQuestion: {query}"}],
                    }
                ],
            )
            smoke = current_policy()
            if smoke is not None:
                smoke.validate_query(query)
                request["modelId"] = smoke.config["models"]["haiku"]
                request["inferenceConfig"] = {"maxTokens": smoke.config["output_tokens"]["generation"]}
                response = smoke.invoke("generation", "Converse", request)
            else:
                response = _ordinary_client().converse(**request)
        except Exception as e:
            raise failure_from("qa_generate", e) from e
    record_converse_usage("qa_generate", BEDROCK_MODEL_ID, response)

    try:
        answer = response["output"]["message"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise ServiceFailure("qa_generate", "invalid_model_output", type(e).__name__, str(e)) from e
    if not answer.strip():
        raise ServiceFailure("qa_generate", "invalid_model_output", "EmptyAnswer", "model returned empty text")

    citations = list({chunk["source"] for chunk in chunks})
    retrieved_context = [
        {"text": chunk["content"], "source": chunk["source"], "score": chunk["score"]}
        for chunk in chunks
    ]
    # "generated" covers both factual answers and evidence-based abstentions.
    annotate("outcome", "generated")
    return {"answer": answer, "citations": citations, "retrieved_context": retrieved_context}


if __name__ == "__main__":
    load_dotenv()
    result = retrieve_and_generate(
        "What was JPMorgan Chase's net revenue for fiscal year 2025?"
    )
    print(result["answer"])
    print("Citations:", result["citations"])
