#!/usr/bin/python3
#-*- coding: utf-8 -*-

from annotation.export import COLUMN_HEADERS, cell_to_text

_NO_DATA = "No data found"


def _cell_has_data(cell):
    return cell_to_text(cell) != _NO_DATA


def compute_summary(infos, meta=None):
    if not infos:
        summary = {
            "total_genes": 0,
            "complete_genes": 0,
            "coverage_percent": 0.0,
            "columns": [],
            "errors": [],
            "cached": 0,
            "annotated": 0,
            "duration_seconds": 0.0,
        }
        if meta:
            summary.update(meta)
        return summary

    column_stats = []
    complete_genes = 0
    filled_cells = 0
    total_cells = len(infos) * len(COLUMN_HEADERS)

    for col_index, header in enumerate(COLUMN_HEADERS):
        count = sum(1 for row in infos if _cell_has_data(row[col_index]))
        column_stats.append({
            "name": header,
            "filled": count,
            "total": len(infos),
            "percent": round(100 * count / len(infos), 1),
        })

    for row in infos:
        gene_filled = sum(1 for cell in row if _cell_has_data(cell))
        filled_cells += gene_filled
        if gene_filled == len(COLUMN_HEADERS):
            complete_genes += 1

    summary = {
        "total_genes": len(infos),
        "complete_genes": complete_genes,
        "coverage_percent": round(100 * filled_cells / total_cells, 1),
        "columns": column_stats,
        "errors": [],
        "cached": 0,
        "annotated": 0,
        "duration_seconds": 0.0,
    }
    if meta:
        summary.update(meta)
    return summary


def format_summary_text(summary):
    lines = [
        "=== Annotation Report ===",
        f"Genes analyzed      : {summary['total_genes']}",
        f"Complete genes      : {summary['complete_genes']}",
        f"Overall coverage    : {summary['coverage_percent']}%",
    ]
    if summary.get("cached") or summary.get("annotated"):
        lines.append(
            f"From cache / fetched : {summary.get('cached', 0)} / {summary.get('annotated', 0)}"
        )
    if summary.get("duration_seconds"):
        lines.append(f"Duration            : {summary['duration_seconds']}s")
    if summary.get("errors"):
        lines.extend(["", f"Failed genes ({len(summary['errors'])}):"])
        for item in summary["errors"]:
            lines.append(f"  - {item['gene']},{item['organism']}: {item['error']}")
    lines.extend(["", "Coverage by column:"])
    for col in summary["columns"]:
        lines.append(
            f"  - {col['name']}: {col['filled']}/{col['total']} ({col['percent']}%)"
        )
    return "\n".join(lines)


def format_summary_html(summary):
    extra = ""
    if summary.get("cached") or summary.get("annotated"):
        extra += (
            f" | <strong>Cache:</strong> {summary.get('cached', 0)}"
            f" | <strong>Fetched:</strong> {summary.get('annotated', 0)}"
        )
    if summary.get("duration_seconds"):
        extra += f" | <strong>Duration:</strong> {summary['duration_seconds']}s"

    error_block = ""
    if summary.get("errors"):
        error_rows = "".join(
            f"<tr><td>{item['gene']},{item['organism']}</td>"
            f"<td>{item['error']}</td></tr>"
            for item in summary["errors"]
        )
        error_block = f"""
  <h3>Failed genes ({len(summary['errors'])})</h3>
  <table class="summary-table">
    <thead><tr><th>Gene</th><th>Error</th></tr></thead>
    <tbody>{error_rows}</tbody>
  </table>"""

    rows = "".join(
        f"<tr><td>{col['name']}</td><td>{col['filled']}/{col['total']}</td>"
        f"<td>{col['percent']}%</td></tr>"
        for col in summary["columns"]
    )
    return f"""
<div class="summary-box">
  <h2>Annotation Report</h2>
  <p><strong>Genes analyzed:</strong> {summary['total_genes']} |
     <strong>Complete genes:</strong> {summary['complete_genes']} |
     <strong>Coverage:</strong> {summary['coverage_percent']}%{extra}</p>
  {error_block}
  <table class="summary-table">
    <thead><tr><th>Column</th><th>Filled</th><th>%</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<style>
.summary-box {{ margin: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
.summary-table {{ border-collapse: collapse; width: 100%; max-width: 800px; margin-top: 12px; }}
.summary-table th, .summary-table td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
.summary-table th {{ background: #e9ecef; }}
</style>
"""
