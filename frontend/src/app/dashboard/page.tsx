"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shield, Clock, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Scan } from "@/types";

function StatusIcon({ status }: { status: string }) {
  if (status === "done") return <CheckCircle className="w-4 h-4 text-emerald-500" />;
  if (status === "failed") return <XCircle className="w-4 h-4 text-red-500" />;
  if (status === "running") return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
  return <Clock className="w-4 h-4 text-gray-400" />;
}

export default function DashboardPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listScans()
      .then((data) => setScans(data as Scan[]))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <Shield className="w-5 h-5 text-emerald-500" />
          <h1 className="font-semibold text-gray-900">Scan History</h1>
          <Link href="/" className="ml-auto text-sm text-emerald-600 hover:underline">
            + New Scan
          </Link>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {loading && <div className="text-center text-gray-400 py-16">Loading scans...</div>}
        {error && <div className="text-red-600 text-center py-8">{error}</div>}

        {!loading && scans.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            No scans yet.{" "}
            <Link href="/" className="text-emerald-600 hover:underline">
              Run your first scan →
            </Link>
          </div>
        )}

        <div className="space-y-3">
          {scans.map((scan) => (
            <Link
              key={scan.id}
              href={`/scan/${scan.id}`}
              className="block bg-white rounded-xl border border-gray-200 px-5 py-4 hover:border-emerald-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-center gap-4">
                <StatusIcon status={scan.status} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-gray-400">{scan.id.slice(0, 8)}</span>
                    <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-2 py-0.5">
                      {scan.language}
                    </span>
                  </div>
                  {scan.repo_url && (
                    <p className="text-sm text-gray-600 truncate mt-0.5">{scan.repo_url}</p>
                  )}
                </div>
                <div className="text-right text-xs text-gray-400">
                  {new Date(scan.created_at).toLocaleDateString()}
                </div>
                <div className="text-emerald-600 text-sm font-medium">View →</div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
