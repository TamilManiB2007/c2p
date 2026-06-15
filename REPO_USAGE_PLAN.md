# REPO_USAGE_PLAN.md

**Project:** C2P Platform — Contract-to-Payment Compliance  
**Current Release:** v0.6-document-intelligence  
**Phase:** 7 — Repository Extraction (Plan Only — NO Integration Yet)  
**Audit Date:** 2026-06-15  
**Status:** PLAN ONLY. Nothing integrated. Awaiting approval.

---

## Audit Scope

| Repository | Purpose | Audit Method |
|---|---|---|
| `patchy631/ai-engineering-hub` | LLM/RAG tutorials, document pipelines, background execution patterns | Full tree scan + key file reads |
| `Shubhamsaboo/awesome-llm-apps` | 100+ AI agent & workflow apps with production-grade backend patterns | Full tree scan + key file reads |

---

## Repository 1: `patchy631/ai-engineering-hub`

**Repository summary:**  
A collection of 93+ standalone tutorial projects. Each folder is an independent mini-app covering LLMs, RAG, agents, OCR, and evaluation. Projects range from Jupyter notebooks to full Streamlit apps. No shared backend infrastructure — each project is self-contained.

### Folder Inventory (Relevant to C2P Platform)

| Folder | Purpose | Can Reuse? | Decision |
|---|---|---|---|
| `agentic_rag/` | RAG pipeline with CrewAI + PDFSearchTool. Multi-agent document retrieval with YAML-configured agents and tasks. | NO — requires CrewAI + Serper API + external LLM. Would introduce 3 external API dependencies. | **REJECT** |
| `agentic_rag_deepseek/` | Same as above but using DeepSeek. Adds external LLM dependency. | NO | **REJECT** |
| `LaTeX-OCR-with-Llama/` | OCR of LaTeX equations using Llama 3.2 vision. Requires Llama API or local model. | NO — vision-model dependency, unrelated domain. | **REJECT** |
| `llama-ocr/` | 100% local OCR via Llama 3.2. Requires Ollama + model download. | NO — not PDF text extraction, vision-model OCR. We already use pdfplumber. | **REJECT** |
| `gemma3-ocr/` | Structured text extraction using Gemma-3 vision model. | NO — same issues as above. External model dependency. | **REJECT** |
| `ai-podcast-generation/src/` | Multi-module structured pipeline: `script_generator.py`, `text_to_speech.py`, `web_scraper.py`. Clean service-layer separation. | **PARTIAL** — pipeline structure pattern (not the code) is reusable. | **MODIFY (Pattern only)** |
| `agentic_rag/src/agentic_rag/config/agents.yaml` | YAML-based agent/task configuration schema. Declarative pipeline definition. | **YES** — schema pattern is portable. No code to copy. | **MODIFY (Structure)** |
| `streaming-ai-chatbot/` | Real-time streaming using Motia framework. | NO — chatbot domain, requires Motia SDK. | **REJECT** |
| `ai-avatar-demo/services/` | Service-layer pattern: `anam_service.py`, `llm_service.py`, `zep_service.py`. Clean `services/` module separation. | **PARTIAL** — demonstrates clean service isolation. Already implemented in C2P. | **KEEP (Already done)** |

### Component Selected from Repo 1

#### COMPONENT A — `ai-podcast-generation/src/podcast/` — Pipeline Stage Separation Pattern

| Field | Value |
|---|---|
| **Folder** | `ai-podcast-generation/src/podcast/` |
| **Key files** | `script_generator.py` (2 variants), `text_to_speech.py` |
| **Purpose** | Implements a clean multi-stage pipeline: each stage is a discrete class with a single responsibility. Input validation → processing → output hand-off. |
| **Can reuse?** | Pattern only — no copy-paste. The stage-class architecture applies to C2P's document extraction pipeline. |
| **How to adapt** | Refactor `document_parser.py` to use a `PipelineStage` base class pattern. Each stage (TextExtraction → StructuredParsing → Validation → Scoring) becomes its own class with a `run(input) → output` contract. Enables independent testing of each stage and easier fallback switching. |
| **Risk** | LOW — this is a structural/pattern change. No new dependencies. Does not touch DB, auth, or business rules. |
| **Estimated LOC** | ~80 LOC for the refactored `document_parser.py` stage classes |
| **Decision** | **MODIFY** |

---

