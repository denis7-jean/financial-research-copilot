# Financial Research Multi-Agent Copilot

A production-grade agentic AI system built on AWS that answers questions
and generates summaries from FY2025 SEC 10-K filings using a router-based
multi-agent architecture.

**Deployment:** the `financial-copilot` Lambda function exists in `us-east-1` (Python 3.11,
`$LATEST` only, dependencies in the `financial-copilot-deps` layer). It currently has **no public
HTTP entry point**: no Function URL, no API Gateway and no invoke permission for other
principals, so it can only be invoked directly with AWS credentials.

As of 2026-09-28, production Bedrock calls are also blocked while AWS completes an account-level
verification.

---

## What This Demonstrates

- **Multi-agent orchestration** — RouterAgent classifies intent and dispatches to specialized agents
- **Manual RAG pipeline** — PDF extraction → chunking → Titan Embeddings V2 → FAISS vector search → Claude generation, all via pure boto3
- **Production CI/CD** — 5-job GitHub Actions pipeline. An LLM-as-judge gate enforces ≥ 80% context relevance and faithfulness on 19 labeled QA cases
- **Serverless deployment** — FastAPI + Mangum on AWS Lambda (see Deployment above for the current state)
- **Observability** — one structured `request.timing` record per request: stage latency, Bedrock token usage, router outcome, cold-start flag and trace ID

---

## Architecture

```
User Query
↓
FastAPI (/ask or /summarize)          ← Mangum ASGI adapter on AWS Lambda
↓
CopilotOrchestrator
↓
RouterAgent (Claude Haiku 4.5)        ← classifies: "qa" or "summarize" (/ask only)
↓                    ↓
QAAgent              SummarizerAgent  ← direct Converse call, no retrieval
↓
retriever.py                          ← Titan query embedding + FAISS similarity search
↓
bedrock_client.py                     ← Claude Haiku 4.5 via Converse API
↓
Pydantic validated response + trace_id
```

`/summarize` bypasses the router and goes straight to the SummarizerAgent.

**RAG Pipeline (one-time indexing):**

```
5 x FY2025 10-K PDFs (S3)             ← JPM, GS, BAC, BLK, Visa
↓ PyMuPDF extraction
↓ 500-word chunks (50-word overlap)
↓ Titan Embeddings V2 (1024 dims)
↓ FAISS IndexFlatIP
→ 2,220 vectors stored on S3
```

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Claude Haiku 4.5 (router, QA, summarizer), Claude Sonnet 4.6 (eval judge) |
| Embeddings | Amazon Titan Embeddings V2 |
| Vector store | FAISS IndexFlatIP (manual, $0/month) |
| API framework | FastAPI + Mangum |
| Deployment | AWS Lambda (no public HTTP entry point at present) |
| Storage | Amazon S3 |
| LLM API | Amazon Bedrock (pure boto3, no wrappers) |
| CI/CD | GitHub Actions (5-job pipeline) |
| Eval | Custom LLM-as-judge with labeled cases (RAGAS-inspired) |
| Linting | Ruff |

**Hard constraints (no exceptions):**
- Pure boto3 for all Bedrock calls — no LangChain, no Anthropic SDK, no OpenAI SDK
- No Docker, no provisioned concurrency, no managed vector stores
- requirements.txt only — no pyproject.toml

---

## Eval Results

**Measured** (last run of the pre-Phase-0 harness, 2026-06-04; archived at
`eval/results/legacy/2026-06-04_pre_phase0_harness.json`):

| Metric | Score | Threshold |
|---|---|---|
| Context Relevance | 80% (8/10) | 80% |
| Faithfulness | 80% (8/10) | 80% |
| Mean Context Relevance | 3.8 / 5 | — |
| Mean Faithfulness | 4.6 / 5 | — |

What that run did **not** measure:
- Only 10 of the 20 queries were judged. The 9 routed to the summarizer were skipped, and the
  boundary queries were excluded.
- Routing accuracy, answer correctness and abstention were not measured.
- The population depended on router output.

**Current harness (Phase 0)** — see [`eval/README.md`](eval/README.md):
- 34 labeled cases.
- Separate metrics for routing, retrieval relevance, faithfulness, summary grounding, answer
  correctness, abstention and cross-company contamination.
- Label-based gate populations.
- Latency and token capture per case.

**It has not been run yet.** No results from the new harness exist, and none are claimed here.

---

## CI/CD Pipeline

```
lint → unit-tests → integration-tests → eval-gate → deploy-ready
```

What each job actually verifies:

- **lint** — `ruff check app/ eval/ tests/ scripts/`.
- **unit-tests** — `pytest tests/ -m "not llm and not integration"`:
  - Covers routing and fallbacks, error paths, response contracts, `/evaluate` access control,
    trace records and all evaluation/metric logic.
  - Bedrock, S3 and CloudWatch are mocked.
  - The test harness forces fake credentials and blocks botocore network I/O, so these tests
    cannot reach AWS.
