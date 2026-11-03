"""Private assistant conversations, preferences and presentation."""

import sqlalchemy as sa
from alembic import op

revision = "a51005af0001"
down_revision = "f80510c00001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("pending_request", sa.String(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index("ix_assistant_conversations_user_id", "assistant_conversations", ["user_id"])
    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint(
            "conversation_id", "request_id", "role", name="uq_assistant_message_request"
        ),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_assistant_message_role"),
    )
    op.create_index(
        "ix_assistant_messages_conversation_id", "assistant_messages", ["conversation_id"]
    )
    op.create_table(
        "assistant_preferences",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("motion", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("typewriter", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("voice", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "assistant_configuration",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("greeting", sa.String(), nullable=False),
        sa.Column("suggestions", sa.JSON(), nullable=False),
    )


def downgrade():
    op.drop_table("assistant_messages")
    op.drop_table("assistant_conversations")
    op.drop_table("assistant_preferences")
    op.drop_table("assistant_configuration")
