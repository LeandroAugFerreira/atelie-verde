"""Separate illustrative references from uploaded project photographs."""

import sqlalchemy as sa
from alembic import op

revision = "b9e74d0123ac"
down_revision = "fe57b97abb13"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "projects", sa.Column("reference_image_url", sa.String(), server_default="", nullable=False)
    )
    op.add_column(
        "projects",
        sa.Column("reference_image_note", sa.String(), server_default="", nullable=False),
    )


def downgrade():
    op.drop_column("projects", "reference_image_note")
    op.drop_column("projects", "reference_image_url")
