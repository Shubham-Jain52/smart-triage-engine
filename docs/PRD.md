# Product Requirement Document (PRD)

## 1. Objective & Scope

The **Automated Ticket Routing** product is a **headless, Bring-Your-Own-Key (BYOK)** local application that augments IT ticketing workflows. **Jira** is the primary user interface; agents and requesters never interact with a separate triage UI.

| Phase | Name | Status |
|-------|------|--------|
| **Phase 1** | ML Triage Engine | **Implemented** — webhook ingest, zero-shot routing, HITL, async processing, optional outbound callback |
| **Phase 2** | RAG Resolution Engine | **Planned** — historical ticket retrieval + LLM-generated resolution strategy |
| **Phase 3** | n8n Orchestration | **Planned** — Jira webhooks, triage trigger, write-back to Jira |
| **Phase 4** | Packaging & Local Stack | **Planned** — single `docker-compose up`, single `.env` for all services |

**Phase 1 objective:** Intercept incoming IT tickets, classify them with a local ML model, and route to the correct functional team with confidence-based HITL flagging—without mandatory external LLM APIs for classification.

**Expanded product objective (Phases 2–4):** After routing, automatically surface **similar past tickets** and a **concise resolution strategy** from organizational history, then deliver that intelligence **inside Jira** via orchestration—while keeping embeddings and inference configurable under BYOK (customer-supplied Pinecone, Ollama, or optional cloud LLM keys).

## 2. Core Features

### Phase 1 (Implemented)

* **Webhook Ingestion:** Accept HTTP POST payloads (from n8n, a simulator, or Jira Automation).
* **ML Triage Engine:** Predict team assignment from ticket title and description.
* **Asynchronous Processing:** Return 202 immediately; classify in a background worker.
* **Human-in-the-Loop (HITL):** Flag tickets when confidence is below 80% for manual review.
* **Result Retrieval:** Poll by `ticket_id` or receive an optional HTTP callback.

### Phase 2 — RAG Resolution Engine (Planned)

* **Historical Resolution Retrieval (RAG):** Query a **Pinecone** vector index for the top similar resolved tickets; pass retrieved context to a **local LLM** (e.g. Ollama) or an optional BYOK API to produce a **2–3 sentence resolution strategy**.
* **Enriched Triage Output:** Expose `rag_resolution_summary` and `similar_past_tickets` alongside routing fields so downstream automation can act on one payload.

### Phase 3 — Workflow Orchestration (Planned)

* **n8n Integration:** A local **n8n** instance listens to **Jira** events (issue created), calls the FastAPI microservice, and writes results back to Jira.
* **Assignee routing:** Update Jira assignee (or component/labels) from `assigned_team` and HITL rules.
* **Zero-UI Integration:** Post the AI **resolution summary** as an **internal Jira comment**—no standalone product UI required.

### Phase 4 — Packaging (Planned)

* **One-command local stack:** API, ML dependencies, n8n, and optional Ollama/Pinecone clients configured via a **single root `.env`** and **`docker-compose up`**.
* **BYOK:** Customers supply their own Pinecone index/API key and LLM endpoint (Ollama local or cloud API keys); secrets never ship in the image.

## 3. Success Metrics

### Phase 1

* **Routing accuracy:** ≥ 85% correct team assignments on the validation dataset.
* **Classification latency:** Under 200 ms per ticket for the **classification layer** (steady-state, after model warm-up).
* **Privacy (classification):** 100% of triage classification runs locally without external LLM calls (zero-shot HF model).

### Phase 2

* **RAG relevance:** Qualitative review—retrieved tickets are plausibly related on a held-out set; top-3 Pinecone matches logged for audit.
* **Resolution usefulness:** Internal comment text is 2–3 sentences, actionable, and cites patterns from past fixes (no hallucinated ticket IDs).
* **End-to-end latency budget:** Documented p95 for RAG path (embedding + Pinecone + LLM) separate from Phase 1 routing SLA.

### Phase 3–4

* **Integration reliability:** n8n workflow completes Jira update + comment on ≥ 95% of test issues in a staging project.
* **Packaging:** Fresh clone → `cp .env.example .env` → `docker-compose up` → health checks green for API and n8n within documented startup time.
* **Zero-UI:** Agents see routing + RAG comment only in Jira; no login to a separate triage portal.

## 4. User Experience Principles

* **Jira-native:** Create ticket → automation runs → assignee/labels updated → internal comment with suggested resolution.
* **Headless API:** All intelligence exposed via REST; orchestration owns side effects in Jira.
* **BYOK trust:** Customer controls vector data (Pinecone) and LLM provider; `.env` documents required keys only.

## 5. Out of Scope (Current Roadmap)

* Custom web dashboard for ticket management.
* Multi-tenant SaaS hosting (local / customer VPC first).
* Universal connector for every ITSM product (Jira first via n8n).

## 6. Related Documentation

* [TRD.md](TRD.md) — technical architecture, API contracts, RAG flow, n8n nodes
* [INTEGRATION_N8N_JIRA.md](INTEGRATION_N8N_JIRA.md) — Jira + n8n integration guide
* [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — Phase 2/4 build checklist and target folder structure
