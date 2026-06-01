import io
import json
import os
import tempfile
import time

import boto3
import faiss
import fitz
import numpy as np
from dotenv import load_dotenv

load_dotenv()

AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
FAISS_INDEX_S3_KEY = os.getenv("FAISS_INDEX_S3_KEY")
FAISS_META_S3_KEY = os.getenv("FAISS_META_S3_KEY")

s3 = boto3.client("s3", region_name="us-east-1")
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")


def extract_text_from_pdf(pdf_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text)
    return pages


def chunk_text(pages: list[str], chunk_size: int = 500, overlap: int = 50) -> list[str]:
    full_text = " ".join(pages)
    words = full_text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        if len(chunk_words) >= 20:
            chunks.append(" ".join(chunk_words))
        start += chunk_size - overlap
    return chunks


def embed_texts(texts: list[str]) -> np.ndarray:
    embeddings = []
    for i, text in enumerate(texts):
        embedding = _embed_single(text)
        embeddings.append(embedding)
        if i < len(texts) - 1:
            time.sleep(0.5)
    return np.array(embeddings, dtype=np.float32)


def _embed_single(text: str) -> list[float]:
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    try:
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        return json.loads(response["body"].read())["embedding"]
    except bedrock.exceptions.ThrottlingException:
        print("  ThrottlingException — retrying after 2s...")
        time.sleep(2)
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        return json.loads(response["body"].read())["embedding"]


def build_and_save_index(bucket: str, index_s3_key: str, meta_s3_key: str, docs_prefix: str = "docs/"):
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=docs_prefix)

    all_chunks = []
    all_metadata = []
    chunk_id = 0
    pdf_count = 0

    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(".pdf"):
                continue

            s3_uri = f"s3://{bucket}/{key}"
            print(f"Processing {s3_uri}...")

            try:
                response = s3.get_object(Bucket=bucket, Key=key)
                pdf_bytes = response["Body"].read()
                text_pages = extract_text_from_pdf(pdf_bytes)
                chunks = chunk_text(text_pages)

                for chunk in chunks:
                    all_chunks.append(chunk)
                    all_metadata.append({
                        "chunk_id": chunk_id,
                        "source": s3_uri,
                        "text": chunk,
                        "chunk_preview": chunk[:100],
                    })
                    chunk_id += 1

                pdf_count += 1
                print(f"  Extracted {len(chunks)} chunks")

            except Exception as e:
                print(f"  Error processing {s3_uri}: {e} — skipping")
                continue

    print(f"\nEmbedding {len(all_chunks)} total chunks from {pdf_count} PDFs...")
    embeddings = embed_texts(all_chunks)

    index = faiss.IndexFlatIP(1024)
    index.add(embeddings)

    local_index_path = os.path.join(tempfile.gettempdir(), "financial_index.faiss")
    local_meta_path = os.path.join(tempfile.gettempdir(), "financial_meta.json")

    faiss.write_index(index, local_index_path)
    with open(local_meta_path, "w") as f:
        json.dump(all_metadata, f)

    s3.upload_file(local_index_path, bucket, index_s3_key)
    s3.upload_file(local_meta_path, bucket, meta_s3_key)

    print(f"\nDone.")
    print(f"  PDFs processed : {pdf_count}")
    print(f"  Total chunks   : {len(all_chunks)}")
    print(f"  Index saved to : s3://{bucket}/{index_s3_key}")
    print(f"  Meta saved to  : s3://{bucket}/{meta_s3_key}")


if __name__ == "__main__":
    load_dotenv()
    build_and_save_index(
        bucket=os.getenv("S3_BUCKET_NAME"),
        index_s3_key=os.getenv("FAISS_INDEX_S3_KEY"),
        meta_s3_key=os.getenv("FAISS_META_S3_KEY"),
    )
