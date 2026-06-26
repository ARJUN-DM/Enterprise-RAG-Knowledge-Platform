"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { askQuestion, type QueryResponse, type Citation, type HistoryTurn } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  latencyMs?: number;
  steps?: Record<string, number>;
  error?: boolean;
}

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Hello! I'm your enterprise knowledge assistant. Ask me anything about the documents in your organization. I'll answer with source citations so you can verify every claim.",
};

const STORAGE_KEY_PREFIX = "rag-chat-history:";
const MAX_STORED_MESSAGES = 50;

function loadMessages(role: string): Message[] {
  if (typeof window === "undefined") return [WELCOME_MESSAGE]; // SSR guard
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${role}`);
    if (raw) {
      const parsed: Message[] = JSON.parse(raw);
      // Ensure welcome message is always first
      const hasWelcome = parsed.some((m) => m.id === "welcome");
      return hasWelcome ? parsed : [WELCOME_MESSAGE, ...parsed];
    }
  } catch {
    // localStorage unavailable or corrupt — start fresh
  }
  return [WELCOME_MESSAGE];
}

function saveMessages(role: string, messages: Message[]): void {
  if (typeof window === "undefined") return; // SSR guard
  try {
    // Keep the welcome message, then the last MAX_STORED_MESSAGES-1 others
    const welcome = messages.filter((m) => m.id === "welcome");
    const others = messages.filter((m) => m.id !== "welcome").slice(-(MAX_STORED_MESSAGES - 1));
    const toStore = [...welcome, ...others];
    localStorage.setItem(`${STORAGE_KEY_PREFIX}${role}`, JSON.stringify(toStore));
  } catch {
    // localStorage full or unavailable — silently skip
  }
}

function clearStoredMessages(role: string): void {
  if (typeof window === "undefined") return; // SSR guard
  try {
    localStorage.removeItem(`${STORAGE_KEY_PREFIX}${role}`);
  } catch {
    // silently skip
  }
}

export default function ChatPage() {
  const [currentRole, setCurrentRole] = useState<string>("hr");
  const [hydrated, setHydrated] = useState(false);

  const [messages, setMessages] = useState<Message[]>(() => loadMessages(currentRole));
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Persist messages to localStorage whenever they change
  useEffect(() => {
    saveMessages(currentRole, messages);
  }, [messages, currentRole]);

  // Scroll to bottom on new messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Hydrate from localStorage on first client render
  useEffect(() => {
    const storedRole = localStorage.getItem("rag-role") || "hr";
    setCurrentRole(storedRole);
    setMessages(loadMessages(storedRole));
    setHydrated(true);
  }, []);

  // Poll for role changes (the nav switcher writes to localStorage)
  useEffect(() => {
    if (!hydrated) return;
    const interval = setInterval(() => {
      const storedRole = localStorage.getItem("rag-role") || "hr";
      if (storedRole !== currentRole) {
        // Save current messages before switching
        saveMessages(currentRole, messages);
        setCurrentRole(storedRole);
        setMessages(loadMessages(storedRole));
      }
    }, 500);
    return () => clearInterval(interval);
  }, [currentRole, messages, hydrated]);

  // Build history from recent messages (exclude welcome, exclude citations)
  const buildHistory = useCallback(
    (msgs: Message[]): HistoryTurn[] => {
      return msgs
        .filter((m) => m.id !== "welcome")
        .slice(-6) // last 6 messages = ~3 turns
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));
    },
    []
  );

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      const question = input.trim();
      if (!question || loading) return;

      setInput("");
      setLoading(true);

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: question,
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const storedRole = localStorage.getItem("rag-role") || "hr";
        // Build history from prior messages (excludes the current question)
        const history = buildHistory(messages);

        const response = await askQuestion(
          question,
          storedRole as "hr" | "engineering" | "admin",
          history.length > 0 ? history : undefined
        );

        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          citations: response.citations,
          latencyMs: response.latency_ms,
          steps: response.steps,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: err instanceof Error ? err.message : "An error occurred while processing your question.",
          error: true,
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading, messages, buildHistory]
  );

  const handleClearChat = useCallback(() => {
    clearStoredMessages(currentRole);
    setMessages([WELCOME_MESSAGE]);
    setShowClearConfirm(false);
  }, [currentRole]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Convert role key to display label
  const roleLabel = currentRole.charAt(0).toUpperCase() + currentRole.slice(1);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 h-[calc(100vh-8rem)] flex flex-col">
      {/* Chat Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">💬</span>
          <div>
            <h1 className="text-xl font-bold">Chat with Your Documents</h1>
            <p className="text-sm text-[var(--muted)]">
              Ask questions and get cited answers from your organization&apos;s knowledge base
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--muted)] bg-[var(--card)] border border-[var(--border)] rounded-lg px-2 py-1">
            {roleLabel}
          </span>
          {/* Clear chat button */}
          <div className="relative">
            <button
              onClick={() => setShowClearConfirm(!showClearConfirm)}
              disabled={loading || messages.length <= 1}
              className="p-2 rounded-lg text-[var(--muted)] hover:text-[var(--danger)] hover:bg-[var(--danger)]/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="Clear chat"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>

            {/* Confirm dropdown */}
            <AnimatePresence>
              {showClearConfirm && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 top-full mt-1 z-50 bg-[var(--card)] border border-[var(--border)] rounded-xl p-3 shadow-lg min-w-[200px]"
                >
                  <p className="text-xs text-[var(--muted)] mb-2">
                    Clear all messages for <strong>{roleLabel}</strong>?
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={handleClearChat}
                      className="flex-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-[var(--danger)] text-white hover:opacity-90 transition-opacity"
                    >
                      Clear
                    </button>
                    <button
                      onClick={() => setShowClearConfirm(false)}
                      className="flex-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-[var(--background)] border border-[var(--border)] hover:bg-[var(--card)] transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 ${
                  msg.role === "user"
                    ? "bg-[var(--primary)] text-white"
                    : msg.error
                    ? "bg-[var(--danger)]/10 border border-[var(--danger)]/30"
                    : "bg-[var(--card)] border border-[var(--border)]"
                }`}
              >
                {/* Assistant avatar */}
                {msg.role === "assistant" && msg.id !== "welcome" && (
                  <div className="flex items-center gap-2 mb-2 text-xs text-[var(--muted)]">
                    <span>🧠 Assistant</span>
                    {msg.latencyMs && (
                      <span>· {(msg.latencyMs / 1000).toFixed(1)}s</span>
                    )}
                    {msg.steps && (
                      <span>
                        · Embed: {((msg.steps.embed_ms ?? 0) / 1000).toFixed(1)}s ·{" "}
                        Search: {((msg.steps.search_ms ?? 0) / 1000).toFixed(1)}s ·{" "}
                        LLM: {((msg.steps.llm_ms ?? 0) / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>
                )}

                {/* Content */}
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {msg.content}
                </div>

                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[var(--border)]">
                    <p className="text-xs font-semibold text-[var(--muted)] mb-2">
                      Sources ({msg.citations.length}):
                    </p>
                    <div className="space-y-2">
                      {msg.citations.map((c, i) => (
                        <details key={c.chunk_id} className="group">
                          <summary className="text-xs cursor-pointer hover:text-[var(--primary)] transition-colors list-none flex items-center gap-1">
                            <span className="shrink-0">[{i + 1}]</span>
                            <span className="truncate">{c.document}</span>
                            {c.section && (
                              <span className="text-[var(--muted)] truncate">— {c.section}</span>
                            )}
                            <span className="text-[var(--muted)] ml-auto shrink-0">
                              {c.similarity.toFixed(3)}
                            </span>
                          </summary>
                          <div className="mt-1 p-2 rounded-lg bg-[var(--background)] text-xs text-[var(--muted)]">
                            {c.content_preview}
                          </div>
                        </details>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading indicator */}
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl p-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[var(--primary)] animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-2 h-2 rounded-full bg-[var(--primary)] animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-2 h-2 rounded-full bg-[var(--primary)] animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex items-end gap-2 bg-[var(--card)] border border-[var(--border)] rounded-xl p-2 focus-within:border-[var(--primary)] transition-colors">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your documents..."
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm px-2 py-1 max-h-32"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2 rounded-lg bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19V5m0 0l-7 7m7-7l7 7" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
