"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  getEvalStats,
  getEvalHistory,
  type EvalStats,
  type EvalHistoryItem,
} from "@/lib/api";

type MetricKey = "avg_faithfulness" | "avg_relevance" | "avg_context_precision" | "avg_context_recall";

const METRICS: { key: MetricKey; label: string; icon: string; desc: string; color: string }[] = [
  {
    key: "avg_faithfulness",
    label: "Faithfulness",
    icon: "🎯",
    desc: "Fraction of claims supported by retrieved context",
    color: "from-green-500 to-emerald-600",
  },
  {
    key: "avg_relevance",
    label: "Relevance",
    icon: "🎯",
    desc: "Query-answer cosine similarity",
    color: "from-blue-500 to-cyan-600",
  },
  {
    key: "avg_context_precision",
    label: "Context Precision",
    icon: "📐",
    desc: "Fraction of retrieved chunks used in answer",
    color: "from-purple-500 to-violet-600",
  },
  {
    key: "avg_context_recall",
    label: "Context Recall",
    icon: "📋",
    desc: "Overlap with golden QA dataset",
    color: "from-amber-500 to-orange-600",
  },
];

export default function EvalDashboardPage() {
  const [stats, setStats] = useState<EvalStats | null>(null);
  const [history, setHistory] = useState<EvalHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState(168);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const storedRole = (localStorage.getItem("rag-role") || "admin") as "hr" | "engineering" | "admin";
      const [s, h] = await Promise.all([
        getEvalStats(storedRole, timeWindow),
        getEvalHistory(storedRole, 100),
      ]);
      setStats(s);
      setHistory(h);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evaluation data");
    } finally {
      setLoading(false);
    }
  }, [timeWindow]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Score color
  const scoreColor = (val: number) => {
    if (val >= 0.85) return "text-green-500";
    if (val >= 0.7) return "text-amber-500";
    return "text-red-500";
  };

  const scoreBg = (val: number) => {
    if (val >= 0.85) return "bg-green-500/10 border-green-500/30";
    if (val >= 0.7) return "bg-amber-500/10 border-amber-500/30";
    return "bg-red-500/10 border-red-500/30";
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl">📊</span>
          <h1 className="text-2xl font-bold">Evaluation Dashboard</h1>
        </div>
        <p className="text-[var(--muted)]">
          Monitor answer quality metrics: faithfulness, relevance, context precision, and context recall.
        </p>
      </motion.div>

      {/* Time Window Selector */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-[var(--muted)]">Time window:</span>
        {[
          { value: 24, label: "24h" },
          { value: 168, label: "7d" },
          { value: 720, label: "30d" },
        ].map((w) => (
          <button
            key={w.value}
            onClick={() => setTimeWindow(w.value)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
              timeWindow === w.value
                ? "bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/30"
                : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--muted)]"
            }`}
          >
            {w.label}
          </button>
        ))}
        <button
          onClick={fetchData}
          className="ml-auto px-3 py-1.5 rounded-lg text-sm border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
          disabled={loading}
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="p-4 rounded-xl bg-[var(--danger)]/10 border border-[var(--danger)]/30 text-sm text-[var(--danger)]"
        >
          {error}
        </motion.div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {METRICS.map((metric, i) => {
          const val = stats ? stats[metric.key] : 0;
          return (
            <motion.div
              key={metric.key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * i }}
              className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5"
            >
              <div className="flex items-center gap-2 mb-2">
                <span>{metric.icon}</span>
                <span className="font-semibold text-sm">{metric.label}</span>
              </div>
              <div className={`text-3xl font-bold mb-1 ${scoreColor(val)}`}>
                {(val * 100).toFixed(0)}%
              </div>
              <div className="w-full h-2 bg-[var(--border)] rounded-full overflow-hidden mt-2">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${val * 100}%` }}
                  transition={{ duration: 1, delay: 0.2 + 0.05 * i }}
                  className={`h-full rounded-full bg-gradient-to-r ${metric.color}`}
                />
              </div>
              <p className="text-xs text-[var(--muted)] mt-2">{metric.desc}</p>
            </motion.div>
          );
        })}
      </div>

      {/* Stats Summary */}
      {stats && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              <span>📈</span>
              <span className="font-medium">
                {stats.total_evaluations} evaluation{stats.total_evaluations !== 1 ? "s" : ""} recorded
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <span>⏱️ {stats.window_hours}h window</span>
            </div>
          </div>
          <div className="mt-2 text-sm">
            <span className="text-[var(--muted)]">Average score: </span>
            <span className={`font-bold ${scoreColor(
              (stats.avg_faithfulness + stats.avg_relevance + stats.avg_context_precision + stats.avg_context_recall) / 4
            )}`}>
              {((stats.avg_faithfulness + stats.avg_relevance + stats.avg_context_precision + stats.avg_context_recall) / 4 * 100).toFixed(1)}%
            </span>
          </div>
        </motion.div>
      )}

      {/* Flagged Evaluations */}
      {history.filter(h => h.flagged).length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <span>⚠️</span> Flagged Evaluations (Low Faithfulness)
          </h2>
          <div className="space-y-2">
            {history.filter(h => h.flagged).slice(0, 10).map((item) => (
              <div
                key={item.id}
                className={`rounded-xl border p-4 ${scoreBg(item.faithfulness)}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{item.question}</p>
                    <p className="text-xs text-[var(--muted)] mt-0.5">
                      Role: {item.role} · {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className={`text-lg font-bold ${scoreColor(item.faithfulness)}`}>
                      {(item.faithfulness * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-[var(--muted)]">Faithfulness</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Evaluation History Table */}
      {history.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <span>📋</span> Recent Evaluations
          </h2>
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[var(--card-hover)] border-b border-[var(--border)]">
                  <th className="text-left px-4 py-3 font-medium">Question</th>
                  <th className="text-left px-4 py-3 font-medium">Role</th>
                  <th className="text-center px-4 py-3 font-medium">Faithfulness</th>
                  <th className="text-center px-4 py-3 font-medium">Relevance</th>
                  <th className="text-center px-4 py-3 font-medium">Precision</th>
                  <th className="text-center px-4 py-3 font-medium">Recall</th>
                  <th className="text-right px-4 py-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 25).map((item) => (
                  <tr key={item.id} className="border-b border-[var(--border)] hover:bg-[var(--card-hover)] transition-colors">
                    <td className="px-4 py-3 max-w-[250px] truncate">{item.question}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 text-xs rounded-full bg-[var(--primary)]/10 text-[var(--primary)]">
                        {item.role}
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-center font-medium ${scoreColor(item.faithfulness)}`}>
                      {(item.faithfulness * 100).toFixed(0)}%
                    </td>
                    <td className={`px-4 py-3 text-center font-medium ${scoreColor(item.relevance)}`}>
                      {(item.relevance * 100).toFixed(0)}%
                    </td>
                    <td className={`px-4 py-3 text-center font-medium ${scoreColor(item.context_precision)}`}>
                      {(item.context_precision * 100).toFixed(0)}%
                    </td>
                    <td className={`px-4 py-3 text-center font-medium ${scoreColor(item.context_recall)}`}>
                      {(item.context_recall * 100).toFixed(0)}%
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--muted)] text-xs">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}

      {/* Empty state */}
      {!loading && !error && history.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16 text-[var(--muted)]"
        >
          <div className="text-5xl mb-4">📊</div>
          <p className="font-medium mb-1">No evaluations yet</p>
          <p className="text-sm">
            Start asking questions in the Chat tab to generate evaluation data.
          </p>
        </motion.div>
      )}
    </div>
  );
}
