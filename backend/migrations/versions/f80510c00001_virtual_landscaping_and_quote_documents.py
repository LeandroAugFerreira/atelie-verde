"""Virtual landscaping brief and private request documents."""

import sqlalchemy as sa
from alembic import op

revision = "f80510c00001"
down_revision = "e118c5d02005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("services") as batch:
        batch.add_column(
            sa.Column("delivery_mode", sa.String(), nullable=False, server_default="Presencial")
        )
    with op.batch_alter_table("quotes") as batch:
        batch.add_column(sa.Column("brief", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(
            sa.Column("brief_revision", sa.Integer(), nullable=False, server_default="0")
        )
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("brief", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(
            sa.Column("brief_revision", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("delivery_mode", sa.String(), nullable=False, server_default="Presencial")
        )
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("quote_id", sa.Integer(), nullable=True))
        batch.alter_column("project_id", existing_type=sa.Integer(), nullable=True)
        batch.create_foreign_key("fk_documents_quote_id", "quotes", ["quote_id"], ["id"])
        batch.create_check_constraint(
            "ck_documents_parent",
            "(project_id IS NOT NULL AND quote_id IS NULL) OR (project_id IS NULL AND quote_id IS NOT NULL)",
        )


def downgrade():
    # Refuse destructive downgrades while request attachments exist.
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM documents WHERE quote_id IS NOT NULL")):
        raise RuntimeError("Preserve os documentos de orçamentos antes de reverter esta migração.")
    with op.batch_alter_table("documents") as batch:
        batch.drop_constraint("ck_documents_parent", type_="check")
        batch.drop_constraint("fk_documents_quote_id", type_="foreignkey")
        batch.drop_column("quote_id")
        batch.alter_column("project_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("delivery_mode")
        batch.drop_column("brief")
        batch.drop_column("brief_revision")
    with op.batch_alter_table("quotes") as batch:
        batch.drop_column("brief")
        batch.drop_column("brief_revision")
    with op.batch_alter_table("services") as batch:
        batch.drop_column("delivery_mode")
