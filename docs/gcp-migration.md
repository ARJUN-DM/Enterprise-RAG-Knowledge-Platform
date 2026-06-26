# GCP / Vertex AI Production Migration Guide

> **⚠️ Phase 7 deliverable.** This document outlines the architecture and migration path for deploying the RAG Knowledge Platform on Google Cloud Platform with Vertex AI. It will be completed in Phase 7 (Observability + CI/CD Eval Gate + Docs).

## Migration Areas

| Component | Local (Dev) | GCP (Production) |
|-----------|-------------|-------------------|
| LLM | Gemini API | Vertex AI Gemini |
| Embeddings | Gemini API / sentence-transformers | Vertex AI text-embedding |
| Database | PostgreSQL 16 + pgvector (Docker) | Cloud SQL for PostgreSQL + pgvector |
| Storage | Local filesystem | Cloud Storage (GCS) |
| Auth | Persona header | Firebase Auth / Identity Platform |
| Monitoring | Console + /metrics endpoint | Cloud Monitoring + Vertex AI Model Monitoring |
| Containers | Docker Compose | Cloud Run / GKE |
| CI/CD | GitHub Actions | Cloud Build + Deploy |

## Provider Adapters

All cloud-specific implementations follow the provider interfaces defined in `backend/app/providers/interfaces.py`:

- `LLMProvider` → `VertexAILLMProvider`
- `EmbeddingProvider` → `VertexAIEmbeddingProvider`
- `MonitoringProvider` → `VertexAIMonitoringProvider`
- `StorageProvider` → `GCSStorageProvider`

## Migration Steps

1. **Set up GCP project**, enable Vertex AI API, Cloud SQL, Cloud Storage
2. **Deploy PostgreSQL** via Cloud SQL with pgvector extension
3. **Build container images** with Cloud Build and push to Artifact Registry
4. **Deploy backend** to Cloud Run with Vertex AI provider selected
5. **Deploy frontend** to Cloud Run (static export) or Firebase Hosting
6. **Set up Cloud Monitoring** dashboards and alerts
7. **Enable Vertex AI Model Monitoring** for evaluation metrics
8. **Update CI/CD** to deploy to Cloud Run on merge to main
