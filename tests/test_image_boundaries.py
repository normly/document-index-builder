# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Run explicitly after building both images; inspects artifacts, not Dockerfile text."""
import json
import os
import subprocess

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("RUN_IMAGE_TESTS") != "1", reason="requires built Docker images; mandatory release check")


@pytest.mark.parametrize("target", ["builder", "retrieval"])
def test_image_is_nonroot_has_offline_models_and_no_source_inputs(target):
    image = f"normly/document-index-{target}:dev"
    config = json.loads(subprocess.check_output(["docker", "image", "inspect", image]))[0]["Config"]
    assert config["User"] not in ("", "root", "0", "0:0")
    check = """
import os,pathlib
assert os.getuid() != 0
assert os.environ['HF_HUB_OFFLINE'] == '1'
assert pathlib.Path(os.environ['NORMLY_EMBEDDING_MODEL_PATH']).is_dir()
assert pathlib.Path(os.environ['NORMLY_EMBEDDING_MODEL_PATH'], 'model.safetensors').is_file()
assert pathlib.Path('/app/LICENSE').is_file()
assert not any(pathlib.Path('/app/core').rglob('*.pdf'))
assert not pathlib.Path('/run/secrets').exists()
assert not pathlib.Path('/inputs').exists()
"""
    subprocess.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python", image, "-c", check], check=True)


def test_retrieval_has_no_docling_package_but_imports_api():
    subprocess.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python",
        "normly/document-index-retrieval:dev", "-c", """
import importlib.util
assert importlib.util.find_spec('docling') is None
from normly_api.main import create_app
assert '/v1/documents/search' in create_app().openapi()['paths']
"""], check=True)
