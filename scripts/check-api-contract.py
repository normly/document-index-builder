#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Check the reviewed schema without starting lifespan/models or a database."""

import argparse
from pathlib import Path
import sys

import yaml

from normly_api.main import create_app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "api/openapi.yaml",
    )
    args = parser.parse_args()
    expected = yaml.safe_load(args.contract.read_text())
    actual = create_app().openapi()
    if expected != actual:
        print("retrieval OpenAPI differs from the reviewed contract", file=sys.stderr)
        return 1
    print("retrieval OpenAPI matches the reviewed contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
