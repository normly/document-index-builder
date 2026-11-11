# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
from pathlib import Path

import yaml


def test_openapi_matches_reviewed_contract():
    from normly_api.main import create_app

    expected = yaml.safe_load((Path(__file__).parents[1] / "openapi.yaml").read_text())
    assert create_app().openapi() == expected
