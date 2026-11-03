"""Session state, public research cache and private conversation photographs."""

import sqlalchemy as sa
from alembic import op

revision = "b51005af0002"
down_revision = "a51005af0001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("assistant_conversations") as batch:
        batch.add_column(sa.Column("memory", sa.JSON(), nullable=False, server_default="{}"))
    op.create_table(
        "assistant_research_cache",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.Double(), nullable=False),
    )
    op.create_table(
        "assistant_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index(
        "ix_assistant_attachments_conversation_id", "assistant_attachments", ["conversation_id"]
    )


def downgrade():
    op.drop_table("assistant_attachments")
    op.drop_table("assistant_research_cache")
    with op.batch_alter_table("assistant_conversations") as batch:
        batch.drop_column("memory")
