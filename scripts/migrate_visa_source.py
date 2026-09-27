"""Minimal S3 migration for the mislabeled Visa 10-K.

Visa Inc.'s FY2025 10-K was uploaded as docs/mastercard-10k-fy2025.pdf and indexed
under that name. This tool copies the PDF to docs/visa-10k-fy2025.pdf and rewrites
only the affected `source` values in the index metadata JSON. Vectors, row order,
chunk text and the FAISS binary are never modified; nothing is ever deleted.

Usage (from the repository root):
  python -m scripts.migrate_visa_source plan --out-dir DIR           read-only
  python -m scripts.migrate_visa_source execute --confirm MIGRATE-VISA
  python -m scripts.migrate_visa_source verify --expect-index-sha256 SHA
  python -m scripts.migrate_visa_source rollback --backup-key KEY --confirm ROLLBACK-VISA

S3 versioning is disabled on the bucket, so `execute` writes and verifies a
metadata backup before it overwrites the live metadata key.
"""
import argparse
import copy
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

OLD_PDF_KEY = "docs/mastercard-10k-fy2025.pdf"
NEW_PDF_KEY = "docs/visa-10k-fy2025.pdf"
BACKUP_PREFIX = "index/backups/"
EXECUTE_CONFIRMATION = "MIGRATE-VISA"
ROLLBACK_CONFIRMATION = "ROLLBACK-VISA"


class MigrationError(RuntimeError):
    pass


