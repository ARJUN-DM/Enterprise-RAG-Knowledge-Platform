"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { uploadDocument, getDocuments, deleteDocument, type UploadResponse, type DocumentItem, type DocumentStatus } from "@/lib/api";

const ACCEPTED_TYPES = ".pdf,.md,.txt,.docx";
const ACCEPTED_MIME = [
  "application/pdf",
  "text/markdown",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const MAX_SIZE = 20 * 1024 * 1024; // 20 MB
const ROLES = ["hr", "engineering", "admin"];

interface UploadItem {
  id: string;
  file: File;
  allowedRoles: string[];
  status: "pending" | "uploading" | "success" | "error";
  message: string;
  response?: UploadResponse;
}

function statusBadgeClass(status: DocumentStatus): string {
  switch (status) {
    case "queued":
      return "bg-yellow-500/10 text-yellow-500 border-yellow-500/30";
    case "processing":
      return "bg-blue-500/10 text-blue-500 border-blue-500/30";
    case "ingested":
      return "bg-green-500/10 text-green-500 border-green-500/30";
    case "failed":
      return "bg-red-500/10 text-red-500 border-red-500/30";
  }
}

function statusIcon(status: DocumentStatus): string {
  switch (status) {
    case "queued":
      return "⏳";
    case "processing":
      return "🔄";
    case "ingested":
      return "✅";
    case "failed":
      return "❌";
  }
}

export default function UploadPage() {
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [defaultRoles, setDefaultRoles] = useState<string[]>(["hr", "engineering"]);
  const [persistedDocs, setPersistedDocs] = useState<DocumentItem[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load persisted documents on mount and periodically
  const loadDocuments = useCallback(async () => {
    try {
      const role = (localStorage.getItem("rag-role") || "hr") as "hr" | "engineering" | "admin";
      const docs = await getDocuments(role);
      setPersistedDocs(docs);
    } catch {
      // Silently fail — docs list is a nice-to-have
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
    // Poll for status updates every 5 seconds while there are non-terminal docs
    const interval = setInterval(() => {
      // Check if any persisted docs have non-terminal status
      const hasActive = persistedDocs.some(
        (d) => d.status === "queued" || d.status === "processing"
      );
      if (hasActive) {
        loadDocuments();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [loadDocuments, persistedDocs]);

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const newItems: UploadItem[] = Array.from(files)
        .filter((f) => {
          const ext = "." + f.name.split(".").pop()?.toLowerCase();
          return ACCEPTED_TYPES.includes(ext);
        })
        .map((file) => ({
          id: crypto.randomUUID(),
          file,
          allowedRoles: [...defaultRoles],
          status: "pending" as const,
          message: "",
        }));

      if (newItems.length === 0) {
        setUploads((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            file: files[0],
            allowedRoles: [...defaultRoles],
            status: "error",
            message: `Unsupported file type. Accepted: ${ACCEPTED_TYPES}`,
          },
        ]);
        return;
      }

      setUploads((prev) => [...prev, ...newItems]);
    },
    [defaultRoles]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        addFiles(e.target.files);
        e.target.value = "";
      }
    },
    [addFiles]
  );

  const uploadFile = useCallback(async (item: UploadItem) => {
    setUploads((prev) =>
      prev.map((u) => (u.id === item.id ? { ...u, status: "uploading" as const, message: "Uploading..." } : u))
    );

    try {
      const role = item.allowedRoles[0] || "hr";
      const response = await uploadDocument(
        item.file,
        item.allowedRoles.join(","),
        role as "hr" | "engineering" | "admin"
      );
      setUploads((prev) =>
        prev.map((u) =>
          u.id === item.id
            ? { ...u, status: "success" as const, message: "Queued for ingestion!", response }
            : u
        )
      );
      // Refresh the persisted documents list to show the new queued document
      setTimeout(loadDocuments, 1000);
    } catch (err) {
      setUploads((prev) =>
        prev.map((u) =>
          u.id === item.id
            ? { ...u, status: "error" as const, message: err instanceof Error ? err.message : "Upload failed" }
            : u
        )
      );
    }
  }, [loadDocuments]);

  const uploadAll = useCallback(() => {
    uploads
      .filter((u) => u.status === "pending")
      .forEach((u) => uploadFile(u));
  }, [uploads, uploadFile]);

  const removeItem = useCallback((id: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  }, []);

  const handleDelete = useCallback(
    async (docId: string, docName: string) => {
      if (!window.confirm(`Delete "${docName}"? This cannot be undone.`)) {
        return;
      }
      try {
        const role = (localStorage.getItem("rag-role") || "hr") as "hr" | "engineering" | "admin";
        await deleteDocument(docId, role);
        setPersistedDocs((prev) => prev.filter((d) => d.id !== docId));
      } catch (err) {
        alert(err instanceof Error ? err.message : "Failed to delete document");
      }
    },
    []
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        <div>
          <h1 className="text-2xl font-bold mb-1">Upload Documents</h1>
          <p className="text-[var(--muted)]">
            Upload PDF, Markdown, TXT, or DOCX files. Documents are parsed,
            chunked, embedded, and stored with role-based access control.
          </p>
        </div>

        {/* Default Role Assignment */}
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
          <label className="text-sm font-medium mb-2 block">
            Default allowed roles for new uploads:
          </label>
          <div className="flex flex-wrap gap-2">
            {ROLES.map((r) => (
              <button
                key={r}
                onClick={() =>
                  setDefaultRoles((prev) =>
                    prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]
                  )
                }
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-200 ${
                  defaultRoles.includes(r)
                    ? "bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/30"
                    : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--muted)]"
                }`}
              >
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Drop Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative rounded-xl border-2 border-dashed p-12 text-center cursor-pointer transition-all duration-300 ${
            dragOver
              ? "border-[var(--primary)] bg-[var(--primary)]/5 scale-[1.02]"
              : "border-[var(--border)] hover:border-[var(--muted)] hover:bg-[var(--card-hover)]"
          }`}
        >
          <div className="text-5xl mb-4">📄</div>
          <p className="font-medium mb-1">
            Drag & drop files here, or click to browse
          </p>
          <p className="text-sm text-[var(--muted)]">
            Supports PDF, Markdown, TXT, and DOCX (up to 20 MB)
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>

        {/* Upload Queue */}
        <AnimatePresence>
          {uploads.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="space-y-3"
            >
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">
                  Upload Queue ({uploads.length} file{uploads.length !== 1 ? "s" : ""})
                </h2>
                <div className="flex gap-2">
                  <button
                    onClick={uploadAll}
                    disabled={uploads.every((u) => u.status !== "pending")}
                    className="px-4 py-1.5 bg-[var(--primary)] text-white rounded-lg text-sm font-medium hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50"
                  >
                    Upload All
                  </button>
                  <button
                    onClick={() => setUploads([])}
                    className="px-4 py-1.5 border border-[var(--border)] rounded-lg text-sm font-medium text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </div>

              {uploads.map((item) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20, height: 0 }}
                  className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">
                          {item.file.name.endsWith(".pdf") ? "📕" :
                           item.file.name.endsWith(".md") ? "📝" :
                           item.file.name.endsWith(".docx") ? "📘" : "📄"}
                        </span>
                        <span className="font-medium truncate">{item.file.name}</span>
                        <span className="text-xs text-[var(--muted)] shrink-0">
                          ({(item.file.size / 1024).toFixed(0)} KB)
                        </span>
                      </div>

                      {/* Progress bar for uploading */}
                      {item.status === "uploading" && (
                        <div className="mt-2 h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: "0%" }}
                            animate={{ width: "100%" }}
                            transition={{ duration: 3, ease: "easeInOut" }}
                            className="h-full bg-[var(--primary)] rounded-full"
                          />
                        </div>
                      )}

                      {/* Role badges */}
                      <div className="flex flex-wrap gap-1 mt-1">
                        {item.allowedRoles.map((r) => (
                          <span
                            key={r}
                            className="px-2 py-0.5 text-xs rounded-full bg-[var(--primary)]/10 text-[var(--primary)]"
                          >
                            {r}
                          </span>
                        ))}
                      </div>

                      {/* Status message — show queued, not ingested */}
                      {item.message && (
                        <p className={`text-sm mt-1 ${
                          item.status === "success" ? "text-yellow-500" :
                          item.status === "error" ? "text-[var(--danger)]" :
                          "text-[var(--muted)]"
                        }`}>
                          {item.status === "success" && "⏳ "}
                          {item.status === "error" && "❌ "}
                          {item.message}
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      {item.status === "pending" && (
                        <>
                          <button
                            onClick={() => uploadFile(item)}
                            className="px-3 py-1 bg-[var(--primary)] text-white rounded-lg text-xs font-medium hover:bg-[var(--primary-hover)] transition-colors"
                          >
                            Upload
                          </button>
                          <button
                            onClick={() => removeItem(item.id)}
                            className="p-1 text-[var(--muted)] hover:text-[var(--danger)] transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </>
                      )}
                      {item.status === "success" && (
                        <span className="text-yellow-500 text-lg">⏳</span>
                      )}
                      {item.status === "error" && (
                        <button onClick={() => removeItem(item.id)} className="text-[var(--muted)] hover:text-[var(--danger)]">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Persisted Documents List */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold flex items-center gap-2">
              <span>📂</span> Stored Documents
            </h2>
            <button
              onClick={loadDocuments}
              className="px-3 py-1 border border-[var(--border)] rounded-lg text-xs font-medium text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              Refresh
            </button>
          </div>

          {loadingDocs ? (
            <div className="text-center py-8 text-[var(--muted)] text-sm">
              Loading documents...
            </div>
          ) : persistedDocs.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--border)] p-8 text-center text-[var(--muted)] text-sm">
              No documents uploaded yet.
            </div>
          ) : (
            <div className="space-y-2">
              {persistedDocs.map((doc) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 flex items-start justify-between gap-4"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">
                        {doc.name.endsWith(".pdf") ? "📕" :
                         doc.name.endsWith(".md") ? "📝" :
                         doc.name.endsWith(".docx") ? "📘" : "📄"}
                      </span>
                      <span className="font-medium truncate">{doc.name}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full border ${statusBadgeClass(doc.status)}`}>
                        {statusIcon(doc.status)} {doc.status}
                      </span>
                      <span className="text-xs text-[var(--muted)]">{doc.chunk_count} chunks</span>
                      <span className="text-xs text-[var(--muted)]">by {doc.uploaded_by_role}</span>
                      {doc.allowed_roles.map((r) => (
                        <span
                          key={r}
                          className="px-2 py-0.5 text-xs rounded-full bg-[var(--primary)]/10 text-[var(--primary)]"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                    {doc.status === "failed" && doc.error && (
                      <p className="text-xs text-red-500 mt-1 truncate" title={doc.error}>
                        Error: {doc.error}
                      </p>
                    )}
                    {doc.status === "processing" && (
                      <div className="mt-2 h-1 bg-[var(--border)] rounded-full overflow-hidden w-32">
                        <motion.div
                          animate={{ x: ["-100%", "200%"] }}
                          transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                          className="h-full w-1/3 bg-[var(--primary)] rounded-full"
                        />
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleDelete(doc.id, doc.name)}
                      className="p-1.5 text-[var(--muted)] hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-all duration-200"
                      title="Delete document"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                    <span className="text-xs text-[var(--muted)]">
                      {new Date(doc.created_at).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
}