## Repository 2: `Shubhamsaboo/awesome-llm-apps`

**Repository summary:**  
100+ real AI apps spanning single agents, multi-agent teams, and RAG systems. More production-oriented than repo 1. Notable patterns: structured background task tracking with SQLAlchemy, structured logging with `loguru`, FastAPI background tasks with status polling, and repository-pattern database access.

### Folder Inventory (Relevant to C2P Platform)

| Folder | Purpose | Can Reuse? | Decision |
|---|---|---|---|
| `advanced_ai_agents/multi_agent_apps/agent_teams/ai_travel_planner_agent_team/backend/` | Full FastAPI backend: agents, background jobs, repository pattern, structured logging, SQLAlchemy models with `TaskStatus` enum. Most complete backend pattern in the repo. | **YES (patterns)** — background task queue model, logger configuration, and repository pattern are directly relevant. | **MODIFY** |
| `advanced_ai_agents/multi_agent_apps/agent_teams/ai_travel_planner_agent_team/backend/models/plan_task.py` | `TaskStatus` enum (`queued`, `in_progress`, `success`, `error`) + Mapped SQLAlchemy columns. Exact pattern C2P needs for document job tracking. | **YES** — adapts directly to `DocumentJob` model with minimal changes. No external dependencies. | **MODIFY** |
| `advanced_ai_agents/multi_agent_apps/agent_teams/ai_travel_planner_agent_team/backend/config/logger.py` | `loguru`-based structured logger with `InterceptHandler` for stdlib compatibility. Colorized console output with backtrace support. | **YES** — production-grade logging pattern we can adopt in `app/core/logging.py`. Only dependency: `loguru`. | **MODIFY** |
| `advanced_ai_agents/multi_agent_apps/agent_teams/ai_travel_planner_agent_team/backend/repository/` | `TripPlanRepository` + `PlanTaskRepository`: clean repository pattern separating DB queries from business logic. | **PARTIAL** — C2P's existing CRUD functions in routers should be refactored to a repository pattern (future sprint). | **KEEP (Future)** |
| `advanced_ai_agents/multi_agent_apps/agent_teams/ai_legal_agent_team/` | Legal document processing agents. Uses external LLM APIs. | NO — LLM-dependent, business rule replacement risk. | **REJECT** |
| `advanced_ai_agents/multi_agent_apps/agent_teams/ai_finance_agent_team/` | Finance agent team. Thin wrapper around external LLM API for financial analysis. | NO — external API dependency, replaces compliance logic. | **REJECT** |
| `advanced_ai_agents/multi_agent_apps/agent_teams/ag2_adaptive_research_team/` | Multi-agent research system. Complex agent orchestration requiring OpenAI API. | NO — external LLM, agent framework (AG2). | **REJECT** |
| `advanced_ai_agents/multi_agent_apps/agent_teams/ai_seo_audit_team/` | SEO analysis agents. Web-scraping focus, not document extraction. | NO — domain mismatch. | **REJECT** |

### Components Selected from Repo 2

#### COMPONENT B — `backend/models/plan_task.py` — Background Job Status Model

| Field | Value |
|---|---|
| **Folder** | `ai_travel_planner_agent_team/backend/models/plan_task.py` |
| **Key files** | `plan_task.py` |
| **Purpose** | Defines `TaskStatus` enum (`queued`, `in_progress`, `success`, `error`) with case-insensitive `_missing_` fallback. SQLAlchemy `Mapped` columns with `DateTime(timezone=True)`. Tracks async job lifecycle in the DB. |
| **Can reuse?** | YES — pattern maps directly to C2P's need to track document parsing jobs (upload → parse → validate → confirm). |
| **How to adapt** | Create `apps/api/app/models/document_job.py`. Add `DocumentJob` model with: `id`, `document_id` (FK), `status` (TaskStatus enum), `started_at`, `completed_at`, `error_detail` (JSON). Add Alembic migration. Wire to `documents/router.py` background task handlers. No new pip dependencies (SQLAlchemy already installed). |
| **Risk** | LOW — additive only. New table, new model. Does not modify existing models, routes, or business logic. |
| **Estimated LOC** | ~60 LOC (model: 35 + migration: 25) |
| **Decision** | **MODIFY** |

#### COMPONENT C — `backend/config/logger.py` — Structured Logging Configuration

