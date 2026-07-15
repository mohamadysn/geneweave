#!/usr/bin/python3
#-*- coding: utf-8 -*-

import argparse
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from annotation.databases.ensembl import *
from annotation.databases.ncbi import *
from annotation.databases.go import *
from annotation.databases.pdb import *
from annotation.databases.kegg import *
from annotation.databases.uniprot import *
from annotation.databases.prosite import *
from annotation.databases.pfam import *
from annotation.databases.string_db import *
from annotation.cache import get_cached_row, set_cached_row, clear_cache, cache_stats
from annotation.export import write_csv, write_excel, write_json, write_manifest, COLUMN_HEADERS
from annotation.summary import compute_summary, format_summary_text, format_summary_html
from annotation.config import (
    DEFAULT_WORKERS,
    MAX_WORKERS,
    TEMPLATES_DIR,
    DEFAULT_OUTPUT_DIR,
    PROJECT_DIR,
    VERSION,
    APP_NAME,
    IS_FROZEN,
)
from annotation.paths import resolve_output_stem

_NO_DATA = "No data found"
HTML_TEMPLATE = TEMPLATES_DIR / "table_head.html"
ORGANISM_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")
logger = logging.getLogger("annotation")


def setup_logging(verbose=False, log_file=None):
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )


def create_link(info, link):
    if info in (_NO_DATA, ["No data found"], []) or link in (_NO_DATA, ["No data found"], []):
        return [_NO_DATA]
    if info == [_NO_DATA] or link == [_NO_DATA]:
        return [_NO_DATA]
    return [
        f'<a href="{link[i]}" target="_blank" rel="noopener noreferrer">{info[i]}</a>'
        for i in range(len(info))
    ]


def _flatten_cell(cell):
    if not isinstance(cell, list):
        return [str(cell)]
    items = []
    for item in cell:
        if isinstance(item, list):
            items.extend(_flatten_cell(item))
        else:
            items.append(str(item))
    return items


def _format_html_cell(cell):
    """Join list cells and force every link to open in a new browser tab."""
    text = "<br>".join(_flatten_cell(cell))
    # Strip any existing target/rel, then force a new tab (viewer uses an iframe).
    text = re.sub(r'\s+target="[^"]*"', "", text, flags=re.IGNORECASE)
    text = re.sub(r'\s+rel="[^"]*"', "", text, flags=re.IGNORECASE)
    return re.sub(
        r"<a(\s+href=\"[^\"]+\")",
        r'<a\1 target="_blank" rel="noopener noreferrer"',
        text,
        flags=re.IGNORECASE,
    )


def empty_row(gene_symbol, organism, error_message=None):
    row = [_NO_DATA] * len(COLUMN_HEADERS)
    label = f"{gene_symbol},{organism}"
    if error_message:
        label += f" (ERROR: {error_message})"
    row[0] = [label]
    return row


def parse_gene_line(line, line_no=1):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "," not in line:
        logger.warning("Line %d skipped (invalid format): %s", line_no, line)
        return None
    gene_symbol, organism = line.split(",", 1)
    gene_symbol = gene_symbol.strip()
    organism = organism.strip()
    if not gene_symbol:
        logger.warning("Line %d skipped (empty gene symbol)", line_no)
        return None
    if not ORGANISM_PATTERN.match(organism.lower()):
        logger.warning(
            "Line %d: unusual organism format '%s' (expected e.g. homo_sapiens)",
            line_no,
            organism,
        )
    return gene_symbol, organism


def parse_gene_string(value):
    parsed = parse_gene_line(value)
    if not parsed:
        raise ValueError("Expected format: GENE,organism (e.g. RAD51,homo_sapiens)")
    return parsed


