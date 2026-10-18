# Financial Research Multi-Agent Copilot

A financial-document research application built with FastAPI, Amazon Bedrock,
S3 and FAISS. It routes questions to retrieval-backed QA or a summarization
agent, using a five-company corpus labelled as FY2025 10-K filings.

**Upgrade status:** the agreed three-item Upgrade scope is complete. The repaired
artifact was deployed to an isolated Lambda function and published as **Version 1**.
A single qualified, end-to-end RAG smoke returned successfully, retrieved **five
JPMorgan hits**, and produced a non-abstaining answer supported by the bound test
corpus. See the [completion note](docs/experiments/upgrade-completion.md).

**Haiku remains the default.** The ordinary application now supports explicit
Jev intent routing, demonstrated live on two in-sample queries with downstream
Haiku generation. This does not establish routing-quality qualification or a
production rollout. No deployment/default configuration was changed. The
ordinary HTTP application and isolated smoke handler remain separate entry points.

## What This Demonstrates

- **Agent orchestration:** intent routing to QA or summarization.
- **Manual RAG:** PDF extraction, chunking, Titan embeddings, FAISS search and
  Haiku answer generation through boto3.
- **Explicit experimental controls:** isolated smoke inputs, object integrity,
  request budgets, one-use claims and no-retry gates.
- **Serverless application:** FastAPI through Mangum, plus a dedicated isolated
  smoke handler on Lambda.
- **Observability and evaluation:** structured timings, token accounting,
  guarded offline tests and separately authorized live evaluation tools.

## Architecture

```text
FastAPI /ask -> CopilotOrchestrator -> Haiku (default) or Jev (explicit opt-in)
                                      | qa                 | summarize
                                      v                    v
                                   QAAgent           SummarizerAgent
                                      |              direct generation
                         S3 index + metadata               (no retrieval)
                                      |
                         Titan query embedding (1024 dimensions)
                                      |
                         FAISS IndexFlatIP top-5 search
                                      |
                         Haiku generation from retrieved context
                                      |
                         Answer, citations and response metadata
```

`/summarize` bypasses intent routing. The separate
`app.rag_smoke_handler.handler` uses the reviewed, bounded smoke path; it is not
an HTTP endpoint or a switch that enables Jev in the application.

The indexing utility extracts PDFs into 500-word chunks with 50-word overlap,
embeds them with Titan Embeddings V2 and writes an index and metadata to S3.
The accepted test snapshot has 2,220 vectors. Index construction is a separate,
billable operation, not a prerequisite to rerun for an existing snapshot.

## Tech Stack

| Component | Implementation |
|---|---|
| Intent routing | Claude Haiku 4.5 by default; explicit Jev HTTP opt-in |
| Generation | Claude Haiku 4.5 through Amazon Bedrock Converse |
| Query embeddings | Amazon Titan Embeddings V2 |
| Retrieval | FAISS IndexFlatIP with S3-backed index and metadata |
| API | FastAPI, Pydantic and Mangum |
| Runtime | Local Python application; isolated Lambda ZIP deployment |
| Testing | pytest, offline network guards and synthetic fixtures |
| CI | Offline packaging checks, lint and guarded regressions |

## Jev Intent Routing

Set `COPILOT_ROUTER_PROVIDER=jev` and supply a nonempty `TYPESAFE_API_KEY` through
your authorized environment or secret store **before starting/importing the
application**. The HTTP classifier is pinned to `jev-1.13.0`. Missing or invalid
keys fail configuration; arbitrary injected live transports remain rejected.
Shadow routing remains disabled.

For the unconfigured default or rollback, leave `COPILOT_ROUTER_PROVIDER` unset
or set it to `haiku`, then restart the application. Haiku does not need the Jev
key. Keep `BEDROCK_MODEL_ID` set to Haiku: Jev replaces only the existing binary
`qa`/`summarize` classifier. QA still uses the same S3-backed index, Titan query
embedding, FAISS top-five retrieval and downstream Haiku generation. Summarize
still uses direct Haiku generation without retrieval. `/summarize` still bypasses
intent classification; `/ask` exercises the selected router.

