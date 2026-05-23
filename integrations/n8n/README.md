# n8n workflows (optional)

**Primary orchestration:** Python Jira worker — see [docs/PHASE3_SETUP.md](../../docs/PHASE3_SETUP.md).

This folder holds shared configuration used by the Python worker:

- **`jira-team-mapping.example.json`** — map `assigned_team` → Jira component, assignee accountId, labels; includes `hitl` entry.

Copy to your own mapping file and set `JIRA_TEAM_MAPPING_PATH` in `.env`.

## Optional n8n path

Importable n8n workflow JSON is **not yet included**. Use [docs/INTEGRATION_N8N_JIRA.md](../../docs/INTEGRATION_N8N_JIRA.md) or [docs/HANDOFF_N8N_JIRA_PROMPT.md](../../docs/HANDOFF_N8N_JIRA_PROMPT.md) if you prefer no-code orchestration instead of the Python worker.