| Field | Value |
|---|---|
| **Folder** | `ai_travel_planner_agent_team/backend/config/` |
| **Key files** | `logger.py` |
| **Purpose** | Configures `loguru` as the application-wide logger. Replaces Python's default `logging` with structured, colorized output. `InterceptHandler` redirects all stdlib `logging` calls (uvicorn, sqlalchemy, alembic) to `loguru`. Supports per-module log levels. |
| **Can reuse?** | YES — C2P currently uses bare `print()` and default `logging` calls. This improves observability with zero risk. |
| **How to adapt** | Create `apps/api/app/core/logging.py`. Import and call `configure_logger()` in `main.py` startup. Add `InterceptHandler` to intercept uvicorn/SQLAlchemy logs. Add `loguru` to `requirements.txt`. No schema changes. No route changes. |
| **Risk** | VERY LOW — purely observability enhancement. `loguru` is a well-maintained, zero-conflict library. No business logic touched. |
| **Estimated LOC** | ~70 LOC (logging.py: 60 + main.py edits: 10) |
| **Decision** | **MODIFY** |

---

## Final Selection Summary

> Maximum 3 components as instructed. All 3 are from the **allowed areas** (Document Extraction, Background Jobs, Monitoring).

| # | Component | Source Repo | Source Folder | Allowed Area | Decision | Risk | Est. LOC |
|---|---|---|---|---|---|---|---|
| **A** | Pipeline Stage Separation Pattern | `patchy631/ai-engineering-hub` | `ai-podcast-generation/src/podcast/` | Document Extraction | **MODIFY** | LOW | ~80 |
| **B** | Background Job Status Model (`DocumentJob`) | `Shubhamsaboo/awesome-llm-apps` | `ai_travel_planner.../models/plan_task.py` | Background Jobs | **MODIFY** | LOW | ~60 |
| **C** | Structured Logging (`loguru` + `InterceptHandler`) | `Shubhamsaboo/awesome-llm-apps` | `ai_travel_planner.../config/logger.py` | Monitoring | **MODIFY** | VERY LOW | ~70 |

**Total estimated adaptation LOC: ~210**

---

## What Was Rejected (and Why)

| Component | Reason |
|---|---|
| All RAG pipelines (agentic_rag, agentic_rag_deepseek) | External LLM API dependency (Serper, OpenAI, DeepSeek). Violates "no external APIs" rule. |
| All vision-OCR projects (LaTeX, llama-ocr, gemma3-ocr, qwen-ocr) | Vision model dependency. C2P already has pdfplumber + PyMuPDF. Redundant and heavier. |
| All agent team frameworks (CrewAI, AG2, AutoGen) | Agent orchestration frameworks introduce non-deterministic behavior. C2P uses deterministic extraction only. |
| Legal and Finance agent teams | Risk of replacing C2P business rule logic with LLM-based decisions. Explicitly forbidden. |
| UI components | Forbidden by Phase 7 rules. |
| Auth patterns | Forbidden by Phase 7 rules. C2P auth is already complete. |
| Database replacement patterns | Forbidden. SQLAlchemy + SQLite/Postgres is already production-ready. |

---

## Forbidden Boundaries (Confirmed Clean)

| Boundary | Status |
|---|---|
| UI replacement | NOT touched |
| Authentication | NOT touched |
| Database replacement | NOT touched |
| Business rule replacement | NOT touched |
| External API introduction | NOT introduced |
| Full project cloning | NOT done |

---

## Integration Prerequisite

> **Nothing is integrated yet.** This document is an audit and plan.  
> Integration will only begin after explicit user approval of this plan.

When approved, integration order should be:

1. **Component C** (Logging) — lowest risk, highest immediate value, no schema changes  
2. **Component B** (DocumentJob model) — adds observability to existing document pipeline  
3. **Component A** (Pipeline stage refactor) — structural improvement to document_parser.py

---

## Source References

- `patchy631/ai-engineering-hub` — https://github.com/patchy631/ai-engineering-hub
- `Shubhamsaboo/awesome-llm-apps` — https://github.com/Shubhamsaboo/awesome-llm-apps
- `ai-podcast-generation/src/podcast/` — clean stage-class pipeline pattern (no external dependencies)
- `ai_travel_planner.../backend/models/plan_task.py` — `TaskStatus` enum + SQLAlchemy mapped model
- `ai_travel_planner.../backend/config/logger.py` — `loguru` structured logger with `InterceptHandler`
