"use client";

import DatasetListPanel from "@/components/DatasetListPanel";
import RequireAuth from "@/components/RequireAuth";
import Nav from "@/components/Nav";

export default function DatasetsPage() {
  return (
    <RequireAuth>
      <main className="shell">
        <Nav />
        <div className="wrap dash">
          <span className="eyebrow">Datasets</span>
          <h1 className="section-title">All uploaded datasets</h1>
          <DatasetListPanel />
        </div>
      </main>
    </RequireAuth>
  );
}
