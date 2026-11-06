#!/usr/bin/env python3
"""Convenience script to validate dataset partition disjointness."""

from __future__ import annotations

import sys

from slt_corpus.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    return cli_main(["validate-splits", *args])


if __name__ == "__main__":
    sys.exit(main())