Jev uses the selected label's probability and the existing 0.6 threshold.
A lower score, malformed response or invocation error falls back to QA with
confidence 0.5 and sanitized fallback reasoning. It does not call Haiku for a
second classification. Missing-key configuration errors fail before routing.
Existing downstream error handling and public response shapes are unchanged.
The Jev client disables retries, redirects and environment proxy discovery;
its owned connection is closed at application shutdown.

### Observed application integration

On **2026-10-18**, one explicitly authorized run exercised the ordinary
in-process `/ask` endpoint with two fixed, in-sample queries:

| Query | Jev intent / dispatch | Observed downstream result |
|---|---|---|
| JPMorgan Chase total net revenue for fiscal year 2025 | `qa` / QAAgent | Five retrieval hits, source citation and a substantive Haiku answer |
| Summarize the key risks in Goldman Sachs 2025 annual report | `summarize` / SummarizerAgent | Nonempty Haiku summary, key points and risk flags |

Both cases reported provider `jev`, model `jev-1.13.0`, `router_live=true`, HTTP
200 and `router_outcome=model`, with one classifier attempt each and no fallback.
Both passed the bounded test's completion assertions. The run used two Jev POSTs,
two Haiku Converse calls, one Titan embedding call and two S3 HEAD plus two GET
attempts, with no retry or rejected extra attempt. Generation used a **test-only
`maxTokens=1024`** cap; ordinary generation behavior was not changed.

This demonstrates real Jev application intent integration on two in-sample
queries. It adds no routing-quality qualification, held-out accuracy evidence,
external-server validation or production deployment. The summary is not grounded
in a retrieved filing, and the QA result does not independently authenticate
financial facts or establish exact answer-to-passage attribution. Private results,
credentials and operational evidence remain outside Git. This completed one-use
test provides no authority to rerun live calls.

## Deployment and Observed RAG Result

The repaired, self-contained Linux/Python 3.11 artifact uses the explicit smoke
handler. Its published **Version 1** received one qualified
`RequestResponse`/`Tail` Invoke: HTTP 200, executed version 1, no function error,
and a structural-success result.

| Bound test-corpus question | Observed result |
|---|---|
| JPMorgan Chase total net revenue for fiscal year 2025 | Five of five JPMorgan hits; answer **$182.447 billion**, comprising $87.004 billion noninterest revenue and $95.443 billion net interest income |

The answer's year, metric, units and arithmetic were independently reviewed
against the **bound test corpus**. These are not independently verified SEC
facts. The retained response has retrieval source/score pairs, but no exact
chunk IDs, passage text or generation prompt; exact retrieved-passage attribution
and answer-to-actual-context grounding remain unestablished.

The sample recorded one parent Invoke, five inner calls and three model
inferences, with no recorded retry or extra request. **USD 0.00625386 is sample
model accounting**, not total task, infrastructure or AWS invoice cost. The
retained reservation is not an enforceable billing cap and was not released.

This was one isolated request, not a benchmark or production release. Earlier
ordinary-function observations describe older builds; they are not evidence
that this branch was rolled out to production. No current public endpoint or
production configuration was checked during this documentation update.

## Local Setup

The current offline CI uses Python **3.13.12** for development regressions.
The deployed smoke artifact uses Python **3.11** and a separately reviewed Linux
dependency closure. `requirements.txt` describes the development environment;
it is not a recipe for reproducing that deployed artifact.

From a checkout, create the virtual environment:

```bash
python -m venv .venv
```

Then activate it and install dependencies using the block for your platform.
The activated `python` installs into `.venv`.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**Linux/macOS (bash):**

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

With `.venv` activated, use
[`.env.example`](.env.example) as the configuration template. Set the region,
model and S3 index/metadata keys for your own authorized environment. Keep real
credentials outside Git. `COPILOT_ROUTER_PROVIDER=haiku` preserves the default;
Jev opt-in additionally requires `TYPESAFE_API_KEY` as described above.
`COPILOT_CW_REQUEST_LOG=false` disables the optional custom request log.

For an authorized AWS-backed local session:

