#!/usr/bin/env python3
"""Convenience script to initialize the SLT Corpus catalog and directories."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from slt_corpus.catalog import CorpusCatalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize SLT Corpus catalog.")
    parser.add_argument("--root", default="corpus/lsc", help="Corpus root directory")
    parser.add_argument("--db", default="data/private/catalog.sqlite3", help="Catalog DB path")
    args = parser.parse_args(argv)

    Path(args.root).mkdir(parents=True, exist_ok=True)
    catalog = CorpusCatalog(args.db)
    print(f"SLT Corpus initialized successfully at {catalog.db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
