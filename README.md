# GeneWeave

**Multi-database gene annotation** — weave together NCBI, Ensembl, UniProt, STRING, ProSite, Pfam, PDB, KEGG, and Gene Ontology into a single report.

## Project layout

```text
geneweave/
├── annotation/              # Core Python package
│   ├── cli.py               # Command-line orchestration
│   ├── gui.py               # Tkinter interface
│   ├── config.py            # Paths and settings
│   ├── cache.py             # Local gene cache
│   ├── export.py            # CSV, Excel, JSON export
│   ├── summary.py           # Coverage reports
│   ├── paths.py             # Output path helpers
│   ├── databases/           # API clients (NCBI, Ensembl, …)
│   └── templates/           # HTML table templates
├── viewer/                  # Flask web viewer
│   ├── app.py
│   └── templates/
├── packaging/               # PyInstaller spec (desktop builds)
├── scripts/                 # build_linux.sh / build_windows.bat
├── data/                    # Sample input files
├── docs/                    # Quarto documentation
├── results/                 # Default output directory
├── main.py                  # CLI entry point
├── viewer.py                # Viewer entry point
├── interface.py             # GUI entry point
└── pyproject.toml
```

## Databases queried

NCBI, Ensembl, UniProt, STRING, ProSite, Pfam, PDB, KEGG, Gene Ontology

## Installation

```bash
pip install -r requirements.txt
# or editable install:
pip install -e .

sudo apt install python3-tk   # for the GUI
```

## Input format

```text
# Comments are supported with #
RAD51,homo_sapiens
DMD,mus_musculus
PHYB,arabidopsis_thaliana
```

Sample file: `data/GeneSymbols_2.txt`

## Command line

```bash
# HTML + CSV + summary report in results/ (default)
python3 main.py data/GeneSymbols_2.txt
# or
python3 -m annotation data/GeneSymbols_2.txt

# Also generate Excel and JSON
python3 main.py data/GeneSymbols_2.txt --excel --json

# Single gene (no input file needed)
python3 main.py --gene RAD51,homo_sapiens

# Quick test on first 3 genes
python3 main.py data/GeneSymbols_2.txt --limit 3

# Validate input without API calls
python3 main.py data/GeneSymbols_2.txt --dry-run

# Show cache statistics
python3 main.py --cache-info

# Custom output folder
python3 main.py data/GeneSymbols_2.txt --output-dir ./my_run

# Open web viewer when finished
python3 main.py data/GeneSymbols_2.txt --serve

# Parallel processing (watch API rate limits)
python3 main.py data/GeneSymbols_2.txt --workers 2

# Force fresh annotation
python3 main.py data/GeneSymbols_2.txt --no-cache --clear-cache

# Verbose logs and log file
python3 main.py data/GeneSymbols_2.txt -v --log-file results/run.log
```

## Local web viewer

```bash
python3 viewer.py --open
```

Opens `http://127.0.0.1:5000` in your browser.

Options: `--port 8080`, `--dir /path/to/results`

## GUI

```bash
python3 interface.py
```

## Generated files

All outputs are written to `results/` by default (or `--output-dir`):

| File | Description |
|---|---|
| `*_annotation.html` | Interactive table with coverage report |
| `*_annotation.csv` | Text export (Excel-compatible, `;` separator) |
| `*_annotation.xlsx` | Formatted Excel export (with `--excel`) |
| `*_annotation.json` | Structured export (with `--json`) |
| `*_manifest.json` | Run metadata (timestamp, duration, outputs) |
| `*_summary.txt` | Coverage statistics by column |
| `.cache/gene_annotations.json` | Local cache |

## Configuration

```bash
export NCBI_EMAIL="your.email@domain.com"   # required by NCBI
export NCBI_DELAY=0.34                         # seconds between NCBI calls
export ANNOTATION_WORKERS=2                    # default parallelism
export ANNOTATION_HTTP_TIMEOUT=60              # API read timeout (seconds)
export ANNOTATION_HTTP_RETRIES=3               # retries on timeout / connection errors
```

## Documentation (Quarto)

### Online (GitHub Pages)

After pushing to GitHub and enabling **Pages → GitHub Actions**, docs are available at:

```text
https://mohamadysn.github.io/geneweave/
```

See [GITHUB.md](GITHUB.md) for setup steps.

### Local (HTTP)

Preview with live reload — opens `http://127.0.0.1:8088` in your default browser:

```bash
python3 docs/render.py
```

Build static site and serve over HTTP:

```bash
python3 docs/render.py --build --serve
```

Requires [Quarto](https://quarto.org).

## Desktop builds (Linux / Windows)

Standalone binaries (no Python install required) are produced with PyInstaller.

### Build locally

**Linux**

```bash
bash scripts/build_linux.sh
```

Produces `dist/GeneWeave`, `dist/geneweave-cli`, `dist/geneweave-viewer`, and
`dist/GeneWeave-<version>-linux.tar.gz`.

**Windows** (from Command Prompt or PowerShell)

```bat
scripts\build_windows.bat
```

Produces `dist\GeneWeave.exe`, `dist\geneweave-cli.exe`, `dist\geneweave-viewer.exe`, and
`dist\GeneWeave-<version>-windows.zip`.

### Run the packaged app

| Binary | Role |
|--------|------|
| `GeneWeave` / `GeneWeave.exe` | Desktop GUI |
| `geneweave-cli` | Command-line annotation |
| `geneweave-viewer` | Local web viewer |

Results and cache are written next to the binary (`results/`, `.cache/`) for portable builds,
or under `~/.local/share/geneweave/` for a system `.deb` install.
Internet access is required to query the annotation APIs.
Database ID links in the HTML report open in a **new browser tab**.

### Debian package (Ubuntu / Debian)

```bash
bash scripts/build_linux.sh
bash scripts/build_deb.sh
sudo apt install ./dist/geneweave_1.1.0_amd64.deb
```

Provides `geneweave-gui` (also in the Softwares menu), `geneweave`, and `geneweave-viewer`.

### CI / GitHub Release

Push a version tag (e.g. `v1.1.0`) or run the **Build desktop binaries** workflow
manually. Artifacts for Linux and Windows are uploaded; tagged pushes also create a
GitHub Release with the archives attached.

## Notes

- `--workers 2` speeds up processing but may trigger API rate limits (especially NCBI).
- NCBI rate limiting uses a delay between calls (`NCBI_DELAY`, default 0.34 s).
- The cache makes re-runs nearly instant for already annotated genes.
- `No data found` is normal for poorly documented organisms.
