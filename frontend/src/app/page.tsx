"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { checkHealth, type HealthStatus, type Role } from "@/lib/api";

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const features = [
    {
      icon: "📄",
      title: "Upload Documents",
      desc: "Upload PDF, Markdown, DOCX, or TXT files with role-based access control.",
      href: "/upload",
      color: "from-blue-500/20 to-cyan-500/20",
    },
    {
      icon: "💬",
      title: "Ask Questions",
      desc: "Get grounded answers with source citations from your organization's documents.",
      href: "/chat",
      color: "from-purple-500/20 to-pink-500/20",
    },
    {
      icon: "📊",
      title: "Evaluation Dashboard",
      desc: "Monitor answer quality with faithfulness, relevance, precision, and recall metrics.",
      href: "/eval",
      color: "from-emerald-500/20 to-teal-500/20",
    },
    {
      icon: "🔐",
      title: "Role-Based Access",
      desc: "Switch between HR, Engineering, and Admin personas to see role-filtered results.",
      href: "#",
      color: "from-amber-500/20 to-orange-500/20",
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center mb-12 sm:mb-16"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--border)] text-sm text-[var(--muted)] mb-4">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          {loading ? (
            <span>Checking system...</span>
          ) : health?.status === "healthy" ? (
            <span>All systems operational</span>
          ) : (
            <span className="text-[var(--danger)]">System issue detected</span>
          )}
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-4">
          Enterprise RAG
          <span className="text-[var(--primary)]"> Knowledge Platform</span>
        </h1>
        <p className="text-lg sm:text-xl text-[var(--muted)] max-w-2xl mx-auto">
          Ask questions across your organization&apos;s documents and get answers
          grounded in sources — with role-based access control and continuous
          quality evaluation.
        </p>
      </motion.div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-12">
        {features.map((feature, i) => (
          <motion.div
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * i, duration: 0.4 }}
          >
            <Link
              href={feature.href}
              className="block h-full group"
            >
              <div className={`h-full rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 transition-all duration-300 hover:shadow-lg hover:-translate-y-1 bg-gradient-to-br ${feature.color}`}>
                <div className="text-3xl mb-3">{feature.icon}</div>
                <h3 className="font-semibold mb-2 group-hover:text-[var(--primary)] transition-colors">
                  {feature.title}
                </h3>
                <p className="text-sm text-[var(--muted)]">{feature.desc}</p>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>

      {/* System Health */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="max-w-lg mx-auto"
      >
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <span>🖥️</span> System Health
          </h2>

          {error && (
            <div className="text-sm text-[var(--danger)] p-3 rounded-lg bg-[var(--danger)]/10">
              Failed to connect: {error}
            </div>
          )}

          {loading && !error && (
            <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <div className="w-4 h-4 rounded-full border-2 border-[var(--primary)] border-t-transparent animate-spin" />
              <span>Connecting to backend...</span>
            </div>
          )}

          {health && (
            <div className="space-y-2">
              <HealthRow label="API" value={health.status} ok={health.status === "healthy"} />
              <HealthRow label="Database" value={health.database} ok={health.database === "connected"} />
              <HealthRow
                label="pgvector"
                value={health.pgvector.installed ? `v${health.pgvector.version}` : "Not installed"}
                ok={health.pgvector.installed}
              />
              <HealthRow label="Version" value={health.version} ok />
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

function HealthRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className="text-[var(--muted)]">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`} />
        <span className="font-medium">{value}</span>
      </div>
    </div>
  );
}
