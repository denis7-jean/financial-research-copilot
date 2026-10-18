"""Tests for the Visa source migration and Visa/Mastercard regressions. In-memory S3; no AWS."""
import hashlib
import io
import json

import faiss
import numpy as np
import pytest

from app.services import bedrock_client, retriever
from scripts import migrate_visa_source as mig
from tests.conftest import FakeBedrock, converse_text

BUCKET = "financial-copilot-hl"
INDEX_KEY = "index/financial_index.faiss"
META_KEY = "index/financial_meta.json"
OLD_SRC = f"s3://{BUCKET}/{mig.OLD_PDF_KEY}"
NEW_SRC = f"s3://{BUCKET}/{mig.NEW_PDF_KEY}"
BAC_SRC = f"s3://{BUCKET}/docs/bank-of-america-10k-fy2025.pdf"
JPM_SRC = f"s3://{BUCKET}/docs/jpmorgan-chase-10k-fy2025.pdf"
DIM = 1024


class NotFound(Exception):
    def __init__(self):
        super().__init__("404")
        self.response = {"Error": {"Code": "404"}}


class FakeS3:
    """Minimal in-memory S3 with single-part MD5 ETags and write recording."""

    def __init__(self, objects: dict[str, bytes], reject_if_match: bool = False):
        self.objects = dict(objects)
        self.writes: list[tuple] = []
        self.reject_if_match = reject_if_match

    def _etag(self, key):
        return f'"{hashlib.md5(self.objects[key]).hexdigest()}"'

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise NotFound()
        return {"ETag": self._etag(Key), "ContentLength": len(self.objects[Key])}

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise NotFound()
        return {"Body": io.BytesIO(self.objects[Key])}

    def copy_object(self, Bucket, Key, CopySource):
        self.writes.append(("copy", CopySource["Key"], Key))
        self.objects[Key] = self.objects[CopySource["Key"]]

    def put_object(self, Bucket, Key, Body, ContentType=None, IfMatch=None):
        if IfMatch is not None and (self.reject_if_match or IfMatch != self._etag(Key)):
            raise RuntimeError("PreconditionFailed")
        self.writes.append(("put", Key))
        self.objects[Key] = Body

    def delete_object(self, Bucket, Key):
        self.writes.append(("delete", Key))
        del self.objects[Key]


def _unit(seed: int) -> np.ndarray:
    v = np.random.default_rng(seed).random(DIM).astype(np.float32)
    return v / np.linalg.norm(v)


def _corpus():
    """8 rows: 3 BAC, 3 JPM, 2 Visa (under the legacy name), with vectors and index bytes."""
    sources = [BAC_SRC] * 3 + [JPM_SRC] * 3 + [OLD_SRC] * 2
    meta = [{"chunk_id": i, "source": s, "text": f"chunk {i} text", "chunk_preview": f"chunk {i}"}
            for i, s in enumerate(sources)]
    vectors = np.stack([_unit(i + 1) for i in range(len(sources))])
    index = faiss.IndexFlatIP(DIM)
    index.add(vectors)
    return meta, vectors, index, faiss.serialize_index(index).tobytes()


def _s3(meta=None, extra=None, **kw) -> tuple[FakeS3, list[dict], bytes]:
    base_meta, _, _, index_bytes = _corpus()
    meta = meta if meta is not None else base_meta
    objects = {
        mig.OLD_PDF_KEY: b"%PDF-1.4 visa 10-k bytes",
        INDEX_KEY: index_bytes,
        META_KEY: mig.serialize_metadata(meta),
    }
    objects.update(extra or {})
    return FakeS3(objects, **kw), meta, index_bytes


# --- pure helpers --------------------------------------------------------------------

def test_serialization_matches_build_index_json_dump():
    meta, *_ = _corpus()
    buf = io.StringIO()
    json.dump(meta, buf)  # exactly what build_index.py does
    assert mig.serialize_metadata(meta) == buf.getvalue().encode("ascii")