def parse_gene_file(request_file):
    genes = []
    seen = set()
    with open(request_file, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            parsed = parse_gene_line(line, line_no)
            if not parsed:
                continue
            gene_symbol, organism = parsed
            key = (gene_symbol.upper(), organism.lower())
            if key in seen:
                logger.warning("Duplicate skipped: %s,%s", gene_symbol, organism)
                continue
            seen.add(key)
            genes.append((gene_symbol, organism))
    return genes


def annotate_gene(gene_symbol, organism):
    try:
        ncbi = NCBI_function_call(gene_symbol, organism)
    except Exception as error:
        logger.warning("NCBI failed for %s,%s: %s", gene_symbol, organism, error)
        ncbi = [_NO_DATA, [], ([], []), ([], [])]

    ncbi_gene_ids = ncbi[1] if isinstance(ncbi[1], list) else []
    ncbi_id_link = (
        create_link(ncbi_gene_ids, NCBI_gene_link(ncbi_gene_ids))
        if ncbi_gene_ids else [_NO_DATA]
    )
    try:
        transcript_link = create_link(ncbi[2][0], ncbi[2][1])
        protein_link = create_link(ncbi[3][0], ncbi[3][1])
    except Exception:
        transcript_link = [_NO_DATA]
        protein_link = [_NO_DATA]

    try:
        ensembl = Ensembl_function_calling(gene_symbol, organism)
    except Exception as error:
        logger.warning("Ensembl failed for %s,%s: %s", gene_symbol, organism, error)
        ensembl = [_NO_DATA, _NO_DATA, _NO_DATA, _NO_DATA, _NO_DATA]

    ensembl_gene_id = ensembl[0]
    ensembl_gene_link_html = (
        create_link([ensembl_gene_id], [ensembl_gene_link(ensembl_gene_id, organism)])
        if ensembl_gene_id != _NO_DATA else _NO_DATA
    )

    genome_browser_url = ensembl[3]
    genome_browser_link = (
        create_link(["View genome browser"], [genome_browser_url])
        if genome_browser_url != _NO_DATA else _NO_DATA
    )

    orthologs_url = ensembl[4]
    orthologs_link = (
        create_link(["View orthologs"], [orthologs_url])
        if orthologs_url != _NO_DATA else _NO_DATA
    )

    transcript_list = ensembl[1]
    if transcript_list and transcript_list != _NO_DATA:
        try:
            rna_links, prot_links = RNA_and_protein_links(ensembl_gene_id, organism, transcript_list)
            ensembl_transcript_link = create_link(transcript_list, rna_links)
            ensembl_prot_link = create_link(ensembl[2], prot_links)
        except Exception as error:
            logger.warning("Ensembl links failed for %s,%s: %s", gene_symbol, organism, error)
            ensembl_transcript_link = _NO_DATA
            ensembl_prot_link = _NO_DATA
    else:
        ensembl_transcript_link = _NO_DATA
        ensembl_prot_link = _NO_DATA

    try:
        uniprot_ids = uniprot_ID(ncbi_gene_ids, ensembl_gene_id, gene_symbol, organism)
    except Exception as error:
        logger.warning("UniProt failed for %s,%s: %s", gene_symbol, organism, error)
        uniprot_ids = [_NO_DATA]
    uniprot_url = create_link(uniprot_ids, uniprot_link(uniprot_ids))

    try:
        prosite_ids, prosite_graph_url = scan_prosite(uniprot_ids)
    except Exception as error:
        logger.warning("ProSite failed for %s,%s: %s", gene_symbol, organism, error)
        prosite_ids, prosite_graph_url = _NO_DATA, _NO_DATA
    if prosite_ids != _NO_DATA:
        prosite_link = create_link(prosite_ids, prosite_id_link(prosite_ids))
        prosite_graph_view_link = create_link(["Graphical View"], [prosite_graph_url])
    else:
        prosite_link = [_NO_DATA]
        prosite_graph_view_link = [_NO_DATA]

    try:
        string_ids = string_id(gene_symbol, organism)
        string_url = Network_view(string_ids)
        string_link = create_link(string_ids, string_url[0])
        string_image_url = image_network(string_ids)
        string_message = ["Network view"] if string_ids != [_NO_DATA] else [_NO_DATA]
        string_image = create_link(string_message, string_image_url[0])
    except Exception as error:
        logger.warning("STRING failed for %s,%s: %s", gene_symbol, organism, error)
        string_link = [_NO_DATA]
        string_image = [_NO_DATA]

    try:
        pfam_access = pfam_id(uniprot_ids)
        if pfam_access:
            pfam_links, pfam_views = graphic_view(pfam_access)
            pfam_domain_link = create_link(pfam_access, pfam_links)
            pfam_view_link = create_link(["Graphical view"] * len(pfam_access), pfam_views)
        else:
            pfam_domain_link = [_NO_DATA]
            pfam_view_link = [_NO_DATA]
    except Exception as error:
        logger.warning("Pfam failed for %s,%s: %s", gene_symbol, organism, error)
        pfam_domain_link = [_NO_DATA]
        pfam_view_link = [_NO_DATA]

    try:
        pdb_names, pdb_urls = PDB_infos(gene_symbol, organism)
        pdb_link = create_link(pdb_names, pdb_urls)
    except Exception as error:
        logger.warning("PDB failed for %s,%s: %s", gene_symbol, organism, error)
        pdb_link = [_NO_DATA]

    ncbi_gene_id = ncbi_gene_ids[0] if ncbi_gene_ids else None
    try:
        kegg_id, kegg_link, pathways, pathways_link = KEGG_infos(ncbi_gene_id, gene_symbol, organism)
        kegg_id_link = create_link(kegg_id, kegg_link)
        pathways_link_html = create_link(pathways, pathways_link)
    except Exception as error:
        logger.warning("KEGG failed for %s,%s: %s", gene_symbol, organism, error)
        kegg_id_link = [_NO_DATA]
        pathways_link_html = [_NO_DATA]

    try:
        mol_func, bio_proc, cell_comp, bio_links, func_links, cell_links = Quick_GO(uniprot_ids)
        molecular_function_link = create_link(mol_func, func_links)
        biological_process_link = create_link(bio_proc, bio_links)
        cellular_component_link = create_link(cell_comp, cell_links)
    except Exception as error:
        logger.warning("GO failed for %s,%s: %s", gene_symbol, organism, error)
        molecular_function_link = [_NO_DATA]
        biological_process_link = [_NO_DATA]
        cellular_component_link = [_NO_DATA]

    row = [_NO_DATA] * len(COLUMN_HEADERS)
    row[0] = [f"{gene_symbol},{organism}"]
    row[1] = ncbi[0]
    row[2] = ncbi_id_link
    row[3] = transcript_link
    row[4] = protein_link
    row[5] = ensembl_gene_link_html
    row[6] = genome_browser_link
    row[7] = ensembl_transcript_link
    row[8] = ensembl_prot_link
    row[9] = orthologs_link
    row[10] = uniprot_url
    try:
        row[11] = uniprot_name(uniprot_ids)
    except Exception:
        row[11] = [_NO_DATA]
    row[12] = [string_link]
    row[13] = [string_image]
    row[14] = prosite_link
    row[15] = prosite_graph_view_link
    row[16] = pfam_domain_link
    row[17] = pfam_view_link
    row[18] = [pdb_link]
    row[19] = [kegg_id_link]
    row[20] = [pathways_link_html]
    row[21] = [molecular_function_link]
    row[22] = [cellular_component_link]
    row[23] = [biological_process_link]
    return row


def _annotate_one(gene_symbol, organism, use_cache):
    label = f"{gene_symbol},{organism}"
    if use_cache:
        cached = get_cached_row(gene_symbol, organism)
        if cached:
            logger.info("Cache: %s", label)
            return gene_symbol, organism, cached, None, True

    logger.info("Annotation: %s", label)
    try:
        row = annotate_gene(gene_symbol, organism)
        if use_cache:
            set_cached_row(gene_symbol, organism, row)
        return gene_symbol, organism, row, None, False
    except Exception as error:
        logger.error("Failed %s: %s", label, error)
        return gene_symbol, organism, empty_row(gene_symbol, organism, str(error)), str(error), False


def annotate_genes(genes, use_cache=True, workers=1):
    if not genes:
        return [], {"errors": [], "cached": 0, "annotated": 0, "duration_seconds": 0.0}

    workers = max(1, min(workers, MAX_WORKERS, len(genes)))
    results = {}
    errors = []
    cached_count = 0
    annotated_count = 0
    started = time.monotonic()

    try:
        from tqdm import tqdm
        progress = tqdm(total=len(genes), desc="Annotation", unit="gene")
    except ImportError:
        progress = None

    def store(gene_symbol, organism, row, error, from_cache):
        nonlocal cached_count, annotated_count
        results[(gene_symbol, organism)] = row
        if error:
            errors.append({"gene": gene_symbol, "organism": organism, "error": error})
        elif from_cache:
            cached_count += 1
        else:
            annotated_count += 1
        if progress:
            progress.update(1)

    if workers == 1:
        for gene_symbol, organism in genes:
            store(*_annotate_one(gene_symbol, organism, use_cache))
    else:
        logger.info("Parallel mode: %d workers", workers)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_annotate_one, gene, org, use_cache): (gene, org)
                for gene, org in genes
            }
            for future in as_completed(futures):
                store(*future.result())

    if progress:
        progress.close()

    rows = [results[(gene, org)] for gene, org in genes]
    stats = {
        "errors": errors,
        "cached": cached_count,
        "annotated": annotated_count,
        "duration_seconds": round(time.monotonic() - started, 1),
    }
    return rows, stats


