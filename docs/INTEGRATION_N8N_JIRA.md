# Jira + n8n integration guide

This document describes how to connect **Jira** to the **Smart Triage Engine** microservice using **n8n** as the orchestration layer. The microservice classifies tickets; n8n applies results back to Jira.

## Microservice readiness (Phase 1)

The triage API is **ready for integration**. You do not need to change the service to demo Jira routing.

| Capability | Endpoint / config | Status |
|------------|-------------------|--------|
| Accept ticket | `POST /api/v1/triage` | Ready |
| Poll result | `GET /api/v1/triage/{ticket_id}` | Ready |
| Push result | `TRIAGE_CALLBACK_URL` env | Ready |
| Inbound API key | `WEBHOOK_INGEST_API_KEY` + `X-API-Key` | Optional |
| Idempotent ingest | Same `ticket_id` while processing/terminal | Ready |
| HITL flag | `requires_hitl` when confidence &lt; `HITL_THRESHOLD` | Ready |

**Not in scope of the microservice:** updating Jira issues (assignee, components, transitions). That is **n8n’s job** (or Jira Automation).

**Limitations for production demos:** in-memory cache (lost on restart); first ML run downloads model weights; zero-shot latency may exceed PRD 200ms on CPU-only hosts.

---

## Architecture

```text
┌─────────────┐     issue created      ┌──────┐    POST /triage     ┌──────────────────┐
│ Jira Cloud  │ ─────────────────────► │ n8n  │ ──────────────────► │ Triage service   │
│ (or Server) │                        │      │ ◄── GET or webhook ── │ (FastAPI :8000)  │
└─────────────┘                        │      │                       └──────────────────┘
       ▲                               │      │
       │         Jira REST API          │      │
       └────────────────────────────────┘      │
              assign / label / transition       │
```

**Recommended `ticket_id`:** Jira **issue key** (e.g. `PROJ-42`) so GET/callback and Jira updates use the same id.

---

## API contract (for n8n HTTP nodes)

### Ingest — `POST /api/v1/triage`

- **URL:** `http://<triage-host>:8000/api/v1/triage`
- **Headers:** `Content-Type: application/json`; optional `X-API-Key: <WEBHOOK_INGEST_API_KEY>`
- **Body:**

```json
{
  "ticket_id": "PROJ-42",
  "title": "VPN disconnects after login",
  "description": "User reports remote access drops every 10 minutes.",
  "created_at": "2026-05-20T10:00:00Z"
}
```

- **Response:** `202` — `{ "ticket_id": "PROJ-42", "status": "processing" }`

### Result — `GET /api/v1/triage/{ticket_id}`

- **Response when done:**

```json
{
  "ticket_id": "PROJ-42",
  "assigned_team": "DevOps",
  "confidence_score": 0.91,
  "requires_hitl": false,
  "status": "completed"
}
```

- **`status` values:** `processing` | `completed` | `failed`
- **`failed`:** `assigned_team` is `unassigned`, `requires_hitl` is `true`

### Optional callback — triage service → n8n

Set in triage `.env`:

```env
TRIAGE_CALLBACK_URL=https://<your-n8n>/webhook/triage-result
TRIAGE_CALLBACK_API_KEY=<optional-shared-secret>
```

The service **POSTs** the same JSON shape as GET when triage finishes. Use an n8n **Webhook** node (POST) as the second workflow’s trigger.

---

## Jira field mapping

| Triage field | Typical Jira source |
|--------------|-------------------|
| `ticket_id` | `{{ $json.key }}` (issue key) |
| `title` | `fields.summary` |
| `description` | `fields.description` (plain text or ADF → extract text in n8n) |
| `created_at` | `fields.created` (ISO 8601) |

| Triage result | Typical Jira action (configure per project) |
|---------------|---------------------------------------------|
| `assigned_team` | Set **Component**, **Assignee** (mapped user), or **label** `team-devops` |
| `requires_hitl: true` | Add label `hitl`, transition to “Needs review”, or clear assignee |
| `requires_hitl: false` | Auto-assign per team lookup table |

`CANDIDATE_LABELS` in the triage `.env` must match the label names you expect (e.g. `IT Support,DevOps,HR,Security,Hardware`).

---

## Integration patterns

### Pattern A — Poll (simpler to debug)

Single n8n workflow:

1. **Trigger:** Jira Trigger (issue created) *or* Webhook (from Jira Automation “Send web request”).
2. **HTTP Request:** POST triage ingest (map fields above).
3. **Wait** 2–5 s (adjust for cold ML).
4. **HTTP Request:** GET triage result.
5. **IF** `status === "processing"` → loop back to Wait (cap iterations, e.g. 30).
6. **Switch** on `assigned_team` → **Jira** node: Update issue (component/assignee/labels).
7. **IF** `requires_hitl` → add label or transition.

### Pattern B — Callback (fewer polls)

**Workflow 1 — Ingest**

1. Jira trigger → POST `/api/v1/triage` → end.

**Workflow 2 — Apply**

1. Webhook URL from n8n (`/webhook/triage-result`) → set `TRIAGE_CALLBACK_URL` on triage service.
2. Webhook receives JSON body → Jira update nodes.

**Networking:** Jira Cloud and n8n cloud must reach your triage host. For local triage, use **ngrok** (or run n8n + triage on the same Docker network).

---

## Jira trigger options

| Method | When to use |
|--------|-------------|
| **n8n Jira Trigger** | n8n has Jira credentials; “Issue created” events |
| **Jira Automation** → Webhook to n8n | No n8n trigger license issues; rule on “Issue created” |
| **Schedule + Jira search** | Polling JQL `created >= -5m` (not real-time) |

**Jira Cloud credentials (n8n):** email + [API token](https://id.atlassian.com/manage-profile/security/api-tokens); site URL `https://<site>.atlassian.net`.

---

## Local development checklist

1. Start triage: `uvicorn src.main:app --reload` (port 8000).
2. Start n8n (Docker or desktop).
3. Expose URLs if needed: `ngrok http 8000`, `ngrok http 5678`.
4. Align `CANDIDATE_LABELS` with your Jira mapping table.
5. Create one test issue in Jira; verify n8n execution log and `GET /api/v1/triage/PROJ-XX`.

---

## Deliverables for the n8n build (next task)

Planned artifacts (not yet in repo):

- `integrations/n8n/workflow-jira-triage-poll.json` — exportable n8n workflow (Pattern A)
- `integrations/n8n/workflow-jira-triage-callback.json` — optional Pattern B
- `integrations/n8n/jira-team-mapping.example.json` — `assigned_team` → Jira assignee accountId / component name

See [HANDOFF_N8N_JIRA_PROMPT.md](HANDOFF_N8N_JIRA_PROMPT.md) for a copy-paste prompt to continue in a new chat.

---

## Related docs

- [README.md](../README.md) — run triage service, env vars
- [TRD.md](TRD.md) — architecture and implementation status
- [PRD.md](PRD.md) — product goals
