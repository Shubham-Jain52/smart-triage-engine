# Product Requirement Document (PRD)

## 1. Objective & Scope

The **Automated Ticket Routing** product is a **headless, Bring-Your-Own-Key (BYOK)** local application that augments IT ticketing workflows. **Jira** is the primary user interface; agents and requesters never interact with a separate triage UI.

| Phase | Name | Status |
|-------|------|--------|
| **Phase 1** | ML Triage Engine | **Implemented** — webhook ingest, zero-shot routing, HITL, async processing, optional outbound callback |
| **Phase 2** | RAG Resolution Engine | **Implemented** — Pinecone retrieval + Mermaid flowcharts via BYOK LLM |
| **Phase 3** | Jira Orchestration (Python) | **Planned** — poll/webhook worker, assignee update, post flowcharts to Jira |
| **Phase 3.1** | On-Resolve Re-Ingest | **Implemented** — Jira resolve → Pinecone upsert (webhook + poll fallback) |
| **Phase 4** | Packaging & Local Stack | **Planned** — single `docker-compose up`, single `.env` for all services |
| **Phase 5** | Historical Data Ingestion (Cold Start) | **Implemented** — one-time Jira/CSV → Pinecone backfill before live RAG |

**Phase 1 objective:** Intercept incoming IT tickets, classify them with a local ML model, and route to the correct functional team with confidence-based HITL flagging—without mandatory external LLM APIs for classification.

**Expanded product objective (Phases 2–5):** Before live RAG is useful, **backfill Pinecone** with resolved Jira history (Phase 5). After routing, generate **visual resolution aids** (Phase 2): a **problem flowchart** for the current ticket and a **past-resolutions flowchart** synthesized from similar historical fixes—giving teams a mental map instead of a raw list of ticket IDs. Deliver those diagrams **inside Jira** via Python orchestration (Phase 3), with BYOK Pinecone and LLM (e.g. Ollama).

## 2. Core Features

### Phase 1 (Implemented)

* **Webhook Ingestion:** Accept HTTP POST payloads (from n8n, a simulator, or Jira Automation).
* **ML Triage Engine:** Predict team assignment from ticket title and description.
* **Asynchronous Processing:** Return 202 immediately; classify in a background worker.
* **Human-in-the-Loop (HITL):** Flag tickets when confidence is below 80% for manual review.
* **Result Retrieval:** Poll by `ticket_id` or receive an optional HTTP callback.

### Phase 2 — RAG Resolution Engine (Implemented)

* **Historical retrieval (internal):** Query **Pinecone** for top-k similar resolved tickets; use metadata (`resolution_text`, `ticket_id`) as **LLM context only**—not as the primary agent-facing artifact.
* **Problem flowchart:** A **local LLM** (e.g. Ollama) or BYOK API generates a **Mermaid flowchart** of the current issue: symptoms, likely components, decision branches, and escalation paths—so the assignee sees how the problem is structured before acting.
* **Past-resolutions flowchart:** The same pipeline synthesizes a second **Mermaid flowchart** showing how **similar historical tickets** were resolved (merged pattern from top-k matches): typical steps, checks, and fixes—so the team gets a mental map of proven resolution flows rather than reading N separate ticket threads.
* **Enriched triage output:** Expose `problem_flowchart_mermaid`, `resolution_flowchart_mermaid`, and a short optional `rag_resolution_summary` (caption). Keep `similar_past_tickets` in the API for **audit/debug** only; Jira comments emphasize the two diagrams.

### Phase 3 — Workflow Orchestration (Planned)

* **Python Jira worker:** Poll or webhook-triggered service calls the triage API and writes results back to Jira (replaces n8n for this project).
* **Assignee routing:** Update assignee (or component/labels) from `assigned_team` and HITL rules.
* **Zero-UI integration:** Post an **internal Jira comment** containing rendered or fenced **Mermaid** flowcharts (problem + past resolutions)—no standalone triage portal and no bullet-list of “similar tickets” for agents to parse manually.

### Phase 3.1 — On-Resolve Re-Ingest (Implemented)

* **Continuous knowledge refresh:** When a Jira issue moves to a resolved terminal status, upsert it into Pinecone using the same vector schema as Phase 5—so RAG retrieval stays current without re-running full batch ingest.
* **Dual trigger:** Jira Automation **webhook** → `POST /api/v1/ingest/resolved` (primary); **poll script** for cron/fallback when webhooks are unavailable.
* **Skip guards:** Only resolved issues with usable problem text and (optionally) resolution comments are ingested; failures do not affect live triage routing.

