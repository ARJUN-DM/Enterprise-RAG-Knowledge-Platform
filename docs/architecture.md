# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Client Layer                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  Web Browser │    │   MCP Client │    │  curl/API │  │
│  │  (Next.js)   │    │   (any)      │    │  clients  │  │
│  └──────┬───────┘    └──────┬───────┘    └─────┬─────┘  │
└─────────┼──────────────────┼────────────────────┼────────┘
          │                  │                    │
┌─────────▼──────────────────▼────────────────────▼────────┐
│                    API Gateway (Nginx/Docker)             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  Frontend ←→ API proxy ←→ Backend ←→ MCP Server   │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────┬────────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────┐
│                  Application Layer                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │             FastAPI (Python 3.11)                    │  │
│  │  ┌─────────┐  ┌───────────┐  ┌──────────────────┐  │  │
│  │  │Ingestion│  │  Query    │  │  Evaluation      │  │  │
│  │  │Pipeline │  │  Pipeline │  │  Framework       │  │  │
│  │  └────┬────┘  └─────┬─────┘  └────────┬─────────┘  │  │
│  │       │              │                  │            │  │
│  │  ┌────▼──────────────▼──────────────────▼──────────┐ │  │
│  │  │           Provider Interfaces                   │ │  │
│  │  │  (LLM, Embedding, Monitoring, Storage)          │ │  │
│  │  └───────────────────┬────────────────────────────┘ │  │
│  └──────────────────────┼───────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────┘
                          │
┌─────────────────────────▼──────────────────────────────────┐
│                   Data Layer                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        PostgreSQL 16 + pgvector                      │  │
│  │  ┌──────────┐  ┌────────┐  ┌────────┐  ┌─────────┐ │  │
│  │  │Documents │  │ Chunks │  │Queries │  │Eval     │ │  │
│  │  │          │  │(vec)   │  │        │  │Scores   │ │  │
│  │  └──────────┘  └────────┘  └────────┘  └─────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Design Principles

### 1. Local-first, Cloud-ready
Everything runs on your machine via Docker Compose with zero paid services. Cloud implementations sit behind clean interfaces.

### 2. Provider-agnostic LLM & Embeddings
`LLMProvider` and `EmbeddingProvider` interfaces with adapters for Gemini (default), Claude, OpenAI, Vertex AI, and Nvidia NIM.

### 3. RBAC at the Data Layer
Role filtering happens inside the retrieval SQL query (`WHERE role = ANY(allowed_roles)`), never only in the application layer.

### 4. Simulated Personas → Real Auth
Phase 1 uses predefined roles selected via a persona switcher. The auth layer is structured as middleware so JWT/OAuth can replace it later.

## Data Model

### documents
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique identifier |
| name | VARCHAR(512) | Document name |
| source | VARCHAR(128) | Upload source |
| uploaded_by_role | VARCHAR(64) | Role that uploaded |
| created_at | TIMESTAMPTZ | Creation timestamp |

### chunks
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique identifier |
| document_id | UUID (FK) | Parent document |
| content | TEXT | Chunk text content |
| embedding | vector(N) | Vector embedding |
| metadata | JSONB | Source, section, page |
| allowed_roles | TEXT[] | Roles with access |
| created_at | TIMESTAMPTZ | Creation timestamp |

### queries
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique identifier |
| role | VARCHAR(64) | Querying role |
| question | TEXT | User question |
| answer | TEXT | Generated answer |
| trace_id | VARCHAR(64) | Correlation ID |
| latency_ms | INTEGER | Query latency |
| created_at | TIMESTAMPTZ | Creation timestamp |

### eval_scores
| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Unique identifier |
| query_id | UUID (FK) | Associated query |
| faithfulness | FLOAT | Faithfulness score |
| relevance | FLOAT | Relevance score |
| context_precision | FLOAT | Context precision |
| context_recall | FLOAT | Context recall |
| flagged | BOOLEAN | Quality alert flag |
| created_at | TIMESTAMPTZ | Creation timestamp |

## Repository Layout

```
/                   Root — Makefile, .gitignore
├── backend/        FastAPI app, providers, ingestion, query, eval
├── frontend/       Next.js + TypeScript + Tailwind
├── infra/          Docker Compose, init SQL, env templates
├── evals/          Golden QA dataset + eval runner
├── docs/           README, architecture, ADRs, GCP migration guide
└── .github/        CI/CD workflows
```