```bash
uvicorn app.main:app --reload --port 8000
```

QA, summarization and indexing use AWS services and may incur charges. They are
not offline demos. This README does not authorize running retained smoke or
deployment commands; their one-use permissions are consumed.

### Offline checks

```bash
python -B -m pytest tests/ -m "not llm and not integration" -k "not test_accepted_population_regression" -q
```

This is the guarded regression selection used by offline CI. The root
`conftest.py` and `tests/offline_guard.py` install fake test credentials, disable
dotenv loading and block outbound service traffic. Live tests require explicit
opt-in and separate authorization. Do not run billable checks as a substitute
for offline tests.

## API Usage

These examples address the local server:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What was JPMorgan net revenue in FY2025?"}'

curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize Goldman Sachs key risks in 2025"}'
```

`/ask` returns the selected task, router confidence, agent result, timings and
trace ID. Ordinary routing can fall back to QA; the isolated smoke instead
stops on routing errors or fallback. An ordinary empty retrieval or abstention
can return HTTP 200, so HTTP status alone does not establish answer success.
Infrastructure/model failures use classified error responses.

`/evaluate` is disabled by default. Enabling it requires both
`ENABLE_EVALUATE_ENDPOINT=true` and a non-empty `EVALUATE_ENDPOINT_TOKEN`, checked
through `X-Evaluate-Token`. `/ask` and `/summarize` do not provide authentication,
and the app permits CORS from any origin; public exposure needs separate review.

## Evaluation and CI

The [evaluation guide](eval/README.md) describes the 34-case harness, label-based
gate populations, historical results and report-only retrieval metrics. Archived
evaluations and exploratory routing experiments have their own scopes; they do
not establish held-out Jev qualification or broad answer quality.

[GitHub Actions](.github/workflows/eval-ci.yml) currently has two offline jobs:
synthetic packaging-contract checks, and guarded lint/regressions plus a
synthetic comparison smoke. It does **not** automatically invoke models, run the
live evaluation gate or deploy Lambda resources. Live evaluation remains a
separate, explicitly authorized operation.

## Observability

The ordinary API emits structured `request.timing` records with trace IDs, stage
latencies, model usage, router outcomes and classified failures. Query text is
excluded from this timing record; its shortened digest is pseudonymous, not
anonymous. The optional custom CloudWatch request log is enabled by default.

The isolated smoke retains bounded private responses and request/accounting
records. Its Tail/REPORT measurements are same-response, unauthenticated
telemetry, not a complete execution log, process-tree audit or latency baseline.

## Data Sources and Limitations

The bound corpus covers JPMorgan Chase, Goldman Sachs, Bank of America,
BlackRock and Visa. Mastercard is not covered. The
[Visa migration runbook](docs/runbooks/visa-source-migration.md) records the
historical metadata-source rename; no new migration or cleanup is implied.

- Retrieval searches a shared index without company filtering.
- Summarization uses direct generation and is not grounded in retrieved filings.
- Source citations do not by themselves validate every answer claim.
- Index structure and metadata row consistency do not prove semantic
  vector-to-passage alignment.
- The isolated smoke and two-query Jev application test have distinct scopes;
  neither establishes general Lambda compatibility or production rollout.
- Lambda packaging needs target-specific, verified wheels. The offline
  `scripts/package_lambda.ps1` wrapper requires explicit target/lock/allocation
  inputs; it does not download dependencies or deploy. Development requirements
  retain different FAISS/NumPy pins from the accepted smoke artifact.

## Project Structure

```text
app/main.py                     FastAPI endpoints
app/lambda_handler.py           Mangum adapter for the ordinary API
app/rag_smoke_handler.py         Isolated, opt-in smoke entry
app/agents/                     Routing, QA and summarization
app/services/                   Retrieval, generation, indexing and smoke controls
eval/                           Evaluation harness, metrics and archived results
experiments/                    Isolated routing and qualification tooling
tests/                          Guarded offline tests and synthetic fixtures
scripts/                        Packaging, preflight and gated operational tools
docs/experiments/                Design, acceptance contracts and completion note
docs/runbooks/                   Operational history and procedures
```
