"""Unit tests for tools/ helper scripts."""

from __future__ import annotations

import json
from pathlib import Path

from tools.corpus_audit import main as audit_main
from tools.corpus_init import main as init_main
from tools.split_validate import main as split_main


def test_tools_init_and_audit(tmp_path: Path):
    db_file = tmp_path / "tools_catalog.sqlite3"
    corpus_dir = tmp_path / "corpus_tools"

    # Test tools.corpus_init
    ret = init_main(["--root", str(corpus_dir), "--db", str(db_file)])
    assert ret == 0
    assert db_file.is_file()

    # Test tools.corpus_audit
    ret = audit_main(["--db", str(db_file)])
    assert ret == 0


def test_tools_split_validate(tmp_path: Path):
    splits_file = tmp_path / "splits.json"
    splits_file.write_text(
        json.dumps({"splits": {"train": ["r1"], "test": ["r2"]}}), encoding="utf-8"
    )
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text(
        json.dumps({"r1": "signer_1", "r2": "signer_2"}), encoding="utf-8"
    )

    ret = split_main(["--splits-json", str(splits_file), "--mapping-json", str(mapping_file)])
    assert ret == 0
