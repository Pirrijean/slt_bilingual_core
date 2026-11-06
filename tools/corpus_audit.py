#!/usr/bin/env python3
"""Convenience script to generate a complete SLT Corpus audit report."""

from __future__ import annotations

import sys

from slt_corpus.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    return cli_main(["audit", *args])


if __name__ == "__main__":
    sys.exit(main())
