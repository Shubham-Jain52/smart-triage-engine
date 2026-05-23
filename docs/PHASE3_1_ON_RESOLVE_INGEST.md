# Phase 3.1 — On-Resolve Re-Ingest

Keep Pinecone fresh after the Phase 5 cold start. When a Jira issue is **resolved**, upsert it into Pinecone so future RAG retrieval (Phase 2) can find that fix.

**Ingest only on resolve** — open tickets and live triage POSTs do **not** write to Pinecone.

## Prerequisites

1. Phase 5 complete: Pinecone index exists and initial backfill ran ([PHASE5_SETUP.md](PHASE5_SETUP.md)).
2. Jira credentials in `.env`: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`.
3. `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` set.

## Enable

In `.env`:

```bash
INGEST_ON_RESOLVE_ENABLED=true
INGEST_ON_RESOLVE_REQUIRE_RESOLUTION=true   # skip if no usable resolution comment
INGEST_ON_RESOLVE_POLL_MINUTES=15            # poll script lookback
INGEST_ON_RESOLVE_POLL_INTERVAL_SECONDS=300  # daemon mode interval
```

Restart the API if it is already running.

## Trigger A — Jira Automation webhook (primary)

1. In Jira: **Project settings → Automation** (or global automation).
2. **Trigger:** Issue transitioned → status is one of `Resolved`, `Done`, `Closed`.
3. **Action:** Send web request
   - **URL:** `http://<triage-host>:8000/api/v1/ingest/resolved`
   - **Method:** POST
   - **Content-Type:** application/json
   - **Body:**

```json
{
  "ticket_id": "{{issue.key}}"
}
```

4. If `WEBHOOK_INGEST_API_KEY` is set, add header `X-API-Key: <your-key>`.

**Response (200):**

```json
{
  "ticket_id": "PROJ-42",
  "status": "ingested",
  "message": "upserted 1 vector(s)"
}
```

`status` may also be `skipped` (disabled flag, not resolved, no resolution text) or `failed` (Jira/Pinecone error). Upsert is **idempotent** by `ticket_id` — safe to retry.

For local dev without a public URL, use Trigger B or expose the API via ngrok/cloud tunnel.

## Trigger B — Poll script (fallback)

Catches missed webhooks or environments without Jira Automation.

**One-shot (cron):**

```bash
PYTHONPATH=. python scripts/poll_resolved_ingest.py --once
```

Example crontab (every 5 minutes):

```cron
*/5 * * * * cd /path/to/ticket_routing_agent && PYTHONPATH=. .venv/bin/python scripts/poll_resolved_ingest.py --once >> /var/log/resolve-ingest.log 2>&1
```

**Daemon loop:**

```bash
PYTHONPATH=. python scripts/poll_resolved_ingest.py
```

**Dry run:**

```bash
PYTHONPATH=. python scripts/poll_resolved_ingest.py --once --dry-run
```

The poll script JQL: issues in your project resolved within the last `INGEST_ON_RESOLVE_POLL_MINUTES` (or `--since-minutes` override).

## What gets stored

Same schema as Phase 5:

| Field | Source |
|-------|--------|
| Vector id | Jira issue key |
| Embedding | `title` + `description` (cleaned) |
| Metadata | `ticket_id`, `title`, `description`, `resolution_text`, `team`, `resolved_at` |

Resolution text comes from the last comment matching resolution keywords, or the final comment ([`JiraClient._extract_resolution_text`](../src/integrations/jira/client.py)).

## Skip rules

Ingest is skipped when:

- `INGEST_ON_RESOLVE_ENABLED=false`
- Issue status is not `Resolved`, `Done`, or `Closed`
- Both title and description are empty
- `INGEST_ON_RESOLVE_REQUIRE_RESOLUTION=true` and resolution text is missing or only a status name

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `skipped` — feature disabled | Set `INGEST_ON_RESOLVE_ENABLED=true` |
| `skipped` — no resolution | Add a resolution comment in Jira or set `INGEST_ON_RESOLVE_REQUIRE_RESOLUTION=false` |
| `failed` — Jira | Verify `JIRA_*` credentials and issue key |
| `failed` — Pinecone | Verify `PINECONE_API_KEY`, index name, dimension matches embedding model |
| Webhook never fires | Confirm automation rule scope, transition, and API reachability |
| Duplicate upserts | Expected and safe; Pinecone upsert by id is idempotent |

## Relationship to other phases

| Phase | When | Action |
|-------|------|--------|
| **5** | One-time setup | Batch backfill resolved history |
| **3.1** | Each resolve | Incremental upsert one ticket |
| **2** | Each new ticket triage | Query Pinecone (read only) |
| **3** | Each new ticket | Triage + Jira comment (separate from 3.1) |

Phase 3 (issue-created worker) and Phase 3.1 share Jira credentials but run independently.

## API reference

**POST** `/api/v1/ingest/resolved`

- Auth: optional `X-API-Key` when `WEBHOOK_INGEST_API_KEY` is set
- Body: `{ "ticket_id": "PROJ-42" }`
- Sync response; single-ticket embed is fast enough for v1

See [TRD.md](TRD.md) §5.5 for technical details.