### Phase 4 — Packaging (Planned)

* **One-command local stack:** API, ML dependencies, n8n, and optional Ollama/Pinecone clients configured via a **single root `.env`** and **`docker-compose up`**.
* **BYOK:** Customers supply their own Pinecone index/API key and LLM endpoint (Ollama local or cloud API keys); secrets never ship in the image.

### Phase 5 — Historical Data Ingestion (Cold Start Resolution) (Implemented)

* **Objective:** Populate the vector database with **past organizational knowledge** before the live RAG pipeline (Phase 2) is activated—eliminating the empty-index “cold start” where retrieval returns no useful matches.
* **Jira Data Extraction:** A **standalone** ingestion script queries the **Jira REST API** for tickets **resolved in the past 12 months** (configurable window), independent of the FastAPI server.
* **Knowledge Mapping:** For each closed ticket, capture:
  - **Problem:** original **Title** + **Description**
  - **Solution:** final **resolution comment** and/or resolution **status** metadata from Jira
* **Vector Load:** Embed problem text locally and **upsert** into Pinecone with full **metadata** (ticket id, problem text, resolution text, team, resolved date) so Phase 2 retrieval can feed the **resolution flowchart** generator with real past fix steps.

## 3. Success Metrics

### Phase 1

* **Routing accuracy:** ≥ 85% correct team assignments on the validation dataset.
* **Classification latency:** Under 200 ms per ticket for the **classification layer** (steady-state, after model warm-up).
* **Privacy (classification):** 100% of triage classification runs locally without external LLM calls (zero-shot HF model).

### Phase 2

* **Retrieval relevance:** Top-k Pinecone matches are plausibly related on a held-out set (logged for audit via `similar_past_tickets`).
* **Flowchart usefulness:** Problem and resolution Mermaid diagrams are structurally valid, readable in Jira (fenced code block or Mermaid macro), and align with retrieved history—agents report faster orientation vs. text-only summaries.
* **Grounding:** Resolution flowchart steps must trace to retrieved `resolution_text`; no invented ticket IDs in diagram node labels (use generic step names or “Past fix pattern”).
* **End-to-end latency budget:** Documented p95 for RAG path (embedding + Pinecone + dual LLM diagram generation) separate from Phase 1 routing SLA.

### Phase 3–4

* **Integration reliability:** n8n workflow completes Jira update + comment on ≥ 95% of test issues in a staging project.
* **Packaging:** Fresh clone → `cp .env.example .env` → `docker-compose up` → health checks green for API and n8n within documented startup time.
* **Zero-UI:** Agents see routing + flowchart comment only in Jira; no login to a separate triage portal.

### Phase 5

* **Ingestion completeness:** Successfully upload a **batch of historical resolved tickets** (target: 12-month window per project) to Pinecone with **correct metadata** (`ticket_id`, problem text, `resolution_text`, team, `resolved_at`).
* **Retrieval readiness:** After ingest, a sample query from Phase 2 retriever returns ≥ 1 relevant neighbor for typical IT tickets in the same project (smoke test documented in runbook).
* **Operational safety:** Ingest is **idempotent** by `ticket_id` (re-runs upsert/update without duplicate vectors); failures logged per issue without aborting the entire batch.

## 4. User Experience Principles

* **Jira-native:** Create ticket → automation runs → assignee/labels updated → internal comment with **problem + resolution flowcharts**.
* **Diagram-first:** Prefer visual flow over listing similar issue keys; IDs remain in API metadata for support engineers only.
* **Headless API:** All intelligence exposed via REST; orchestration owns side effects in Jira.
* **BYOK trust:** Customer controls vector data (Pinecone) and LLM provider; `.env` documents required keys only.

## 5. Out of Scope (Current Roadmap)

* Custom web dashboard for ticket management.
* Multi-tenant SaaS hosting (local / customer VPC first).
* Universal connector for every ITSM product (Jira first via Python worker).
* Pixel-perfect diagram image rendering server (Mermaid text in Jira is sufficient for v1).

## 6. Related Documentation

* [TRD.md](TRD.md) — technical architecture, API contracts, RAG flow, n8n nodes
* [INTEGRATION_N8N_JIRA.md](INTEGRATION_N8N_JIRA.md) — Jira + n8n integration guide
* [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — Phase 2/4/5 build checklist and target folder structure
* [PHASE3_1_ON_RESOLVE_INGEST.md](PHASE3_1_ON_RESOLVE_INGEST.md) — on-resolve continuous Pinecone upsert
