"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Finding } from "@/types";

interface Props {
  findings: Finding[];
}

const COLORS: Record<string, string> = {
  "A01:2021": "#3b82f6",
  "A02:2021": "#8b5cf6",
  "A03:2021": "#ef4444",
  "A04:2021": "#f97316",
  "A05:2021": "#eab308",
  "A06:2021": "#06b6d4",
  "A07:2021": "#ec4899",
  "A08:2021": "#14b8a6",
  "A09:2021": "#84cc16",
  "A10:2021": "#f59e0b",
};

function getColor(category: string): string {
  const key = Object.keys(COLORS).find((k) => category.startsWith(k));
  return key ? COLORS[key] : "#94a3b8";
}

export default function OWASPBreakdown({ findings }: Props) {
  const counts: Record<string, number> = {};
  for (const f of findings) {
    const label = f.owasp_category.split(" – ")[0] ?? f.owasp_category;
    counts[label] = (counts[label] ?? 0) + 1;
  }

  const data = Object.entries(counts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  if (data.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 px-5 py-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Findings by OWASP Category</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical" margin={{ left: 16, right: 16 }}>
          <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
          <Tooltip
            formatter={(value: number) => [`${value} finding${value !== 1 ? "s" : ""}`, ""]}
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={getColor(entry.name)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
