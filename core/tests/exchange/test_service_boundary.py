# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import subprocess
import sys

import pytest

from normly_core.exchange.tables import (
    KNOWLEDGE_TABLES, OPERATIONAL_TABLES, PIPELINE_STATE_TABLES, SYSTEM_TABLES,
)
from normly_core.graph.postgres.orm import Base


def test_every_local_table_has_an_owner_and_no_user_data_is_exported():
    assert set(Base.metadata.tables) == set(
        KNOWLEDGE_TABLES + OPERATIONAL_TABLES + PIPELINE_STATE_TABLES + SYSTEM_TABLES
    )
    assert set(KNOWLEDGE_TABLES).isdisjoint({"account", "chat_message", "rate_limit_bucket"})


@pytest.mark.parametrize("command", ["export-deletions", "replay-deletions"])
def test_exchange_cli_does_not_own_user_maintenance(command):
    result = subprocess.run([sys.executable, "-m", "normly_core.exchange", command], capture_output=True, text=True)
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
