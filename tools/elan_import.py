#!/usr/bin/env python3
"""Convenience script to import an ELAN .eaf annotation file into the SLT catalog."""

from __future__ import annotations

import sys

from slt_corpus.cli import main as cli_main


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    return cli_main(["elan-import", *args])


if __name__ == "__main__":
    sys.exit(main())
