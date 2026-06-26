# Enterprise RAG Knowledge Platform

A multi-tenant enterprise knowledge assistant where users in different roles (HR, Engineering, Admin) upload documents, ask questions in natural language, and get answers grounded **only** in documents their role is allowed to see — every answer carries source citations.

Built as a portfolio project demonstrating: **LLM/GenAI engineering, prompt engineering + evaluation, RBAC, RAG architecture, MCP integration, FastAPI + Next.js full-stack, Docker microservices, observability, and a credible GCP/Vertex AI production path.**

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend    │────▶│  PostgreSQL │
│  (Next.js)  │     │  (FastAPI)   │     │  + pgvector │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  MCP Server  │
                    │  (Python)    │
                    └──────────────┘
```

### Services

| Service | Technology | Port |
|---------|-----------|------|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS | 3000 |
| Backend API | FastAPI (Python 3.11) | 8000 |
| Database | PostgreSQL 16 + pgvector | 5432 |
| MCP Server | Python MCP SDK | TBD (Phase 6) |

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/)
- (Optional) A [Gemini API key](https://aistudio.google.com/apikey) for best quality — the app can run with local defaults

### Setup

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd rag-knowledge-platform

# 2. Copy and configure environment
cp infra/.env.example infra/.env

# 3. (Optional) Add your Gemini API key
#    Edit infra/.env and set GEMINI_API_KEY=your-key-here

# 4. Start everything
docker compose -f infra/docker-compose.yml up -d

# 5. Verify all services are healthy
docker compose -f infra/docker-compose.yml ps
```

### Verify

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Open the web UI
open http://localhost:3000
```

### Development

```bash
# Run backend tests
cd backend && pytest -v

# Lint backend
cd backend && ruff check .

# Start frontend dev server (hot reload)
cd frontend && npm run dev
```

## RBAC Demo (coming in Phase 3)

The platform enforces role-based access at the SQL level. HR and Engineering users asking the same question will see different answers based on document permissions.

## Evaluation Dashboard (coming in Phase 4)

Built-in evaluation of RAG quality: faithfulness, answer relevance, context precision, and context recall.

## MCP Integration (coming in Phase 6)

The platform exposes RBAC-aware search and retrieval as MCP tools that can be connected to any MCP client.

## Production Deployment on GCP/Vertex AI

> **Note:** See [GCP Migration Guide](./docs/gcp-migration.md) for a detailed migration path.

All cloud-specific concerns (embeddings, LLM, model monitoring, object storage) sit behind clean interfaces with local default implementations, so a GCP/Vertex AI implementation can be dropped in later without architectural change.

## License

MIT
