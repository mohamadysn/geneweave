#!/usr/bin/python3
#-*- coding: utf-8 -*-

import argparse
import re
import webbrowser
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, render_template, send_from_directory

from annotation.config import DEFAULT_OUTPUT_DIR, APP_NAME, VIEWER_TEMPLATES_DIR, IS_FROZEN

app = Flask(__name__, template_folder=str(VIEWER_TEMPLATES_DIR))
RESULTS_DIR = DEFAULT_OUTPUT_DIR


def _parse_summary_line(line, data):
    line = line.strip()
    if re.match(r"Genes anal", line, re.I):
        data["total_genes"] = int(re.search(r":\s*(\d+)", line).group(1))
    elif re.match(r"Genes compl", line, re.I) or re.match(r"Complete genes", line, re.I):
        data["complete_genes"] = int(re.search(r":\s*(\d+)", line).group(1))
    elif "Couverture globale" in line or "Overall coverage" in line:
        data["coverage_percent"] = float(re.search(r":\s*([\d.]+)", line).group(1))
    elif line.startswith("  - "):
        match = re.match(r"\s*- (.+): (\d+)/(\d+) \(([\d.]+)%\)", line)
        if match:
            data["columns"].append({
                "name": match.group(1),
                "filled": int(match.group(2)),
                "total": int(match.group(3)),
                "percent": float(match.group(4)),
            })


def parse_summary_file(summary_path):
    if not summary_path.exists():
        return None

    data = {
        "total_genes": 0,
        "complete_genes": 0,
        "coverage_percent": 0.0,
        "columns": [],
    }
    with open(summary_path, "r", encoding="utf-8") as handle:
        for line in handle:
            _parse_summary_line(line, data)
    return data


def discover_results(directory=None):
    directory = Path(directory or RESULTS_DIR)
    results = []

    for html_path in sorted(directory.glob("*_annotation.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        base = html_path.name.replace("_annotation.html", "")
        summary_path = directory / f"{base}_summary.txt"
        csv_path = directory / f"{base}_annotation.csv"
        xlsx_path = directory / f"{base}_annotation.xlsx"
        json_path = directory / f"{base}_annotation.json"

        modified = datetime.fromtimestamp(html_path.stat().st_mtime)
        results.append({
            "name": base,
            "html_file": html_path.name,
            "csv_file": csv_path.name if csv_path.exists() else None,
            "xlsx_file": xlsx_path.name if xlsx_path.exists() else None,
            "json_file": json_path.name if json_path.exists() else None,
            "summary_file": summary_path.name if summary_path.exists() else None,
            "summary": parse_summary_file(summary_path),
            "modified": modified.strftime("%Y-%m-%d %H:%M"),
        })
    return results


@app.route("/")
def index():
    results = discover_results(RESULTS_DIR)
    return render_template("index.html", results=results)


@app.route("/view/<name>")
def view_result(name):
    html_file = f"{name}_annotation.html"
    html_path = RESULTS_DIR / html_file
    if not html_path.exists():
        abort(404)

    summary_path = RESULTS_DIR / f"{name}_summary.txt"
    csv_file = RESULTS_DIR / f"{name}_annotation.csv"
    xlsx_file = RESULTS_DIR / f"{name}_annotation.xlsx"
    json_file = RESULTS_DIR / f"{name}_annotation.json"

    return render_template(
        "view.html",
        name=name,
        html_file=html_file,
        summary=parse_summary_file(summary_path),
        has_csv=csv_file.exists(),
        has_xlsx=xlsx_file.exists(),
        has_json=json_file.exists(),
    )


@app.route("/files/<path:filename>")
def serve_file(filename):
    safe_path = (RESULTS_DIR / filename).resolve()
    if not str(safe_path).startswith(str(RESULTS_DIR.resolve())):
        abort(403)
    if not safe_path.exists():
        abort(404)
    return send_from_directory(RESULTS_DIR, filename)


def build_parser():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} — local web viewer for gene annotations")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--host", default="127.0.0.1", help="Listen address (default: 127.0.0.1)")
    parser.add_argument("--dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory containing results")
    parser.add_argument("--open", action="store_true", help="Open browser automatically")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    return parser


def main():
    global RESULTS_DIR
    parser = build_parser()
    args = parser.parse_args()
    RESULTS_DIR = Path(args.dir).resolve()

    url = f"http://{args.host}:{args.port}/"
    print(f"Viewer  : {url}")
    print(f"Folder  : {RESULTS_DIR}")
    print("Press Ctrl+C to stop")

    if args.open:
        webbrowser.open(url)

    use_reload = not args.no_reload and not IS_FROZEN
    app.run(
        host=args.host,
        port=args.port,
        debug=use_reload,
        use_reloader=use_reload,
    )


if __name__ == "__main__":
    main()
