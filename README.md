# 🧠 Enterprise RAG Knowledge Platform

[![CI](https://github.com/your-org/rag-knowledge-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/rag-knowledge-platform/actions/workflows/ci.yml)

A multi-tenant-style enterprise knowledge assistant where users in different roles (HR, Engineering, Admin) upload documents, ask questions in natural language, and get answers grounded **only** in documents their role is allowed to see — every answer carries source citations. The platform continuously measures answer quality (faithfulness, relevance, context precision/recall) and surfaces it in a dashboard. It exposes retrieval as MCP tools and ships with full observability.

---

## 🚀 Getting Started

Get the full stack running locally in about five minutes. Everything runs in Docker — you only need one API key.

### Prerequisites

- **Docker Desktop** (running) — bundles Docker + Docker Compose
- **Git** — to clone the repo
- **An NVIDIA API key** — free from [build.nvidia.com](https://build.nvidia.com/). Required for the chat/Q&A LLM. *(Embeddings run locally, so document upload needs no key.)*

### Setup & Run

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd rag-knowledge-platform

# 2. Create your environment file from the template
cp infra/.env.example infra/.env

# 3. Open infra/.env and add your NVIDIA key
#    NVIDIA_API_KEY=nvapi-xxxxxxxx
#    (All other values have working defaults.)

# 4. Build and start the full stack (first run pulls images + builds — give it a few minutes)
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --build

# 5. Verify the backend is healthy
curl http://localhost:8000/api/v1/health
#    Expected: {"status":"healthy","database":"connected","pgvector":{...}}
```

Then open **http://localhost:3000** in your browser.

### First steps in the app

1. Go to the **Upload** tab and upload a document (PDF, Markdown, TXT, or DOCX).
   > The first upload downloads the local embedding model (~90 MB) into the container, so it takes a little longer. Subsequent uploads are fast.
2. Wait for the document status to show **ingested**.
3. Switch to the **Chat** tab and ask a question — you'll get an answer with source citations.
4. Try the **persona switcher** (top-right) to see role-based access control in action.

### Shutting down

```bash
# Stop the stack (keeps your data)
docker compose -f infra/docker-compose.yml down

# Stop and delete the database volume (fresh start)
docker compose -f infra/docker-compose.yml down -v
```

### Notes & troubleshooting

- **Chat needs the NVIDIA key.** Without it, the app still runs and you can upload documents, but asking a question will error. Add `NVIDIA_API_KEY` to `infra/.env` and recreate the backend: `docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --force-recreate backend`.
- **Ports must be free:** `3000` (frontend), `8000` (backend), `5432` (Postgres). If one is taken, change the matching value in `infra/.env`.
- **Changed a value in `.env`?** Re-run the `up -d` command (a plain Docker "restart" won't pick up new env values — the container must be recreated).
- **Empty knowledge base:** a fresh install has no documents — upload your own first.

---

## ✨ Key Features

- **📄 Document Ingestion** — Upload PDF, Markdown, TXT, and DOCX files with drag-and-drop. Documents are parsed, semantically chunked, embedded, and stored with role-based access control.
- **💬 Natural Language Q&A** — Ask questions and get answers grounded *only* in your organization's documents with source citations.
- **🔐 Role-Based Access Control (RBAC)** — HR, Engineering, and Admin personas. Role filtering happens at the SQL query level — no cross-role data leakage.
- **🔄 Persona Switcher** — Switch between HR, Engineering, and Admin from the UI to see role-filtered results.
- **📊 Evaluation Dashboard** — Monitor answer quality with four metrics: faithfulness, relevance, context precision, and context recall. Low-scoring answers are flagged.
- **🔌 MCP Integration** — Expose RBAC-aware search and retrieval tools via the Model Context Protocol for AI IDE integration.
- **🌐 Provider-Agnostic LLM & Embeddings** — Swap between Gemini, Ollama, OpenAI, Claude, Vertex AI, and Nvidia NIM via a single env variable.
- **📈 Observability** — Structured JSON logging, Prometheus metrics, OpenTelemetry tracing, and per-request trace IDs end-to-end.
- **🏭 GCP-Ready** — Every component sits behind a clean interface so GCP/Vertex AI can replace local implementations without architectural changes.
- **✅ CI Quality Gate** — GitHub Actions runs linting, type-checking, tests, AND an evaluation suite against a golden QA dataset. Fails if faithfulness drops below a configurable threshold.

---

## 🏗️ Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   Frontend   │────▶│   FastAPI API   │────▶│   PostgreSQL 16  │
│  (Next.js +  │     │  (Python 3.11)  │     │   + pgvector     │
│   Tailwind)  │     │                 │     │                  │
│  :3000       │     │  :8000          │     │  :5432           │
└──────────────┘     └────────┬────────┘     └──────────────────┘
                              │
                              ├── LLM Providers ──► Gemini / Ollama / OpenAI / Claude / Vertex
                              │
                              ├── Embedding Providers ──► Gemini / sentence-transformers / OpenAI
                              │
                              └── MCP Server (stdio) ──► AI IDE Integration (Claude Code, etc.)
```

### Data Flow: Ingestion

```
File Upload → Parse (PDF/MD/TXT/DOCX) → Semantic Chunking
    → Embedding (configurable provider) → Store in pgvector with allowed_roles[]
```

### Data Flow: Query

```
User Question → Embed Query → Role-Filtered Vector Search (pgvector ≤>)
    → Re-Rank → Grounded Prompt → LLM → Cited Answer + Citations
    → Async Evaluation (faithfulness, relevance, precision, recall)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic |
| **Vector Store** | PostgreSQL 16 + pgvector (Docker) |
| **LLM** | Gemini (default), Ollama, OpenAI, Claude, Vertex AI, Nvidia NIM |
| **Embeddings** | Gemini, sentence-transformers (local, no API key), OpenAI, Vertex |
| **Frontend** | Next.js 14 (App Router) + TypeScript + Tailwind CSS + Framer Motion |
| **MCP** | Python MCP SDK (Model Context Protocol) |
| **Observability** | structlog, Prometheus metrics, OpenTelemetry tracing |
| **Infra** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions (lint + typecheck + test + eval gate) |

---

## 📁 Project Structure

```
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/              # API route handlers
│   │   ├── auth/             # RBAC dependencies (X-User-Role → JWT)
│   │   ├── core/             # Core utilities
│   │   ├── db/               # SQLAlchemy models + session
│   │   ├── eval/             # Evaluation framework (4 metrics)
│   │   ├── ingestion/        # Document parsing, chunking, embedding pipeline
│   │   ├── observability/    # Logging, metrics, tracing
│   │   ├── providers/        # LLM + Embedding provider interfaces & implementations
│   │   │   ├── llm/          # Gemini, Ollama, OpenAI, Claude, Vertex, Nvidia NIM
│   │   │   └── embeddings/   # Gemini, sentence-transformers, OpenAI, Vertex
│   │   └── query/            # RAG query pipeline (embed → search → rerank → LLM)
│   ├── mcp/                  # MCP server (separate Docker service)
│   ├── tests/                # pytest suite
│   └── alembic/              # Database migrations
├── frontend/                 # Next.js application
│   └── src/app/
│       ├── page.tsx          # Home / Dashboard
│       ├── upload/           # Document upload with drag-and-drop
│       ├── chat/             # Chat interface with citations
│       └── eval/             # Evaluation dashboard
├── infra/                    # Docker Compose, init SQL, env templates
├── evals/                    # Golden QA dataset for evaluation gate
├── docs/                     # Architecture docs, GCP migration guide
└── .github/workflows/        # CI/CD pipelines
```

---

## 📡 API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | System health check (DB, pgvector) |
| `POST` | `/api/v1/documents/upload` | Upload a document for ingestion |
| `POST` | `/api/v1/query` | Ask a question (non-streaming) |
| `GET` | `/api/v1/query/stream` | Ask a question (SSE streaming) |
| `GET` | `/api/v1/query/history` | Recent query history |
| `GET` | `/api/v1/eval/scores` | Average evaluation scores |
| `GET` | `/api/v1/eval/history` | Detailed evaluation history |
| `GET` | `/api/v1/eval/flagged` | Flagged low-scoring evaluations |
| `POST` | `/api/v1/eval/run` | Trigger golden QA evaluation run |
| `GET` | `/metrics` | Prometheus metrics |

All query/eval endpoints require the `X-User-Role` header: `hr`, `engineering`, or `admin`.

---

## 🔌 Provider System

The LLM and embedding providers are fully pluggable via environment variables:

### LLM Providers

| Provider | Env Value | API Key Required | Default Model |
|----------|-----------|-----------------|---------------|
| **Gemini** | `gemini` | Yes (for real responses) | `gemini-2.0-flash` |
| **Ollama** | `ollama` | No (local) | `llama3.2` |
| **OpenAI** | `openai` | Yes | `gpt-4o-mini` |
| **Claude** | `claude` | Yes | `claude-sonnet-4-20250514` |
| **Vertex AI** | `vertex` | Yes (GCP) | `gemini-2.0-flash-001` |
| **Nvidia NIM** | `nvidia-nim` | Yes | `meta/llama-3.3-70b-instruct` |

### Embedding Providers

| Provider | Env Value | API Key Required | Dimensions |
|----------|-----------|-----------------|------------|
| **Gemini** | `gemini` | Yes | 768 |
| **sentence-transformers** | `sentence-transformers` | **No** (local, ~90 MB model) | 384 → padded to 768 |
| **OpenAI** | `openai` | Yes | 768 (configurable) |
| **Vertex AI** | `vertex` | Yes (GCP) | 768 (stub) |

**Default config** (no API key needed):
- `LLM_PROVIDER=nvidia-nim` — calls NVIDIA's hosted Llama 3.3 70B via OpenAI-compatible API (requires `NVIDIA_API_KEY`)
- `EMBEDDING_PROVIDER=sentence-transformers` — runs locally, no key needed

**For best quality**, add an [NVIDIA API key](https://build.nvidia.com/):
```bash
NVIDIA_API_KEY=your_key_here
```

**Legacy providers**: `LLM_PROVIDER=gemini` (Gemini) and `LLM_PROVIDER=ollama` (local) are also available with their respective API keys.

---

## 🔐 RBAC Model

Role-based access control is enforced at the **SQL query level**:

- Each `chunk` has an `allowed_roles TEXT[]` column
- All retrieval queries include `WHERE :role = ANY(allowed_roles)`
- The `X-User-Role` header (set by the persona switcher in the UI) drives the role
- **Three roles**: `hr`, `engineering`, `admin`
- The auth module is structured as a FastAPI dependency, ready for JWT/OAuth2 replacement

### RBAC Demo Script

To verify RBAC isolation manually:

```bash
# 1. Upload an HR document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "X-User-Role: hr" \
  -F "file=@hr_policy.pdf" \
  -F "allowed_roles=hr"

# 2. Search as HR (should find the document)
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-User-Role: hr" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the remote work policy?"}'

# 3. Search as Engineering (should NOT find it)
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-User-Role: engineering" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the remote work policy?"}'
```

---

## 📊 Evaluation Dashboard

The evaluation framework computes four metrics for every query:

| Metric | Description | Calculation |
|--------|-------------|-------------|
| **Faithfulness** | What fraction of claims in the answer are supported by the context? | LLM-judged (claims extraction + verification) |
| **Relevance** | How relevant is the answer to the question? | Cosine similarity of query and answer embeddings |
| **Context Precision** | What fraction of retrieved chunks are actually used? | Direct content overlap check |
| **Context Recall** | What fraction of relevant chunks were retrieved? | Overlap with golden QA dataset |

A faithfulness score below **0.85** flags the answer for review and fails the CI evaluation gate.

Open the dashboard at [http://localhost:3000/eval](http://localhost:3000/eval)

---

## 🔌 MCP Connection

The MCP server runs as a separate Docker container and communicates via stdio transport. Connect it to any MCP-compatible client:

### Claude Desktop / Claude Code

In your MCP config (`claude_desktop_config.json` or `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "rag-platform": {
      "command": "docker",
      "args": [
        "exec", "-i", "rag-mcp",
        "python", "-m", "rag_mcp"
      ]
    }
  }
}
```

### Available Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_documents` | `query` (str), `role` (enum), `top_k` (int, optional) | Semantic search with RBAC filtering |
| `get_document` | `document_id` (str), `role` (enum) | Get document details and chunks |

