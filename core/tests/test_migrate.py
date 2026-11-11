# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

from pathlib import Path


def test_password_percent_encoding_survives_configuration():
    from normly_core.migrate import _alembic_config

    url = "postgresql+psycopg://user:p%2Fx@localhost/db"
    config = _alembic_config(url, Path("core"))
    assert config.get_main_option("sqlalchemy.url") == url
