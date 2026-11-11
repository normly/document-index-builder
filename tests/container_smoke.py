# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""End-to-end synthetic CLI/Compose rehearsal; cleans only its unique projects."""

import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

from normly_core.exchange.signing import generate_keypair

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "core/tests/pipeline"))
from synthetic_fixtures import fixture_directory

os.chdir(root)
endpoint = (
    os.environ.get("DOCKER_HOST")
    or subprocess.check_output(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        text=True,
    ).strip()
)
if not endpoint.startswith("unix://"):
    raise RuntimeError(
        "Synthetic integration rehearsal requires a local Unix-socket Docker engine"
    )
nonce = secrets.token_hex(8)
work = root / ".local" / ("container-smoke-" + nonce)
inputs = work / "inputs" / "dguv"
inputs.mkdir(parents=True)
pdf = inputs / "dguv_synthetic.pdf"
shutil.copyfile(fixture_directory() / "dguv_sample_vorschrift.pdf", pdf)
private, public = generate_keypair()
key = work / "private.pem"
key.write_bytes(private)
key.chmod(0o600)
pub = work / "public.pub.pem"
pub.write_bytes(public)
releases = work / "releases"
releases.mkdir()
base = dict(
    os.environ,
    NORMLY_BUILD_POSTGRES_PASSWORD=secrets.token_hex(16),
    NORMLY_POSTGRES_PASSWORD=secrets.token_hex(16),
    NORMLY_RETRIEVAL_IMAGE="normly/document-index-retrieval:dev",
    NORMLY_ENVIRONMENT="production",
)
projects = []


def register(project, kind):
    for resource in ("container", "volume", "network"):
        if resource == "container":
            command = [
                "docker",
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ]
        else:
            command = [
                "docker",
                resource,
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ]
        if subprocess.check_output(command, text=True).strip():
            raise RuntimeError("Refusing to reuse an existing Docker project")
    projects.append((project, kind))


