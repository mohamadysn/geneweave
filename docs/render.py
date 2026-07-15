#!/usr/bin/env python3
"""Serve Quarto documentation over HTTP and open the default browser."""

import argparse
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import webbrowser
from pathlib import Path
from threading import Timer

DOCS_DIR = Path(__file__).resolve().parent
SITE_DIR = DOCS_DIR / "_site"
DEFAULT_PORT = 8088


def _require_quarto():
    if not shutil.which("quarto"):
        print("Error: Quarto is not installed.", file=sys.stderr)
        print("Install from https://quarto.org/docs/get-started/", file=sys.stderr)
        sys.exit(1)


def render_docs(site_url=None):
    _require_quarto()
    cmd = ["quarto", "render"]
    if site_url:
        cmd.extend(["--site-url", site_url])
    print("Rendering documentation...")
    subprocess.run(cmd, cwd=DOCS_DIR, check=True)
    print(f"Site built: {SITE_DIR / 'index.html'}")


def preview_docs(port=DEFAULT_PORT, no_open=False):
    """Live preview with Quarto dev server (HTTP)."""
    _require_quarto()
    url = f"http://127.0.0.1:{port}/"
    print(f"Preview server: {url}")
    print("Press Ctrl+C to stop")

    if not no_open:
        Timer(1.5, lambda: webbrowser.open(url)).start()

    subprocess.run(
        ["quarto", "preview", "--port", str(port), "--no-browser"],
        cwd=DOCS_DIR,
    )


def serve_static(port=DEFAULT_PORT, no_open=False):
    """Serve the built _site folder over HTTP."""
    if not (SITE_DIR / "index.html").exists():
        print("Building site first...")
        render_docs()

    url = f"http://127.0.0.1:{port}/"
    print(f"Serving {SITE_DIR} at {url}")
    print("Press Ctrl+C to stop")

    if not no_open:
        Timer(0.5, lambda: webbrowser.open(url)).start()

    os.chdir(SITE_DIR)
    with socketserver.TCPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(
        description="Build or preview documentation over HTTP"
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Render static HTML only (no server)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Serve built _site/ over HTTP (builds first if needed)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the default browser",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"HTTP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--site-url",
        default=None,
        help="Base URL for links (used with --build, e.g. GitHub Pages URL)",
    )
    args = parser.parse_args()

    if args.build:
        render_docs(site_url=args.site_url)
        if args.serve:
            serve_static(port=args.port, no_open=args.no_open)
        return

    if args.serve:
        serve_static(port=args.port, no_open=args.no_open)
        return

    preview_docs(port=args.port, no_open=args.no_open)


if __name__ == "__main__":
    main()
