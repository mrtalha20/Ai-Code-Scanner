export type SeverityLabel = "Critical" | "High" | "Medium" | "Low";

export function severityLabel(score: number): SeverityLabel {
  if (score >= 9) return "Critical";
  if (score >= 7) return "High";
  if (score >= 4) return "Medium";
  return "Low";
}

export function severityColor(score: number): string {
  if (score >= 9) return "text-red-600 bg-red-50 border-red-200";
  if (score >= 7) return "text-orange-600 bg-orange-50 border-orange-200";
  if (score >= 4) return "text-amber-600 bg-amber-50 border-amber-200";
  return "text-green-600 bg-green-50 border-green-200";
}

export function severityRingColor(score: number): string {
  if (score >= 9) return "#dc2626";
  if (score >= 7) return "#ea580c";
  if (score >= 4) return "#d97706";
  return "#16a34a";
}
