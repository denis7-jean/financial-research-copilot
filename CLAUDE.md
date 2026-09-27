# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Financial Research Multi-Agent Copilot

## Stack — Non-Negotiable
- Python 3.11, FastAPI, pure boto3, Pydantic v2, pytest + httpx, Mangum
- `pydantic-ai` is pinned in requirements.txt but is not imported anywhere
- NO LangChain. NO langchain-aws. Not anywhere. Ever.
- ALL Bedrock API calls via pure boto3 only — no wrappers

## AWS Configuration
- Region: us-east-1 (enforce on all boto3 clients)
- S3 bucket: financial-copilot-hl (PDFs at /docs/ prefix)
- FAISS index stored at S3 keys from env: FAISS_INDEX_S3_KEY, FAISS_META_S3_KEY
- Bedrock model: us.anthropic.claude-haiku-4-5-20251001-v1:0
- Embedding model: amazon.titan-embed-text-v2:0 (1024 dimensions)
- Judge model: us.anthropic.claude-sonnet-4-6 (used in eval/llm_judge.py only)

## Architecture — Router-Based Dispatch
User query → RouterAgent → classifies "qa" or "summarize"
→ QAAgent (FAISS retrieval + Claude generation)
OR SummarizerAgent (direct Claude Converse call, NO retrieval)
→ Pydantic validated response → FastAPI return

No ReAct loops. No tool-calling cycles. No observe-reason-act chains.
Plain Pydantic models are used for typed responses and validation — not
for agent execution or LLM calls.

## RAG Pipeline (Manual — No Bedrock Knowledge Bases)
- build_index.py: PDF extraction (PyMuPDF) → chunking → Titan embed → FAISS
- retriever.py: load FAISS from S3 → embed query → similarity search
- bedrock_client.py: retrieve_chunks → build context → Claude Converse API

## Project Structure
```
financial-multi-agent-copilot/
├── app/
│   ├── main.py                    ← FastAPI app, request tracing, /evaluate gate
│   ├── lambda_handler.py          ← Mangum ASGI adapter
│   ├── observability.py           ← request.timing trace (stages, tokens, cold start)
│   ├── agents/
│   │   ├── router.py              ← RouterAgent + RouterDecision
│   │   ├── qa_agent.py            ← QAAgent + QAResponse
│   │   ├── summarizer_agent.py    ← SummarizerAgent + SummaryResponse
│   │   └── orchestrator.py        ← CopilotOrchestrator
│   └── services/
│       ├── build_index.py         ← One-time indexing pipeline
│       ├── retriever.py           ← FAISS retrieval
│       └── bedrock_client.py      ← RAG generation via Claude
├── tests/                         ← offline; conftest.py blocks all AWS network I/O
│   ├── conftest.py                ← fake creds, network guard, FakeBedrock
│   ├── test_router.py
│   ├── test_agents.py
│   ├── test_api.py
│   ├── test_observability.py
│   ├── test_harness.py
│   └── test_eval.py
├── eval/
│   ├── README.md              ← metrics, gates, cost
│   ├── llm_judge.py           ← LLM-as-judge harness (live)
│   ├── metrics.py             ← pure metrics + GATES (single source of thresholds)
│   ├── eval_queries.py        ← 34 labeled cases with verified references
│   ├── test_llm_judge.py      ← CI eval gate (live)
│   └── results/
│       ├── latest.json        ← generated, gitignored
│       └── legacy/            ← archived pre-Phase-0 result
├── .github/workflows/eval-ci.yml
├── .env                           ← Never commit
├── .gitignore
├── requirements.txt
└── README.md
```

## Environment Variables Required
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
S3_BUCKET_NAME=financial-copilot-hl
FAISS_INDEX_S3_KEY=index/financial_index.faiss
FAISS_META_S3_KEY=index/financial_meta.json
JUDGE_MODEL_ID=us.anthropic.claude-sonnet-4-6

# Optional
COPILOT_CW_REQUEST_LOG=true
ENABLE_EVALUATE_ENDPOINT=false
EVALUATE_ENDPOINT_TOKEN=
EVAL_RESULTS_PATH=eval/results/latest.json
EVAL_SLEEP_SECONDS=2
```

## Coding Conventions
- All boto3 clients created with explicit `region_name="us-east-1"`
- All env vars loaded via python-dotenv `load_dotenv()`
- All exceptions caught explicitly — never bare `except:`
- Every service function has a `__main__` block for standalone testing
- Pydantic models defined in same file as the agent that uses them
- No relative imports — use full `app.services.x` and `app.agents.x` paths
- Instrument new stages/model calls via `app.observability` helpers (`stage`,
  `record_converse_usage`, `record_error`); never log query text
- Unit tests must mock Bedrock/S3 (see `tests/conftest.py` FakeBedrock); real
  botocore network calls raise in tests
- Eval thresholds live only in `eval/metrics.py` GATES

## Commands
```bash
# Local run
uvicorn app.main:app --reload --port 8000

# Build index
python -m app.services.build_index

# Test retrieval
python -m app.services.retriever

# Run offline unit tests (what CI unit-tests runs; no AWS calls)
pytest tests/ -m "not llm and not integration" -v

# Run CI eval gate (LIVE, billable)
pytest eval/test_llm_judge.py -m llm -v

# Run LLM-as-judge evaluation (LIVE, billable)
python -m eval.llm_judge
```