---

## 🧪 Testing & CI/CD

### Local Testing

```bash
# Backend tests
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx
pytest -v --cov=app

# Frontend type check
cd frontend
npm install
npm run typecheck
```

### CI Pipeline (GitHub Actions)

The CI workflow runs on every push/PR to `main`:

1. **Backend**: Lint (ruff), format check (black), type check (mypy), tests (pytest)
2. **Frontend**: Type check (tsc), lint (eslint), build (next build)
3. **Eval Quality Gate**: Runs the evaluator against the golden QA dataset. Fails if average faithfulness < 0.85

---

## 🏭 Production Deployment (GCP/Vertex AI Path)

| Local Component | GCP Equivalent |
|----------------|----------------|
| PostgreSQL + pgvector | Cloud SQL for PostgreSQL + pgvector |
| Gemini API | Vertex AI Gemini API |
| sentence-transformers | Vertex AI Text Embeddings |
| Local monitoring | Cloud Monitoring + Vertex AI Model Monitoring |
| Docker Compose | Cloud Run + GKE |
| File storage | Cloud Storage (GCS) |
| Background tasks | Cloud Tasks + Cloud Functions |
| OpenTelemetry console | Cloud Trace |

**Migration steps:**
1. Replace `EmbeddingProvider` with Vertex AI embeddings implementation
2. Replace `LLMProvider` with Vertex AI Gemini implementation
3. Replace `MonitoringProvider` with Vertex AI Model Monitoring
4. Migrate file storage to GCS
5. Deploy with Cloud Run or GKE
6. Set up Cloud SQL for PostgreSQL with pgvector

