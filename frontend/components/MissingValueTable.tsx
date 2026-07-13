import { ColumnProfile } from "@/lib/types";

export default function MissingValueTable({ columns }: { columns: ColumnProfile[] }) {
  const rows = columns.filter((c) => c.missing_count > 0);
  if (rows.length === 0)
    return <p className="text-sm text-slate-500">No missing values detected.</p>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-slate-500">
          <th className="py-2">Column</th>
          <th>Missing count</th>
          <th>Missing %</th>
          <th>Flag</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((c) => (
          <tr key={c.name} className="border-b">
            <td className="py-2 font-medium">{c.name}</td>
            <td>{c.missing_count}</td>
            <td>{(c.missing_pct * 100).toFixed(2)}%</td>
            <td>{c.high_missing ? <span className="text-red-600">HIGH</span> : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