def write_html(infos, html_path, summary=None):
    logger.info("Creating %s", html_path)
    Path(html_path).parent.mkdir(parents=True, exist_ok=True)

    with open(HTML_TEMPLATE, "r", encoding="utf-8") as template:
        header = template.read()

    if os.path.exists(html_path):
        os.remove(html_path)

    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(header)
        handle.write("<tbody>\n")
        for row in infos:
            handle.write("\t<tr>\n")
            for col_index, cell in enumerate(row):
                if col_index == 0:
                    css_class = "white"
                elif col_index <= 4:
                    css_class = "ncbi"
                elif col_index <= 9:
                    css_class = "ensembl"
                elif col_index <= 11:
                    css_class = "uniprot"
                elif col_index <= 13:
                    css_class = "string"
                elif col_index <= 15:
                    css_class = "prosite"
                elif col_index <= 17:
                    css_class = "pfam"
                elif col_index == 18:
                    css_class = "pdb"
                elif col_index <= 20:
                    css_class = "kegg"
                else:
                    css_class = "go"

                handle.write(f"\t\t<td class='{css_class}'><div class='scroll'>")
                handle.write(_format_html_cell(cell))
                handle.write("</div></td>")
            handle.write("\n\t</tr>\n")
        handle.write("</table>\n")
        if summary:
            handle.write(format_summary_html(summary))
        handle.write("</html>")
    return html_path


