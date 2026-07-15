#!/usr/bin/python3
#-*- coding: utf-8 -*-

from pathlib import Path

from annotation.config import DEFAULT_OUTPUT_DIR


def resolve_output_stem(input_file, output_dir=None):
    stem = Path(input_file).stem
    if output_dir:
        directory = Path(output_dir)
    else:
        directory = DEFAULT_OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory / stem)


def output_paths(input_file, output_dir=None):
    stem = resolve_output_stem(input_file, output_dir)
    return {
        "stem": stem,
        "html": f"{stem}_annotation.html",
        "csv": f"{stem}_annotation.csv",
        "xlsx": f"{stem}_annotation.xlsx",
        "json": f"{stem}_annotation.json",
        "summary": f"{stem}_summary.txt",
        "manifest": f"{stem}_manifest.json",
    }
