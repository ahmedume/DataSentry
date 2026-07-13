"use client";

import { useEffect, useState } from "react";
import { getDataset, DatasetOut } from "@/lib/api";

export function useJobPoller(datasetId: string) {
  const [dataset, setDataset] = useState<DatasetOut | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    const tick = async () => {
      try {
        const d = await getDataset(datasetId);
        if (!active) return;
        setDataset(d);
        if (d.status === "READY") setReady(true);
        if (d.status === "FAILED") {
          setFailed(true);
          setReady(true);
        }
      } catch {
        /* ignore transient */
      }
    };
    tick();
    const iv = setInterval(tick, 2000);
    return () => {
      active = false;
      clearInterval(iv);
    };
  }, [datasetId]);

  return { dataset, ready, failed };
}
