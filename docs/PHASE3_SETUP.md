# Phase 3 — Jira Triage Worker Setup

Connect Jira to the triage API so agents see **routing + Mermaid flowcharts** on each new issue.

## Architecture

```text
Jira issue created
    → Jira Automation OR poll script
    → run_jira_worker.py
    → POST /api/v1/triage → poll GET
    → Update assignee/component/labels
    → Add comment (problem + resolution flowcharts)
```

## Prerequisites

1. Triage API running: `uvicorn src.main:app --reload`
2. Phase 2 optional but recommended (`RAG_ENABLED=true` for flowcharts)
3. Jira Cloud credentials in `.env`
4. Copy and edit team mapping: `integrations/n8n/jira-team-mapping.example.json`

## Configure `.env`

```bash
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_EMAIL=you@company.com
JIRA_API_TOKEN=...
JIRA_PROJECT_KEY=PROJ

TRIAGE_API_URL=http://127.0.0.1:8000
JIRA_TEAM_MAPPING_PATH=integrations/n8n/jira-team-mapping.example.json
JIRA_WORKER_PROCESSED_LABEL=auto-triaged
INCLUDE_TICKET_IDS_IN_COMMENT=false
```

If triage API uses inbound auth:

```bash
WEBHOOK_INGEST_API_KEY=your-secret
```

## Team mapping

Edit `JIRA_TEAM_MAPPING_PATH` JSON — keys must match `CANDIDATE_LABELS` plus a `hitl` entry:

```json
{
  "DevOps": {
    "component": "DevOps",
    "assigneeAccountId": "712020:...",
    "labels": ["auto-routed"]
  },
  "hitl": {
    "labels": ["hitl", "needs-review"]
  }
}
```

When `requires_hitl: true`, assignee is **not** set; HITL labels are applied instead.

## Trigger A — Jira Automation (recommended)

1. **Trigger:** Issue created (your project)
2. **Action:** Send web request
   - URL: `http://<worker-host>/` — run worker on issue key via a small HTTP wrapper, **or** run worker on a schedule and use Trigger B

For a direct single-issue run from Automation, invoke the worker script on a server that can reach both Jira and the triage API:

```bash
PYTHONPATH=. python scripts/run_jira_worker.py --issue {{issue.key}}
```

Use Jira Automation **incoming webhook** + cron on your side, or schedule poll (Trigger B).

## Trigger B — Poll script (fallback)

```bash
PYTHONPATH=. python scripts/run_jira_worker.py --once
```

Cron example (every 5 minutes):

```cron
*/5 * * * * cd /path/to/ticket_routing_agent && PYTHONPATH=. .venv/bin/python scripts/run_jira_worker.py --once
```

Poll JQL: issues created in the last `JIRA_WORKER_POLL_MINUTES` without label `JIRA_WORKER_PROCESSED_LABEL`.

## Manual test

```bash
# Terminal 1
uvicorn src.main:app --reload

# Terminal 2 — dry run
PYTHONPATH=. python scripts/run_jira_worker.py --issue PROJ-42 --dry-run

# Live run
PYTHONPATH=. python scripts/run_jira_worker.py --issue PROJ-42
```

Verify in Jira: labels/component updated, comment contains Mermaid code blocks.

## Comment format

```
[Auto-Triage] Team: DevOps | Confidence: 0.91 | HITL: false
Renew certificate for VPN issues.

Current problem (flowchart)
<mermaid code block>

How similar issues were resolved (flowchart)
<mermaid code block>
```

`similar_past_tickets` are **not** shown unless `INCLUDE_TICKET_IDS_IN_COMMENT=true`.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Worker can't reach triage | `TRIAGE_API_URL`, firewall, API running |
| 401 on triage POST | `WEBHOOK_INGEST_API_KEY` + worker uses same key via env |
| No comment | Triage `status=failed` skips Jira write-back; check API logs |
| Wrong team labels | `CANDIDATE_LABELS` vs mapping JSON keys |
| Re-processing same issue | `auto-triaged` label prevents duplicate runs |

## Related

- [PHASE2_SETUP.md](PHASE2_SETUP.md) — enable RAG flowcharts
- [PHASE3_1_ON_RESOLVE_INGEST.md](PHASE3_1_ON_RESOLVE_INGEST.md) — keep Pinecone fresh on resolve
- [INTEGRATION_N8N_JIRA.md](INTEGRATION_N8N_JIRA.md) — optional n8n alternative
