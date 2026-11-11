# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import json

import pytest


def config_document(tmp_path):
    return {
        "build_id": "synthetic-01", "output_version": "2026.11.1",
        "sources": [{"adapter": "baua", "directory": str(tmp_path)}],
        "embedding_model": {
            "name": "intfloat/multilingual-e5-large",
            "revision": "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3", "dimension": 1024,
        },
        "strategy": {"name": "source-adapters", "revision": "1"},
    }


def test_validated_build_configuration_roundtrip(tmp_path):
    from normly_core.pipeline.build_config import load_build_config

    path = tmp_path / "config.json"
    path.write_text(json.dumps(config_document(tmp_path)))
    config = load_build_config(path)
    assert config.build_id == "synthetic-01"
    assert config.output_version == "2026.11.1"
    assert config.sources[0].directory == tmp_path


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(build_id="../escape"),
    lambda d: d.update(output_version="../escape"),
    lambda d: d.update(sources=[]),
    lambda d: d["sources"][0].update(adapter="unknown"),
    lambda d: d["sources"][0].update(directory="/not-present-document-index"),
    lambda d: d["embedding_model"].update(dimension=12),
    lambda d: d["embedding_model"].update(revision="moving-main"),
    lambda d: d["strategy"].update(revision="unknown"),
    lambda d: d.update(database_url="postgresql://secret"),
    lambda d: d.update(private_key="secret"),
])
def test_invalid_or_credential_bearing_configuration_is_refused(tmp_path, mutation):
    from normly_core.pipeline.build_config import load_build_config

    data = config_document(tmp_path)
    mutation(data)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_build_config(path)
