#!/usr/bin/env bash
# Build GeneWeave standalone binaries for Linux.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi
DIST_DIR="${DIST_DIR:-$ROOT/dist}"
BUILD_DIR="${BUILD_DIR:-$ROOT/build}"

echo "==> Installing build dependencies"
"$PYTHON" -m pip install -q -r requirements.txt -r requirements-build.txt

echo "==> Cleaning previous build"
rm -rf "$BUILD_DIR" "$DIST_DIR"/GeneWeave "$DIST_DIR"/geneweave-cli "$DIST_DIR"/geneweave-viewer
rm -f "$DIST_DIR"/GeneWeave "$DIST_DIR"/geneweave-cli "$DIST_DIR"/geneweave-viewer
rm -f "$DIST_DIR"/GeneWeave-*-linux.tar.gz

echo "==> Running PyInstaller"
"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath "$DIST_DIR" \
  --workpath "$BUILD_DIR" \
  packaging/geneweave.spec

VERSION="$("$PYTHON" -c "from annotation.config import VERSION; print(VERSION)")"
ARCHIVE="$DIST_DIR/GeneWeave-${VERSION}-linux.tar.gz"

echo "==> Packaging $ARCHIVE"
tar -C "$DIST_DIR" -czf "$ARCHIVE" GeneWeave geneweave-cli geneweave-viewer

echo ""
echo "Build complete."
echo "  GUI    : $DIST_DIR/GeneWeave"
echo "  CLI    : $DIST_DIR/geneweave-cli"
echo "  Viewer : $DIST_DIR/geneweave-viewer"
echo "  Archive: $ARCHIVE"