def write_summary_file(summary, summary_path):
    Path(summary_path).parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as handle:
        handle.write(format_summary_text(summary))
    logger.info("Creating %s", summary_path)
    return summary_path


def export_results(
    infos,
    summary,
    input_file=None,
    output_stem=None,
    output_dir=None,
    export_html=True,
    export_csv=True,
    export_excel=False,
    export_json=False,
    metadata=None,
):
    if output_stem is None:
        output_stem = resolve_output_stem(input_file, output_dir)
    paths = {
        "stem": output_stem,
        "html": f"{output_stem}_annotation.html",
        "csv": f"{output_stem}_annotation.csv",
        "xlsx": f"{output_stem}_annotation.xlsx",
        "json": f"{output_stem}_annotation.json",
        "summary": f"{output_stem}_summary.txt",
        "manifest": f"{output_stem}_manifest.json",
    }

    if export_html:
        write_html(infos, paths["html"], summary=summary)
    if export_csv:
        write_csv(infos, paths["csv"])
        logger.info("Creating %s", paths["csv"])
    if export_excel:
        write_excel(infos, paths["xlsx"])
        logger.info("Creating %s", paths["xlsx"])
    if export_json:
        write_json(infos, paths["json"], summary=summary, metadata=metadata)
        logger.info("Creating %s", paths["json"])
    if summary:
        write_summary_file(summary, paths["summary"])
    if metadata:
        write_manifest(paths["manifest"], paths, summary, metadata)
        logger.info("Creating %s", paths["manifest"])
    return paths


def launch_viewer(output_dir=None, host="127.0.0.1", port=5000):
    target = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    target.mkdir(parents=True, exist_ok=True)

    if IS_FROZEN:
        _launch_viewer_embedded(target, host=host, port=port)
        return

    import subprocess

    cmd = [
        sys.executable,
        str(PROJECT_DIR / "viewer.py"),
        "--dir",
        str(target),
        "--open",
        "--no-reload",
    ]
    subprocess.Popen(cmd, cwd=PROJECT_DIR)
    logger.info("Web viewer started (folder: %s)", target)


def _launch_viewer_embedded(target, host="127.0.0.1", port=5000):
    """Start the Flask viewer in-process (used by frozen binaries)."""
    import threading
    import webbrowser

    from viewer import app as viewer_mod

    viewer_mod.RESULTS_DIR = target.resolve()
    url = f"http://{host}:{port}/"

    def run():
        viewer_mod.app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
        )

    threading.Thread(target=run, daemon=True).start()
    webbrowser.open(url)
    logger.info("Web viewer started at %s (folder: %s)", url, target)


