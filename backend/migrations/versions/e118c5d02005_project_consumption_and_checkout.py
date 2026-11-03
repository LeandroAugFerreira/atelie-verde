"""Project stock consumption and replay-safe checkout."""

import sqlalchemy as sa
from alembic import op

revision = "e118c5d02005"
down_revision = "d4278ee1024a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("orders") as batch:
        batch.add_column(sa.Column("request_key", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("request_payload", sa.JSON(), nullable=False, server_default="{}")
        )
        batch.create_unique_constraint("uq_orders_request_key", ["request_key"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    with op.batch_alter_table("stock_moves") as batch:
        batch.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_stock_moves_project_id", "projects", ["project_id"], ["id"])
    op.create_index("ix_stock_moves_project_id", "stock_moves", ["project_id"])
    op.create_index("ix_stock_moves_product_id", "stock_moves", ["product_id"])


def downgrade():
    op.drop_index("ix_stock_moves_product_id", table_name="stock_moves")
    op.drop_index("ix_stock_moves_project_id", table_name="stock_moves")
    with op.batch_alter_table("stock_moves") as batch:
        batch.drop_constraint("fk_stock_moves_project_id", type_="foreignkey")
        batch.drop_column("project_id")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("uq_orders_request_key", type_="unique")
        batch.drop_column("request_payload")
        batch.drop_column("request_key")
