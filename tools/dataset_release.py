#!/usr/bin/env python3
"""Convenience script to build or validate an immutable dataset release."""

from __future__ import annotations

import sys

from slt_corpus.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    return cli_main(["release", *args])


if __name__ == "__main__":
    sys.exit(main())
