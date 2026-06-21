<div align="center">

# Enterprise RAG Knowledge Platform

**Multi-tenant RAG knowledge assistant with RBAC, evaluation, and MCP integration.**

[![CI](https://img.shields.io/github/actions/workflow/status/your-org/rag-knowledge-platform/ci.yml?branch=main&style=for-the-badge&label=CI&logo=github)](https://github.com/your-org/rag-knowledge-platform/actions)
[![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Development Setup](#-development-setup)
- [Project Structure](#-project-structure)
- [API Overview](#-api-overview)
- [Provider System](#-provider-system)
- [RBAC Model](#-rbac-model)
- [Evaluation Framework](#-evaluation-framework)
- [Testing & CI/CD](#-testing--cicd)
- [Production Deployment](#-production-deployment-on-gcpvertex-ai)
- [License](#-license)

---

## 🌟 Overview

A **multi-tenant enterprise knowledge assistant** where users across different roles (HR, Engineering, Admin) upload documents, ask questions in natural language, and receive answers **grounded exclusively** in documents their role is permitted to access — every answer carries source citations.

This is a **portfolio-grade** project demonstrating:

- **LLM/GenAI engineering** — provider-agnostic LLM and embedding interfaces
- **Prompt engineering + evaluation** — faithfulness, relevance, context precision/recall
- **RBAC at the data layer** — role filtering enforced inside SQL queries
- **RAG architecture** — ingestion → embedding → vector search → re-rank → grounded generation
- **MCP integration** — RBAC-aware retrieval exposed as MCP tools
- **Full-stack engineering** — FastAPI + Next.js with clean separation
- **Docker microservices** — Postgres, backend API, frontend, MCP server
- **Observability** — structured logging, tracing, Prometheus metrics
- **Cloud readiness** — clean provider interfaces with a documented GCP/Vertex AI migration path

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Local-first, cloud-ready** | Everything runs locally via Docker Compose with zero paid services. Cloud implementations sit behind clean interfaces. |
| **Provider-agnostic** | Never hardcode a provider. Switch between Gemini, Claude, OpenAI, Vertex AI, or Nvidia NIM via environment config. |
| **RBAC at the SQL level** | Role filtering happens inside the retrieval query, never only in the application layer. |
| **Simulated personas → real auth** | Phase 1 uses role-based persona switching. Auth is structured as middleware so JWT/OAuth can replace it with zero business logic changes. |
| **Citations are mandatory** | Every generated answer cites the specific source chunks, traceable back to document + section. |
| **Quality is measurable** | Evaluation is a first-class subsystem with configurable alert thresholds. |

---

## ✨ Key Features

- **📄 Document Upload** — Drag-and-drop upload of PDF, Markdown, TXT, DOCX with per-document role assignment
- **💬 Chat Interface** — Streaming responses with message history, typing animations, and role-specific answers
- **🔐 Role-Based Access Control** — HR, Engineering, and Admin personas with SQL-enforced document isolation
- **📎 Source Citations** — Expandable cards showing exact chunks, documents, and sections behind each answer with similarity scores
- **📊 Evaluation Dashboard** — Charts of faithfulness, relevance, context precision, and recall over time with flagged low-scoring answers
- **🔄 Role Switcher** — Instantly switch between HR, Engineering, and Admin personas to see role-specific results
- **🔌 MCP Tools** — RBAC-aware `search_documents` and `get_document` tools for any MCP client
- **📈 Observability** — Trace IDs end-to-end, structured JSON logging, Prometheus `/metrics` endpoint, OpenTelemetry tracing
- **🧪 CI/CD Quality Gate** — GitHub Actions runs the evaluation suite against a golden QA dataset and fails if faithfulness drops below threshold

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│   ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│   │  Web Browser │    │  MCP Client  │    │  curl / API   │  │
│   │  (Next.js)   │    │  (any)       │    │  clients      │  │
│   └──────┬───────┘    └──────┬───────┘    └───────┬───────┘  │
└──────────┼──────────────────┼──────────────────────┼──────────┘
           │                  │                      │
┌──────────▼──────────────────▼──────────────────────▼──────────┐
│                       API Gateway                              │
│   ┌─────────────────────────────────────────────────────────┐ │
│   │   Frontend ←→ API Proxy ←→ Backend ←→ MCP Server       │ │
│   └─────────────────────────────────────────────────────────┘ │
└──────────────────────────┬────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────┐
│                     Application Layer                          │
│   ┌─────────────────────────────────────────────────────────┐ │
│   │                  FastAPI (Python 3.11)                   │ │
│   │   ┌────────────┐  ┌──────────┐  ┌──────────────────┐   │ │
│   │   │  Ingestion │  │  Query   │  │  Evaluation      │   │ │
│   │   │  Pipeline  │  │  Pipeline│  │  Framework       │   │ │
│   │   └──────┬─────┘  └────┬─────┘  └────────┬─────────┘   │ │
│   │          │              │                  │             │ │
│   │   ┌──────▼──────────────▼──────────────────▼──────────┐ │ │
│   │   │            Provider Interfaces                     │ │ │
│   │   │   (LLM, Embedding, Monitoring, Storage)            │ │ │
│   │   └──────────────────────┬────────────────────────────┘ │ │
│   └──────────────────────────┼───────────────────────────────┘ │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                        Data Layer                                │
│   ┌──────────────────────────────────────────────────────────┐ │
│   │              PostgreSQL 16 + pgvector                     │ │
│   │   ┌──────────┐  ┌────────┐  ┌────────┐  ┌────────────┐ │ │
│   │   │Documents │  │ Chunks │  │Queries │  │Eval Scores │ │ │
│   │   │          │  │(vector)│  │        │  │            │ │ │
│   │   └──────────┘  └────────┘  └────────┘  └────────────┘ │ │
│   └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**Ingestion Pipeline** (background, async):
```
Upload → Parse → Semantic Chunking → Embed (via EmbeddingProvider) → Store in pgvector with allowed_roles
```

**Query Pipeline** (request path):
```
Question → Embed → Role-filtered Vector Search → Re-rank → Grounded Prompt → LLM (via LLMProvider) → Cited Answer + Sources
```

### Services

| Service | Technology | Port | Description |
|---------|-----------|------|-------------|
| **Frontend** | Next.js 14 + TypeScript + Tailwind CSS + Framer Motion | `3000` | Web UI for upload, chat, eval dashboard, persona switching |
| **Backend API** | FastAPI (Python 3.11) + SQLAlchemy 2.x (async) | `8000` | REST API for ingestion, query, evaluation, and health monitoring |
| **Database** | PostgreSQL 16 + pgvector | `5432` | Document storage, vector embeddings, queries, eval scores |
| **MCP Server** | Python MCP SDK | `8001` | RBAC-aware retrieval tools for MCP clients (Phase 6) |

---

## 🛠 Tech Stack

### Backend

| Category | Technology |
|----------|-----------|
| **Runtime** | Python 3.11+ |
| **Framework** | FastAPI with Pydantic v2 |
| **ORM** | SQLAlchemy 2.x (async) + Alembic |
| **Database** | PostgreSQL 16 + pgvector |
| **Driver** | asyncpg |
| **LLM Providers** | Gemini (default), Claude, OpenAI, Vertex AI, Nvidia NIM |
| **Embedding Providers** | Gemini (default), sentence-transformers (local fallback), OpenAI, Vertex AI, Nvidia NIM |
| **Observability** | structlog, OpenTelemetry, Prometheus client |
| **Testing** | pytest + pytest-asyncio + pytest-cov |
| **Linting/Formatting** | ruff + black |
| **Type Checking** | mypy (strict mode) |

### Frontend

| Category | Technology |
|----------|-----------|
| **Framework** | Next.js 14 (App Router) |
| **Language** | TypeScript (strict) |
| **Styling** | Tailwind CSS |
| **Animations** | Framer Motion |
| **Linting** | ESLint |

### Infrastructure

| Category | Technology |
|----------|-----------|
| **Containerization** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions |
| **Production Target** | Cloud Run / GKE (documented migration path) |

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/)
- (Optional) A [Gemini API key](https://aistudio.google.com/apikey) for best quality — the app runs with local defaults

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/rag-knowledge-platform.git
cd rag-knowledge-platform

# 2. Copy and configure environment
cp infra/.env.example infra/.env

# 3. (Optional) Add your Gemini API key
#    Edit infra/.env and set GEMINI_API_KEY=your-key-here

# 4. Start all services
docker compose -f infra/docker-compose.yml up -d

# 5. Verify all services are healthy
docker compose -f infra/docker-compose.yml ps
```

### Verification

```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "pgvector": {"installed": true, "version": "0.7.0"},
#   "version": "0.1.0"
# }

# Open the web UI
open http://localhost:3000
```

The frontend landing page displays a live **System Health** panel showing API, database, and pgvector status.

### Shutdown

```bash
docker compose -f infra/docker-compose.yml down
```

To also remove the database volume (reset all data):
```bash
docker compose -f infra/docker-compose.yml down -v
```

---

## 🔧 Development Setup

### Backend (Python 3.11+)

```bash
# Create and activate virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install ruff black mypy pytest pytest-asyncio httpx

# Copy environment config
cp .env.example .env
# Edit .env with your local database URL

# Run tests
pytest -v

# Lint and format
ruff check .
black .

# Type check
mypy app tests

# Generate Alembic migration (after schema changes)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend (Node.js 20+)

```bash
cd frontend
npm install

# Start dev server with hot reload
npm run dev

# Type check
npx tsc --noEmit

# Lint
npm run lint

# Production build
npm run build
```

### Common Commands (Makefile)

```bash
make up            # Start all services
make down          # Stop all services
make logs          # Tail logs from all services
make psql          # Connect to PostgreSQL
make backend-test  # Run backend tests
make backend-lint  # Lint backend
```

---

## 📁 Project Structure

```
├── 📁 backend/                     # FastAPI application
│   ├── 📁 app/
│   │   ├── 📁 api/v1/              # API route handlers
│   │   │   └── health.py           # Health check endpoint
│   │   ├── 📁 core/                # Core utilities (middleware, auth)
│   │   ├── 📁 db/
│   │   │   ├── models.py           # SQLAlchemy ORM models
│   │   │   └── session.py          # Async DB session factory
│   │   ├── 📁 providers/
│   │   │   └── interfaces.py       # LLMProvider & EmbeddingProvider ABCs
│   │   ├── config.py               # Pydantic settings (env-driven)
│   │   └── main.py                 # FastAPI app factory with lifespan
│   ├── 📁 alembic/                 # Database migrations
│   │   ├── env.py                  # Async Alembic environment
│   │   └── versions/               # Migration scripts
│   ├── 📁 tests/                   # pytest test suite
│   ├── Dockerfile                  # Multi-stage production build
│   ├── pyproject.toml              # Project metadata, tool config
│   └── requirements.txt            # Python dependencies
│
├── 📁 frontend/                    # Next.js application
│   ├── 📁 src/
│   │   ├── 📁 app/                 # App Router pages
│   │   │   ├── globals.css         # Tailwind + CSS variables
│   │   │   ├── layout.tsx          # Root layout with metadata
│   │   │   └── page.tsx            # Landing page with health display
│   │   ├── 📁 components/          # Reusable UI components
│   │   └── 📁 lib/                 # Utilities, API client, types
│   ├── Dockerfile                  # Multi-stage production build
│   ├── next.config.js              # Standalone output + API rewrites
│   ├── tailwind.config.ts          # Tailwind with dark mode
│   └── tsconfig.json               # TypeScript strict config
│
├── 📁 infra/                       # Infrastructure
│   ├── docker-compose.yml          # Full stack orchestration
│   ├── init.sql                    # pgvector extension setup
│   └── .env.example                # Environment variable template
│
├── 📁 evals/                       # Evaluation
│   └── (golden QA dataset, eval runner, thresholds)
│
├── 📁 docs/                        # Documentation
│   ├── architecture.md             # System architecture deep-dive
│   ├── gcp-migration.md            # GCP/Vertex AI production path
│   └── adrs/                       # Architecture Decision Records
│
├── 📁 .github/workflows/
│   └── ci.yml                      # CI pipeline with quality gates
│
├── Makefile                        # Common development commands
├── .gitignore                      # Comprehensive ignore rules
└── README.md                       # You are here
```

---

## 📡 API Overview

### Health

```http
GET /api/v1/health
```
Returns API, database, and pgvector status.

| Response Field | Description |
|---------------|-------------|
| `status` | `"healthy"` if all systems operational |
| `database` | `"connected"` if DB reachable |
| `pgvector.installed` | Whether pgvector extension exists |
| `pgvector.version` | Installed pgvector version |
| `version` | Application version |

### Future Endpoints (Coming in Phases 2–4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload a document with role assignment |
| `GET` | `/api/v1/documents` | List accessible documents |
| `POST` | `/api/v1/query` | Ask a question (RBAC-filtered) |
| `GET` | `/api/v1/query/{id}` | Retrieve query history and eval scores |
| `GET` | `/api/v1/eval/dashboard` | Eval dashboard data |
| `GET` | `/api/v1/metrics` | Prometheus metrics |

All endpoints accept an `X-User-Role` header (or `X-User-Token` for JWT) and propagate `X-Trace-ID` for request correlation.

---

## 🔌 Provider System

The platform uses **provider-agnostic interfaces** for all AI and infrastructure dependencies. Switch providers via environment variables — no code changes needed.

### LLM Providers (`LLMProvider`)

| Provider | Config Value | Status | API Key Needed |
|----------|-------------|--------|---------------|
| **Gemini** (default) | `gemini` | ✅ Active | Optional (free tier) |
| **Claude** | `claude` | ➕ Stub ready | `ANTHROPIC_API_KEY` |
| **OpenAI** | `openai` | ➕ Stub ready | `OPENAI_API_KEY` |
| **Vertex AI** | `vertex` | ➕ Stub ready | GCP auth |
| **Nvidia NIM** | `nvidia-nim` | ➕ Stub ready | Nvidia NGC key |

### Embedding Providers (`EmbeddingProvider`)

| Provider | Config Value | Status | Dimensions |
|----------|-------------|--------|------------|
| **Gemini** (default) | `gemini` | ✅ Active | 768 |
| **sentence-transformers** (local) | `sentence-transformers` | ➕ Stub ready | 384 |
| **OpenAI** | `openai` | ➕ Stub ready | 1536 |
| **Vertex AI** | `vertex` | ➕ Stub ready | 768 |
| **Nvidia NIM** | `nvidia-nim` | ➕ Stub ready | 1024 |

### Configuration

```env
# Select providers
LLM_PROVIDER=gemini          # Options: gemini, claude, openai, vertex, nvidia-nim
EMBEDDING_PROVIDER=gemini    # Options: gemini, sentence-transformers, openai, vertex, nvidia-nim

# API keys (only needed for non-default providers)
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

> **Note:** With the default `gemini` provider and no API key, the app falls back to local defaults for smoke tests. For best quality, [get a free Gemini API key](https://aistudio.google.com/apikey).

---

## 🔐 RBAC Model

Role-based access control is enforced at **two layers**:

### 1. Data Layer (SQL-Level)

Role filtering happens inside the retrieval query — never only in the application layer:

```sql
SELECT * FROM chunks
WHERE embedding <=> :query_embedding < :threshold
  AND :user_role = ANY(allowed_roles)
ORDER BY embedding <=> :query_embedding
LIMIT :k;
```

This guarantees that even if a bug exists in the application logic, a user cannot retrieve chunks assigned to a role they don't have.

### 2. Application Layer (Middleware)

The `X-User-Role` header is validated and passed through the request context. This is structured as FastAPI dependency injection, so swapping to JWT/OAuth requires no changes to business logic.

### Personas

| Role | Description |
|------|-------------|
| **HR** | Can access HR documents (policies, benefits, compensation) |
| **Engineering** | Can access engineering documents (architecture, API docs, runbooks) |
| **Admin** | Can access all documents across all roles |

> **Demo:** Two users (HR and Engineering) asking "What is our vacation policy?" will see different answers — HR gets the full HR policy; Engineering gets nothing (or a polite refusal) if only HR documents contain that information.

---

## 📊 Evaluation Framework

Quality is a **first-class subsystem**. Every query can be evaluated on four metrics:

### Metrics

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **Faithfulness** | Fraction of answer claims grounded in retrieved context | LLM-as-judge scoring |
| **Answer Relevance** | How relevant the answer is to the question | Cosine similarity (query vs answer embeddings) |
| **Context Precision** | Fraction of retrieved chunks actually used in the answer | Precision@k |
| **Context Recall** | Fraction of relevant ground-truth chunks retrieved | Recall against golden QA dataset |

### Thresholds

| Metric | Warning | Alert (Flagged) |
|---------|---------|----------------|
| Faithfulness | < 0.90 | < 0.85 |
| Answer Relevance | < 0.80 | < 0.70 |
| Context Precision | < 0.70 | < 0.60 |
| Context Recall | < 0.70 | < 0.60 |

Alerts are persisted to the `eval_scores` table with timestamps. The CI pipeline runs the eval suite as a **quality gate** — builds fail if faithfulness drops below the configured threshold.

### Golden QA Dataset

Located in `evals/`, this is a manually curated set of questions with expected answers and relevant document IDs. Used to measure context recall and as a regression suite.

---

## 🧪 Testing & CI/CD

### Local Testing

```bash
make backend-test        # pytest with coverage
make backend-lint        # ruff check
make backend-format      # black --check
make backend-typecheck   # mypy strict
```

### CI Pipeline (GitHub Actions)

The `.github/workflows/ci.yml` workflow runs on every push and pull request to `main`:

```
Backend Job:
  ├── ruff lint
  ├── black format check
  ├── mypy type check (strict)
  ├── pytest with coverage
  └── eval quality gate (faithfulness ≥ threshold)

Frontend Job:
  ├── tsc --noEmit
  ├── eslint
  └── next build
```

> **Note:** DB-dependent tests require a running PostgreSQL + pgvector container. The CI workflow spins up a `pgvector/pgvector:pg16` service container for this purpose.

---

## ☁ Production Deployment on GCP/Vertex AI

> **Full details in [docs/gcp-migration.md](./docs/gcp-migration.md)**

The platform is designed with a **clean migration path** to Google Cloud. Every cloud-specific concern sits behind a provider interface — no architectural changes needed.

| Component | Local (Dev) | GCP (Production) |
|-----------|-------------|-------------------|
| **LLM** | Gemini API | Vertex AI Gemini |
| **Embeddings** | Gemini API / sentence-transformers | Vertex AI text-embedding |
| **Database** | PostgreSQL 16 + pgvector (Docker) | Cloud SQL for PostgreSQL + pgvector |
| **Storage** | Local filesystem | Cloud Storage (GCS) |
| **Auth** | Persona header (`X-User-Role`) | Firebase Auth / Identity Platform |
| **Monitoring** | Console + `/metrics` endpoint | Cloud Monitoring + Vertex AI Model Monitoring |
| **Containers** | Docker Compose | Cloud Run / GKE |
| **CI/CD** | GitHub Actions | Cloud Build + Deploy to Cloud Run |

### Migration Steps

1. Set up GCP project, enable Vertex AI API, Cloud SQL, Cloud Storage
2. Deploy PostgreSQL via Cloud SQL with pgvector extension
3. Build container images with Cloud Build, push to Artifact Registry
4. Deploy backend to Cloud Run with `LLM_PROVIDER=vertex` and `EMBEDDING_PROVIDER=vertex`
5. Deploy frontend to Cloud Run or Firebase Hosting
6. Set up Cloud Monitoring dashboards and alerts
7. Enable Vertex AI Model Monitoring for evaluation metrics
8. Update CI/CD to deploy to Cloud Run on merge to main

---

## 📄 License

MIT — see [LICENSE](./LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ as a portfolio project demonstrating LLM/GenAI engineering, RAG architecture, and full-stack development.</sub>
</div>
