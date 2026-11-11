# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
from alembic import op
import sqlalchemy as sa

revision = "0002_build_identity"
down_revision = "0001_knowledge_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("knowledge_build",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("build_id", sa.String(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_knowledge_build_single_row"),
    )


def downgrade():
    op.drop_table("knowledge_build")