def run_annotation(
    genes,
    input_file=None,
    output_stem=None,
    use_cache=True,
    export_html=True,
    export_csv=True,
    export_excel=False,
    export_json=False,
    output_dir=None,
    serve=False,
    workers=DEFAULT_WORKERS,
):
    if not genes:
        logger.error("No valid genes to annotate.")
        return []

    logger.info("%d gene(s) to annotate", len(genes))
    infos, stats = annotate_genes(genes, use_cache=use_cache, workers=workers)
    metadata = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_file": str(input_file) if input_file else None,
        "gene_count": len(genes),
    }
    summary = compute_summary(infos, meta=stats)
    print(format_summary_text(summary))

    paths = export_results(
        infos,
        summary,
        input_file=input_file,
        output_stem=output_stem,
        output_dir=output_dir,
        export_html=export_html,
        export_csv=export_csv,
        export_excel=export_excel,
        export_json=export_json,
        metadata=metadata,
    )
    logger.info("Output folder: %s", Path(paths["stem"]).parent)

    if serve:
        launch_viewer(output_dir or DEFAULT_OUTPUT_DIR)

    logger.info("Done")
    return infos


def read_request_file(
    request_file,
    use_cache=True,
    export_html=True,
    export_csv=True,
    export_excel=False,
    export_json=False,
    output_dir=None,
    serve=False,
    workers=DEFAULT_WORKERS,
    limit=None,
):
    genes = parse_gene_file(request_file)
    if limit:
        genes = genes[:limit]
    return run_annotation(
        genes,
        input_file=request_file,
        use_cache=use_cache,
        export_html=export_html,
        export_csv=export_csv,
        export_excel=export_excel,
        export_json=export_json,
        output_dir=output_dir,
        serve=serve,
        workers=workers,
    )


def print_cache_info():
    stats = cache_stats()
    print(f"Cache file : {stats['file']}")
    print(f"Cached genes: {stats['genes']}")
    print(f"Size        : {stats['size_kb']} KB")


def build_parser():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} — multi-database gene annotation (NCBI, Ensembl, UniProt, etc.)"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Text file: GENE,organism per line",
    )
    parser.add_argument(
        "--gene",
        help="Annotate a single gene (e.g. RAD51,homo_sapiens)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N genes (for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List genes without running annotation",
    )
    parser.add_argument(
        "--cache-info",
        action="store_true",
        help="Show cache statistics and exit",
    )
    parser.add_argument("--no-cache", action="store_true", help="Ignore local cache")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cache before running")
    parser.add_argument("--html-only", action="store_true", help="Generate HTML only")
    parser.add_argument("--csv-only", action="store_true", help="Generate CSV only")
    parser.add_argument("--excel", action="store_true", help="Also generate an Excel file (.xlsx)")
    parser.add_argument("--json", action="store_true", help="Also generate a JSON file")
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Open the web viewer when annotation finishes",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Write logs to this file in addition to the console",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Parallel genes (1-{MAX_WORKERS}, default: {DEFAULT_WORKERS})",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logs")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(verbose=args.verbose, log_file=args.log_file)

    if args.cache_info:
        print_cache_info()
        return

    if args.gene:
        genes = [parse_gene_string(args.gene)]
        input_file = None
        output_stem = resolve_output_stem(
            f"{genes[0][0]}_{genes[0][1]}.txt",
            args.output_dir,
        )
    elif args.input_file:
        genes = parse_gene_file(args.input_file)
        input_file = args.input_file
        output_stem = None
    else:
        parser.error("Provide input_file or --gene")

    if args.limit:
        genes = genes[: args.limit]

    if args.dry_run:
        if not genes:
            logger.error("No valid genes found.")
            sys.exit(1)
        print(f"Dry run — {len(genes)} gene(s):")
        for gene_symbol, organism in genes:
            print(f"  {gene_symbol},{organism}")
        return

    if args.clear_cache:
        clear_cache()
        logger.info("Cache cleared.")

    export_html = not args.csv_only
    export_csv = not args.html_only
    export_excel = args.excel
    export_json = args.json

    run_annotation(
        genes,
        input_file=input_file,
        output_stem=output_stem,
        use_cache=not args.no_cache,
        export_html=export_html,
        export_csv=export_csv,
        export_excel=export_excel,
        export_json=export_json,
        output_dir=args.output_dir,
        serve=args.serve,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
