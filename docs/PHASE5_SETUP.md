# Phase 5: Pinecone cold-start setup

One vector per ticket. **No chunking** in v1.

## Prerequisites

- Python 3.10–3.12, project venv with `pip install -r requirements.txt`
- Pinecone account (BYOK API key)
- **Jira optional** — use bundled dummy CSV for local dev (default)

## 1. Configure `.env`

```bash
cp .env.example .env
```

### Minimum (dummy data — no Jira)

| Variable | Example |
|----------|---------|
| `PINECONE_API_KEY` | `pc-...` |
| `PINECONE_INDEX_NAME` | `ticket-routing` |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` (384 dims) |
| `INGEST_SOURCE` | `dummy` |

Bundled sample data: [`src/data/historical_tickets.csv`](../src/data/historical_tickets.csv) (12 IT-style tickets).

### When you have Jira (switch later)

Set `INGEST_SOURCE=jira` and configure:

| Variable | Example |
|----------|---------|
| `JIRA_BASE_URL` | `https://your-site.atlassian.net` |
| `JIRA_EMAIL` | your email |
| `JIRA_API_TOKEN` | token |
| `JIRA_PROJECT_KEY` | `PROJ` |

## 2. Create Pinecone index (once)

```bash
source .venv/bin/activate
PYTHONPATH=. python scripts/setup_pinecone_index.py
```

Creates a **serverless** index with dimension **384** if it does not exist.

## 3. Ingest historical tickets

**Dummy / CSV (default — no Jira):**

```bash
PYTHONPATH=. python scripts/ingest.py
# same as:
PYTHONPATH=. python scripts/ingest.py --source dummy
```

Custom CSV (same columns as bundled file):

```bash
PYTHONPATH=. python scripts/ingest.py --source csv --csv-path path/to/your_tickets.csv
```

**Real Jira (when ready):**

```bash
PYTHONPATH=. python scripts/ingest.py --source jira
```

Dry run (embed only, no Pinecone writes):

```bash
PYTHONPATH=. python scripts/ingest.py --dry-run
```

### CSV columns

`ticket_id`, `title`, `description`, `resolution_text`, `team`, `resolved_at`

## 4. Validate retrieval

```bash
PYTHONPATH=. python scripts/pinecone_smoke_query.py "VPN disconnects after login"
```

Expect top matches such as `DEMO-101` with VPN-related `resolution_text`.

## Pipeline summary

```text
dummy: historical_tickets.csv → clean → embed(title+description) → Pinecone upsert
jira:  Jira JQL (resolved, 12m) → same pipeline
Metadata: ticket_id, title, description, resolution_text, team, resolved_at
```

## Next step

Enable Phase 2 (`RAG_ENABLED=true`) after ingest succeeds. Phase 2 will expose **problem** and **resolution** Mermaid flowcharts on triage GET (see [TRD.md](TRD.md) §4), not a primary list of similar ticket IDs for agents.
