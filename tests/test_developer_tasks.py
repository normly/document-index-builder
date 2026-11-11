# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).parents[1]


@pytest.fixture()
def fake_docker(tmp_path):
    directory = tmp_path / "fake-bin"
    directory.mkdir()
    docker = directory / "docker"
    docker.write_text("""#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['DOCKER_LOG'],'a') as f:f.write(json.dumps(args)+'\\n')
if os.environ.get('DOCKER_ENV_LOG'):
 with open(os.environ['DOCKER_ENV_LOG'],'a') as f:f.write(json.dumps({'args':args,'builder_image':os.environ.get('NORMLY_BUILDER_IMAGE')})+'\\n')
status=int(os.environ.get('FAKE_DOCKER_EXIT','0'))
if status:sys.exit(status)
if args[:2]==['image','inspect']:print('sha256:resolved-test-image')
if 'inspect' in args and '--no-deps' in args:
 for arg in args:
  if arg.endswith(':/outputs:rw'):
   out=Path(arg[:-len(':/outputs:rw')])/'result'
   out.mkdir();(out/'document.md').write_text('Synthetic output')
""")
    docker.chmod(0o755)
    log = tmp_path / "docker-args.jsonl"
    env = dict(
        os.environ,
        PATH=str(directory) + os.pathsep + os.environ["PATH"],
        DOCKER_LOG=str(log),
    )
    return env, log


def test_inspection_quotes_paths_mounts_readonly_and_uses_no_database(
    tmp_path, fake_docker
):
    env, log = fake_docker
    pdf, config = tmp_path / "one PDF.pdf", tmp_path / "my config.json"
    pdf.write_bytes(b"synthetic")
    config.write_text("{}")
    output = tmp_path / "inspection output"
    result = subprocess.run(
        [str(ROOT / "scripts/inspect-pdf"), str(pdf), str(config), "baua", str(output)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    args = json.loads(log.read_text())
    assert "--no-deps" in args
    assert "up" not in args
    assert f"{pdf}:/inputs/document.pdf:ro" in args
    assert f"{config}:/config/inspection.json:ro" in args
    assert args[args.index("--user") + 1] == f"{os.getuid()}:{os.getgid()}"
    assert args[-1] == "/outputs/result"
    assert (output / "document.md").read_text() == "Synthetic output"
    assert not list(tmp_path.glob(".inspection-*"))


def test_inspection_propagates_container_failure_and_preserves_existing_output(
    tmp_path, fake_docker
):
    env, _ = fake_docker
    pdf, config = tmp_path / "input.pdf", tmp_path / "config.json"
    pdf.write_bytes(b"synthetic")
    config.write_text("{}")
    output = tmp_path / "result"
    command = [
        str(ROOT / "scripts/inspect-pdf"),
        str(pdf),
        str(config),
        "baua",
        str(output),
    ]
    result = subprocess.run(
        command, env={**env, "FAKE_DOCKER_EXIT": "17"}, capture_output=True
    )
    assert result.returncode == 17
    assert not output.exists()
    output.mkdir()
    (output / "keep").write_text("user work")
    assert subprocess.run(command, env=env, capture_output=True).returncode != 0
    assert (output / "keep").read_text() == "user work"


def test_vscode_tasks_expose_the_three_documented_workflows():
    config = json.loads((ROOT / ".vscode/tasks.json").read_text())
    tasks = {t["label"]: t for t in config["tasks"]}
    assert set(tasks) == {
        "Document Index: Build builder image",
        "Document Index: Inspect PDF",
        "Document Index: Build knowledge release",
    }
    assert tasks["Document Index: Inspect PDF"]["type"] == "process"
    assert (
        tasks["Document Index: Inspect PDF"]["command"]
        == "${workspaceFolder}/scripts/inspect-pdf"
    )
    assert {i["id"] for i in config["inputs"]} >= {
        "pdf",
        "inspectionConfig",
        "source",
        "inspectionOutput",
        "buildConfig",
        "inputs",
        "releaseOutput",
        "signingKey",
    }


def test_build_wrapper_pins_the_resolved_image_instead_of_reusing_a_mutable_tag(
    tmp_path, fake_docker
):
    env, _ = fake_docker
    config, key = tmp_path / "build.json", tmp_path / "test.pem"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    config.write_text("{}")
    key.write_text("ephemeral test placeholder")
    environment_log = tmp_path / "environment.jsonl"
    env = {**env, "DOCKER_ENV_LOG": str(environment_log)}
    env.pop("NORMLY_BUILDER_IMAGE", None)
    result = subprocess.run(
        [
            str(ROOT / "scripts/build-knowledge"),
            str(config),
            str(inputs),
            str(tmp_path / "output"),
            str(key),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in environment_log.read_text().splitlines()]
    run = next(call for call in calls if "run" in call["args"])
    assert run["builder_image"] == "sha256:resolved-test-image"
    assert "NORMLY_BUILDER_IMAGE_DIGEST=sha256:resolved-test-image" in run["args"]
