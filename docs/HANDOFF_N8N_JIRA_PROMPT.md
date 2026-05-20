# Handoff prompt — build n8n + Jira integration

Copy everything inside the fenced block below into a **new Cursor chat** (Agent mode) to implement the automation. The triage microservice in this repo is already built; do not rewrite it unless a bug is found.

---

```
## Goal

Build an **n8n integration** that connects **Jira Cloud** (or Jira Server if specified) to the existing **Smart Triage Engine** FastAPI microservice in this repository, so that:

1. When a Jira issue is created (or meets a JQL rule), n8n sends it to the triage service.
2. When triage completes, n8n updates the Jira issue (assignee, component, and/or labels) based on `assigned_team` and `requires_hitl`.

The microservice is **ready** — implement orchestration only (n8n workflows + docs + optional mapping config). Do not change ML logic unless tests fail.

## Repository context

- **Project path:** ticket_routing_agent (Smart Triage Engine)
- **Stack:** FastAPI, BackgroundTasks, Hugging Face zero-shot classifier, in-memory cache
- **Python:** 3.10–3.12 recommended; see `.python-version`

### Triage API (already implemented)

**Base URL (local):** `http://127.0.0.1:8000`

| Action | Method | Path | Notes |
|--------|--------|------|-------|
| Health | GET | `/health` | |
| Submit ticket | POST | `/api/v1/triage` | Returns **202** immediately |
| Get result | GET | `/api/v1/triage/{ticket_id}` | Poll until `status` is `completed` or `failed` |

**POST body (JSON):**
```json
{
  "ticket_id": "PROJ-42",
  "title": "summary text",
  "description": "description text",
  "created_at": "2026-05-20T10:00:00.000Z"
}
```

Use Jira **issue key** as `ticket_id` (e.g. `PROJ-42`).

**GET response when done:**
```json
{
  "ticket_id": "PROJ-42",
  "assigned_team": "DevOps",
  "confidence_score": 0.91,
  "requires_hitl": false,
  "status": "completed"
}
```

**Optional inbound auth:** If `WEBHOOK_INGEST_API_KEY` is set in triage `.env`, POST must include header `X-API-Key: <value>`.

**Optional outbound callback:** If `TRIAGE_CALLBACK_URL` is set on the triage service, it POSTs the same JSON as GET when triage finishes (optional header `X-API-Key` via `TRIAGE_CALLBACK_API_KEY`). n8n can use a Webhook node as Pattern B instead of polling.

**Idempotency:** Re-POSTing the same `ticket_id` while `processing` or after `completed`/`failed` does not enqueue duplicate work.

**Env vars (triage `.env`):** See `.env.example` — especially `CANDIDATE_LABELS`, `HITL_THRESHOLD`, `WEBHOOK_INGEST_API_KEY`, `TRIAGE_CALLBACK_URL`.

### Key source files (read before building)

- `src/api/v1/routes.py` — POST/GET triage
- `src/api/v1/schemas.py` — request/response shapes
- `src/services/triage_service.py` — background processing + callback invoke
- `src/services/callback_service.py` — outbound POST to TRIAGE_CALLBACK_URL
- `src/config.py` — all settings
- `docs/INTEGRATION_N8N_JIRA.md` — integration guide (extend if needed)
- `tests/test_api.py` — API behavior tests

### ML / labels

- Runtime: Hugging Face zero-shot (`CANDIDATE_LABELS` env, comma-separated team names).
- Default labels example: `IT Support,DevOps,HR,Security,Hardware`
- n8n must map `assigned_team` strings to Jira-specific fields (assignee accountId, component name, labels) via a lookup table — Jira has no universal "team" field.

## What to deliver

1. **n8n workflow export(s)** under `integrations/n8n/`:
   - **Pattern A (preferred for first demo):** Jira trigger → POST triage → wait/loop → GET triage → Switch on `assigned_team` → Jira update; handle `requires_hitl` (label or transition).
   - **Pattern B (optional):** Second workflow: Webhook receives triage callback → Jira update; document setting `TRIAGE_CALLBACK_URL` to n8n webhook URL.

2. **`integrations/n8n/jira-team-mapping.example.json`** — example mapping:
   ```json
   {
     "IT Support": { "component": "IT Support", "assigneeAccountId": null, "labels": ["auto-routed"] },
     "DevOps": { "component": "DevOps", "labels": ["auto-routed"] },
     "hitl": { "labels": ["hitl", "needs-review"] }
   }
   ```

3. **`integrations/n8n/README.md`** — how to import workflows, configure Jira credentials in n8n, set ngrok for local dev, and test end-to-end.

4. **Update `docs/INTEGRATION_N8N_JIRA.md`** if the workflow structure differs from the doc.

5. **Do NOT** edit the plan file at `.cursor/plans/`.

## Jira + n8n assumptions (adjust if user specifies otherwise)

- **Jira Cloud** (Atlassian site URL + API token).
- **Project:** user will provide project key; use placeholders in workflow.
- **Trigger:** n8n Jira Trigger "issue created" OR document Jira Automation → n8n Webhook.
- **Update actions:** set **labels** (`team-<name>`, `hitl` when needed) and/or **components**; assignee only if mapping provides accountId.

## Local test procedure

1. `cp .env.example .env` — set `CANDIDATE_LABELS`; leave API keys empty for local test unless desired.
2. `uvicorn src.main:app --reload`
3. Run n8n; import workflow; configure Jira credential.
4. Create Jira issue → verify n8n execution → `curl http://127.0.0.1:8000/api/v1/triage/ISSUE-KEY` shows `completed`.
5. Verify Jira issue has expected label/component/assignee.

## Out of scope for this task

- Rewriting the triage microservice or switching to sklearn
- Redis/SQLite persistence
- ServiceNow / Zendesk (Jira only unless time permits a second doc section)
- Production hardening (rate limits, DLQ) unless trivial

## Success criteria

- Documented steps allow a developer to run triage + n8n + Jira and see automatic routing on a new issue.
- Workflow JSON is importable in n8n.
- Team mapping is configurable without editing Python code.
```

---

## Quick answer: is the microservice ready?

**Yes**, for integration: ingest, async classification, GET results, optional callback, optional ingest API key, and idempotency are implemented and tested (`pytest tests/`). What remains is **external orchestration** (n8n + Jira), which this handoff describes.
