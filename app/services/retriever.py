import json
import os
import tempfile
import time

import boto3
import faiss
import numpy as np
from dotenv import load_dotenv

from app.errors import ServiceFailure, failure_from
from app.observability import annotate, record_model_call, stage

load_dotenv()

EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"

AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
FAISS_INDEX_S3_KEY = os.getenv("FAISS_INDEX_S3_KEY")
FAISS_META_S3_KEY = os.getenv("FAISS_META_S3_KEY")

s3 = boto3.client("s3", region_name="us-east-1")
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

_index = None
_metadata = None


def _load_index_if_needed():
    global _index, _metadata

    if _index is not None:
        annotate("index_loaded_this_request", False)
        return

    local_index_path = os.path.join(tempfile.gettempdir(), "financial_index.faiss")
    local_meta_path = os.path.join(tempfile.gettempdir(), "financial_meta.json")

    print("Loading FAISS index from S3...")
    with stage("retrieval.index_load"):
        s3.download_file(S3_BUCKET_NAME, FAISS_INDEX_S3_KEY, local_index_path)
        s3.download_file(S3_BUCKET_NAME, FAISS_META_S3_KEY, local_meta_path)

        index = faiss.read_index(local_index_path)
        with open(local_meta_path, "r") as f:
            metadata = json.load(f)
    _index, _metadata = index, metadata
    annotate("index_loaded_this_request", True)

    print(f"Index loaded: {_index.ntotal} vectors, {len(_metadata)} metadata entries")


def embed_query(query: str) -> np.ndarray:
    """Embed the query with Titan. Raises ServiceFailure (stage retrieval.embed)."""
    body = json.dumps({"inputText": query, "dimensions": 1024, "normalize": True})
    start = time.monotonic()
    with stage("retrieval.embed"):
        try:
            response = bedrock.invoke_model(
                modelId=EMBEDDING_MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
        except Exception as e:
            raise failure_from("retrieval.embed", e) from e
        try:
            payload = json.loads(response["body"].read())
            embedding = payload["embedding"]
        except (KeyError, TypeError, ValueError) as e:
            raise ServiceFailure("retrieval.embed", "invalid_model_output", type(e).__name__, str(e)) from e
    record_model_call(
        "embed_query",
        EMBEDDING_MODEL_ID,
        input_tokens=payload.get("inputTextTokenCount"),
        output_tokens=0,
        latency_ms=round((time.monotonic() - start) * 1000, 1),
    )
    return np.array([embedding], dtype=np.float32)


def retrieve_chunks(query: str, n_results: int = 5) -> list[dict]:
    """Top-n chunks for the query.

    Returns [] only when the search genuinely finds nothing. Infrastructure and
    model failures raise app.errors.ServiceFailure instead of looking like an
    empty result.
    """
    try:
        _load_index_if_needed()
    except Exception as e:
        raise failure_from("retrieval.index_load", e) from e

    query_embedding = embed_query(query)

    try:
        with stage("retrieval.search"):
            distances, indices = _index.search(query_embedding, n_results)
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            entry = _metadata[idx]
            results.append({
                "content": entry["text"],
                "source": entry["source"],
                "score": float(distance),
            })
    except Exception as e:
        raise failure_from("retrieval.search", e) from e

    return results


if __name__ == "__main__":
    load_dotenv()
    results = retrieve_chunks("What was JPMorgan Chase net revenue 2025?")
    for r in results:
        print(r["source"], r["score"])
        print(r["content"][:200])
        print("---")
