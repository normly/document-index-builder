# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import json
from pathlib import Path
import subprocess
import sys


def test_contract_checker_rejects_schema_drift(tmp_path):
    root = Path(__file__).parents[1]
    contract = json.loads((root / "api/openapi.yaml").read_text())
    contract["info"]["version"] = "unreviewed-change"
    path = tmp_path / "modified-contract.yaml"
    path.write_text(json.dumps(contract))
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/check-api-contract.py"),
            "--contract",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "differs" in result.stderr
    result = subprocess.run(
        [sys.executable, str(root / "scripts/check-api-contract.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