See [docs/gcp-migration.md](docs/gcp-migration.md) for detailed migration instructions.

---

## 📝 Assumptions & Decisions

- **NVIDIA NIM LLM provider (Meta Llama 3.3 70B)**: The default LLM provider is now NVIDIA's hosted OpenAI-compatible API using `meta/llama-3.3-70b-instruct`. Set `NVIDIA_API_KEY` in your `.env` file. The provider raises a clear error if the API key is missing (no silent stub). Transient errors (429/5xx) are retried up to 3 times with exponential backoff. The endpoint and model are configurable via `NVIDIA_BASE_URL` and `NVIDIA_MODEL` env vars.
- **Local embeddings (sentence-transformers)**: Embeddings run locally via `sentence-transformers` (`all-MiniLM-L6-v2`, 384-d padded to 768-d). No API key, no quota limits. The model (~90 MB) downloads on first use. **Switching to a different embedding model will orphan existing document vectors** — you must delete and re-upload all documents.
- **Local LLM fallback**: When no NVIDIA API key is set, the Gemini provider is available as a fallback (set `LLM_PROVIDER=gemini`). For a fully local LLM, set `LLM_PROVIDER=ollama` and run Ollama separately.
- **sentence-transformers padding**: The default local embedding model (`all-MiniLM-L6-v2`) produces 384-dimensional vectors. These are zero-padded to 768 to match the Gemini embedding schema. Configure via `EMBEDDING_DIMENSIONS` env var.
- **Persona-based auth (not real auth)**: v1 uses the `X-User-Role` header for persona switching. The auth module is a FastAPI dependency, ready for JWT/OAuth2 replacement with zero business-logic changes.
- **HNSW vs IVFFlat**: The system uses pgvector's default indexing (IVFFlat). For production-scale deployments (>100K chunks), add an HNSW index for faster search.
- **Background ingestion**: Document ingestion runs as FastAPI background tasks (not a separate worker). For production, replace with Celery, Cloud Tasks, or Pub/Sub using the same `IngestionTask` abstraction.
- **MCP transport**: The MCP server uses stdio transport (the most widely supported). For remote connections, add SSE or streamable HTTP transport.
- **MCP temporarily disabled**: The standalone MCP container is currently disabled in Docker Compose pending a transport rework (stdio → HTTP/SSE). It remains fully wired in code and can be re-enabled once the transport change lands.
- **Document ingestion status tracking**: Documents now have a lifecycle (`queued → processing → ingested/failed`) visible via `GET /api/v1/documents`. The upload endpoint creates a Document row immediately (status=queued) so it appears in the listing even before background ingestion completes. Failed documents show the error message inline.
- **Default embedding provider**: Changed from `gemini` to `sentence-transformers` in `config.py` so the app works out of the box without any API key. The local sentence-transformers model (`all-MiniLM-L6-v2`) produces 384-dim vectors padded to 768. Set `EMBEDDING_PROVIDER=gemini` and provide `GEMINI_API_KEY` for production-quality embeddings.
- **Gemini embedding model**: Renamed from `text-embedding-004` to `gemini-embedding-001` (the 2025 active model). Output dimensionality is explicitly set to 768 via `EmbedContentConfig(output_dimensionality=768)`. Each embedding is L2-normalized before storage so cosine-distance ranking is well-behaved (the 001 model does not auto-normalize at reduced dimensions). The model name is configurable via `GEMINI_EMBEDDING_MODEL` env var.
- **No zero-vector fallback on embedding failure**: Removed the silent fallback that stored zero-vector embeddings on failure. If embedding generation throws, the exception now propagates and the document's status is set to `failed` with the error message. A document is only marked `ingested` when all chunks have real embeddings.
- **Frontend error display**: Added `extractErrorMessage()` helper in `api.ts` that unwraps backend `detail` objects (`{error, trace_id, message}`). This prevents the raw `[object Object]` stringification that appeared when the chat hit a 502 error. All API functions (`askQuestion`, `uploadDocument`, `getDocuments`, eval/query history) use this helper.
- **Document delete**: Added `DELETE /api/v1/documents/{document_id}` endpoint with RBAC (admin can delete all, other roles can delete documents they can see). The frontend shows a trash icon per document with a `window.confirm()` step. On success the document is removed from the list without a full reload.
- **Gemini embedding batch limit**: The Gemini embedding API caps a single batch at **100 requests**. The `embed_batch()` method splits larger document batches into sub-batches of at most 100 texts, calls `embed_content` per sub-batch, and concatenates results in original order. Each sub-batch is retried up to 4 times with exponential backoff on transient errors (429/503). The batch size is configurable via the `GEMINI_EMBED_BATCH_SIZE` constant in the module. If the returned count doesn't match the input count, a clear error is raised (no silent padding/dropping).
- **Chunk merging for small segments**: The chunker (`app/ingestion/chunker.py`) merges consecutive short segments sharing the same section heading and source into larger chunks (target ≥200 chars, max 512). This prevents single-line fragments from being stored as individual chunks. Long paragraphs continue to be split at sentence boundaries with overlap. Previously-stored documents should be re-uploaded to benefit from merged chunking.
- **Document name in chunk metadata**: Chunk `meta_data["source"]` now stores the original uploaded file name (e.g. `Conversation_1.pdf`) instead of the temporary upload filename (e.g. `tmpu2uwx28l.pdf`). The citation renderer (`format_citation_text`) also prefers the authoritative DB document name over parser-level metadata, so even previously-stored chunks display the correct name.
- **De-duplication of retrieved chunks**: The query pipeline drops exact-duplicate chunk contents after re-ranking, keeping only the highest-similarity instance. This prevents the LLM context from containing multiple copies of the same line. `top_k` is configured at 8 (up from 5) to increase the diversity of retrieved content.
- **Empty-content robustness (NVIDIA reasoning models)**: MiniMax M3 is a reasoning model that may put its output in a hidden `reasoning_content` channel, leaving `content` empty. The NVIDIA provider never raises on empty content — it first tries to recover `reasoning_content`, then returns an empty string. The pipeline provides a friendly fallback if the LLM does return empty. No `Internal Server Error` is ever surfaced for empty LLM responses.
- **MiniMax M3 requires max_tokens**: Unlike Meta Llama 3.3, MiniMax M3 on NVIDIA's OpenAI-compatible API returns an empty response (zero choices) when the request does not include `max_tokens`. The NVIDIA provider always sends `max_tokens` (default 2048, configurable via `NVIDIA_MAX_TOKENS` env var) on every chat completion call. If the API still returns no choices after retries, the provider returns an empty string so the pipeline's friendly fallback handles it instead of surfacing a raw error.
- **Low-similarity threshold (removed)**: The query pipeline previously skipped the grounded LLM call when the top chunk similarity was below `similarity_threshold` (0.35). The local embedding model (sentence-transformers all-MiniLM-L6-v2) produces cosine similarities in the ~0.2–0.4 range even for **relevant** chunks, so filtering on absolute similarity was causing real questions to be answered with the canned greeting. The threshold has been removed entirely. Instead, greetings are detected by a small explicit heuristic (matches a known set like {"hi", "hello", "hey"}, ≤4 words) and the no-documents case is handled separately. All other queries proceed to the full RAG + LLM path regardless of absolute similarity.
- **Multi-turn conversation memory**: The chat endpoint accepts an optional `history` field (list of `{"role", "content"}` turns, max 6 messages). Follow-up questions are condensed into a standalone retrieval query (heuristic: appends prior user context) so they retrieve the right chunks. The conversation history is passed to the LLM, making follow-ups like "list them one by one" work. The frontend sends the last 6 non-welcome messages as history with each query.
- **Per-role capped localStorage chat persistence**: Chat history is saved to `localStorage` keyed by role (`rag-chat-history:<role>`), so HR, Engineering, and Admin each have their own conversation. The stored history is capped at 50 messages per role. A "Clear chat" button in the header resets the conversation with a confirmation step and clears that role's localStorage entry. History survives navigation and browser reloads.

---

## 📄 License

MIT — feel free to use this project as a portfolio piece or production starter.
