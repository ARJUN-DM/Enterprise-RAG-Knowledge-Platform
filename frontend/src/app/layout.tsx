"use client";

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export type Role = "hr" | "engineering" | "admin";

const ROLE_LABELS: Record<Role, string> = {
  hr: "HR",
  engineering: "Engineering",
  admin: "Admin",
};

const ROLE_ICONS: Record<Role, string> = {
  hr: "👤",
  engineering: "⚙️",
  admin: "🔐",
};

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: "🏠" },
  { href: "/upload", label: "Upload", icon: "📄" },
  { href: "/chat", label: "Chat", icon: "💬" },
  { href: "/eval", label: "Dashboard", icon: "📊" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [role, setRole] = useState<Role>("hr");
  const [darkMode, setDarkMode] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("rag-role");
    if (saved && ["hr", "engineering", "admin"].includes(saved)) {
      setRole(saved as Role);
    }
    const savedDark = localStorage.getItem("rag-dark");
    if (savedDark !== null) {
      setDarkMode(savedDark === "true");
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("rag-dark", String(darkMode));
  }, [darkMode]);

  const handleRoleChange = useCallback((newRole: Role) => {
    setRole(newRole);
    localStorage.setItem("rag-role", newRole);
  }, []);

  return (
    <html lang="en" suppressHydrationWarning className={darkMode ? "dark" : ""}>
      <body className={`${inter.className} antialiased min-h-screen`}>
        <div className="min-h-screen flex flex-col">
          {/* ── Navigation Bar ── */}
          <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--background)]/80 backdrop-blur-md">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between h-16">
                {/* Logo */}
                <Link href="/" className="flex items-center gap-2 font-bold text-lg">
                  <span className="text-[var(--primary)]">🧠</span>
                  <span className="hidden sm:inline">RAG Platform</span>
                </Link>

                {/* Desktop Nav */}
                <nav className="hidden md:flex items-center gap-1">
                  {NAV_ITEMS.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                          isActive
                            ? "bg-[var(--primary)]/10 text-[var(--primary)]"
                            : "text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-hover)]"
                        }`}
                      >
                        <span>{item.icon}</span>
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </nav>

                {/* Role Switcher + Dark Mode Toggle */}
                <div className="flex items-center gap-3">
                  {/* Role Switcher */}
                  <div className="relative group">
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--card)] border border-[var(--border)] text-sm font-medium hover:bg-[var(--card-hover)] transition-all duration-200">
                      <span>{ROLE_ICONS[role]}</span>
                      <span className="hidden sm:inline">{ROLE_LABELS[role]}</span>
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    <div className="absolute right-0 mt-1 w-44 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl shadow-lg overflow-hidden">
                        {(["hr", "engineering", "admin"] as Role[]).map((r) => (
                          <button
                            key={r}
                            onClick={() => handleRoleChange(r)}
                            className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm transition-all duration-150 ${
                              role === r
                                ? "bg-[var(--primary)]/10 text-[var(--primary)] font-medium"
                                : "text-[var(--foreground)] hover:bg-[var(--card-hover)]"
                            }`}
                          >
                            <span>{ROLE_ICONS[r]}</span>
                            <span>{ROLE_LABELS[r]}</span>
                            {role === r && (
                              <svg className="w-4 h-4 ml-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Dark Mode Toggle */}
                  <button
                    onClick={() => setDarkMode(!darkMode)}
                    className="p-2 rounded-lg text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-hover)] transition-all duration-200"
                    aria-label="Toggle dark mode"
                  >
                    {darkMode ? (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                      </svg>
                    )}
                  </button>

                  {/* Mobile Menu */}
                  <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="md:hidden p-2 rounded-lg text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-hover)] transition-all duration-200"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      {mobileMenuOpen ? (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      ) : (
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                      )}
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            {/* Mobile Nav */}
            <AnimatePresence>
              {mobileMenuOpen && (
                <motion.nav
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="md:hidden border-t border-[var(--border)]"
                >
                  <div className="px-4 py-2 space-y-1">
                    {NAV_ITEMS.map((item) => {
                      const isActive = pathname === item.href;
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={() => setMobileMenuOpen(false)}
                          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                            isActive
                              ? "bg-[var(--primary)]/10 text-[var(--primary)]"
                              : "text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--card-hover)]"
                          }`}
                        >
                          <span>{item.icon}</span>
                          <span>{item.label}</span>
                        </Link>
                      );
                    })}
                  </div>
                </motion.nav>
              )}
            </AnimatePresence>
          </header>

          {/* ── Main Content ── */}
          <main className="flex-1">
            {children}
          </main>

          {/* ── Footer ── */}
          <footer className="border-t border-[var(--border)] py-4 text-center text-xs text-[var(--muted)]">
            <p>RAG Knowledge Platform v1.0.0 — Powered by FastAPI + Next.js + pgvector</p>
          </footer>
        </div>
      </body>
    </html>
  );
}
