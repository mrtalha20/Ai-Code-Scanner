import { Loader2 } from "lucide-react";

interface Props {
  stage: string;
  progress: number;
}

const STAGES = ["Chunking", "Classifying", "Scoring", "Generating fixes"];

export default function ScanProgress({ stage, progress }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-5 py-4">
      <div className="flex items-center gap-3 mb-3">
        <Loader2 className="w-4 h-4 text-emerald-500 animate-spin flex-shrink-0" />
        <span className="text-sm font-medium text-gray-700 capitalize">{stage}</span>
        <span className="ml-auto text-sm text-gray-400">{progress}%</span>
      </div>

      {/* Main progress bar */}
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald-500 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Stage indicators */}
      <div className="flex gap-2 mt-3">
        {STAGES.map((s, i) => {
          const pct = (i / (STAGES.length - 1)) * 100;
          const active = progress >= pct;
          return (
            <div key={s} className="flex-1 text-center">
              <div
                className={`text-xs font-medium transition-colors ${
                  active ? "text-emerald-600" : "text-gray-300"
                }`}
              >
                {s}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
