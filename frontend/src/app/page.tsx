"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { Shield, Zap, GitPullRequest } from "lucide-react";
import { api } from "@/lib/api";

const CodeMirror = dynamic(() => import("@uiw/react-codemirror"), { ssr: false });

const LANGUAGES = ["python", "javascript", "typescript", "java", "go", "php", "ruby", "csharp", "cpp"];

const DEMO_CODE = `# Paste your code here or try this vulnerable example:
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()

def set_password(username, password):
    import hashlib
    # Weak hashing vulnerability
    hashed = hashlib.md5(password.encode()).hexdigest()
    db.execute(f"UPDATE users SET password='{hashed}' WHERE username='{username}'")
`;

export default function HomePage() {
  const router = useRouter();
  const [code, setCode] = useState(DEMO_CODE);
  const [language, setLanguage] = useState("python");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleScan() {
    if (!code.trim()) return;
    setLoading(true);
    setError("");
    try {
      const scan = await api.createScan({ code, language }) as { id: string };
      router.push(`/scan/${scan.id}`);
    } catch (e: any) {
      setError(e.message ?? "Failed to start scan");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
      {/* Nav */}
      <nav className="border-b border-slate-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-emerald-400" />
          <span className="font-semibold text-lg">AI Code Scanner</span>
        </div>
        <a href="/dashboard" className="text-sm text-slate-300 hover:text-white transition-colors">
          Dashboard →
        </a>
      </nav>

      {/* Hero */}
      <div className="max-w-5xl mx-auto px-6 pt-16 pb-10">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">
            Find & Fix Security Vulnerabilities{" "}
            <span className="text-emerald-400">Instantly</span>
          </h1>
          <p className="text-slate-300 text-lg max-w-2xl mx-auto">
            Paste your code — our AI scans for OWASP Top 10 vulnerabilities, explains each in plain
            English, and generates a ready-to-merge fix.
          </p>
          <div className="flex items-center justify-center gap-8 mt-6 text-sm text-slate-400">
            <span className="flex items-center gap-1"><Zap className="w-4 h-4 text-emerald-400" /> Real-time scanning</span>
            <span className="flex items-center gap-1"><Shield className="w-4 h-4 text-emerald-400" /> OWASP Top 10</span>
            <span className="flex items-center gap-1"><GitPullRequest className="w-4 h-4 text-emerald-400" /> GitHub PR integration</span>
          </div>
        </div>

        {/* Editor card */}
        <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden shadow-2xl">
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 bg-slate-900">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 border border-slate-600 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            >
              {LANGUAGES.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>

          <div className="min-h-64 max-h-96 overflow-auto">
            <CodeMirror
              value={code}
              onChange={setCode}
              height="350px"
              theme="dark"
              style={{ fontSize: "14px" }}
            />
          </div>

          <div className="px-4 py-3 border-t border-slate-700 bg-slate-900 flex items-center justify-between">
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="ml-auto">
              <button
                onClick={handleScan}
                disabled={loading || !code.trim()}
                className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-6 py-2.5 rounded-xl transition-colors"
              >
                {loading ? (
                  <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> Scanning...</>
                ) : (
                  <><Shield className="w-4 h-4" /> Scan for Vulnerabilities</>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
