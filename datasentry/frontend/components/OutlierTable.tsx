import { ColumnProfile } from "@/lib/types";

export default function OutlierTable({ columns }: { columns: ColumnProfile[] }) {
  const rows = columns.filter((c) => (c.outlier_count || 0) > 0 && c.is_numeric);
  if (rows.length === 0)
    return <p className="text-sm text-slate-500">No numeric outliers detected (IQR method).</p>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-slate-500">
          <th className="py-2">Column</th>
          <th>Outlier count</th>
          <th>Q1</th>
          <th>Median</th>
          <th>Q3</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((c) => (
          <tr key={c.name} className="border-b">
            <td className="py-2 font-medium">{c.name}</td>
            <td>{c.outlier_count}</td>
            <td>{c.q1 ?? "—"}</td>
            <td>{c.median ?? "—"}</td>
            <td>{c.q3 ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