def test_migrate_metadata_changes_only_visa_sources():
    meta, *_ = _corpus()
    migrated, changed = mig.migrate_metadata(meta, OLD_SRC, NEW_SRC)
    assert changed == [6, 7]
    assert [r["source"] for r in migrated] == [BAC_SRC] * 3 + [JPM_SRC] * 3 + [NEW_SRC] * 2
    for before, after in zip(meta, migrated):
        assert {k: v for k, v in before.items() if k != "source"} == {k: v for k, v in after.items() if k != "source"}
    assert meta[6]["source"] == OLD_SRC  # input not mutated
    assert mig.validate_migration(meta, migrated, OLD_SRC, NEW_SRC) == []


def test_migrate_metadata_refuses_to_run_twice_or_without_targets():
    meta, *_ = _corpus()
    migrated, _ = mig.migrate_metadata(meta, OLD_SRC, NEW_SRC)
    with pytest.raises(mig.MigrationError, match="already contains"):
        mig.migrate_metadata(migrated, OLD_SRC, NEW_SRC)
    with pytest.raises(mig.MigrationError, match="no metadata rows"):
        mig.migrate_metadata([r for r in meta if r["source"] != OLD_SRC], OLD_SRC, NEW_SRC)


@pytest.mark.parametrize("tamper", ["text", "reorder", "drop", "other_source"])
def test_validate_migration_detects_any_other_change(tamper):
    meta, *_ = _corpus()
    migrated, _ = mig.migrate_metadata(meta, OLD_SRC, NEW_SRC)
    if tamper == "text":
        migrated[2]["text"] = "changed"
    elif tamper == "reorder":
        migrated[0], migrated[1] = migrated[1], migrated[0]
    elif tamper == "drop":
        migrated.pop()
    else:
        migrated[0]["source"] = JPM_SRC
    assert mig.validate_migration(meta, migrated, OLD_SRC, NEW_SRC)


def test_byte_level_check_allows_only_source_replacement():
    meta, *_ = _corpus()
    migrated, changed = mig.migrate_metadata(meta, OLD_SRC, NEW_SRC)
    original, new = mig.serialize_metadata(meta), mig.serialize_metadata(migrated)
    assert mig.byte_level_check(original, new, OLD_SRC, NEW_SRC, len(changed)) == []
    assert len(original) - len(new) == len(changed) * (len("mastercard") - len("visa"))
    tampered = new.replace(b"chunk 0 text", b"chunk 0 TEXT")
    assert mig.byte_level_check(original, tampered, OLD_SRC, NEW_SRC, len(changed))


def test_source_histogram_reports_contiguous_blocks():
    meta, *_ = _corpus()
    hist = mig.source_histogram(meta)
    assert hist[OLD_SRC] == {"rows": 2, "first_row": 6, "last_row": 7, "contiguous": True}


def test_compare_chunk_text_detects_mismatch():
    meta, *_ = _corpus()
    ok = mig.compare_chunk_text(meta, OLD_SRC, ["chunk 6 text", "chunk 7 text"])
    bad = mig.compare_chunk_text(meta, OLD_SRC, ["chunk 6 text", "something else"])
    assert ok["identical"] and ok["chunk_ids_match_rows"]
    assert not bad["identical"] and bad["mismatched_rows"] == [7]


# --- plan (read-only) -------------------------------------------------------------------

def test_plan_is_read_only_and_lists_exact_writes(tmp_path):
    s3, meta, index_bytes = _s3()
    report = mig.plan(mig.ReadOnlyS3(s3), BUCKET, INDEX_KEY, META_KEY, out_dir=str(tmp_path))
    assert s3.writes == []
    assert report["metadata"]["rows_to_change"] == 2
    assert report["metadata"]["changed_row_range"] == [6, 7]
    assert report["objects"][INDEX_KEY]["sha256"] == hashlib.sha256(index_bytes).hexdigest()
    assert [w["action"].split(" ")[0] for w in report["writes"]] == ["CopyObject", "CopyObject", "PutObject"]
    assert report["writes"][1]["destination"] == mig.NEW_PDF_KEY
    assert INDEX_KEY in report["never_written"] and mig.OLD_PDF_KEY in report["never_written"]
    assert report["deletes"] == []
    assert report["index"]["ntotal_equals_metadata_rows"] is True
    assert set(report["index"]["document_boundaries"]) == {"2|3", "5|6"}
    written = json.loads((tmp_path / "financial_meta.migrated.json").read_bytes())
    assert [r["source"] for r in written][6:] == [NEW_SRC, NEW_SRC]


