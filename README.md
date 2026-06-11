# Financial Research Multi-Agent Copilot

A production-grade agentic AI system built on AWS that answers questions
and generates summaries from FY2025 SEC 10-K filings using a router-based
multi-agent architecture.

**Deployment:** Live on AWS Lambda (endpoint available on request)

---

## What This Demonstrates

- **Multi-agent orchestration** — RouterAgent classifies intent and dispatches to specialized agents
- **Manual RAG pipeline** — PDF extraction → chunking → Titan Embeddings V2 → FAISS vector search → Claude generation, all via pure boto3
- **Production CI/CD** — 5-job GitHub Actions pipeline with an LLM-as-Judge eval gate enforcing 80% quality threshold
- **Serverless deployment** — FastAPI + Mangum on AWS Lambda with Function URL
- **Observability** — UUID trace_id threaded through every layer, structured JSON logs queryable in CloudWatch Logs Insights

---

## Architecture

```
User Query
↓
FastAPI (/ask or /summarize)          ← Mangum ASGI adapter on AWS Lambda
↓
CopilotOrchestrator
↓
RouterAgent (Claude Haiku 4.5)        ← classifies: "qa" or "summarize"
↓                    ↓
QAAgent              SummarizerAgent
↓
retriever.py                          ← FAISS similarity search
↓
bedrock_client.py                     ← Claude Haiku 4.5 via Converse API
↓
Pydantic validated response + trace_id
```

**RAG Pipeline (one-time indexing):**

```
5 x FY2025 SEC 10-K PDFs (S3)
↓ PyMuPDF extraction
↓ 500-word chunks
↓ Titan Embeddings V2 (1024 dims)
↓ FAISS IndexFlatIP
→ 2,220 vectors stored on S3
```

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Claude Haiku 4.5 (main), Claude Sonnet 4.6 (eval judge) |
| Embeddings | Amazon Titan Embeddings V2 |
| Vector store | FAISS IndexFlatIP (manual, $0/month) |
| API framework | FastAPI + Mangum |
| Deployment | AWS Lambda + Function URL |
| Storage | Amazon S3 |
| LLM API | Amazon Bedrock (pure boto3, no wrappers) |
| CI/CD | GitHub Actions (5-job pipeline) |
| Eval | Custom LLM-as-Judge (RAGAS-inspired) |
| Linting | Ruff |

**Hard constraints (no exceptions):**
- Pure boto3 for all Bedrock calls — no LangChain, no Anthropic SDK, no OpenAI SDK
- No Docker, no provisioned concurrency, no managed vector stores
- requirements.txt only — no pyproject.toml

---

## Eval Results

Evaluated against 20 queries across 5 categories using Claude Sonnet 4.6 as judge:

| Metric | Score | Threshold |
|---|---|---|
| Context Relevance | 80% | 80% ✅ |
| Faithfulness | 90% | 80% ✅ |
| Mean Context Relevance | 3.8 / 5 | — |
| Mean Faithfulness | 4.8 / 5 | — |

Eval gate runs automatically on every push to main via GitHub Actions.

---

## CI/CD Pipeline

```
lint → unit-tests → integration-tests → eval-gate → deploy-ready
```

- **lint** — Ruff checks app/, eval/, tests/
- **unit-tests** — pytest, no AWS calls
- **integration-tests** — live uvicorn, /health + /ask smoke test
- **eval-gate** — 20-query LLM-as-Judge eval, fails build if below 80%
- **deploy-ready** — confirms all gates passed

---

## API Usage

**Health check:**
```bash
curl https://<lambda-url>.lambda-url.us-east-1.on.aws/health
```

**Ask a question (RAG):**
```bash
curl -X POST https://<lambda-url>.lambda-url.us-east-1.on.aws/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What was JPMorgan net revenue in FY2025?"}'
```

**Summarize:**
```bash
curl -X POST https://<lambda-url>.lambda-url.us-east-1.on.aws/summarize \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize Goldman Sachs key risks in 2025"}'
```

**Example response:**
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

---

## Data Sources

Five FY2025 SEC 10-K filings stored in S3:

- JPMorgan Chase
- Goldman Sachs
- Bank of America
- BlackRock
- Mastercard

---

## Known Limitations

- **Mastercard FAISS retrieval** — cross-company vector confusion; Mastercard queries occasionally return JPMorgan/Goldman chunks due to overlapping financial terminology in the shared index
- **Summarizer context** — SummarizerAgent makes direct Converse API calls without RAG retrieval; it does not ground responses in the 10-K documents

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

---

## Project Structure

```
app/
├── main.py                  ← FastAPI app + CloudWatch logging
├── lambda_handler.py        ← Mangum ASGI adapter for Lambda
├── agents/
│   ├── orchestrator.py      ← CopilotOrchestrator
│   ├── router.py            ← RouterAgent (intent classification)
│   ├── qa_agent.py          ← QAAgent (RAG-grounded answers)
│   └── summarizer_agent.py  ← SummarizerAgent
└── services/
    ├── build_index.py       ← One-time PDF → FAISS indexing pipeline
    ├── retriever.py         ← FAISS similarity search
    └── bedrock_client.py    ← RAG generation via Bedrock

eval/
├── llm_judge.py             ← LLM-as-Judge evaluation pipeline
├── eval_queries.py          ← 20 test queries + boundary cases
└── test_llm_judge.py        ← pytest wrapper for CI eval gate

.github/workflows/
└── eval-ci.yml              ← 5-job CI/CD pipeline
```

---

*Built as a portfolio project demonstrating production agentic AI engineering on AWS.*
