import os

import boto3
from dotenv import load_dotenv

from app.services.retriever import retrieve_chunks

load_dotenv()

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")


def retrieve_and_generate(query: str, knowledge_base_id: str = None) -> dict:
    try:
        chunks = retrieve_chunks(query, n_results=5)

        if not chunks:
            return {
                "answer": "No relevant documents found.",
                "citations": [],
                "retrieved_context": [],
                "error": "empty_retrieval",
            }

        context = "".join(
            f"Source: {chunk['source']}\n{chunk['content']}\n\n"
            for chunk in chunks
        )

        response = bedrock.converse(
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

        answer = response["output"]["message"]["content"][0]["text"]
        citations = list({chunk["source"] for chunk in chunks})
        retrieved_context = [
            {"text": chunk["content"], "source": chunk["source"], "score": chunk["score"]}
            for chunk in chunks
        ]

        return {"answer": answer, "citations": citations, "retrieved_context": retrieved_context}

    except Exception as e:
        return {"answer": "", "citations": [], "retrieved_context": [], "error": str(e)}


if __name__ == "__main__":
    load_dotenv()
    result = retrieve_and_generate(
        "What was JPMorgan Chase's net revenue for fiscal year 2025?"
    )
    print(result["answer"])
    print("Citations:", result["citations"])