def test_plan_compares_local_pdfs(tmp_path):
    s3, meta, _ = _s3(extra={"docs/bank-of-america-10k-fy2025.pdf": b"bac pdf",
                             "docs/jpmorgan-chase-10k-fy2025.pdf": b"jpm pdf"})
    (tmp_path / "visa-10k-fy2025.pdf").write_bytes(s3.objects[mig.OLD_PDF_KEY])
    (tmp_path / "bank-of-america-10k-fy2025.pdf").write_bytes(b"bac pdf")
    (tmp_path / "jpmorgan-chase-10k-fy2025.pdf").write_bytes(b"jpm pdf - locally modified")
    texts = {b"bac pdf": [f"chunk {i} text" for i in range(3)],
             b"jpm pdf - locally modified": [f"chunk {i} text" for i in range(3, 6)],
             s3.objects[mig.OLD_PDF_KEY]: ["chunk 6 text", "chunk 7 text"]}
    report = mig.plan(mig.ReadOnlyS3(s3), BUCKET, INDEX_KEY, META_KEY, str(tmp_path), chunker=texts.__getitem__)
    by_file = {c["local_file"]: c for c in report["content"]}
    assert by_file["visa-10k-fy2025.pdf"]["identical"] and by_file["visa-10k-fy2025.pdf"]["local_md5_equals_s3_etag"]
    assert by_file["bank-of-america-10k-fy2025.pdf"]["local_md5_equals_s3_etag"] is True
    assert by_file["jpmorgan-chase-10k-fy2025.pdf"]["local_md5_equals_s3_etag"] is False


def test_plan_refuses_metadata_that_would_not_reserialize_identically():
    s3, meta, _ = _s3()
    s3.objects[META_KEY] = json.dumps(meta, indent=2).encode()
    with pytest.raises(mig.MigrationError, match="byte-identical"):
        mig.plan(mig.ReadOnlyS3(s3), BUCKET, INDEX_KEY, META_KEY)


def test_read_only_wrapper_blocks_writes():
    s3, *_ = _s3()
    ro = mig.ReadOnlyS3(s3)
    for op in ("copy_object", "put_object", "delete_object"):
        with pytest.raises(mig.MigrationError, match="read-only"):
            getattr(ro, op)
    assert s3.writes == []


# --- execute / verify / rollback ---------------------------------------------------------------

def test_execute_writes_exactly_three_objects_and_never_the_index():
    s3, meta, index_bytes = _s3()
    original_meta = s3.objects[META_KEY]
    original_pdf = s3.objects[mig.OLD_PDF_KEY]
    result = mig.execute(s3, BUCKET, INDEX_KEY, META_KEY)

    backup = result["backup_key"]
    assert backup.startswith(mig.BACKUP_PREFIX)
    assert s3.writes == [("copy", META_KEY, backup), ("copy", mig.OLD_PDF_KEY, mig.NEW_PDF_KEY), ("put", META_KEY)]
    assert all(w[-1] != INDEX_KEY for w in s3.writes)
    assert s3.objects[INDEX_KEY] == index_bytes
    assert s3.objects[backup] == original_meta
    assert s3.objects[mig.OLD_PDF_KEY] == original_pdf  # original kept for rollback
    assert s3.objects[mig.NEW_PDF_KEY] == original_pdf
    live = json.loads(s3.objects[META_KEY])
    assert mig.validate_migration(meta, live, OLD_SRC, NEW_SRC) == []
    assert mig.verify(s3, BUCKET, INDEX_KEY, META_KEY, result["index_sha256"], backup) == []


def test_verify_fails_before_migration():
    s3, *_ = _s3()
    problems = mig.verify(mig.ReadOnlyS3(s3), BUCKET, INDEX_KEY, META_KEY)
    assert any("still reference" in p for p in problems)
    assert any(mig.NEW_PDF_KEY in p for p in problems)


def test_execute_is_not_repeatable():
    s3, *_ = _s3()
    mig.execute(s3, BUCKET, INDEX_KEY, META_KEY)
    writes = len(s3.writes)
    with pytest.raises(mig.MigrationError):
        mig.execute(s3, BUCKET, INDEX_KEY, META_KEY)
    assert len(s3.writes) == writes