# --- pure helpers (unit-tested) ------------------------------------------------------

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def source_uri(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


def serialize_metadata(entries: list[dict]) -> bytes:
    """Same serialization build_index.py uses (json.dump defaults, ASCII-only)."""
    return json.dumps(entries).encode("ascii")


def source_histogram(entries: list[dict]) -> dict[str, dict]:
    """Rows per source, with first/last row and whether the rows are contiguous."""
    hist: dict[str, dict] = {}
    for i, row in enumerate(entries):
        info = hist.setdefault(row["source"], {"rows": 0, "first_row": i, "last_row": i})
        info["rows"] += 1
        info["last_row"] = i
    for info in hist.values():
        info["contiguous"] = info["last_row"] - info["first_row"] + 1 == info["rows"]
    return hist


def migrate_metadata(entries: list[dict], old_source: str, new_source: str) -> tuple[list[dict], list[int]]:
    """Return (migrated copy, changed row indices). Only `source` changes."""
    if any(row.get("source") == new_source for row in entries):
        raise MigrationError(f"metadata already contains {new_source}; refusing to migrate twice")
    changed = [i for i, row in enumerate(entries) if row.get("source") == old_source]
    if not changed:
        raise MigrationError(f"no metadata rows reference {old_source}")
    migrated = copy.deepcopy(entries)
    for i in changed:
        migrated[i]["source"] = new_source
    return migrated, changed


def validate_migration(original: list[dict], migrated: list[dict], old_source: str,
                       new_source: str) -> list[str]:
    """Every row must be identical except `source` old -> new. Returns problems."""
    problems = []
    if len(original) != len(migrated):
        return [f"row count changed: {len(original)} -> {len(migrated)}"]
    for i, (before, after) in enumerate(zip(original, migrated)):
        if set(before) != set(after):
            problems.append(f"row {i}: fields changed")
            continue
        for field_name in before:
            if field_name == "source":
                expected = new_source if before["source"] == old_source else before["source"]
                if after["source"] != expected:
                    problems.append(f"row {i}: source {after['source']!r} != {expected!r}")
            elif before[field_name] != after[field_name]:
                problems.append(f"row {i}: field {field_name!r} changed")
    return problems


def byte_level_check(original_bytes: bytes, migrated_bytes: bytes, old_source: str,
                     new_source: str, expected_rows: int) -> list[str]:
    """The new file must equal the old file with exactly the source strings replaced."""
    old_token = json.dumps({"source": old_source})[1:-1].encode("ascii")
    new_token = json.dumps({"source": new_source})[1:-1].encode("ascii")
    problems = []
    occurrences = original_bytes.count(old_token)
    if occurrences != expected_rows:
        problems.append(f"expected {expected_rows} source tokens in original bytes, found {occurrences}")
    if original_bytes.replace(old_token, new_token) != migrated_bytes:
        problems.append("migrated bytes differ from original beyond the source replacement")
    return problems


def compare_chunk_text(entries: list[dict], source: str, expected_texts: list[str]) -> dict:
    """Compare the indexed chunk text for one source with a fresh re-chunk of its PDF."""
    rows = [(i, row) for i, row in enumerate(entries) if row["source"] == source]
    indexed = [row["text"] for _, row in rows]
    mismatched = [rows[k][0] for k, (a, b) in enumerate(zip(indexed, expected_texts)) if a != b]
    return {
        "source": source,
        "indexed_rows": len(indexed),
        "rechunked": len(expected_texts),
        "identical": indexed == expected_texts,
        "mismatched_rows": mismatched[:10],
        "chunk_ids_match_rows": all(row.get("chunk_id") == i for i, row in rows),
    }


def backup_key_for(now: datetime) -> str:
    return f"{BACKUP_PREFIX}financial_meta.pre-visa-migration.{now.strftime('%Y%m%dT%H%M%SZ')}.json"


# --- S3 access ------------------------------------------------------------------------

class ReadOnlyS3:
    """Wraps an S3 client so read-only modes cannot write, even by mistake."""

    _ALLOWED = frozenset({"head_object", "get_object", "list_objects_v2"})

    def __init__(self, client):
        self._client = client

    def __getattr__(self, name):
        if name not in self._ALLOWED:
            raise MigrationError(f"read-only mode: S3 operation {name!r} is not allowed")
        return getattr(self._client, name)


def _head(s3, bucket: str, key: str) -> dict | None:
    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except Exception as e:  # botocore ClientError 404, or a fake in tests
        code = getattr(e, "response", {}).get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def _get(s3, bucket: str, key: str) -> bytes:
    return s3.get_object(Bucket=bucket, Key=key)["Body"].read()


def _etag(head: dict) -> str:
    return head["ETag"].strip('"')


def load_state(s3, bucket: str, index_key: str, meta_key: str) -> dict:
    """Read everything the migration depends on. Read-only."""
    old_head = _head(s3, bucket, OLD_PDF_KEY)
    if old_head is None:
        raise MigrationError(f"s3://{bucket}/{OLD_PDF_KEY} does not exist")
    meta_head = _head(s3, bucket, meta_key)
    index_head = _head(s3, bucket, index_key)
    if meta_head is None or index_head is None:
        raise MigrationError("index or metadata object is missing")
    old_pdf = _get(s3, bucket, OLD_PDF_KEY)
    meta_bytes = _get(s3, bucket, meta_key)
    index_bytes = _get(s3, bucket, index_key)
    return {
        "old_pdf_head": old_head,
        "new_pdf_head": _head(s3, bucket, NEW_PDF_KEY),
        "meta_head": meta_head,
        "index_head": index_head,
        "old_pdf": old_pdf,
        "meta_bytes": meta_bytes,
        "meta": json.loads(meta_bytes),
        "index_bytes": index_bytes,
    }


def check_preconditions(state: dict, bucket: str) -> tuple[list[dict], list[int], bytes]:
    """Validate state and build the migrated metadata. Raises MigrationError on any problem."""
    old_source = source_uri(bucket, OLD_PDF_KEY)
    new_source = source_uri(bucket, NEW_PDF_KEY)
    meta, meta_bytes = state["meta"], state["meta_bytes"]
    if serialize_metadata(meta) != meta_bytes:
        raise MigrationError("metadata re-serialization is not byte-identical; refusing to rewrite")
    if md5_hex(state["old_pdf"]) != _etag(state["old_pdf_head"]):
        raise MigrationError("downloaded PDF does not match its S3 ETag")
    if state["new_pdf_head"] is not None and _etag(state["new_pdf_head"]) != _etag(state["old_pdf_head"]):
        raise MigrationError(f"{NEW_PDF_KEY} already exists with different content")
    migrated, changed = migrate_metadata(meta, old_source, new_source)
    problems = validate_migration(meta, migrated, old_source, new_source)
    migrated_bytes = serialize_metadata(migrated)
    problems += byte_level_check(meta_bytes, migrated_bytes, old_source, new_source, len(changed))
    if problems:
        raise MigrationError("; ".join(problems[:5]))
    return migrated, changed, migrated_bytes


# --- modes ----------------------------------------------------------------------------------

def plan(s3, bucket: str, index_key: str, meta_key: str, local_pdf_dir: str | None = None,
         chunker=None, out_dir: str | None = None) -> dict:
    """Read-only verification and the exact list of writes `execute` would perform."""
    state = load_state(s3, bucket, index_key, meta_key)
    migrated, changed, migrated_bytes = check_preconditions(state, bucket)
    meta = state["meta"]
    report: dict = {
        "bucket": bucket,
        "objects": {
            OLD_PDF_KEY: {"size": len(state["old_pdf"]), "etag": _etag(state["old_pdf_head"]),
                          "sha256": sha256_hex(state["old_pdf"])},
            NEW_PDF_KEY: {"exists": state["new_pdf_head"] is not None},
            meta_key: {"size": len(state["meta_bytes"]), "etag": _etag(state["meta_head"]),
                       "sha256": sha256_hex(state["meta_bytes"])},
            index_key: {"size": len(state["index_bytes"]), "etag": _etag(state["index_head"]),
                        "sha256": sha256_hex(state["index_bytes"])},
        },
        "metadata": {
            "rows": len(meta),
            "chunk_ids_equal_row_index": all(row.get("chunk_id") == i for i, row in enumerate(meta)),
            "fields": sorted({k for row in meta for k in row}),
            "reserialization_byte_identical": True,
            "sources": source_histogram(meta),
            "rows_to_change": len(changed),
            "changed_row_range": [changed[0], changed[-1]],
            "migrated_sha256": sha256_hex(migrated_bytes),
            "migrated_size": len(migrated_bytes),
        },
    }
    report["index"] = inspect_index(state["index_bytes"], meta, source_uri(bucket, OLD_PDF_KEY))
    if local_pdf_dir:
        report["content"] = compare_local_pdfs(s3, bucket, meta, local_pdf_dir, chunker)
    report["writes"] = [
        {"action": "CopyObject", "source": meta_key, "destination": f"{BACKUP_PREFIX}financial_meta"
         ".pre-visa-migration.<UTC timestamp>.json", "verify": "sha256 == live metadata sha256"},
        {"action": "CopyObject", "source": OLD_PDF_KEY, "destination": NEW_PDF_KEY,
         "verify": "sha256 of copy == sha256 of original"},
        {"action": "PutObject (If-Match current ETag)", "destination": meta_key,
         "sha256": report["metadata"]["migrated_sha256"], "size": len(migrated_bytes)},
    ]
    report["never_written"] = [index_key, OLD_PDF_KEY]
    report["deletes"] = []
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "financial_meta.migrated.json"), "wb") as f:
            f.write(migrated_bytes)
        with open(os.path.join(out_dir, "financial_meta.original.json"), "wb") as f:
            f.write(state["meta_bytes"])
        with open(os.path.join(out_dir, "plan.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    return report


def inspect_index(index_bytes: bytes, meta: list[dict], affected_source: str, seed: int = 7) -> dict:
    """Structural checks plus cheap evidence that vectors line up with metadata rows.

    Exact text-to-vector identity can only be proven by re-embedding (a paid
    call). Vector-to-vector adjacency cannot detect a uniform shift, so the
    alignment evidence reported here is document-level: consecutive chunks
    share a 50-word overlap and are highly similar, so cosine similarity should
    drop sharply exactly at the metadata's document boundaries. A shift between
    vectors and metadata would move those drops off the boundaries.
    """
    import faiss
    import numpy as np

    index = faiss.deserialize_index(np.frombuffer(index_bytes, dtype=np.uint8))
    vectors = index.reconstruct_n(0, index.ntotal)
    norms = np.linalg.norm(vectors, axis=1)
    sources = [row["source"] for row in meta]
    rng = random.Random(seed)

    adjacent = [float(vectors[i] @ vectors[i + 1]) for i in range(len(sources) - 1)]
    same_doc = [c for i, c in enumerate(adjacent) if sources[i] == sources[i + 1]]
    same_doc_sorted = sorted(same_doc)
    # Percentile of each boundary's similarity among within-document adjacent pairs
    # (low = the boundary looks like a real document change).
    boundaries = {
        f"{i}|{i + 1}": {
            "cosine": round(c, 4),
            "percentile_among_same_doc_pairs": round(
                100 * sum(1 for s in same_doc_sorted if s < c) / len(same_doc_sorted), 2),
        }
        for i, c in enumerate(adjacent) if sources[i] != sources[i + 1]
    }
    random_pairs = [float(vectors[a] @ vectors[b]) for a, b in
                    ((rng.randrange(len(sources)), rng.randrange(len(sources))) for _ in range(2000)) if a != b]

    affected = [i for i, s in enumerate(sources) if s == affected_source]
    _, neighbours = index.search(vectors[affected], 6)
    purity = [sum(1 for n in row[1:] if sources[n] == affected_source) / 5 for row in neighbours]

    return {
        "type": type(index).__name__,
        "metric": "inner_product" if index.metric_type == faiss.METRIC_INNER_PRODUCT else str(index.metric_type),
        "dimension": index.d,
        "ntotal": index.ntotal,
        "ntotal_equals_metadata_rows": index.ntotal == len(meta),
        "norm_min": round(float(norms.min()), 6),
        "norm_max": round(float(norms.max()), 6),
        "mean_cosine_adjacent_same_doc": round(float(np.mean(same_doc)), 4),
        "mean_cosine_random_pairs": round(float(np.mean(random_pairs)), 4),
        "document_boundaries": boundaries,
        "affected_rows": len(affected),
        "affected_mean_neighbour_purity": round(float(np.mean(purity)), 4),
        "note": "Document-level alignment evidence only; row-level identity needs re-embedding a sample.",
    }


def compare_local_pdfs(s3, bucket: str, meta: list[dict], local_pdf_dir: str, chunker=None) -> list[dict]:
    """Byte-compare local PDFs with S3 (single-part ETag = MD5) and text-compare the chunks."""
    if chunker is None:
        from app.services.build_index import chunk_text, extract_text_from_pdf

        def chunker(pdf_bytes):
            return chunk_text(extract_text_from_pdf(pdf_bytes))

    local_names = {
        OLD_PDF_KEY: ("visa-10k-fy2025.pdf", "mastercard-10k-fy2025.pdf"),
    }
    results = []
    for source in source_histogram(meta):
        key = source.split(f"s3://{bucket}/", 1)[1]
        candidates = local_names.get(key, (os.path.basename(key),))
        path = next((os.path.join(local_pdf_dir, n) for n in candidates
                     if os.path.exists(os.path.join(local_pdf_dir, n))), None)
        if path is None:
            results.append({"source": source, "local_file": None, "identical": None})
            continue
        with open(path, "rb") as f:
            local_bytes = f.read()
        head = _head(s3, bucket, key)
        entry = compare_chunk_text(meta, source, chunker(local_bytes))
        entry.update({
            "local_file": os.path.basename(path),
            "local_md5_equals_s3_etag": head is not None and md5_hex(local_bytes) == _etag(head),
        })
        results.append(entry)
    return results


def execute(s3, bucket: str, index_key: str, meta_key: str, now: datetime | None = None) -> dict:
    """Perform the migration. Every step is verified before the next one runs."""
    state = load_state(s3, bucket, index_key, meta_key)
    migrated, changed, migrated_bytes = check_preconditions(state, bucket)
    original_sha = sha256_hex(state["meta_bytes"])
    index_sha = sha256_hex(state["index_bytes"])
    backup_key = backup_key_for(now or datetime.now(timezone.utc))

    # 1. Back up the live metadata and verify the copy.
    s3.copy_object(Bucket=bucket, Key=backup_key, CopySource={"Bucket": bucket, "Key": meta_key})
    if sha256_hex(_get(s3, bucket, backup_key)) != original_sha:
        raise MigrationError(f"backup {backup_key} does not match the live metadata; nothing else was written")

    # 2. Copy the PDF under its correct name and verify the copy.
    if state["new_pdf_head"] is None:
        s3.copy_object(Bucket=bucket, Key=NEW_PDF_KEY, CopySource={"Bucket": bucket, "Key": OLD_PDF_KEY})
    if sha256_hex(_get(s3, bucket, NEW_PDF_KEY)) != sha256_hex(state["old_pdf"]):
        raise MigrationError(f"{NEW_PDF_KEY} does not match {OLD_PDF_KEY}; live metadata not modified")

    # 3. Replace the live metadata, only if nobody changed it since we read it.
    s3.put_object(Bucket=bucket, Key=meta_key, Body=migrated_bytes, ContentType="application/json",
                  IfMatch=state["meta_head"]["ETag"])

    # 4. Verify the result and that the FAISS binary is untouched.
    problems = []
    if sha256_hex(_get(s3, bucket, meta_key)) != sha256_hex(migrated_bytes):
        problems.append("live metadata does not match the migrated file")
    if sha256_hex(_get(s3, bucket, index_key)) != index_sha:
        problems.append("FAISS index changed")
    if _head(s3, bucket, OLD_PDF_KEY) is None:
        problems.append("original PDF is missing")
    if problems:
        raise MigrationError(f"post-write verification failed ({'; '.join(problems)}); "
                             f"roll back with --backup-key {backup_key}")
    return {"backup_key": backup_key, "rows_changed": len(changed), "index_sha256": index_sha,
            "metadata_sha256": sha256_hex(migrated_bytes), "original_metadata_sha256": original_sha}


def verify(s3, bucket: str, index_key: str, meta_key: str, expect_index_sha256: str | None = None,
           backup_key: str | None = None) -> list[str]:
    """Read-only post-migration checks. Returns problems (empty means OK)."""
    old_source = source_uri(bucket, OLD_PDF_KEY)
    new_source = source_uri(bucket, NEW_PDF_KEY)
    problems = []
    meta = json.loads(_get(s3, bucket, meta_key))
    hist = source_histogram(meta)
    if old_source in hist:
        problems.append(f"{hist[old_source]['rows']} rows still reference {old_source}")
    if new_source not in hist:
        problems.append(f"no rows reference {new_source}")
    if backup_key:
        original = json.loads(_get(s3, bucket, backup_key))
        problems += validate_migration(original, meta, old_source, new_source)
    if expect_index_sha256 and sha256_hex(_get(s3, bucket, index_key)) != expect_index_sha256:
        problems.append("FAISS index sha256 differs from the expected value")
    old_pdf, new_pdf = _head(s3, bucket, OLD_PDF_KEY), _head(s3, bucket, NEW_PDF_KEY)
    if new_pdf is None:
        problems.append(f"{NEW_PDF_KEY} is missing")
    elif old_pdf is not None and _etag(old_pdf) != _etag(new_pdf):
        problems.append("new PDF ETag differs from the original")
    return problems


def rollback(s3, bucket: str, meta_key: str, backup_key: str) -> str:
    """Restore the live metadata from the backup. Leaves both PDFs in place."""
    backup_bytes = _get(s3, bucket, backup_key)
    json.loads(backup_bytes)  # must be valid JSON
    s3.put_object(Bucket=bucket, Key=meta_key, Body=backup_bytes, ContentType="application/json")
    restored = sha256_hex(_get(s3, bucket, meta_key))
    if restored != sha256_hex(backup_bytes):
        raise MigrationError("rollback verification failed")
    return restored


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["plan", "execute", "verify", "rollback"], nargs="?", default="plan")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--out-dir")
    parser.add_argument("--local-pdf-dir", default=os.path.join("..", "data"))
    parser.add_argument("--expect-index-sha256")
    parser.add_argument("--backup-key")
    args = parser.parse_args(argv)

    import boto3

    bucket = os.environ["S3_BUCKET_NAME"]
    index_key = os.environ["FAISS_INDEX_S3_KEY"]
    meta_key = os.environ["FAISS_META_S3_KEY"]
    s3 = boto3.client("s3", region_name="us-east-1")
    if args.mode in ("plan", "verify"):
        s3 = ReadOnlyS3(s3)

    try:
        if args.mode == "plan":
            report = plan(s3, bucket, index_key, meta_key, args.local_pdf_dir, out_dir=args.out_dir)
            print(json.dumps(report, indent=2))
        elif args.mode == "execute":
            if args.confirm != EXECUTE_CONFIRMATION:
                print(f"Refusing: pass --confirm {EXECUTE_CONFIRMATION}", file=sys.stderr)
                return 2
            print(json.dumps(execute(s3, bucket, index_key, meta_key), indent=2))
        elif args.mode == "verify":
            problems = verify(s3, bucket, index_key, meta_key, args.expect_index_sha256, args.backup_key)
            print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
            return 0 if not problems else 1
        else:
            if args.confirm != ROLLBACK_CONFIRMATION or not args.backup_key:
                print(f"Refusing: pass --backup-key KEY --confirm {ROLLBACK_CONFIRMATION}", file=sys.stderr)
                return 2
            print(json.dumps({"restored_sha256": rollback(s3, bucket, meta_key, args.backup_key)}, indent=2))
    except MigrationError as e:
        print(f"MIGRATION ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
