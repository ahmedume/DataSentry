"use client";

import { RecommendationOut } from "@/lib/types";

export default function CleaningRecommendationCard({
  rec,
  checked,
  onToggle,
}: {
  rec: RecommendationOut;
  checked: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <label className="flex gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <input type="checkbox" checked={checked} onChange={() => onToggle(rec.id)} className="mt-1" />
      <div className="text-sm">
        <p className="font-medium">
          {rec.column_name ? `${rec.column_name} — ` : ""}
          {rec.issue_type.replace("_", " ")} ({rec.stat_reference})
        </p>
        <p className="text-slate-600">{rec.rationale}</p>
        <p className="mt-1 text-xs text-blue-600">Suggested: {rec.recommendation}</p>
      </div>
    </label>
  );
}
