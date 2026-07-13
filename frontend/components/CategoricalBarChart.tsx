"use client";

import { Bar } from "react-chartjs-2";
import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
} from "chart.js";
import { CategoricalBars } from "@/lib/types";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function CategoricalBarChart({ data }: { data: CategoricalBars }) {
  if (data.omitted)
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h4 className="mb-2 text-sm font-semibold">{data.column}</h4>
        <p className="text-sm text-slate-500">{data.reason || "Chart omitted."}</p>
      </div>
    );
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h4 className="mb-2 text-sm font-semibold">{data.column} (top {data.categories.length})</h4>
      <Bar
        data={{
          labels: data.categories,
          datasets: [{ label: "count", data: data.counts, backgroundColor: "#8e44ad" }],
        }}
        options={{ plugins: { legend: { display: false } }, indexAxis: "y" }}
      />
    </div>
  );
}
