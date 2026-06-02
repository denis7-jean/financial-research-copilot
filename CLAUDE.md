# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Financial Research Multi-Agent Copilot

## Stack — Non-Negotiable
- Python 3.11, FastAPI, pure boto3, Pydantic AI, pytest + httpx, Mangum
- NO LangChain. NO langchain-aws. Not anywhere. Ever.
- ALL Bedrock API calls via pure boto3 only — no wrappers

## AWS Configuration
- Region: us-east-1 (enforce on all boto3 clients)
- S3 bucket: financial-copilot-hl (PDFs at /docs/ prefix)
- FAISS index stored at S3 keys from env: FAISS_INDEX_S3_KEY, FAISS_META_S3_KEY
- Bedrock model: us.anthropic.claude-haiku-4-5-20251001-v1:0
- Embedding model: amazon.titan-embed-text-v2:0 (1024 dimensions)
- Judge model: anthropic.claude-sonnet-4-6 (used in eval/llm_judge.py only)

## Architecture — Router-Based Dispatch
User query → RouterAgent → classifies "qa" or "summarize"
→ QAAgent (FAISS retrieval + Claude generation)
OR SummarizerAgent (direct Claude Converse call)
→ Pydantic validated response → FastAPI return

No ReAct loops. No tool-calling cycles. No observe-reason-act chains.
Pydantic AI is used exclusively for typed response models and structured
output validation — not for agent execution or LLM calls.

## RAG Pipeline (Manual — No Bedrock Knowledge Bases)
- build_index.py: PDF extraction (PyMuPDF) → chunking → Titan embed → FAISS
- retriever.py: load FAISS from S3 → embed query → similarity search
- bedrock_client.py: retrieve_chunks → build context → Claude Converse API

## Project Structure
```
financial-multi-agent-copilot/
├── app/
│   ├── main.py                    ← FastAPI app, Mangum handler
│   ├── lambda_handler.py          ← Mangum ASGI adapter
│   ├── agents/
│   │   ├── router.py              ← RouterAgent + RouterDecision
│   │   ├── qa_agent.py            ← QAAgent + QAResponse
│   │   ├── summarizer_agent.py    ← SummarizerAgent + SummaryResponse
│   │   └── orchestrator.py        ← CopilotOrchestrator
│   └── services/
│       ├── build_index.py         ← One-time indexing pipeline
│       ├── retriever.py           ← FAISS retrieval
│       └── bedrock_client.py      ← RAG generation via Claude
├── tests/
│   ├── test_router.py
│   ├── test_api.py
│   └── test_eval.py
├── eval/
│   ├── llm_judge.py           ← LLM-as-judge evaluation pipeline
│   ├── eval_queries.py        ← 20 test queries
│   └── results/
│       └── latest.json        ← Scored eval output
├── .github/workflows/ci.yml
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
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
S3_BUCKET_NAME=financial-copilot-hl
FAISS_INDEX_S3_KEY=index/financial_index.faiss
FAISS_META_S3_KEY=index/financial_meta.json
JUDGE_MODEL_ID=anthropic.claude-sonnet-4-5
```

## Coding Conventions
- All boto3 clients created with explicit `region_name="us-east-1"`
- All env vars loaded via python-dotenv `load_dotenv()`
- All exceptions caught explicitly — never bare `except:`
- Every service function has a `__main__` block for standalone testing
- Pydantic models defined in same file as the agent that uses them
- No relative imports — use full `app.services.x` and `app.agents.x` paths

## Commands
```bash
# Local run
uvicorn app.main:app --reload --port 8000

# Build index
python -m app.services.build_index

# Test retrieval
python -m app.services.retriever

# Run tests
pytest tests/ -v --ignore=tests/test_eval.py

# Run eval
pytest tests/test_eval.py -v

# Run LLM-as-judge evaluation
python -m eval.llm_judge
```
