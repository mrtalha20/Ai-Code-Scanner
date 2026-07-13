"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Shield, CheckCircle, XCircle, Loader2, ArrowLeft, Download } from "lucide-react";
import Link from "next/link";
import { createWsUrl } from "@/lib/api";
import { Finding, WsMessage } from "@/types";
import FindingCard from "@/components/findings/FindingCard";
import SeveritySummary from "@/components/findings/SeveritySummary";
import OWASPBreakdown from "@/components/findings/OWASPBreakdown";
import ScanProgress from "@/components/scanner/ScanProgress";

type ScanState = "connecting" | "running" | "done" | "error";

export default function ScanPage() {
  const { id } = useParams<{ id: string }>();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [status, setStatus] = useState<ScanState>("connecting");
  const [stage, setStage] = useState("Connecting...");
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!id) return;
    const ws = new WebSocket(createWsUrl(id));
    wsRef.current = ws;

    ws.onopen = () => setStatus("running");

    ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data);
      if (msg.event === "progress") {
        setStage(msg.stage ?? "Scanning...");
        setProgress(msg.progress_pct ?? 0);
      } else if (msg.event === "finding" && msg.finding) {
        setFindings((prev) => {
          // deduplicate by id
          if (prev.some((f) => f.id === msg.finding!.id)) return prev;
          return [...prev, msg.finding!];
        });
        setProgress((p) => Math.min(p + 2, 95));
      } else if (msg.event === "done") {
        setStatus("done");
        setProgress(100);
        setStage("Complete");
      } else if (msg.event === "error") {
        setStatus("error");
        setErrorMsg(msg.message ?? "Scan failed");
      }
    };

    ws.onerror = () => {
      setStatus("error");
      setErrorMsg("WebSocket connection failed — check backend is running");
    };
    ws.onclose = () => {
      if (status === "running") setStatus("done");
    };

    return () => { ws.close(); };
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const critical = findings.filter((f) => f.severity >= 9).length;
  const high = findings.filter((f) => f.severity >= 7 && f.severity < 9).length;
  const medium = findings.filter((f) => f.severity >= 4 && f.severity < 7).length;
  const low = findings.filter((f) => f.severity < 4).length;

  const filtered = findings
    .filter((f) => {
      if (filterSeverity === "critical") return f.severity >= 9;
      if (filterSeverity === "high") return f.severity >= 7 && f.severity < 9;
      if (filterSeverity === "medium") return f.severity >= 4 && f.severity < 7;
      if (filterSeverity === "low") return f.severity < 4;
      return true;
    })
    .sort((a, b) => b.severity - a.severity);

  function downloadReport() {
    const report = {
      scan_id: id,
      generated_at: new Date().toISOString(),
      total_findings: findings.length,
      summary: { critical, high, medium, low },
      findings: findings.sort((a, b) => b.severity - a.severity),
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `scan-report-${id?.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <Link href="/" className="text-gray-400 hover:text-gray-900 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Shield className="w-5 h-5 text-emerald-500" />
          <div className="flex-1">
            <h1 className="font-semibold text-gray-900 text-sm">Scan Results</h1>
            <p className="text-xs text-gray-400 font-mono">{id}</p>
          </div>
          <div className="flex items-center gap-3">
            {status === "done" && findings.length > 0 && (
              <button
                onClick={downloadReport}
                className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Download className="w-4 h-4" />
                Export JSON
              </button>
            )}
            <div className="flex items-center gap-1.5">
              {status === "connecting" && <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />}
              {status === "running" && <Loader2 className="w-4 h-4 text-emerald-500 animate-spin" />}
              {status === "done" && <CheckCircle className="w-4 h-4 text-emerald-500" />}
              {status === "error" && <XCircle className="w-4 h-4 text-red-500" />}
              <span className="text-sm text-gray-600 capitalize">{status}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Progress bar */}
        {(status === "connecting" || status === "running") && (
          <ScanProgress stage={stage} progress={progress} />
        )}

        {/* Error */}
        {status === "error" && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-800">Scan failed</p>
              <p className="text-sm text-red-600 mt-0.5">{errorMsg}</p>
            </div>
          </div>
        )}

        {/* No findings */}
        {status === "done" && findings.length === 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-16 text-center">
            <CheckCircle className="w-14 h-14 text-emerald-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No vulnerabilities found</h2>
            <p className="text-gray-500 text-sm">
              The scanned code passed all OWASP Top 10 checks.
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-2 mt-6 text-sm text-emerald-600 hover:underline"
            >
              ← Scan another file
            </Link>
          </div>
        )}

        {/* Summary cards */}
        {findings.length > 0 && (
          <SeveritySummary critical={critical} high={high} medium={medium} low={low} />
        )}

        {/* OWASP breakdown chart */}
        {findings.length > 1 && <OWASPBreakdown findings={findings} />}

        {/* Filter */}
        {findings.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Filter:</span>
            {["all", "critical", "high", "medium", "low"].map((f) => (
              <button
                key={f}
                onClick={() => setFilterSeverity(f)}
                className={`text-xs px-3 py-1 rounded-full border font-medium capitalize transition-colors ${
                  filterSeverity === f
                    ? "bg-gray-900 text-white border-gray-900"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
                }`}
              >
                {f === "all" ? `All (${findings.length})` : f}
              </button>
            ))}
          </div>
        )}

        {/* Findings list */}
        <div className="space-y-4">
          {filtered.map((f) => (
            <FindingCard key={f.id} finding={f} />
          ))}
        </div>

        {filtered.length === 0 && findings.length > 0 && (
          <div className="text-center text-gray-400 py-8 text-sm">
            No findings match the selected filter.
          </div>
        )}
      </div>
    </div>
  );
}
