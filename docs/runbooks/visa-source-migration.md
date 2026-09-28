# Runbook: rename the Visa 10-K in S3 (metadata-only migration)

**Status:**
- **S3 writes executed and verified on 2026-09-28** (see [Execution record](#execution-record)).
- Pending, each needing separate approval: Lambda refresh, `/ask` smoke test, deletion of the
  old object.

## Background

Visa Inc.'s FY2025 10-K was uploaded as `docs/mastercard-10k-fy2025.pdf` and indexed under
that name. The facts:

- EDGAR accession `0001403161-25-000089`, CIK 1403161 = Visa, fiscal year ended 2025-09-30.
- The project now uses Visa as its fifth company. Mastercard is out of corpus.
- The migration copies the PDF to its correct name and rewrites the `source` string on the
  affected metadata rows.
- Chunk text, row order and every vector are unchanged. The FAISS binary is never written.

## Evidence the existing index can be reused (read-only checks)

Produced by `python -m scripts.migrate_visa_source plan`.

| Check | Result |
|---|---|
| S3 objects | `docs/` has 5 PDFs. `index/financial_index.faiss` (9,093,165 B) and `index/financial_meta.json` (7,749,302 B) were written 1 s apart (2026-04-26 19:42:46/47 UTC), after the PDFs (04:33:21 UTC) |
| Bucket versioning | **Never enabled.** An overwrite can't be undone unless we back up first |
| PDF identity | For every local PDF, MD5 = S3 ETag (single-part uploads). Visa file ETag `3b5252fff748927d32e5e24847f1f3d0` |
| Metadata rows | 2,220; `chunk_id` equals row index for every row. Fields: `chunk_id`, `chunk_preview`, `source`, `text` |
| Row order | Contiguous per document, in S3 listing order: BAC 0–444, BLK 445–681, GS 682–1531, JPM 1532–2050, Visa (old name) **2051–2219 (169 rows)** |
| Content identity | **All 2,220 rows** are text-identical to a fresh re-chunk of the matching PDF, using `build_index`'s own extraction and chunking code. This covers all 5 documents, not only Visa |
| Index structure | `IndexFlatIP`, d=1024, ntotal=2,220 (equals the metadata rows). All vectors have unit norm |
| Vector/row alignment | Adjacent same-document chunks (50-word overlap) have mean cosine 0.61; random pairs 0.17. All four document boundaries are in the bottom 1% of within-document adjacent similarity, and JPM→Visa (2050\|2051, cos 0.056) is the lowest in the index. This is document-level evidence. Exact row-level identity would need re-embedding a sample (paid) |
| Visa cluster | Mean nearest-neighbour purity 0.81. The 4 rows with purity 0 are boilerplate (auditor opinion, internal controls, lease notes) |
| Serialization | Re-serializing the metadata with `json.dump` defaults reproduces the S3 file byte for byte |
| Migrated file | Differs from the original only in 169 source strings (−1,014 bytes = 169 × 6) |

Embeddings were computed from chunk text only (`build_index.embed_texts(all_chunks)`). The
source path is not part of the embedding input. Renaming the source therefore cannot
invalidate any vector.

Recorded hashes:

| Object | SHA-256 |
|---|---|
| `index/financial_index.faiss` | `3d2b3ebd4f992aad3c2be8a09761a18fbc9a17d08d63db99bf6853697abfa5e9` (must stay unchanged) |
| `index/financial_meta.json` (current) | `30c2c187717a6ae791febe082eff105065f5b958bad17a5398a826912d98d23f` |
| `index/financial_meta.json` (migrated) | `f771ba6ce75759ba88e4ad376c642746327592afb991e107bd63c09029317429` |
| `docs/mastercard-10k-fy2025.pdf` | `eb17e780eb392e8f0b9001473a783fd6dfd880659803cb2b78af9ad5cab9e63d` |

## Exact S3 writes (execute step)

Bucket `financial-copilot-hl`, run from the repo root:

```
python -m scripts.migrate_visa_source execute --confirm MIGRATE-VISA
```

Steps, in order, each verified before the next:

| # | Operation | Object | Verification |
|---|---|---|---|
| 1 | CopyObject (write) | `index/financial_meta.json` → `index/backups/financial_meta.pre-visa-migration.<UTC yyyymmddThhmmssZ>.json` | SHA-256 of the backup equals the live metadata |
| 2 | CopyObject (write) | `docs/mastercard-10k-fy2025.pdf` → `docs/visa-10k-fy2025.pdf` | SHA-256 of the copy equals the original. Skipped if an identical copy already exists; aborts if a different object exists |
| 3 | PutObject with `If-Match` on the ETag read in the same run (overwrite) | `index/financial_meta.json` | SHA-256 equals `f771ba6c…`. The conditional write fails if the object changed in the meantime |
| 4 | Post-checks (read) | all | FAISS SHA-256 unchanged; original PDF still present |

**Never written:** `index/financial_index.faiss`, `docs/mastercard-10k-fy2025.pdf`.
**Never deleted:** anything. Deletion is a separate step with its own approval.

Required IAM permissions: `s3:GetObject` and `s3:PutObject` on `docs/*` and `index/*`. The
credentials used for the read-only checks have only been exercised for reads.

Afterwards, run the read-only check, using the backup key that `execute` prints:

```
python -m scripts.migrate_visa_source verify --expect-index-sha256 3d2b3ebd4f992aad3c2be8a09761a18fbc9a17d08d63db99bf6853697abfa5e9 --backup-key <backup key>
```

## Lambda warm containers

`retriever.py` keeps `_index` and `_metadata` in module globals for the lifetime of an
execution environment. It re-downloads from S3 only on a cold start.

- **After step 3:** new environments cite `docs/visa-10k-fy2025.pdf`. Warm environments keep
  citing `docs/mastercard-10k-fy2025.pdf` until they are recycled.
- **Effect:** answers are unaffected, because the text and vectors are identical. Only the
  citation string differs, so for a while some responses may show the old path.
- **Option A (no production change):** let environments recycle naturally. How long that takes
  is not guaranteed.
- **Option B (production change, needs approval):** make a function configuration update so
  new invocations run in fresh environments. For example, add an environment variable
  `INDEX_METADATA_VERSION=2026-09-visa`.
  - `aws lambda update-function-configuration --environment` **replaces the entire variable
    map**. Include every existing variable, or edit in the console.
- The deployed Lambda runs pre-Phase-0 code. The metadata change needs no code deployment.

## Deleting the old object (separate approval, after validation)

Preconditions:
- `verify` passes.
- Lambda environments have been refreshed.
- An approved `/ask` spot check (a paid Bedrock call) shows Visa citations.

```
aws s3api delete-object --bucket financial-copilot-hl --key docs/mastercard-10k-fy2025.pdf
```

**This is permanent (versioning is off).** The content survives in `docs/visa-10k-fy2025.pdf`
(verified identical). After deleting, remove the `mastercard-10k-fy2025.pdf` entry from
`LEGACY_SOURCE_NAMES` in `eval/metrics.py`.

**Do not run `python -m app.services.build_index` while both PDFs exist.** It indexes every
PDF under `docs/`, so Visa would be embedded twice.

## Rollback

Before the old object is deleted:

```
python -m scripts.migrate_visa_source rollback --backup-key <backup key> --confirm ROLLBACK-VISA
```

- This restores the original metadata bytes (SHA-256 `30c2c187…`) and verifies them.
- Then refresh Lambda environments the same way as for the forward change.
- `docs/visa-10k-fy2025.pdf` can stay; it isn't read at runtime. Removing it needs its own
  approval:
  ```
  aws s3api delete-object --bucket financial-copilot-hl --key docs/visa-10k-fy2025.pdf
  ```

After the old object has been deleted, first copy `docs/visa-10k-fy2025.pdf` back to
`docs/mastercard-10k-fy2025.pdf`, then run the rollback command above.

## Execution record

Executed 2026-09-28 01:06 UTC with
`python -m scripts.migrate_visa_source execute --confirm MIGRATE-VISA`.

- The preflight `plan` matched the recorded hashes.
- `execute` passed its internal post-checks.
- `verify` returned `{"ok": true, "problems": []}`.

| Item | Value |
|---|---|
| Backup key | `index/backups/financial_meta.pre-visa-migration.20260928T010613Z.json` (7,749,302 B, ETag `1830234705ac10210162097256fead8d`) |
| Original metadata SHA-256 | `30c2c187717a6ae791febe082eff105065f5b958bad17a5398a826912d98d23f` (= backup) |
| New metadata SHA-256 | `f771ba6ce75759ba88e4ad376c642746327592afb991e107bd63c09029317429` (7,748,288 B, ETag `64ae8c8d1da8872e228480b9fe334cbf`) |
| FAISS SHA-256 | `3d2b3ebd4f992aad3c2be8a09761a18fbc9a17d08d63db99bf6853697abfa5e9`, unchanged. LastModified still 2026-04-26 19:42:46 UTC |
| `docs/visa-10k-fy2025.pdf` | SHA-256 `eb17e780…` and ETag `3b5252ff…`, identical to `docs/mastercard-10k-fy2025.pdf` (kept) |

Independent read-only checks:
- 2,220 rows, and `chunk_id` equals the row index.
- 169 rows (2051–2219) cite `docs/visa-10k-fy2025.pdf`; none cite the old path.
- Those 169 are exactly the rows that cited the old path, and they are identical apart from
  `source`.
- The BAC (445), BLK (237), GS (850) and JPM (519) rows are identical in every field.
- A FAISS self-search using stored vectors returns the same row with the expected source.

Rollback from this state:

```
python -m scripts.migrate_visa_source rollback --backup-key index/backups/financial_meta.pre-visa-migration.20260928T010613Z.json --confirm ROLLBACK-VISA
```

Then refresh Lambda environments.
