from __future__ import annotations

import io
import logging
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services import quality_checks as qc

logger = logging.getLogger(__name__)


def _fig_to_image(fig) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=6 * inch, height=3 * inch)


def _missingness_chart(profile: dict) -> Image:
    cols = [c["name"] for c in profile["columns"]]
    pcts = [c.get("missing_pct", 0.0) * 100 for c in profile["columns"]]
    fig, ax = plt.subplots()
    ax.bar(range(len(cols)), pcts, color="#c0392b")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=90, fontsize=6)
    ax.set_ylabel("% missing")
    ax.set_title("Missingness by column")
    return _fig_to_image(fig)


def _histogram_chart(df, column: str) -> Image:
    from app.services.chart_aggregator import numeric_histogram

    h = numeric_histogram(df, column)
    if h.get("omitted"):
        return None
    edges = h["bins"]
    counts = h["counts"]
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
    fig, ax = plt.subplots()
    ax.bar(centers, counts, width=(edges[1] - edges[0]) * 0.9, color="#2980b9")
    ax.set_title(f"Histogram: {column}")
    ax.set_xlabel(column)
    ax.set_ylabel("count")
    return _fig_to_image(fig)


def generate_report_pdf(
    original_filename: str,
    profile: dict,
    insights: dict | None,
    diff: dict | None,
    df=None,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title = ParagraphStyle("title", parent=styles["Title"], fontSize=20)
    story.append(Paragraph("DataSentry — Dataset Report", title))
    story.append(Paragraph(f"File: {original_filename}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {datetime.now(timezone.utc).isoformat()}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Overview
    story.append(Paragraph("1. Dataset Overview", styles["Heading2"]))
    overview = [
        ["Rows", str(profile.get("row_count"))],
        ["Columns", str(profile.get("column_count"))],
        ["Size (bytes)", str(profile.get("byte_size"))],
        ["Exact duplicate rows", str(profile.get("duplicate_row_count"))],
    ]
    t = Table(overview, hAlign="LEFT")
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(t)
    story.append(Spacer(1, 12))

    # EDA summary chart
    story.append(Paragraph("2. EDA Summary", styles["Heading2"]))
    story.append(_missingness_chart(profile))
    story.append(Spacer(1, 8))
    if df is not None:
        numeric_cols = [c["name"] for c in profile["columns"] if c.get("is_numeric")][:3]
        for col in numeric_cols:
            img = _histogram_chart(df, col)
            if img:
                story.append(img)
                story.append(Spacer(1, 6))

    # Data quality findings
    story.append(Paragraph("3. Data Quality Findings", styles["Heading2"]))
    rows = [["Column", "Dtype", "Missing %", "Outliers", "High missing"]]
    for c in profile["columns"]:
        rows.append([
            c["name"],
            c.get("dtype", ""),
            f"{c.get('missing_pct', 0.0)*100:.1f}",
            str(c.get("outlier_count", 0)),
            "YES" if c.get("high_missing") else "",
        ])
    qt = Table(rows, hAlign="LEFT", repeatRows=1)
    qt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]))
    story.append(qt)
    story.append(Spacer(1, 12))

    # AI insights
    if insights:
        story.append(Paragraph("4. AI Insights & Risks", styles["Heading2"]))
        risks = insights.get("risks_and_assumptions", [])
        if risks:
            story.append(ListFlowable(
                [ListItem(Paragraph(str(r), styles["Normal"])) for r in risks],
                bulletType="bullet",
            ))
        targets = insights.get("candidate_targets", [])
        if targets:
            story.append(Paragraph("Candidate target variables: " + ", ".join(map(str, targets)), styles["Normal"]))
        story.append(Spacer(1, 12))

    # Cleaning / diff
    if diff:
        story.append(Paragraph("5. Applied Cleaning", styles["Heading2"]))
        crows = [
            ["Rows before", str(diff.get("row_count_before"))],
            ["Rows after", str(diff.get("row_count_after"))],
            ["Row change", str(diff.get("row_count_change"))],
        ]
        ct = Table(crows, hAlign="LEFT")
        ct.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        story.append(ct)
        story.append(Spacer(1, 8))
        mrows = [["Column", "Missing % before", "Missing % after"]]
        for m in diff.get("per_column_missing", []):
            mrows.append([
                m["column"],
                f"{m['missing_pct_before']*100:.1f}",
                f"{m['missing_pct_after']*100:.1f}",
            ])
        mt = Table(mrows, hAlign="LEFT", repeatRows=1)
        mt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                                ("FONTSIZE", (0, 0), (-1, -1), 7)]))
        story.append(mt)

    doc.build(story)
    return buf.getvalue()
