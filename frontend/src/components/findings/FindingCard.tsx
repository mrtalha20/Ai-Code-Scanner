"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Finding } from "@/types";
import { severityLabel, severityColor } from "@/lib/severity";

interface Props {
  finding: Finding;
}

export default function FindingCard({ finding }: Props) {
  const [expanded, setExpanded] = useState(false);
  const label = severityLabel(finding.severity);
  const colorClass = severityColor(finding.severity);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      {/* Header */}
      <div
        className="flex items-start gap-4 px-5 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        {/* Severity ring */}
        <div className={`flex-shrink-0 w-12 h-12 rounded-full border-2 flex flex-col items-center justify-center ${colorClass}`}>
          <span className="text-sm font-bold leading-none">{finding.severity}</span>
          <span className="text-[9px] font-medium leading-none">/10</span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${colorClass}`}>
              {label}
            </span>
            <span className="text-xs text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">
              {finding.owasp_category}
            </span>
            {finding.function_name && (
              <span className="text-xs text-blue-600 bg-blue-50 rounded-full px-2 py-0.5 font-mono">
                {finding.function_name}()
              </span>
            )}
            {finding.line_start && (
              <span className="text-xs text-gray-400">Line {finding.line_start}</span>
            )}
          </div>
          <h3 className="font-semibold text-gray-900 truncate">{finding.title}</h3>
          <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">{finding.description}</p>
        </div>

        <div className="flex-shrink-0 text-gray-400">
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </div>

      {/* Expanded diff */}
      {expanded && (
        <div className="border-t border-gray-100 px-5 py-4 space-y-4">
          <p className="text-sm text-gray-700">{finding.description}</p>

          {finding.severity_justification && (
            <div className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
              <strong>Severity: </strong>{finding.severity_justification}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <div className="text-xs font-semibold text-red-600 mb-1.5 uppercase tracking-wide">
                Vulnerable Code
              </div>
              <pre className="bg-red-50 border border-red-100 rounded-lg p-3 text-xs overflow-x-auto text-red-900 whitespace-pre-wrap">
                {finding.vulnerable_code}
              </pre>
            </div>
            <div>
              <div className="text-xs font-semibold text-emerald-600 mb-1.5 uppercase tracking-wide">
                Fixed Code
              </div>
              <pre className="bg-emerald-50 border border-emerald-100 rounded-lg p-3 text-xs overflow-x-auto text-emerald-900 whitespace-pre-wrap">
                {finding.fixed_code}
              </pre>
            </div>
          </div>

          {finding.fix_explanation && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3">
              <p className="text-xs font-semibold text-blue-700 mb-1">What was fixed</p>
              <p className="text-sm text-blue-900">{finding.fix_explanation}</p>
            </div>
          )}

          {finding.diff_summary && (
            <p className="text-xs text-gray-500 italic">{finding.diff_summary}</p>
          )}
        </div>
      )}
    </div>
  );
}
