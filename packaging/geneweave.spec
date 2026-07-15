# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for GeneWeave (Linux / Windows)."""

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "annotation" / "templates"), "annotation/templates"),
    (str(ROOT / "viewer" / "templates"), "viewer/templates"),
    (str(ROOT / "data"), "data"),
]

hiddenimports = [
    "annotation",
    "annotation.cli",
    "annotation.gui",
    "annotation.cache",
    "annotation.config",
    "annotation.export",
    "annotation.paths",
    "annotation.summary",
    "annotation.databases",
    "annotation.databases.ensembl",
    "annotation.databases.ncbi",
    "annotation.databases.go",
    "annotation.databases.pdb",
    "annotation.databases.kegg",
    "annotation.databases.uniprot",
    "annotation.databases.prosite",
    "annotation.databases.pfam",
    "annotation.databases.string_db",
    "viewer",
    "viewer.app",
    "Bio",
    "Bio.Entrez",
    "openpyxl",
    "flask",
    "jinja2",
    "tqdm",
    "requests",
]

def _analysis(entry, **kwargs):
    return Analysis(
        [str(ROOT / entry)],
        pathex=[str(ROOT)],
        binaries=[],
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
        **kwargs,
    )


gui_a = _analysis("interface.py")
cli_a = _analysis("main.py")
viewer_a = _analysis("viewer.py")

gui_pyz = PYZ(gui_a.pure)
cli_pyz = PYZ(cli_a.pure)
viewer_pyz = PYZ(viewer_a.pure)

gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    gui_a.binaries,
    gui_a.datas,
    [],
    name="GeneWeave",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

cli_exe = EXE(
    cli_pyz,
    cli_a.scripts,
    cli_a.binaries,
    cli_a.datas,
    [],
    name="geneweave-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

viewer_exe = EXE(
    viewer_pyz,
    viewer_a.scripts,
    viewer_a.binaries,
    viewer_a.datas,
    [],
    name="geneweave-viewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
