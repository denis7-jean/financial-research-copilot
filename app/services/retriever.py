import json
import os
import tempfile

import boto3
import faiss
import numpy as np
from dotenv import load_dotenv

load_dotenv()

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
        return

    local_index_path = os.path.join(tempfile.gettempdir(), "financial_index.faiss")
    local_meta_path = os.path.join(tempfile.gettempdir(), "financial_meta.json")

    print("Loading FAISS index from S3...")
    s3.download_file(S3_BUCKET_NAME, FAISS_INDEX_S3_KEY, local_index_path)
    s3.download_file(S3_BUCKET_NAME, FAISS_META_S3_KEY, local_meta_path)

    _index = faiss.read_index(local_index_path)
    with open(local_meta_path, "r") as f:
        _metadata = json.load(f)

    print(f"Index loaded: {_index.ntotal} vectors, {len(_metadata)} metadata entries")


def embed_query(query: str) -> np.ndarray:
    body = json.dumps({"inputText": query, "dimensions": 1024, "normalize": True})
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    embedding = json.loads(response["body"].read())["embedding"]
    return np.array([embedding], dtype=np.float32)


def retrieve_chunks(query: str, n_results: int = 5) -> list[dict]:
    try:
        _load_index_if_needed()
        query_embedding = embed_query(query)
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

        return results

    except Exception as e:
        print(f"retrieve_chunks error: {e}")
        return []


if __name__ == "__main__":
    load_dotenv()
    results = retrieve_chunks("What was JPMorgan Chase net revenue 2025?")
    for r in results:
        print(r["source"], r["score"])
        print(r["content"][:200])
        print("---")