def test_execute_aborts_before_writing_if_target_pdf_differs():
    s3, *_ = _s3(extra={mig.NEW_PDF_KEY: b"some other document"})
    with pytest.raises(mig.MigrationError, match="different content"):
        mig.execute(s3, BUCKET, INDEX_KEY, META_KEY)
    assert s3.writes == []


def test_execute_skips_pdf_copy_when_identical_copy_exists():
    s3, *_ = _s3()
    s3.objects[mig.NEW_PDF_KEY] = s3.objects[mig.OLD_PDF_KEY]
    mig.execute(s3, BUCKET, INDEX_KEY, META_KEY)
    assert [w[0] for w in s3.writes] == ["copy", "put"]


def test_conditional_put_protects_against_concurrent_metadata_change():
    s3, *_ = _s3(reject_if_match=True)
    original_meta = s3.objects[META_KEY]
    with pytest.raises(RuntimeError, match="PreconditionFailed"):
        mig.execute(s3, BUCKET, INDEX_KEY, META_KEY)
    assert s3.objects[META_KEY] == original_meta


def test_rollback_restores_original_metadata():
    s3, *_ = _s3()
    original_meta = s3.objects[META_KEY]
    result = mig.execute(s3, BUCKET, INDEX_KEY, META_KEY)
    mig.rollback(s3, BUCKET, META_KEY, result["backup_key"])
    assert s3.objects[META_KEY] == original_meta
    assert mig.OLD_PDF_KEY in s3.objects and mig.NEW_PDF_KEY in s3.objects
    assert not any(w[0] == "delete" for w in s3.writes)


def test_execute_cli_requires_confirmation(capsys):
    assert mig.main(["execute"]) == 2
    assert mig.main(["rollback", "--backup-key", "k"]) == 2
    assert "Refusing" in capsys.readouterr().err


# --- Visa retrieval and citation regressions ---------------------------------------------------

@pytest.fixture
def installed_corpus(monkeypatch):
    meta, vectors, index, _ = _corpus()

    def install(rows):
        monkeypatch.setattr(retriever, "_index", index)
        monkeypatch.setattr(retriever, "_metadata", rows)

    return meta, vectors, install


def _search(monkeypatch, vector, n=3):
    monkeypatch.setattr(retriever, "bedrock", FakeBedrock(
        invoke_responses=[{"embedding": vector.tolist(), "inputTextTokenCount": 5}]))
    return retriever.retrieve_chunks("q", n_results=n)


def test_visa_chunks_are_cited_under_the_visa_source_after_migration(monkeypatch, installed_corpus):
    meta, vectors, install = installed_corpus
    migrated, _ = mig.migrate_metadata(meta, OLD_SRC, NEW_SRC)
    install(migrated)
    chunks = [{"content": c["content"], "source": c["source"], "score": c["score"]}
              for c in _search(monkeypatch, vectors[6], n=1)]
    assert chunks[0]["source"] == NEW_SRC
    assert chunks[0]["content"] == "chunk 6 text"

    monkeypatch.setattr(bedrock_client, "retrieve_chunks", lambda q, n_results=5: chunks)
    monkeypatch.setattr(bedrock_client, "bedrock", FakeBedrock(converse_responses=[converse_text("$40,000 million")]))
    result = bedrock_client.retrieve_and_generate("What was Visa's net revenue?")
    assert result["citations"] == [NEW_SRC]
    assert all("mastercard" not in c["source"] for c in result["retrieved_context"])


@pytest.mark.parametrize("row", [0, 2, 3, 5])
def test_other_companies_retrieve_identically_before_and_after(monkeypatch, installed_corpus, row):
    meta, vectors, install = installed_corpus
    install(meta)
    before = _search(monkeypatch, vectors[row], n=len(meta))
    migrated, _ = mig.migrate_metadata(meta, OLD_SRC, NEW_SRC)
    install(migrated)
    after = _search(monkeypatch, vectors[row], n=len(meta))
    assert [(c["content"], c["score"]) for c in before] == [(c["content"], c["score"]) for c in after]
    for b, a in zip(before, after):
        expected = NEW_SRC if b["source"] == OLD_SRC else b["source"]
        assert a["source"] == expected
    assert before[0]["source"] in (BAC_SRC, JPM_SRC)
