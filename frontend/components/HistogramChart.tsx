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
import { NumericHistogram } from "@/lib/types";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function HistogramChart({ data }: { data: NumericHistogram }) {
  if (data.omitted) return <p className="text-sm text-slate-500">Chart omitted (non-numeric column).</p>;
  const labels = data.bins.slice(0, -1).map((b, i) => `${b}–${data.bins[i + 1]}`);
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h4 className="mb-2 text-sm font-semibold">{data.column}</h4>
      <Bar
        data={{
          labels,
          datasets: [{ label: "count", data: data.counts, backgroundColor: "#2980b9" }],
        }}
        options={{ plugins: { legend: { display: false } } }}
      />
    </div>
  );
}
