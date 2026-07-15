#!/usr/bin/env bash
# Build a .deb package from PyInstaller binaries (no fpm/Ruby required).
# Usage:
#   bash scripts/build_linux.sh    # if dist/ binaries are missing
#   bash scripts/build_deb.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DIST_DIR="${DIST_DIR:-$ROOT/dist}"
PKG_ROOT="$DIST_DIR/deb-root"
PKG_NAME="geneweave"

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON="$ROOT/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

VERSION="$("$PYTHON" -c "from annotation.config import VERSION; print(VERSION)")"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
DEB_FILE="$DIST_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"

for bin in GeneWeave geneweave-cli geneweave-viewer; do
  if [[ ! -x "$DIST_DIR/$bin" ]]; then
    echo "Missing $DIST_DIR/$bin — run: bash scripts/build_linux.sh" >&2
    exit 1
  fi
done

if ! command -v dpkg-deb >/dev/null; then
  echo "dpkg-deb not found. Install with: sudo apt install dpkg-dev" >&2
  exit 1
fi

echo "==> Staging Debian package tree"
rm -rf "$PKG_ROOT"
mkdir -p \
  "$PKG_ROOT/DEBIAN" \
  "$PKG_ROOT/opt/geneweave" \
  "$PKG_ROOT/usr/bin" \
  "$PKG_ROOT/usr/share/applications" \
  "$PKG_ROOT/usr/share/doc/geneweave"

install -m 755 "$DIST_DIR/GeneWeave" "$PKG_ROOT/opt/geneweave/GeneWeave"
install -m 755 "$DIST_DIR/geneweave-cli" "$PKG_ROOT/opt/geneweave/geneweave-cli"
install -m 755 "$DIST_DIR/geneweave-viewer" "$PKG_ROOT/opt/geneweave/geneweave-viewer"

cat > "$PKG_ROOT/usr/bin/geneweave" <<'EOF'
#!/bin/sh
exec /opt/geneweave/geneweave-cli "$@"
EOF
cat > "$PKG_ROOT/usr/bin/geneweave-gui" <<'EOF'
#!/bin/sh
exec /opt/geneweave/GeneWeave "$@"
EOF
cat > "$PKG_ROOT/usr/bin/geneweave-viewer" <<'EOF'
#!/bin/sh
exec /opt/geneweave/geneweave-viewer "$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/geneweave" "$PKG_ROOT/usr/bin/geneweave-gui" "$PKG_ROOT/usr/bin/geneweave-viewer"

cat > "$PKG_ROOT/usr/share/applications/geneweave.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=GeneWeave
GenericName=Gene annotation
Comment=Multi-database gene annotation (NCBI, Ensembl, UniProt, …)
Exec=geneweave-gui
Terminal=false
Categories=Science;Biology;Education;
Keywords=gene;annotation;bioinformatics;NGS;
StartupNotify=true
EOF

cat > "$PKG_ROOT/usr/share/doc/geneweave/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: GeneWeave
Source: https://github.com/mohamadysn/geneweave

Files: *
Copyright: GeneWeave contributors
License: permissive project license — see upstream repository
EOF

gzip -9 -c > "$PKG_ROOT/usr/share/doc/geneweave/changelog.Debian.gz" <<EOF
geneweave (${VERSION}) unstable; urgency=low

  * Packaged standalone GeneWeave binaries for Debian/Ubuntu.

 -- GeneWeave maintainers <noreply@example.com>  $(date -R)
EOF

# Installed size in KiB
INSTALLED_SIZE="$(du -sk "$PKG_ROOT/opt" "$PKG_ROOT/usr" | awk '{s+=$1} END {print s}')"

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: science
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Maintainer: GeneWeave maintainers <noreply@example.com>
Homepage: https://github.com/mohamadysn/geneweave
Description: Multi-database gene annotation toolkit
 GeneWeave queries NCBI, Ensembl, UniProt, STRING, ProSite, Pfam, PDB,
 KEGG and Gene Ontology to produce unified annotation reports
 (HTML, CSV, Excel, JSON) with a desktop GUI and local web viewer.
EOF

echo "==> Building $DEB_FILE"
rm -f "$DEB_FILE"
if command -v fakeroot >/dev/null; then
  fakeroot dpkg-deb --build "$PKG_ROOT" "$DEB_FILE"
else
  dpkg-deb --build "$PKG_ROOT" "$DEB_FILE"
fi

echo ""
echo "Debian package ready:"
echo "  $DEB_FILE"
echo ""
echo "Install with:"
echo "  sudo apt install ./$(basename "$DEB_FILE")"
echo "  # or: sudo dpkg -i ./$(basename "$DEB_FILE")"
echo ""
echo "After install:"
echo "  geneweave-gui          # desktop app (also in the Softwares menu)"
echo "  geneweave …            # CLI"
echo "  geneweave-viewer       # web viewer"
echo "Data/cache: ~/.local/share/geneweave/"
