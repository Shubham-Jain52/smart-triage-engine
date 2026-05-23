# Phase 2 — RAG Resolution Engine Setup

Enable Mermaid **problem** and **resolution** flowcharts on triage GET/callback responses.

## Prerequisites

1. **Phase 5 complete** — Pinecone index populated ([PHASE5_SETUP.md](PHASE5_SETUP.md)).
2. **BYOK LLM** — local Ollama (recommended) or OpenAI-compatible API.

## 1. Configure `.env`

```bash
RAG_ENABLED=true
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=ticket-routing
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RAG_TOP_K=3

# Ollama (default)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
FLOWCHART_MAX_NODES=15
```

For OpenAI-compatible APIs instead:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## 2. Start Ollama (local)

```bash
ollama pull llama3.2
ollama serve   # if not already running
```

## 3. Run API and triage a ticket

```bash
uvicorn src.main:app --reload
```

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/triage \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TEST-1",
    "title": "VPN disconnects after login",
    "description": "Remote user loses connection every 10 minutes.",
    "created_at": "2026-05-20T10:00:00Z"
  }'

curl -s http://127.0.0.1:8000/api/v1/triage/TEST-1 | jq
```

Expected fields on `completed`:

- `problem_flowchart_mermaid` — Mermaid `flowchart TD/LR` for current issue structure
- `resolution_flowchart_mermaid` — merged path from similar past fixes
- `rag_resolution_summary` — 1–2 sentence caption
- `similar_past_tickets` — audit list of Pinecone match ids (not for default Jira UI)

## 4. Render Mermaid

Paste diagram text into [mermaid.live](https://mermaid.live) or a Jira Mermaid plugin. Phase 3 worker will post these as fenced blocks in Jira comments.

## Failure behavior

- RAG errors **do not** fail ML routing — classification still completes.
- Empty Pinecone index → problem diagram still generated; resolution diagram may be generic.
- Invalid LLM output → retried once; then RAG fields left empty with warning in logs.

## Architecture

```text
POST /triage → classify (Phase 1)
            → embed + Pinecone query (retriever)
            → LLM problem flowchart
            → LLM resolution flowchart + caption
            → cache + optional callback
```

See [TRD.md](TRD.md) §4 for full spec.