def run(command, env, expected=0):
    result = subprocess.run(
        command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    with (work / "commands.log").open("a") as log:
        log.write(result.stdout + "\n")
    if result.returncode != expected:
        print(result.stdout, flush=True)
        raise RuntimeError(
            f"command returned {result.returncode}; expected {expected}: {command[:3]}"
        )
    return result.stdout


def compose(project, *args):
    return [
        "docker",
        "compose",
        "--project-directory",
        str(root),
        "-p",
        project,
        "-f",
        str(root / "compose.yaml"),
        "-f",
        str(work / "consumer-override.json"),
        *args,
    ]


try:
    inspection_config = work / "inspect.json"
    inspection_config.write_text(
        json.dumps(
            {
                "source": "dguv",
                "input_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                "rights": {
                    "jurisdiction": "DE",
                    "may_process": True,
                    "legal_basis_reference": "Invented synthetic test fixture",
                },
                "docling": {},
            }
        )
    )
    inspect_project = "di-inspect-" + nonce
    register(inspect_project, "build")
    run(
        [
            str(root / "scripts/inspect-pdf"),
            str(pdf),
            str(inspection_config),
            "dguv",
            str(work / "inspection"),
        ],
        dict(base, COMPOSE_PROJECT_NAME=inspect_project),
    )
    assert (work / "inspection/document.md").is_file()
    assert (work / "inspection/document.md").stat().st_uid == os.getuid()
    assert set(
        json.loads((work / "inspection/report.json").read_text())["model_revisions"]
    ) == {"layout", "layout_onnx", "tableformer"}
    print(
        "PASS: single-PDF container inspection, Markdown/JSON/config/report, host ownership",
        flush=True,
    )
    for index in (1, 2):
        project = f"di-build-{nonce}-{index}"
        register(project, "build")
        config = work / f"build-{index}.json"
        config.write_text(
            json.dumps(
                {
                    "build_id": f"smoke-{nonce}-{index}",
                    "output_version": f"2026.11.{index}",
                    "sources": [{"adapter": "dguv", "directory": "/inputs/dguv"}],
                    "embedding_model": {
                        "name": "intfloat/multilingual-e5-large",
                        "revision": "3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3",
                        "dimension": 1024,
                    },
                    "strategy": {"name": "source-adapters", "revision": "1"},
                    "docling": {"accelerator_threads": index},
                }
            )
        )
        run(
            [
                str(root / "scripts/build-knowledge"),
                str(config),
                str(work / "inputs"),
                str(releases),
                str(key),
            ],
            dict(base, COMPOSE_PROJECT_NAME=project),
        )
        assert (releases / f"2026.11.{index}/manifest.json.sig").is_file()
        print(
            f"PASS: isolated builder configuration {index} -> signed release 2026.11.{index}",
            flush=True,
        )

    consumer = "di-consumer-" + nonce
    register(consumer, "consumer")
    # A test-only localhost server inside the initializer honors fetch's HTTP
    # localhost exception without exposing any host port or private key.
    server = """import functools,threading
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
server=ThreadingHTTPServer(('127.0.0.1',8765),functools.partial(SimpleHTTPRequestHandler,directory='/releases'))
threading.Thread(target=server.serve_forever,daemon=True).start()
"""
    bootstrap = (
        server
        + "from normly_core.exchange.bootstrap import main\nraise SystemExit(main())\n"
    )
    override = {
        "services": {
            "bootstrap": {
                "volumes": [str(releases) + ":/releases:ro"],
                "command": ["python", "-c", bootstrap],
            }
        }
    }
    (work / "consumer-override.json").write_text(json.dumps(override))
    env = dict(
        base,
        NORMLY_KB_VERSION="2026.11.1",
        NORMLY_KB_BASE_URL="http://localhost:8765",
        NORMLY_KB_PUBLIC_KEY_FILE=str(pub),
        NORMLY_NETWORK_NAME=consumer,
    )
    run(compose(consumer, "up", "-d", "--wait", "--wait-timeout", "240"), env)

    def query(path):
        code = (
            "import json,urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000"
            + path
            + "').read().decode())"
        )
        return json.loads(
            run(compose(consumer, "exec", "-T", "retrieval", "python", "-c", code), env)
        )

    assert query("/health/ready")["knowledge_version"] == "2026.11.1"
    hits = query("/v1/documents/search?jurisdiction=DE")
    assert len(hits["results"]) == 1
    document_id = hits["results"][0]["best_match"]["id"]
    assert len(query(f"/v1/documents/{document_id}/segments?jurisdiction=DE")) == 3
    print(
        "PASS: fresh populated consumer, ready API, document search and three parsed segments",
        flush=True,
    )
    importer = (
        server
        + "from normly_core.exchange.__main__ import main\nraise SystemExit(main(['import','--fetch','2026.11.2']))\n"
    )
    run(
        compose(
            consumer, "run", "--rm", "--no-deps", "bootstrap", "python", "-c", importer
        ),
        env,
    )
    assert query("/health/ready")["knowledge_version"] == "2026.11.2"
    assert len(query("/v1/documents/search?jurisdiction=DE")["results"]) == 1
    print("PASS: explicit transactional knowledge update to second build", flush=True)
    broken = releases / "2026.11.3"
    shutil.copytree(releases / "2026.11.2", broken)
    manifest = json.loads((broken / "manifest.json").read_text())
    manifest["dump_version"] = "2026.11.3"
    (broken / "manifest.json").write_text(json.dumps(manifest))
    failed = (
        server
        + "from normly_core.exchange.__main__ import main\nraise SystemExit(main(['import','--fetch','2026.11.3']))\n"
    )
    run(
        compose(
            consumer, "run", "--rm", "--no-deps", "bootstrap", "python", "-c", failed
        ),
        env,
        expected=1,
    )
    assert query("/health/ready")["knowledge_version"] == "2026.11.2"
    env["NORMLY_KB_VERSION"] = "2026.11.2"
    run(compose(consumer, "up", "-d", "--wait", "--wait-timeout", "240"), env)
    assert query("/health/ready")["knowledge_version"] == "2026.11.2"
    print(
        "PASS: invalid signed update leaves previous release ready; restart preserves selected release",
        flush=True,
    )
    print("Smoke artifacts:", work, flush=True)
finally:
    for project, kind in reversed(projects):
        if kind == "build":
            command = [
                "docker",
                "compose",
                "--project-directory",
                str(root),
                "-p",
                project,
                "-f",
                str(root / "compose.build.yaml"),
                "down",
                "--volumes",
            ]
            run(command, base)
        else:
            run(compose(project, "down", "--volumes"), env)
