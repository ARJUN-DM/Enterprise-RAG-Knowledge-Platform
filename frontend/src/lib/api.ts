/** API client library for the RAG platform backend. */

const API_BASE = "/api/v1";

export type Role = "hr" | "engineering" | "admin";

export type DocumentStatus = "queued" | "processing" | "ingested" | "failed";

export interface HealthStatus {
  status: string;
  database: string;
  pgvector: { installed: boolean; version: string | null };
  version: string;
}

export interface Citation {
  chunk_id: string;
  document: string;
  section: string;
  similarity: number;
  content_preview: string;
}

export interface QueryResponse {
  query_id: string;
  answer: string;
  citations: Citation[];
  trace_id: string;
  latency_ms: number;
  steps: { [key: string]: number };
}

export interface EvalStats {
  avg_faithfulness: number;
  avg_relevance: number;
  avg_context_precision: number;
  avg_context_recall: number;
  total_evaluations: number;
  window_hours: number;
}

export interface EvalHistoryItem {
  id: string;
  faithfulness: number;
  relevance: number;
  context_precision: number;
  context_recall: number;
  flagged: boolean;
  created_at: string;
  question: string;
  role: string;
  trace_id: string;
}

export interface UploadResponse {
  document_id: string;
  file_name: string;
  status: string;
  message: string;
}

export interface DocumentItem {
  id: string;
  name: string;
  uploaded_by_role: string;
  allowed_roles: string[];
  status: DocumentStatus;
  error: string | null;
  chunk_count: number;
  created_at: string;
}

/**
 * Extract a human-readable error message from an API error response body.
 *
 * The backend wraps 5xx errors in `detail` which may be a plain string or an
 * object like `{ error, trace_id, message }`.  This helper unwraps both so
 * the frontend never displays "[object Object]".
 */
function extractErrorMessage(body: unknown): string {
  if (typeof body === "string") return body;
  if (body && typeof body === "object") {
    const obj = body as Record<string, unknown>;
    // The backend returns { detail: { error, trace_id, message } } on 502
    if (obj.detail) {
      return extractErrorMessage(obj.detail);
    }
    // Prefer message, then error, then JSON-stringify the whole thing
    return (
      (typeof obj.message === "string" ? obj.message : undefined) ??
      (typeof obj.error === "string" ? obj.error : undefined) ??
      JSON.stringify(obj)
    );
  }
  return String(body);
}

function headers(role: Role): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-User-Role": role,
  };
}

export async function checkHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export interface HistoryTurn {
  role: "user" | "assistant";
  content: string;
}

export async function askQuestion(
  question: string,
  role: Role,
  history?: HistoryTurn[]
): Promise<QueryResponse> {
  const body: Record<string, unknown> = { question };
  if (history && history.length > 0) {
    body.history = history;
  }
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: headers(role),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      extractErrorMessage(body) || `Query failed: ${res.status}`
    );
  }
  return res.json();
}

export async function uploadDocument(
  file: File,
  allowedRoles: string,
  role: Role
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("allowed_roles", allowedRoles);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    headers: { "X-User-Role": role },
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      extractErrorMessage(body) || `Upload failed: ${res.status}`
    );
  }
  return res.json();
}

export async function getDocuments(
  role: Role,
  limit = 200
): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE}/documents?limit=${limit}`, {
    headers: headers(role),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      extractErrorMessage(body) || `List documents failed: ${res.status}`
    );
  }
  return res.json();
}

export async function deleteDocument(
  documentId: string,
  role: Role
): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: "DELETE",
    headers: headers(role),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      extractErrorMessage(body) || `Delete failed: ${res.status}`
    );
  }
}

export async function getEvalStats(
  role: Role,
  hours = 168
): Promise<EvalStats> {
  const res = await fetch(`${API_BASE}/eval/scores?hours=${hours}`, {
    headers: headers(role),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      extractErrorMessage(body) || `Eval stats failed: ${res.status}`
    );
  }
  return res.json();
}

export async function getEvalHistory(
  role: Role,
  limit = 100
): Promise<EvalHistoryItem[]> {
  const res = await fetch(`${API_BASE}/eval/history?limit=${limit}`, {
    headers: headers(role),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      extractErrorMessage(body) || `Eval history failed: ${res.status}`
    );
  }
  return res.json();
}

export async function getQueryHistory(
  role: Role,
  limit = 50
): Promise<Array<{ id: string; question: string; answer: string; latency_ms: number; created_at: string }>> {
  const res = await fetch(`${API_BASE}/query/history?limit=${limit}`, {
    headers: headers(role),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(
      extractErrorMessage(body) || `Query history failed: ${res.status}`
    );
  }
  return res.json();
}
