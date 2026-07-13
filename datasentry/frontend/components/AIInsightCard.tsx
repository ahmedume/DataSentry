import { AiInsightOut } from "@/lib/types";

export default function AIInsightCard({ insight }: { insight: AiInsightOut }) {
  return (
    <div className="space-y-4">
      {!insight.available && (
        <p className="rounded bg-amber-50 p-3 text-sm text-amber-700">
          AI explanation unavailable — profiling data is still shown below.
        </p>
      )}
      <section>
        <h3 className="font-semibold">Column explanations</h3>
        <ul className="list-disc pl-5 text-sm">
          {insight.column_explanations.map((c) => (
            <li key={c.column}>
              <span className="font-medium">{c.column}:</span> {c.explanation}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3 className="font-semibold">Candidate target variables</h3>
        <p className="text-sm">{insight.candidate_targets.join(", ") || "—"}</p>
      </section>
      <section>
        <h3 className="font-semibold">Possible tasks</h3>
        <p className="text-sm">{insight.possible_tasks.join(", ") || "—"}</p>
      </section>
      <section>
        <h3 className="font-semibold">Risks & assumptions</h3>
        <ul className="list-disc pl-5 text-sm">
          {insight.risks_and_assumptions.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </section>
      <p className="text-xs italic text-slate-400">AI-generated suggestions — verify before acting.</p>
    </div>
  );
}