- **integration-tests** (live AWS):
  - Starts uvicorn and checks `/health`.
  - Runs `python -m scripts.smoke_check` with two known in-corpus questions (JPMorgan Chase and
    Visa FY2025 net revenue).
  - Each must return HTTP 200 with no `error`, a real answer (not the no-evidence answer), a
    citation of the expected filing and the expected figure.
  - Infrastructure failures return 5xx and fail the job.
- **eval-gate** (live, billable) — `pytest eval/test_llm_judge.py -m llm`:
  - Runs all 34 cases.
  - Fails the build if context relevance or faithfulness falls below 80% on the gated QA
    population.
  - Other metrics are report-only.
  - Results are uploaded as a build artifact.
- **deploy-ready** — confirms the earlier jobs passed. **It does not deploy anything.**
  Deployment is a manual step (`scripts/package_lambda.ps1`).

The pipeline runs on pushes and pull requests to `main`. The integration and eval-gate jobs make
Bedrock calls.

---

## Observability

Each `/ask`, `/summarize` and (authorized) `/evaluate` request writes one JSON line to stdout,
which Lambda ships to CloudWatch Logs. The record has `"event": "request.timing"` and contains:

- `trace_id` (the same value returned in the response)
- `endpoint`
- `cold_start` (true only for the first request in a process)
- `total_ms`
- `stages_ms`: `route`, `agent`, `retrieval.index_load`, `retrieval.embed`, `retrieval.search`,
  `qa.build_context`, `llm.qa_generate`, `llm.summarize`, `request_log`
- `model_calls`: input/output tokens and Bedrock server latency for each of `router`,
  `embed_query`, `qa_generate` and `summarize`
- `route`: task type, confidence, and `router_outcome` (`model`, `fallback_invoke_error`,
  `fallback_parse_error`, `fallback_low_confidence` or `direct`)
- `errors`: sanitized failures (`stage`, `kind`, `code`, `retryable`, `fatal`). A router
  fallback is recorded as non-fatal
- `attrs`: includes `http_status` and `outcome` (`generated`, `no_evidence` or `failed`)
- `query_chars` and a 12-character SHA-256 prefix of the query

The query text itself is never logged. The digest is pseudonymous, not anonymous.

The custom log group `/financial-copilot/requests` still receives a small per-request entry. It
is on by default; set `COPILOT_CW_REQUEST_LOG=false` to disable it. The entry now carries
`query_chars` in place of the former 100-character `query_preview`.

**Measured latency data:** none is committed to this repository. The example response below is a
single request, not a benchmark. P50/P95 figures will come from the first approved baseline eval
run or from CloudWatch Logs Insights over `request.timing` records.

---

## API Usage

There is currently no public endpoint (see Deployment). The examples use a local server
(`uvicorn app.main:app --port 8000`).

**Health check:**
```bash
curl http://localhost:8000/health
```

**Ask a question (RAG):**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What was JPMorgan net revenue in FY2025?"}'
```

**Summarize:**
```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize Goldman Sachs key risks in 2025"}'
```

**Example response** (one request; illustrative, not a benchmark):
```json
{
  "task_type": "qa",
  "router_confidence": 0.95,
  "result": {
    "answer": "JPMorgan Chase total net revenue for FY2025 was $182.447 billion...",
    "confidence": 1.0,
    "agent": "qa",
    "latency_ms": 2736.9
  },
  "agent_used": "qa",
  "total_latency_ms": 3630.0,
  "trace_id": "c48be98d-c164-40bd-99cd-a0d30dfc0e78"
}
```

`total_latency_ms` is router plus agent time only.

**Outcomes and status codes**

Legitimate outcomes return **200** with the normal contract:
- a grounded answer;
- an evidence-based abstention ("the documents don't contain…");
- a genuinely empty retrieval (`"answer": "No relevant documents found."`, no citations).

Infrastructure and model failures return the same body shape with `"result": {}`, a sanitized
`error` message and `error_detail`
(`{"stage", "kind", "code", "retryable"}`). Raw provider messages, ARNs and account IDs never
appear in responses.

| `kind` | Status | Example |
|---|---|---|
| `access_denied` | 503 | Bedrock `AccessDeniedException` |
| `throttled` | 503 | `ThrottlingException` (retryable) |
| `unavailable` | 503 | connection failure, provider 5xx (retryable) |
| `timeout` | 504 | read/connect timeout, `ModelTimeoutException` (retryable) |
| `model_error`, `invalid_model_output` | 502 | malformed or empty model output, unparseable summary |
| `configuration`, `internal` | 500 | missing S3 object or model ID, unexpected exception |

A router failure on its own does not fail the request: routing falls back to `qa`.
`/evaluate` is a batch endpoint, so it stays 200 overall with per-case `error_detail`.

**`/evaluate`** is disabled by default and returns 404. To enable it:
- Set `ENABLE_EVALUATE_ENDPOINT=true` **and** a non-empty `EVALUATE_ENDPOINT_TOKEN`.
- Send the token in an `X-Evaluate-Token` header.
- A request may contain at most 25 cases, with queries of at most 2,000 characters.

---

## Data Sources

Five FY2025 10-K filings stored in S3:

- JPMorgan Chase
- Goldman Sachs
- Bank of America
- BlackRock
- Visa (fiscal year ended September 30, 2025)

**Mastercard is not covered.** Questions about Mastercard (or any other company outside the
five) are out of corpus; the correct behavior is to say the documents don't contain the answer.

**S3 rename (2026-09-28).** Visa's 10-K was originally uploaded as
`docs/mastercard-10k-fy2025.pdf`. It is now also at `docs/visa-10k-fy2025.pdf`, and the index
metadata cites the new path. The FAISS index was not changed. See
[`docs/runbooks/visa-source-migration.md`](docs/runbooks/visa-source-migration.md).

No Lambda refresh was needed. The function had 0 invocations in the previous 90 days, so no
warm container held the old metadata, and a cold start on 2026-09-28 loaded the migrated file.

Still pending:
- A production smoke test (blocked by the Bedrock account verification).
- Deletion of the old object.

---

## Known Limitations

- **The earlier "Mastercard retrieval" failures** came from the mislabeled file: Mastercard was
  never in the corpus. Retrieval ranking was not the cause (see Data Sources).
- **No company filtering in retrieval.** Top-5 similarity search runs over the shared index, so
  chunks from other companies can appear in the context.
- **The summarizer is not grounded.** SummarizerAgent calls Claude without retrieval. When
  `/ask` routes a question to it, the answer is not based on the filings.
- **Deployed code predates these changes.** The Lambda still runs the June 2026 build, which
  reports failures as HTTP 200 with a "No relevant documents found." answer. The 5xx behavior
  above applies once this code is deployed.
- **`/ask` and `/summarize` are unauthenticated** and allow CORS from any origin.
- **Packaging script.**
  - `scripts/package_lambda.ps1` installs packages for the host platform. On Windows that means
    Windows binaries, for example `pydantic_core`.
  - It does not install `faiss-cpu` or `numpy`.
  - A package built this way on Windows will not import on Lambda (Linux) unless those gaps are
    covered some other way, such as a Linux build or a layer.

---

## Local Setup

```bash
# Clone
git clone https://github.com/denis7-jean/financial-research-copilot.git
cd financial-research-copilot

# Environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your AWS credentials and config to .env

# Run locally
uvicorn app.main:app --reload --port 8000

# Offline tests (no AWS calls)
pytest tests/ -m "not llm and not integration" -v
```

**Required `.env` keys:**
```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
JUDGE_MODEL_ID=us.anthropic.claude-sonnet-4-6
S3_BUCKET_NAME=financial-copilot-hl
FAISS_INDEX_S3_KEY=index/financial_index.faiss
FAISS_META_S3_KEY=index/financial_meta.json
```

**Optional keys:**
```
COPILOT_CW_REQUEST_LOG=true        # custom CloudWatch request log (default on)
ENABLE_EVALUATE_ENDPOINT=false     # /evaluate stays 404 unless true AND a token is set
EVALUATE_ENDPOINT_TOKEN=           # secret; set in the deployment environment, never commit
EVAL_RESULTS_PATH=eval/results/latest.json
EVAL_SLEEP_SECONDS=2
```

---

## Project Structure

```
app/
├── main.py                  ← FastAPI app, request tracing, CloudWatch request log
├── lambda_handler.py        ← Mangum ASGI adapter for Lambda
├── observability.py         ← request.timing trace: stages, tokens, cold start
├── errors.py                ← ServiceFailure: classified, sanitized failures → HTTP status
├── agents/
│   ├── orchestrator.py      ← CopilotOrchestrator
│   ├── router.py            ← RouterAgent (intent classification)
│   ├── qa_agent.py          ← QAAgent (RAG-grounded answers)
│   └── summarizer_agent.py  ← SummarizerAgent (no retrieval)
└── services/
    ├── build_index.py       ← One-time PDF → FAISS indexing pipeline
    ├── retriever.py         ← FAISS similarity search
    └── bedrock_client.py    ← RAG generation via Bedrock

eval/
├── README.md                ← Evaluation methodology, metrics, gates, cost
├── eval_queries.py          ← 34 labeled cases with verified references
├── metrics.py               ← Pure metric/gate logic (single source of thresholds)
├── llm_judge.py             ← LLM-as-judge harness (live)
├── test_llm_judge.py        ← CI eval gate (live)
└── results/legacy/          ← Archived pre-Phase-0 result

tests/                       ← Offline unit tests (network blocked in conftest.py)

scripts/
├── package_lambda.ps1       ← Lambda packaging (manual)
├── smoke_check.py           ← CI/post-deploy /ask check (live when run)
└── migrate_visa_source.py   ← S3 Visa rename: read-only plan, gated execute/rollback

docs/runbooks/
└── visa-source-migration.md ← Evidence, exact S3 writes, Lambda refresh, rollback

.github/workflows/
└── eval-ci.yml              ← 5-job CI/CD pipeline
```

---

*Built as a portfolio project demonstrating production agentic AI engineering on AWS.*
