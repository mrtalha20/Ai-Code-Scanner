interface Props {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

const cards = [
  { label: "Critical", key: "critical" as const, color: "text-red-600 bg-red-50 border-red-200" },
  { label: "High", key: "high" as const, color: "text-orange-600 bg-orange-50 border-orange-200" },
  { label: "Medium", key: "medium" as const, color: "text-amber-600 bg-amber-50 border-amber-200" },
  { label: "Low", key: "low" as const, color: "text-green-600 bg-green-50 border-green-200" },
];

export default function SeveritySummary(props: Props) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {cards.map(({ label, key, color }) => (
        <div key={key} className={`rounded-xl border p-4 text-center ${color}`}>
          <div className="text-3xl font-bold">{props[key]}</div>
          <div className="text-sm font-medium mt-1">{label}</div>
        </div>
      ))}
    </div>
  );
}
