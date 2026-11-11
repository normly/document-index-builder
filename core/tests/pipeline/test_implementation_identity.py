# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors


def test_source_identity_tracks_source_bytes_not_checkout_path_or_bytecode(tmp_path):
    from normly_core.pipeline.implementation import source_tree_digest

    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir()
    second.mkdir()
    (first / "parser.py").write_text("strategy = 1\n")
    (second / "parser.py").write_text("strategy = 1\n")
    before = source_tree_digest(first)
    assert source_tree_digest(second) == before
    (first / "parser.pyc").write_bytes(b"not runtime source")
    assert source_tree_digest(first) == before
    (first / "parser.py").write_text("strategy = 2\n")
    assert source_tree_digest(first) != before
